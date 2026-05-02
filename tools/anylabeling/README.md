# X-Anylabeling AI 辅助标注工具

本目录用于存放 X-Anylabeling 的 AI 辅助标注相关文件，包括模型权重和配置文件。

## 目录结构

```
tools/anylabeling/
├── models/                  # AI 标注模型权重
│   ├── detection.onnx       # YOLO 物体检测模型
│   ├── pose.onnx           # （可选）姿态估计模型
│   └── segmentation.onnx   # （可选）分割模型
├── configs/                # X-Anylabeling 配置文件
│   ├── anylabeling.ini     # 主配置文件
│   └── model_config.yaml   # 模型配置文件
└── README.md              # 本文件
```

## 模型转换指南

### 将训练的 YOLOv8 模型转换为 ONNX

X-Anylabeling 的 AI 功能需要 ONNX 格式的模型。以下是转换步骤：

#### 步骤 1：导出为 ONNX 格式

在 Windows 上执行转换：

```powershell
# 激活训练环境
conda activate rknn-yolov8-train

# 设置 PYTHONPATH（重要！）
$env:PYTHONPATH = ".\"

# 运行导出脚本
python src/export/1_pt_to_onnx.py --config configs/export_config.yaml

# 或指定特定的 pt 模型
python src/export/1_pt_to_onnx.py --input models/best.pt --output tools/anylabeling/models/detection.onnx
```

**输出**: `tools/anylabeling/models/detection.onnx`

#### 步骤 2：验证 ONNX 模型

```python
import onnx

# 加载并验证模型
model = onnx.load('tools/anylabeling/models/detection.onnx')
onnx.checker.check_model(model)
print("✓ ONNX 模型验证通过！")
```

### 导出配置 (`configs/export_config.yaml`)

```yaml
# ONNX 导出配置
onnx_export:
  # 输入模型（训练后的 YOLOv8 权重）
  input_model: models/best.pt
  
  # 输出 ONNX 模型路径（用于 X-Anylabeling）
  output_onnx: tools/anylabeling/models/detection.onnx
  
  # 模型输入尺寸
  imgsz: 640
  
  # ONNX Opset 版本（建议使用 13 或以上）
  opset_version: 13
  
  # 是否使用 onnxsim 简化模型（推荐 True）
  simplify: true
  
  # 设备（CPU 或 GPU）
  device: 0  # GPU device ID，或使用 'cpu'
```

## X-Anylabeling 配置

### 1. 配置文件位置

X-Anylabeling 的配置通常存储在：

- **Windows**: `%APPDATA%\x-anylabeling\`
- **Linux**: `~/.config/x-anylabeling/`
- **macOS**: `~/Library/Application Support/x-anylabeling/`

### 2. 在 X-Anylabeling 中加载 ONNX 模型

启动 X-Anylabeling 后：

1. 菜单 → **AI Features** → **Model Management**
2. 点击 **Add Model**
3. 选择模型类型：**Object Detection** (YOLOv8)
4. 选择 ONNX 文件：`tools/anylabeling/models/detection.onnx`
5. 配置模型参数：
   - **Model Input Size**: 640×640
   - **Confidence Threshold**: 0.5
   - **IOU Threshold**: 0.45
6. 保存并测试

### 3. 模型配置文件示例 (`tools/anylabeling/configs/model_config.yaml`)

```yaml
# X-Anylabeling YOLO 模型配置
model:
  # 模型基本信息
  name: "YOLO v8 Detection"
  type: "object_detection"
  framework: "onnx"
  
  # 模型路径
  path: "models/detection.onnx"
  
  # 输入配置
  input:
    size: 640
    channels: 3
    format: "RGB"
    normalize: true
    mean: [0.0, 0.0, 0.0]
    std: [1.0, 1.0, 1.0]
  
  # 输出配置
  output:
    # YOLO 输出格式：[x_center, y_center, width, height, confidence, class_0, class_1, ...]
    format: "yolo"
    num_classes: 6
    class_names:
      - "yellow_ball"
      - "blue_ball"
      - "red_ball"
      - "black_ball"
      - "blue_placement_zone"
      - "red_placement_zone"
  
  # 推理配置
  inference:
    confidence_threshold: 0.5
    iou_threshold: 0.45
    # 执行提供者（CUDA 优先，其次 CPU）
    execution_providers: ["CUDAExecutionProvider", "CPUExecutionProvider"]
  
  # 性能配置
  performance:
    max_batch_size: 1
    use_fp16: true  # 半精度浮点（需要 GPU 支持）
