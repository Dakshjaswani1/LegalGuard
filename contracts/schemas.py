
from pydantic import BaseModel,Field
from typing import List,Literal


#defining what a  single issue looks like
class AuditIssue(BaseModel):
    """Represents a specific legal risk found in the contract"""
    clause_name:str=Field(description="Name of legal clause")
    risk_level:Literal["Low","Medium","High"]=Field(description="the severity of the legal risk")
    explanation:str=Field(description="Detailed reason why this issue")
    suggestion:str=Field(description="How to rewrite this clause to be safer")


# defining the final strcuture AI must return
class AuditResultSchema(BaseModel):
    """The final structered response AI must provide"""
    summary:str=Field(description="One sentence summary of the contract")
    findings:List[AuditIssue]=Field(description="a list of specific risks identified")
    is_compliant:bool=Field(description="True if the contract meets basic safety standards")
