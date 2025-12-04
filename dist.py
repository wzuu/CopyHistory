#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
发布脚本，用于创建发布包
"""

import os
import sys
import shutil
import zipfile
from datetime import datetime

# 导入版本信息
try:
    from version import __version__
except ImportError:
    __version__ = "1.1.0"


def create_dist_package():
    """创建发布包"""
    print(f"创建版本 {__version__} 的发布包...")
    
    # 检查构建目录是否存在
    build_dir = "build/dist"
    if not os.path.exists(build_dir):
        print("错误: 构建目录不存在，请先运行构建命令")
        print("构建命令: python build_exe.py build")
        return False
    
    # 创建发布目录
    dist_dir = f"dist/剪贴板管理器_v{__version__}"
    os.makedirs(dist_dir, exist_ok=True)
    
    # 复制必要的文件到发布目录
    files_to_copy = [
        "剪贴板管理器.exe",
        "mini.ico",
        "icon.ico",
        "clipboard_history.db"
    ]
    
    for file in files_to_copy:
        src = os.path.join(build_dir, file)
        dst = os.path.join(dist_dir, file)
        if os.path.exists(src):
            shutil.copy2(src, dst)
            print(f"已复制: {file}")
        else:
            print(f"警告: 文件不存在 {file}")
    
    # 复制lib目录
    lib_src = os.path.join(build_dir, "lib")
    lib_dst = os.path.join(dist_dir, "lib")
    if os.path.exists(lib_src):
        shutil.copytree(lib_src, lib_dst, dirs_exist_ok=True)
        print("已复制: lib目录")
    
    # 复制share目录（如果存在）
    share_src = os.path.join(build_dir, "share")
    share_dst = os.path.join(dist_dir, "share")
    if os.path.exists(share_src):
        shutil.copytree(share_src, share_dst, dirs_exist_ok=True)
        print("已复制: share目录")
    
    # 复制clipboard_files目录（如果存在）
    clipboard_files_src = os.path.join(build_dir, "clipboard_files")
    clipboard_files_dst = os.path.join(dist_dir, "clipboard_files")
    if os.path.exists(clipboard_files_src):
        shutil.copytree(clipboard_files_src, clipboard_files_dst, dirs_exist_ok=True)
        print("已复制: clipboard_files目录")
    
    # 复制发布说明
    release_notes = f"RELEASE_NOTES_v{__version__}.md"
    if os.path.exists(release_notes):
        shutil.copy2(release_notes, dist_dir)
        print(f"已复制: {release_notes}")
    
    # 创建zip压缩包
    zip_filename = f"剪贴板管理器_v{__version__}.zip"
    print(f"创建压缩包: {zip_filename}")
    
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(dist_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arc_path = os.path.relpath(file_path, dist_dir)
                zipf.write(file_path, arc_path)
    
    print(f"发布包创建完成: {zip_filename}")
    return True


def main():
    """主函数"""
    print("剪贴板管理器发布工具")
    print("=" * 30)
    
    if create_dist_package():
        print(f"\n版本 {__version__} 发布包创建成功!")
        print("您可以将生成的zip文件分发给用户。")
    else:
        print(f"\n版本 {__version__} 发布包创建失败!")
        sys.exit(1)


if __name__ == "__main__":
    main()