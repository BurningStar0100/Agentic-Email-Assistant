"""Pydantic models and type definitions for the email assistant"""
from langgraph.graph import MessagesState
from typing import Literal , Optional , Dict, Any, List
from pydantic import BaseModel , Field

class State(MessagesState):
    """State for thr email assistant graph"""
    email_input : dict
    classification_response : Literal["ignore","respond","notify"]

class RouterSchema(BaseModel):
    """Schema for email triage routing decisions.""" 
    classification: Literal["ignore", "respond", "notify"] = Field(
        description="The classification of an email: 'ignore' for irrelevant emails, "
        "'notify' for important information that doesn't need a response, "
        "'respond' for emails that need a reply",
    )
    reasoning: str = Field(
        description="Step-by-step reasoning behind the classification."
    )

class ProcessEmailResponse(BaseModel):
    """Response schema for processing email"""
    classification: Literal["ignore","respond","notify"]
    response : str
    reasoning : str

class EmailInput(BaseModel):
    """"""
    author : str = Field(description="Email sender")
    to : str = Field(description="email receiver")
    subject : str = Field(description="subject of the email")
    email_thread : str = Field(description="the content of the email body")

class InterruptInfo(BaseModel):
    action: str = Field(description="The tool/action that triggered the interrupt")
    args: Dict[str, Any] = Field(description="Original arguments for the action")
    description: str = Field(description="Human-readable description of the action")
    allowed_actions: List[str] = Field(description="List of allowed human response types")


class ProcessEmailRequest(BaseModel):
    """Defines the input request schema"""
    email_input : EmailInput

class ProcessEmailHITLRequest(BaseModel):
    """Defines the input request schema"""
    email_input : Optional[EmailInput] = Field(
        default= None,
        description= "Email data (required for new workflow)."
    )
    thread_id : Optional[str] = Field(
        default= None,
        description= "Thread_id required for resuming the graph."
    )
    human_response : Optional[HumanResponse]  = Field(
        default= None,
        description= "Human response to resume from the interruption."
    )

class ProcessEmailHITLResponse(BaseModel):
    """Response schema for HITL email processing."""

    status: Literal["interrupted", "completed", "error"] = Field(
        description="Status of the workflow"
    )
    thread_id: str = Field(description="Thread ID for this workflow")
    interrupt: Optional[InterruptInfo] = Field(
        default=None,
        description="Interrupt details when status=interrupted"
    )
    result: Optional[ProcessEmailResponse] = Field(
        default=None,
        description="Final result when status=completed"
    )
    error: Optional[str] = Field(
        default=None,
        description="Error message when status=error"
    )

