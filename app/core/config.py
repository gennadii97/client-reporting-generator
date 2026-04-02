from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # App
    app_name: str = "Client Reporting Generator"
    debug: bool = False

    # Database
    database_url: str = "postgresql+asyncpg://user:pass@localhost:5432/reports_db"

    # Redis / Celery
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"

    # Reports
    reports_output_dir: str = "/tmp/reports"

    sentry_dsn: str = ""


settings = Settings()