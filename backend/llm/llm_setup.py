from dotenv import load_dotenv
import os 
load_dotenv()
from langchain.chat_models import init_chat_model 

endpoint = os.getenv("API_ENDPOINT")
deployment_name = os.getenv("DEPLOYMENT_NAME")
api_key = os.getenv("API_KEY")

client = init_chat_model(
    model=f"azure_ai:{os.getenv("DEPLOYMENT_NAME")}",
    base_url=endpoint,
    api_key=api_key
)