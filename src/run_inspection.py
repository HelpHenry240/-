"""批量巡检运行器。

遍历数据集中的所有样本，逐个调用 VLM provider，
记录 run 元信息，保存每个样本的输出。

用法：
    python -m src.run_inspection --dataset demo --provider mock
    python -m src.run_inspection --dataset datasets/custom --provider qwen --api-key XXX
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from .datasets.loaders import load_dataset
from .datasets.schema import ModelOutput, validate_model_output
from .providers import get_provider, load_config
from .providers.base import ProviderError
from .prompts import PromptBuilder


ROOT = Path(__file__).resolve().parents[1]
OUTPUTS_DIR = ROOT / "outputs" / "vlm_results"


def run_inspection(
    dataset: str = "demo",
    provider_name: str = "mock",
    api_key: str | None = None,
    prompt_id: str = "risk_inspection_v1",
    output_dir: Path | None = None,
    temperature: float = 0.1,
) -> dict[str, Any]:
    """批量运行巡检。

    Args:
        dataset: 数据集名称或路径。
        provider_name: provider 名称。
        api_key: 可选 API Key。
        prompt_id: prompt 模板 ID。
        output_dir: 输出目录，默认 outputs/vlm_results/{run_id}。
        temperature: 生成温度。

    Returns:
        run 元信息和统计。
    """
    # 加载数据集
    samples = load_dataset(dataset)
    if not samples:
        return {"error": f"数据集为空或不存在: {dataset}"}

    # 获取 provider
    config = load_config()
    provider_cfg = config.get("providers", {}).get(provider_name)
    if not provider_cfg:
        return {"error": f"未知 provider: {provider_name}"}

    try:
        provider = get_provider(name=provider_name, config=config, api_key=api_key)
    except ProviderError as exc:
        return {"error": str(exc)}

    # 构建 prompt
    builder = PromptBuilder()
    if prompt_id and prompt_id != "risk_inspection_v1":
        template_path = ROOT / "configs" / "prompts" / f"{prompt_id}.md"
        builder.template_path = template_path
    prompt_text = builder.build()

    # 生成 run_id
    timestamp = datetime.now()
    run_id = f"{timestamp.strftime('%Y%m%d_%H%M%S')}_{provider_name}_{prompt_id}"
    run_dir = output_dir or (OUTPUTS_DIR / run_id)
    run_dir.mkdir(parents=True, exist_ok=True)

    # run 元信息
    run_meta: dict[str, Any] = {
        "run_id": run_id,
        "dataset": dataset,
        "provider": provider_name,
        "model": provider_cfg.get("model", ""),
        "prompt_id": prompt_id,
        "input_mode": "multi_image" if any(len(s.media) > 1 for s in samples) else "single_image",
        "temperature": temperature,
        "created_at": timestamp.isoformat(),
        "sample_count": len(samples),
        "results": [],
    }

    # 逐个样本运行
    success_count = 0
    error_count = 0
    has_risk_count = 0

    for i, sample in enumerate(samples):
        sample_id = sample.sample_id
        print(f"[{i+1}/{len(samples)}] 巡检 {sample_id} ({sample.title})...")

        # 获取图片路径
        image_paths = [Path(m.path) for m in sample.media if m.type == "image" and m.path]
        image_paths = [p for p in image_paths if p.exists()]

        # 调用 provider
        options = {"temperature": temperature}
        if provider_name == "mock":
            options["mock_scene"] = sample_id

        result = provider.inspect(image_paths, prompt_text, options)

        # 构建模型输出
        model_output = ModelOutput(
            sample_id=sample_id,
            provider=provider_name,
            model=provider_cfg.get("model", ""),
            prompt_id=prompt_id,
        )

        if result.success:
            valid, msg = validate_model_output(result.data)
            model_output.has_risk = result.data.get("has_risk", False)
            model_output.risks = []
            for r in result.data.get("risks", []):
                from .datasets.schema import RiskItem
                model_output.risks.append(RiskItem(
                    type=r.get("type", ""),
                    objects=r.get("objects", []),
                    location=r.get("location", ""),
                    bbox=r.get("bbox"),
                    level=r.get("level", ""),
                    reason=r.get("reason", ""),
                    suggestion=r.get("suggestion", ""),
                ))
            model_output.evidence_sufficiency = result.data.get("evidence_sufficiency", "")
            model_output.uncertain_points = result.data.get("uncertain_points", [])
            model_output.raw_response = result.data
            if not valid:
                model_output.error = f"格式校验警告: {msg}"
            success_count += 1
            if model_output.has_risk:
                has_risk_count += 1
        else:
            model_output.error = result.error or "未知错误"
            error_count += 1

        # 保存单个样本结果
        sample_result = {
            "sample_id": sample_id,
            "title": sample.title,
            "scene_type": sample.scene_type,
            "media_count": len(image_paths),
            "ground_truth": [g.to_dict() for g in sample.ground_truth],
            "model_output": model_output.to_dict(),
            "success": result.success,
        }
        run_meta["results"].append(sample_result)

    # 汇总统计
    run_meta["summary"] = {
        "total": len(samples),
        "success": success_count,
        "error": error_count,
        "has_risk": has_risk_count,
        "no_risk": success_count - has_risk_count,
    }

    # 保存 run 结果
    output_file = run_dir / "results.json"
    output_file.write_text(
        json.dumps(run_meta, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"\n运行完成: {run_id}")
    print(f"  成功: {success_count}/{len(samples)}")
    print(f"  有风险: {has_risk_count}")
    print(f"  无风险: {success_count - has_risk_count}")
    print(f"  错误: {error_count}")
    print(f"  结果保存至: {run_dir}")

    return run_meta


def list_runs() -> list[dict[str, Any]]:
    """列出所有历史 run。"""
    if not OUTPUTS_DIR.exists():
        return []

    runs = []
    for d in sorted(OUTPUTS_DIR.iterdir(), reverse=True):
        if d.is_dir():
            results_file = d / "results.json"
            if results_file.exists():
                try:
                    data = json.loads(results_file.read_text(encoding="utf-8"))
                    runs.append({
                        "run_id": data.get("run_id", d.name),
                        "dataset": data.get("dataset", ""),
                        "provider": data.get("provider", ""),
                        "model": data.get("model", ""),
                        "prompt_id": data.get("prompt_id", ""),
                        "created_at": data.get("created_at", ""),
                        "sample_count": data.get("sample_count", 0),
                        "summary": data.get("summary", {}),
                    })
                except Exception:
                    pass
    return runs


def get_run(run_id: str) -> dict[str, Any] | None:
    """获取某个 run 的完整结果。"""
    run_dir = OUTPUTS_DIR / run_id
    results_file = run_dir / "results.json"
    if results_file.exists():
        return json.loads(results_file.read_text(encoding="utf-8"))
    return None


def main():
    """命令行入口。"""
    parser = argparse.ArgumentParser(description="批量巡检运行")
    parser.add_argument("--dataset", default="demo", help="数据集名称或路径")
    parser.add_argument("--provider", default="mock", help="provider 名称")
    parser.add_argument("--api-key", default=None, help="API Key（可选）")
    parser.add_argument("--prompt-id", default="risk_inspection_v1", help="prompt 模板 ID")
    parser.add_argument("--temperature", type=float, default=0.1, help="生成温度")
    parser.add_argument("--list-runs", action="store_true", help="列出历史 run")
    args = parser.parse_args()

    if args.list_runs:
        runs = list_runs()
        for r in runs:
            s = r.get("summary", {})
            print(f"{r['run_id']} | {r['dataset']} | {r['provider']} | "
                  f"{s.get('success', 0)}/{s.get('total', 0)} 成功")
        return

    result = run_inspection(
        dataset=args.dataset,
        provider_name=args.provider,
        api_key=args.api_key,
        prompt_id=args.prompt_id,
        temperature=args.temperature,
    )

    if "error" in result:
        print(f"错误: {result['error']}")


if __name__ == "__main__":
    main()
