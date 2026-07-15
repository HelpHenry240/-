"""视觉模型结构化输出校验。"""

from __future__ import annotations

from typing import Any


RISK_LEVELS = {"低", "中", "高"}
EVIDENCE_LEVELS = {"充分", "部分充分", "不充分"}
REQUIRED_RISK_FIELDS = {
    "risk_type",
    "risk_name",
    "rule_id",
    "objects",
    "location",
    "bbox",
    "level",
    "reason",
    "suggestion",
}


def validate_model_output(data: dict[str, Any]) -> tuple[bool, str]:
    """校验模型输出的字段、类型与基本一致性。"""
    if not isinstance(data, dict):
        return False, "输出不是 JSON 对象"
    if not isinstance(data.get("has_risk"), bool):
        return False, "has_risk 必须是布尔值"
    if not isinstance(data.get("risks"), list):
        return False, "risks 必须是数组"
    if data["has_risk"] != bool(data["risks"]):
        return False, "has_risk 与 risks 是否为空不一致"
    if data.get("evidence_sufficiency") not in EVIDENCE_LEVELS:
        return False, "evidence_sufficiency 必须为充分、部分充分或不充分"
    if not isinstance(data.get("uncertain_points"), list):
        return False, "uncertain_points 必须是数组"

    for index, risk in enumerate(data["risks"]):
        if not isinstance(risk, dict):
            return False, f"risks[{index}] 不是对象"
        missing = sorted(REQUIRED_RISK_FIELDS - risk.keys())
        if missing:
            return False, f"risks[{index}] 缺少字段: {', '.join(missing)}"
        if risk.get("level") not in RISK_LEVELS:
            return False, f"risks[{index}].level 必须为低、中或高"
        if not isinstance(risk.get("objects"), list):
            return False, f"risks[{index}].objects 必须是数组"
        bbox = risk.get("bbox")
        if bbox is not None:
            if not isinstance(bbox, list) or len(bbox) != 4:
                return False, f"risks[{index}].bbox 必须为 null 或包含 4 个数值的数组"
            if any(not isinstance(value, (int, float)) or not 0 <= value <= 1 for value in bbox):
                return False, f"risks[{index}].bbox 数值必须在 0 到 1 之间"
        views = risk.get("view_indices", [])
        primary = risk.get("primary_view_index")
        if not isinstance(views, list) or any(not isinstance(value, int) or value < 1 for value in views):
            return False, f"risks[{index}].view_indices 必须是正整数数组"
        if primary is not None and primary not in views:
            return False, f"risks[{index}].primary_view_index 必须属于 view_indices"
    return True, ""
