#!/usr/bin/env python3
"""
Split raw YOLO dataset into train/valid folders.

Default workflow:
1. Read paired files from datasets/raw/images and datasets/raw/labels
2. Randomly split by --val-ratio
3. Move pairs into datasets/yolo_dataset/train|valid

Example:
        python datasets/scripts/split_dataset.py --val-ratio 0.2 --seed 42
"""

from __future__ import annotations

import argparse
import random
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


@dataclass(frozen=True)
class Pair:
    """A matched image/label pair with a relative path under source roots."""

    image: Path
    label: Path
    rel_image: Path
    rel_label: Path


def _scan_pairs(images_root: Path, labels_root: Path) -> tuple[list[Pair], list[Path]]:
    """Find image-label pairs recursively by matching relative stem path."""
    pairs: list[Pair] = []
    missing_labels: list[Path] = []

    for image_path in images_root.rglob("*"):
        if not image_path.is_file():
            continue
        if image_path.suffix.lower() not in IMAGE_EXTS:
            continue

        rel_image = image_path.relative_to(images_root)
        rel_stem = rel_image.with_suffix("")
        rel_label = rel_stem.with_suffix(".txt")
        label_path = labels_root / rel_label

        if not label_path.exists():
            missing_labels.append(rel_image)
            continue

        pairs.append(
            Pair(
                image=image_path,
                label=label_path,
                rel_image=rel_image,
                rel_label=rel_label,
            )
        )

    return pairs, missing_labels


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _transfer(src: Path, dst: Path, mode: str, overwrite: bool) -> None:
    if dst.exists():
        if overwrite:
            dst.unlink()
        else:
            raise FileExistsError(
                f"Destination exists: {dst}. Use --overwrite to replace existing files."
            )

    _ensure_parent(dst)
    if mode == "move":
        shutil.move(str(src), str(dst))
    else:
        shutil.copy2(src, dst)


def _split_pairs(
    pairs: list[Pair], val_ratio: float, seed: int
) -> tuple[list[Pair], list[Pair]]:
    if not pairs:
        return [], []

    rng = random.Random(seed)
    shuffled = pairs[:]
    rng.shuffle(shuffled)

    val_count = int(len(shuffled) * val_ratio)
    val_pairs = shuffled[:val_count]
    train_pairs = shuffled[val_count:]
    return train_pairs, val_pairs


def _iter_targets(
    pairs: Iterable[Pair],
    dataset_root: Path,
    split_name: str,
) -> Iterable[tuple[Path, Path]]:
    for pair in pairs:
        img_dst = dataset_root / split_name / "images" / pair.rel_image
        lbl_dst = dataset_root / split_name / "labels" / pair.rel_label
        yield pair.image, img_dst
        yield pair.label, lbl_dst


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Split datasets/raw into datasets/yolo_dataset/train|valid"
    )
    parser.add_argument(
        "--src",
        type=Path,
        default=Path("datasets/raw"),
        help="Source root containing images/ and labels/ (default: datasets/raw)",
    )
    parser.add_argument(
        "--dst",
        type=Path,
        default=Path("datasets/yolo_dataset"),
        help="Destination YOLO dataset root (default: datasets/yolo_dataset)",
    )
    parser.add_argument(
        "--images-subdir",
        type=str,
        default="images",
        help="Images subdirectory under source root (default: images)",
    )
    parser.add_argument(
        "--labels-subdir",
        type=str,
        default="labels",
        help="Labels subdirectory under source root (default: labels)",
    )
    parser.add_argument(
        "--val-ratio",
        type=float,
        default=0.2,
        help="Validation ratio between 0 and 1 (default: 0.2)",
    )
    parser.add_argument(
        "--seed", type=int, default=42, help="Random seed (default: 42)"
    )
    parser.add_argument(
        "--mode",
        choices=["move", "copy"],
        default="move",
        help="Transfer mode for paired files (default: move)",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing destination files",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview split results without moving/copying files",
    )
    args = parser.parse_args()

    if not (0.0 <= args.val_ratio <= 1.0):
        raise ValueError("--val-ratio must be in range [0, 1]")

    src = args.src
    dst = args.dst
    images_root = src / args.images_subdir
    labels_root = src / args.labels_subdir

    if not images_root.exists() or not images_root.is_dir():
        raise FileNotFoundError(f"Images directory not found: {images_root}")
    if not labels_root.exists() or not labels_root.is_dir():
        raise FileNotFoundError(f"Labels directory not found: {labels_root}")

    pairs, missing_labels = _scan_pairs(images_root, labels_root)
    train_pairs, val_pairs = _split_pairs(pairs, args.val_ratio, args.seed)

    print(f"[Info] Source images: {images_root}")
    print(f"[Info] Source labels: {labels_root}")
    print(f"[Info] Destination:   {dst}")
    print(f"[Info] Found pairs:   {len(pairs)}")
    print(f"[Info] Missing label: {len(missing_labels)}")
    print(f"[Info] Train pairs:   {len(train_pairs)}")
    print(f"[Info] Valid pairs:   {len(val_pairs)}")
    print(f"[Info] Mode:          {args.mode}")
    print(f"[Info] Dry run:       {args.dry_run}")

    if not pairs:
        print("[Warn] No valid image-label pairs found. Nothing to do.")
        return 0

    if missing_labels:
        print("[Warn] Example images without labels:")
        for rel in missing_labels[:10]:
            print(f"  - {rel}")
        if len(missing_labels) > 10:
            print(f"  ... and {len(missing_labels) - 10} more")

    if args.dry_run:
        return 0

    transferred = 0
    for src_path, dst_path in _iter_targets(train_pairs, dst, "train"):
        _transfer(src_path, dst_path, args.mode, args.overwrite)
        transferred += 1
    for src_path, dst_path in _iter_targets(val_pairs, dst, "valid"):
        _transfer(src_path, dst_path, args.mode, args.overwrite)
        transferred += 1

    print(f"[Done] Transferred files: {transferred}")
    print("[Done] Dataset split completed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
