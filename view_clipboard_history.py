#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
查看剪贴板历史记录
"""

from clipboard_db import ClipboardDatabase
import os

def format_file_size(size_bytes):
    """格式化文件大小"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"

def view_history():
    """查看历史记录"""
    print("📋 剪贴板历史记录查看器")
    print("=" * 50)
    
    # 创建数据库实例
    db = ClipboardDatabase()
    
    # 查看文本记录
    print("📄 文本记录:")
    print("-" * 30)
    text_records = db.get_text_records(20)  # 获取最近20条记录
    if text_records:
        for i, record in enumerate(text_records, 1):
            print(f"{i:2d}. 时间: {record[2]}")
            content_preview = record[1].replace('\n', '\\n')[:100] + "..." if len(record[1]) > 100 else record[1].replace('\n', '\\n')
            print(f"     内容: {content_preview}")
            print()
    else:
        print("    暂无文本记录")
    
    # 查看文件记录
    print("\n📁 文件记录:")
    print("-" * 30)
    file_records = db.get_file_records(20)  # 获取最近20条记录
    if file_records:
        for i, record in enumerate(file_records, 1):
            print(f"{i:2d}. 文件名: {record[3]}")
            print(f"     大小: {format_file_size(record[4])} | 类型: {record[5]} | 时间: {record[7]}")
            print()
    else:
        print("    暂无文件记录")
    
    # 统计信息
    print("\n📊 统计信息:")
    print("-" * 30)
    print(f"    文本记录总数: {len(text_records)}")
    print(f"    文件记录总数: {len(file_records)}")
    
    if file_records:
        total_size = sum(record[4] for record in file_records)
        print(f"    文件总大小: {format_file_size(total_size)}")
        
        # 按类型统计
        type_count = {}
        for record in file_records:
            file_type = record[5]
            type_count[file_type] = type_count.get(file_type, 0) + 1
        
        print("    文件类型分布:")
        for file_type, count in sorted(type_count.items()):
            print(f"      {file_type}: {count} 个")

if __name__ == "__main__":
    view_history()