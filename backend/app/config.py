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

    # Encryption
    encryption_key: str = ""  # Fernet key for broker credential encryption

    # AI
    anthropic_api_key: str = ""
    anthropic_admin_api_key: str = ""  # sk-ant-admin... for Usage & Cost API

    # AI feature flags
    ai_signal_quality_enabled: bool = True
    ai_risk_tuning_enabled: bool = True
    ai_feedback_loop_enabled: bool = True
    ai_multi_timeframe_enabled: bool = True
    ai_pattern_analysis_enabled: bool = True

    # AI cost control
    ai_signal_quality_cache_ttl: int = 300
    ai_risk_tuning_interval_hours: int = 24
    ai_max_daily_api_calls: int = 500
    ai_prepaid_credit_usd: float = 0.0

    # Admin
    admin_user_id: str = ""  # UUID of admin user; empty = no admin restriction

    # Email alerts
    resend_api_key: str = ""
    resend_domain: str = "signalforge.dev"

    # Exchange
    default_exchange: str = "binance"

    # Sentry
    sentry_dsn: str = ""

    # App
    app_name: str = "SignalForge"
    debug: bool = True
    cors_origins: list[str] = ["http://localhost:5173"]

    model_config = {"env_prefix": "SF_", "env_file": ".env"}


settings = Settings()
