"""多 run 对比模块。

对多个 run 的评测结果进行横向对比，
支持：同一数据集不同 Prompt 对比、同一 Prompt 不同模型对比。
"""

from __future__ import annotations

from typing import Any

from ..run_inspection import get_run, list_runs
from .metrics import evaluate_run


def compare_runs(run_ids: list[str]) -> dict[str, Any]:
    """对比多个 run 的评测结果。

    Args:
        run_ids: 要对比的 run ID 列表。

    Returns:
        对比结果，包含每个 run 的指标和逐样本对比。
    """
    if not run_ids:
        return {"error": "未提供 run ID"}

    runs_data: list[dict[str, Any]] = []

    for run_id in run_ids:
        run_data = get_run(run_id)
        if run_data is None:
            runs_data.append({
                "run_id": run_id,
                "error": f"未找到 run: {run_id}",
            })
            continue

        eval_result = evaluate_run(run_data)

        runs_data.append({
            "run_id": run_id,
            "dataset": run_data.get("dataset", ""),
            "provider": run_data.get("provider", ""),
            "model": run_data.get("model", ""),
            "prompt_id": run_data.get("prompt_id", ""),
            "created_at": run_data.get("created_at", ""),
            "metrics": {
                "total_samples": eval_result.get("total_samples", 0),
                "correct_samples": eval_result.get("correct_samples", 0),
                "accuracy": eval_result.get("accuracy", 0),
                "miss_count": eval_result.get("miss_count", 0),
                "false_alarm_count": eval_result.get("false_alarm_count", 0),
                "level_error_count": eval_result.get("level_error_count", 0),
                "format_error_count": eval_result.get("format_error_count", 0),
                "risk_samples": eval_result.get("risk_samples", 0),
                "normal_samples": eval_result.get("normal_samples", 0),
                "risk_category_coverage": eval_result.get("risk_category_coverage", 0),
                "risk_category_detected": eval_result.get("risk_category_detected", 0),
                "risk_category_match_rate": eval_result.get("risk_category_match_rate", 0),
            },
            "sample_evaluations": eval_result.get("sample_evaluations", []),
        })

    # 逐样本对比表
    sample_comparison = _build_sample_comparison(runs_data)

    # 找出差异样本（不同 run 结果不一致的样本）
    divergent_samples = _find_divergent_samples(sample_comparison)

    return {
        "run_count": len(runs_data),
        "runs": runs_data,
        "sample_comparison": sample_comparison,
        "divergent_samples": divergent_samples,
        "summary": _build_summary(runs_data),
    }


def _build_sample_comparison(runs_data: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """构建逐样本对比表。"""
    # 收集所有样本 ID（保持顺序）
    all_samples: list[str] = []
    seen: set[str] = set()
    for run in runs_data:
        for s in run.get("sample_evaluations", []):
            sid = s.get("sample_id", "")
            if sid and sid not in seen:
                all_samples.append(sid)
                seen.add(sid)

    result = []
    for sid in all_samples:
        row: dict[str, Any] = {"sample_id": sid}
        # 获取样本标题和场景类型
        for run in runs_data:
            for s in run.get("sample_evaluations", []):
                if s.get("sample_id") == sid:
                    row["title"] = s.get("title", "")
                    row["scene_type"] = s.get("scene_type", "")
                    break

        # 每个 run 的结果
        results_per_run = []
        for run in runs_data:
            run_id = run.get("run_id", "")
            found = None
            for s in run.get("sample_evaluations", []):
                if s.get("sample_id") == sid:
                    found = s
                    break
            if found:
                results_per_run.append({
                    "run_id": run_id,
                    "is_correct": found.get("is_correct", False),
                    "errors": [e.get("error_type", "") for e in found.get("errors", [])],
                    "gt_risk_count": found.get("gt_risk_count", 0),
                    "model_risk_count": found.get("model_risk_count", 0),
                })
            else:
                results_per_run.append({
                    "run_id": run_id,
                    "is_correct": None,
                    "errors": [],
                    "gt_risk_count": 0,
                    "model_risk_count": 0,
                })
        row["results"] = results_per_run
        result.append(row)

    return result


def _find_divergent_samples(sample_comparison: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """找出不同 run 结果不一致的样本。"""
    divergent = []
    for row in sample_comparison:
        results = row.get("results", [])
        if len(results) < 2:
            continue

        # 检查是否有差异
        correct_values = [r.get("is_correct") for r in results]
        if len(set([str(v) for v in correct_values])) > 1:
            divergent.append(row)
            continue

        # 检查错误类型是否有差异
        error_sets = [tuple(sorted(r.get("errors", []))) for r in results]
        if len(set(error_sets)) > 1:
            divergent.append(row)

    return divergent


def _build_summary(runs_data: list[dict[str, Any]]) -> dict[str, Any]:
    """构建对比摘要。"""
    valid_runs = [r for r in runs_data if "metrics" in r]
    if not valid_runs:
        return {}

    # 找出最佳 run
    best_run = max(valid_runs, key=lambda r: r["metrics"].get("accuracy", 0))

    # 收集所有 prompt 和 model
    prompts = list(set(r.get("prompt_id", "") for r in valid_runs))
    models = list(set(r.get("model", "") or r.get("provider", "") for r in valid_runs))

    return {
        "best_run_id": best_run.get("run_id", ""),
        "best_accuracy": best_run["metrics"].get("accuracy", 0),
        "prompts_compared": prompts,
        "models_compared": models,
        "comparison_type": "prompt" if len(prompts) > 1 else ("model" if len(models) > 1 else "single"),
    }


def auto_compare(
    dataset: str | None = None,
    provider: str | None = None,
    prompt_id: str | None = None,
    limit: int = 10,
) -> dict[str, Any]:
    """自动查找并对比符合条件的历史 run。

    Args:
        dataset: 筛选数据集。
        provider: 筛选 provider。
        prompt_id: 筛选 prompt。
        limit: 最多对比的 run 数量。

    Returns:
        对比结果。
    """
    all_runs = list_runs()
    filtered = []

    for r in all_runs:
        if dataset and r.get("dataset", "") != dataset:
            continue
        if provider and r.get("provider", "") != provider:
            continue
        if prompt_id and r.get("prompt_id", "") != prompt_id:
            continue
        filtered.append(r)

    filtered = filtered[:limit]
    run_ids = [r["run_id"] for r in filtered]

    if len(run_ids) < 2:
        return {
            "error": "找到的 run 少于 2 个，无法对比",
            "found_count": len(run_ids),
            "run_ids": run_ids,
        }

    return compare_runs(run_ids)
