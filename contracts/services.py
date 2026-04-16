import json
import os
from typing import TypedDict,List
from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint
from langgraph.graph import StateGraph, START, END
from .schemas import AuditResultSchema
from langchain_core.prompts import ChatPromptTemplate
#we create a prompt that tells AI to behave like a JSON generator

#1 setup Model (Qwen 2.5 will be best-in-class for following JSON )
llm_endpoint=HuggingFaceEndpoint(
    repo_id="Qwen/Qwen2.5-7B-Instruct",
    task="text-generation",
    huggingfacehub_api_token=os.getenv("HUGGINGFACEHUB_API_TOKEN")
)

model=ChatHuggingFace(llm=llm_endpoint)

# 2 define StateGraph

class AgentState(TypedDict):
    contract_text:str
    audit_data:dict #This will store validated pydantic data
    errors:List[str]

# 3 Logic node

def audit_contract_node(state:AgentState):
    # we convert our pydantic schema into JSON structure AI can understand

    json_schema=json.dumps(AuditResultSchema.model_json_schema(),indent=2)

    prompt=f"""
    You are a senior legal auditor. Analyze the following contract text.
    You MUST respond in valid JSON that matches the schema:
    {json_schema}

    contract_text:
    {state['contract_text'][:3000]}
    """

    response=model.invoke(prompt)

    try:
        # we parse the AI's streing response into a python dictinary
        # in a senior setup, we'd handle the ```json' markdown wrapper if the AI adds it

        content=response.content.replace("```json","").replace("```","").strip()
        raw_data=json.loads(content)

        #pydantic validates the data. If it's wrong, it throws and error

        validated=AuditResultSchema(**raw_data)

        return {"audit_data":validated.model_dump()}
    except Exception as e:
        return {"errors":[f"AI formatting error: {str(e)}"]}


# 4 building workflow

workflow=StateGraph(AgentState)
workflow.add_node("auditor",audit_contract_node)
workflow.add_edge(START,"auditor")
workflow.add_edge("auditor",END)


# compile 
contract_agent=workflow.compile()