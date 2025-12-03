#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查数据库内容的脚本
"""

import sqlite3

def check_database():
    """检查数据库内容"""
    conn = sqlite3.connect('clipboard_history.db')
    cursor = conn.cursor()
    
    # 查询最近的带有MD5的记录
    cursor.execute("SELECT id, md5_hash, number FROM text_records WHERE md5_hash IS NOT NULL ORDER BY id DESC LIMIT 10")
    results = cursor.fetchall()
    print('最近的带MD5的记录:')
    for r in results:
        print(r)
    
    # 查询具有相同MD5的记录
    cursor.execute("SELECT md5_hash, COUNT(*) as count FROM text_records WHERE md5_hash IS NOT NULL GROUP BY md5_hash HAVING COUNT(*) > 1")
    duplicates = cursor.fetchall()
    print('\n重复的MD5记录:')
    for d in duplicates:
        print(d)
    
    conn.close()

if __name__ == "__main__":
    check_database()