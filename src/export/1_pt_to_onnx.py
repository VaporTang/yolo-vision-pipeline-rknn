#!/usr/bin/env python3
"""
Export YOLOv8 model to ONNX format.

This script exports a trained YOLOv8 model (.pt) to ONNX format using
the Rockchip-customized ultralytics_yolov8 toolkit, which removes
unsupported post-processing operations for NPU compatibility.

Requirements:
    - Rockchip ultralytics_yolov8 installed with: pip install -e .
    - The directory containing this script must be in PYTHONPATH

Usage (Windows PowerShell):
    $env:PYTHONPATH = ".\"
    python src/export/1_pt_to_onnx.py --config configs/export_config.yaml
    
Usage (Linux/WSL):
    export PYTHONPATH=./
    python src/export/1_pt_to_onnx.py --config configs/export_config.yaml
"""

import argparse
import sys
from pathlib import Path
import yaml

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from ultralytics import YOLO
except ImportError:
    print("ERROR: ultralytics not installed!")
    print("For Windows: Install Rockchip customized version")
    print("  git clone https://github.com/airockchip/ultralytics_yolov8.git")
    print("  cd ultralytics_yolov8")
    print("  pip install -e .")
    print("  pip install onnx onnxsim")
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
    parser = argparse.ArgumentParser(
        description="Export YOLOv8 model to ONNX format",
        epilog="Ensure PYTHONPATH includes the project root directory."
    )
    parser.add_argument(
        "--config",
        type=str,
        default="configs/export_config.yaml",
        help="Path to export configuration file (default: configs/export_config.yaml)"
    )
    parser.add_argument(
        "--input",
        type=str,
        help="Override input model path (e.g., models/best.pt)"
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Override output ONNX path (e.g., models/best.onnx)"
    )
    parser.add_argument(
        "--imgsz",
        type=int,
        help="Override input image size (default: 640)"
    )
    parser.add_argument(
        "--device",
        type=int,
        help="Override GPU device (0 for GPU, -1 for CPU)"
    )
    parser.add_argument(
        "--simplify",
        action="store_true",
        default=None,
        help="Simplify ONNX model using onnxsim"
    )
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
    export_config = config.get("onnx_export", {})
    
    # Override with command line arguments
    if args.input:
        export_config["input_model"] = args.input
    if args.output:
        export_config["output_onnx"] = args.output
    if args.imgsz:
        export_config["imgsz"] = args.imgsz
    if args.device is not None:
        export_config["device"] = args.device
    if args.simplify is not None:
        export_config["simplify"] = args.simplify
    
    # Validate paths
    input_model = Path(export_config.get("input_model", "models/best.pt"))
    if not input_model.exists():
        print(f"ERROR: Input model not found: {input_model}")
        sys.exit(1)
    
    output_onnx = Path(export_config.get("output_onnx", "models/best.onnx"))
    output_onnx.parent.mkdir(parents=True, exist_ok=True)
    
    print("=" * 60)
    print("YOLO Model Export to ONNX")
    print("=" * 60)
    print(f"Input model:     {input_model}")
    print(f"Output ONNX:     {output_onnx}")
    print(f"Image size:      {export_config.get('imgsz', 640)}")
    print(f"Device:          {export_config.get('device', 0)}")
    print(f"Simplify:        {export_config.get('simplify', False)}")
    print("=" * 60)
    
    # Load model
    print(f"\n1. Loading model: {input_model}")
    try:
        model = YOLO(str(input_model))
    except Exception as e:
        print(f"ERROR: Failed to load model: {e}")
        sys.exit(1)
    
    # Export to ONNX
    print(f"\n2. Exporting to ONNX format...")
    try:
        # Export using Rockchip's method
        export_kwargs = {
            "format": "onnx",
            "imgsz": export_config.get("imgsz", 640),
            "device": export_config.get("device", 0),
        }
        
        # Run export
        results = model.export(**export_kwargs)
        
        print(f"✅ Export completed!")
        print(f"   Output: {output_onnx}")
        
        # Check if output was created
        if output_onnx.exists():
            file_size_mb = output_onnx.stat().st_size / (1024 * 1024)
            print(f"   Size: {file_size_mb:.2f} MB")
        
        # Optional: Simplify ONNX model
        if export_config.get("simplify", False):
            print(f"\n3. Simplifying ONNX model...")
            try:
                import onnxsim
                
                input_model_onnx = str(output_onnx)
                output_simplified = input_model_onnx.replace(".onnx", "_simplified.onnx")
                
                print(f"   Using onnxsim to simplify...")
                import subprocess
                result = subprocess.run([
                    sys.executable, "-m", "onnxsim",
                    input_model_onnx, output_simplified
                ], capture_output=True, text=True)
                
                if result.returncode == 0:
                    print(f"✅ Simplified ONNX saved: {output_simplified}")
                else:
                    print(f"⚠️ Simplification failed: {result.stderr}")
            
            except ImportError:
                print("⚠️ onnxsim not installed. Skipping simplification.")
                print("   Install with: pip install onnxsim")
        
        print("\n✅ Export successful!")
        print(f"\nNext step: Convert {output_onnx.name} to RKNN format using 2_onnx_to_rknn.py")
        return 0
    
    except Exception as e:
        print(f"ERROR: Export failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    sys.exit(main())
