"""Qwen-VL Provider：通过 DashScope OpenAI 兼容接口调用通义千问视觉模型。

DashScope 兼容接口文档：
https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions

使用标准 OpenAI chat/completions 格式，
content 为 [{type: "text"}, {type: "image_url", image_url: {url: data_url}}]。
"""

from __future__ import annotations

import base64
import json
import mimetypes
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from .base import VLMProvider, ProviderError, ProviderResult


def _image_to_data_url(path: Path) -> str:
    """将图片文件转为 base64 data URL。"""
    mime = mimetypes.guess_type(path.name)[0] or "image/jpeg"
    data = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{data}"


def _extract_text(response: dict) -> str:
    """从 chat/completions 响应中提取文本。"""
    choices = response.get("choices", [])
    if not choices:
        return ""
    message = choices[0].get("message", {})
    content = message.get("content", "")
    # 有些模型返回 list 格式
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(item.get("text", ""))
            elif isinstance(item, str):
                parts.append(item)
        return "\n".join(parts)
    return str(content)


def _parse_json(text: str) -> dict[str, Any] | None:
    """尝试从模型输出文本中提取 JSON。

    模型可能返回纯 JSON，也可能包裹在 markdown 代码块中。
    """
    text = text.strip()
    # 直接尝试
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # 尝试提取 ```json ... ``` 块
    if "```" in text:
        start = text.find("```")
        # 跳过 "json" 标记
        lang_end = text.find("\n", start)
        if lang_end != -1:
            content_start = lang_end + 1
            end = text.find("```", content_start)
            if end != -1:
                block = text[content_start:end].strip()
                try:
                    return json.loads(block)
                except json.JSONDecodeError:
                    pass
    # 尝试找第一个 { 和最后一个 }
    first_brace = text.find("{")
    last_brace = text.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        fragment = text[first_brace : last_brace + 1]
        try:
            return json.loads(fragment)
        except json.JSONDecodeError:
            pass
    return None


class QwenProvider(VLMProvider):
    """通义千问 Qwen-VL provider。"""

    name = "qwen"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self.base_url = config.get("base_url", "https://dashscope.aliyuncs.com/compatible-mode/v1")
        self.model = config.get("model", "qwen-vl-plus")
        self.api_key_env = config.get("api_key_env", "DASHSCOPE_API_KEY")
        self._api_key: str | None = None

    def _get_api_key(self) -> str:
        if self._api_key:
            return self._api_key
        key = os.getenv(self.api_key_env, "")
        if not key:
            raise ProviderError(
                f"未找到环境变量 {self.api_key_env}。"
                f"请在 .env.local 或环境变量中设置通义千问 API Key。"
            )
        return key

    def set_api_key(self, key: str) -> None:
        """运行时设置 API Key（不从环境变量读取）。"""
        self._api_key = key

    def is_available(self) -> bool:
        return bool(os.getenv(self.api_key_env)) or bool(self._api_key)

    def inspect(self, images: list[Path], prompt: str, options: dict | None = None) -> ProviderResult:
        """调用 Qwen-VL 进行巡检。"""
        if not images:
            return ProviderResult(success=False, error="没有提供图片")

        options = options or {}
        temperature = options.get("temperature", 0.1)

        try:
            api_key = self._get_api_key()
        except ProviderError as exc:
            return ProviderResult(success=False, error=str(exc))

        # 构建 messages
        content: list[dict[str, Any]] = [{"type": "text", "text": prompt}]
        for img_path in images:
            content.append({
                "type": "image_url",
                "image_url": {"url": _image_to_data_url(Path(img_path))},
            })

        payload = {
            "model": options.get("model", self.model),
            "messages": [{"role": "user", "content": content}],
            "temperature": temperature,
        }

        url = self.base_url.rstrip("/") + "/chat/completions"
        request = urllib.request.Request(
            url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=120) as resp:
                raw = resp.read().decode("utf-8")
            response = json.loads(raw)
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            return ProviderResult(
                success=False,
                error=f"HTTP {exc.code}: {body}",
            )
        except urllib.error.URLError as exc:
            return ProviderResult(
                success=False,
                error=f"网络错误: {exc}",
            )

        text = _extract_text(response)
        parsed = _parse_json(text)

        if parsed is None:
            return ProviderResult(
                success=False,
                error="无法从模型输出中解析 JSON",
                raw_text=text,
            )

        return ProviderResult(
            success=True,
            data=parsed,
            raw_text=text,
        )
