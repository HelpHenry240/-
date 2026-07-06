"""FastAPI 后端服务：提供图片上传、provider 选择、实时巡检接口。

启动方式：
    python -m src.server
    或
    uvicorn src.server:app --reload --port 8000
"""

from __future__ import annotations

import json
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from .providers import get_provider, list_providers, load_config
from .providers.base import ProviderError
from .prompts import PromptBuilder
from .datasets.schema import validate_model_output
from .datasets.loaders import load_dataset, list_datasets
from .run_inspection import run_inspection, list_runs, get_run
from .evaluation import evaluate_run, generate_failure_report, compare_runs, auto_compare


ROOT = Path(__file__).resolve().parents[1]
OUTPUTS = ROOT / "outputs" / "vlm_results"
CUSTOM_DATASET = ROOT / "datasets" / "custom"

app = FastAPI(title="AI 视觉室内巡检 API", version="0.1.0")

# 允许前端跨域访问（开发阶段）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静态文件：让前端可以直接访问 demo 目录
app.mount("/demo", StaticFiles(directory=str(ROOT / "demo")), name="demo")

# 静态文件：巡逻游戏
app.mount("/game", StaticFiles(directory=str(ROOT / "game")), name="game")


@app.get("/api/health")
async def health():
    """健康检查。"""
    return {"status": "ok", "version": "0.1.0"}


@app.get("/api/providers")
async def api_providers():
    """列出所有可用 provider。"""
    config = load_config()
    providers = list_providers(config)
    active = config.get("active_provider", "mock")
    return {"active": active, "providers": providers}


@app.get("/api/prompts")
async def api_prompts():
    """列出可用 prompt 模板。"""
    builder = PromptBuilder()
    prompts = builder.list_available_prompts()
    return {"prompts": prompts}


@app.get("/api/risk_rules")
async def api_risk_rules():
    """返回风险规则。"""
    builder = PromptBuilder()
    rules = builder.load_rules()
    return {"rules": rules}


