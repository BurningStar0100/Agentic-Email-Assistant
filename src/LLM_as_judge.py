"""This module implements LLM as a judge for our Email Assistanct pipeline.
    It uses CriteriaGrade as the eval metric.
"""

from email_assistant.prompts import RESPONSE_CRITERIA_SYSTEM_PROMPT
from langchain.chat_models import init_chat_model
from pydantic import BaseModel, Field
from email_assistant.eval.email_test_dataset import email_inputs, response_criteria_list
from email_assistant.agents import compiled_email_assistant
from email_assistant.utils import messages_formatter

class EVAL_SCHEMA(BaseModel):
    """Score the response against specific criteria"""
    justification : str = Field(description="the justification for grade. also provide example from the response")
    grade : bool = Field(description="Mark true if response satisfy all bullet point criteria, else mark false.")

criteria_eval_llm = init_chat_model(model_provider= "openai",model="gpt-4o")
criteria_eval_structured_llm = criteria_eval_llm.with_structured_output(EVAL_SCHEMA)

response = compiled_email_assistant.invoke({'email_input' : email_inputs[0]})
messages = response['messages']
all_msg_str = messages_formatter(messages)
response_criteria = response_criteria_list[0]
def run_llm_as_judge():
    """Using structured LLM grading """

    eval_results = criteria_eval_structured_llm.invoke(
        [{"role": "system", "content": RESPONSE_CRITERIA_SYSTEM_PROMPT},
         {'role': 'user', 'content': f"""Response Criteria: {response_criteria} \n 
          assistant message: {all_msg_str} \n 
          evaluate whether assistant response meet the response criteria and provide justification for your evaluation."""}]
    )

    print(f"GRADE: {'PASS' if eval_results.grade else 'FAIL'}")
    print(f"Justification: {eval_results.justification}")

    return eval_results

if __name__ == "__main__" :
    run_llm_as_judge()