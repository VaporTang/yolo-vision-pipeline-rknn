#!/usr/bin/env python3
"""
Dataset processing scripts for common data preparation tasks.

Usage examples:
    python src/dataset_tools/check_overlaps.py
    python src/dataset_tools/split_dataset.py
    python src/dataset_tools/filter_classes.py
    python src/dataset_tools/prepare_calibration.py
"""

import argparse
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.dataset_utils import (
    check_overlapping_boxes,
    split_train_val,
    filter_classes,
    prepare_calibration_dataset,
)

try:
    from utils.path_manager import paths
except ImportError:
    paths = None  # Optional path manager


def check_overlaps():
    """Check for overlapping bounding boxes in annotations."""
    parser = argparse.ArgumentParser(description="Check for overlapping bounding boxes")
    parser.add_argument(
        "--json-dir",
        type=str,
        required=True,
        help="Directory with JSON annotation files",
    )
    parser.add_argument(
        "--threshold", type=float, default=0.8, help="IoU threshold (0-1)"
    )
    args = parser.parse_args()

    check_overlapping_boxes(args.json_dir, args.threshold)


def split_dataset():
    """Split dataset into train/validation sets."""
    parser = argparse.ArgumentParser(description="Split dataset into train/validation")
    parser.add_argument(
        "--image-dir", type=str, required=True, help="Training images directory"
    )
    parser.add_argument(
        "--label-dir", type=str, required=True, help="Training labels directory"
    )
    parser.add_argument(
        "--val-ratio", type=float, default=0.2, help="Validation ratio (default 0.2)"
    )
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    args = parser.parse_args()

    split_train_val(args.image_dir, args.label_dir, args.val_ratio, args.seed)


def filter_dataset_classes():
    """Remove specified classes from dataset."""
    parser = argparse.ArgumentParser(description="Filter classes from dataset")
    parser.add_argument(
        "--label-dirs", type=str, nargs="+", required=True, help="Label directories"
    )
    parser.add_argument(
        "--remove-classes",
        type=int,
        nargs="+",
        required=True,
        help="Class indices to remove",
    )
    args = parser.parse_args()

    filter_classes(args.label_dirs, set(args.remove_classes))


def prepare_calibration():
    """Prepare calibration dataset for quantization."""
    parser = argparse.ArgumentParser(
        description="Prepare calibration dataset for RKNN quantization",
        epilog="Example: python src/dataset_tools.py prepare_calibration --image-dir datasets/yolo_dataset/train/images --output datasets/calibration/dataset.txt",
    )
    parser.add_argument(
        "--image-dir",
        type=str,
        required=True,
        help="Calibration images directory (searches recursively)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="datasets/calibration/dataset.txt",
        help="Output dataset.txt file (default: datasets/calibration/dataset.txt)",
    )
    parser.add_argument(
        "--num-images",
        type=int,
        default=20,
        help="Number of images to use (default: 20)",
    )
    args = parser.parse_args()

    prepare_calibration_dataset(args.image_dir, args.output, args.num_images)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Available commands:")
        print("  check_overlaps      - Check for overlapping boxes")
        print("  split_dataset       - Split into train/validation")
        print("  filter_classes      - Remove specified classes")
        print("  prepare_calibration - Prepare calibration dataset")
        print("  show-paths          - Show path configuration")
        sys.exit(0)

    command = sys.argv[1]

    # Handle --show-paths at any position
    if command == "show-paths" or "--show-paths" in sys.argv:
        if paths:
            paths.print_config()
            sys.exit(0)
        else:
            print("Path manager not available")
            sys.exit(1)

    sys.argv = [sys.argv[0]] + sys.argv[2:]  # Remove command from args

    if command == "check_overlaps":
        check_overlaps()
    elif command == "split_dataset":
        split_dataset()
    elif command == "filter_classes":
        filter_dataset_classes()
    elif command == "prepare_calibration":
        prepare_calibration()
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
