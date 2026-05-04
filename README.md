# YOLO Vision Pipeline RKNN

**用于 YOLOv8 训练、导出并转换为 RKNN 格式以在瑞芯微 (Rockchip) NPU 上部署的统一工作流。**

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![YOLOv8](https://img.shields.io/badge/YOLOv8-Latest-green)
![Status](https://img.shields.io/badge/Status-Active-brightgreen)

## 概述

本项目将完整的 YOLOv8 → ONNX → RKNN 转换流程整合为一个结构清晰的单一代码库。它消除了以往分散在多个代码库中的繁杂工作流，并提供以下特性：

- 针对训练、导出和转换的**统一配置系统**
- 包含预处理工具的**有条理的数据集管理**
- 针对 Windows 和 Ubuntu/WSL 的**自动化环境设置**
- 针对工作流各个阶段的**生产级脚本**

## 项目结构

```text
yolo-vision-pipeline-rknn/
├── configs/                      # 配置文件
│   ├── data.yaml                 # 数据集配置
│   ├── train_config.yaml         # 训练超参数
│   ├── export_config.yaml        # ONNX 导出设置
│   └── rknn_config.yaml          # RKNN 转换设置
├── datasets/                     # 数据集目录
│   ├── raw/                      # 原始数据集文件
│   │   ├── images/               # 原始图像（按批次组织）
│   └── labels/                   # 对应的 YOLO 格式标签
│   ├── videos/                   # 视频源文件（可选）
│   ├── cleaning/                 # 数据去重与清洗
│   │   ├── README.md             # 去重指南
│   │   └── duplicates/           # 检测到的重复图像
│   ├── calibration/              # 量化校准图像
│   ├── yolo_dataset/             # 最终整理好的 YOLO 数据集
│   │   ├── train/
│   │   └── valid/
│   └── scripts/                  # 数据集处理工具脚本
│       ├── deduplicate.py        # 图像去重脚本
│       ├── extract_frames.py     # 视频抽帧脚本
│       ├── download_hf_data.py
│       └── split_dataset.py
├── models/                       # 训练和转换后的模型
│   └── training_results/         # 训练输出
├── src/                          # 源代码
│   ├── train.py                  # 统一训练脚本
│   ├── dataset_tools.py          # 数据集处理工具
│   ├── export/                   # 模型导出脚本
│   │   ├── 1_pt_to_onnx.py       # .pt → .onnx 导出
│   │   └── 2_onnx_to_rknn.py     # .onnx → .rknn 转换
│   └── utils/                    # 实用工具模块
│       └── dataset_utils.py      # 数据集操作函数
├── tools/                        # 扩展工具
│   └── anylabeling/              # X-Anylabeling AI 标注工具
│       ├── models/               # 用于 AI 标注的 ONNX 模型
│       ├── configs/              # X-Anylabeling 模型配置
│       └── README.md             # X-Anylabeling 设置指南
├── docs/                         # 文档
├── setup_win.ps1                 # Windows 安装脚本
└── setup_wsl.sh                  # Ubuntu/WSL 安装脚本
```

## 快速开始

### Windows: 训练与 ONNX 导出

#### 1. 初始设置（一次性）

```powershell
# 以管理员身份打开 PowerShell
cd path/to/yolo-vision-pipeline-rknn

# 运行安装脚本
.\setup_win.ps1

# 激活训练环境
conda activate rknn-yolov8-train

# 安装脚本会从源码克隆并安装两个 YOLO 仓库，以及 X-AnyLabeling：
# - rknn-yolov8-train：用于官方 Ultralytics 训练
# - rknn-yolov8-export：用于瑞芯微 ONNX 导出
# - x-anylabeling-cu12：用于基于 CUDA 12 的数据标记与注释
```

#### 2. 从视频中提取帧（可选）

如果您有录制的视频文件，可以使用帧提取工具自动抽帧：

```powershell
# 首先安装 opencv-python
pip install opencv-python

# 单个视频提取（每 30 帧提取一次）
python datasets/scripts/extract_frames.py --video datasets/videos/batch1/recording.mp4 --output datasets/raw/images/batch1 --every 30

# 或者从目录批量提取（保留子文件夹结构）
python datasets/scripts/extract_frames.py --video-dir datasets/videos --output datasets/raw/images --every 15

# 自定义递归模式示例 (avi)
python datasets/scripts/extract_frames.py --video-dir datasets/videos --output datasets/raw/images --every 15 --pattern "**/*.avi"
```

在目录模式下，提取的帧会保留相对的文件夹布局。例如：

- `datasets/videos/batch1/*.mp4` -> `datasets/raw/images/batch1/`
- `datasets/videos/batch2/*.mp4` -> `datasets/raw/images/batch2/`

默认的文件搜索模式为 `**/*.mp4`（递归）。

详细选项请参阅 `datasets/videos/README.md`。

#### 3. 准备数据集

```powershell
# 使用您的数据集路径更新 configs/data.yaml
# 文件结构应当如下：
# datasets/yolo_dataset/
#   ├── train/images/
#   │   ├── img1.jpg, img2.jpg, ...
#   │   └── img1.txt, img2.txt, ...  (YOLO 格式标签)
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

#### 4. 训练模型

```powershell
# 使用默认配置
python src/train.py

# 或者使用自定义参数
python src/train.py --data configs/data.yaml --epochs 300 --batch -1

# 或者覆盖配置文件
python src/train.py --config configs/train_config.yaml
```

最佳模型将保存至 `models/best.pt`。

#### 5. 导出为 ONNX

```powershell
# 切换至瑞芯微导出环境（重要）
conda activate rknn-yolov8-export

# 设置 PYTHONPATH（重要！）
$env:PYTHONPATH = ".\"

# 运行导出
python src/export/1_pt_to_onnx.py --purpose rknn --config configs/export_config.yaml
```

输出文件：`models/best.onnx`

说明：RKNN 导出默认使用 opset 12，并禁用 onnxsim 简化，以避免图结构变化导致 NPU 端无框问题。

#### 6. （可选）导出 ONNX 用于 X-Anylabeling AI 标注

如果您希望在数据标注时使用 X-Anylabeling 进行 AI 辅助标注，请将模型导出至 anylabeling 工具目录：

```powershell
# 切换至官方训练环境（重要）
conda activate rknn-yolov8-train

# 设置 PYTHONPATH（重要！）
$env:PYTHONPATH = ".\"

# 导出至 X-Anylabeling 模型目录
python src/export/1_pt_to_onnx.py --purpose anylabeling --input models/best.pt --output tools/anylabeling/models/detection.onnx --imgsz 640 --simplify
```

然后在 X-Anylabeling 中配置模型：

1. 启动 **X-Anylabeling**
2. 前往 **菜单 (Menu)** → **AI 功能 (AI Features)** → **模型管理 (Model Management)**
3. 添加模型：`tools/anylabeling/models/detection.onnx`
4. 使用 **自动标注 (Auto Label)** 功能进行 AI 辅助标注

有关 X-Anylabeling 详细设置和配置，请参阅 [tools/anylabeling/README.md](tools/anylabeling/README.md)。

### Ubuntu/WSL: ONNX 到 RKNN 的转换

#### 1. 在 WSL 上安装 Ubuntu 22.04（如果是 Windows 系统）

```powershell
# Windows PowerShell (管理员)
wsl --install -d Ubuntu-22.04
# 重启电脑
```

#### 2. 设置 WSL 环境（一次性）

```bash
# 在 Ubuntu/WSL 内部
cd /mnt/c/Users/YourUsername/Documents/GitHub/yolo-vision-pipeline-rknn

# 可选：在 WSL 文件系统上选择一个快速工作目录
export RKNN_WORKDIR=~/rknn-workdir

bash setup_wsl.sh

# 激活环境（创建在 RKNN_WORKDIR 下）
source ~/rknn-workdir/rknn-env/bin/activate
```

#### 3. 准备校准数据集

```bash
# 从训练集中提取 20-30 张具代表性的图像用于量化
python src/dataset_tools.py prepare_calibration --image-dir datasets/yolo_dataset/train/images --output datasets/calibration/dataset.txt --num-images 20
```

生成的 `datasets/calibration/dataset.txt` 现在包含图像的绝对路径，这是 RKNN Toolkit2 在量化期间所需要的格式。

#### 4. 将 ONNX 转换为 RKNN

```bash
# 从 Windows 复制 ONNX 模型
cp /mnt/c/Users/YourUsername/Documents/GitHub/yolo-vision-pipeline-rknn/models/best.onnx ./models/

# 激活 WSL 虚拟环境
source ~/rknn-workdir/rknn-env/bin/activate

# 运行转换
python src/export/2_onnx_to_rknn.py --config configs/rknn_config.yaml
```

输出文件：`models/best.rknn`

## ⚙️ 路径配置系统

工作流中的所有路径均集中管理在 `configs/paths.yaml` 中。这保持了训练和导出脚本的路径一致性。

### 快速设置

1. **验证路径**（一次性）：

  ```powershell
  python verify_paths.py
  ```

1. **查看当前配置**：

  ```powershell
  python src/train.py --show-paths
  ```

   路径检查仅使用标准库，因此您可以在安装训练依赖项之前运行它。

1. **自定义路径**（如果需要）：
  编辑 `configs/paths.yaml`：

  ```yaml
  project_root: null  # 自动检测，或设置绝对路径
   
  dataset:
    root: datasets/yolo_dataset
    train_images: datasets/yolo_dataset/train/images
    # ... 更多路径
   
  models:
    best_pt: models/best.pt
    best_onnx: models/best.onnx
    best_rknn: models/best.rknn
  ```

### 在 Python 中使用 PathManager

```python
from src.utils.path_manager import paths

# 获取一个路径
model_path = paths.get("models.best_pt")

# 获取路径字符串
model_str = paths.get_str("models.best_onnx")

# 确保目录存在
paths.ensure_dir("dataset.calibration_images")

# 获取某一节下的所有路径
all_models = paths.get_all("models")
```

📖 **完整指南**：请参阅 [PATH_SETUP.md](PATH_SETUP.md) 或 [docs/path_configuration.md](docs/path_configuration.md)

## 配置文件

### `configs/data.yaml` - 数据集配置

```yaml
path: datasets/yolo_dataset  # 数据集根目录
train: datasets/yolo_dataset/train/images
val: datasets/yolo_dataset/valid/images

nc: 6  # 类别数量
names:  # 类别名称
  0: yellow_ball
  1: blue_ball
  2: red_ball
  3: black_ball
  4: blue_placement_zone
  5: red_placement_zone
```

### `configs/train_config.yaml` - 训练配置

```yaml
training:
  model: yolov8l.pt          # 模型变体
  data: configs/data.yaml    # 数据集配置
  epochs: 300                # 训练轮数
  batch: -1                  # 自动批次大小
  imgsz: 640                 # 图像尺寸
  device: 0                  # GPU 设备 ID
  workers: 8                 # 数据加载工作线程数
```

### `configs/export_config.yaml` - ONNX 导出配置

```yaml
onnx_export:
  input_model: models/best.pt
  output_onnx: models/best.onnx
  purpose: rknn            # rknn 或 anylabeling
  strict_backend_check: true
  imgsz: 640
  opset_version: 13
  simplify: true             # 使用 onnxsim 进行优化
```

### `configs/rknn_config.yaml` - RKNN 转换配置

```yaml
rknn_conversion:
  input_onnx: models/best.onnx
  output_rknn: models/best.rknn
  quantization_dataset: datasets/calibration/dataset.txt
  do_quantization: true
  target_platform: rk3588    # RK3588, RK3568 等
  mean_values: [[0, 0, 0]]
  std_values: [[255, 255, 255]]
```

## 数据集工具

该流水线包含几个数据集处理工具：

### 检查边界框重叠

```bash
python src/dataset_tools.py check_overlaps --json-dir path/to/annotations --threshold 0.8
```

### 拆分训练集/验证集

```bash
python src/dataset_tools.py split_dataset --image-dir datasets/yolo_dataset/train/images --label-dir datasets/yolo_dataset/train/labels --val-ratio 0.2
```

### 从 raw 一步拆分到 yolo_dataset（自动移动）

```bash
python datasets/scripts/split_dataset.py --src datasets/raw --dst datasets/yolo_dataset --val-ratio 0.2 --seed 42
```

默认行为会把 `datasets/raw/images` 与 `datasets/raw/labels` 下可配对的数据，按比例随机划分并移动到：

- `datasets/yolo_dataset/train/images` + `datasets/yolo_dataset/train/labels`
- `datasets/yolo_dataset/valid/images` + `datasets/yolo_dataset/valid/labels`

如需仅预览不执行，可加 `--dry-run`；如需复制而非移动，可加 `--mode copy`。

### 移除未使用的类别

```bash
python src/dataset_tools.py filter_classes --label-dirs datasets/yolo_dataset/train/labels datasets/yolo_dataset/valid/labels --remove-classes 6 7 8
```

### 准备校准数据集

```bash
python src/dataset_tools.py prepare_calibration --image-dir datasets/yolo_dataset/train/images --output datasets/calibration/dataset.txt --num-images 20
```

## 完整工作流示例

### 第 1 步：设置 Windows 环境

```powershell
.\setup_win.ps1
conda activate rknn-yolov8-train
```

### 第 2 步：准备与训练

```powershell
# 整理您的数据集并更新 configs/data.yaml

# 训练
python src/train.py --epochs 300

# 准备校准数据集（供后续量化使用）
python src/dataset_tools.py prepare_calibration --image-dir datasets/yolo_dataset/train/images --output datasets/calibration/dataset.txt
```

### 第 3 步：导出为 ONNX (Windows)

```powershell
# 使用瑞芯微导出环境以匹配 RKNN 路径要求
conda activate rknn-yolov8-export

$env:PYTHONPATH = ".\"
python src/export/1_pt_to_onnx.py --purpose rknn
```

### 第 3.5 步：（可选）设置 X-Anylabeling 进行 AI 辅助标注

如果您希望在未来的标注任务中使用 AI 辅助标注：

```powershell
# 使用官方 Ultralytics 环境以匹配 X-Anylabeling 路径要求
conda activate rknn-yolov8-train

# 为 X-Anylabeling 导出模型
$env:PYTHONPATH = ".\"
python src/export/1_pt_to_onnx.py --purpose anylabeling --input models/best.pt --output tools/anylabeling/models/detection.onnx --simplify

# 启动 X-Anylabeling 并加载模型
# 菜单 (Menu) → AI 功能 (AI Features) → 模型管理 (Model Management) → 添加模型 (Add Model)
```

更多详细信息，请参阅 [tools/anylabeling/README.md](tools/anylabeling/README.md)。

### 第 5 步：转换为 RKNN (Ubuntu/WSL)

```bash
# 在 Ubuntu/WSL 终端中
source ~/rknn-workdir/rknn-env/bin/activate

# 复制 ONNX 模型
cp /mnt/c/path/to/models/best.onnx ./models/

# 校准数据集应该已经存在于 datasets/calibration/dataset.txt 中
# 如果没有，请生成它：
# python src/dataset_tools.py prepare_calibration --image-dir /mnt/c/path/to/training/images --output datasets/calibration/dataset.txt --num-images 20

# 执行转换
python src/export/2_onnx_to_rknn.py

# 输出文件：models/best.rknn
```

## 支持的平台

RKNN 转换支持多种瑞芯微平台。请在 `configs/rknn_config.yaml` 中设置：

- `rk3588` (推荐，性能最强)
- `rk3588s`
- `rk3568`
- `rk3566`
- `rk3562`

## 环境管理

### Windows

```powershell
# 激活环境
conda activate rknn-yolov8-train

# 退出环境
conda deactivate

# 移除环境（如果需要）
conda env remove -n rknn-yolov8-train
```

### Ubuntu/WSL

```bash
# 激活环境
source ~/rknn-workdir/rknn-env/bin/activate

# 退出环境
deactivate

# 移除环境（如果需要）
rm -rf ~/rknn-workdir/rknn-env
```

## 故障排除

### "PYTHONPATH not set" (Windows 导出时)

**解决方案**：在运行导出脚本前，设置 PYTHONPATH：

```powershell
$env:PYTHONPATH = ".\"
```

### "RKNN Toolkit2 not found" (WSL 转换时)

**解决方案**：确保您正在 WSL/Ubuntu 上运行，并且已经激活了对应环境：

```bash
source ~/rknn-workdir/rknn-env/bin/activate
```

### "No module named 'yaml'"

**解决方案**：在 WSL 虚拟环境中安装 PyYAML：

```bash
pip install pyyaml
```

### "ONNX model not found"

**解决方案**：将 ONNX 模型复制到 `models/` 目录，或者指定确切路径：

```bash
python src/export/2_onnx_to_rknn.py --input /path/to/your/model.onnx
```

### "Calibration dataset not found"

**解决方案**：请先准备校准数据集：

```bash
python src/dataset_tools.py prepare_calibration --image-dir your_training_images_dir --output datasets/calibration/dataset.txt
```

### 转换期间出现内存不足 (Out of Memory)

**解决方案**：在 `configs/rknn_config.yaml` 中降低优化级别：

```yaml
rknn_conversion:
  optimization_level: 1  # 默认是 3，将其改小
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

## 参考资料

- [YOLOv8 Ultralytics](https://github.com/ultralytics/ultralytics)
- [Rockchip YOLOv8 分支](https://github.com/airockchip/ultralytics_yolov8)
- [RKNN Toolkit2](https://github.com/airockchip/rknn-toolkit2)
- [RKNN 文档](https://docs.rockchip.com/en/apis/rknpu2_api/rknpu2_core_api_common.html)

## 项目统计

- **训练**：使用瑞芯微定制版的 YOLOv8 以确保 NPU 兼容性
- **导出**：使用 ONNX 格式，支持可选项简化 (simplify)
- **转换**：INT8 量化，支持校准数据集
- **部署**：已准备好部署于瑞芯微 RK3588/RK3568 NPU

## 许可证

此流水线整合了多个开源项目的工作。请参考以下项目的许可证：

- Ultralytics YOLOv8
- Rockchip YOLOv8 fork
- RKNN Toolkit2

## 注意事项

- 所有脚本均在 Python 3.10 上测试通过
- ONNX 导出在 Windows 上的瑞芯微定制版 ultralytics 环境中执行
- RKNN 转换必须在 Ubuntu/WSL（需要 x86_64 Linux）上执行
- 量化处理能够显著提升 NPU 推理性能

---

**最后更新**：2026年5月3日
**维护者**：VaporTang
