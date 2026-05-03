#!/usr/bin/env python3
"""
Dataset utility functions for YOLO data preparation.
Includes functions for train/val split, class filtering, etc.
"""

import os
import json
import shutil
from pathlib import Path
from typing import List, Tuple, Set
import random


def calculate_iou(box1: List[float], box2: List[float]) -> float:
    """
    Calculate Intersection over Union (IoU) for two bounding boxes.

    Args:
        box1: [xmin, ymin, xmax, ymax]
        box2: [xmin, ymin, xmax, ymax]

    Returns:
        IoU value between 0 and 1
    """
    x1 = max(box1[0], box2[0])
    y1 = max(box1[1], box2[1])
    x2 = min(box1[2], box2[2])
    y2 = min(box1[3], box2[3])

    inter_area = max(0, x2 - x1) * max(0, y2 - y1)

    area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
    area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])

    union_area = area1 + area2 - inter_area
    if union_area == 0:
        return 0
    return inter_area / union_area


def check_overlapping_boxes(json_dir: str, iou_threshold: float = 0.8) -> int:
    """
    Check for overlapping bounding boxes in JSON annotation files.

    Args:
        json_dir: Directory containing JSON annotation files
        iou_threshold: IoU threshold for considering boxes as overlapping

    Returns:
        Number of files with overlapping boxes
    """
    print(f"Checking directory: {json_dir}")
    print(f"IoU threshold: {iou_threshold}\n")

    problematic_files = 0

    for filename in os.listdir(json_dir):
        if not filename.endswith(".json"):
            continue

        json_path = os.path.join(json_dir, filename)
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"Warning: Could not read {filename}: {e}")
            continue

        shapes = data.get("shapes", [])
        if len(shapes) < 2:
            continue

        # Extract all boxes
        boxes = []
        for shape in shapes:
            points = shape.get("points", [])
            if not points:
                continue
            x_coords = [p[0] for p in points]
            y_coords = [p[1] for p in points]
            boxes.append(
                {
                    "label": shape.get("label", "unknown"),
                    "bbox": [
                        min(x_coords),
                        min(y_coords),
                        max(x_coords),
                        max(y_coords),
                    ],
                }
            )

        # Check for overlaps
        found_overlap = False
        for i in range(len(boxes)):
            for j in range(i + 1, len(boxes)):
                iou = calculate_iou(boxes[i]["bbox"], boxes[j]["bbox"])

                if iou > iou_threshold:
                    if not found_overlap:
                        print(f"--- File with overlaps: {filename} ---")
                        found_overlap = True

                    print(
                        f"  [Overlap] Label1: '{boxes[i]['label']}' vs Label2: '{boxes[j]['label']}'"
                    )
                    print(f"  IoU: {iou:.4f}")

        if found_overlap:
            problematic_files += 1
            print("")

    print(f"Check completed! Found {problematic_files} files with overlaps.")
    return problematic_files


def split_train_val(
    image_dir: str, label_dir: str, val_ratio: float = 0.2, seed: int = 42
) -> Tuple[int, int]:
    """
    Split paired image and label files into train and validation sets.

    Args:
        image_dir: Directory containing training images
        label_dir: Directory containing training labels
        val_ratio: Ratio of validation data (default 0.2 = 20%)
        seed: Random seed for reproducibility

    Returns:
        Tuple of (num_train, num_val)
    """
    image_path = Path(image_dir)
    label_path = Path(label_dir)
    val_img_dir = image_path.parent / "valid" / "images"
    val_lbl_dir = label_path.parent / "valid" / "labels"

    # Create valid directories
    val_img_dir.mkdir(parents=True, exist_ok=True)
    val_lbl_dir.mkdir(parents=True, exist_ok=True)

    print(f"Finding image-label pairs in:")
    print(f"  Images: {image_dir}")
    print(f"  Labels: {label_dir}\n")

    # Find paired data
    paired_data = []
    for ext in ["*.jpg", "*.png", "*.jpeg"]:
        for img_path in image_path.glob(ext):
            lbl_path = label_path / f"{img_path.stem}.txt"
            if lbl_path.exists():
                paired_data.append((img_path, lbl_path))

    total = len(paired_data)
    print(f"Found {total} image-label pairs\n")

    # Shuffle and split
    random.seed(seed)
    random.shuffle(paired_data)

    val_size = int(total * val_ratio)
    val_data = paired_data[:val_size]

    # Move validation files
    for img_path, lbl_path in val_data:
        shutil.move(str(img_path), str(val_img_dir / img_path.name))
        shutil.move(str(lbl_path), str(val_lbl_dir / lbl_path.name))

    print(f"Split completed!")
    print(f"  Train: {total - val_size} samples")
    print(f"  Valid: {val_size} samples")

    return total - val_size, val_size


def filter_classes(label_dirs: List[str], classes_to_remove: Set[int]) -> int:
    """
    Remove specified classes from label files.

    Args:
        label_dirs: List of directories containing label files
        classes_to_remove: Set of class indices to remove

    Returns:
        Number of files processed
    """
    count = 0
    for label_dir in label_dirs:
        if not os.path.exists(label_dir):
            print(f"Warning: Directory not found: {label_dir}")
            continue

        for filename in os.listdir(label_dir):
            if not filename.endswith(".txt"):
                continue

            filepath = os.path.join(label_dir, filename)

            with open(filepath, "r") as f:
                lines = f.readlines()

            # Keep only lines whose class index is not in classes_to_remove
            new_lines = [
                line
                for line in lines
                if line.strip() and int(line.split()[0]) not in classes_to_remove
            ]

            with open(filepath, "w") as f:
                f.writelines(new_lines)

            count += 1

    print(f"Processed {count} label files")
    return count


def prepare_calibration_dataset(
    image_dir: str, output_file: str, num_images: int = 20
) -> None:
    """
    Prepare a calibration dataset list for RKNN quantization.

    Args:
        image_dir: Directory containing calibration images (supports recursive search)
        output_file: Output file path for dataset.txt
        num_images: Number of images to use (randomly selected)
    """
    image_path = Path(image_dir)

    if not image_path.exists():
        print(f"Error: Image directory not found: {image_dir}")
        return

    # Recursively search for images in all subdirectories
    images = []
    for ext in ["*.jpg", "*.JPG", "*.png", "*.PNG", "*.jpeg", "*.JPEG"]:
        images.extend(image_path.glob(f"**/{ext}"))

    if len(images) == 0:
        print(f"Warning: No images found in {image_dir} or its subdirectories")
        # Try to provide helpful suggestions
        subdirs = [d for d in image_path.iterdir() if d.is_dir()]
        if subdirs:
            print(f"Available subdirectories: {', '.join([d.name for d in subdirs])}")
            print(f"Tip: Try specifying one of these subdirectories directly")
        return

    print(f"Found {len(images)} images in {image_dir}")

    # Randomly select images
    random.seed(42)
    selected = random.sample(images, min(num_images, len(images)))

    # Write to file
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        for img in selected:
            f.write(f"{img.resolve()}\n")

    print(f"Created calibration dataset with {len(selected)} images")
    print(f"Saved to: {output_file}")

    print(f"Created calibration dataset with {len(selected)} images")
    print(f"Saved to: {output_file}")


if __name__ == "__main__":
    # Example usage
    print("Dataset utilities module. Import and use the functions as needed.")
