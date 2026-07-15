"""单次巡检报告的 Markdown、HTML 与 PDF 渲染。"""

from __future__ import annotations

import base64
import binascii
import html
import re
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any


IMAGE_PATTERN = re.compile(
    r"^!\[([^\]]*)\]\((data:image/(?:jpeg|png|webp);base64,[A-Za-z0-9+/=]+)\)$"
)


def render_single_report(
    inspection: dict[str, Any],
    image_filenames: list[str] | None = None,
    risk_annotations: dict[int, list[dict[str, Any]]] | None = None,
) -> str:
    data = inspection.get("data") or {}
    risks = data.get("risks") or []
    risk_annotations = risk_annotations or {}
    lines = [
        "# 室内安全巡检报告",
        "",
        f"**巡检时间：** {inspection.get('timestamp', datetime.now().isoformat(timespec='seconds'))}",
        f"**模型服务：** {inspection.get('provider', '')}",
        f"**模型名称：** {inspection.get('model', '')}",
        f"**Prompt：** {inspection.get('prompt_id', '')}",
        f"**输入图片：** {', '.join(image_filenames or inspection.get('filenames') or [])}",
        "",
        "---",
        "",
        "## 巡检结论",
        "",
    ]
    if not inspection.get("success"):
        lines.extend(["> 巡检调用失败。", "", f"**错误信息：** {inspection.get('error', '未知错误')}"])
        return "\n".join(lines)

    if data.get("has_risk") and risks:
        levels: dict[str, int] = {}
        for risk in risks:
            level = str(risk.get("level", "未知"))
            levels[level] = levels.get(level, 0) + 1
        summary = "、".join(f"{level}风险 {count} 项" for level, count in levels.items())
        lines.append(f"发现 **{len(risks)}** 项安全风险：{summary}。")
    else:
        lines.append("本次图像中未发现有充分视觉证据支持的安全风险。")
    lines.extend(["", f"- 证据充分性：{data.get('evidence_sufficiency', '未说明')}"])
    uncertain = data.get("uncertain_points") or []
    if uncertain:
        lines.append(f"- 不确定点：{'；'.join(map(str, uncertain))}")

    if risks:
        lines.extend(["", "## 风险明细", ""])
        for index, risk in enumerate(risks, 1):
            risk_name = risk.get("risk_name") or risk.get("type") or risk.get("risk_type") or "未命名风险"
            lines.extend([
                f"### {index}. {risk_name}（{risk.get('level', '未知')}）",
                "",
                f"- 规则编号：{risk.get('rule_id', '未提供')}",
                f"- 相关物体：{', '.join(map(str, risk.get('objects') or [])) or '未说明'}",
                f"- 风险位置：{risk.get('location', '未说明')}",
                f"- 判断依据：{risk.get('reason', '未说明')}",
                f"- 整改建议：{risk.get('suggestion', '未说明')}",
                "",
            ])
            annotations = risk_annotations.get(index - 1, [])
            for annotation in annotations:
                lines.extend([
                    f"**风险区域标注：** 视角 {annotation['view_index']} · {annotation['filename']}",
                    "",
                    f"![{annotation['alt']}]({annotation['data_url']})",
                    "",
                ])
            if risk.get("bbox") is None:
                lines.extend(["> 模型未提供可靠定位框，本项风险不绘制区域标注。", ""])

    lines.extend([
        "",
        "---",
        "",
        "*本报告由 AI 视觉室内巡检系统自动生成，结论应由现场负责人复核。*",
    ])
    return "\n".join(lines)


def _inline_markdown(value: str) -> str:
    escaped = html.escape(value)
    escaped = re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)
    escaped = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", escaped)
    return escaped


def render_markdown_html(markdown: str) -> str:
    """渲染项目报告使用到的 Markdown 子集，输出已转义 HTML。"""
    output: list[str] = []
    in_code = False
    in_list = False
    for raw_line in markdown.splitlines():
        line = raw_line.rstrip()
        if line.startswith("```"):
            if in_list:
                output.append("</ul>")
                in_list = False
            output.append("</code></pre>" if in_code else "<pre><code>")
            in_code = not in_code
            continue
        if in_code:
            output.append(html.escape(line) + "\n")
            continue
        if line.startswith("- "):
            if not in_list:
                output.append("<ul>")
                in_list = True
            output.append(f"<li>{_inline_markdown(line[2:])}</li>")
            continue
        if in_list:
            output.append("</ul>")
            in_list = False
        if not line:
            continue
        image_match = IMAGE_PATTERN.match(line)
        if image_match:
            alt, data_url = image_match.groups()
            output.append(
                '<figure class="risk-annotation">'
                f'<img src="{data_url}" alt="{html.escape(alt, quote=True)}" loading="lazy">'
                "</figure>"
            )
        elif line == "---":
            output.append("<hr>")
        elif line.startswith("### "):
            output.append(f"<h3>{_inline_markdown(line[4:])}</h3>")
        elif line.startswith("## "):
            output.append(f"<h2>{_inline_markdown(line[3:])}</h2>")
        elif line.startswith("# "):
            output.append(f"<h1>{_inline_markdown(line[2:])}</h1>")
        elif line.startswith("> "):
            output.append(f"<blockquote>{_inline_markdown(line[2:])}</blockquote>")
        else:
            output.append(f"<p>{_inline_markdown(line)}</p>")
    if in_list:
        output.append("</ul>")
    if in_code:
        output.append("</code></pre>")
    return "\n".join(output)


