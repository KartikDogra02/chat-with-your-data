from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    openai_api_key: str = ""
    openai_model: str = "gpt-5.4-mini"
    # Comma-separated list of origins allowed to call the API. Needed once the
    # frontend is deployed separately from the backend (different origin).
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    # BaseSettings supplies this field from the environment at runtime.
    return Settings()  # pyright: ignore[reportCallIssue]
