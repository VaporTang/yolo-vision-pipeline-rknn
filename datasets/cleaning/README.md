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
python datasets/scripts/deduplicate.py --src datasets/raw --images-subdir images --labels-subdir labels --dst datasets/cleaning/duplicates --move
