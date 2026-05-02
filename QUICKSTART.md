# YOLO 视觉流水线 - 5分钟快速入门

以下是上手该流水线最快的方式。

## 前置条件

- 安装了 Miniconda/Anaconda 的 Windows 10/11
- 20GB 以上的可用磁盘空间
- NVIDIA GPU（可选，但强烈建议）
- Git

### 如果还没有安装 Miniconda

建议直接安装 Miniconda（比 Anaconda 更轻量，适合这个项目）：

1. 打开官方页面：<https://www.anaconda.com/download/success?reg=skipped>
2. 下载 Miniconda Windows x86_64 安装包
3. 运行安装程序，建议选择默认安装位置
4. 不建议勾选 Add installation to my PATH environment variable
5. 建议勾选 Register Miniconda3 as my default Python 3.13
6. 建议勾选 Clear the package cache upon completion
7. 安装完成后，重新打开 PowerShell，并执行：

```powershell
conda --version
```

如果提示找不到 `conda`，先在新终端中执行：

```powershell
conda init powershell
```

然后关闭并重新打开 PowerShell 再试一次。

## 第一步：设置项目路径（可选，推荐）

编辑 `configs/paths.yaml` 设置你的项目根目录，或者让它自动检测：

```yaml
# 自动检测（推荐）
project_root: null

# 或者手动指定 Windows 路径：
# project_root: C:\Users\YourUsername\Documents\GitHub\yolo-vision-pipeline-rknn
```

这个路径检查命令不依赖训练环境，首次克隆后就可以直接运行。

查看当前路径配置：

```powershell
python src/train.py --show-paths
```

## 第二步：克隆与环境配置（5分钟）

```powershell
# 以管理员身份打开 PowerShell
cd path/to/yolo-vision-pipeline-rknn

# 运行一次性安装脚本
.\setup_win.ps1

# 激活训练环境
conda activate rknn-yolov8-train
```

脚本会分别创建两个环境：

- `rknn-yolov8-train`：官方 Ultralytics 源码安装，用于训练
- `rknn-yolov8-export`：Rockchip Ultralytics 源码安装，用于 ONNX 导出

## 第二步补充：从视频抽帧（可选）

如果你有录制的视频文件，可以使用抽帧工具从视频中自动提取帧图像。

然后将视频放入 `datasets/videos/batch{N}/` 目录，使用以下命令抽帧：

```powershell
# 单个视频抽帧（每隔 30 帧取一帧）
python datasets/scripts/extract_frames.py --video datasets/videos/batch1/recording.mp4 --output datasets/raw/images/batch1 --every 30

# 或者批量抽帧（按目录）
python datasets/scripts/extract_frames.py --video-dir datasets/videos --output datasets/raw/images --batch-prefix batch1 --every 15
```

参数说明：

- `--every N`: 每隔 N 帧抽取 1 帧。若视频是 30fps，`--every 30` 表示每秒 1 帧；`--every 15` 表示每秒 2 帧。
- `--batch-prefix`: 输出文件名前缀（可选）。
- `--pattern`: 查找视频的文件模式，默认 `*.mp4`，也支持 `*.avi` 等。

详见 `datasets/videos/README.md`。

## 第三步：准备数据集（时间不定）

你的数据集应当符合 YOLO 格式：

```text
datasets/yolo_dataset/
├── train/
│   ├── images/  (你的 jpg 图片文件)
│   └── labels/  (YOLO 格式的 txt 标注文件)
└── valid/
    ├── images/
    └── labels/
```

### 数据清洗（可选但推荐）

在将图片放入 `datasets/yolo_dataset` 前，建议先对原始数据进行清洗，去除高度重复或近似重复的图片以减少训练冗余。

仓库提供了一个去重脚本：`datasets/scripts/deduplicate.py`，并附有使用说明 `datasets/cleaning/README.md`。

#### 示例命令

```powershell
# 预览（不移动/复制）
python datasets/scripts/deduplicate.py --src datasets/raw --dst datasets/cleaning/duplicates --threshold 4 --workers 0 --dry-run

# 确认后移动重复项
python datasets/scripts/deduplicate.py --src datasets/raw --dst datasets/cleaning/duplicates --threshold 4 --workers -4 --move
```

