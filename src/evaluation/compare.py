"""失败案例筛选与对比。

对 ground truth 和模型输出进行逐项对比，
输出结构化的失败案例列表，包含错误类型、原因和改进建议。
"""

from __future__ import annotations

from typing import Any


# 错误类型到原因和改进方案的映射
ERROR_ANALYSIS: dict[str, dict[str, list[str]]] = {
    "漏检": {
        "possible_causes": [
            "遮挡：目标物体被其他物体遮挡，模型无法从当前视角观察到",
            "视角不足：单视角无法覆盖所有风险区域",
            "小目标：风险物体在图像中占比过小",
            "Prompt 规则不清：未明确要求检查该类风险",
            "模型能力不足：模型对该类空间关系理解有限",
        ],
        "improvements": [
            "补充视角：增加侧面或俯视角度的图片",
            "细化规则：在 Prompt 中明确要求检查该类风险",
            "要求证据充分性判断：让模型报告不确定的区域",
            "更换模型：尝试能力更强的视觉模型",
            "引入检测 baseline：先用目标检测定位物体再做关系推理",
        ],
    },
    "误检": {
        "possible_causes": [
            "模型幻觉：模型将正常摆放误判为风险",
            "空间关系错误：模型对距离和位置关系判断不准",
            "Prompt 过于宽泛：规则描述不够精确导致过度触发",
            "训练偏差：模型对某些物体组合有偏见",
        ],
        "improvements": [
            "细化规则：在 Prompt 中增加距离阈值或排除条件",
            "增加负样本：在 Prompt 中给出正常场景的示例",
            "要求空间推理：让模型明确说明距离和位置关系",
            "降低温度：减少模型的随机性",
        ],
    },
    "等级错误": {
        "possible_causes": [
            "等级定义模糊：Prompt 中未明确各级别的判断标准",
            "模型对严重程度判断不一致",
            "场景上下文不足：缺少环境信息导致等级偏差",
        ],
        "improvements": [
            "明确等级标准：在 Prompt 中给出每个等级的具体定义和示例",
            "增加场景上下文：提供场景类型和环境信息",
            "要求模型说明等级判断依据",
        ],
    },
    "输出格式错误": {
        "possible_causes": [
            "Prompt 对输出格式的约束不够强",
            "模型不遵循 JSON 输出指令",
            "模型输出了额外的解释文本干扰解析",
        ],
        "improvements": [
            "强化格式约束：在 Prompt 中多次强调只输出 JSON",
            "增加格式示例：给出完整的输出 JSON 示例",
            "增加后处理：用更鲁棒的 JSON 解析逻辑",
        ],
    },
    "空间关系错误": {
        "possible_causes": [
            "模型对 3D 空间关系理解不足",
            "单视角缺乏深度信息",
            "物体遮挡导致空间关系误判",
        ],
        "improvements": [
            "补充多视角图片",
            "在 Prompt 中要求模型描述物体间的空间关系",
            "使用支持空间推理的模型",
        ],
    },
}


def analyze_failure_case(failure: dict[str, Any]) -> dict[str, Any]:
    """分析单个失败案例，补充原因和改进建议。

    Args:
        failure: 失败案例数据，包含 errors 列表。

    Returns:
        增强后的失败案例，包含分析。
    """
    errors = failure.get("errors", [])
    analyzed_errors = []

    for err in errors:
        error_type = err.get("error_type", "")
        analysis = ERROR_ANALYSIS.get(error_type, ERROR_ANALYSIS.get("误检", {}))

        analyzed = {
            "error_type": error_type,
            "detail": err.get("detail", ""),
            "possible_causes": analysis.get("possible_causes", []),
            "improvements": analysis.get("improvements", []),
        }
        # 保留原始字段
        for k, v in err.items():
            if k not in analyzed:
                analyzed[k] = v
        analyzed_errors.append(analyzed)

    return {
        "sample_id": failure.get("sample_id", ""),
        "title": failure.get("title", ""),
        "scene_type": failure.get("scene_type", ""),
        "errors": analyzed_errors,
        "ground_truth": failure.get("ground_truth", []),
        "model_output": failure.get("model_output", {}),
    }


def compare_samples(
    ground_truth: list[dict[str, Any]],
    model_output: dict[str, Any],
) -> dict[str, Any]:
    """对比单个样本的 ground truth 和模型输出。

    返回详细的逐项对比结果。
    """
    from .metrics import evaluate_sample

    eval_result = evaluate_sample(ground_truth, model_output)

    # 逐风险项对比
    risk_comparisons = []
    gt_risks = {r.get("type", r.get("risk_type", "")): r for r in (ground_truth or [])}
    model_risks = {r.get("type", ""): r for r in (model_output.get("risks", []) if model_output else [])}

    all_types = set(gt_risks.keys()) | set(model_risks.keys())
    for risk_type in sorted(all_types):
        gt = gt_risks.get(risk_type)
        model = model_risks.get(risk_type)

        comparison: dict[str, Any] = {
            "risk_type": risk_type,
            "in_ground_truth": gt is not None,
            "in_model_output": model is not None,
        }

        if gt and model:
            comparison["status"] = "匹配"
            comparison["gt_level"] = gt.get("level", "")
            comparison["model_level"] = model.get("level", "")
            comparison["level_match"] = gt.get("level", "") == model.get("level", "")
            if not comparison["level_match"]:
                comparison["status"] = "等级不一致"
        elif gt and not model:
            comparison["status"] = "漏检"
        elif model and not gt:
            comparison["status"] = "误检"

        risk_comparisons.append(comparison)

    return {
        "is_correct": eval_result["is_correct"],
        "errors": eval_result["errors"],
        "risk_comparisons": risk_comparisons,
        "gt_risk_count": eval_result["gt_risk_count"],
        "model_risk_count": eval_result["model_risk_count"],
    }


def generate_failure_report(eval_data: dict[str, Any]) -> dict[str, Any]:
    """从评测结果生成失败案例分析报告。

    Args:
        eval_data: evaluate_run 的输出。

    Returns:
        结构化的失败案例分析报告。
    """
    failure_cases = eval_data.get("failure_cases", [])

    analyzed_cases = [analyze_failure_case(fc) for fc in failure_cases]

    # 按错误类型分组
    by_error_type: dict[str, list[dict]] = {}
    for case in analyzed_cases:
        for err in case.get("errors", []):
            etype = err.get("error_type", "其他")
            if etype not in by_error_type:
                by_error_type[etype] = []
            by_error_type[etype].append({
                "sample_id": case["sample_id"],
                "title": case["title"],
                "detail": err.get("detail", ""),
                "possible_causes": err.get("possible_causes", []),
                "improvements": err.get("improvements", []),
            })

    return {
        "run_id": eval_data.get("run_id", ""),
        "total_failures": len(analyzed_cases),
        "failure_cases": analyzed_cases,
        "by_error_type": by_error_type,
        "summary": {
            "accuracy": eval_data.get("accuracy", 0),
            "miss_count": eval_data.get("miss_count", 0),
            "false_alarm_count": eval_data.get("false_alarm_count", 0),
            "level_error_count": eval_data.get("level_error_count", 0),
            "format_error_count": eval_data.get("format_error_count", 0),
        },
    }
