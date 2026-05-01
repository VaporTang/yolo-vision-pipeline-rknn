**视频存储与抽帧**

此目录用于存放原始视频文件，包括各批次的录制数据。

## 目录结构

```
datasets/videos/
├── batch1/
│   ├── recording_1.mp4
│   ├── recording_2.mp4
│   └── ...
├── batch2/
│   └── ...
└── README.md (本文件)
```

## 抽帧工具

使用 `datasets/scripts/extract_frames.py` 从视频中抽取帧图像。

### 安装依赖

```bash
pip install opencv-python
```

### 单个视频抽帧

```bash
python datasets/scripts/extract_frames.py \
    --video datasets/videos/batch1/recording_1.mp4 \
    --output datasets/raw/images/batch1 \
    --every 30
```

- `--video`: 视频文件路径
- `--output`: 抽取帧的输出目录
- `--every`: 每隔多少帧抽取一次（默认 1 表示全抽，30 表示每秒 1 帧左右，取决于视频 fps）

### 批量抽帧

```bash
python datasets/scripts/extract_frames.py \
    --video-dir datasets/videos \
    --output datasets/raw/images \
    --batch-prefix batch1 \
    --every 15 \
    --pattern "*.mp4"
```

- `--video-dir`: 存放视频的目录
- `--batch-prefix`: 输出文件名前缀（可选）
- `--pattern`: 查找视频文件的模式（默认 `*.mp4`，支持 `*.avi`, `*.mov` 等）
- `--every`: 抽取频率

### 输出格式

抽取的帧会以 `{video_name}_{frame_id:06d}.jpg` 的格式保存，例如：

- `recording_1_000000.jpg`
- `recording_1_000030.jpg`
- `recording_1_000060.jpg`
- ...

## 工作流

1. **采集视频**: 将录制的视频文件放到 `datasets/videos/batch{N}/`。
2. **抽帧**: 运行 `extract_frames.py` 抽取帧图像到 `datasets/raw/images/batch{N}/`。
3. **清洗**: 使用 `datasets/cleaning/deduplicate.py` 去除重复图像。
4. **标注**: 对抽取的帧进行标注（YOLO 格式）。
5. **组织**: 将清洗后的数据移到 `datasets/yolo_dataset/train` 和 `datasets/yolo_dataset/valid`。

## 建议

- **帧率选择**: 如果视频是 30 fps，`--every 30` 会给出每秒 1 帧；`--every 15` 给出每秒 2 帧。可根据数据量需求调整。
- **存储空间**: 抽帧会生成大量 .jpg 文件，建议预留足够的磁盘空间。
- **视频格式**: 支持 OpenCV 能打开的格式（mp4, avi, mov, mkv 等）。
