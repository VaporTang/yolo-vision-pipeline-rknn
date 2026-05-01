**数据清洗 — 重复图像检测**

- **目的**: 在将数据喂给 YOLO 训练前，检测并分离高度重复或近似重复的图像，以减少冗余样本。
- **目录**: 本工具默认扫描 `datasets/raw`，将检测出的重复项保存到 `datasets/cleaning/duplicates`（可通过参数修改）。

使用示例:

```bash
python datasets/cleaning/deduplicate.py --src datasets/raw --dst datasets/cleaning/duplicates --move
```

参数说明:

- `--src`: 要扫描的源图片目录，默认 `datasets/raw`。
- `--dst`: 将重复图片复制/移动到的目标目录，默认 `datasets/cleaning/duplicates`。
- `--threshold`: 汉明距离阈值（默认 5），值越小表示越严格。
- `--move`: 若设置则移动重复文件（连同同名 `.txt` 标签），否则复制。
- `--dry-run`: 只列出将被处理的文件，不实际移动或复制。

建议:

- 先用 `--dry-run` 与较小的阈值测试，确认效果后再执行 `--move`。
- 处理完成后，将 `datasets/cleaning/duplicates` 中的文件人工复核，必要时删除或归档。
