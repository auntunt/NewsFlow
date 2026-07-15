"""NewsFlow — Phase 1: Data Models (config.py)

Application configuration loaded from .env + config YAML.
"""
from __future__ import annotations

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AIConfig(BaseModel):
    """LLM configuration (litellm model strings)."""

    model: str = "deepseek/deepseek-chat"
    score_model: str = "deepseek/deepseek-chat"
    generate_model: str = "deepseek/deepseek-chat"
    max_tokens: int = 4096
    temperature: float = 0.3
    # provider_chain: list[str] = []  # future: fallback chain


class Settings(BaseSettings):
    """Top-level settings loaded from environment variables / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="NEWSFLOW_",
        extra="ignore",
    )

    # AI
    model: str = "deepseek/deepseek-chat"
    score_model: str = "deepseek/deepseek-chat"
    generate_model: str = "deepseek/deepseek-chat"

    # Storage
    data_dir: str = "./data"

    # API keys passed through to litellm via env (no prefix needed)


def get_settings() -> Settings:
    return Settings()
