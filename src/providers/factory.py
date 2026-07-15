"""Provider 配置加载与实例工厂。"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .base import ProviderError, VLMProvider
from .openai_compatible import OpenAICompatibleProvider


ROOT = Path(__file__).resolve().parents[2]


def _find_config() -> Path | None:
    for path in (ROOT / "configs" / "providers.json", ROOT / "configs" / "providers.example.json"):
        if path.exists():
            return path
    return None


def load_config() -> dict[str, Any]:
    path = _find_config()
    return json.loads(path.read_text(encoding="utf-8")) if path else {"active_provider": "qwen", "providers": {}}


def get_provider(
    name: str | None = None,
    config: dict[str, Any] | None = None,
    api_key: str | None = None,
    overrides: dict[str, Any] | None = None,
) -> VLMProvider:
    config = config or load_config()
    name = name or config.get("active_provider")
    providers = config.get("providers", {})
    if name not in providers:
        raise ProviderError(f"未找到 provider: {name}")
    provider_config = {**providers[name], **(overrides or {})}
    if provider_config.get("type", "openai_compatible") != "openai_compatible":
        raise ProviderError(f"不支持的 provider 类型: {provider_config.get('type')}")
    provider = OpenAICompatibleProvider(provider_config)
    if api_key:
        provider.set_api_key(api_key)
    return provider


def list_providers(config: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    config = config or load_config()
    result = []
    for name, cfg in config.get("providers", {}).items():
        key_env = cfg.get("api_key_env", "")
        result.append({
            "name": name,
            "label": cfg.get("label", name),
            "type": cfg.get("type", "openai_compatible"),
            "base_url": cfg.get("base_url", ""),
            "model": cfg.get("model", ""),
            "description": cfg.get("description", ""),
            "api_key_env": key_env,
            "has_env_key": bool(os.getenv(key_env)) if key_env else bool(cfg.get("api_key_optional")),
            "api_key_optional": bool(cfg.get("api_key_optional")),
        })
    return result
