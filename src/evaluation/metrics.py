"""评测指标计算。

统计漏检、误检、风险类型匹配、等级错误等指标。
"""

from __future__ import annotations

from collections import Counter
from typing import Any


def _normalize_risk_type(risk_type: str) -> str:
    """归一化风险类型名称，容忍小差异。"""
    return risk_type.strip()


def evaluate_sample(
    ground_truth: list[dict[str, Any]],
    model_output: dict[str, Any],
) -> dict[str, Any]:
    """评测单个样本。

    Args:
        ground_truth: 人工标注的风险列表。
        model_output: 模型输出的结构化结果。

    Returns:
        评测结果，包含错误类型列表。
    """
    gt_risks = ground_truth or []
    model_risks = model_output.get("risks", []) if model_output else []
    model_has_risk = model_output.get("has_risk", False)

    gt_types = {_normalize_risk_type(r.get("type", r.get("risk_type", ""))) for r in gt_risks}
    model_types = {_normalize_risk_type(r.get("type", "")) for r in model_risks}

    errors: list[dict[str, str]] = []

    # 漏检：ground truth 有风险但模型没检测到
    if gt_risks and not model_has_risk:
        errors.append({
            "error_type": "漏检",
            "detail": f"人工标注 {len(gt_risks)} 个风险，但模型未检出任何风险",
            "missing_types": ", ".join(sorted(gt_types)),
        })
    elif gt_risks and model_has_risk:
        # 检查每个 ground truth 风险类型是否被模型覆盖
        missing_types = gt_types - model_types
        if missing_types:
            errors.append({
                "error_type": "漏检",
                "detail": f"模型未检出以下风险类型: {', '.join(sorted(missing_types))}",
                "missing_types": ", ".join(sorted(missing_types)),
            })

    # 误检：模型检测到风险但 ground truth 没有
    if model_has_risk and not gt_risks:
        errors.append({
            "error_type": "误检",
            "detail": f"人工标注无风险，但模型检出 {len(model_risks)} 个风险",
            "extra_types": ", ".join(sorted(model_types)),
        })
    elif model_has_risk and gt_risks:
        extra_types = model_types - gt_types
        if extra_types:
            errors.append({
                "error_type": "误检",
                "detail": f"模型检出了人工未标注的风险类型: {', '.join(sorted(extra_types))}",
                "extra_types": ", ".join(sorted(extra_types)),
            })

    # 等级错误：检查匹配的风险类型中等级是否一致
    if gt_risks and model_has_risk:
        gt_level_map = {
            _normalize_risk_type(r.get("type", r.get("risk_type", ""))): r.get("level", "")
            for r in gt_risks
        }
        model_level_map = {
            _normalize_risk_type(r.get("type", "")): r.get("level", "")
            for r in model_risks
        }
        for risk_type, gt_level in gt_level_map.items():
            if risk_type in model_level_map:
                model_level = model_level_map[risk_type]
                if gt_level and model_level and gt_level != model_level:
                    errors.append({
                        "error_type": "等级错误",
                        "detail": f"风险「{risk_type}」: 人工标注「{gt_level}」，模型判定「{model_level}」",
                        "risk_type": risk_type,
                        "gt_level": gt_level,
                        "model_level": model_level,
                    })

    # 格式错误
    if model_output and model_output.get("error") and "格式校验" in str(model_output.get("error", "")):
        errors.append({
            "error_type": "输出格式错误",
            "detail": model_output["error"],
        })

    is_correct = len(errors) == 0
    return {
        "is_correct": is_correct,
        "errors": errors,
        "gt_risk_count": len(gt_risks),
        "model_risk_count": len(model_risks),
        "gt_types": sorted(gt_types),
        "model_types": sorted(model_types),
    }


def evaluate_run(run_data: dict[str, Any]) -> dict[str, Any]:
    """评测整个 run。

    Args:
        run_data: run 的完整结果数据（含 results 数组）。

    Returns:
        评测汇总，包含总体指标和失败案例列表。
    """
    results = run_data.get("results", [])
    if not results:
        return {"error": "run 结果为空"}

    total = len(results)
    success = sum(1 for r in results if r.get("success", False))
    error_count = total - success

    # 风险样本数（人工标注有风险）
    risk_samples = sum(1 for r in results if r.get("ground_truth"))
    normal_samples = total - risk_samples

    # 逐样本评测
    sample_evals = []
    failure_cases = []
    correct_count = 0

    # 错误类型统计
    error_type_counts: Counter = Counter()

    # 风险类别覆盖
    all_gt_types: set[str] = set()
    all_model_types: set[str] = set()

    for r in results:
        sample_id = r.get("sample_id", "")
        gt = r.get("ground_truth", [])
        model_out = r.get("model_output", {})
        title = r.get("title", "")
        scene_type = r.get("scene_type", "")

        eval_result = evaluate_sample(gt, model_out)

        # 收集风险类型
        for t in eval_result["gt_types"]:
            all_gt_types.add(t)
        for t in eval_result["model_types"]:
            all_model_types.add(t)

        sample_eval = {
            "sample_id": sample_id,
            "title": title,
            "scene_type": scene_type,
            "is_correct": eval_result["is_correct"],
            "errors": eval_result["errors"],
            "gt_risk_count": eval_result["gt_risk_count"],
            "model_risk_count": eval_result["model_risk_count"],
        }
        sample_evals.append(sample_eval)

        if eval_result["is_correct"]:
            correct_count += 1
        else:
            failure_cases.append({
                "sample_id": sample_id,
                "title": title,
                "scene_type": scene_type,
                "errors": eval_result["errors"],
                "ground_truth": gt,
                "model_output": model_out,
            })

        for err in eval_result["errors"]:
            error_type_counts[err["error_type"]] += 1

    # 风险类型匹配数
    matched_types = all_gt_types & all_model_types

    return {
        "run_id": run_data.get("run_id", ""),
        "total_samples": total,
        "success_samples": success,
        "error_samples": error_count,
        "risk_samples": risk_samples,
        "normal_samples": normal_samples,
        "correct_samples": correct_count,
        "accuracy": round(correct_count / total, 4) if total > 0 else 0,
        "risk_category_coverage": len(all_gt_types),
        "risk_category_detected": len(matched_types),
        "risk_category_match_rate": round(len(matched_types) / len(all_gt_types), 4) if all_gt_types else 0,
        "error_type_counts": dict(error_type_counts),
        "miss_count": error_type_counts.get("漏检", 0),
        "false_alarm_count": error_type_counts.get("误检", 0),
        "level_error_count": error_type_counts.get("等级错误", 0),
        "format_error_count": error_type_counts.get("输出格式错误", 0),
        "failure_cases": failure_cases,
        "sample_evaluations": sample_evals,
    }
