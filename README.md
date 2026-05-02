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

```text
yolo-vision-pipeline-rknn/
├── configs/                      # Configuration files
│   ├── data.yaml                 # Dataset configuration
│   ├── train_config.yaml         # Training hyperparameters
│   ├── export_config.yaml        # ONNX export settings
│   └── rknn_config.yaml          # RKNN conversion settings
├── datasets/                     # Dataset directory
│   ├── raw/                      # Original dataset files
│   │   ├── images/               # Original images (organized by batch)
│   │   └── labels/               # Corresponding YOLO format labels
│   ├── videos/                   # Video source files (optional)
│   ├── cleaning/                 # Data deduplication & cleaning
│   │   ├── README.md             # Deduplication guide
│   │   └── duplicates/           # Detected duplicate images
│   ├── calibration/              # Quantization calibration images
│   ├── yolo_dataset/             # Final organized YOLO dataset
│   │   ├── train/
│   │   └── valid/
│   └── scripts/                  # Dataset processing utilities
│       ├── deduplicate.py        # Image deduplication script
│       ├── extract_frames.py     # Video frame extraction
│       ├── download_hf_data.py
│       └── split_dataset.py
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
├── tools/                        # Utility tools
│   └── anylabeling/              # X-Anylabeling AI annotation tools
│       ├── models/               # ONNX models for AI annotation
│       ├── configs/              # X-Anylabeling model configurations
│       └── README.md             # X-Anylabeling setup guide
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

# Activate the training environment
conda activate rknn-yolov8-train

# The setup script clones and installs both YOLO repos from source, plus X-AnyLabeling:
# - rknn-yolov8-train for official Ultralytics training
# - rknn-yolov8-export for Rockchip ONNX export
# - x-anylabeling-cu12 for CUDA 12 labeling and annotation
```

#### 2. Extract Frames from Videos (Optional)

If you have recorded video files, use the frame extraction tool to automatically extract frames:

```powershell
# First install opencv-python
pip install opencv-python

# Single video extraction (every 30 frames)
python datasets/scripts/extract_frames.py --video datasets/videos/batch1/recording.mp4 --output datasets/raw/images/batch1 --every 30

# Or batch extraction from directory (preserve subfolder structure)
python datasets/scripts/extract_frames.py --video-dir datasets/videos --output datasets/raw/images --every 15

# Custom recursive pattern example (avi)
python datasets/scripts/extract_frames.py --video-dir datasets/videos --output datasets/raw/images --every 15 --pattern "**/*.avi"
```

In directory mode, extracted frames keep the relative folder layout. For example:

- `datasets/videos/batch1/*.mp4` -> `datasets/raw/images/batch1/`
- `datasets/videos/batch2/*.mp4` -> `datasets/raw/images/batch2/`

Default file discovery pattern is `**/*.mp4` (recursive).

See `datasets/videos/README.md` for detailed options.

#### 3. Prepare Your Dataset

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

### 数据清洗（去重工具）

为了减少训练集中的冗余样本，建议在整理 `datasets/yolo_dataset` 前先对 `datasets/raw` 进行去重与清洗。仓库包含去重工具：`datasets/scripts/deduplicate.py`。

#### 示例命令

```bash
# 预览（不移动/复制）
python datasets/scripts/deduplicate.py --src datasets/raw --images-subdir images --labels-subdir labels --dst datasets/cleaning/duplicates --threshold 4 --workers 0 --dry-run

# 确认后移动重复项
python datasets/scripts/deduplicate.py --src datasets/raw --images-subdir images --labels-subdir labels --dst datasets/cleaning/duplicates --threshold 4 --workers -4 --move
```

#### GUI 人工审核

如果需要更直观地查看和管理重复图像，可以使用 GUI 模式：

```bash
python datasets/scripts/deduplicate.py --src datasets/raw --dst datasets/cleaning/duplicates --gui --threshold 4
```

GUI 会将相似图分组显示，并支持选择保留图后按组导出（每组包含 images/ 和 labels/）。

#### 参数说明

- `--threshold N`: 设置重复检测的敏感度，值越小越严格，GUI 模式下也支持此参数。
- `--workers N`: 并行计算线程数，`0` 表示单线程，`-1` 表示使用 CPU 核心数减 1。
- `--gui`: 启动图形界面模式，便于人工审核。

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
# Switch to Rockchip export environment (important)
conda activate rknn-yolov8-export