#### GUI 人工审核

如果需要更直观地查看和管理重复图像，可以使用 GUI 模式：

```powershell
python datasets/scripts/deduplicate.py --src datasets/raw --dst datasets/cleaning/duplicates --gui --threshold 4
```

GUI 会将相似图分组显示，并支持选择保留图后按组导出（每组包含 images/ 和 labels/）。

#### 参数说明

- `--threshold N`: 设置重复检测的敏感度，值越小越严格，GUI 模式下也支持此参数。
- `--workers N`: 并行计算线程数，`0` 表示单线程，`-1` 表示使用 CPU 核心数减 1。
- `--gui`: 启动图形界面模式，便于人工审核。

## 第四步：训练模型（1到数小时不等，取决于数据量）

```powershell
python src/train.py
```

模型将被保存至 `models/best.pt`。

## 第五步：导出为 ONNX 格式（5-10分钟）

先切换到导出环境：

```powershell
conda activate rknn-yolov8-export
```

然后导出：

```powershell
$env:PYTHONPATH = ".\"
python src/export/1_pt_to_onnx.py
```

输出文件：`models/best.onnx`

## 第六步：转换为 RKNN 格式（在 Ubuntu/WSL 环境下，10-20分钟）

### 仅限首次运行

```bash
cd /mnt/c/Users/你的用户名/path/to/yolo-vision-pipeline-rknn
bash setup_wsl.sh
source rknn-env/bin/activate
```

### 随后运行

```bash
# 从 Windows 环境中复制 ONNX 文件
cp /mnt/c/path/to/models/best.onnx ./models/

# 准备校准数据集（使用训练集图像）
python src/dataset_tools.py prepare_calibration \
    --image-dir /mnt/c/path/to/training/images \
    --output datasets/calibration/dataset.txt

# 转换模型
python src/export/2_onnx_to_rknn.py
```

输出文件：`models/best.rknn`

## 下一步做什么？

- **部署**：将 `models/best.rknn` 复制到你的 RK3588 设备上
- **优化**：在 `configs/train_config.yaml` 中调整模型大小或批次大小（batch size）
- **改进**：添加更多训练数据或尝试不同的模型变体

## 常见问题与故障排除

| 问题 | 解决方案 |
| --------- | ---------- |
| `PYTHONPATH` 环境变量错误 | 运行 `$env:PYTHONPATH = ".\"` |
| CUDA 显存不足 (out of memory) | 减小批次大小，例如：`--batch 8` |
| 找不到 RKNN toolkit | 运行 `source rknn-env/bin/activate` |

## 文件结构

```text
yolo-vision-pipeline-rknn/
├── configs/          ← 编辑这些 YAML 配置文件
│   ├── data.yaml     ← 你的类别和数据集路径
│   ├── train_config.yaml
│   ├── export_config.yaml
│   └── rknn_config.yaml
├── datasets/         ← 将你的数据存放在这里
│   ├── yolo_dataset/
│   └── calibration/
├── models/           ← 输出的模型保存在这里
├── src/              ← 脚本文件（请勿编辑）
│   ├── train.py
│   ├── export/
│   └── dataset_tools.py
├── README.md         ← 完整文档
├── setup_win.ps1
└── setup_wsl.sh
```

## 常用命令

```powershell
# Windows - 训练
python src/train.py --epochs 200

# Windows - 导出
$env:PYTHONPATH = ".\"
python src/export/1_pt_to_onnx.py

# Ubuntu/WSL - 准备校准数据
python src/dataset_tools.py prepare_calibration \
    --image-dir datasets/yolo_dataset/train/images \
    --output datasets/calibration/dataset.txt

# Ubuntu/WSL - 转换为 RKNN
python src/export/2_onnx_to_rknn.py
```

---

**从零开始到生成 .rknn 文件的总耗时大约为 2-8 小时，具体取决于：**

- 数据集的大小
- 模型的复杂度
- 硬件设备的运行速度

如需了解更详细的信息，请参阅 [README.md](../README.md) 和 [docs/workflow.md](../docs/workflow.md)。
