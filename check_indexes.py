#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查数据库索引的脚本
"""

import sqlite3

def check_indexes():
    """检查数据库索引"""
    conn = sqlite3.connect('clipboard_history.db')
    cursor = conn.cursor()
    
    # 查询text_records表的索引
    cursor.execute('SELECT name FROM sqlite_master WHERE type="index" AND tbl_name="text_records"')
    indexes = cursor.fetchall()
    print('Text records indexes:', indexes)
    
    # 查询file_records表的索引
    cursor.execute('SELECT name FROM sqlite_master WHERE type="index" AND tbl_name="file_records"')
    indexes = cursor.fetchall()
    print('File records indexes:', indexes)
    
    conn.close()

if __name__ == "__main__":
    check_indexes()