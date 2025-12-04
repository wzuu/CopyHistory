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
    ("mini.ico", "mini.ico"),  # 图标文件
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

# 创建可执行文件配置 - 只包含主程序
clipboard_manager_exe = Executable(
    script="run_clipboard_manager.py",
    target_name="剪贴板管理器.exe",
    icon="mini.ico",  # 使用mini.ico作为图标
    base="Win32GUI" if sys.platform == "win32" else None  # Windows下使用GUI模式
)

# 设置信息
setup(
    name="剪贴板管理器",
    version=__version__,
    description="剪贴板历史记录管理工具",
    options={"build_exe": build_exe_options},
    executables=[clipboard_manager_exe],  # 只包含主程序
)