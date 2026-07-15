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
        self.template_path = template_path or (root / "configs" / "prompts" / "indoor_safety_v1.md")

    def load_rules(self) -> list[dict[str, Any]]:
        """加载风险规则。"""
        if self.rules_path.exists():
            return json.loads(self.rules_path.read_text(encoding="utf-8"))
        return []

    def load_template(self) -> str:
        """加载 prompt 模板。"""
        if self.template_path.exists():
            return self.template_path.read_text(encoding="utf-8")
        return ""

    def build(self, extra_context: str = "") -> str:
        """构建完整 prompt。

        Args:
            extra_context: 额外的上下文信息（如场景类型提示）。

        Returns:
            完整 prompt 文本。
        """
        template = self.load_template()
        rules_json = json.dumps(self.load_rules(), ensure_ascii=False, indent=2)
        template = template.replace("{{RISK_RULES_JSON}}", rules_json)
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
