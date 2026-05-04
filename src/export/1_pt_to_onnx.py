#!/usr/bin/env python3
"""
Export YOLOv8 model to ONNX format.

This script exports a trained YOLOv8 model (.pt) to ONNX format for two
different purposes:
1) RKNN conversion (requires Rockchip ultralytics_yolov8 backend)
2) X-Anylabeling inference (requires official Ultralytics backend)

Requirements:
    - ultralytics installed in the active environment
    - The directory containing this script must be in PYTHONPATH

Usage (Windows PowerShell):
    $env:PYTHONPATH = ".\"
    python src/export/1_pt_to_onnx.py --purpose rknn --config configs/export_config.yaml
    python src/export/1_pt_to_onnx.py --purpose rknn --simplify
    python src/export/1_pt_to_onnx.py --purpose rknn --no-simplify
    python src/export/1_pt_to_onnx.py --purpose anylabeling --input models/best.pt --output tools/anylabeling/models/detection.onnx

Usage (Linux/WSL):
    export PYTHONPATH=./
    python src/export/1_pt_to_onnx.py --purpose rknn --config configs/export_config.yaml
    python src/export/1_pt_to_onnx.py --purpose rknn --simplify
    python src/export/1_pt_to_onnx.py --purpose rknn --no-simplify
"""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path
import yaml

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import ultralytics
    from ultralytics import YOLO
except ImportError:
    print("ERROR: ultralytics not installed!")
    print("Install one of the following in the active environment:")
    print("  - Rockchip backend for RKNN export")
    print("  - Official Ultralytics backend for X-Anylabeling export")
    print("  pip install onnx onnxsim")
    sys.exit(1)

try:
    from utils.path_manager import paths
except ImportError:
    paths = None  # Optional path manager


def load_config(config_path: str) -> dict:
    """Load YAML configuration file."""
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def detect_backend() -> str:
    """Best-effort detection of current ultralytics backend type."""
    module_path = Path(ultralytics.__file__).resolve().as_posix().lower()
    if "ultralytics_yolov8" in module_path or "airockchip" in module_path:
        return "rockchip"
    return "official"


def resolve_exported_path(export_result) -> Path | None:
    """Resolve ONNX path returned by model.export across ultralytics variants."""
    if export_result is None:
        return None

    if isinstance(export_result, (str, Path)):
        return Path(export_result)

    if isinstance(export_result, (list, tuple)) and export_result:
        first = export_result[0]
        if isinstance(first, (str, Path)):
            return Path(first)

    return None


