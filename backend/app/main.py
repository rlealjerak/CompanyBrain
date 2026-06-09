from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.database import check_postgres, check_redis

app = FastAPI(
    title="Company Brain API",
    version="0.1.0",
    description="Organizational knowledge base with semantic search and RAG chat.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check():
    """Liveness + readiness check.

    Returns 200 only when both PostgreSQL and Redis are reachable.
    Returns 503 if either dependency is down so load balancers and
    compose health checks treat the instance as unhealthy.
    """
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
