# YOLO 视觉流水线 - 5分钟快速入门

以下是上手该流水线最快的方式。

## 前置条件

- 安装了 Miniconda/Anaconda 的 Windows 10/11
- 20GB 以上的可用磁盘空间
- NVIDIA GPU（可选，但强烈建议）
- Git

### 如果还没有安装 Miniconda

建议直接安装 Miniconda（比 Anaconda 更轻量，适合这个项目）：

1. 打开官方页面：[https://www.anaconda.com/download/success?reg=skipped](https://www.anaconda.com/download/success?reg=skipped)
2. 下载 Miniconda Windows x86_64 安装包
3. 运行安装程序，建议选择默认安装位置
4. **不建议**勾选 *Add installation to my PATH environment variable*
5. **建议**勾选 *Register Miniconda3 as my default Python 3.13*
6. **建议**勾选 *Clear the package cache upon completion*
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

# 或者手动指定 Windows 绝对路径：
# project_root: C:\Users\YourUsername\Documents\GitHub\yolo-vision-pipeline-rknn
```

这个路径检查命令不依赖训练环境，首次克隆后就可以直接运行，查看当前路径配置：

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

安装脚本会自动配置以下三个环境：

- `rknn-yolov8-train`：官方 Ultralytics 源码安装，用于模型训练
- `rknn-yolov8-export`：瑞芯微 (Rockchip) Ultralytics 源码安装，用于 ONNX 模型导出
- `x-anylabeling-cu12`：X-AnyLabeling 源码安装，用于基于 GPU (CUDA 12) 的数据标注

如果你需要用 X-AnyLabeling 进行数据标注，可以在安装完成后随时切换到该环境：

```powershell
conda activate x-anylabeling-cu12
xanylabeling
```

## 第二步补充：从视频抽帧（可选）

如果你有录制的视频文件，可以使用抽帧工具自动提取帧图像。将视频放入 `datasets/videos/batch{N}/` 目录，使用以下命令抽帧：

```powershell
# 批量抽帧（按目录，自动保留 batch 子目录结构）
# 默认递归查找 **/*.mp4 文件
python datasets/scripts/extract_frames.py --video-dir datasets/videos --output datasets/raw/images --every 30

# 自定义递归模式示例（例如只抽 .avi 视频，每 15 帧抽 1 帧）
python datasets/scripts/extract_frames.py --video-dir datasets/videos --output datasets/raw/images --every 15 --pattern "**/*.avi"
```

批量模式会将 `datasets/videos/batch1/*.mp4` 输出到 `datasets/raw/images/batch1/`，`batch2` 同理。详见 `datasets/videos/README.md`。

## 第三步：准备数据集（时间不定）

你的数据集应当符合标准 YOLO 格式：

```text
datasets/yolo_dataset/
├── train/
│   ├── images/  (你的 jpg 图片文件)
│   └── labels/  (YOLO 格式的 txt 标注文件)
└── valid/
    ├── images/
    └── labels/
```

### 数据清洗与去重（可选但强烈推荐）

在将图片正式归入 `datasets/yolo_dataset` 前，建议先对原始数据进行清洗，去除高度重复的图片以减少训练冗余。

```powershell
# 1. 预览重复项（Dry-run，不实际移动）
python datasets/scripts/deduplicate.py --src datasets/raw --dst datasets/cleaning/duplicates --threshold 3 --workers 0 --dry-run

# 2. 确认无误后，移动重复项进行隔离
python datasets/scripts/deduplicate.py --src datasets/raw --dst datasets/cleaning/duplicates --threshold 3 --workers -4 --move

# 3. 启动 GUI 人工审核模式（按组预览和保留相似图片）
python datasets/scripts/deduplicate.py --src datasets/raw --dst datasets/cleaning/duplicates --gui --threshold 4
```

### 从 raw 一步拆分到 yolo_dataset（推荐）

清洗完成后，可以直接把 `datasets/raw` 中已配对的图片与标签按比例拆分到标准 YOLO 目录：

```powershell
# 先预览（不实际移动）
python datasets/scripts/split_dataset.py --src datasets/raw --dst datasets/yolo_dataset --val-ratio 0.2 --seed 42 --dry-run

# 确认后执行移动
python datasets/scripts/split_dataset.py --src datasets/raw --dst datasets/yolo_dataset --val-ratio 0.2 --seed 42
```

默认会递归匹配 `datasets/raw/images` 与 `datasets/raw/labels` 的同名样本，并输出到：

- `datasets/yolo_dataset/train/images` 与 `datasets/yolo_dataset/train/labels`
- `datasets/yolo_dataset/valid/images` 与 `datasets/yolo_dataset/valid/labels`

可选参数：

- `--mode copy`：复制而不是移动
- `--overwrite`：目标文件已存在时覆盖

## 第四步：训练模型（1到数小时不等）

确保处于 `rknn-yolov8-train` 环境下：

```powershell
# 使用默认配置 (基于 configs/train_config.yaml)
python src/train.py

# 或通过命令行覆盖参数
python src/train.py --epochs 300 --batch -1
```

训练完成后，最佳模型将被保存至 `models/best.pt`。

## 第五步：导出为 ONNX 格式（5-10分钟）

**注意：必须切换到专门的导出环境！**

```powershell
conda activate rknn-yolov8-export

# 设置环境变量确保路径被正确识别
$env:PYTHONPATH = ".\"

# 执行导出
python src/export/1_pt_to_onnx.py --purpose rknn
```

输出文件：`models/best.onnx`

说明：RKNN 导出默认使用 opset 12。`onnxsim` 是否启用由 `configs/export_config.yaml` 的 `simplify` 控制；也可通过命令行显式覆盖（`--simplify` / `--no-simplify`）。

强制测试 RKNN + onnxsim：

```powershell
$env:PYTHONPATH = ".\"
python src/export/1_pt_to_onnx.py --purpose rknn --simplify
```

### 💡 进阶：导出 X-Anylabeling AI 辅助标注模型（可选）

如果你希望用刚才训练好的模型，去自动标注未来的新数据：

```powershell
# 切换回官方训练环境
conda activate rknn-yolov8-train

$env:PYTHONPATH = ".\"
# 导出并简化模型，专供 X-Anylabeling 使用
python src/export/1_pt_to_onnx.py --purpose anylabeling --input models/best.pt --output tools/anylabeling/models/detection.onnx --simplify
```

然后在 X-Anylabeling 的 `菜单 -> AI 功能 -> 模型管理` 中加载 `detection.onnx` 即可实现一键自动标注。

## 第六步：转换为 RKNN 格式（Ubuntu/WSL，10-20分钟）

RKNN 模型转换必须在 Linux (x86_64) 环境下进行。

### 首次运行环境初始化

```bash
# 在 Ubuntu/WSL 终端中执行
cd /mnt/c/Users/你的用户名/Documents/GitHub/yolo-vision-pipeline-rknn
bash setup_wsl.sh
source ~/rknn-workdir/rknn-env/bin/activate
```

### 执行转换

```bash
# 1. 确保在 WSL 的虚拟环境中
source ~/rknn-workdir/rknn-env/bin/activate

# 2. 验证 ONNX 文件存在（无需复制，文件已在 ./models 目录中）
ls -lh ./models/best.onnx

# 3. 准备量化校准数据集（从训练集抽取 20-30 张代表性图像）
python src/dataset_tools.py prepare_calibration --image-dir datasets/yolo_dataset/train/images --output datasets/calibration/dataset.txt --num-images 20

# 4. 转换模型为 RKNN 格式
python src/export/2_onnx_to_rknn.py
```

输出文件：`models/best.rknn`

## 下一步做什么？

- **部署**：将生成的 `models/best.rknn` 复制并部署到你的 RK3588/RK3568 NPU 设备上。
- **优化**：在 `configs/train_config.yaml` 中调整模型尺寸（如 yolov8n, yolov8s）或批次大小（batch size）。
- **扩充**：收集更多数据，利用刚刚导出的 AI 辅助模型在 X-AnyLabeling 中快速标注，提升模型精度。

## 常见问题与故障排除

| 问题现象 | 解决方案 |
| :--- | :--- |
| `PYTHONPATH not set` (Windows) | 执行 `$env:PYTHONPATH = ".\"` |
| CUDA Out of Memory (OOM) 内存不足 | 在训练命令中减小批次大小，例如追加参数：`--batch 8` 或 `--batch 4` |
| RKNN toolkit not found (WSL) | 确保已激活正确的环境：`source ~/rknn-workdir/rknn-env/bin/activate` |
| 转换时提示 PyYAML 缺失 (WSL) | 在 WSL 环境中执行：`pip install pyyaml` |
| OOM (转换模型到 RKNN 时) | 在 `configs/rknn_config.yaml` 中将 `optimization_level` 改为 `1` |

## 文件结构一览

```text
yolo-vision-pipeline-rknn/
├── configs/          ← 统一配置中心 (重点关注 data.yaml 和 rknn_config.yaml)
├── datasets/         ← 数据集存放与处理目录
│   ├── raw/
│   ├── yolo_dataset/
│   └── calibration/
├── models/           ← 训练产出与导出的模型 (.pt, .onnx, .rknn)
├── src/              ← 核心代码逻辑（通常无需修改）
├── tools/            ← 扩展工具 (如 anylabeling)
├── README.md         ← 完整功能说明书
├── setup_win.ps1     ← Windows 一键安装包
└── setup_wsl.sh      ← Linux/WSL 一键安装包
```

---

⏱️ **总耗时预估**：从零开始到生成最终的 `.rknn` 文件，总耗时大约为 **2-8 小时**，主要取决于您的**数据集大小**、**模型复杂度**以及**显卡性能**。
