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
import yaml

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

try:
    from ultralytics import YOLO
except ImportError:
    print("ERROR: ultralytics not installed. Install with:")
    print("  pip install ultralytics")
    sys.exit(1)

try:
    from utils.path_manager import paths
except ImportError:
    paths = None  # Optional path manager


def load_config(config_path: str) -> dict:
    """Load YAML configuration file."""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def main():
    parser = argparse.ArgumentParser(description="Train YOLOv8 model")
    parser.add_argument(
        "--config",
        type=str,
        default="configs/train_config.yaml",
        help="Path to training configuration file"
    )
    parser.add_argument("--model", type=str, help="Override model variant")
    parser.add_argument("--data", type=str, help="Override data config path")
    parser.add_argument("--epochs", type=int, help="Override number of epochs")
    parser.add_argument("--batch", type=int, help="Override batch size")
    parser.add_argument("--device", type=int, help="Override GPU device")
    parser.add_argument("--imgsz", type=int, help="Override image size")
    parser.add_argument(
        "--show-paths",
        action="store_true",
        help="Show path configuration and exit"
    )
    
    args = parser.parse_args()
    
    # Show paths configuration if requested
    if args.show_paths and paths:
        paths.print_config()
        return 0
    
    # Load configuration
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"ERROR: Config file not found: {config_path}")
        sys.exit(1)
    
    config = load_config(args.config)
    training_config = config.get("training", {})
    
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
        "project": training_config.get("project", "models/training_results"),
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
