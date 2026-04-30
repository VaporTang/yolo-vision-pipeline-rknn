# YOLO Vision Pipeline RKNN

**Unified pipeline for YOLOv8 training, export, and conversion to RKNN format for Rockchip NPU deployment.**

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![YOLOv8](https://img.shields.io/badge/YOLOv8-Latest-green)
![Status](https://img.shields.io/badge/Status-Active-brightgreen)

## Overview

This project consolidates the entire YOLOv8 → ONNX → RKNN conversion pipeline into a single, organized repository. It eliminates the previous scattered workflow across multiple repositories and provides:

- **Unified configuration system** for training, export, and conversion
- **Organized dataset management** with preprocessing tools
- **Automated environment setup** for Windows and Ubuntu/WSL
- **Production-ready scripts** for each pipeline stage

## Project Structure

```
yolo-vision-pipeline-rknn/
├── configs/                      # Configuration files
│   ├── data.yaml                 # Dataset configuration
│   ├── train_config.yaml         # Training hyperparameters
│   ├── export_config.yaml        # ONNX export settings
│   └── rknn_config.yaml          # RKNN conversion settings
├── datasets/                     # Dataset directory
│   ├── raw/                      # Original dataset files
│   ├── calibration/              # Quantization calibration images
│   └── scripts/                  # Dataset processing utilities
├── models/                       # Trained and converted models
│   └── training_results/         # Training outputs
├── src/                          # Source code
│   ├── train.py                  # Unified training script
│   ├── dataset_tools.py          # Dataset processing utilities
│   ├── export/                   # Model export scripts
│   │   ├── 1_pt_to_onnx.py       # .pt → .onnx export
│   │   └── 2_onnx_to_rknn.py     # .onnx → .rknn conversion
│   └── utils/                    # Utility modules
│       └── dataset_utils.py      # Dataset manipulation functions
├── docs/                         # Documentation
├── setup_win.ps1                 # Windows setup script
└── setup_wsl.sh                  # Ubuntu/WSL setup script
```

## Quick Start

### Windows: Training and ONNX Export

#### 1. Initial Setup (One-time)

```powershell
# Open PowerShell as Administrator
cd path/to/yolo-vision-pipeline-rknn

# Run the setup script
.\setup_win.ps1

# Activate the environment
conda activate rknn-yolov8
```

#### 2. Prepare Your Dataset

```powershell
# Update configs/data.yaml with your dataset paths
# File structure should be:
# datasets/yolo_dataset/
#   ├── train/images/
#   │   ├── img1.jpg, img2.jpg, ...
#   │   └── img1.txt, img2.txt, ...  (YOLO format labels)
#   └── valid/images/
#       ├── img_val1.jpg, ...
#       └── img_val1.txt, ...
```

#### 3. Train a Model

```powershell
# Using default config
python src/train.py

# Or with custom parameters
python src/train.py --data configs/data.yaml --epochs 300 --batch -1

# Or override config file
python src/train.py --config configs/train_config.yaml
```

The best model will be saved to `models/best.pt`.

#### 4. Export to ONNX

```powershell
# Set PYTHONPATH (important!)
$env:PYTHONPATH = ".\"

# Run export
python src/export/1_pt_to_onnx.py --config configs/export_config.yaml
```

Output: `models/best.onnx`

### Ubuntu/WSL: ONNX to RKNN Conversion

#### 1. Install Ubuntu 22.04 on WSL (if on Windows)

```powershell
# Windows PowerShell (Administrator)
wsl --install -d Ubuntu-22.04
# Restart your computer
```

#### 2. Setup WSL Environment (One-time)

```bash
# Inside Ubuntu/WSL
cd /mnt/c/Users/YourUsername/Documents/GitHub/yolo-vision-pipeline-rknn

bash setup_wsl.sh

# Activate the environment
source rknn-env/bin/activate
```

#### 3. Prepare Calibration Dataset

```bash
# 20-30 representative training images for quantization
python src/dataset_tools.py prepare_calibration \
    --image-dir datasets/yolo_dataset/train/images \
    --output datasets/calibration/dataset.txt \
    --num-images 20
```

#### 4. Convert ONNX to RKNN

```bash
# Copy ONNX model from Windows
cp /mnt/c/Users/YourUsername/.../best.onnx ./models/

# Run conversion
python src/export/2_onnx_to_rknn.py --config configs/rknn_config.yaml
```

Output: `models/best.rknn`

## ⚙️ Path Configuration System

All paths in the pipeline are centralized in `configs/paths.yaml`. This eliminates the need to manually copy paths between scripts.

### Quick Setup

1. **Verify paths** (one-time):

  ```powershell
  python verify_paths.py
  ```

1. **View current configuration**:

  ```powershell
  python src/train.py --show-paths
  ```

1. **Customize paths** (if needed):
  Edit `configs/paths.yaml`:

  ```yaml
  project_root: null  # auto-detect, or set absolute path
   
  dataset:
    root: datasets/yolo_dataset
    train_images: datasets/yolo_dataset/train/images
    # ... more paths
   
  models:
    best_pt: models/best.pt
    best_onnx: models/best.onnx
    best_rknn: models/best.rknn
  ```

### Using PathManager in Python

```python
from src.utils.path_manager import paths

# Get a path
model_path = paths.get("models.best_pt")

# Get as string
model_str = paths.get_str("models.best_onnx")

# Ensure directory exists
paths.ensure_dir("dataset.calibration_images")

# Get all paths in a section
all_models = paths.get_all("models")
```

📖 **Full Guide**: See [PATH_SETUP.md](PATH_SETUP.md) or [docs/path_configuration.md](docs/path_configuration.md)

## Configuration Files

### `configs/data.yaml` - Dataset Configuration

```yaml
path: datasets/yolo_dataset  # Dataset root
train: datasets/yolo_dataset/train/images
val: datasets/yolo_dataset/valid/images

nc: 6  # Number of classes
names:  # Class names
  0: yellow_ball
  1: blue_ball
  2: red_ball
  3: black_ball
  4: blue_placement_zone
  5: red_placement_zone
```

### `configs/train_config.yaml` - Training Configuration

```yaml
training:
  model: yolov8l.pt          # Model variant
  data: configs/data.yaml    # Dataset config
  epochs: 300                # Training epochs
  batch: -1                  # Auto batch size
  imgsz: 640                 # Image size
  device: 0                  # GPU device
  workers: 8                 # Data loading workers
```

### `configs/export_config.yaml` - ONNX Export Configuration

```yaml
onnx_export:
  input_model: models/best.pt
  output_onnx: models/best.onnx
  imgsz: 640
  opset_version: 13
  simplify: true             # Use onnxsim for optimization
```

### `configs/rknn_config.yaml` - RKNN Conversion Configuration

```yaml
rknn_conversion:
  input_onnx: models/best.onnx
  output_rknn: models/best.rknn
  quantization_dataset: datasets/calibration/dataset.txt
  do_quantization: true
  target_platform: rk3588    # RK3588, RK3568, etc.
  mean_values: [[0, 0, 0]]
  std_values: [[255, 255, 255]]
```

## Dataset Tools

The pipeline includes several dataset processing utilities:

### Check for Overlapping Bounding Boxes

```bash
python src/dataset_tools.py check_overlaps --json-dir path/to/annotations --threshold 0.8
```

### Split Dataset into Train/Validation

```bash
python src/dataset_tools.py split_dataset \
    --image-dir datasets/yolo_dataset/train/images \
    --label-dir datasets/yolo_dataset/train/labels \
    --val-ratio 0.2
```

### Remove Unused Classes

```bash
python src/dataset_tools.py filter_classes \
    --label-dirs datasets/yolo_dataset/train/labels \
                   datasets/yolo_dataset/valid/labels \
    --remove-classes 6 7 8
```

### Prepare Calibration Dataset

```bash
python src/dataset_tools.py prepare_calibration \
    --image-dir datasets/yolo_dataset/train/images \
    --output datasets/calibration/dataset.txt \
    --num-images 20
```

## Complete Workflow Example

### Step 1: Setup Windows Environment

```powershell
.\setup_win.ps1
conda activate rknn-yolov8
```

### Step 2: Prepare and Train

```powershell
# Organize your dataset and update configs/data.yaml

# Train
python src/train.py --epochs 300

# Prepare calibration dataset (for quantization later)
python src/dataset_tools.py prepare_calibration \
    --image-dir datasets/yolo_dataset/train/images \
    --output datasets/calibration/dataset.txt
```

### Step 3: Export to ONNX (Windows)

```powershell
$env:PYTHONPATH = ".\"
python src/export/1_pt_to_onnx.py
```

### Step 4: Convert to RKNN (Ubuntu/WSL)

```bash
# In Ubuntu/WSL terminal
source rknn-env/bin/activate

# Copy the ONNX model
cp /mnt/c/path/to/models/best.onnx ./models/

# Calibration dataset should already be in datasets/calibration/dataset.txt
# If not, prepare it:
# python src/dataset_tools.py prepare_calibration \
#     --image-dir /mnt/c/path/to/training/images ...

# Convert
python src/export/2_onnx_to_rknn.py

# Output: models/best.rknn
```

## Supported Platforms

RKNN conversion supports multiple Rockchip platforms. Set in `configs/rknn_config.yaml`:

- `rk3588` (Recommended, most powerful)
- `rk3588s`
- `rk3568`
- `rk3566`
- `rk3562`

## Environment Management

### Windows

```powershell
# Activate
conda activate rknn-yolov8

# Deactivate
conda deactivate

# Remove (if needed)
conda env remove -n rknn-yolov8
```

### Ubuntu/WSL

```bash
# Activate
source rknn-env/bin/activate

# Deactivate
deactivate

# Remove (if needed)
rm -rf rknn-env
```

## Troubleshooting

### "PYTHONPATH not set" (Windows Export)

**Solution**: Before running export, set PYTHONPATH:

```powershell
$env:PYTHONPATH = ".\"
```

### "RKNN Toolkit2 not found" (WSL Conversion)

**Solution**: Ensure you're running on WSL/Ubuntu and the environment is activated:

```bash
source rknn-env/bin/activate
```

### "ONNX model not found"

**Solution**: Copy the ONNX model to `models/` directory or specify the path:

```bash
python src/export/2_onnx_to_rknn.py --input /path/to/your/model.onnx
```

### "Calibration dataset not found"

**Solution**: Prepare it first:

```bash
python src/dataset_tools.py prepare_calibration \
    --image-dir your_training_images_dir \
    --output datasets/calibration/dataset.txt
```

### Out of Memory During Conversion

**Solution**: Reduce the optimization level in `configs/rknn_config.yaml`:

```yaml
rknn_conversion:
  optimization_level: 1  # Instead of 3
```

## References

- [YOLOv8 Ultralytics](https://github.com/ultralytics/ultralytics)
- [Rockchip YOLOv8](https://github.com/airockchip/ultralytics_yolov8)
- [RKNN Toolkit2](https://github.com/airockchip/rknn-toolkit2)
- [RKNN Documentation](https://docs.rockchip.com/en/apis/rknpu2_api/rknpu2_core_api_common.html)

## Project Statistics

- **Training**: Uses Rockchip-customized YOLOv8 for NPU compatibility
- **Export**: ONNX format with optional simplification
- **Conversion**: INT8 quantization with calibration dataset support
- **Deployment**: Ready for Rockchip RK3588/RK3568 NPU

## License

This pipeline consolidates work from multiple open-source projects. Please refer to the licenses of:

- Ultralytics YOLOv8
- Rockchip YOLOv8 fork
- RKNN Toolkit2

## Notes

- All scripts are tested on Python 3.10
- ONNX export is performed on Windows with Rockchip's customized ultralytics
- RKNN conversion must be done on Ubuntu/WSL (x86_64 Linux required)
- Quantization significantly improves NPU inference performance

---

**Last Updated**: 2026年4月30日
**Maintainer**: YOLO Vision Pipeline Team
