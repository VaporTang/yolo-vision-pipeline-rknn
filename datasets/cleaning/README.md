**数据清洗 — 重复图像检测**

- **目的**: 在将数据喂给 YOLO 训练前，检测并分离高度重复或近似重复的图像，以减少冗余样本。
- **目录**: 本工具默认扫描 `datasets/raw`，将检测出的重复项保存到 `datasets/cleaning/duplicates`（可通过参数修改）。

目录结构说明:

```
datasets/raw/
├── images/
│   ├── batch1/1.jpg
│   └── batch2/...
└── labels/
 ├── batch1/1.txt
 └── batch2/...
```

脚本会先尝试在图片同目录下查找 `.txt` 标签，若找不到则会把 `images/` 下的相对路径映射到 `labels/` 下查找对应标签（例如 `images/batch1/1.jpg` -> `labels/batch1/1.txt`）。

使用示例:

```bash
# 预览（不移动/复制）
python datasets/scripts/deduplicate.py --src datasets/raw --images-subdir images --labels-subdir labels --dst datasets/cleaning/duplicates --threshold 5 --workers 0 --dry-run

# 确认后移动重复项
python datasets/scripts/deduplicate.py --src datasets/raw --images-subdir images --labels-subdir labels --dst datasets/cleaning/duplicates --threshold 5 --workers 4 --move
```

速度提示:

- `--workers N` 可并行计算哈希（`0` 表示单进程，推荐 4~12 之间按机器调整）。
- `--workers -1` 表示使用 `CPU 核心数 - 1`（给系统预留资源）。
