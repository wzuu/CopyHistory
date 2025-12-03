#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试数据库修复是否有效的脚本
"""

import os
import sys

def test_database_connection():
    """测试数据库连接"""
    print("测试数据库连接...")
    
    # 测试clipboard_db.py中的ClipboardDatabase
    try:
        from clipboard_db import ClipboardDatabase
        db1 = ClipboardDatabase()
        print(f"✓ clipboard_db.py 数据库路径: {db1.db_path}")
        
        # 测试基本操作
        db1.init_database()
        print("✓ clipboard_db.py 数据库初始化成功")
    except Exception as e:
        print(f"✗ clipboard_db.py 数据库测试失败: {e}")
        return False
    
    # 测试clipboard_manager_main.py中的ClipboardDatabase
    try:
        from clipboard_manager_main import ClipboardDatabase
        db2 = ClipboardDatabase()
        print(f"✓ clipboard_manager_main.py 数据库路径: {db2.db_path}")
        
        # 测试基本操作
        db2.init_database()
        print("✓ clipboard_manager_main.py 数据库初始化成功")
    except Exception as e:
        print(f"✗ clipboard_manager_main.py 数据库测试失败: {e}")
        return False
    
    return True

def test_clipboard_manager():
    """测试ClipboardManager"""
    print("\n测试ClipboardManager...")
    
    try:
        from clipboard_manager_main import ClipboardManager
        manager = ClipboardManager()
        print("✓ ClipboardManager 初始化成功")
        print(f"  数据库路径: {manager.db.db_path}")
        
        # 测试获取设置
        settings = manager.db.get_settings()
        print("✓ 数据库设置读取成功")
        return True
    except Exception as e:
        print(f"✗ ClipboardManager 测试失败: {e}")
        return False

if __name__ == "__main__":
    print("开始测试数据库修复...")
    print("=" * 50)
    
    success = True
    success &= test_database_connection()
    success &= test_clipboard_manager()
    
    print("\n" + "=" * 50)
    if success:
        print("✓ 所有测试通过！数据库修复成功。")
        sys.exit(0)
    else:
        print("✗ 测试失败，请检查错误信息。")
        sys.exit(1)