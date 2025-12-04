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
    __version__ = "1.1.0"
# 获取当前目录
current_dir = os.path.dirname(os.path.abspath(__file__))

# 包含的文件
include_files = [
    ("mini.ico", "mini.ico"),
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
    "clipboard_manager_main",
    "clipboard_content_detector"
]

# 排除的模块
excludes = []

# 构建选项 - 优化打包配置
build_exe_options = {
    "packages": packages,
    "includes": includes,
    "excludes": excludes,
    "include_files": include_files,
    "optimize": 2,  # 优化级别
    "zip_include_packages": ["encodings", "tkinter", "PIL", "pystray"],  # 将指定包打包到zip文件中
    "build_exe": "build/dist"  # 构建输出目录
}

# 基础设置
base = None
if sys.platform == "win32":
    base = "Win32GUI"  # GUI应用程序

# 可执行文件配置 - 只包含主程序
executables = [
    Executable(
        script="run_clipboard_manager.py",
        target_name="剪贴板管理器.exe",
        icon="mini.ico",
        base=base
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