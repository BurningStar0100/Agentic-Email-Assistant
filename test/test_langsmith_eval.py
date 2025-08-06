from langsmith import Client
from email_assistant.eval.email_test_dataset import examples_triage
from email_assistant.agents import compiled_email_assistant
from typing import Dict
import os

def classification_matcher(outputs:Dict , reference_outputs:Dict) -> bool :
    "matches if the output classification matches the expected value"
    return outputs["classification_decision"].lower() == reference_outputs["classification"].lower()

def create_dataset_langsmith():
    "creates data online"
    client = Client()
    dataset_name = "Email triage evaluation"
    if not client.has_dataset(dataset_name=dataset_name):
        dataset = client.create_dataset(
            dataset_name=dataset_name,
            description="A dataset of emails and their triage decisions."
        )
        print(f"Dataset with name {dataset_name} created successfully!!")
        client.create_examples(dataset_id=dataset.id, examples = examples_triage)
        print("examples added successfully.")
    return dataset_name

def target_eval_function(inputs : Dict):
    "creates the target function to be eval by langsmith"
    print(inputs)
    response = compiled_email_assistant.nodes["triage_router"].invoke({'email_input':inputs["email_input"]})
    return {"classification_decision" : response.update["classification_response"]}

def langsmith_test_eval():
    "Eval router traige function using LangSmith"
    client = Client()
    dataset_name = create_dataset_langsmith()
    print(f"running eval against dataset: {dataset_name}")
    experiment_result = client.evaluate(
        target = target_eval_function,
        experiment_prefix= "runs eval for router function",
        evaluators= [classification_matcher],
        data= dataset_name,
        max_concurrency= 2,
        )
        # Run evaluation 
    # experiment_results = client.evaluate(
        
    #     # Run agent 
    #     target_eval_function,
    #     # Evaluator
    #     evaluators=[classification_matcher], # we can pass multiple evaluators
    #     # Dataset name   
    #     data=dataset_name,
    #     # Name of the experiment
    #     experiment_prefix="E-mail assistant workflow", 
    #     # Number of concurrent evaluations
    #     max_concurrency=10, 
    # )
if __name__ == "__main__":
    print("🚀 LangSmith Evaluation Demo")
    print("=" * 40)

    if os.getenv("LANGSMITH_API_KEY"):
        result = langsmith_test_eval()
        if result:
            print(f"View results at: https://smith.langchain.com/")
    else:
        print("⚠️ Set LANGSMITH_API_KEY environment variable to run LangSmith evaluation")
        print("This is optional – you can complete the tutorial without LangSmith")

