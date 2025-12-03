#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
打包脚本，用于版本管理和项目打包
"""

import os
import sys
import subprocess
import shutil
from datetime import datetime

# 导入版本信息
try:
    from version import __version__
except ImportError:
    __version__ = "1.1.0"


def update_version(new_version=None):
    """更新版本号"""
    if new_version:
        # 更新version.py文件
        version_content = f'''# -*- coding: utf-8 -*-
"""
版本信息
"""

__version__ = "{new_version}"
__author__ = "Clipboard Manager Team"
__description__ = "剪贴板历史记录管理工具"
'''
        with open("version.py", "w", encoding="utf-8") as f:
            f.write(version_content)
        print(f"版本号已更新为: {new_version}")
        return new_version
    else:
        print(f"当前版本号: {__version__}")
        return __version__


def build_project():
    """构建项目"""
    print("开始构建项目...")
    try:
        # 运行构建命令
        result = subprocess.run([sys.executable, "build_exe.py", "build"], 
                              capture_output=True, text=True, check=True)
        print("项目构建成功!")
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print("项目构建失败:")
        print(e.stderr)
        return False
    except FileNotFoundError:
        print("错误: 找不到build_exe.py文件")
        return False


def create_release_notes(version):
    """创建发布说明"""
    release_notes = f"""# 剪贴板管理器 v{version} 发布说明

## 更新时间
{datetime.now().strftime("%Y-%m-%d")}

## 版本亮点
- 统一了主面板和系统托盘图标
- 增加了版本管理机制
- 优化了打包流程

## 功能改进
- 修复了图标不一致的问题
- 增强了程序的稳定性和用户体验

## 文件列表
- 剪贴板管理器.exe - 主程序
- 查看剪贴板历史.exe - 历史记录查看工具
- 剪贴板内容检测器.exe - 内容检测工具

## 安装说明
1. 下载并解压所有文件
2. 双击运行"剪贴板管理器.exe"
3. 程序将在系统托盘运行，点击托盘图标可打开界面
"""
    
    with open(f"RELEASE_NOTES_v{version}.md", "w", encoding="utf-8") as f:
        f.write(release_notes)
    print(f"发布说明已创建: RELEASE_NOTES_v{version}.md")


def main():
    """主函数"""
    print("剪贴板管理器打包工具")
    print("=" * 30)
    
    # 获取命令行参数
    if len(sys.argv) > 1:
        if sys.argv[1] == "version":
            if len(sys.argv) > 2:
                # 更新版本号
                new_version = sys.argv[2]
                update_version(new_version)
            else:
                # 显示当前版本号
                update_version()
        elif sys.argv[1] == "build":
            # 构建项目
            build_project()
        elif sys.argv[1] == "release":
            # 创建发布版本
            version = update_version()
            if build_project():
                create_release_notes(version)
                print(f"版本 {version} 打包完成!")
        else:
            print("用法:")
            print("  python package.py version [new_version]  # 查看或更新版本号")
            print("  python package.py build                 # 构建项目")
            print("  python package.py release               # 创建发布版本")
    else:
        print("用法:")
        print("  python package.py version [new_version]  # 查看或更新版本号")
        print("  python package.py build                 # 构建项目")
        print("  python package.py release               # 创建发布版本")


if __name__ == "__main__":
    main()