def validate_backend_for_purpose(
    purpose: str, backend: str, strict_check: bool
) -> bool:
    """Validate whether active backend matches export purpose."""
    expected_backend = {
        "rknn": "rockchip",
        "anylabeling": "official",
    }[purpose]

    if backend == expected_backend:
        return True

    print("ERROR: Backend and export purpose mismatch!")
    print(f"  Purpose:          {purpose}")
    print(f"  Expected backend: {expected_backend}")
    print(f"  Detected backend: {backend}")

    if purpose == "rknn":
        print("  Suggested environment: conda activate rknn-yolov8-export")
    else:
        print("  Suggested environment: conda activate rknn-yolov8-train")

    if strict_check:
        print("Aborting due to strict backend check.")
        print("Use --allow-mismatch only if you know this backend is still compatible.")
        return False

    print("WARNING: Continuing because strict backend check is disabled.")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Export YOLOv8 model to ONNX format",
        epilog="Ensure PYTHONPATH includes the project root directory.",
    )
    parser.add_argument(
        "--config",
        type=str,
        default="configs/export_config.yaml",
        help="Path to export configuration file (default: configs/export_config.yaml)",
    )
    parser.add_argument(
        "--input", type=str, help="Override input model path (e.g., models/best.pt)"
    )
    parser.add_argument(
        "--output", type=str, help="Override output ONNX path (e.g., models/best.onnx)"
    )
    parser.add_argument(
        "--imgsz", type=int, help="Override input image size (default: 640)"
    )
    parser.add_argument(
        "--device", type=int, help="Override GPU device (0 for GPU, -1 for CPU)"
    )
    parser.add_argument(
        "--purpose",
        type=str,
        choices=["rknn", "anylabeling"],
        help="Export purpose: rknn (Rockchip backend) or anylabeling (official backend)",
    )
    parser.add_argument(
        "--simplify",
        action="store_true",
        default=None,
        help="Simplify ONNX model using onnxsim (for RKNN this is an explicit override)",
    )
    parser.add_argument(
        "--no-simplify",
        action="store_false",
        dest="simplify",
        help="Disable ONNX simplification",
    )
    parser.add_argument(
        "--allow-mismatch",
        action="store_true",
        help="Allow backend/purpose mismatch (not recommended)",
    )
    parser.add_argument(
        "--show-paths", action="store_true", help="Show path configuration and exit"
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

    purpose = args.purpose or export_config.get("purpose", "rknn")
    strict_backend_check = export_config.get("strict_backend_check", True)
    if args.allow_mismatch:
        strict_backend_check = False

    backend = detect_backend()
    if not validate_backend_for_purpose(purpose, backend, strict_backend_check):
        return 1

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
    print(f"Purpose:         {purpose}")
    print(f"Backend:         {backend}")
    print(f"Input model:     {input_model}")
    print(f"Output ONNX:     {output_onnx}")
    print(f"Image size:      {export_config.get('imgsz', 640)}")
    print(f"Device:          {export_config.get('device', 0)}")
    print(f"Opset version:   {export_config.get('opset_version', 13)}")
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
        export_format = "onnx"
        opset_version = export_config.get("opset_version", 13)
        simplify = export_config.get("simplify", False)
        simplify_cli = args.simplify is not None

        if purpose == "rknn" and backend == "rockchip":
            export_format = "rknn"
            if opset_version != 12:
                print("WARNING: For Rockchip RKNN export, opset 12 is recommended.")
                opset_version = 12
            if simplify and not simplify_cli:
                print(
                    "WARNING: Disabling onnxsim for RKNN export to avoid graph changes."
                )
                simplify = False
            elif simplify and simplify_cli:
                print(
                    "WARNING: Forcing onnxsim for RKNN export; verify accuracy and outputs."
                )

        export_kwargs = {
            "format": export_format,
            "imgsz": export_config.get("imgsz", 640),
            "device": export_config.get("device", 0),
            "opset": opset_version,
            "batch": 1,
            "simplify": False,
        }

        # Run export
        result = model.export(**export_kwargs)
        exported_onnx = resolve_exported_path(result)

        if exported_onnx and exported_onnx.exists():
            if exported_onnx.resolve() != output_onnx.resolve():
                shutil.copy2(exported_onnx, output_onnx)
                print(f"   Copied exported ONNX to requested path: {output_onnx}")
        elif not output_onnx.exists():
            print("ERROR: Export did not produce an ONNX file at expected location.")
            if exported_onnx:
                print(f"  Returned path: {exported_onnx}")
            return 1

        print("Export completed.")
        print(f"   Output: {output_onnx}")

        # Check if output was created
        if output_onnx.exists():
            file_size_mb = output_onnx.stat().st_size / (1024 * 1024)
            print(f"   Size: {file_size_mb:.2f} MB")

        # Optional: Simplify ONNX model
        if simplify:
            print(f"\n3. Simplifying ONNX model...")
            try:
                import onnxsim

                input_model_onnx = str(output_onnx)
                output_simplified = input_model_onnx.replace(
                    ".onnx", "_simplified.onnx"
                )

                print("   Using onnxsim to simplify...")

                result = subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "onnxsim",
                        input_model_onnx,
                        output_simplified,
                    ],
                    capture_output=True,
                    text=True,
                )

                if result.returncode == 0:
                    print(f"Simplified ONNX saved: {output_simplified}")
                else:
                    print(f"WARNING: Simplification failed: {result.stderr}")

            except ImportError:
                print("WARNING: onnxsim not installed. Skipping simplification.")
                print("   Install with: pip install onnxsim")

        print("\nExport successful.")
        if purpose == "rknn":
            print(
                f"\nNext step: Convert {output_onnx.name} to RKNN format using 2_onnx_to_rknn.py"
            )
        else:
            print("\nNext step: Load this ONNX model in X-Anylabeling model manager.")
        return 0

    except Exception as e:
        print(f"ERROR: Export failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    sys.exit(main())