# Set PYTHONPATH (important!)
$env:PYTHONPATH = ".\"

# Run export
python src/export/1_pt_to_onnx.py --purpose rknn --config configs/export_config.yaml
```

Output: `models/best.onnx`

#### 5. (Optional) Export to ONNX for X-Anylabeling AI Annotation

If you want to use X-Anylabeling for AI-assisted annotation during data labeling, export the model to the anylabeling tools directory:

```powershell
# Switch to official training environment (important)
conda activate rknn-yolov8-train

# Set PYTHONPATH (important!)
$env:PYTHONPATH = ".\"

# Export to X-Anylabeling models directory
python src/export/1_pt_to_onnx.py --purpose anylabeling --input models/best.pt --output tools/anylabeling/models/detection.onnx --imgsz 640 --simplify
```

Then configure the model in X-Anylabeling:

1. Launch **X-Anylabeling**
2. Go to **Menu** → **AI Features** → **Model Management**
3. Add the model: `tools/anylabeling/models/detection.onnx`
4. Use **Auto Label** feature for AI-assisted annotation

For detailed X-Anylabeling setup and configuration, see [tools/anylabeling/README.md](tools/anylabeling/README.md).

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
python src/dataset_tools.py prepare_calibration --image-dir datasets/yolo_dataset/train/images --output datasets/calibration/dataset.txt --num-images 20
```

#### 4. Convert ONNX to RKNN

```bash
# Copy ONNX model from Windows
cp /mnt/c/Users/YourUsername/.../best.onnx ./models/

# Activate the export environment before converting
conda activate rknn-yolov8-export

# Run conversion
python src/export/2_onnx_to_rknn.py --config configs/rknn_config.yaml
```

Output: `models/best.rknn`

## ⚙️ Path Configuration System

All paths in the pipeline are centralized in `configs/paths.yaml`. This keeps the training and export scripts aligned.

### Quick Setup

1. **Verify paths** (one-time):

  ```powershell
  python verify_paths.py
  ```

1. **View current configuration**:

  ```powershell
  python src/train.py --show-paths
  ```

   This path check uses only the standard library, so you can run it before installing the training dependencies.

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
  purpose: rknn            # rknn or anylabeling
  strict_backend_check: true
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
python src/dataset_tools.py split_dataset --image-dir datasets/yolo_dataset/train/images --label-dir datasets/yolo_dataset/train/labels --val-ratio 0.2
```

### Remove Unused Classes

```bash
python src/dataset_tools.py filter_classes --label-dirs datasets/yolo_dataset/train/labels datasets/yolo_dataset/valid/labels --remove-classes 6 7 8
```

### Prepare Calibration Dataset

```bash
python src/dataset_tools.py prepare_calibration --image-dir datasets/yolo_dataset/train/images --output datasets/calibration/dataset.txt --num-images 20
```

## Complete Workflow Example

### Step 1: Setup Windows Environment

```powershell
.\setup_win.ps1
conda activate rknn-yolov8-train
```

### Step 2: Prepare and Train

```powershell
# Organize your dataset and update configs/data.yaml

# Train
python src/train.py --epochs 300

# Prepare calibration dataset (for quantization later)
python src/dataset_tools.py prepare_calibration --image-dir datasets/yolo_dataset/train/images --output datasets/calibration/dataset.txt
```

### Step 3: Export to ONNX (Windows)

```powershell
# Use Rockchip export environment for RKNN path
conda activate rknn-yolov8-export

$env:PYTHONPATH = ".\"
python src/export/1_pt_to_onnx.py --purpose rknn
```

### Step 3.5: (Optional) Setup X-Anylabeling for AI-Assisted Annotation

If you want to use AI-assisted annotation for future labeling tasks:

```powershell
# Use official Ultralytics environment for X-Anylabeling path
conda activate rknn-yolov8-train

# Export model for X-Anylabeling
$env:PYTHONPATH = ".\"
python src/export/1_pt_to_onnx.py --purpose anylabeling --input models/best.pt --output tools/anylabeling/models/detection.onnx --simplify

