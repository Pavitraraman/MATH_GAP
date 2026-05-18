from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "math-gap"
    app_env: str = "development"
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/math_gap"
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.5-flash"
    input_cost_per_1k_tokens_usd: float = 0.0
    output_cost_per_1k_tokens_usd: float = 0.0
    default_prompt_name: str = "adaptive_recommendation"
    default_prompt_version: str = "v1"
    llm_max_retries: int = 2
    llm_retry_base_delay_seconds: float = 0.5


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
