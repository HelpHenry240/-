from pathlib import Path

from PIL import Image

from src.datasets.schema import validate_model_output
from src.prompts import PromptBuilder
from src.reports import (
    build_risk_annotations,
    render_markdown_html,
    render_pdf,
    render_single_report,
)


def valid_output():
    return {
        "has_risk": True,
        "risks": [{
            "risk_type": "electric_shock",
            "risk_name": "触电风险",
            "rule_id": "electric_shock_001",
            "objects": ["水杯", "插座"],
            "location": "桌面右侧",
            "bbox": [0.1, 0.2, 0.3, 0.4],
            "view_indices": [1],
            "primary_view_index": 1,
            "level": "高",
            "reason": "液体紧邻插座",
            "suggestion": "立即移开水杯",
        }],
        "evidence_sufficiency": "充分",
        "uncertain_points": [],
    }


def test_prompt_injects_the_canonical_rules():
    prompt = PromptBuilder().build()
    assert "{{RISK_RULES_JSON}}" not in prompt
    assert "electric_shock_001" in prompt
    assert "gas_leak_001" in prompt


def test_validate_model_output_accepts_expected_schema():
    assert validate_model_output(valid_output()) == (True, "")


def test_validate_model_output_rejects_inconsistent_has_risk():
    output = valid_output()
    output["has_risk"] = False
    valid, message = validate_model_output(output)
    assert not valid
    assert "不一致" in message


def test_report_html_is_rendered_and_escaped():
    inspection = {
        "provider": "test",
        "model": "vision",
        "prompt_id": "indoor_safety_v1",
        "timestamp": "2026-07-15T10:00:00",
        "success": True,
        "valid": True,
        "data": valid_output(),
    }
    markdown = render_single_report(inspection, ["<scene>.png"])
    rendered = render_markdown_html(markdown)
    assert "<h1>室内安全巡检报告</h1>" in rendered
    assert "&lt;scene&gt;.png" in rendered
    assert "结构化" not in markdown
    assert "输出校验" not in markdown
    assert '"has_risk"' not in markdown
    assert "<script>" not in rendered


def test_risk_annotation_is_embedded_in_html_markdown_and_pdf(tmp_path: Path):
    first = tmp_path / "front.png"
    second = tmp_path / "side.png"
    Image.new("RGB", (320, 240), "white").save(first)
    Image.new("RGB", (320, 240), "#e5edf0").save(second)
    output = valid_output()
    output["risks"][0]["view_indices"] = [1, 2]
    output["risks"][0]["primary_view_index"] = 2

    annotations = build_risk_annotations(
        [first, second],
        ["front.png", "side.png"],
        output["risks"],
    )
    assert annotations[0][0]["view_index"] == 2
    assert annotations[0][0]["data_url"].startswith("data:image/jpeg;base64,")

    inspection = {
        "provider": "test",
        "model": "vision",
        "prompt_id": "indoor_safety_v1",
        "success": True,
        "valid": True,
        "data": output,
    }
    markdown = render_single_report(inspection, ["front.png", "side.png"], annotations)
    rendered = render_markdown_html(markdown)
    assert "风险区域标注" in markdown
    assert '<figure class="risk-annotation">' in rendered
    assert "data:image/jpeg;base64," in rendered
    assert render_pdf(markdown).startswith(b"%PDF")
