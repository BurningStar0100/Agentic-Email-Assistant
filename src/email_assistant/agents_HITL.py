from langgraph.graph import StateGraph, START, END
from langchain.chat_models import init_chat_model
from langgraph.types import Command , interrupt
from typing import Literal , TypedDict, Annotated, List
from langchain_core.messages import HumanMessage, AIMessage ,AnyMessage, ToolMessage, SystemMessage
from email_assistant.schemas import State , RouterSchema
from email_assistant.utils import email_parser , format_email_markdown
from email_assistant.prompts import TRIAGE_SYSTEM_PROMPT, default_triage_instructions, default_background, TRIAGE_USER_PROMPT, Agent_system_prompt, DEFAULT_RESPONSE_PREFERENCES, DEFAULT_CAL_PREFERENCES
from dotenv import load_dotenv
from email_assistant.agent_tools import Tools
from IPython.display import Image , display
from langgraph.checkpoint.memory import MemorySaver


load_dotenv()

#initial the llm:
llm = init_chat_model(model= "gpt-4o", model_provider= "openai" , temperature = 0.0)

#structured output:
llm_router = llm.with_structured_output(RouterSchema)

#llm with tools
tool_names = {tool.name: tool for tool in Tools}
llm_with_tools = llm.bind_tools(Tools, tool_choice= "any") #we are forcing to call at least on tool

def triage_router(state: State)  -> Command[Literal["triage_interrupt_handler", 'response_agent', '__end__'] ] :
    """Analyze email content to classify it into ignore, notify and respond
        If it's notify then it interrupts and ask for human input"""
    print("state received at traigae router:",state)
    author, to, subject, email_thread = email_parser(state["email_input"])
    system_prompt = TRIAGE_SYSTEM_PROMPT.format(background = default_background, triage_instructions = default_triage_instructions)
    user_prompt = TRIAGE_USER_PROMPT.format( author = author , to = to , subject = subject ,email_thread = email_thread)

    result = llm_router.invoke([
        {"role":"system", "content": system_prompt},
        {"role": "user", "content": user_prompt}])
    print(f"Classification result:", result.classification.upper())

    if result.classification == 'respond':
        print("Routing to response agent...")
        go_to = "response_agent"
        update1= {'classification_response' : result.classification, 
                 'messages': [
                     {
                         'role' : 'user',
                         'content' : f"Respond to the email: \n\n {format_email_markdown(subject,author,to,email_thread)}"
                     }
                 ]}
    elif result.classification == 'ignore':
        print("Email has been ignored.")
        go_to = END
        update1= {'classification_response' : result.classification}
    elif result.classification == 'notify':
        print("Email has been marked for notification and sent for human feedback")
        go_to = 'triage_interrupt_handler'
        update1= {'classification_response' : result.classification}
    else:
        raise ValueError(f"Invalid classification: {result.classification}")
    
    return Command(goto= go_to, update= update1)

def triage_interrupt_handler(state : State) :
    """for notify emails, it asks user for the feedback and then either end the workflow or calls response agent"""
    author, to, subject, email_thread = email_parser(state["email_input"])
    email_markdown = format_email_markdown(subject,author,to,email_thread)
    request = {
        "action_request" :{
            'action' : f"the email assistant classification : {state['classification_response']}",
            'args' : {}
        },
        'config' : {
            'allow_ignore' :True,
            'allow_respond' : True,
            'allow_edit' : False,
            'allow_accept' : False,
        },
        'description': email_markdown
         
    }
    #calling the interrupt handler:
    response1 = interrupt([request])
    print("#######################################")
    print("response from the interrupt:",response1)
    response = response1[0]
    print('#'*40)
    print("used part of response:",response)

    messages = [{
        'role': 'user',
        'content': f"email to notify user about: {email_markdown}"
    }]

    if response['type'] == 'response' :
        print('#'*40)
        print("going to RESPOND because user said respond to the mail.")
        user_input = response['args']
        messages.append(
            {
                'role' : 'user',
                'content' : f"User want to reply to the email. Use the feedback to respond : {user_input}"
            }
        )
        goto = 'response_agent'
    elif response['type'] == 'ignore':
        print('#'*40)
        print("going to END because user said ignore the mail.")
        goto = END

    else :
        raise ValueError(f"Invalid response type: {response}")
    update = {
        'messages' : messages
    }
    return Command(goto = goto , update = update)



