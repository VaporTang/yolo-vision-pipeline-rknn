#!/usr/bin/env python3
"""
datasets/cleaning/deduplicate.py

查找并分离高度相似/重复的图像（同时移动或复制对应的标签文件）。

用法示例:
  python deduplicate.py --src ../raw --dst ../cleaning/duplicates --move --threshold 5

默认行为是扫描 `datasets/raw`，识别平均哈希（aHash）汉明距离小于等于阈值的图像为重复项。
"""

import argparse
import os
import shutil
from PIL import Image
import sys


def image_ahash(path, hash_size=8):
    try:
        with Image.open(path) as img:
            img = img.convert("L").resize(
                (hash_size, hash_size), Image.Resampling.LANCZOS
            )
            pixels = list(img.getdata())
            avg = sum(pixels) / len(pixels)
            bits = "".join("1" if p > avg else "0" for p in pixels)
            return bits
    except Exception:
        return None


def hamming_distance(a, b):
    return sum(ch1 != ch2 for ch1, ch2 in zip(a, b))


def find_images(src, exts=(".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff")):
    for root, _, files in os.walk(src):
        for f in files:
            if os.path.splitext(f)[1].lower() in exts:
                yield os.path.join(root, f)


def corresponding_label(path):
    base, _ = os.path.splitext(path)
    txt = base + ".txt"
    if os.path.exists(txt):
        return txt
    return None


def ensure_dir(path):
    os.makedirs(path, exist_ok=True)


def main():
    p = argparse.ArgumentParser(prog="deduplicate")
    p.add_argument(
        "--src",
        default=os.path.join(os.path.dirname(__file__), "..", "raw"),
        help="源图片目录，默认 datasets/raw",
    )
    p.add_argument(
        "--dst",
        default=os.path.join(os.path.dirname(__file__), "duplicates"),
        help="重复文件保存目录",
    )
    p.add_argument(
        "--threshold",
        type=int,
        default=5,
        help="汉明距离阈值，越小要求越严格（默认 5）",
    )
    p.add_argument("--move", action="store_true", help="移动重复文件（默认复制）")
    p.add_argument(
        "--dry-run", action="store_true", help="只显示将要操作的文件，不执行移动/复制"
    )
    p.add_argument(
        "--hash-size",
        type=int,
        default=8,
        help="哈希尺寸（hash_size x hash_size），默认 8",
    )
    args = p.parse_args()

    src = os.path.abspath(args.src)
    dst = os.path.abspath(args.dst)

    if not os.path.isdir(src):
        print(f"源目录不存在: {src}", file=sys.stderr)
        sys.exit(2)

    ensure_dir(dst)

    hashes = []  # list of tuples (hash_bits, path)
    duplicates = []

    print("Scanning images...")
    for img_path in find_images(src):
        h = image_ahash(img_path, hash_size=args.hash_size)
        if h is None:
            print(f"无法读取图像，跳过: {img_path}")
            continue

        found = False
        for existing_h, existing_path in hashes:
            d = hamming_distance(h, existing_h)
            if d <= args.threshold:
                duplicates.append((img_path, existing_path, d))
                found = True
                break

        if not found:
            hashes.append((h, img_path))

    if not duplicates:
        print("未发现重复图片。")
        return

    print(f"发现 {len(duplicates)} 个重复项，目标目录: {dst}")

    for dup_path, kept_path, dist in duplicates:
        rel_kept = os.path.relpath(kept_path, src)
        rel_dup = os.path.relpath(dup_path, src)
        print(f"DUP ({dist}): {rel_dup}  <-- similar to -- {rel_kept}")

        # 复制/移动图片
        target_img_dir = os.path.join(dst, os.path.dirname(rel_dup))
        ensure_dir(target_img_dir)
        target_img = os.path.join(target_img_dir, os.path.basename(dup_path))

        if args.dry_run:
            continue

        if args.move:
            shutil.move(dup_path, target_img)
        else:
            shutil.copy2(dup_path, target_img)

        # 处理标签文件（若存在同名 .txt）
        label = corresponding_label(dup_path)
        if label:
            target_label_dir = target_img_dir
            ensure_dir(target_label_dir)
            target_label = os.path.join(target_label_dir, os.path.basename(label))
            if args.move:
                shutil.move(label, target_label)
            else:
                shutil.copy2(label, target_label)

    print("处理完成。")


if __name__ == "__main__":
    main()
