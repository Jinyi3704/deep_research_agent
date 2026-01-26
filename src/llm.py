import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

class LLMClient:
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        base_url = os.getenv("OPENAI_BASE_URL")
        
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in .env file")
        
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url if base_url else None
        )
        self.model = "gpt-4o-mini"
    
    def chat(self, messages, model=None):
        try:
            response = self.client.chat.completions.create(
                model=model or self.model,
                messages=messages
            )
            return response.choices[0].message.content
        except Exception as e:
            raise Exception(f"LLM API error: {e}")
