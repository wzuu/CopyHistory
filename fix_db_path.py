#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复数据库路径问题的脚本
确保数据库文件能够在正确的路径下创建
"""

import os
import sys
import sqlite3

def get_appropriate_db_path():
    """
    获取适当的数据库路径
    优先级：
    1. 程序所在目录
    2. 用户数据目录
    3. 临时目录
    """
    # 获取程序所在目录
    if getattr(sys, 'frozen', False):
        # 如果是打包后的exe文件
        program_dir = os.path.dirname(sys.executable)
    else:
        # 如果是python脚本
        program_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 尝试在程序目录创建数据库
    db_path = os.path.join(program_dir, "clipboard_history.db")
    if _test_db_path(db_path):
        return db_path
    
    # 尝试在用户数据目录创建
    try:
        import appdirs
        user_data_dir = appdirs.user_data_dir("ClipboardManager", "ClipboardManager")
        os.makedirs(user_data_dir, exist_ok=True)
        db_path = os.path.join(user_data_dir, "clipboard_history.db")
        if _test_db_path(db_path):
            return db_path
    except ImportError:
        pass
    
    # 尝试在AppData目录创建
    appdata_dir = os.environ.get('APPDATA')
    if appdata_dir:
        clipboard_dir = os.path.join(appdata_dir, "ClipboardManager")
        os.makedirs(clipboard_dir, exist_ok=True)
        db_path = os.path.join(clipboard_dir, "clipboard_history.db")
        if _test_db_path(db_path):
            return db_path
    
    # 尝试在临时目录创建
    temp_dir = os.environ.get('TEMP', os.environ.get('TMP', '/tmp'))
    clipboard_dir = os.path.join(temp_dir, "ClipboardManager")
    os.makedirs(clipboard_dir, exist_ok=True)
    db_path = os.path.join(clipboard_dir, "clipboard_history.db")
    if _test_db_path(db_path):
        return db_path
    
    # 最后回退到程序目录
    return os.path.join(program_dir, "clipboard_history.db")

def _test_db_path(db_path):
    """
    测试数据库路径是否可用
    """
    try:
        conn = sqlite3.connect(db_path)
        conn.close()
        # 如果文件已存在，删除测试文件
        if os.path.exists(db_path):
            os.remove(db_path)
        return True
    except Exception as e:
        print(f"测试数据库路径 {db_path} 失败: {e}")
        return False

if __name__ == "__main__":
    db_path = get_appropriate_db_path()
    print(f"推荐的数据库路径: {db_path}")
    
    # 测试创建数据库
    try:
        conn = sqlite3.connect(db_path)
        print("数据库连接成功!")
        conn.close()
        
        # 删除测试文件
        if os.path.exists(db_path):
            os.remove(db_path)
    except Exception as e:
        print(f"数据库连接测试失败: {e}")