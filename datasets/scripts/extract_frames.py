#!/usr/bin/env python3
"""
datasets/scripts/extract_frames.py

从视频文件中抽取帧图像，支持批量处理、频率控制、时间戳命名。

用法示例:
  python extract_frames.py --video path/to/video.mp4 --output ../raw/images/batch1 --every 30
  python extract_frames.py --video-dir ../videos --output ../raw/images --batch-prefix batch1 --every 15

支持格式: mp4, avi, mov, mkv, flv 等 OpenCV 支持的视频格式
"""

import argparse
import os
import sys
import cv2
from pathlib import Path


def extract_frames_from_video(
    video_path, output_dir, every_n_frames=1, video_name_prefix=None
):
    """
    从单个视频中抽取帧

    Args:
        video_path: 视频文件路径
        output_dir: 输出目录
        every_n_frames: 每隔多少帧抽取一次（默认1表示全抽）
        video_name_prefix: 输出文件名前缀，若为空则使用视频文件名

    Returns:
        int: 成功抽取的帧数
    """
    video_path = os.path.abspath(video_path)
    output_dir = os.path.abspath(output_dir)

    if not os.path.isfile(video_path):
        print(f"视频文件不存在: {video_path}", file=sys.stderr)
        return 0

    # 打开视频
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"无法打开视频文件: {video_path}", file=sys.stderr)
        return 0

    # 获取视频信息
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)

    if video_name_prefix is None:
        video_name_prefix = Path(video_path).stem

    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)

    frame_count = 0
    saved_count = 0

    print(f"视频: {os.path.basename(video_path)} ({total_frames} 帧, {fps:.2f} fps)")
    print(
        f"抽取策略: 每 {every_n_frames} 帧抽取一次 -> {total_frames // every_n_frames} 帧"
    )

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_count % every_n_frames == 0:
            # 生成输出文件名
            output_filename = f"{video_name_prefix}_{frame_count:06d}.jpg"
            output_path = os.path.join(output_dir, output_filename)

            cv2.imwrite(output_path, frame)
            saved_count += 1

        frame_count += 1

    cap.release()
    print(f"  已保存 {saved_count} 帧 -> {output_dir}\n")
    return saved_count


def extract_frames_from_directory(
    video_dir, output_dir, every_n_frames=1, batch_prefix=None, pattern=None
):
    """
    从目录下的所有视频文件中批量抽取帧

    Args:
        video_dir: 视频文件所在目录
        output_dir: 输出目录
        every_n_frames: 每隔多少帧抽取一次
        batch_prefix: 输出文件名前缀，若设置则为 {batch_prefix}_{video_name}_{frame_id}
        pattern: 文件模式，默认 *.mp4

    Returns:
        int: 总共保存的帧数
    """
    video_dir = os.path.abspath(video_dir)

    if not os.path.isdir(video_dir):
        print(f"视频目录不存在: {video_dir}", file=sys.stderr)
        return 0

    if pattern is None:
        pattern = "*.mp4"

    # 查找视频文件
    video_files = sorted(Path(video_dir).glob(pattern))  # 包括 **/*.mp4 递归查找

    if not video_files:
        print(f"在 {video_dir} 中未找到视频文件（模式: {pattern}）", file=sys.stderr)
        return 0

    print(f"找到 {len(video_files)} 个视频文件")
    print()

    total_saved = 0

    for video_file in video_files:
        video_path = str(video_file)
        video_name = video_file.stem

        if batch_prefix:
            # 使用 batch_prefix + video_name 作为文件名前缀
            prefix = f"{batch_prefix}_{video_name}"
        else:
            prefix = video_name

        saved = extract_frames_from_video(
            video_path, output_dir, every_n_frames, prefix
        )
        total_saved += saved

    print(f"总计: 抽取了 {total_saved} 帧图像")
    return total_saved


def main():
    p = argparse.ArgumentParser(
        prog="extract_frames", description="从视频文件中抽取帧图像"
    )

    # 单视频或目录模式
    p.add_argument("--video", help="单个视频文件路径（与 --video-dir 互斥）")
    p.add_argument(
        "--video-dir",
        help="视频文件所在目录（与 --video 互斥）",
    )
    p.add_argument(
        "--output",
        required=True,
        help="输出目录（保存抽取的帧图像）",
    )
    p.add_argument(
        "--every",
        type=int,
        default=1,
        dest="every_n_frames",
        help="每隔多少帧抽取一次（默认 1 表示全抽）",
    )
    p.add_argument(
        "--batch-prefix",
        help="输出文件名前缀（仅在 --video-dir 模式下使用）",
    )
    p.add_argument(
        "--pattern",
        default="*.mp4",
        help="查找视频文件的模式（默认 *.mp4，支持 *.avi, *.mov 等）",
    )

    args = p.parse_args()

    # 检查输入参数
    if args.video and args.video_dir:
        print("错误: --video 和 --video-dir 不能同时指定", file=sys.stderr)
        sys.exit(1)

    if not args.video and not args.video_dir:
        print("错误: 必须指定 --video 或 --video-dir", file=sys.stderr)
        sys.exit(1)

    if args.every_n_frames < 1:
        print("错误: --every 必须 >= 1", file=sys.stderr)
        sys.exit(1)

    # 检查依赖
    try:
        import cv2
    except ImportError:
        print(
            "错误: 未安装 opencv-python，请运行: pip install opencv-python",
            file=sys.stderr,
        )
        sys.exit(1)

    # 执行抽帧
    if args.video:
        extract_frames_from_video(args.video, args.output, args.every_n_frames)
    else:
        extract_frames_from_directory(
            args.video_dir,
            args.output,
            args.every_n_frames,
            args.batch_prefix,
            args.pattern,
        )


if __name__ == "__main__":
    main()
