import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from groq import Groq
from sentence_transformers import SentenceTransformer

load_dotenv()

# 1. Postgres
engine = create_engine(os.environ["DATABASE_URL"])
with engine.connect() as conn:
    result = conn.execute(text("SELECT version();"))
    print("POSTGRES:", result.scalar())

# 2. Groq
client = Groq(api_key=os.environ["GROQ_API_KEY"])
response = client.chat.completions.create(
    model=os.environ["GROQ_MODEL"],
    messages=[{"role": "user", "content": "Say hello in exactly 3 words."}],
)
print("GROQ:", response.choices[0].message.content)

# 3. Embedding model
model = SentenceTransformer("BAAI/bge-small-en-v1.5")
vector = model.encode("test sentence")
print("EMBEDDING VECTOR LENGTH:", len(vector))