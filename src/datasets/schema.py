"""数据 schema 定义。

按 AGENTS.md 3.3 节推荐的结构定义场景样本和模型输出，
不依赖第三方库，仅用 dataclass + dict 转换。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any


@dataclass
class MediaItem:
    """单个媒体文件（图片或视频帧）。"""

    type: str = "image"  # image | video_frame
    path: str = ""
    view: str = "front"  # front | side | top | back
    timestamp: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "path": self.path,
            "view": self.view,
            "timestamp": self.timestamp,
        }


@dataclass
class GroundTruth:
    """人工标注的风险项。"""

    risk_type: str = ""
    risk_name: str = ""
    objects: list[str] = field(default_factory=list)
    location: str = ""
    bbox: list[float] | None = None  # [x, y, width, height], normalized 0-1
    level: str = ""  # 低 | 中 | 高
    rule_id: str = ""
    reason: str = ""
    suggestion: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "risk_type": self.risk_type,
            "risk_name": self.risk_name,
            "objects": list(self.objects),
            "location": self.location,
            "bbox": list(self.bbox) if self.bbox else None,
            "level": self.level,
            "rule_id": self.rule_id,
            "reason": self.reason,
            "suggestion": self.suggestion,
        }


@dataclass
class RiskItem:
    """模型输出的风险项。"""

    type: str = ""
    objects: list[str] = field(default_factory=list)
    location: str = ""
    bbox: list[float] | None = None  # [x, y, width, height], normalized 0-1
    level: str = ""
    reason: str = ""
    suggestion: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "objects": list(self.objects),
            "location": self.location,
            "bbox": list(self.bbox) if self.bbox else None,
            "level": self.level,
            "reason": self.reason,
            "suggestion": self.suggestion,
        }


@dataclass
class SampleSchema:
    """场景样本的通用结构。"""

    sample_id: str = ""
    dataset: str = "custom"
    scene_type: str = ""  # 宿舍 | 厨房 | 客厅 | 实验室 | 走廊 | 其他
    title: str = ""
    summary: str = ""
    media: list[MediaItem] = field(default_factory=list)
    objects: list[str] = field(default_factory=list)
    regions: list[str] = field(default_factory=list)
    ground_truth: list[GroundTruth] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "sample_id": self.sample_id,
            "dataset": self.dataset,
            "scene_type": self.scene_type,
            "title": self.title,
            "summary": self.summary,
            "media": [m.to_dict() for m in self.media],
            "objects": list(self.objects),
            "regions": list(self.regions),
            "ground_truth": [g.to_dict() for g in self.ground_truth],
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SampleSchema:
        media = [MediaItem(**m) for m in data.get("media", [])]
        gt = [GroundTruth(**g) for g in data.get("ground_truth", [])]
        return cls(
            sample_id=data.get("sample_id", data.get("id", "")),
            dataset=data.get("dataset", "custom"),
            scene_type=data.get("scene_type", ""),
            title=data.get("title", ""),
            summary=data.get("summary", ""),
            media=media,
            objects=list(data.get("objects", [])),
            regions=list(data.get("regions", [])),
            ground_truth=gt,
            metadata=dict(data.get("metadata", {})),
        )


@dataclass
class ModelOutput:
    """模型结构化输出。"""

    sample_id: str = ""
    provider: str = ""
    model: str = ""
    prompt_id: str = ""
    has_risk: bool = False
    risks: list[RiskItem] = field(default_factory=list)
    evidence_sufficiency: str = ""
    uncertain_points: list[str] = field(default_factory=list)
    raw_response: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "sample_id": self.sample_id,
            "provider": self.provider,
            "model": self.model,
            "prompt_id": self.prompt_id,
            "has_risk": self.has_risk,
            "risks": [r.to_dict() for r in self.risks],
            "evidence_sufficiency": self.evidence_sufficiency,
            "uncertain_points": list(self.uncertain_points),
            "raw_response": self.raw_response,
        }
        if self.error:
            result["error"] = self.error
        if self.note:
            result["note"] = self.note
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ModelOutput:
        risks = [RiskItem(**r) for r in data.get("risks", [])]
        return cls(
            sample_id=data.get("sample_id", ""),
            provider=data.get("provider", ""),
            model=data.get("model", ""),
            prompt_id=data.get("prompt_id", ""),
            has_risk=data.get("has_risk", False),
            risks=risks,
            evidence_sufficiency=data.get("evidence_sufficiency", ""),
            uncertain_points=list(data.get("uncertain_points", [])),
            raw_response=data.get("raw_response", {}),
            error=data.get("error"),
            note=data.get("note", ""),
        )


def validate_model_output(data: dict[str, Any]) -> tuple[bool, str]:
    """校验模型输出是否包含必要字段。

    返回 (是否有效, 错误信息)。
    """
    if not isinstance(data, dict):
        return False, "输出不是 JSON 对象"
    if "has_risk" not in data:
        return False, "缺少 has_risk 字段"
    if "risks" not in data:
        return False, "缺少 risks 字段"
    if not isinstance(data["risks"], list):
        return False, "risks 不是数组"
    for i, risk in enumerate(data["risks"]):
        if not isinstance(risk, dict):
            return False, f"risks[{i}] 不是对象"
        if "type" not in risk:
            return False, f"risks[{i}] 缺少 type 字段"
        if "level" not in risk:
            return False, f"risks[{i}] 缺少 level 字段"
    return True, ""
