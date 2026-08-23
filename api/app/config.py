from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite+aiosqlite:///./dev.db"
    session_ttl_days: int = 30
    cookie_secure: bool = False  # True behind TLS in production


settings = Settings()
