#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
清理重复MD5记录的脚本
"""

import sqlite3

def cleanup_duplicates():
    """清理重复的MD5记录"""
    conn = sqlite3.connect('clipboard_history.db')
    cursor = conn.cursor()
    
    # 查找所有重复的MD5值
    cursor.execute("""
        SELECT md5_hash, COUNT(*) as count 
        FROM text_records 
        WHERE md5_hash IS NOT NULL 
        GROUP BY md5_hash 
        HAVING COUNT(*) > 1
    """)
    duplicates = cursor.fetchall()
    
    print(f"发现 {len(duplicates)} 组重复的MD5记录")
    
    for md5_hash, count in duplicates:
        print(f"\n处理MD5: {md5_hash} (共{count}条记录)")
        
        # 获取所有具有相同MD5的记录
        cursor.execute("""
            SELECT id, content, timestamp, char_count, number
            FROM text_records 
            WHERE md5_hash = ?
            ORDER BY timestamp DESC
        """, (md5_hash,))
        
        records = cursor.fetchall()
        print(f"  找到 {len(records)} 条记录")
        
        # 保留第一条记录（最新的），并累加计数
        main_record = records[0]
        main_id, content, timestamp, char_count, main_number = main_record
        
        # 计算总的计数
        total_number = sum(record[4] for record in records)
        print(f"  主记录ID: {main_id}, 原始计数: {main_number}, 总计数: {total_number}")
        
        # 更新主记录的计数
        cursor.execute("""
            UPDATE text_records 
            SET number = ?
            WHERE id = ?
        """, (total_number, main_id))
        
        # 删除其他重复记录
        duplicate_ids = [record[0] for record in records[1:]]
        if duplicate_ids:
            placeholders = ','.join('?' * len(duplicate_ids))
            cursor.execute(f"DELETE FROM text_records WHERE id IN ({placeholders})", duplicate_ids)
            print(f"  删除了 {len(duplicate_ids)} 条重复记录")
    
    conn.commit()
    conn.close()
    print("\n清理完成")

if __name__ == "__main__":
    cleanup_duplicates()