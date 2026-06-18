from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.auth import router as auth_router
from app.api.ingest import router as ingest_router
from app.api.personal import router as personal_router
from app.api.query import router as query_router
from app.core.database import check_postgres, check_redis

app = FastAPI(
    title="Company Brain API",
    version="0.2.0",
    description="Organizational knowledge base with semantic search and RAG chat.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────── standardized error responses (4.7)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": f"http_{exc.status_code}", "message": exc.detail},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"error": "validation_error", "message": str(exc.errors())},
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"error": "internal_error", "message": "An unexpected error occurred"},
    )


# ──────────────────────────────────────────────────────────────── routers

app.include_router(auth_router)
app.include_router(query_router)
app.include_router(ingest_router)
app.include_router(personal_router)


# ──────────────────────────────────────────────────────────────── health

@app.get("/health")
def health_check():
    postgres_ok = check_postgres()
    redis_ok = check_redis()
    healthy = postgres_ok and redis_ok
    return JSONResponse(
        status_code=200 if healthy else 503,
        content={
            "status": "ok" if healthy else "degraded",
            "postgres": postgres_ok,
            "redis": redis_ok,
        },
    )
