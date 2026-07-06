"""Provider 工厂：根据配置创建 provider 实例。"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .base import VLMProvider, ProviderError
from .mock_provider import MockProvider
from .qwen_provider import QwenProvider


def _find_config() -> Path | None:
    """查找 provider 配置文件。"""
    root = Path(__file__).resolve().parents[2]
    candidates = [
        root / "configs" / "providers.json",
        root / "configs" / "providers.example.json",
    ]
    for p in candidates:
        if p.exists():
            return p
    return None


def load_config() -> dict[str, Any]:
    """加载 provider 配置。"""
    path = _find_config()
    if path is None:
        return {"active_provider": "mock", "providers": {}}
    return json.loads(path.read_text(encoding="utf-8"))


def get_provider(
    name: str | None = None,
    config: dict[str, Any] | None = None,
    api_key: str | None = None,
) -> VLMProvider:
    """根据名称创建 provider 实例。

    Args:
        name: provider 名称。为 None 时使用配置中的 active_provider。
        config: 自定义配置。为 None 时从 configs/providers.json 加载。
        api_key: 可选的 API Key，运行时传入，不从环境变量读取。

    Returns:
        VLMProvider 实例。
    """
    if config is None:
        config = load_config()

    providers = config.get("providers", {})
    if name is None:
        name = config.get("active_provider", "mock")

    if name not in providers:
        raise ProviderError(f"未找到 provider: {name}，可用: {list(providers.keys())}")

    provider_config = providers[name]
    provider_type = provider_config.get("type", "mock")

    if provider_type == "mock":
        return MockProvider(provider_config)
    elif provider_type in ("openai_compatible", "qwen", "openai", "ollama"):
        provider = QwenProvider(provider_config)
        if api_key:
            provider.set_api_key(api_key)
        return provider
    else:
        raise ProviderError(f"不支持的 provider 类型: {provider_type}")


def list_providers(config: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """列出所有可用 provider 的信息。"""
    if config is None:
        config = load_config()
    providers = config.get("providers", {})
    result = []
    for name, cfg in providers.items():
        result.append({
            "name": name,
            "type": cfg.get("type", ""),
            "model": cfg.get("model", ""),
            "description": cfg.get("description", ""),
            "api_key_env": cfg.get("api_key_env", ""),
            "has_env_key": bool(os.getenv(cfg.get("api_key_env", ""), "")) if cfg.get("api_key_env") else True,
        })
    return result
