from functools import lru_cache
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    llm_provider: Literal["openai", "anthropic"] = "openai"
    llm_model: str = "gpt-4o-mini"
    app_env: str = "development"
    log_level: str = "DEBUG"

    @model_validator(mode="after")
    def _require_active_provider_key(self):
        if not getattr(self, f"{self.llm_provider}_api_key"):
            raise ValueError(
                f"{self.llm_provider.upper()}_API_KEY is required "
                f"when LLM_PROVIDER={self.llm_provider}"
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
