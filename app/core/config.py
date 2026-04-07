from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Load from environment; prefix MYHELPER_."""

    model_config = SettingsConfigDict(
        env_prefix="MYHELPER_",
        env_file=".env",
        extra="ignore",
    )

    database_url: str = "sqlite:///./myhelper.db"
    gotify_url: str = "http://localhost:8080"
    gotify_token: str = ""
    scheduler_timezone: str = "UTC"
    scan_interval_seconds: int = 5
    misfire_grace_seconds: int = 60


def get_settings() -> Settings:
    return Settings()
