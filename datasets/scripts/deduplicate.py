#!/usr/bin/env python3
"""
datasets/scripts/deduplicate.py

查找并分离高度相似/重复的图像（同时移动或复制对应的标签文件）。

用法示例:
  python datasets/scripts/deduplicate.py --src datasets/raw --dst datasets/cleaning/duplicates --move --threshold 5
    python datasets/scripts/deduplicate.py --src datasets/raw --dst datasets/cleaning/duplicates --gui

默认行为是扫描 `datasets/raw`，识别平均哈希（aHash）汉明距离小于等于阈值的图像为重复项。
GUI 模式会将相似图分组，并支持人工审核与按组导出。
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

    def search_all(self, hash_value, threshold):
        if self.root is None:
            return []

        matches = []
        stack = [self.root]
        while stack:
            node = stack.pop()
            d = hamming_distance(hash_value, node.hash)
            if d <= threshold:
                matches.append((node.path, d))
            low = d - threshold
            high = d + threshold
            for dist, child in node.children.items():
                if low <= dist <= high:
                    stack.append(child)
        return matches


class UnionFind:
    def __init__(self):
        self.parent = {}
        self.rank = {}

    def add(self, item):
        if item in self.parent:
            return
        self.parent[item] = item
        self.rank[item] = 0

    def find(self, item):
        parent = self.parent.get(item)
        if parent is None:
            return None
        if parent != item:
            self.parent[item] = self.find(parent)
        return self.parent[item]

    def union(self, a, b):
        root_a = self.find(a)
        root_b = self.find(b)
        if root_a is None or root_b is None or root_a == root_b:
            return
        rank_a = self.rank[root_a]
        rank_b = self.rank[root_b]
        if rank_a < rank_b:
            self.parent[root_a] = root_b
        elif rank_a > rank_b:
            self.parent[root_b] = root_a
        else:
            self.parent[root_b] = root_a
            self.rank[root_a] += 1


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


def build_similar_groups(image_paths, hash_size, threshold, workers):
    tree = BKTree()
    uf = UnionFind()
    hashes = {}

    for img_path, h in iter_hashes(image_paths, hash_size=hash_size, workers=workers):
        if h is None:
            print(f"无法读取图像，跳过: {img_path}")
            continue

        uf.add(img_path)
        matches = tree.search_all(h, threshold)
        for match_path, _ in matches:
            uf.add(match_path)
            uf.union(img_path, match_path)

        tree.add(h, img_path)
        hashes[img_path] = h

    groups = {}
    for path in hashes.keys():
        root = uf.find(path)
        if root is None:
            continue
        groups.setdefault(root, []).append(path)

    grouped = [sorted(paths) for paths in groups.values() if len(paths) > 1]
    grouped.sort(key=lambda g: (-len(g), g[0]))
    return grouped, hashes


def export_grouped_results(
    groups,
    selections,
    dst,
    move,
    include_kept,
    images_root,
    labels_root,
    dry_run,
):
    for index, group in enumerate(groups, 1):
        kept = selections.get(index - 1, group[0])
        group_dir = os.path.join(dst, f"group_{index:04d}")
        image_base = os.path.join(group_dir, "images")
        label_base = os.path.join(group_dir, "labels")

        for path in group:
            if path == kept and not include_kept:
                continue

            if images_root:
                rel_image = os.path.relpath(path, images_root)
            else:
                rel_image = os.path.basename(path)

            target_image = os.path.join(image_base, rel_image)
            ensure_dir(os.path.dirname(target_image))

            if not dry_run:
                if move:
                    shutil.move(path, target_image)
                else:
                    shutil.copy2(path, target_image)

            label = corresponding_label(
                path, images_root=images_root, labels_root=labels_root
            )
            if label:
                if labels_root:
                    rel_label = os.path.relpath(label, labels_root)
                elif images_root:
                    rel_label = os.path.relpath(label, images_root)
                else:
                    rel_label = os.path.basename(label)

                target_label = os.path.join(label_base, rel_label)
                ensure_dir(os.path.dirname(target_label))
                if not dry_run:
                    if move:
                        shutil.move(label, target_label)
                    else:
                        shutil.copy2(label, target_label)


def launch_gui(groups, hashes, args, images_root, labels_root, src):
    try:
        from PySide6.QtCore import Qt, QUrl
        from PySide6.QtGui import QDesktopServices, QPixmap
        from PySide6.QtWidgets import (
            QApplication,
            QCheckBox,
            QComboBox,
            QHBoxLayout,
            QLabel,
            QListWidget,
            QListWidgetItem,
            QMainWindow,
            QMessageBox,
            QPushButton,
            QSizePolicy,
            QVBoxLayout,
            QWidget,
        )
    except Exception:
        print("未检测到 PySide6，请先安装: pip install PySide6", file=sys.stderr)
        sys.exit(2)

    class DedupReviewWindow(QMainWindow):
        def __init__(self):
            super().__init__()
            self.groups = groups
            self.hashes = hashes
            self.selections = {i: group[0] for i, group in enumerate(groups)}
            self.current_group_index = 0

            self.setWindowTitle("Duplicate Review")
            self.resize(1200, 720)

            root = QWidget()
            main_layout = QHBoxLayout(root)

            self.group_list = QListWidget()
            for i, group in enumerate(groups, 1):
                self.group_list.addItem(f"Group {i} ({len(group)} images)")
            self.group_list.currentRowChanged.connect(self.on_group_changed)
            main_layout.addWidget(self.group_list, 1)

            right = QVBoxLayout()
            main_layout.addLayout(right, 3)

            self.group_info = QLabel("Select a group")
            right.addWidget(self.group_info)

            self.keep_combo = QComboBox()
            self.keep_combo.currentIndexChanged.connect(self.on_keep_changed)
            right.addWidget(self.keep_combo)

            self.image_list = QListWidget()
            self.image_list.currentRowChanged.connect(self.on_image_selected)
            right.addWidget(self.image_list, 2)

            self.preview = QLabel("No image")
            self.preview.setAlignment(Qt.AlignCenter)
            self.preview.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            self.preview.setMinimumHeight(320)
            right.addWidget(self.preview, 3)

            self.include_kept = QCheckBox("Include kept image in export")
            self.include_kept.setChecked(True)
            right.addWidget(self.include_kept)

            button_row = QHBoxLayout()
            self.open_button = QPushButton("Open selected file")
            self.open_button.clicked.connect(self.on_open_selected)
            button_row.addWidget(self.open_button)

            self.export_copy = QPushButton("Export (Copy)")
            self.export_copy.clicked.connect(lambda: self.on_export(move=False))
            button_row.addWidget(self.export_copy)

            self.export_move = QPushButton("Export (Move)")
            self.export_move.clicked.connect(lambda: self.on_export(move=True))
            button_row.addWidget(self.export_move)
            right.addLayout(button_row)

            self.setCentralWidget(root)
            if groups:
                self.group_list.setCurrentRow(0)

        def resizeEvent(self, event):
            super().resizeEvent(event)
            self.update_preview()

        def current_group(self):
            if not self.groups:
                return []
            index = self.group_list.currentRow()
            if index < 0:
                index = 0
            self.current_group_index = index
            return self.groups[index]

        def on_group_changed(self, index):
            group = self.current_group()
            if not group:
                return

            self.group_info.setText(
                f"Group {index + 1} / {len(self.groups)} | {len(group)} images"
            )
            self.keep_combo.blockSignals(True)
            self.keep_combo.clear()
            for path in group:
                self.keep_combo.addItem(os.path.basename(path), userData=path)
            kept = self.selections.get(index, group[0])
            kept_index = max(0, group.index(kept))
            self.keep_combo.setCurrentIndex(kept_index)
            self.keep_combo.blockSignals(False)
            self.refresh_image_list()

        def on_keep_changed(self, index):
            group = self.current_group()
            if not group:
                return
            kept = self.keep_combo.currentData()
            if kept:
                self.selections[self.current_group_index] = kept
            self.refresh_image_list()

        def refresh_image_list(self):
            group = self.current_group()
            if not group:
                return
            kept = self.selections.get(self.current_group_index, group[0])
            self.image_list.blockSignals(True)
            self.image_list.clear()
            for path in group:
                dist = hamming_distance(self.hashes[path], self.hashes[kept])
                label = f"{os.path.basename(path)} | dist {dist}"
                item = QListWidgetItem(label)
                item.setData(Qt.UserRole, path)
                if path == kept:
                    item.setText(label + " | kept")
                self.image_list.addItem(item)
            self.image_list.setCurrentRow(0)
            self.image_list.blockSignals(False)
            self.update_preview()

        def on_image_selected(self, _):
            self.update_preview()

        def current_selected_path(self):
            item = self.image_list.currentItem()
            if not item:
                return None
            return item.data(Qt.UserRole)

        def update_preview(self):
            path = self.current_selected_path()
            if not path or not os.path.exists(path):
                self.preview.setText("No image")
                self.preview.setPixmap(QPixmap())
                return
            pix = QPixmap(path)
            if pix.isNull():
                self.preview.setText("Preview unavailable")
                self.preview.setPixmap(QPixmap())
                return
            scaled = pix.scaled(
                self.preview.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            self.preview.setPixmap(scaled)

        def on_open_selected(self):
            path = self.current_selected_path()
            if not path:
                return
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))

        def on_export(self, move):
            if not self.groups:
                return
            mode = "move" if move else "copy"
            reply = QMessageBox.question(
                self,
                "Confirm export",
                f"Export {len(self.groups)} groups to {args.dst} (mode: {mode}). Proceed?",
            )
            if reply != QMessageBox.Yes:
                return
            export_grouped_results(
                self.groups,
                self.selections,
                dst=args.dst,
                move=move,
                include_kept=self.include_kept.isChecked(),
                images_root=images_root,
                labels_root=labels_root,
                dry_run=args.dry_run,
            )
            QMessageBox.information(self, "Done", "Export complete.")

    app = QApplication(sys.argv)
    window = DedupReviewWindow()
    window.show()
    app.exec()


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
    p.add_argument(
        "--gui",
        action="store_true",
        help="启动可视化审核界面（PySide6）",
    )
    args = p.parse_args()

    src = os.path.abspath(args.src)
    images_root = os.path.abspath(os.path.join(src, args.images_subdir))
    labels_root = os.path.abspath(os.path.join(src, args.labels_subdir))
    dst = os.path.abspath(args.dst)
    args.dst = dst

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

    if args.gui:
        groups, hashes = build_similar_groups(
            image_paths,
            hash_size=args.hash_size,
            threshold=args.threshold,
            workers=workers,
        )
        if not groups:
            print("未发现重复图片。")
            return
        launch_gui(groups, hashes, args, images_root, labels_root, src)
        return

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
