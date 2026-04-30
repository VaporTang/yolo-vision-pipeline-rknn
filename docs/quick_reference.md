# YOLO Vision Pipeline - Quick Reference

## Common Commands

### Training

```powershell
conda activate rknn-yolov8
python src/train.py
python src/train.py --epochs 200 --batch 32
python src/train.py --model yolov8s.pt  # Smaller model
```

### Export to ONNX

```powershell
$env:PYTHONPATH = ".\"
python src/export/1_pt_to_onnx.py
```

### Prepare Calibration Data

```bash
python src/dataset_tools.py prepare_calibration \
    --image-dir datasets/yolo_dataset/train/images \
    --output datasets/calibration/dataset.txt
```

### Convert to RKNN

```bash
source rknn-env/bin/activate
python src/export/2_onnx_to_rknn.py
```

### Dataset Tools

```bash
# Check overlaps
python src/dataset_tools.py check_overlaps \
    --json-dir path/to/annotations

# Split train/valid
python src/dataset_tools.py split_dataset \
    --image-dir train/images \
    --label-dir train/labels

# Remove classes
python src/dataset_tools.py filter_classes \
    --label-dirs train/labels valid/labels \
    --remove-classes 6 7 8
```

## Configuration Quick Reference

### data.yaml

```yaml
path: datasets/yolo_dataset
train: datasets/yolo_dataset/train/images
val: datasets/yolo_dataset/valid/images
nc: 6
names: [class0, class1, ...]
```

### train_config.yaml

```yaml
training:
  model: yolov8l.pt
  epochs: 300
  batch: -1
  imgsz: 640
  device: 0
  workers: 8
```

### export_config.yaml

```yaml
onnx_export:
  input_model: models/best.pt
  output_onnx: models/best.onnx
  imgsz: 640
  simplify: true
```

### rknn_config.yaml

```yaml
rknn_conversion:
  input_onnx: models/best.onnx
  output_rknn: models/best.rknn
  quantization_dataset: datasets/calibration/dataset.txt
  do_quantization: true
  target_platform: rk3588
```

## File Locations

| Purpose | Location |
|---------|----------|
| Training dataset | `datasets/yolo_dataset/` |
| Calibration data | `datasets/calibration/` |
| Trained models | `models/best.pt` |
| ONNX export | `models/best.onnx` |
| RKNN model | `models/best.rknn` |
| Configuration | `configs/` |
| Scripts | `src/` |

## Model Sizes (Approximate)

| Model | .pt | .onnx | .rknn (INT8) |
|-------|-----|-------|------------|
| YOLOv8n | 6MB | 12MB | 3MB |
| YOLOv8s | 22MB | 45MB | 11MB |
| YOLOv8m | 50MB | 100MB | 25MB |
| YOLOv8l | 100MB | 200MB | 50MB |
| YOLOv8x | 200MB | 400MB | 100MB |

## Environment Variables

### Windows (PowerShell)

```powershell
# Required for ONNX export
$env:PYTHONPATH = ".\"
```

### Linux/WSL

```bash
# Optional, usually set by setup script
export PYTHONPATH=./
```

## Conda Environment

```powershell
# List environments
conda env list

# Activate
conda activate rknn-yolov8

# Deactivate
conda deactivate

# Remove
conda env remove -n rknn-yolov8

# Clone for backup
conda create --name rknn-yolov8-backup --clone rknn-yolov8
```

## Common Issues & Solutions

| Issue | Solution |
|-------|----------|
| CUDA out of memory | Reduce batch size: `--batch 8` |
| ONNX export fails | Set PYTHONPATH: `$env:PYTHONPATH = ".\"` |
| RKNN toolkit not found | Activate env: `source rknn-env/bin/activate` |
| Calibration dataset not found | Prepare it: `prepare_calibration --image-dir ...` |
| Model accuracy too low | Increase epochs or use larger model variant |
| Slow inference | Use smaller model or INT8 quantization |

## YOLO Label Format

File: `image.txt`

```
0 0.5 0.5 0.3 0.4
2 0.2 0.3 0.1 0.2
```

Format: `<class_id> <x_center> <y_center> <width> <height>`

- Coordinates normalized to 0-1
- One line per object

## Inference Example (Python)

```python
from ultralytics import YOLO

# Load model
model = YOLO("models/best.pt")

# Inference
results = model.predict(source="image.jpg", conf=0.5)

# Access predictions
for result in results:
    boxes = result.boxes
    for box in boxes:
        print(f"Class: {box.cls}, Confidence: {box.conf}")
```

---

For detailed information, see [workflow.md](workflow.md) or [README.md](../README.md)
