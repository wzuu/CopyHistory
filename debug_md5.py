#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试文本MD5功能的脚本
"""

from clipboard_db import ClipboardDatabase
import hashlib
import sqlite3

def debug_text_md5_feature():
    """调试文本MD5功能"""
    print("开始调试文本MD5功能...")
    
    # 初始化数据库
    db = ClipboardDatabase()
    
    # 使用相同的长文本进行测试
    long_text = "这是一个较长的测试文本，用于测试MD5功能。" * 100
    
    print(f"文本长度: {len(long_text)} 字符")
    
    # 计算MD5
    md5_hash = hashlib.md5(long_text.encode('utf-8')).hexdigest()
    print(f"MD5: {md5_hash}")
    
    # 第一次保存
    print("\n第一次保存...")
    record_id1 = db.save_text_record(long_text)
    print(f"第一次保存的记录ID: {record_id1}")
    
    # 检查数据库状态
    conn = sqlite3.connect(db.db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id, md5_hash, number FROM text_records WHERE md5_hash = ?", (md5_hash,))
    result = cursor.fetchall()
    print(f"数据库中的记录: {result}")
    conn.close()
    
    # 第二次保存相同的文本
    print("\n第二次保存相同的文本...")
    record_id2 = db.save_text_record(long_text)
    print(f"第二次保存的记录ID: {record_id2}")
    
    # 检查数据库状态
    conn = sqlite3.connect(db.db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id, md5_hash, number FROM text_records WHERE md5_hash = ?", (md5_hash,))
    result = cursor.fetchall()
    print(f"数据库中的记录: {result}")
    conn.close()
    
    print("\n调试完成。")

if __name__ == "__main__":
    debug_text_md5_feature()