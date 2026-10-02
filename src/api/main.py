from fastapi import FastAPI
from src.api.routes import resumes, search, candidates, chat  # <--- 1. Import chat

app = FastAPI(title="HireView API")

@app.get("/health")
def health_check():
    return {"status": "ok"}

app.include_router(resumes.router)
app.include_router(search.router)
app.include_router(candidates.router)
app.include_router(chat.router)        # <--- 2. Plug chat into the main app!

