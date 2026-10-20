import os
from dotenv import load_dotenv
from groq import Groq
from src.config import LLM_MAX_TOKENS

load_dotenv()

client = Groq(api_key=os.environ["GROQ_API_KEY"])


class AIServiceError(Exception):
    """The LLM returned unusable output even after a retry."""


def call_llm(prompt: str, json_mode: bool = False) -> str:
    kwargs = {"response_format": {"type": "json_object"}} if json_mode else {}
    response = client.chat.completions.create(
        model=os.environ["GROQ_MODEL"],
        messages=[{"role": "user", "content": prompt}],
        max_tokens=LLM_MAX_TOKENS,
        **kwargs,
    )
    content = response.choices[0].message.content
    # A reasoning model can spend its whole token budget thinking and return no answer at all.
    if not content or not content.strip():
        raise AIServiceError("The model returned an empty reply")
    return content