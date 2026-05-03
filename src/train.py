#!/usr/bin/env python3
"""
Unified YOLO training script with configuration support.

Usage:
    python src/train.py                    # Use default config
    python src/train.py --config custom_config.yaml
    python src/train.py --data path/to/data.yaml --epochs 300
"""

import argparse
import sys
from pathlib import Path

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))


def _parse_scalar(value: str):
    """Parse a simple YAML scalar value without third-party dependencies."""
    text = value.strip()
    if text == "":
        return ""
    if text in {"null", "Null", "NULL", "~"}:
        return None
    if text.lower() == "true":
        return True
    if text.lower() == "false":
        return False
    if (text.startswith('"') and text.endswith('"')) or (
        text.startswith("'") and text.endswith("'")
    ):
        return text[1:-1]
    try:
        return int(text)
    except ValueError:
        pass
    try:
        return float(text)
    except ValueError:
        return text


def _load_simple_yaml(file_path: Path) -> dict:
    """Load the small path configuration file using only the standard library."""
    root = {}
    stack = [(0, root)]

    with open(file_path, "r", encoding="utf-8") as file_handle:
        for raw_line in file_handle:
            line = raw_line.rstrip("\n")
            stripped = line.strip()

            if not stripped or stripped.startswith("#"):
                continue

            indent = len(line) - len(line.lstrip(" "))
            content = stripped.split("#", 1)[0].rstrip()
            if not content:
                continue

            while len(stack) > 1 and indent < stack[-1][0]:
                stack.pop()

            current = stack[-1][1]
            if ":" not in content:
                continue

            key, value = content.split(":", 1)
            key = key.strip()
            value = value.strip()

            if value == "":
                nested = {}
                current[key] = nested
                stack.append((indent + 2, nested))
            else:
                current[key] = _parse_scalar(value)

    return root


def _find_project_root(config_path: Path) -> Path:
    """Find the project root by walking up from the current directory."""
    current_dir = Path.cwd()
    for parent in [current_dir] + list(current_dir.parents):
        if (parent / config_path).exists():
            return parent
    return current_dir


def _resolve_path(value, project_root: Path):
    if value is None:
        return None
    path = Path(str(value))
    if path.is_absolute():
        return path
    return project_root / path


def _resolve_training_project(project_value, project_root: Path) -> Path:
    """Resolve the Ultralytics project directory to an absolute path."""
    if project_value is None:
        return project_root / "models" / "training_results"

    return _resolve_path(project_value, project_root)


def _print_path_tree(data: dict, project_root: Path, indent: int = 0):
    prefix = "  " * indent
    for key, value in data.items():
        if key == "project_root":
            continue
        if isinstance(value, dict):
            print(f"{prefix}[{key}]")
            _print_path_tree(value, project_root, indent + 1)
        elif isinstance(value, str):
            resolved = _resolve_path(value, project_root)
            print(f"{prefix}  {key}: {value} → {resolved}")
        else:
            print(f"{prefix}  {key}: {value}")


def show_paths() -> int:
    """Show path configuration without requiring third-party packages."""
    config_path = Path("configs/paths.yaml")
    if not config_path.exists():
        print(f"ERROR: Path config file not found: {config_path}")
        return 1

    config = _load_simple_yaml(config_path)
    project_root_value = config.get("project_root")
    if project_root_value:
        project_root = Path(str(project_root_value))
    else:
        project_root = _find_project_root(config_path)

    print("=" * 70)
    print("YOLO Vision Pipeline - Path Configuration")
    print("=" * 70)
    print(f"Project Root: {project_root}\n")
    _print_path_tree(config, project_root)
    print("=" * 70)
    return 0


def load_config(config_path: str) -> dict:
    """Load YAML configuration file."""
    try:
        import yaml
    except ImportError:
        print("ERROR: PyYAML not installed. Install with:")
        print("  pip install pyyaml")
        sys.exit(1)

    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def main():
    parser = argparse.ArgumentParser(description="Train YOLOv8 model")
    parser.add_argument(
        "--config",
        type=str,
        default="configs/train_config.yaml",
        help="Path to training configuration file",
    )
    parser.add_argument("--model", type=str, help="Override model variant")
    parser.add_argument("--data", type=str, help="Override data config path")
    parser.add_argument("--epochs", type=int, help="Override number of epochs")
    parser.add_argument("--batch", type=int, help="Override batch size")
    parser.add_argument("--device", type=int, help="Override GPU device")
    parser.add_argument("--imgsz", type=int, help="Override image size")
    parser.add_argument(
        "--show-paths", action="store_true", help="Show path configuration and exit"
    )

    args = parser.parse_args()

    # Show paths configuration if requested
    if args.show_paths:
        return show_paths()

    try:
        from ultralytics import YOLO
    except ImportError:
        print("ERROR: ultralytics not installed. Install with:")
        print("  pip install ultralytics")
        sys.exit(1)

    # Load configuration
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"ERROR: Config file not found: {config_path}")
        sys.exit(1)

    config = load_config(args.config)
    training_config = config.get("training", {})
    project_root = _find_project_root(config_path)

    # Override with command line arguments
    if args.model:
        training_config["model"] = args.model
    if args.data:
        training_config["data"] = args.data
    if args.epochs:
        training_config["epochs"] = args.epochs
    if args.batch:
        training_config["batch"] = args.batch
    if args.device:
        training_config["device"] = args.device
    if args.imgsz:
        training_config["imgsz"] = args.imgsz

    # Validate configuration
    required_keys = ["model", "data", "epochs", "imgsz"]
    for key in required_keys:
        if key not in training_config:
            print(f"ERROR: Missing required config key: {key}")
            sys.exit(1)

    # Load model
    print(f"Loading model: {training_config['model']}")
    model = YOLO(training_config["model"])

    # Prepare training arguments
    train_args = {
        "data": training_config["data"],
        "epochs": training_config["epochs"],
        "imgsz": training_config["imgsz"],
        "device": training_config["device"],
        "workers": training_config.get("workers", 8),
        "patience": training_config.get("patience", 50),
        "project": str(
            _resolve_training_project(
                training_config.get("project", "models/training_results"),
                project_root,
            )
        ),
        "name": training_config.get("name", "yolo_train"),
        "save_period": training_config.get("save_period", 10),
        "close_mosaic": training_config.get("close_mosaic", 10),
        "pretrained": training_config.get("pretrained", True),
    }

    # Handle batch size
    if training_config.get("batch") and training_config["batch"] > 0:
        train_args["batch"] = training_config["batch"]
    elif training_config.get("batch") == -1:
        train_args["batch"] = -1  # Auto batch

    print("\nTraining configuration:")
    for key, value in train_args.items():
        print(f"  {key}: {value}")

    print("\nStarting training...")
    # Start training
    results = model.train(**train_args)

    # Save results
    output_dir = Path(train_args["project"]) / train_args["name"]
    best_model = output_dir / "weights" / "best.pt"

    if best_model.exists():
        print(f"\n✅ Training completed!")
        print(f"Best model saved to: {best_model}")

        # Copy best model to models directory for convenient access
        import shutil

        models_dir = Path("models")
        models_dir.mkdir(exist_ok=True)
        dest_path = models_dir / "best.pt"
        shutil.copy(str(best_model), str(dest_path))
        print(f"Copied to: {dest_path}")
    else:
        print(f"\n⚠️ Training finished but best model not found at {best_model}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
