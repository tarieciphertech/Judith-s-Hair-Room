from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # CORS_ORIGINS is intentionally supplied as a comma-separated environment
    # variable (rather than JSON) so CI, Render, and local .env files can use
    # the same simple format. Disable pydantic-settings' JSON decoding so the
    # validator below receives the raw string first.
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        extra='ignore',
        enable_decoding=False,
    )

    database_url: str
    secret_key: str
    cors_origins: list[str] = []
    supabase_url: str | None = None
    supabase_anon_key: str | None = None

    @field_validator('cors_origins', mode='before')
    @classmethod
    def parse_origins(cls, value):
        if isinstance(value, str):
            return [item.strip() for item in value.split(',') if item.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
