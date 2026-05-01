# Path Configuration Guide

## Overview

The YOLO Vision Pipeline now includes a centralized path configuration system. This means you only need to configure paths **once**, and all scripts will automatically use these paths.

## Quick Start

### 1. Set Your Project Root (Optional)

Edit `configs/paths.yaml`:

```yaml
# Set to your absolute project path (optional - auto-detects by default)
project_root: null  # null = auto-detect

# Or specify absolute path:
project_root: C:\Users\YourUsername\Documents\GitHub\yolo-vision-pipeline-rknn
```

**Or on Ubuntu/WSL:**

```yaml
project_root: /home/username/path/to/yolo-vision-pipeline-rknn
```

### 2. View Current Configuration

Check what paths are being used:

```powershell
# Windows
python src/train.py --show-paths
```

This check uses only the standard library, so it can run before the training environment is installed.

The other scripts may still require their own installed dependencies.

This will display all configured paths with their resolved absolute paths.

### 3. Customize Paths (If Needed)

Edit `configs/paths.yaml` to change default paths:

```yaml
dataset:
  train_images: your/custom/path/train/images
  val_images: your/custom/path/val/images

models:
  best_pt: your/custom/path/best.pt
  best_onnx: your/custom/path/best.onnx
  best_rknn: your/custom/path/best.rknn
```

## How It Works

### Path Resolution

1. **Absolute Paths**: Used as-is (e.g., `/home/user/models`)
2. **Relative Paths**: Resolved from `project_root`
3. **Auto-detection**: If `project_root: null`, automatically finds the project directory

### Example

If `project_root` is `/home/user/yolo-pipeline/`:

```yaml
models:
  best_pt: models/best.pt  # Resolves to: /home/user/yolo-pipeline/models/best.pt
```

## Configuration Sections

### Dataset Paths

```yaml
dataset:
  root: datasets/yolo_dataset
  train_images: datasets/yolo_dataset/train/images
  train_labels: datasets/yolo_dataset/train/labels
  val_images: datasets/yolo_dataset/valid/images
  val_labels: datasets/yolo_dataset/valid/labels
  calibration_images: datasets/calibration/images
  calibration_list: datasets/calibration/dataset.txt
```

### Model Paths

```yaml
models:
  root: models
  best_pt: models/best.pt          # Trained model
  best_onnx: models/best.onnx      # Exported ONNX
  best_rknn: models/best.rknn      # Final RKNN
  training_results: models/training_results
```

### Config Paths

```yaml
configs:
  root: configs
  data: configs/data.yaml
  train: configs/train_config.yaml
  export: configs/export_config.yaml
  rknn: configs/rknn_config.yaml
```

### Source Code Paths

```yaml
src:
  train_script: src/train.py
  dataset_tools: src/dataset_tools.py
  export_pt2onnx: src/export/1_pt_to_onnx.py
  export_onnx2rknn: src/export/2_onnx_to_rknn.py
```

## Using PathManager in Python

You can use the PathManager in your own scripts:

```python
from src.utils.path_manager import paths

# Get a single path
best_pt = paths.get("models.best_pt")
print(f"Model path: {best_pt}")

# Get as string
best_onnx_str = paths.get_str("models.best_onnx")

# Get all paths in a section
all_models = paths.get_all("models")
for name, path in all_models.items():
    print(f"{name}: {path}")

# Ensure directory exists
calibration_dir = paths.ensure_dir("dataset.calibration_images")

# Get project root
root = paths.get_project_root()
print(f"Project root: {root}")
```

## Command Examples

### Training with Paths

```powershell
# Show paths first to verify
python src/train.py --show-paths

# Then train
python src/train.py
```

### Export with Paths

```powershell
# Check paths
$env:PYTHONPATH = ".\"
python src/export/1_pt_to_onnx.py --show-paths

# Export
python src/export/1_pt_to_onnx.py
```

### Dataset Tools with Paths

```bash
# Show paths
python src/dataset_tools.py show-paths

# Prepare calibration
python src/dataset_tools.py prepare_calibration \
    --image-dir $(python -c "from src.utils.path_manager import paths; print(paths.get_str('dataset.train_images'))") \
    --output $(python -c "from src.utils.path_manager import paths; print(paths.get_str('dataset.calibration_list'))")
```

## Windows & WSL Paths

### Windows (PowerShell)

```yaml
project_root: C:\Users\YourName\Documents\GitHub\yolo-vision-pipeline-rknn
```

### Ubuntu/WSL

```yaml
project_root: /home/username/yolo-vision-pipeline-rknn
# Or access Windows paths via:
project_root: /mnt/c/Users/YourName/Documents/GitHub/yolo-vision-pipeline-rknn
```

## Troubleshooting

### "configs/paths.yaml not found"

**Solution**: Ensure you're running from project root:

```bash
cd /path/to/yolo-vision-pipeline-rknn
python src/train.py --show-paths
```

### Paths not resolving correctly

**Solution**: Check `project_root` in `configs/paths.yaml`:

```yaml
# Auto-detect (recommended)
project_root: null

# Or explicitly set:
project_root: /absolute/path/to/project
```

### Accessing WSL paths from Windows

**In config.yaml:**

```yaml
# Windows: use standard Windows paths
project_root: C:\Users\YourName\path\to\project

# WSL: use /mnt/c for Windows drives
project_root: /mnt/c/Users/YourName/path/to/project
```

## Best Practices

1. **Use relative paths** when possible for portability
2. **Set `project_root: null`** to auto-detect
3. **Keep paths in `configs/paths.yaml`** for centralized management
4. **Run `--show-paths`** before executing scripts to verify paths
5. **Use consistent separators** (forward slashes work on all platforms)

## Environment Variables

Currently, the path system does **not** expand environment variables (e.g., `$HOME`, `%USERPROFILE%`).

To use environment-based paths, either:

1. Manually set them in `configs/paths.yaml`
2. Write a pre-processing script that expands variables
3. Use absolute paths directly

Example for future enhancement:

```yaml
# NOT currently supported:
project_root: ${HOME}/yolo-vision-pipeline  # Won't work

# DO this instead:
project_root: /home/username/yolo-vision-pipeline
```

## Next Steps

- Run `python src/train.py --show-paths` to see your current configuration
- Modify `configs/paths.yaml` if you need custom paths
- Start training: `python src/train.py`

---

**All paths are centralized!** No more manually copying paths between scripts. 🎉
