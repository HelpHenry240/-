"""根据模型 bbox 在巡检图片上绘制风险标注。"""

from __future__ import annotations

import base64
from io import BytesIO
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont, ImageOps


MAX_RENDER_EDGE = 1400
LEVEL_COLORS = {
    "高": (190, 45, 38),
    "中": (190, 105, 8),
    "低": (18, 126, 105),
}


def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        Path("C:/Windows/Fonts/msyh.ttc"),
        Path("C:/Windows/Fonts/simhei.ttf"),
        Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
        Path("/System/Library/Fonts/PingFang.ttc"),
    ]
    for candidate in candidates:
        if candidate.exists():
            try:
                return ImageFont.truetype(str(candidate), size=size, index=0)
            except (OSError, ValueError):
                continue
    return ImageFont.load_default()


def _risk_view_index(risk: dict[str, Any], image_count: int) -> int | None:
    primary = risk.get("primary_view_index")
    if isinstance(primary, int) and 1 <= primary <= image_count:
        return primary
    views = risk.get("view_indices") or []
    if len(views) == 1 and isinstance(views[0], int) and 1 <= views[0] <= image_count:
        return views[0]
    if image_count == 1:
        return 1
    return None


def _valid_bbox(value: Any) -> list[float] | None:
    if not isinstance(value, list) or len(value) != 4:
        return None
    if any(not isinstance(item, (int, float)) for item in value):
        return None
    x, y, width, height = (max(0.0, min(1.0, float(item))) for item in value)
    if width <= 0 or height <= 0 or x >= 1 or y >= 1:
        return None
    width = min(width, 1 - x)
    height = min(height, 1 - y)
    return [x, y, width, height]


def _annotate_image(path: Path, bbox: list[float], label: str, color: tuple[int, int, int]) -> str:
    with Image.open(path) as source:
        image = ImageOps.exif_transpose(source).convert("RGB")
    if max(image.size) > MAX_RENDER_EDGE:
        image.thumbnail((MAX_RENDER_EDGE, MAX_RENDER_EDGE), Image.Resampling.LANCZOS)

    image_width, image_height = image.size
    x, y, width, height = bbox
    left = max(0, min(image_width - 1, round(x * image_width)))
    top = max(0, min(image_height - 1, round(y * image_height)))
    right = max(left + 1, min(image_width, round((x + width) * image_width)))
    bottom = max(top + 1, min(image_height, round((y + height) * image_height)))

    draw = ImageDraw.Draw(image)
    stroke = max(3, round(max(image_width, image_height) / 350))
    draw.rectangle((left, top, right, bottom), outline=color, width=stroke)

    font = _load_font(max(15, min(28, round(image_width / 45))))
    try:
        text_box = draw.textbbox((0, 0), label, font=font, stroke_width=0)
    except UnicodeEncodeError:
        label = "Risk"
        text_box = draw.textbbox((0, 0), label, font=font, stroke_width=0)
    padding = max(5, stroke * 2)
    label_width = text_box[2] - text_box[0] + padding * 2
    label_height = text_box[3] - text_box[1] + padding * 2
    label_left = min(left, max(0, image_width - label_width))
    label_top = top - label_height if top >= label_height else min(image_height - label_height, bottom)
    draw.rectangle(
        (label_left, label_top, label_left + label_width, label_top + label_height),
        fill=color,
    )
    draw.text(
        (label_left + padding, label_top + padding - text_box[1]),
        label,
        fill="white",
        font=font,
    )

    output = BytesIO()
    image.save(output, format="JPEG", quality=82, optimize=True)
    encoded = base64.b64encode(output.getvalue()).decode("ascii")
    return f"data:image/jpeg;base64,{encoded}"


def build_risk_annotations(
    image_paths: list[Path],
    filenames: list[str],
    risks: list[dict[str, Any]],
) -> dict[int, list[dict[str, Any]]]:
    """按风险序号生成报告可嵌入的标注图片。"""
    annotations: dict[int, list[dict[str, Any]]] = {}
    for risk_index, risk in enumerate(risks):
        bbox = _valid_bbox(risk.get("bbox"))
        view_index = _risk_view_index(risk, len(image_paths))
        if bbox is None or view_index is None:
            continue
        risk_name = str(risk.get("risk_name") or risk.get("risk_type") or "风险")
        level = str(risk.get("level") or "未知")
        label = f"风险 {risk_index + 1}｜{risk_name}｜{level}"
        try:
            data_url = _annotate_image(
                image_paths[view_index - 1],
                bbox,
                label,
                LEVEL_COLORS.get(level, (43, 76, 99)),
            )
        except (OSError, ValueError):
            continue
        annotations.setdefault(risk_index, []).append({
            "view_index": view_index,
            "filename": filenames[view_index - 1],
            "data_url": data_url,
            "alt": f"{risk_name}风险区域标注，视角 {view_index}",
        })
    return annotations
