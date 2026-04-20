import json
import os
import re
from datetime import datetime
from typing import TypedDict,List,Literal
from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint
from langchain_core.output_parsers import JsonOutputParser
from langgraph.graph import StateGraph, START, END
from .schemas import AuditResultSchema
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader

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

# 2 file extraction logic

def extract_text_from_file(file_path):
    """Agnostic loader based on extension."""
    ext=os.path.splitext(file_path)[1].lower()

    if ext==".pdf":
        loader=PyPDFLoader(file_path)
    elif ext in [".docx", ".doc"]:
        loader=Docx2txtLoader(file_path)
    else:
        with open(file_path,'r',encoding="utf-8",errors="ignore") as f:
            return f.read()
    
    docs=loader.load()
    return "\n".join([doc.page_content for doc in docs])

# 2 AI Agent logic

class AgentState(TypedDict):
    contract_text:str
    audit_data:dict #This will store validated pydantic data
    errors:List[str]
    critique:str #stores the senior partner feedback
    retry_count:int # tracks how many times we have tried to fix it


# senior tool deterministic validator
def deterministic_checks(text:str)->List[dict]:
    """Catches mistakes LLMs often miss using pure python logic."""
    issues=[]

    if "â‚" in text or "Â" in text:
        issues.append({
            "clause_name":"Document Integrity",
            "risk_level":"Medium",
            "explanation":"Character encoding error detected (e.g.,'â‚¹'). This indicates a professional drafting error.",
            "suggestion":"Fix character encoding to correctly display symbols like ₹."
        })

    # check 2 simpler date validation( April 31/32, etc..)
    # this is a bassic regex; a real app would use libraries like 'dateparser'
    date_matches=re.findall(r'(\d{1,2})(?:st|nd|rd|th)?\s+(January|February|March|April|June|July|August|September|October|Novmeber|December)\s+(\d{4})',text)
    for day,month,year in date_matches:
        try:
            datetime.strptime(f"{day} {month} {year}","%d %B %Y")
        except ValueError:
            issues.append({
                "clause_name":"Dates",
                "risk_level":"High",
                "explanation":f"Invalid date detected: '{day} {month} {year}'.",
                "suggestion":"Correct the calender date to a valid date"    
            })
    return issues


# 3 Node 1 : The Initial Auditor
def audit_node(state:AgentState):
    parser=JsonOutputParser(pydantic_object=AuditResultSchema)\
    
    # we incldue the critique if this is a retry
    critique_context=f"\n\nSENIOR REVIEW FEEDBACK: {state.get('critique','')}\nPlease address these misses." if state.get('critique') else ""

    prompt=f"""
    SYSTEM: You are an expert legal auditor.
    TASK: Analyze the contract. Use this CHECKLIST:
    1. Identify all parties (Name, Address, Identity)
    2. Validate all Dates and Deliverables.
    3. Check Scope (Flag 'Unlimited' or 'without limitation').
    4. Verify Indemnity and Force Major clauses.

    {parser.get_format_instructions()}
    {critique_context}

    CONTRACT TEXT:
    {state['contract_text'][:4000]}
    """
    response=model.invoke(prompt)

    try:
        #Extract last JSON block'
        json_str=re.findall(r'(\{.*\})',response.content,re.DOTALL)[-1]
        data=json.loads(json_str)

        #Merge deterministic issues into LLM findings
        det_issues=deterministic_checks(state['contract_text'])
        data['findings'].extend(det_issues)

        return {"audit_data":data,"retry_count":state.get("retry_count",0)+1}
    except Exception as e:
        return {"errors":[str(e)]}

def critique_node(state:AgentState):
    """The 'Reviewer' node that specifically looks for what the auditor missed."""
    findings=json.dumps(state["audit_data"])
    prompt=f"""
    You are a Senior Legal Partner. Review the findings of Junior Auditor.
    Findings:{findings}

    Check for:
    - Missed 'Unlimited' scope?
    - Missed missing Indemnity?
    - Missed missing Deliverables?
    - Are the risk levels too low (e.g. Scope should be HIGH)?

    If it's perfect say 'APPROVED'. Otherwise, list the missing issue.

"""
    response=model.invoke(prompt)
    return {"critique":response.content}

# 5 Routing Logic
def should_continue(state:AgentState):
    if "APPROVED" in state['critique'] or state['retry_count'] >= 2:
        return "end"
    return "retry"


# 6 build graph

workflow=StateGraph(AgentState)
workflow.add_node("auditor",audit_node)
workflow.add_node("critiquer",critique_node)
workflow.add_edge(START,"auditor")
workflow.add_edge("auditor","critiquer")
workflow.add_conditional_edges("critiquer", should_continue,{
    "retry":"auditor",
    "end":END
})

contract_agent=workflow.compile()