```

## 使用 AI 标注功能

### 启用自动检测

1. 在 X-Anylabeling 中打开图像或视频
2. 菜单 → **AI Features** → **Auto Label** 或按快捷键
3. 工具将使用加载的 ONNX 模型自动生成标注
4. 根据需要手动调整和修正

### 批量标注

```bash
# 使用命令行进行批量标注（如果 X-Anylabeling 支持）
x-anylabeling --input datasets/raw/images --model tools/anylabeling/models/detection.onnx --output datasets/yolo_dataset/train/labels --auto-save
```

## 常见问题

### Q: ONNX 模型太大怎么办？

**A**: 使用量化或模型压缩：

```python
# 使用 onnxruntime 进行量化
from onnxruntime.quantization import quantize_dynamic, QuantType

quantize_dynamic(
    "tools/anylabeling/models/detection.onnx",
    "tools/anylabeling/models/detection_quantized.onnx",
    weight_type=QuantType.QInt8
)
```

### Q: 推理速度慢怎么办？

**A**: 检查以下内容：

1. 确认使用了 GPU（CUDA）
2. 在模型配置中启用 FP16
3. 降低输入图像尺寸（如改为 480×480）
4. 禁用不必要的后处理步骤

### Q: 如何转换其他模型格式？

**A**: X-Anylabeling 支持以下格式：

- ONNX（推荐）
- TensorFlow (.pb, .tflite)
- PyTorch (.pt, .pth)
- OpenVINO (.xml, .bin)
- CoreML (.mlmodel)
- TensorRT (.engine)

参考 [X-Anylabeling 文档](https://github.com/cpeterann/x-anylabeling) 了解其他格式的转换方式。

## 技巧与最佳实践

### 1. 针对不同场景优化模型

```yaml
# 高精度模式（较慢但准确度高）
inference:
  confidence_threshold: 0.6
  iou_threshold: 0.4

# 高速模式（快速但可能漏检）
inference:
  confidence_threshold: 0.4
  iou_threshold: 0.5
```

### 2. 定期重新训练和导出

建议在收集了足够的新标注数据后，定期重新训练模型并导出新的 ONNX 文件：

```powershell
# 完整的更新流程
$env:PYTHONPATH = ".\"

# 1. 训练新模型
python src/train.py --epochs 300 --data configs/data.yaml

# 2. 导出为 ONNX
python src/export/1_pt_to_onnx.py --input models/best.pt --output tools/anylabeling/models/detection.onnx

# 3. 在 X-Anylabeling 中重新加载模型
```

### 3. 版本管理

为不同版本的模型保留备份：

```
tools/anylabeling/models/
├── detection_v1.onnx       # 初始版本
├── detection_v2.onnx       # 改进版本
├── detection_latest.onnx   # 当前使用的版本（符号链接或副本）
```

## 相关资源

- [X-Anylabeling GitHub](https://github.com/cpeterann/x-anylabeling)
- [X-Anylabeling 文档](https://x-anylabeling.readthedocs.io/)
- [ONNX 文档](https://onnx.ai/)
- [YOLOv8 导出指南](https://docs.ultralytics.com/modes/export/)

## 更新日志

- **2026-05-02**: 初始创建，添加 ONNX 转换和配置指南
