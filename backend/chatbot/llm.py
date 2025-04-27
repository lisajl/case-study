import os
from dotenv import load_dotenv
from langchain_deepseek import ChatDeepSeek

# Check if the DEEPSEEK_API_KEY and OPENAI_API_KEY environment variables exist and are not empty
# If not, locally set via export BLAH_API_KEY = the key
load_dotenv()

ds_api_key = os.getenv("DEEPSEEK_API_KEY")
openai_api_key = os.getenv("OPENAI_API_KEY")

# Print API key status for debugging
if ds_api_key:
    print("DeepSeek API key is set.")
else:
    print("DeepSeek API key is NOT set or is empty.")
    exit()

if openai_api_key:
    print("OpenAI API key is set.")
else:
    print("OpenAI API key is NOT set or is empty.")
    exit()

# Initialize the DeepSeek LLM with the appropriate parameters
llm = ChatDeepSeek(
    model="deepseek-chat",  # Specify the model you want to use
    temperature=0,  # Set the temperature for the responses (0 for deterministic)
    max_tokens=None,  # Set max tokens if necessary (None for no limit)
    timeout=None,  # Adjust timeout if needed
    max_retries=2,  # Set max retries in case of failure
    api_key=ds_api_key,  # Pass the DeepSeek API key
)
