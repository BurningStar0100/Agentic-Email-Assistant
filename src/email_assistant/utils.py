from .schemas import State
from typing import Tuple, List, Any
from langchain_core.messages.utils import convert_to_openai_messages

def email_parser(email : dict) -> Tuple[str, str, str, str]:
    """parsers given email json into required fields"""
    return (
        email.get("author", "") , email.get("to", "") , email.get("subject", "") , email.get("email_thread", "")
    )
def format_email_markdown(subject: str, author: str, to: str, email_thread: str) -> str:
    """Format email details into a markdown string for display.
    
    Args:
        subject: Email subject
        author: Email sender
        to: Email recipient
        email_thread: Email content
        
    Returns:
        Formatted markdown string
    """
    return f"""
**subject** : {subject}
**from** : {author}
**to** : {to}

{email_thread}

---
"""
def extract_tool_calls(messages):
    """extract the kind of tool calls made during the email processing"""
    extracted_calls = []
    for message in messages:
        if message.additional_kwargs :
            for tool_call in message.additional_kwargs['tool_calls']:
                # print('############################################')
                # print("Tool_call happened :" ,tool_call)
                # print("name of tool call:", tool_call["function"]["name"])
                extracted_calls.append(tool_call["function"]["name"])
                # print("extracted tool call becomes:",extracted_calls)
    return extracted_calls

def messages_formatter(messages : List[Any]) :
    """Takes role, content and tool calls made with args and format them properly"""
    actual_messages = convert_to_openai_messages(messages)
    formatted_messages = []
    for message in actual_messages:
        role = message['role']
        content = message['content']
    #     print("#"*40)
    #     print("printing the received message ")
    #     print(message)
    #     print(message['tool_calls'])
    #     print("checking if there are any toolcalls....")
    #     print(list(message.keys()))
        if 'tool_calls' in list(message.keys()):
            # print("tools calls are there")
            for tc in message['tool_calls']:
                # print("getting to the first tool call", tc)
                name = tc['function']['name']
                args = tc['function']['arguments']
                content += 'tool call made to: ' + name + ' with arguments ' + args + " ."
                # print("getting updated content:-",content)
        formatted_messages.append(f"{role.upper()} : {content}")
    # print("formatted message:",formatted_messages)
    return "\n\n".join(formatted_messages)