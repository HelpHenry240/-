"""Prompt 构建器：从风险规则文件动态生成巡检 prompt。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class PromptBuilder:
    """根据风险规则和模板构建巡检 prompt。"""

    def __init__(self, rules_path: Path | None = None, template_path: Path | None = None):
        root = Path(__file__).resolve().parents[2]
        self.rules_path = rules_path or (root / "configs" / "risk_rules.json")
        self.template_path = template_path or (root / "configs" / "prompts" / "risk_inspection_v1.md")

    def load_rules(self) -> list[dict[str, Any]]:
        """加载风险规则。"""
        if self.rules_path.exists():
            return json.loads(self.rules_path.read_text(encoding="utf-8"))
        # 回退到 demo 的规则文件
        demo_rules = Path(__file__).resolve().parents[2] / "demo" / "data" / "risk_rules.json"
        if demo_rules.exists():
            return json.loads(demo_rules.read_text(encoding="utf-8"))
        return []

    def load_template(self) -> str:
        """加载 prompt 模板。"""
        if self.template_path.exists():
            return self.template_path.read_text(encoding="utf-8")
        # 回退到 demo 的 prompt
        demo_prompt = Path(__file__).resolve().parents[2] / "demo" / "prompts" / "risk_inspection_prompt.md"
        if demo_prompt.exists():
            return demo_prompt.read_text(encoding="utf-8")
        return ""

    def build(self, extra_context: str = "") -> str:
        """构建完整 prompt。

        Args:
            extra_context: 额外的上下文信息（如场景类型提示）。

        Returns:
            完整 prompt 文本。
        """
        template = self.load_template()
        if extra_context:
            template = f"{template}\n\n## 额外上下文\n\n{extra_context}"
        return template

    def list_available_prompts(self) -> list[dict[str, str]]:
        """列出 configs/prompts/ 目录下可用的 prompt 模板。"""
        prompts_dir = Path(__file__).resolve().parents[2] / "configs" / "prompts"
        if not prompts_dir.exists():
            return []
        result = []
        for p in sorted(prompts_dir.glob("*.md")):
            result.append({
                "id": p.stem,
                "name": p.stem,
                "path": str(p),
            })
        return result
