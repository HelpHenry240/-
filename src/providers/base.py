"""VLM Provider 抽象基类。

所有 provider 必须实现 inspect 方法，
接收图片路径列表和 prompt，返回结构化 dict。
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


class ProviderError(Exception):
    """Provider 调用异常。"""


@dataclass
class ProviderResult:
    """inspect 方法的返回结构。"""

    success: bool
    data: dict[str, Any] = field(default_factory=dict)
    raw_text: str = ""
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "data": self.data,
            "raw_text": self.raw_text,
            "error": self.error,
        }


class VLMProvider(abc.ABC):
    """视觉语言模型 provider 抽象基类。"""

    name: str = "base"

    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}

    @abc.abstractmethod
    def inspect(self, images: list[Path], prompt: str, options: dict | None = None) -> ProviderResult:
        """对给定图片执行巡检，返回结构化结果。

        Args:
            images: 图片路径列表（至少一张）。
            prompt: 巡检 prompt 文本。
            options: 可选参数（temperature 等）。

        Returns:
            ProviderResult，其中 data 为解析后的结构化 dict。
        """
        ...

    def is_available(self) -> bool:
        """检查此 provider 是否可用（如是否配置了 API Key）。"""
        return True

    def info(self) -> dict[str, Any]:
        """返回 provider 元信息。"""
        return {
            "name": self.name,
            "type": self.config.get("type", ""),
            "model": self.config.get("model", ""),
            "description": self.config.get("description", ""),
        }
