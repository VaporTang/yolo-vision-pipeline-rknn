#!/usr/bin/env python3
"""
Merge a YOLO train/valid dataset back into a raw image/label layout.

Default workflow:
1. Read paired files from datasets/yolo_dataset/train and datasets/yolo_dataset/valid
2. Recreate the original relative layout under datasets/raw/images and datasets/raw/labels
3. Copy or move the paired files back into raw

Example:
    python datasets/scripts/merge_dataset.py --src datasets/yolo_dataset --dst datasets/raw --dry-run
"""

from __future__ import annotations

import argparse
from collections import defaultdict
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
SPLITS = ("train", "valid")


@dataclass(frozen=True)
class Pair:
    """A matched image/label pair under a split folder."""

    image: Path
    label: Path
    rel_image: Path
    rel_label: Path


def _scan_pairs(split_root: Path) -> tuple[list[Pair], list[Path]]:
    """Find image-label pairs recursively under one split folder."""
    images_root = split_root / "images"
    labels_root = split_root / "labels"
    pairs: list[Pair] = []
    missing_labels: list[Path] = []

    if not images_root.exists() or not labels_root.exists():
        return pairs, missing_labels

    for image_path in images_root.rglob("*"):
        if not image_path.is_file():
            continue
        if image_path.suffix.lower() not in IMAGE_EXTS:
            continue

        rel_image = image_path.relative_to(images_root)
        rel_label = rel_image.with_suffix(".txt")
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


def _iter_targets(
    pairs: Iterable[Pair],
    dataset_root: Path,
) -> Iterable[tuple[Path, Path]]:
    for pair in pairs:
        img_dst = dataset_root / "images" / pair.rel_image
        lbl_dst = dataset_root / "labels" / pair.rel_label
        yield pair.image, img_dst
        yield pair.label, lbl_dst


def _preflight_targets(
    targets: list[tuple[Path, Path]], overwrite: bool
) -> tuple[list[tuple[Path, list[Path]]], list[Path]]:
    """Detect destination collisions before any files are moved."""
    by_target: dict[Path, list[Path]] = defaultdict(list)
    existing_conflicts: list[Path] = []

    for src_path, dst_path in targets:
        by_target[dst_path].append(src_path)
        if not overwrite and dst_path.exists():
            existing_conflicts.append(dst_path)

    duplicate_targets = [
        (dst_path, src_paths)
        for dst_path, src_paths in by_target.items()
        if len(src_paths) > 1
    ]

    # Normalize existing conflicts so they are reported once and in a stable order.
    existing_conflicts = sorted(set(existing_conflicts))

    return duplicate_targets, existing_conflicts


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Merge datasets/yolo_dataset/train|valid back into datasets/raw"
    )
    parser.add_argument(
        "--src",
        type=Path,
        default=Path("datasets/yolo_dataset"),
        help="Source YOLO dataset root (default: datasets/yolo_dataset)",
    )
    parser.add_argument(
        "--dst",
        type=Path,
        default=Path("datasets/raw"),
        help="Destination raw dataset root (default: datasets/raw)",
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
        help="Preview merge results without moving/copying files",
    )
    args = parser.parse_args()

    src = args.src
    dst = args.dst

    if not src.exists() or not src.is_dir():
        raise FileNotFoundError(f"Source directory not found: {src}")

    all_pairs: list[Pair] = []
    missing_labels: list[Path] = []
    missing_splits: list[str] = []

    for split_name in SPLITS:
        split_root = src / split_name
        if not split_root.exists() or not split_root.is_dir():
            missing_splits.append(split_name)
            continue

        pairs, split_missing = _scan_pairs(split_root)
        all_pairs.extend(pairs)
        missing_labels.extend([Path(split_name) / rel for rel in split_missing])

    print(f"[Info] Source:      {src}")
    print(f"[Info] Destination: {dst}")
    print(f"[Info] Found pairs:  {len(all_pairs)}")
    print(f"[Info] Missing label: {len(missing_labels)}")
    print(f"[Info] Mode:         {args.mode}")
    print(f"[Info] Dry run:      {args.dry_run}")

    if missing_splits:
        print(f"[Warn] Missing split folders: {', '.join(missing_splits)}")

    if not all_pairs:
        print("[Warn] No valid image-label pairs found. Nothing to do.")
        return 0

    if missing_labels:
        print("[Warn] Example images without labels:")
        for rel in missing_labels[:10]:
            print(f"  - {rel}")
        if len(missing_labels) > 10:
            print(f"  ... and {len(missing_labels) - 10} more")

    targets = list(_iter_targets(all_pairs, dst))
    duplicate_targets, existing_conflicts = _preflight_targets(targets, args.overwrite)

    if duplicate_targets:
        print("[Error] Conflicting destination paths were detected before transfer:")
        for dst_path, src_paths in duplicate_targets[:10]:
            print(f"  - {dst_path}")
            for src_path in src_paths:
                print(f"      from {src_path}")
        if len(duplicate_targets) > 10:
            print(f"  ... and {len(duplicate_targets) - 10} more")
        return 1

    if existing_conflicts:
        print("[Error] Destination files already exist:")
        for dst_path in existing_conflicts[:10]:
            print(f"  - {dst_path}")
        if len(existing_conflicts) > 10:
            print(f"  ... and {len(existing_conflicts) - 10} more")
        print(
            "[Hint] Re-run with --overwrite, or move the existing destination files aside."
        )
        return 1

    if args.dry_run:
        return 0

    transferred = 0
    for src_path, dst_path in targets:
        _transfer(src_path, dst_path, args.mode, args.overwrite)
        transferred += 1

    print(f"[Done] Transferred files: {transferred}")
    print("[Done] Dataset merge completed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