@app.post("/api/inspect")
async def api_inspect(
    files: list[UploadFile] | None = File(None),
    file: UploadFile | None = File(None),
    provider_name: str = Form("mock"),
    api_key: str = Form(""),
    prompt_id: str = Form("risk_inspection_v1"),
    mock_scene: str = Form(""),
    temperature: float = Form(0.1),
):
    """上传图片并执行巡检，支持单图和多视角多图。

    Args:
        files: 上传的图片文件列表（JPG/PNG/SVG）。
        file: 兼容旧前端的单张图片字段。
        provider_name: 使用的 provider 名称。
        api_key: 可选的 API Key（运行时传入，不落盘）。
        prompt_id: 使用的 prompt 模板 ID。
        mock_scene: mock 模式下指定的场景 ID。
        temperature: 生成温度。
    """
    upload_files: list[UploadFile] = []
    if file is not None:
        upload_files.append(file)
    if files:
        upload_files.extend(files)

    if not upload_files:
        raise HTTPException(status_code=400, detail="请至少上传一张图片")

    tmp_paths: list[Path] = []
    filenames: list[str] = []

    # 读取上传文件并保存到临时文件，供 provider 统一处理。
    for upload in upload_files:
        content = await upload.read()
        if not content:
            raise HTTPException(status_code=400, detail=f"上传文件为空: {upload.filename or '未命名文件'}")

        suffix = Path(upload.filename or "upload.jpg").suffix or ".jpg"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(content)
            tmp_paths.append(Path(tmp.name))
            filenames.append(upload.filename or Path(tmp.name).name)

    try:
        # 获取 provider
        config = load_config()
        provider_cfg = config.get("providers", {}).get(provider_name)
        if not provider_cfg:
            raise HTTPException(status_code=400, detail=f"未知 provider: {provider_name}")

        provider = get_provider(
            name=provider_name,
            config=config,
            api_key=api_key if api_key else None,
        )

        # 构建 prompt
        builder = PromptBuilder()
        if prompt_id and prompt_id != "risk_inspection_v1":
            template_path = ROOT / "configs" / "prompts" / f"{prompt_id}.md"
            builder.template_path = template_path
        extra_context = ""
        if len(tmp_paths) > 1:
            extra_context = (
                f"本次输入包含 {len(tmp_paths)} 张同一室内场景的多视角图片。"
                "请综合所有视角判断风险；如果某个视角证据不足，但其他视角能补充，请在 reason 中说明。"
            )
        prompt_text = builder.build(extra_context=extra_context)

        # 执行巡检
        options: dict[str, Any] = {"temperature": temperature}
        if mock_scene:
            options["mock_scene"] = mock_scene

        result = provider.inspect(tmp_paths, prompt_text, options)

        # 构建响应
        response_data: dict[str, Any] = {
            "provider": provider_name,
            "model": provider_cfg.get("model", ""),
            "prompt_id": prompt_id,
            "timestamp": datetime.now().isoformat(),
            "filename": filenames[0],
            "filenames": filenames,
            "input_count": len(filenames),
            "input_mode": "multi_image" if len(filenames) > 1 else "single_image",
            "success": result.success,
        }

        if result.success:
            valid, msg = validate_model_output(result.data)
            response_data["data"] = result.data
            response_data["valid"] = valid
            if not valid:
                response_data["validation_error"] = msg
            if result.raw_text:
                response_data["raw_text"] = result.raw_text[:5000]
        else:
            response_data["error"] = result.error
            if result.raw_text:
                response_data["raw_text"] = result.raw_text[:5000]

        # 保存结果到 outputs
        try:
            OUTPUTS.mkdir(parents=True, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = OUTPUTS / f"inspect_{ts}_{provider_name}.json"
            output_file.write_text(
                json.dumps(response_data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception:
            pass  # 保存失败不影响返回

        return JSONResponse(content=response_data)

    except ProviderError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"服务器内部错误: {exc}")
    finally:
        # 清理临时文件
        for tmp_path in tmp_paths:
            try:
                tmp_path.unlink(missing_ok=True)
            except Exception:
                pass


@app.post("/api/inspect_mock")
async def api_inspect_mock(scene_id: str = Form(...)):
    """快速获取某个场景的 mock 结果（无需上传图片）。"""
    from .providers import MockProvider

    provider = MockProvider()
    result = provider.inspect([], "", {"mock_scene": scene_id})
    return JSONResponse(content={
        "provider": "mock",
        "scene_id": scene_id,
        "success": result.success,
        "data": result.data,
    })


@app.post("/api/annotations/custom")
async def api_save_custom_annotation(
    file: UploadFile = File(...),
    sample_json: str = Form(...),
):
    """保存一张自建数据图片及其人工标注。

    sample_json 使用 SampleSchema 兼容结构，ground_truth 中可包含 bbox。
    API 不保存任何密钥信息，只写入 datasets/custom。
    """
    try:
        sample = json.loads(sample_json)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"sample_json 不是有效 JSON: {exc}")

    sample_id = _safe_sample_id(str(sample.get("sample_id", "")).strip())
    if not sample_id:
        raise HTTPException(status_code=400, detail="缺少 sample_id")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="上传文件为空")

    suffix = Path(file.filename or "image.jpg").suffix.lower() or ".jpg"
    if suffix not in {".jpg", ".jpeg", ".png", ".webp", ".svg", ".bmp"}:
        raise HTTPException(status_code=400, detail=f"不支持的图片格式: {suffix}")

    CUSTOM_DATASET.mkdir(parents=True, exist_ok=True)
    image_name = f"{sample_id}{suffix}"
    image_path = CUSTOM_DATASET / image_name
    image_path.write_bytes(content)

    sample["sample_id"] = sample_id
    sample["dataset"] = sample.get("dataset") or "custom"
    sample["media"] = [{
        "type": "image",
        "path": str(image_path),
        "view": "front",
        "timestamp": None,
    }]
    metadata = dict(sample.get("metadata", {}))
    metadata.update({
        "source": metadata.get("source", "real_photo"),
        "filename": image_name,
        "updated_at": datetime.now().isoformat(),
    })
    sample["metadata"] = metadata

    annotations_path = CUSTOM_DATASET / "annotations.json"
    annotations: list[dict[str, Any]] = []
    if annotations_path.exists():
        try:
            raw = json.loads(annotations_path.read_text(encoding="utf-8"))
            if isinstance(raw, list):
                annotations = raw
        except json.JSONDecodeError:
            annotations = []

    annotations = [item for item in annotations if item.get("sample_id") != sample_id]
    annotations.append(sample)
    annotations.sort(key=lambda item: item.get("sample_id", ""))
    annotations_path.write_text(
        json.dumps(annotations, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return {
        "success": True,
        "sample_id": sample_id,
        "image_path": str(image_path),
        "annotations_path": str(annotations_path),
        "risk_count": len(sample.get("ground_truth", [])),
    }


def _safe_sample_id(value: str) -> str:
    """将用户输入的 sample_id 限制为安全文件名片段。"""
    allowed = []
    for ch in value:
        if ch.isalnum() or ch in {"-", "_"}:
            allowed.append(ch)
    return "".join(allowed)[:80]


# ==================== 阶段 C：批量运行与评测 ====================


@app.get("/api/datasets")
async def api_datasets():
    """列出所有可用数据集。"""
    datasets = list_datasets()
    return {"datasets": datasets}


@app.post("/api/run_batch")
async def api_run_batch(
    dataset: str = Form("demo"),
    provider_name: str = Form("mock"),
    api_key: str = Form(""),
    prompt_id: str = Form("risk_inspection_v1"),
    temperature: float = Form(0.1),
):
    """批量运行数据集巡检。"""
    result = run_inspection(
        dataset=dataset,
        provider_name=provider_name,
        api_key=api_key if api_key else None,
        prompt_id=prompt_id,
        temperature=temperature,
    )

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    # 运行完成后自动评测
    eval_result = evaluate_run(result)
    failure_report = generate_failure_report(eval_result)

    # 保存评测结果
    try:
        eval_dir = ROOT / "outputs" / "evaluations"
        eval_dir.mkdir(parents=True, exist_ok=True)
        run_id = result.get("run_id", "unknown")
        eval_file = eval_dir / f"{run_id}_evaluation.json"
        eval_file.write_text(
            json.dumps(eval_result, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        failure_file = eval_dir / f"{run_id}_failures.json"
        failure_file.write_text(
            json.dumps(failure_report, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception:
        pass

    return JSONResponse(content={
        "run": {
            "run_id": result.get("run_id", ""),
            "dataset": result.get("dataset", ""),
            "provider": result.get("provider", ""),
            "model": result.get("model", ""),
            "summary": result.get("summary", {}),
        },
        "evaluation": {
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
        },
        "failure_cases": failure_report.get("failure_cases", []),
        "sample_evaluations": eval_result.get("sample_evaluations", []),
    })


@app.get("/api/runs")
async def api_runs():
    """列出所有历史 run。"""
    runs = list_runs()
    return {"runs": runs}


@app.get("/api/runs/{run_id}")
async def api_run_detail(run_id: str):
    """获取某个 run 的详细结果。"""
    run_data = get_run(run_id)
    if run_data is None:
        raise HTTPException(status_code=404, detail=f"未找到 run: {run_id}")
    return run_data


@app.get("/api/runs/{run_id}/evaluation")
async def api_run_evaluation(run_id: str):
    """获取某个 run 的评测结果。"""
    run_data = get_run(run_id)
    if run_data is None:
        raise HTTPException(status_code=404, detail=f"未找到 run: {run_id}")

    eval_result = evaluate_run(run_data)
    failure_report = generate_failure_report(eval_result)

    return {
        "evaluation": {
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
            "error_type_counts": eval_result.get("error_type_counts", {}),
        },
        "failure_cases": failure_report.get("failure_cases", []),
        "sample_evaluations": eval_result.get("sample_evaluations", []),
    }


# ==================== 阶段 D：多 Prompt / 多模型对比 ====================


@app.post("/api/compare")
async def api_compare(
    run_ids: str = Form(...),
):
    """对比多个 run 的评测结果。

    Args:
        run_ids: 逗号分隔的 run ID 列表。
    """
    ids = [r.strip() for r in run_ids.split(",") if r.strip()]
    if len(ids) < 2:
        raise HTTPException(status_code=400, detail="至少需要 2 个 run ID 进行对比")

    result = compare_runs(ids)
    return JSONResponse(content=result)


@app.post("/api/run_multi_batch")
async def api_run_multi_batch(
    dataset: str = Form("demo"),
    provider_name: str = Form("mock"),
    api_key: str = Form(""),
    prompt_ids: str = Form("risk_inspection_v1"),
    temperature: float = Form(0.1),
):
    """用多个 Prompt 对同一数据集运行批量巡检并自动对比。

    Args:
        prompt_ids: 逗号分隔的 prompt ID 列表。
    """
    ids = [p.strip() for p in prompt_ids.split(",") if p.strip()]
    if len(ids) < 2:
        raise HTTPException(status_code=400, detail="至少需要 2 个 prompt ID")

    run_ids = []
    for pid in ids:
        result = run_inspection(
            dataset=dataset,
            provider_name=provider_name,
            api_key=api_key if api_key else None,
            prompt_id=pid,
            temperature=temperature,
        )
        if "error" in result:
            raise HTTPException(status_code=400, detail=f"Prompt {pid} 运行失败: {result['error']}")
        run_ids.append(result.get("run_id", ""))

    comparison = compare_runs(run_ids)
    return JSONResponse(content={
        "run_ids": run_ids,
        "comparison": comparison,
    })


@app.get("/api/compare/auto")
async def api_auto_compare(
    dataset: str | None = None,
    provider: str | None = None,
    prompt_id: str | None = None,
):
    """自动查找并对比符合条件的历史 run。"""
    result = auto_compare(dataset=dataset, provider=provider, prompt_id=prompt_id)
    return JSONResponse(content=result)


def main():
    """启动服务器。"""
    import uvicorn

    print("=" * 50)
    print("AI 视觉室内巡检 API 服务")
    print("=" * 50)
    print("访问地址: http://localhost:8000")
    print("API 文档: http://localhost:8000/docs")
    print("前端页面: http://localhost:8000/demo/index.html")
    print("实时巡检: http://localhost:8000/demo/inspect.html")
    print("批量评测: http://localhost:8000/demo/batch.html")
    print("样本标注: http://localhost:8000/demo/annotate.html")
    print("巡逻游戏: http://localhost:8000/game/index.html")
    print("=" * 50)
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
