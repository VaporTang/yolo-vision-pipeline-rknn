#!/usr/bin/env python3
"""
Convert ONNX model to RKNN format for Rockchip NPU.

This script uses RKNN Toolkit2 to convert ONNX models to RKNN format
with INT8 quantization support.

Requirements (on Ubuntu/WSL):
    - Python 3.10
    - RKNN Toolkit2: pip install rknn-toolkit2
    - Calibration images (20-30 representative images)

Usage:
    python src/export/2_onnx_to_rknn.py --config configs/rknn_config.yaml
    
    python src/export/2_onnx_to_rknn.py \
        --input models/best.onnx \
        --output models/best.rknn \
        --dataset datasets/calibration/dataset.txt
"""

import argparse
import sys
from pathlib import Path
import yaml

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from rknn.api import RKNN
except ImportError:
    print("ERROR: RKNN Toolkit2 not installed!")
    print("This script must run on Ubuntu/WSL with RKNN Toolkit2.")
    print("\nSetup instructions:")
    print("  1. Install Ubuntu 22.04 on WSL (if on Windows)")
    print("  2. Create virtual environment:")
    print("     python3 -m venv rknn-env")
    print("     source rknn-env/bin/activate")
    print("  3. Install RKNN Toolkit2:")
    print("     git clone https://github.com/airockchip/rknn-toolkit2.git")
    print("     cd rknn-toolkit2/rknn-toolkit2/packages/x86_64")
    print("     pip install -r requirements_cp310-2.3.2.txt")
    print("     pip install rknn_toolkit2-2.3.2-cp310-cp310-*.whl")
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
        description="Convert ONNX model to RKNN format",
        epilog="Run this script on Ubuntu/WSL with RKNN Toolkit2 installed."
    )
    parser.add_argument(
        "--config",
        type=str,
        default="configs/rknn_config.yaml",
        help="Path to RKNN conversion configuration file"
    )
    parser.add_argument(
        "--input",
        type=str,
        help="Override input ONNX model path (e.g., models/best.onnx)"
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Override output RKNN model path (e.g., models/best.rknn)"
    )
    parser.add_argument(
        "--dataset",
        type=str,
        help="Override calibration dataset path (e.g., datasets/calibration/dataset.txt)"
    )
    parser.add_argument(
        "--platform",
        type=str,
        choices=["rk3588", "rk3588s", "rk3568", "rk3566", "rk3562"],
        help="Override target platform"
    )
    parser.add_argument(
        "--no-quant",
        action="store_true",
        help="Disable INT8 quantization (export as float model)"
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
    rknn_config = config.get("rknn_conversion", {})
    
    # Override with command line arguments
    if args.input:
        rknn_config["input_onnx"] = args.input
    if args.output:
        rknn_config["output_rknn"] = args.output
    if args.dataset:
        rknn_config["quantization_dataset"] = args.dataset
    if args.platform:
        rknn_config["target_platform"] = args.platform
    if args.no_quant:
        rknn_config["do_quantization"] = False
    
    # Validate paths
    input_onnx = Path(rknn_config.get("input_onnx", "models/best.onnx"))
    if not input_onnx.exists():
        print(f"ERROR: Input ONNX model not found: {input_onnx}")
        sys.exit(1)
    
    output_rknn = Path(rknn_config.get("output_rknn", "models/best.rknn"))
    output_rknn.parent.mkdir(parents=True, exist_ok=True)
    
    do_quantization = rknn_config.get("do_quantization", True)
    dataset_path = rknn_config.get("quantization_dataset", "datasets/calibration/dataset.txt")
    
    if do_quantization:
        dataset_file = Path(dataset_path)
        if not dataset_file.exists():
            print(f"ERROR: Quantization dataset not found: {dataset_file}")
            print("Please run: python src/dataset_tools.py prepare_calibration ...")
            sys.exit(1)
    
    print("=" * 70)
    print("ONNX to RKNN Model Conversion")
    print("=" * 70)
    print(f"Input ONNX:           {input_onnx}")
    print(f"Output RKNN:          {output_rknn}")
    print(f"Target Platform:      {rknn_config.get('target_platform', 'rk3588')}")
    print(f"Quantization:         {'INT8' if do_quantization else 'Float'}")
    if do_quantization:
        print(f"Calibration Dataset:  {dataset_path}")
    print("=" * 70)
    
    # Create RKNN object
    print("\n1. Initializing RKNN...")
    rknn = RKNN(verbose=rknn_config.get("verbose", True))
    
    # Configure model
    print("\n2. Configuring RKNN model...")
    try:
        config_kwargs = {
            "mean_values": rknn_config.get("mean_values", [[0, 0, 0]]),
            "std_values": rknn_config.get("std_values", [[255, 255, 255]]),
            "target_platform": rknn_config.get("target_platform", "rk3588"),
            "optimization_level": rknn_config.get("optimization_level", 3),
        }
        
        rknn.config(**config_kwargs)
        print("   Configuration complete")
    
    except Exception as e:
        print(f"ERROR: Configuration failed: {e}")
        rknn.release()
        sys.exit(1)
    
    # Load ONNX model
    print(f"\n3. Loading ONNX model: {input_onnx}")
    try:
        ret = rknn.load_onnx(model=str(input_onnx))
        if ret != 0:
            print(f"ERROR: Failed to load ONNX model")
            rknn.release()
            sys.exit(1)
        print("   ONNX model loaded successfully")
    
    except Exception as e:
        print(f"ERROR: Failed to load ONNX: {e}")
        rknn.release()
        sys.exit(1)
    
    # Build RKNN model
    print(f"\n4. Building RKNN model...")
    print(f"   {'With INT8 quantization' if do_quantization else 'Without quantization'}...")
    try:
        ret = rknn.build(
            do_quantization=do_quantization,
            dataset=dataset_path if do_quantization else None
        )
        if ret != 0:
            print(f"ERROR: Failed to build RKNN model")
            rknn.release()
            sys.exit(1)
        print("   RKNN model built successfully")
    
    except Exception as e:
        print(f"ERROR: Build failed: {e}")
        rknn.release()
        sys.exit(1)
    
    # Export RKNN model
    print(f"\n5. Exporting RKNN model: {output_rknn}")
    try:
        ret = rknn.export_rknn(str(output_rknn))
        if ret != 0:
            print(f"ERROR: Failed to export RKNN model")
            rknn.release()
            sys.exit(1)
        print("   ✅ RKNN model exported successfully")
    
    except Exception as e:
        print(f"ERROR: Export failed: {e}")
        rknn.release()
        sys.exit(1)
    
    # Release resources
    rknn.release()
    
    # Verify output
    if output_rknn.exists():
        file_size_mb = output_rknn.stat().st_size / (1024 * 1024)
        print(f"\n✅ Conversion successful!")
        print(f"   Output file: {output_rknn}")
        print(f"   File size: {file_size_mb:.2f} MB")
    else:
        print(f"\n⚠️ Conversion completed but output file not found: {output_rknn}")
        return 1
    
    print(f"\n✅ Ready to deploy on {rknn_config.get('target_platform', 'rk3588')}!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
