import os
from src.auto_competion import AutoCompletionAgent
from dotenv import load_dotenv
load_dotenv()

# Testing the auto-completion agent
if __name__ == "__main__":
    prefix = "def add_numbers(a, b): \n return a"
    suffix = "\n"
    agent = AutoCompletionAgent(prefix, suffix, completion_length=20, model="gpt-4.1-nano", api_key=os.getenv("OPENAI_API_KEY"))
    
    try:
        completion = agent.generate_completion(prefix, suffix)
        print(f"Generated completion: {completion}")
    except Exception as e:
        print(f"Failed to generate completion: {e}")