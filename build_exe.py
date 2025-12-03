#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
打包脚本，用于将剪贴板管理器打包为exe可执行文件
"""

import os
import sys
from cx_Freeze import setup, Executable

# 导入版本信息
try:
    from version import __version__
except ImportError:
    __version__ = "1.1.0"  # 默认版本号

# 获取当前目录
current_dir = os.path.dirname(os.path.abspath(__file__))

# 添加需要包含的文件
include_files = [
    ("2.ico", "2.ico"),  # 图标文件
    ("icon.ico", "icon.ico"),  # 图标文件
    ("clipboard_history.db", "clipboard_history.db"),  # 数据库文件（如果存在）
]

# 添加需要的包
packages = [
    "tkinter",
    "sqlite3",
    "hashlib",
    "win32clipboard",
    "win32con",
    "PIL",
    "pystray"
]

# 添加需要的模块
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

# 创建可执行文件配置
clipboard_manager_exe = Executable(
    script="run_clipboard_manager.py",
    target_name="剪贴板管理器.exe",
    icon="2.ico",  # 使用2.ico作为图标
    base="Win32GUI" if sys.platform == "win32" else None,  # Windows下使用GUI模式
)

# 查看历史记录的控制台版本
view_history_exe = Executable(
    script="view_clipboard_history.py",
    target_name="查看剪贴板历史.exe",
    icon="2.ico",
    base=None,  # 控制台应用
)

# 剪贴板内容检测器的控制台版本
detector_exe = Executable(
    script="clipboard_content_detector.py",
    target_name="剪贴板内容检测器.exe",
    icon="2.ico",
    base=None,  # 控制台应用
)

# 设置信息
setup(
    name="剪贴板管理器",
    version=__version__,
    description="剪贴板历史记录管理工具",
    options={"build_exe": build_exe_options},
    executables=[clipboard_manager_exe, view_history_exe, detector_exe],
)