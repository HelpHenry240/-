"""报告渲染公共接口。"""

from .annotations import build_risk_annotations
from .render import render_markdown_html, render_pdf, render_single_report

__all__ = ["build_risk_annotations", "render_single_report", "render_markdown_html", "render_pdf"]
