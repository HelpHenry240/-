from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DEFAULT_PROMPT = ROOT / "prompts" / "risk_inspection_prompt.md"


def image_to_data_url(path: Path) -> str:
    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    data = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{data}"


def extract_text(response: dict) -> str:
    if "output_text" in response:
        return str(response["output_text"])

    chunks: list[str] = []
    for item in response.get("output", []):
        for content in item.get("content", []):
            if "text" in content:
                chunks.append(str(content["text"]))
    return "\n".join(chunks).strip()


def call_openai_responses(image: Path, prompt: str, model: str, base_url: str, api_key: str) -> dict:
    payload = {
        "model": model,
        "input": [
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": prompt},
                    {"type": "input_image", "image_url": image_to_data_url(image)},
                ],
            }
        ],
    }

    url = base_url.rstrip("/") + "/responses"
    request = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    with urllib.request.urlopen(request, timeout=90) as result:
        raw = result.read().decode("utf-8")
    response = json.loads(raw)
    text = extract_text(response)
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        parsed = {"raw_text": text, "raw_response": response}
    return parsed


def mock_result(scene_id: str) -> dict:
    mock_path = ROOT / "data" / "mock_vlm_results.json"
    mock_data = json.loads(mock_path.read_text(encoding="utf-8"))
    return mock_data.get(scene_id, {"has_risk": False, "risks": [], "note": "No mock result for this scene."})


def main() -> int:
    parser = argparse.ArgumentParser(description="Call a vision-language model for indoor safety inspection.")
    parser.add_argument("--image", type=Path, help="Path to an input image. Prefer JPG or PNG for real VLM calls.")
    parser.add_argument("--prompt", type=Path, default=DEFAULT_PROMPT, help="Prompt markdown file.")
    parser.add_argument("--output", type=Path, help="Optional JSON output file.")
    parser.add_argument("--model", default=os.getenv("VLM_MODEL", "gpt-4.1-mini"), help="Vision model name.")
    parser.add_argument("--base-url", default=os.getenv("VLM_BASE_URL", "https://api.openai.com/v1"), help="API base URL.")
    parser.add_argument("--api-key", default=os.getenv("VLM_API_KEY") or os.getenv("OPENAI_API_KEY"), help="API key.")
    parser.add_argument("--mock-scene", help="Return the built-in mock result for a scene id, such as S02.")
    args = parser.parse_args()

    if args.mock_scene:
        result = mock_result(args.mock_scene)
    else:
        if not args.image:
            parser.error("--image is required unless --mock-scene is used")
        if not args.api_key:
            parser.error("Set VLM_API_KEY or OPENAI_API_KEY, or use --mock-scene")
        prompt = args.prompt.read_text(encoding="utf-8")
        result = call_openai_responses(args.image, prompt, args.model, args.base_url, args.api_key)

    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        print(f"HTTP error {exc.code}: {body}", file=sys.stderr)
        raise SystemExit(2)
    except urllib.error.URLError as exc:
        print(f"Network error: {exc}", file=sys.stderr)
        raise SystemExit(2)
