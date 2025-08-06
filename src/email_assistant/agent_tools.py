"""Simple tools for the email assistant agent."""

from langchain_core.tools import tool
from datetime import datetime
from pydantic import BaseModel

@tool
def write_email(to:str, subject:str, body: str) -> str :
    """Write an email and sends it"""
    return f"Email sent to {to} with subject {subject}"

@tool
def check_calendar_availability(
    attendees: list[str] ,
    preferred_day : datetime , 
    duration_minutes : int 
) -> str:
    """check availability of all attendees"""
    return f"All attendees available on date : {preferred_day.strftime('%A , %B %d, %Y')}"

@tool
def schedule_meeting(
    attendees: list[str] ,
    subject : str,
    preferred_day : datetime , 
    start_time : int,
    duration_minutes : int 
) -> str :
    """Schedule meeting of all attendees given the available timeslot"""
    return f"Meeting have been scheduled for all attendees: {",".join(attendees)} at {preferred_day.strftime('%A, %B %d,%Y')}"

@tool
def Done(BaseModel):
    """Mark that the email process is complete"""
    done : bool = True

Tools = [check_calendar_availability, schedule_meeting, write_email, Done]
