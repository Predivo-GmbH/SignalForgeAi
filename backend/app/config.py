from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://signalforge:signalforge@localhost:5432/signalforge"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Celery
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # JWT
    jwt_secret: str = "dev-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiry_minutes: int = 30
    jwt_refresh_expiry_days: int = 7

    # App
    app_name: str = "SignalForge"
    debug: bool = True
    cors_origins: list[str] = ["http://localhost:5173"]

    model_config = {"env_prefix": "SF_", "env_file": ".env"}


settings = Settings()