def llm_call(state : State) :
    
    """decides which tool to call or if the processing is done"""
    # print("State received for routing ", state["messages"])
    system_prompt = Agent_system_prompt.format(
        background = default_background ,
        response_preferences = DEFAULT_RESPONSE_PREFERENCES,
        calendar_preferences = DEFAULT_CAL_PREFERENCES,
    )
    response = llm_with_tools.invoke([
        {
            "role" : "system" ,
            "content" : system_prompt
        }, ]
        + state["messages"]
    )
    # print("response:", response)
    return {"messages" : [response]}

def tool_handler(state: State) :
    print("tool handler initiated.")
    last_message = state["messages"][-1]
    # print("priting the last message:", last_message)
    results = []
    for tool_calls in last_message.tool_calls :
        tool = tool_names[tool_calls["name"]]
        observation = tool.invoke(tool_calls["args"])
        results.append({"role": "tool", "content" : observation, "tool_call_id": tool_calls["id"]})
    return {"messages": results}


def should_continue(state: State) -> Literal["tool_handler", "__end__"]:
    print("should continue started")
    last_message = state["messages"][-1]
    if last_message.tool_calls:
        for tool_call in last_message.tool_calls:
            if tool_call["name"]== 'Done' :
                print("the process has beenn completed.")
                return END
        print("going to tool handler")
        return "tool_handler"
    return END



#response_agent subgraph:
response_agent = StateGraph(State)
response_agent.add_node('llm_call',llm_call)
response_agent.add_node('tool_handler', tool_handler)

response_agent.add_edge(START, "llm_call")
response_agent.add_conditional_edges('llm_call',should_continue)
response_agent.add_edge('tool_handler', 'llm_call')

checkpointer = MemorySaver()
compiled_response_agent = response_agent.compile()

# save1 = compiled_graph.get_graph().draw_mermaid_png()
# with open("graph.png" , "wb") as f:
#     f.write(save1)


# creating the workflow of our main graph:
email_assistant = StateGraph(State)

email_assistant.add_node('triage_router', triage_router)
email_assistant.add_node('triage_interrupt_handler',triage_interrupt_handler)
email_assistant.add_node('response_agent', compiled_response_agent )

email_assistant.add_edge(START, 'triage_router')

compiled_email_assistant_hitl = email_assistant.compile(checkpointer= checkpointer)

# save1 = compiled_email_assistant_hitl.get_graph(xray=True).draw_mermaid_png()
# with open("compiled_email_asst.png" , "wb") as f:
#     f.write(save1)

def process_email(email_data : dict) :
    result = compiled_email_assistant_hitl.invoke({ 'email_input': email_data})
    response_text = "no response generated"
    # print(f"result by graph:" ,result)

    if result.get("messages"):
        # Look for the actual email content in tool calls (write_email tool)
        for message in result["messages"]:
            # print('##################################################')
            # print("message:",message)
            # Check if this is an assistant message with tool calls
            if message.additional_kwargs :
                for tool_call in message.additional_kwargs['tool_calls']:
                    # print('###############################################')
                    # print("tool_call:" , tool_call)
                    # print(tool_call["function"]["name"])
                    if tool_call["function"]["name"] == 'write_email':
                        # Extract the email content from the tool arguments
                        args = tool_call['function']['arguments']
                        #email_content = args.get('content', '')
                        if args:
                            response_text = args
                            break
            # if response_text != "No response generated":
            #     break
            # # Fallback: look for assistant messages with actual content
            # elif (hasattr(message, 'role') and message.role == "assistant" and 
            #     hasattr(message, 'content') and message.content.strip()):
            #     response_text = message.content
            #     break
    answer = {
    "classification": result.get("classification_decision", "unknown"),
    "response": response_text,
    "reasoning": f"Email classified as: {result.get('classification_decision', 'unknown')}"
}
    print(f"the final answer by processing the email is: {answer}")
    
    return {
    "classification": result.get("classification_response", "unknown"),
    "response": response_text,
    "reasoning": f"Email classified as: {result.get('classification_response', 'unknown')}"
}




if __name__ == "__main__":
    process_email({"email_input" : {
        "author": "Alice <alice@company.com>",
        "to": "John <john@company.com>",
        "subject": "Question about API",
        "email_thread": "Hi! I have a question about the API documentation. Could we schedule a quick call this week?"
    }})




