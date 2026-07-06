"""数据集加载器。

支持三种数据源：
1. demo 内置场景（从 demo/data/scenes.json 加载）
2. 文件夹导入（扫描目录下的图片，可选关联标注 JSON）
3. 标准 JSON 标注文件（符合 SampleSchema）
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .schema import SampleSchema, MediaItem, GroundTruth


# 支持的图片扩展名
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".svg", ".bmp", ".gif"}


def load_demo_scenes(demo_root: Path | None = None) -> list[SampleSchema]:
    """加载 demo 内置的 12 个场景。

    将 demo 的 scenes.json 格式转换为标准 SampleSchema。
    """
    if demo_root is None:
        demo_root = Path(__file__).resolve().parents[2] / "demo"

    scenes_path = demo_root / "data" / "scenes.json"
    if not scenes_path.exists():
        return []

    raw_scenes = json.loads(scenes_path.read_text(encoding="utf-8"))
    samples: list[SampleSchema] = []

    for raw in raw_scenes:
        media = [MediaItem(
            type="image",
            path=str(demo_root / raw.get("image", "")),
            view="front",
        )]
        gt = [GroundTruth(
            risk_type=g.get("type", ""),
            risk_name=g.get("type", ""),
            objects=g.get("objects", []),
            location=g.get("location", ""),
            bbox=g.get("bbox"),
            level=g.get("level", ""),
            reason=g.get("reason", ""),
            suggestion=g.get("suggestion", ""),
        ) for g in raw.get("ground_truth", [])]

        sample = SampleSchema(
            sample_id=raw.get("id", ""),
            dataset="demo",
            scene_type=raw.get("scene_type", ""),
            title=raw.get("title", ""),
            summary=raw.get("summary", ""),
            media=media,
            objects=raw.get("objects", []),
            ground_truth=gt,
            metadata={"source": "demo"},
        )
        samples.append(sample)

    return samples


def load_from_folder(
    folder: Path,
    annotations_path: Path | None = None,
    dataset_name: str = "custom",
) -> list[SampleSchema]:
    """从文件夹加载图片作为数据集。

    Args:
        folder: 包含图片的文件夹路径。
        annotations_path: 可选的标注 JSON 文件路径。
            如果提供，应为 list[dict]，每个 dict 至少包含 sample_id 和 image 字段。
        dataset_name: 数据集名称。

    Returns:
        样本列表。
    """
    folder = Path(folder)
    if not folder.exists():
        return []

    # 加载标注（如果有）
    annotations: dict[str, dict] = {}
    if annotations_path and annotations_path.exists():
        raw_anns = json.loads(annotations_path.read_text(encoding="utf-8"))
        for ann in raw_anns:
            key = ann.get("sample_id", ann.get("id", ""))
            if key:
                annotations[key] = ann

    samples: list[SampleSchema] = []
    image_files = sorted([
        f for f in folder.iterdir()
        if f.suffix.lower() in IMAGE_EXTENSIONS and f.is_file()
    ])

    for i, img_file in enumerate(image_files):
        sample_id = img_file.stem
        ann = annotations.get(sample_id, {})

        media = [MediaItem(type="image", path=str(img_file), view="front")]
        gt = [GroundTruth(
            risk_type=g.get("type", g.get("risk_type", "")),
            risk_name=g.get("type", g.get("risk_name", "")),
            objects=g.get("objects", []),
            location=g.get("location", ""),
            bbox=g.get("bbox"),
            level=g.get("level", ""),
            reason=g.get("reason", ""),
            suggestion=g.get("suggestion", ""),
        ) for g in ann.get("ground_truth", [])]

        sample = SampleSchema(
            sample_id=ann.get("sample_id", sample_id),
            dataset=dataset_name,
            scene_type=ann.get("scene_type", ""),
            title=ann.get("title", img_file.stem),
            summary=ann.get("summary", ""),
            media=media,
            objects=ann.get("objects", []),
            ground_truth=gt,
            metadata={"source": "folder_import", "filename": img_file.name},
        )
        samples.append(sample)

    return samples


def load_dataset(path: Path | str) -> list[SampleSchema]:
    """通用数据集加载入口。

    Args:
        path: 数据集路径。
            - 如果是 "demo"，加载 demo 内置场景。
            - 如果是文件夹，扫描图片并尝试加载同目录的 annotations.json。
            - 如果是 .json 文件，加载标准格式。

    Returns:
        样本列表。
    """
    if isinstance(path, str) and path == "demo":
        return load_demo_scenes()

    p = Path(path)
    if p.is_dir():
        ann_path = p / "annotations.json"
        return load_from_folder(p, ann_path if ann_path.exists() else None)
    elif p.is_file() and p.suffix == ".json":
        raw = json.loads(p.read_text(encoding="utf-8"))
        if isinstance(raw, list):
            return [SampleSchema.from_dict(item) for item in raw]
        elif isinstance(raw, dict) and "samples" in raw:
            return [SampleSchema.from_dict(item) for item in raw["samples"]]
    return []


def list_datasets() -> list[dict[str, Any]]:
    """列出可用的数据集。"""
    root = Path(__file__).resolve().parents[2]
    datasets_dir = root / "datasets"

    result = [{"name": "demo", "description": "内置 12 个虚拟室内场景", "sample_count": len(load_demo_scenes())}]

    if datasets_dir.exists():
        for d in sorted(datasets_dir.iterdir()):
            if d.is_dir() and not d.name.startswith("."):
                images = [f for f in d.iterdir() if f.suffix.lower() in IMAGE_EXTENSIONS and f.is_file()]
                result.append({
                    "name": d.name,
                    "path": str(d),
                    "sample_count": len(images),
                    "has_annotations": (d / "annotations.json").exists(),
                })

    return result
