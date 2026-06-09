from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Reads from .env automatically; empty defaults prevent ValidationError on
    # import when no .env file exists (e.g. in an IDE without Docker running).
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = ""
    redis_url: str = "redis://localhost:6379/0"
    anthropic_api_key: str = ""
    voyage_api_key: str = ""
    jwt_secret: str = ""
    jwt_algorithm: str = "HS256"
    access_token_ttl_minutes: int = 15
    environment: str = "development"

    # Ingestion worker settings
    brain_worker_concurrency: int = 4
    personal_worker_concurrency: int = 2

    # Job state machine constants
    stale_job_threshold_minutes: int = 15
    max_ingestion_retries: int = 3
    retry_backoff_base_seconds: int = 30


def validate_ai_keys(s: Settings) -> None:
    """Call at ingestion startup — fails fast if either AI key is missing."""
    missing = [k for k, v in [("ANTHROPIC_API_KEY", s.anthropic_api_key), ("VOYAGE_API_KEY", s.voyage_api_key)] if not v]
    if missing:
        raise RuntimeError(
            f"Required environment variables are not set: {', '.join(missing)}. "
            "Both keys are required — the system cannot ingest documents without them."
        )


settings = Settings()
