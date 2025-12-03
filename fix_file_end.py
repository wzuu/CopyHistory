#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复文件末尾问题的脚本
"""

def fix_file_end(file_path):
    """修复文件末尾问题"""
    # 读取文件内容
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 检查文件末尾是否正确
    if not content.endswith('\n'):
        content += '\n'
    
    # 确保main函数正确结束
    # 查找main函数定义
    main_start = content.rfind('def main():')
    if main_start != -1:
        # 查找main函数结束位置
        main_end = content.find('\nif __name__ == "__main__":', main_start)
        if main_end != -1:
            # 确保main函数有正确的结构
            main_section = content[main_start:main_end]
            if '"""主函数"""' in main_section:
                print("Main function structure looks correct")
    
    # 写回文件
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"Fixed file end for {file_path}")

if __name__ == "__main__":
    fix_file_end("clipboard_gui.py")