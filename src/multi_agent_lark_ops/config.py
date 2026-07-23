"""Runtime configuration loaded from environment variables."""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv() -> None:
        return None


@dataclass(frozen=True)
class Settings:
    model_api_key: str | None
    model_base_url: str | None
    model_name: str
    deepseek_api_key: str | None
    deepseek_model: str | None
    semantic_scholar_api_key: str | None
    openalex_api_key: str | None
    lark_cli_path: str
    lark_cli_profile: str | None

    @property
    def has_model_credentials(self) -> bool:
        return bool(self.model_api_key)


def _resolve_cli_path(configured_path: str) -> str:
    return shutil.which(configured_path) or configured_path


def _first_env(*names: str) -> str | None:
    for name in names:
        value = os.getenv(name)
        if value:
            return value
    return None


def load_settings() -> Settings:
    load_dotenv()
    deepseek_api_key = _first_env("DEEPSEEK_API_KEY", "GPT_API_KEY", "OPENAI_API_KEY", "AI_API_KEY")
    return Settings(
        model_api_key=deepseek_api_key,
        model_base_url=_first_env("OPENAI_PROXY_BASE_URL", "OPENAI_BASE_URL", "AI_BASE_URL"),
        model_name=os.getenv("DEEPSEEK_MODEL") or os.getenv("GPT_MODEL") or "deepseek-v4-flash",
        deepseek_api_key=deepseek_api_key,
        deepseek_model=os.getenv("DEEPSEEK_MODEL") or "deepseek-v4-flash",
        semantic_scholar_api_key=os.getenv("SEMANTIC_SCHOLAR_API_KEY") or None,
        openalex_api_key=os.getenv("OPENALEX_API_KEY") or None,
        lark_cli_path=_resolve_cli_path(os.getenv("LARK_CLI_PATH", "lark-cli")),
        lark_cli_profile=os.getenv("LARK_CLI_PROFILE") or None,
    )
