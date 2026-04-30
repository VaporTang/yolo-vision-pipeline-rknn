#!/usr/bin/env python3
"""
Path Verification Tool
Helps users verify and troubleshoot path configuration.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

try:
    from utils.path_manager import paths
except ImportError as e:
    print(f"ERROR: Could not import path_manager: {e}")
    sys.exit(1)


def verify_paths():
    """Verify all critical paths exist."""
    print("=" * 70)
    print("YOLO Vision Pipeline - Path Verification")
    print("=" * 70)
    print()
    
    # Load paths config
    try:
        config = paths.load_config()
    except Exception as e:
        print(f"❌ Failed to load path configuration: {e}")
        return False
    
    project_root = paths.get_project_root()
    print(f"📂 Project Root: {project_root}")
    print(f"   Exists: {'✅' if project_root.exists() else '❌'}")
    print()
    
    # Check critical directories
    critical_paths = [
        ("configs", "configs"),
        ("datasets", "datasets/yolo_dataset"),
        ("src", "src"),
        ("models", "models"),
        ("docs", "docs"),
    ]
    
    print("📋 Checking Critical Directories:")
    all_ok = True
    for name, path_str in critical_paths:
        path = paths.get(f"{name}.root") if name in ["configs", "src", "docs"] else paths.resolve_path(path_str)
        exists = path.exists() if path else False
        status = "✅" if exists else "⚠️"
        print(f"  {status} {name:15} → {path}")
        if name == "datasets" and not exists:
            print(f"     ℹ️  Dataset dir doesn't exist yet - create it when ready")
        elif not exists:
            all_ok = False
    
    print()
    
    # Check configuration files
    print("⚙️  Configuration Files:")
    config_files = [
        ("paths.yaml", "configs.paths"),
        ("data.yaml", "configs.data"),
        ("train_config.yaml", "configs.train"),
        ("export_config.yaml", "configs.export"),
        ("rknn_config.yaml", "configs.rknn"),
    ]
    
    for name, key in config_files:
        path = paths.get(key)
        exists = path.exists() if path else False
        status = "✅" if exists else "❌"
        print(f"  {status} {name:25} → {path}")
        if not exists:
            all_ok = False
    
    print()
    
    # Check Python scripts
    print("🐍 Python Scripts:")
    scripts = [
        ("train.py", "src.train_script"),
        ("dataset_tools.py", "src.dataset_tools"),
        ("1_pt_to_onnx.py", "src.export_pt2onnx"),
        ("2_onnx_to_rknn.py", "src.export_onnx2rknn"),
        ("path_manager.py", "src.utils"),
    ]
    
    for name, key in scripts:
        path = paths.get(key)
        exists = path.exists() if path else False
        status = "✅" if exists else "⚠️"
        print(f"  {status} {name:25} → {path}")
    
    print()
    
    # Model paths
    print("🤖 Model Paths (Output):")
    model_paths = [
        ("Best PT", "models.best_pt"),
        ("Best ONNX", "models.best_onnx"),
        ("Best RKNN", "models.best_rknn"),
    ]
    
    for name, key in model_paths:
        path = paths.get(key)
        exists = path.exists() if path else False
        status = "✅" if exists else "ℹ️"
        print(f"  {status} {name:20} → {path}")
    
    print()
    print("=" * 70)
    
    if all_ok:
        print("✅ All critical paths are OK!")
        print()
        print("Next steps:")
        print("  1. Prepare your dataset in YOLO format")
        print("  2. Update configs/data.yaml with your class names")
        print("  3. Run: python src/train.py")
    else:
        print("⚠️  Some critical paths are missing!")
        print()
        print("To fix:")
        print("  1. Make sure you're running from the project root directory")
        print("  2. Check that configs/paths.yaml exists")
        print("  3. Verify project_root setting in configs/paths.yaml")
    
    print()
    return all_ok


def show_usage():
    """Show usage information."""
    print()
    print("Path Configuration Help:")
    print("-" * 70)
    print()
    print("1. Auto-detect paths (Recommended):")
    print("   Set in configs/paths.yaml:")
    print("   ")
    print("     project_root: null")
    print()
    print("2. Or specify absolute path:")
    print("   ")
    print("     project_root: /absolute/path/to/yolo-vision-pipeline-rknn")
    print()
    print("3. View all paths:")
    print("   ")
    print("     python src/train.py --show-paths")
    print("     python src/export/1_pt_to_onnx.py --show-paths")
    print("     python src/dataset_tools.py show-paths")
    print()
    print("4. Documentation:")
    print("   See docs/path_configuration.md for detailed guide")
    print()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Verify YOLO Vision Pipeline paths")
    parser.add_argument("--help-config", action="store_true", help="Show configuration help")
    parser.add_argument("--show-config", action="store_true", help="Show full configuration")
    
    args = parser.parse_args()
    
    if args.help_config:
        show_usage()
        sys.exit(0)
    
    if args.show_config:
        paths.print_config()
        sys.exit(0)
    
    # Run verification
    success = verify_paths()
    show_usage()
    
    sys.exit(0 if success else 1)
