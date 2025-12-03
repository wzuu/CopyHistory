#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查数据库内容的脚本
"""

import sqlite3
import os

def check_database():
    """检查数据库内容"""
    db_path = "clipboard_history.db"
    
    if not os.path.exists(db_path):
        print(f"数据库文件不存在: {db_path}")
        return
    
    print(f"数据库路径: {os.path.abspath(db_path)}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 检查文本记录
        cursor.execute('SELECT COUNT(*) FROM text_records')
        text_count = cursor.fetchone()[0]
        print(f"文本记录数量: {text_count}")
        
        if text_count > 0:
            print("文本记录详情:")
            cursor.execute('SELECT id, content, timestamp, char_count, md5_hash, number FROM text_records')
            records = cursor.fetchall()
            for record in records:
                print(f"  ID: {record[0]}, 字符数: {record[3]}, 次数: {record[5]}, 内容: {record[1][:50]}...")
        
        # 检查文件记录
        cursor.execute('SELECT COUNT(*) FROM file_records')
        file_count = cursor.fetchone()[0]
        print(f"文件记录数量: {file_count}")
        
        if file_count > 0:
            print("文件记录详情:")
            cursor.execute('SELECT id, filename, file_size, file_type, md5_hash, timestamp, number FROM file_records')
            records = cursor.fetchall()
            for record in records:
                print(f"  ID: {record[0]}, 文件名: {record[1]}, 大小: {record[2]}, 类型: {record[3]}, 次数: {record[6]}")
        
        # 检查设置
        cursor.execute('SELECT max_copy_size, max_copy_count, unlimited_mode FROM settings WHERE id = 1')
        settings = cursor.fetchone()
        if settings:
            print(f"设置: max_copy_size={settings[0]}, max_copy_count={settings[1]}, unlimited_mode={settings[2]}")
        
        conn.close()
        
    except Exception as e:
        print(f"检查数据库时出错: {e}")

if __name__ == "__main__":
    check_database()