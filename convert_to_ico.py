#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
将jpg图片转换为ico图标文件
"""

from PIL import Image
import os

def convert_jpg_to_ico(jpg_path, ico_path, size=(32, 32)):
    """
    将jpg图片转换为ico图标文件
    
    Args:
        jpg_path (str): JPG图片路径
        ico_path (str): 输出ICO文件路径
        size (tuple): 图标尺寸，默认为32x32
    """
    try:
        # 打开JPG图片
        img = Image.open(jpg_path)
        
        # 转换为RGBA模式（支持透明度）
        img = img.convert("RGBA")
        
        # 调整图片大小
        img = img.resize(size, Image.Resampling.LANCZOS)
        
        # 保存为ICO文件
        img.save(ico_path, format="ICO")
        
        print(f"成功将 {jpg_path} 转换为 {ico_path}")
        return True
    except Exception as e:
        print(f"转换失败: {e}")
        return False

if __name__ == "__main__":
    # 转换2.jpg为mini.ico
    jpg_file = "2.jpg"
    ico_file = "mini.ico"
    
    if os.path.exists(jpg_file):
        convert_jpg_to_ico(jpg_file, ico_file, (32, 32))
        convert_jpg_to_ico(jpg_file, "icon.ico", (256, 256))
        print("图标转换完成！")
    else:
        print(f"找不到文件: {jpg_file}")