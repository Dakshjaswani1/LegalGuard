import json
import os
import re
from typing import TypedDict,List
from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint
from langchain_core.output_parsers import JsonOutputParser
from langgraph.graph import StateGraph, START, END
from .schemas import AuditResultSchema
from langchain_core.prompts import ChatPromptTemplate
#we create a prompt that tells AI to behave like a JSON generator

#1 setup Model (Qwen 2.5 will be best-in-class for following JSON )
llm_endpoint=HuggingFaceEndpoint(
    repo_id="Qwen/Qwen2.5-7B-Instruct",
    task="text-generation",
    huggingfacehub_api_token=os.getenv("HUGGINGFACEHUB_API_TOKEN"),
    timeout=300,
    max_new_tokens=2048,
)

model=ChatHuggingFace(llm=llm_endpoint)

# 2 define StateGraph

class AgentState(TypedDict):
    contract_text:str
    audit_data:dict #This will store validated pydantic data
    errors:List[str]

# 3 Logic node

def audit_contract_node(state:AgentState):
    # we use langchain's parser to help clean the output later

    parser=JsonOutputParser(pydantic_object=AuditResultSchema)
    retry_count=state.get("retry_count",0)

    # error_context=""
    # if state["errors"] and retry_count > 0:
    #     error_context=f"\n\nPREVIOUS ERROR: {state['error'][-1]}\n Please fix the JSON formatting and try again."


    prompt=f"""
    SYSTEM: You are a professional legal auditor.
    TASK: Analyze the contract text provided.

    INSTRUCTIONS:
    - Identify legal risks and suggest safer alternatives.
    - Return ONLY the final JSON object.
    - DO NOT include the schema defination or preamble.
    - Ensure 'is_complaint' is a boolean.

    {parser.get_format_instructions()}
    
    CONTRACT TEXT:
    {state['contract_text'][:3000]}

    """

    response=model.invoke(prompt)
    content=response.content
    try:
       # 1 Look for JSON inside markdown blocks first
       
        json_match=re.findall(r'```json\s*(.*?)\s*```',content,re.DOTALL)
        if json_match:
            # if multiple blocks take the last one (usually the data not the schema)
            json_str=json_match[-1]
        else:
            # 2 fallback: find everything between first '{' and last '}'
            # we avoid recursion and just use a greedy match

            match=re.search(r'(\{.*\})',content,re.DOTALL)
            json_str=match.group(1) if match else content
        
        # 3 use pydantic  to validate that the fields match our schema
        raw_data=json.loads(json_str)

        # if the model include the schema metadata dive into the actual property
        if "properties" in raw_data and "summary" not in raw_data:
            return {"errors":["AI returned schema instead of data. Please try again"]}
        
        validated=AuditResultSchema(**raw_data)
        return {"audit_data":validated.model_dump()}
    
    except Exception as e:
        return {"errors":[f"Parsing error:{str(e)}"],
                "audit_data":{}}
           

# 4 building workflow

workflow=StateGraph(AgentState)
workflow.add_node("auditor",audit_contract_node)
workflow.add_edge(START,"auditor")
workflow.add_edge("auditor",END)


# compile 
contract_agent=workflow.compile()