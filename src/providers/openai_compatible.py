"""通用 OpenAI-compatible 视觉模型 Provider。"""

from __future__ import annotations

import base64
import json
import mimetypes
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from .base import ProviderError, ProviderResult, VLMProvider


def _image_to_data_url(path: Path) -> str:
    mime = mimetypes.guess_type(path.name)[0] or "image/jpeg"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def _extract_text(response: dict[str, Any]) -> str:
    choices = response.get("choices") or []
    if not choices:
        return ""
    content = (choices[0].get("message") or {}).get("content", "")
    if isinstance(content, list):
        return "\n".join(
            str(item.get("text", "")) if isinstance(item, dict) else str(item)
            for item in content
            if not isinstance(item, dict) or item.get("type") in {"text", "output_text"}
        )
    return str(content)


def _parse_json(text: str) -> dict[str, Any] | None:
    candidates = [text.strip()]
    if "```" in text:
        for block in text.split("```")[1::2]:
            candidates.append(block.removeprefix("json").strip())
    start, end = text.find("{"), text.rfind("}")
    if start >= 0 and end > start:
        candidates.append(text[start : end + 1])
    for candidate in candidates:
        try:
            value = json.loads(candidate)
            if isinstance(value, dict):
                return value
        except json.JSONDecodeError:
            continue
    return None


class OpenAICompatibleProvider(VLMProvider):
    """适配采用 ``chat/completions`` 多模态消息格式的视觉 API。"""

    name = "openai_compatible"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        cfg = config or {}
        self.base_url = str(cfg.get("base_url", "")).rstrip("/")
        self.model = str(cfg.get("model", ""))
        self.api_key_env = str(cfg.get("api_key_env", ""))
        self.auth_header = str(cfg.get("auth_header", "Authorization"))
        self.auth_scheme = str(cfg.get("auth_scheme", "Bearer"))
        self.extra_headers = dict(cfg.get("extra_headers") or {})
        self.extra_body = dict(cfg.get("extra_body") or {})
        self.timeout = int(cfg.get("timeout", 120))
        self.api_key_optional = bool(cfg.get("api_key_optional", False))
        self._api_key: str | None = None

    def set_api_key(self, key: str) -> None:
        self._api_key = key

    def _get_api_key(self) -> str:
        key = self._api_key or (os.getenv(self.api_key_env, "") if self.api_key_env else "")
        if not key and not self.api_key_optional:
            source = self.api_key_env or "API Key"
            raise ProviderError(f"未提供 {source}，请在当前页面输入或设置对应环境变量。")
        return key

    def is_available(self) -> bool:
        return self.api_key_optional or bool(self._api_key) or bool(self.api_key_env and os.getenv(self.api_key_env))

    def inspect(self, images: list[Path], prompt: str, options: dict | None = None) -> ProviderResult:
        if not images:
            return ProviderResult(success=False, error="没有提供图片")
        if not self.base_url or not self.model:
            return ProviderResult(success=False, error="Provider 缺少 Base URL 或模型名称")

        options = options or {}
        try:
            api_key = self._get_api_key()
        except ProviderError as exc:
            return ProviderResult(success=False, error=str(exc))

        content: list[dict[str, Any]] = [{"type": "text", "text": prompt}]
        content.extend(
            {"type": "image_url", "image_url": {"url": _image_to_data_url(Path(image))}}
            for image in images
        )
        extra_body = {**self.extra_body, **(options.get("extra_body") or {})}
        for protected_key in ("model", "messages"):
            extra_body.pop(protected_key, None)
        payload: dict[str, Any] = {
            **extra_body,
            "model": options.get("model") or self.model,
            "messages": [{"role": "user", "content": content}],
            "temperature": options.get("temperature", 0.1),
        }

        headers = {**self.extra_headers, "Content-Type": "application/json"}
        headers.update(options.get("extra_headers") or {})
        headers["Content-Type"] = "application/json"
        if api_key:
            headers[self.auth_header] = f"{self.auth_scheme} {api_key}".strip()

        url = self.base_url if self.base_url.endswith("/chat/completions") else f"{self.base_url}/chat/completions"
        request = urllib.request.Request(
            url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                raw = response.read().decode("utf-8")
            response_data = json.loads(raw)
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            return ProviderResult(success=False, error=f"HTTP {exc.code}: {body[:2000]}")
        except (urllib.error.URLError, TimeoutError) as exc:
            return ProviderResult(success=False, error=f"网络请求失败: {exc}")
        except json.JSONDecodeError as exc:
            return ProviderResult(success=False, error=f"API 响应不是有效 JSON: {exc}")

        text = _extract_text(response_data)
        parsed = _parse_json(text)
        if parsed is None:
            return ProviderResult(success=False, error="无法从模型输出中解析结构化 JSON", raw_text=text)
        return ProviderResult(success=True, data=parsed, raw_text=text)