def render_pdf(markdown: str) -> bytes:
    """将报告 Markdown 转为 PDF；优先使用系统中文字体。"""
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import Image as ReportImage
    from reportlab.platypus import PageBreak, Paragraph, Preformatted, SimpleDocTemplate, Spacer

    font_name = "Helvetica"
    font_candidates = [
        Path("C:/Windows/Fonts/msyh.ttc"),
        Path("C:/Windows/Fonts/simhei.ttf"),
        Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
        Path("/System/Library/Fonts/PingFang.ttc"),
    ]
    for candidate in font_candidates:
        if candidate.exists():
            try:
                pdfmetrics.registerFont(TTFont("ReportCJK", str(candidate), subfontIndex=0))
                pdfmetrics.registerFontFamily(
                    "ReportCJK",
                    normal="ReportCJK",
                    bold="ReportCJK",
                    italic="ReportCJK",
                    boldItalic="ReportCJK",
                )
                font_name = "ReportCJK"
                break
            except Exception:
                continue

    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title="室内安全巡检报告",
    )
    styles = getSampleStyleSheet()
    body = ParagraphStyle("BodyCJK", parent=styles["BodyText"], fontName=font_name, fontSize=10, leading=17)
    h1 = ParagraphStyle("H1CJK", parent=styles["Title"], fontName=font_name, fontSize=20, leading=28, alignment=TA_CENTER, spaceAfter=16)
    h2 = ParagraphStyle("H2CJK", parent=styles["Heading2"], fontName=font_name, fontSize=14, leading=21, spaceBefore=12, spaceAfter=8)
    h3 = ParagraphStyle("H3CJK", parent=styles["Heading3"], fontName=font_name, fontSize=11, leading=18, spaceBefore=8, spaceAfter=5)
    code = ParagraphStyle("CodeCJK", parent=body, fontName=font_name, fontSize=7, leading=10, leftIndent=6, backColor="#F1F5F9")
    story: list[Any] = []
    in_code = False
    code_lines: list[str] = []
    for raw_line in markdown.splitlines():
        line = raw_line.rstrip()
        if line.startswith("```"):
            if in_code:
                story.extend([Preformatted("\n".join(code_lines), code), Spacer(1, 6)])
                code_lines = []
            in_code = not in_code
            continue
        if in_code:
            code_lines.append(line)
        image_match = IMAGE_PATTERN.match(line)
        if image_match:
            encoded = image_match.group(2).split(",", 1)[1]
            try:
                report_image = ReportImage(BytesIO(base64.b64decode(encoded, validate=True)))
                max_width = 170 * mm
                max_height = 110 * mm
                scale = min(max_width / report_image.imageWidth, max_height / report_image.imageHeight, 1)
                report_image.drawWidth = report_image.imageWidth * scale
                report_image.drawHeight = report_image.imageHeight * scale
                story.extend([report_image, Spacer(1, 8)])
            except (binascii.Error, OSError, ValueError):
                story.append(Paragraph("[风险标注图片无法渲染]", body))
        elif line.startswith("# "):
            story.append(Paragraph(html.escape(line[2:]), h1))
        elif line.startswith("## "):
            story.append(Paragraph(html.escape(line[3:]), h2))
        elif line.startswith("### "):
            story.append(Paragraph(html.escape(line[4:]), h3))
        elif line == "---":
            story.append(Spacer(1, 8))
        elif line:
            cleaned = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", html.escape(line.lstrip("- ").removeprefix("> ")))
            cleaned = re.sub(r"\*([^*]+)\*", r"<i>\1</i>", cleaned)
            prefix = "• " if line.startswith("- ") else ""
            story.append(Paragraph(prefix + cleaned, body))
            story.append(Spacer(1, 3))
    if code_lines:
        story.append(Preformatted("\n".join(code_lines), code))
    if not story:
        story = [Paragraph("Empty report", body), PageBreak()]
    document.build(story)
    return buffer.getvalue()
