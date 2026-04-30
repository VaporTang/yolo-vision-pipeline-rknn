# 路径配置快速设置指南

## 🚀 3 步快速开始

### 第 1 步：验证项目根目录

打开 `configs/paths.yaml` 检查：

```yaml
project_root: null  # ← 保持为 null 让它自动检测
```

或手动指定（Windows 示例）：

```yaml
project_root: C:\Users\YourUsername\Documents\GitHub\yolo-vision-pipeline-rknn
```

### 第 2 步：验证路径配置

```powershell
python verify_paths.py
```

你会看到：

```
📂 Project Root: C:\...\yolo-vision-pipeline-rknn
   Exists: ✅

📋 Checking Critical Directories:
  ✅ configs          → C:\...\configs
  ⚠️  datasets        → C:\...\datasets/yolo_dataset
  ✅ src              → C:\...\src
  ✅ models           → C:\...\models
  ✅ docs             → C:\...\docs
```

### 第 3 步：开始训练

所有脚本都自动读取 `configs/paths.yaml` 中的路径：

```powershell
# 所有脚本都可用
python src/train.py                       # 训练
$env:PYTHONPATH = ".\"
python src/export/1_pt_to_onnx.py        # 导出
python src/dataset_tools.py prepare_calibration  # 数据集处理
```

## 📁 核心配置文件

### `configs/paths.yaml`

所有路径都定义在这里。示例结构：

```yaml
project_root: null  # auto-detect

dataset:
  root: datasets/yolo_dataset
  train_images: datasets/yolo_dataset/train/images
  train_labels: datasets/yolo_dataset/train/labels
  val_images: datasets/yolo_dataset/valid/images
  val_labels: datasets/yolo_dataset/valid/labels
  calibration_images: datasets/calibration/images
  calibration_list: datasets/calibration/dataset.txt

models:
  root: models
  best_pt: models/best.pt
  best_onnx: models/best.onnx
  best_rknn: models/best.rknn
  training_results: models/training_results

configs:
  root: configs
  data: configs/data.yaml
  train: configs/train_config.yaml
  export: configs/export_config.yaml
  rknn: configs/rknn_config.yaml
```

## 🔧 Python 脚本中使用

如果你写自己的脚本，可以这样使用 PathManager：

```python
from src.utils.path_manager import paths

# 获取单个路径
best_pt = paths.get("models.best_pt")
print(best_pt)  # <PosixPath '/home/user/yolo-pipeline/models/best.pt'>

# 获取字符串格式
best_onnx = paths.get_str("models.best_onnx")

# 确保目录存在
paths.ensure_dir("dataset.calibration_images")

# 获取所有路径
all_models = paths.get_all("models")
```

## ❓ 常见问题

**Q: 自动检测没有工作？**  
A: 检查 project_root 设置，或手动指定绝对路径

**Q: 在 WSL 中运行需要什么？**  
A: 使用 `/mnt/c/...` 来访问 Windows 路径，或在 WSL 中设置项目

**Q: 我的数据集不在 `datasets/` 目录？**  
A: 在 `configs/paths.yaml` 中编辑路径即可

## 📖 详细文档

- [路径配置完整指南](docs/path_configuration.md)
- [工作流指南](docs/workflow.md)
- [快速参考](docs/quick_reference.md)

## 验证脚本

使用 `verify_paths.py` 检查所有关键路径：

```powershell
# 基本验证
python verify_paths.py

# 显示完整配置
python verify_paths.py --show-config

# 显示配置帮助
python verify_paths.py --help-config
```

---

**就这么简单！所有路径都集中在一个地方。** 🎉