# Launch X-Anylabeling and load the model
# Menu → AI Features → Model Management → Add Model
```

For more details, see [tools/anylabeling/README.md](tools/anylabeling/README.md).

### Step 5: Convert to RKNN (Ubuntu/WSL)

```bash
# In Ubuntu/WSL terminal
source rknn-env/bin/activate

# Copy the ONNX model
cp /mnt/c/path/to/models/best.onnx ./models/

# Activate the export environment before converting
conda activate rknn-yolov8-export

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
conda activate rknn-yolov8-train

# Deactivate
conda deactivate

# Remove (if needed)
conda env remove -n rknn-yolov8-train
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
python src/dataset_tools.py prepare_calibration --image-dir your_training_images_dir --output datasets/calibration/dataset.txt
```

### Out of Memory During Conversion

**Solution**: Reduce the optimization level in `configs/rknn_config.yaml`:

```yaml
rknn_conversion:
  optimization_level: 1  # Instead of 3
```

## 常用命令

### Windows PowerShell 操作

#### 清理临时文件和缓存

```powershell
# 删除所有 .json 文件
Remove-Item -Path *.json

# 删除所有 .json 文件（递归，当前目录及子目录）
Remove-Item -Path *.json -Recurse

# 删除 __pycache__ 目录（清理 Python 缓存）
Remove-Item -Path __pycache__ -Recurse -Force

# 删除所有 .pyc 文件
Remove-Item -Path *.pyc -Recurse

# 删除 .egg-info 目录
Remove-Item -Path *.egg-info -Recurse -Force

# 删除指定目录下的所有日志文件
Remove-Item -Path "logs/*.log"

# 安全删除模型文件（删除前确认）
Remove-Item -Path models/*.pt -WhatIf  # 预览，不实际删除
Remove-Item -Path models/*.pt          # 确认后执行
```

#### 查看文件和目录

```powershell
# 查看当前目录的所有文件和文件夹
Get-ChildItem

# 查看指定目录下所有 .pt 文件
Get-ChildItem -Path models -Filter "*.pt"

# 查看递归搜索所有 .onnx 文件
Get-ChildItem -Path . -Filter "*.onnx" -Recurse

# 查看目录大小
Get-ChildItem -Path models | Measure-Object -Property Length -Sum
```

#### 文件操作

```powershell
# 复制整个目录
Copy-Item -Path datasets/raw -Destination datasets/backup -Recurse

# 移动文件
Move-Item -Path models/old_model.pt -Destination models/archive/

# 创建目录
New-Item -ItemType Directory -Path datasets/new_folder

# 查看文件内容
Get-Content configs/data.yaml
```

### Ubuntu/WSL Bash 操作

#### 清理临时文件和缓存

```bash
# 删除所有 .json 文件
rm *.json

# 删除所有 .json 文件（递归）
find . -name "*.json" -delete

# 删除 __pycache__ 目录
find . -type d -name __pycache__ -exec rm -rf {} +

# 删除所有 .pyc 文件
find . -name "*.pyc" -delete

# 删除 .egg-info 目录
find . -type d -name "*.egg-info" -exec rm -rf {} +

# 删除指定目录下的日志文件
rm -f logs/*.log
```

#### 查看文件和目录

```bash
# 列出当前目录所有文件
ls -la

# 查看指定目录下所有 .pt 文件
ls -la models/*.pt

# 递归搜索所有 .onnx 文件
find . -name "*.onnx"

# 查看目录大小
du -sh models/
du -sh datasets/
```

#### 文件操作

```bash
# 复制整个目录
cp -r datasets/raw datasets/backup

# 移动文件
mv models/old_model.pt models/archive/

# 创建目录
mkdir -p datasets/new_folder

# 查看文件内容
cat configs/data.yaml
```

### 环境管理

```powershell
# Windows - 列出所有 conda 环境
conda env list

# Windows - 查看当前环境的包
conda list

# Windows - 升级 pip
python -m pip install --upgrade pip

# Windows - 卸载包
pip uninstall -y package_name
```

```bash
# Ubuntu/WSL - 列出所有 conda 环境
conda env list

# Ubuntu/WSL - 查看当前环境的包
conda list

# Ubuntu/WSL - 升级 pip
python -m pip install --upgrade pip

# Ubuntu/WSL - 卸载包
pip uninstall -y package_name
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
**Maintainer**: VaporTang
