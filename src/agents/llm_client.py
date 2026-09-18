import os
from dotenv import load_dotenv
from groq import Groq
from src.config import LLM_MAX_TOKENS

load_dotenv()

client = Groq(api_key=os.environ["GROQ_API_KEY"])

def call_llm(prompt: str, json_mode: bool = False) -> str:
    kwargs = {"response_format": {"type": "json_object"}} if json_mode else {}
    response = client.chat.completions.create(
        model=os.environ["GROQ_MODEL"],
        messages=[{"role": "user", "content": prompt}],
        max_tokens=LLM_MAX_TOKENS,
        **kwargs,
    )
    return response.choices[0].message.content