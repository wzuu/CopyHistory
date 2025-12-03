#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复文件中的全角字符问题
"""

def fix_full_width_characters(file_path):
    """修复文件中的全角字符"""
    # 全角到半角的映射
    full_to_half = {
        '，': ',',
        '：': ':',
        '（': '(',
        '）': ')',
        '“': '"',
        '”': '"',
        '‘': "'",
        '’': "'",
        '。': '.',
        '；': ';',
        '？': '?',
        '！': '!',
        '　': ' ',  # 全角空格
        '０': '0',
        '１': '1',
        '２': '2',
        '３': '3',
        '４': '4',
        '５': '5',
        '６': '6',
        '７': '7',
        '８': '8',
        '９': '9',
        'Ａ': 'A',
        'Ｂ': 'B',
        'Ｃ': 'C',
        'Ｄ': 'D',
        'Ｅ': 'E',
        'Ｆ': 'F',
        'Ｇ': 'G',
        'Ｈ': 'H',
        'Ｉ': 'I',
        'Ｊ': 'J',
        'Ｋ': 'K',
        'Ｌ': 'L',
        'Ｍ': 'M',
        'Ｎ': 'N',
        'Ｏ': 'O',
        'Ｐ': 'P',
        'Ｑ': 'Q',
        'Ｒ': 'R',
        'Ｓ': 'S',
        'Ｔ': 'T',
        'Ｕ': 'U',
        'Ｖ': 'V',
        'Ｗ': 'W',
        'Ｘ': 'X',
        'Ｙ': 'Y',
        'Ｚ': 'Z',
        'ａ': 'a',
        'ｂ': 'b',
        'ｃ': 'c',
        'ｄ': 'd',
        'ｅ': 'e',
        'ｆ': 'f',
        'ｇ': 'g',
        'ｈ': 'h',
        'ｉ': 'i',
        'ｊ': 'j',
        'ｋ': 'k',
        'ｌ': 'l',
        'ｍ': 'm',
        'ｎ': 'n',
        'ｏ': 'o',
        'ｐ': 'p',
        'ｑ': 'q',
        'ｒ': 'r',
        'ｓ': 's',
        'ｔ': 't',
        'ｕ': 'u',
        'ｖ': 'v',
        'ｗ': 'w',
        'ｘ': 'x',
        'ｙ': 'y',
        'ｚ': 'z',
    }
    
    # 读取文件
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 统计修复前的全角字符
    count_before = sum(1 for ch in content if ch in full_to_half)
    print(f"修复前发现 {count_before} 个全角字符")
    
    # 替换全角字符
    for full, half in full_to_half.items():
        content = content.replace(full, half)
    
    # 写回文件
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"成功修复文件 {file_path}")

if __name__ == "__main__":
    fix_full_width_characters("clipboard_gui.py")