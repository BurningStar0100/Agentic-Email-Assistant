""" """

import pytest
from  email_assistant.agents import compiled_email_assistant
from email_assistant.utils import extract_tool_calls
from email_assistant.eval.email_test_dataset import email_inputs, expected_tool_calls
from langsmith import testing as t


@pytest.mark.langsmith
@pytest.mark.parametrize("email_input, expected_calls" , [(email_inputs[i], expected_tool_calls[i]) for i in range(2,4)])
def test_email_dataset_tool_calls(email_input, expected_calls):
    result = compiled_email_assistant.invoke({"email_input": email_input})
    # print("#############################")
    # print("result after graph:" , result)
    extracted_tool_calls = extract_tool_calls(result["messages"])
    print("#############################")
    print("Final tool calls done:", extracted_tool_calls)
    missing_calls = [call for call in expected_calls if call not in extracted_tool_calls]
    print("missing calls:", missing_calls)

    t.log_outputs({
        "missing calls" : missing_calls,
        "Final tool calls done": extracted_tool_calls,
        "response": result["messages"]
    }

    )
    assert len(missing_calls) == 0
