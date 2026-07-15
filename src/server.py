"""AI 视觉室内巡检 FastAPI 服务。"""

from __future__ import annotations

import json
import re
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles

from .datasets.schema import validate_model_output
from .prompts import PromptBuilder
from .providers import ProviderError, get_provider, list_providers, load_config
from .reports import build_risk_annotations, render_markdown_html, render_pdf, render_single_report


ROOT = Path(__file__).resolve().parents[1]
MAX_FILE_SIZE = 20 * 1024 * 1024
ALLOWED_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"}

app = FastAPI(title="AI 视觉室内巡检 API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
app.mount("/demo", StaticFiles(directory=str(ROOT / "demo"), html=True), name="demo")


@app.get("/", include_in_schema=False)
async def root() -> RedirectResponse:
    return RedirectResponse("/demo/index.html")


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "version": "1.0.0"}


@app.get("/api/providers")
async def api_providers() -> dict[str, Any]:
    config = load_config()
    return {"active": config.get("active_provider", "qwen"), "providers": list_providers(config)}


@app.get("/api/prompts")
async def api_prompts() -> dict[str, Any]:
    return {"prompts": PromptBuilder().list_available_prompts()}


@app.get("/api/risk_rules")
async def api_risk_rules() -> dict[str, Any]:
    return {"rules": PromptBuilder().load_rules()}


def _parse_json_object(raw: str, field_name: str) -> dict[str, Any]:
    if not raw.strip():
        return {}
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"{field_name} 不是有效 JSON: {exc.msg}") from exc
    if not isinstance(value, dict):
        raise HTTPException(status_code=400, detail=f"{field_name} 必须是 JSON 对象")
    return value


def _validate_base_url(value: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.username or parsed.password:
        raise HTTPException(status_code=400, detail="Base URL 必须是有效的 HTTP(S) 地址，且不能包含账号密码")
    return value.rstrip("/")


@app.post("/api/inspect")
async def api_inspect(
    files: list[UploadFile] = File(...),
    provider_name: str = Form(...),
    api_key: str = Form(""),
    prompt_id: str = Form("indoor_safety_v1"),
    base_url: str = Form(""),
    model: str = Form(""),
    extra_headers: str = Form(""),
    extra_body: str = Form(""),
    temperature: float = Form(0.1),
) -> JSONResponse:
    """上传单图或同场景多视角图片并生成一次性巡检报告。"""
    if not files:
        raise HTTPException(status_code=400, detail="请至少上传一张图片")
    if len(files) > 8:
        raise HTTPException(status_code=400, detail="单次巡检最多上传 8 张图片")
    if not 0 <= temperature <= 2:
        raise HTTPException(status_code=400, detail="temperature 必须在 0 到 2 之间")

    config = load_config()
    provider_cfg = config.get("providers", {}).get(provider_name)
    if not provider_cfg:
        raise HTTPException(status_code=400, detail=f"未知 Provider: {provider_name}")

    overrides: dict[str, Any] = {}
    if base_url.strip():
        overrides["base_url"] = _validate_base_url(base_url.strip())
    if model.strip():
        overrides["model"] = model.strip()
    headers = _parse_json_object(extra_headers, "额外请求头")
    body = _parse_json_object(extra_body, "额外请求参数")
    if headers:
        overrides["extra_headers"] = headers
    if body:
        overrides["extra_body"] = body

    prompt_path = ROOT / "configs" / "prompts" / f"{prompt_id}.md"
    if not prompt_path.is_file():
        raise HTTPException(status_code=400, detail=f"未知 Prompt: {prompt_id}")

    temporary_paths: list[Path] = []
    filenames: list[str] = []
    try:
        for upload in files:
            suffix = Path(upload.filename or "upload.jpg").suffix.lower()
            if suffix not in ALLOWED_SUFFIXES:
                raise HTTPException(status_code=400, detail=f"不支持的图片格式: {suffix or '无扩展名'}")
            content = await upload.read(MAX_FILE_SIZE + 1)
            if not content:
                raise HTTPException(status_code=400, detail=f"上传文件为空: {upload.filename}")
            if len(content) > MAX_FILE_SIZE:
                raise HTTPException(status_code=413, detail=f"图片超过 20MB: {upload.filename}")
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
                temp_file.write(content)
                temporary_paths.append(Path(temp_file.name))
            filenames.append(upload.filename or "未命名图片")

        builder = PromptBuilder(template_path=prompt_path)
        context = ""
        if len(temporary_paths) > 1:
            context = (
                f"输入含 {len(temporary_paths)} 张同一场景的多视角图片。"
                "请交叉验证各视角；每项风险用 view_indices 标明证据所在图片序号，"
                "用 primary_view_index 标明主要定位图。"
            )
        prompt = builder.build(extra_context=context)
        provider = get_provider(provider_name, config=config, api_key=api_key or None, overrides=overrides)
        result = provider.inspect(temporary_paths, prompt, {"temperature": temperature})
        effective_cfg = {**provider_cfg, **overrides}
        inspection: dict[str, Any] = {
            "provider": provider_name,
            "model": effective_cfg.get("model", ""),
            "prompt_id": prompt_id,
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "filenames": filenames,
            "input_count": len(filenames),
            "input_mode": "multi_image" if len(filenames) > 1 else "single_image",
            "success": result.success,
        }
        if result.success:
            valid, message = validate_model_output(result.data)
            inspection.update({"data": result.data, "valid": valid})
            if not valid:
                inspection["validation_error"] = message
        else:
            inspection["error"] = result.error
            if result.raw_text:
                inspection["raw_text"] = result.raw_text[:5000]

        annotations: dict[int, list[dict[str, Any]]] = {}
        if result.success:
            annotations = build_risk_annotations(
                temporary_paths,
                filenames,
                list((result.data or {}).get("risks") or []),
            )
        markdown = render_single_report(inspection, filenames, annotations)
        return JSONResponse({
            "inspection": inspection,
            "report": {
                "markdown": markdown,
                "html": render_markdown_html(markdown),
                "filename": f"inspection_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            },
        })
    except ProviderError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        for path in temporary_paths:
            path.unlink(missing_ok=True)


@app.post("/api/reports/export")
async def export_report(
    content: str = Form(...),
    format: str = Form("md"),
    filename: str = Form("inspection_report"),
) -> Response:
    """将当前页面中的报告导出为 Markdown 或 PDF，不保存历史记录。"""
    if len(content.encode("utf-8")) > 30 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="报告内容超过 30MB")
    safe_name = re.sub(r"[^A-Za-z0-9_-]+", "_", filename).strip("_")[:80] or "inspection_report"
    if format == "md":
        return Response(
            content.encode("utf-8"),
            media_type="text/markdown; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{safe_name}.md"'},
        )
    if format == "pdf":
        try:
            pdf = render_pdf(content)
        except ImportError as exc:
            raise HTTPException(status_code=503, detail="PDF 组件未安装，请执行 pip install -r requirements.txt") from exc
        return Response(
            pdf,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{safe_name}.pdf"'},
        )
    raise HTTPException(status_code=400, detail="format 仅支持 md 或 pdf")


def main() -> None:
    import uvicorn

    print("AI 视觉室内巡检: http://localhost:8000/demo/index.html")
    print("API 文档: http://localhost:8000/docs")
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
