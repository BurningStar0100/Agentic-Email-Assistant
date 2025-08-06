from fastapi import FastAPI , HTTPException
from typing import Dict
from email_assistant.schemas import ProcessEmailResponse , ProcessEmailRequest
from email_assistant.agents import process_email
from email_assistant.schemas import ProcessEmailHITLRequest, ProcessEmailHITLResponse, InterruptInfo
import uuid
from email_assistant.agents_HITL import compiled_email_assistant_hitl
from email_assistant.utils import _get_allowed_actions , _extract_final_results
from langgraph.types import Command

app = FastAPI(
    title= "Email Assistant App",
    description= "This services connects a complex email agent build on langgraph to FastAPI",
    version= "0.1.0"
)



@app.get("/")
async def root() -> Dict[str,str] :
    """Basic health checkpoint"""
    return {"message": "This root endpoint is working fine."}

@app.post("/process-email", response_model= ProcessEmailResponse)
async def process_email_endpoint(request :ProcessEmailRequest ) -> ProcessEmailResponse:
    """
    Process an email through the assistant agent.

    This endpoint takes an email and runs it through the complete workflow:
    1. Triage - determines if the email should be ignored, noted, or responded to
    2. Response - if needed, generates an appropriate response

    Args:
        request: ProcessEmailRequest containing the email data

    Returns:
        ProcessEmailResponse with classification and response
    """
    try : 
        email_dict = {
            'author': request.email_input.author,
            'to':request.email_input.to,
            'subject': request.email_input.subject,
            'email_thread': request.email_input.email_thread
        }
        print("created email_dict fron input:",email_dict)

        result = process_email(email_dict)

        print("sending response: {result}")
        return ProcessEmailResponse(
            classification = result["classification"],
            response = result["response"],
            reasoning = result["reasoning"]
        )
    except Exception as e:
        raise HTTPException(
            status_code = 500,
            detail = f"Error processing email: {str(e)}" 

        )
    
@app.post('/process-email-hitl' , response_model= ProcessEmailHITLResponse)
async def process_email_hitl_endpoint(request : ProcessEmailHITLRequest) :
    """
    Process an email through the HITL (Human-in-the-Loop) workflow.
    
    This endpoint supports both starting new HITL workflows and resuming 
    interrupted ones:
    
    **New Workflow:**
    - Provide `email` data
    - System generates thread_id and processes until interrupt
    
    **Resume Workflow:**
    - Provide `thread_id` and `human_response`
    - System resumes from interrupt point
    
    Args:
        request: HITL request with email, thread_id, and/or human_response
        
    Returns:
        HITL response with status, thread_id, and interrupt/result data
    """
    try:    
        #determine if the incoming request is a new workflow or resume request
        is_resume = request.thread_id is not None and request.thread_id is not None
        is_new = request.email_input is not None and request.thread_id is None

        if not is_resume and not is_new:
            raise HTTPException(
                status_code= '400',
                detail= "Either provide 'email_input' for new request or 'thread_id'+ 'human_response' for resume" 
            )
        thread_id = request.thread_id if is_resume else str(uuid.uuid4())
        config = {'configurable' : {'thread_id': thread_id}}

        if is_new:
            #Start new HITL worflow
            email_dict = {
                'author': request.email_input.author,
                'to':request.email_input.to,
                'subject': request.email_input.subject,
                'email_thread': request.email_input.email_thread
            }
            
            for chunk in compiled_email_assistant_hitl.stream( #chunk is state after every node
                {'email_input': email_dict},
                config= config,  ):
                if '__interrupt__' in chunk:
                    print(chunk['__interrupt__'])
                    interrupt_data = chunk['__interrupt__'][0].value[0]
                return ProcessEmailHITLResponse(
                    status= 'interrupted',
                    thread_id= thread_id,
                    interrupt=InterruptInfo(
                        action= interrupt_data['action_request']['action'],
                        args= interrupt_data['action_request']['args'],
                        description=interrupt_data['description'],
                        allowed_actions= _get_allowed_actions(interrupt_data['config'])
                    )
                )
        else:
            #resume from interrupt
            try:
                state = compiled_email_assistant_hitl.get_state(config=config)
                print('#'*40)
                print("Printing state.values :", state.values)
                if not state or not state.values :
                    raise HTTPException(
                        status_code= 400,
                        detail= f"Thread id :{thread_id} either invalid "
                    )
                human_response = request.human_response
                resume_command = Command(resume=[
                    {
                        'type' : human_response.type,
                        'args' : human_response.args or {}
                    }
                ])
                final_run_results = compiled_email_assistant_hitl.invoke(resume_command, config=config,)
                print('#'*40)
                print('Printing final_run_results :', final_run_results.values)
                result = _extract_final_results(final_run_results.values)

                return ProcessEmailHITLResponse(
                    status='completed',
                    thread_id=thread_id,
                    result=result,
                )
            except Exception as e:
                if isinstance(e, HTTPException):
                    raise
                raise HTTPException(
                    status_code=400, detail=f"Failed to resume thread: {str(e)}"
                )
        raise HTTPException(
            status_code=500, detail="Unexpected workflow state."
        )
         
    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        
        raise HTTPException(
            status_code=500,
            detail=f"Error processing HITL email: {str(e)}"
        )
  
    
@app.get("/health")
def health() -> Dict[str,str]:
    return {"status": "running", "health" : "OK"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "email_assistant.main:app",
        host= "127.0.0.1" ,
        port=8000,
        reload=True,
    )