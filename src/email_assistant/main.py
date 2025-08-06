from fastapi import FastAPI , HTTPException
from typing import Dict
from email_assistant.schemas import ProcessEmailResponse , ProcessEmailRequest
from email_assistant.agents import process_email
from email_assistant.schemas import ProcessEmailHITLRequest, ProcessEmailHITLResponse

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