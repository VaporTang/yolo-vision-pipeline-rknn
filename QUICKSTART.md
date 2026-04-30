# YOLO 视觉流水线 - 5分钟快速入门

以下是上手该流水线最快的方式。

## 前置条件

- 安装了 Miniconda/Anaconda 的 Windows 10/11
- 20GB 以上的可用磁盘空间
- NVIDIA GPU（可选，但强烈建议）
- Git

## 第一步：设置项目路径（可选，推荐）

编辑 `configs/paths.yaml` 设置你的项目根目录（或者让它自动检测）：

```yaml
# 自动检测（推荐）
project_root: null

# 或者手动指定 Windows 路径：
# project_root: C:\Users\YourUsername\Documents\GitHub\yolo-vision-pipeline-rknn
```

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

# 激活环境
conda activate rknn-yolov8
```

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

在 `configs/data.yaml` 中更新你的类别信息：

```yaml
path: datasets/yolo_dataset
train: datasets/yolo_dataset/train/images
val: datasets/yolo_dataset/valid/images
nc: 6
names:
  0: yellow_ball
  1: blue_ball
  2: red_ball
  3: black_ball
  4: blue_placement_zone
  5: red_placement_zone
```

## 第三步：训练模型（1到数小时不等，取决于数据量）

```powershell
python src/train.py
```

模型将被保存至 `models/best.pt`

## 第四步：导出为 ONNX 格式（5-10分钟）

```powershell
$env:PYTHONPATH = ".\"
python src/export/1_pt_to_onnx.py
```

输出文件：`models/best.onnx`

## 第五步：转换为 RKNN 格式（在 Ubuntu/WSL 环境下，10-20分钟）

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

# 准备校准数据集（如果是首次运行）
python src/dataset_tools.py prepare_calibration \
    --image-dir /mnt/c/path/to/training/images \
    --output datasets/calibration/dataset.txt

# 转换模型
python src/export/2_onnx_to_rknn.py
```

输出文件：`models/best.rknn`

---

## 下一步做什么？

- **部署**：将 `models/best.rknn` 复制到你的 RK3588 设备上
- **优化**：在 `configs/train_config.yaml` 中调整模型大小或批次大小（batch size）
- **改进**：添加更多训练数据或尝试不同的模型变体

## 常见问题与故障排除

| 问题 | 解决方案 |
|---------|----------|
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
