#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
剪贴板管理器打包配置
"""

import sys
import os
from cx_Freeze import setup, Executable

# 导入版本信息
try:
    from version import __version__
except ImportError:
    __version__ = "1.1.0"  # 默认版本号
# 获取当前目录
current_dir = os.path.dirname(os.path.abspath(__file__))

# 包含的文件
include_files = [
    ("2.ico", "2.ico"),
    ("icon.ico", "icon.ico"),
    ("clipboard_history.db", "clipboard_history.db"),
]

# 包含的包
packages = [
    "tkinter",
    "sqlite3",
    "hashlib",
    "win32clipboard",
    "win32con",
    "PIL",
    "pystray"
]

# 包含的模块
includes = [
    "clipboard_db",
    "clipboard_gui",
    "clipboard_content_detector"
]

# 排除的模块
excludes = []

# 构建选项
build_exe_options = {
    "packages": packages,
    "includes": includes,
    "excludes": excludes,
    "include_files": include_files,
}

# 基础设置
base = None
if sys.platform == "win32":
    base = "Win32GUI"  # GUI应用程序

# 可执行文件配置
executables = [
    Executable(
        script="run_clipboard_manager.py",
        target_name="剪贴板管理器.exe",
        icon="2.ico",
        base=base
    ),
    Executable(
        script="view_clipboard_history.py",
        target_name="查看剪贴板历史.exe",
        icon="2.ico",
        base=None  # 控制台应用程序
    ),
    Executable(
        script="clipboard_content_detector.py",
        target_name="剪贴板内容检测器.exe",
        icon="2.ico",
        base=None  # 控制台应用程序
    )
]

# 设置信息
setup(
    name="剪贴板管理器",
    version=__version__,
    description="剪贴板历史记录管理工具",
    options={"build_exe": build_exe_options},
    executables=executables,
)