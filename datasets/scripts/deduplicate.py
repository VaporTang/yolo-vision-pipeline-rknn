#!/usr/bin/env python3
"""
datasets/scripts/deduplicate.py

查找并分离高度相似/重复的图像（同时移动或复制对应的标签文件）。

用法示例:
  python datasets/scripts/deduplicate.py --src datasets/raw --dst datasets/cleaning/duplicates --move --threshold 5

默认行为是扫描 `datasets/raw`，识别平均哈希（aHash）汉明距离小于等于阈值的图像为重复项。
"""

import argparse
import concurrent.futures as cf
from itertools import repeat
import os
import shutil
import sys
from PIL import Image


def image_ahash(path, hash_size=8):
    try:
        with Image.open(path) as img:
            img = img.convert("L").resize(
                (hash_size, hash_size), Image.Resampling.LANCZOS
            )
            pixels = list(img.getdata())
            avg = sum(pixels) / len(pixels)
            bits = 0
            for p in pixels:
                bits = (bits << 1) | (1 if p > avg else 0)
            return bits
    except Exception:
        return None


def hamming_distance(a, b):
    return (a ^ b).bit_count() if hasattr(int, "bit_count") else bin(a ^ b).count("1")


def find_images(src, exts=(".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff")):
    stack = [src]
    while stack:
        root = stack.pop()
        try:
            with os.scandir(root) as it:
                for entry in it:
                    if entry.is_dir(follow_symlinks=False):
                        stack.append(entry.path)
                        continue
                    if entry.is_file(follow_symlinks=False):
                        if os.path.splitext(entry.name)[1].lower() in exts:
                            yield entry.path
        except PermissionError:
            continue


class BKNode:
    __slots__ = ("hash", "path", "children")

    def __init__(self, hash_value, path):
        self.hash = hash_value
        self.path = path
        self.children = {}


class BKTree:
    def __init__(self):
        self.root = None

    def add(self, hash_value, path):
        if self.root is None:
            self.root = BKNode(hash_value, path)
            return

        node = self.root
        while True:
            d = hamming_distance(hash_value, node.hash)
            child = node.children.get(d)
            if child is None:
                node.children[d] = BKNode(hash_value, path)
                return
            node = child

    def search_first(self, hash_value, threshold):
        if self.root is None:
            return None

        stack = [self.root]
        while stack:
            node = stack.pop()
            d = hamming_distance(hash_value, node.hash)
            if d <= threshold:
                return node.path, d
            low = d - threshold
            high = d + threshold
            for dist, child in node.children.items():
                if low <= dist <= high:
                    stack.append(child)
        return None


def iter_hashes(paths, hash_size, workers, report_every=500):
    total = len(paths)
    if workers == 0:
        for i, path in enumerate(paths, 1):
            if report_every and i % report_every == 0:
                print(f"Hashed {i}/{total}...")
            yield path, image_ahash(path, hash_size=hash_size)
        return

    with cf.ProcessPoolExecutor(max_workers=workers) as ex:
        chunksize = max(1, total // (workers * 4)) if total else 1
        for i, (path, h) in enumerate(
            zip(
                paths,
                ex.map(image_ahash, paths, repeat(hash_size), chunksize=chunksize),
            ),
            1,
        ):
            if report_every and i % report_every == 0:
                print(f"Hashed {i}/{total}...")
            yield path, h


def corresponding_label(image_path, images_root=None, labels_root=None):
    # 1) 尝试与图片同目录下的同名 .txt
    base, _ = os.path.splitext(image_path)
    txt_same = base + ".txt"
    if os.path.exists(txt_same):
        return txt_same

    # 2) 如果提供 labels_root，则根据 images_root 的相对路径映射到 labels_root
    if images_root and labels_root:
        try:
            rel = os.path.relpath(image_path, images_root)
        except Exception:
            rel = os.path.basename(image_path)

        label_path = os.path.join(labels_root, os.path.splitext(rel)[0] + ".txt")
        if os.path.exists(label_path):
            return label_path

    return None


def ensure_dir(path):
    os.makedirs(path, exist_ok=True)


def main():
    p = argparse.ArgumentParser(prog="deduplicate")
    p.add_argument(
        "--src",
        default=os.path.join(os.path.dirname(__file__), "..", "raw"),
        help="源根目录，默认 datasets/raw。下面应包含 images/ 和 labels/（可自定义）",
    )
    p.add_argument(
        "--images-subdir",
        default="images",
        help="在 src 下的图片子目录名称（默认 images）",
    )
    p.add_argument(
        "--labels-subdir",
        default="labels",
        help="在 src 下的标签子目录名称（默认 labels）",
    )
    p.add_argument(
        "--dst",
        default=os.path.join(os.path.dirname(__file__), "..", "cleaning", "duplicates"),
        help="重复文件保存目录，默认 datasets/cleaning/duplicates",
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
    p.add_argument(
        "--workers",
        type=int,
        default=0,
        help="哈希并行进程数，0 表示单进程（默认 0）",
    )
    args = p.parse_args()

    src = os.path.abspath(args.src)
    images_root = os.path.abspath(os.path.join(src, args.images_subdir))
    labels_root = os.path.abspath(os.path.join(src, args.labels_subdir))
    dst = os.path.abspath(args.dst)

    if not os.path.isdir(images_root):
        print(f"图片目录不存在: {images_root}", file=sys.stderr)
        sys.exit(2)

    if not os.path.isdir(labels_root):
        # labels_root 可以不存在（标签可能和图片同目录）
        labels_root = None

    ensure_dir(dst)

    duplicates = []

    print("Scanning images...")
    image_paths = list(find_images(images_root))
    if not image_paths:
        print("未发现图片文件。")
        return

    workers = args.workers
    if workers < 0:
        workers = max(1, (os.cpu_count() or 1) + workers)
    print(f"Total images: {len(image_paths)} | workers: {workers}")

    tree = BKTree()
    for img_path, h in iter_hashes(
        image_paths, hash_size=args.hash_size, workers=workers
    ):
        if h is None:
            print(f"无法读取图像，跳过: {img_path}")
            continue

        match = tree.search_first(h, args.threshold)
        if match:
            kept_path, dist = match
            duplicates.append((img_path, kept_path, dist))
        else:
            tree.add(h, img_path)

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

        # 处理标签文件：先尝试同目录，再尝试 labels_root 映射
        label = corresponding_label(
            dup_path, images_root=images_root, labels_root=labels_root
        )
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
