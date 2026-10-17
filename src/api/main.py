import hmac
import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from groq import APIError
from src.agents.llm_client import AIServiceError
from src.api.routes import resumes, search, candidates, chat  # <--- 1. Import chat
from src.config import CORS_ALLOWED_ORIGINS
from src.ingestion.guards import InvalidResumeError

# Temporary shared password for the public deployment until real login exists. Unset = no check (local dev).
ACCESS_CODE = os.getenv("ACCESS_CODE")
OPEN_PATHS = {"/health", "/docs", "/openapi.json"}

app = FastAPI(title="HireView API")


class StripApiPrefix:
    """On Vercel the frontend calls /api/search and the request arrives with that path; route it as /search."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and (scope["path"] == "/api" or scope["path"].startswith("/api/")):
            path = scope["path"][len("/api"):] or "/"
            scope = {**scope, "path": path, "raw_path": path.encode()}
        await self.app(scope, receive, send)


@app.middleware("http")
async def require_access_code(request: Request, call_next):
    if ACCESS_CODE and request.method != "OPTIONS" and request.url.path not in OPEN_PATHS:
        if not hmac.compare_digest(request.headers.get("x-access-code", ""), ACCESS_CODE):
            return JSONResponse(status_code=401, content={"detail": "Enter the access code to use HireView."})
    return await call_next(request)


# Middleware added last runs first: CORS -> strip /api -> access code -> routes.
app.add_middleware(StripApiPrefix)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOWED_ORIGINS,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type", "X-Access-Code"],
)


# Business code raises plain Python exceptions; these handlers turn them into HTTP status codes
# so that FastAPI stays inside src/api/.
@app.exception_handler(InvalidResumeError)
def invalid_resume_handler(request: Request, exc: InvalidResumeError):
    return JSONResponse(status_code=422, content={"detail": str(exc)})


@app.exception_handler(APIError)
@app.exception_handler(AIServiceError)
def ai_unavailable_handler(request: Request, exc: Exception):
    return JSONResponse(status_code=503, content={"detail": "The AI service is unavailable. Please try again."})


@app.get("/health")
def health_check():
    return {"status": "ok", "access_code_required": bool(ACCESS_CODE)}

app.include_router(resumes.router)
app.include_router(search.router)
app.include_router(candidates.router)
app.include_router(chat.router)        # <--- 2. Plug chat into the main app!
