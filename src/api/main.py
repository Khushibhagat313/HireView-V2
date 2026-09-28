from fastapi import FastAPI
from src.api.routes import resumes, search, candidates

app = FastAPI(title="HireView API")

@app.get("/health")
def health_check():
    return {"status": "ok"}

app.include_router(resumes.router)
app.include_router(search.router)
app.include_router(candidates.router)