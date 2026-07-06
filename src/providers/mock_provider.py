"""Mock Provider：无网络、无 API Key 的本地模拟输出。

用于课堂演示和开发调试。当没有真实 VLM 时，返回内置的模拟结果。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .base import VLMProvider, ProviderResult


class MockProvider(VLMProvider):
    """本地模拟 provider。"""

    name = "mock"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        # 尝试加载 demo 的 mock 数据
        demo_root = Path(__file__).resolve().parents[2]
        self.mock_path = demo_root / "demo" / "data" / "mock_vlm_results.json"

    def inspect(self, images: list[Path], prompt: str, options: dict | None = None) -> ProviderResult:
        """返回模拟结果。

        策略：如果 options 中指定了 mock_scene，则返回该场景的预设结果；
        否则返回一个通用的模拟输出（有风险）。
        """
        options = options or {}
        scene_id = options.get("mock_scene", "")

        if scene_id and self.mock_path.exists():
            mock_data = json.loads(self.mock_path.read_text(encoding="utf-8"))
            if scene_id in mock_data:
                return ProviderResult(success=True, data=mock_data[scene_id])

        # 通用模拟输出
        mock_output = {
            "has_risk": True,
            "risks": [
                {
                    "type": "触电风险",
                    "objects": ["水杯", "插座"],
                    "location": "桌面靠墙区域",
                    "level": "高",
                    "reason": "模拟输出：液体容器靠近插座，触发液体靠近电源的规则。",
                    "suggestion": "移动水杯并保持插座周围干燥。",
                }
            ],
            "evidence_sufficiency": "充分",
            "uncertain_points": [],
        }
        return ProviderResult(success=True, data=mock_output)

    def is_available(self) -> bool:
        return True
