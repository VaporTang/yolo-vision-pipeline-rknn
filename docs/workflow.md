# YOLO Vision Pipeline - Complete Workflow Guide

This guide walks you through the complete process from dataset preparation to RKNN deployment.

## Table of Contents

1. [Environment Setup](#environment-setup)
2. [Dataset Preparation](#dataset-preparation)
3. [Model Training](#model-training)
4. [Model Export](#model-export)
5. [RKNN Conversion](#rknn-conversion)
6. [Deployment](#deployment)

---

## Environment Setup

### Windows Setup

**Prerequisites:**

- Windows 10/11 with admin access
- 20+ GB free disk space
- NVIDIA GPU (RTX 3060 or better recommended)
- Miniconda or Anaconda installed

**Steps:**

1. Open PowerShell as Administrator
2. Navigate to project directory
3. Run the setup script:

```powershell
.\setup_win.ps1
```

This script will:

- Create a Conda environment named `rknn-yolov8`
- Install PyTorch with CUDA support
- Clone and install Rockchip's customized YOLOv8
- Install all required dependencies

1. Verify installation:

```powershell
conda activate rknn-yolov8
python -c "import torch; print(f'PyTorch version: {torch.__version__}')"
python -c "from ultralytics import YOLO; print('YOLO imported successfully')"
```

### WSL/Ubuntu Setup

**Prerequisites (on WSL):**

- Ubuntu 22.04 LTS installed on WSL2
- 10+ GB free disk space
- Sufficient RAM (8+ GB recommended)

**Steps:**

1. Open Ubuntu terminal
2. Navigate to project directory:

```bash
cd /mnt/c/Users/YourUsername/path/to/yolo-vision-pipeline-rknn
```

1. Run setup script:

```bash
bash setup_wsl.sh
```

1. Verify installation:

```bash
source rknn-env/bin/activate
python -c "from rknn.api import RKNN; print('RKNN Toolkit2 imported successfully')"
```

---

## Dataset Preparation

### Dataset Format

YOLO expects the following directory structure:

```
datasets/yolo_dataset/
├── train/
│   ├── images/
│   │   ├── img_001.jpg
│   │   ├── img_002.jpg
│   │   └── ...
│   └── labels/
│       ├── img_001.txt  (YOLO format: <class> <x> <y> <w> <h>)
│       ├── img_002.txt
│       └── ...
└── valid/
    ├── images/
    │   ├── val_001.jpg
    │   └── ...
    └── labels/
        ├── val_001.txt
        └── ...
```

### YOLO Label Format

Each `.txt` file contains one line per object:

```
<class_id> <x_center> <y_center> <width> <height>
```

Where coordinates are **normalized** to 0-1:

- `x_center`: center X position / image_width
- `y_center`: center Y position / image_height
- `width`: bounding box width / image_width
- `height`: bounding box height / image_height

**Example:**

```
0 0.5 0.5 0.3 0.4
2 0.2 0.3 0.1 0.2
```

### Dataset Configuration

Edit `configs/data.yaml`:

```yaml
path: datasets/yolo_dataset
train: datasets/yolo_dataset/train/images
val: datasets/yolo_dataset/valid/images

nc: 6  # Number of classes
names:
  0: yellow_ball
  1: blue_ball
  2: red_ball
  3: black_ball
  4: blue_placement_zone
  5: red_placement_zone
```

### Dataset Processing Tools

#### Check for Overlapping Bounding Boxes

```bash
python src/dataset_tools.py check_overlaps \
    --json-dir datasets/annotations \
    --threshold 0.8
```

#### Split Dataset

```bash
python src/dataset_tools.py split_dataset \
    --image-dir datasets/yolo_dataset/train/images \
    --label-dir datasets/yolo_dataset/train/labels \
    --val-ratio 0.2  # 20% validation
```

#### Filter Classes

Remove classes 6, 7, 8 (e.g., if upgrading from v5 to v7 dataset):

```bash
python src/dataset_tools.py filter_classes \
    --label-dirs datasets/yolo_dataset/train/labels \
                   datasets/yolo_dataset/valid/labels \
    --remove-classes 6 7 8
```

---

## Model Training

### Training Configuration

Edit `configs/train_config.yaml`:

```yaml
training:
  model: yolov8l.pt      # yolov8n, yolov8s, yolov8m, yolov8l, yolov8x
  data: configs/data.yaml
  epochs: 300
  batch: -1              # Auto batch size
  imgsz: 640
  device: 0              # GPU device ID
  workers: 8
  patience: 50           # EarlyStopping patience
  project: models/training_results
  name: yolo_train
  close_mosaic: 10       # Disable mosaic in final epochs
  save_period: 10        # Save checkpoint every 10 epochs
```

### Model Variants

| Variant | Size | Speed | Accuracy | Use Case |
|---------|------|-------|----------|----------|
| `yolov8n` | 3.2M | Fast | Lower | Resource-constrained |
| `yolov8s` | 11.2M | Good | Good | Balanced |
| `yolov8m` | 25.9M | Medium | High | Production |
| `yolov8l` | 52.9M | Slower | Higher | High accuracy needed |
| `yolov8x` | 107.3M | Slowest | Highest | Maximum accuracy |

**Recommendation for RK3588:** Use `yolov8l` for good accuracy with acceptable NPU speed.

### Training Process

#### Basic Training

```powershell
conda activate rknn-yolov8
python src/train.py
```

#### Custom Training

```powershell
# Override specific parameters
python src/train.py \
    --epochs 200 \
    --batch 16 \
    --device 0
```

#### Resume Training

```powershell
# If training was interrupted
python src/train.py --config configs/train_config.yaml
```

### Training Outputs

Training results saved to `models/training_results/yolo_train/`:

```
yolo_train/
├── weights/
│   ├── best.pt      # Best model (lowest validation loss)
│   ├── last.pt      # Last checkpoint
│   └── epoch*.pt    # Checkpoint at each epoch
├── results.csv      # Training metrics
├── confusion_matrix.png
└── results.png
```

**Key files:**

- `best.pt` - Use this for export to ONNX
- `results.csv` - Training history for analysis

---

## Model Export

### Export Configuration

Edit `configs/export_config.yaml`:

```yaml
onnx_export:
  input_model: models/best.pt
  output_onnx: models/best.onnx
  imgsz: 640
  opset_version: 13
  simplify: true
  device: 0
```

### Export Process (Windows)

**Important:** Set PYTHONPATH before export!

```powershell
# Set environment variable
$env:PYTHONPATH = ".\"

# Run export
python src/export/1_pt_to_onnx.py
```

### ONNX Export Options

```powershell
# Use default config
python src/export/1_pt_to_onnx.py

# Override input/output paths
python src/export/1_pt_to_onnx.py \
    --input custom_model.pt \
    --output custom_model.onnx

# Simplify with onnxsim
python src/export/1_pt_to_onnx.py --simplify
```

### What Gets Exported

RKNN requires a stripped-down ONNX model without post-processing:

- Input: 640×640×3 RGB images
- Output: Raw bounding box predictions (no NMS)
- Post-processing (NMS, class filtering) happens on the host

The Rockchip customized ultralytics automatically handles this.

---

## RKNN Conversion

### Prerequisites

- Ubuntu 22.04 (or WSL)
- RKNN Toolkit2 installed
- ONNX model ready (`models/best.onnx`)
- Calibration images prepared

### Prepare Calibration Dataset

For INT8 quantization, you need 20-30 representative training images:

```bash
python src/dataset_tools.py prepare_calibration \
    --image-dir datasets/yolo_dataset/train/images \
    --output datasets/calibration/dataset.txt \
    --num-images 20
```

This creates `datasets/calibration/dataset.txt` listing image filenames.

### RKNN Conversion Configuration

Edit `configs/rknn_config.yaml`:

```yaml
rknn_conversion:
  input_onnx: models/best.onnx
  output_rknn: models/best.rknn
  quantization_dataset: datasets/calibration/dataset.txt
  do_quantization: true
  target_platform: rk3588  # Choose your platform
  mean_values: [[0, 0, 0]]
  std_values: [[255, 255, 255]]
  optimization_level: 3
  verbose: true
```

### Target Platforms

Choose based on your hardware:

| Platform | Specs | Use Case |
|----------|-------|----------|
| `rk3588` | Quad-core A76 + quad-core A55 | Recommended |
| `rk3588s` | Similar to RK3588 | Consumer devices |
| `rk3568` | Quad-core A55 | Older devices |
| `rk3566` | Dual-core A55 + dual-core A55 | Low-power |
| `rk3562` | Quad-core A55 | Budget devices |

### Conversion Process

On Ubuntu/WSL:

```bash
# Activate environment
source rknn-env/bin/activate

# Copy ONNX from Windows
cp /mnt/c/path/to/models/best.onnx ./models/

# Run conversion
python src/export/2_onnx_to_rknn.py
```

### Conversion Options

```bash
# Use default config
python src/export/2_onnx_to_rknn.py

# Convert without quantization (larger file, higher accuracy)
python src/export/2_onnx_to_rknn.py --no-quant

# Specify target platform
python src/export/2_onnx_to_rknn.py --platform rk3568

# Use custom paths
python src/export/2_onnx_to_rknn.py \
    --input /path/to/model.onnx \
    --output /path/to/output.rknn \
    --dataset /path/to/dataset.txt
```

### Conversion Output

- **Quantized INT8**: ~15-20 MB (fast inference, minimal accuracy loss)
- **Float32**: ~50+ MB (accurate, slower)

---

## Deployment

### RK3588 Deployment

1. **Transfer RKNN model** to device:

```bash
scp models/best.rknn user@device:/path/to/
```

1. **Install RKNN Runtime** on device (if not already):

```bash
# On RK3588
python -m pip install rknn-toolkit2-lite
```

1. **Inference code example:**

```python
from rknn.api import RKNN_LITE
import cv2
import numpy as np

# Create runtime
rknn_lite = RKNN_LITE(verbose=False)

# Load model
ret = rknn_lite.load_rknn("best.rknn")
assert ret == 0, "Failed to load RKNN model"

# Load image
img = cv2.imread("test.jpg")
img_resized = cv2.resize(img, (640, 640))
img_normalized = img_resized / 255.0

# Inference
outputs = rknn_lite.inference(inputs=[img_normalized])

# Process outputs (depends on your post-processing)
# outputs typically contains:
# - output0: raw bounding box predictions
# - output1: objectness scores
# - output2: class probabilities

rknn_lite.release()
```

### Model Optimization Tips

| Technique | File Size | Speed | Accuracy |
|-----------|-----------|-------|----------|
| INT8 Quantization | ↓ 75% | ↑ 20-30% | ↓ 1-2% |
| Layer fusion | ↓ 5% | ↑ 5-10% | Same |
| Pruning | ↓ 30% | ↑ 10% | ↓ 3% |

---

## Troubleshooting

### Training Issues

**CUDA out of memory:**

```powershell
# Reduce batch size
python src/train.py --batch 8  # Instead of auto
```

**Training too slow:**

```powershell
# Use smaller model
python src/train.py --model yolov8m.pt  # Instead of yolov8l
```

### Export Issues

**"PYTHONPATH not set":**

```powershell
$env:PYTHONPATH = ".\"
```

**"ultralytics not found":**

- Ensure you cloned `ultralytics_yolov8` in `3rdparty/`
- Run: `pip install -e 3rdparty/ultralytics_yolov8`

### Conversion Issues

**"RKNN Toolkit2 not found":**

```bash
source rknn-env/bin/activate
```

**Quantization fails:**

- Check `datasets/calibration/dataset.txt` exists
- Ensure images are readable JPEG/PNG

**Out of memory during conversion:**

```yaml
# In rknn_config.yaml
optimization_level: 1  # Reduce from 3
```

---

## Performance Benchmarks

Estimated on RK3588 with INT8 quantization:

| Model | Latency | FPS | Memory |
|-------|---------|-----|--------|
| YOLOv8n | 8ms | 125 | 50MB |
| YOLOv8s | 15ms | 67 | 100MB |
| YOLOv8m | 25ms | 40 | 200MB |
| YOLOv8l | 40ms | 25 | 300MB |
| YOLOv8x | 60ms | 17 | 400MB |

*Note: Actual performance depends on image resolution and quantization method.*

---

## Next Steps

1. Prepare your dataset in YOLO format
2. Configure `configs/data.yaml`
3. Run training on Windows
4. Export to ONNX
5. Convert to RKNN on WSL/Ubuntu
6. Deploy to RK3588 device

Good luck with your YOLO journey! 🚀
