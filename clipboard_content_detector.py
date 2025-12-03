#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
剪贴板内容检测器
功能：检测剪贴板中的内容类型并处理
"""

import win32clipboard
import win32con
import os
import hashlib
from datetime import datetime
from clipboard_db import ClipboardDatabase

def get_clipboard_formats():
    """获取剪贴板中所有可用的格式"""
    formats = []
    try:
        win32clipboard.OpenClipboard()
        format_id = 0
        while True:
            format_id = win32clipboard.EnumClipboardFormats(format_id)
            if not format_id:
                break
            formats.append(format_id)
    except Exception as e:
        print(f"枚举剪贴板格式时出错: {e}")
    finally:
        try:
            win32clipboard.CloseClipboard()
        except:
            pass
    return formats

def format_name(format_id):
    """获取格式ID对应的名称"""
    # 常见格式映射
    format_names = {
        win32con.CF_TEXT: "CF_TEXT",
        win32con.CF_BITMAP: "CF_BITMAP",
        win32con.CF_METAFILEPICT: "CF_METAFILEPICT",
        win32con.CF_SYLK: "CF_SYLK",
        win32con.CF_DIF: "CF_DIF",
        win32con.CF_TIFF: "CF_TIFF",
        win32con.CF_OEMTEXT: "CF_OEMTEXT",
        win32con.CF_DIB: "CF_DIB",
        win32con.CF_PALETTE: "CF_PALETTE",
        win32con.CF_PENDATA: "CF_PENDATA",
        win32con.CF_RIFF: "CF_RIFF",
        win32con.CF_WAVE: "CF_WAVE",
        win32con.CF_UNICODETEXT: "CF_UNICODETEXT",
        win32con.CF_ENHMETAFILE: "CF_ENHMETAFILE",
        win32con.CF_HDROP: "CF_HDROP",
        win32con.CF_LOCALE: "CF_LOCALE",
        win32con.CF_DIBV5: "CF_DIBV5",
        win32con.CF_OWNERDISPLAY: "CF_OWNERDISPLAY",
        win32con.CF_DSPTEXT: "CF_DSPTEXT",
        win32con.CF_DSPBITMAP: "CF_DSPBITMAP",
        win32con.CF_DSPMETAFILEPICT: "CF_DSPMETAFILEPICT",
        win32con.CF_DSPENHMETAFILE: "CF_DSPENHMETAFILE",
    }
    
    # 尝试注册一些常用格式
    try:
        html_format = win32clipboard.RegisterClipboardFormat("HTML Format")
        format_names[html_format] = "HTML Format"
    except:
        pass
    
    try:
        png_format = win32clipboard.RegisterClipboardFormat("PNG")
        format_names[png_format] = "PNG"
    except:
        pass
    
    # 返回格式名称
    if format_id in format_names:
        return format_names[format_id]
    else:
        try:
            # 尝试获取自定义格式名称
            name = win32clipboard.GetClipboardFormatName(format_id)
            return name if name else f"Unknown({format_id})"
        except:
            return f"Unknown({format_id})"

def get_clipboard_content():
    """获取剪贴板内容"""
    content_info = {
        'text': None,
        'files': [],
        'formats': [],
        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    try:
        win32clipboard.OpenClipboard()
        
        # 获取所有格式
        formats = get_clipboard_formats()
        content_info['formats'] = formats
        
        # 尝试获取文本内容
        if win32clipboard.IsClipboardFormatAvailable(win32con.CF_UNICODETEXT):
            try:
                text_content = win32clipboard.GetClipboardData(win32con.CF_UNICODETEXT)
                if text_content and text_content.strip():
                    content_info['text'] = text_content
            except Exception as e:
                print(f"读取Unicode文本时出错: {e}")
        
        if not content_info['text'] and win32clipboard.IsClipboardFormatAvailable(win32con.CF_TEXT):
            try:
                text_content = win32clipboard.GetClipboardData(win32con.CF_TEXT)
                if text_content and text_content.strip():
                    content_info['text'] = text_content
            except Exception as e:
                print(f"读取ANSI文本时出错: {e}")
        
        # 尝试获取文件列表
        if win32clipboard.IsClipboardFormatAvailable(win32con.CF_HDROP):
            try:
                files = win32clipboard.GetClipboardData(win32con.CF_HDROP)
                if files:
                    content_info['files'] = list(files)
            except Exception as e:
                print(f"读取文件列表时出错: {e}")
                
    except Exception as e:
        print(f"读取剪贴板时出错: {e}")
    finally:
        try:
            win32clipboard.CloseClipboard()
        except:
            pass
    
    return content_info

def calculate_text_md5(text):
    """计算文本内容的MD5值"""
    return hashlib.md5(text.encode('utf-8')).hexdigest()

def check_copy_limits(files, db):
    """检查复制限制"""
    # 获取当前设置
    settings = db.get_settings()
    
    # 如果是无限模式，直接返回True
    if settings['unlimited_mode']:
        return True, ""
    
    # 检查文件数量限制
    if len(files) > settings['max_copy_count']:
        return False, f"一次复制的文件数量({len(files)}个)超过了限制({settings['max_copy_count']}个)"
    
    # 检查文件大小限制
    total_size = 0
    for file_path in files:
        if os.path.exists(file_path):
            try:
                file_size = os.path.getsize(file_path)
                total_size += file_size
                
                # 检查单个文件是否超过大小限制
                if file_size > settings['max_copy_size']:
                    # 格式化文件大小
                    size_str = format_file_size(file_size)
                    limit_str = format_file_size(settings['max_copy_size'])
                    return False, f"文件 '{os.path.basename(file_path)}' 大小({size_str})超过了限制({limit_str})"
            except Exception as e:
                print(f"获取文件大小时出错: {e}")
    
    # 检查总大小是否超过限制
    if total_size > settings['max_copy_size']:
        # 格式化文件大小
        total_str = format_file_size(total_size)
        limit_str = format_file_size(settings['max_copy_size'])
        return False, f"一次复制的总大小({total_str})超过了限制({limit_str})"
    
    return True, ""

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

def format_content_display(content_info):
    """格式化显示内容"""
    print(f"\n[{content_info['timestamp']}] 剪贴板内容发生变化:")
    print("-" * 50)
    
    # 显示文本内容
    if content_info['text']:
        text_preview = content_info['text'][:100] + "..." if len(content_info['text']) > 100 else content_info['text']
        print(f"📝 文本内容: {repr(text_preview)}")
    else:
        print("📝 文本内容: 无")
    
    # 显示文件内容
    if content_info['files']:
        print(f"📁 文件列表 ({len(content_info['files'])} 个文件):")
        for i, file_path in enumerate(content_info['files'], 1):
            print(f"   {i}. {file_path}")
    else:
        print("📁 文件列表: 无")
    
    # 显示格式信息（可选，用于调试）
    # print(f"📊 剪贴板格式: {len(content_info['formats'])} 种")
    
    print("-" * 50)

def monitor_clipboard(interval=1, auto_save=False):
    """监控剪贴板变化"""
    print("🔍 开始监控剪贴板...")
    print(f"⏱  检测间隔: {interval}秒")
    print("按 Ctrl+C 停止监控")
    print("=" * 50)
    
    # 初始化数据库
    db = ClipboardDatabase()
    
    previous_content_key = None
    
    try:
        while True:
            # 获取当前剪贴板内容
            content_info = get_clipboard_content()
            
            # 创建内容唯一标识
            content_key = ""
            if content_info['text']:
                # 对于所有文本，都使用MD5作为标识以确保一致性
                content_key = f"text_md5:{calculate_text_md5(content_info['text'])}"
            elif content_info['files']:
                content_key = f"files:{';'.join(sorted(content_info['files']))}"
            
            # 检查内容是否发生变化
            if content_key and content_key != previous_content_key:
                # 检查复制限制（如果是文件）
                if content_info['files']:
                    allowed, message = check_copy_limits(content_info['files'], db)
                    if not allowed:
                        print(f"🚫 复制限制: {message}")
                        previous_content_key = content_key
                        continue
                
                # 显示内容
                format_content_display(content_info)
                
                # 如果启用自动保存，这里可以调用保存函数
                if auto_save:
                    print("💾 自动保存功能已启用（实际保存逻辑需要实现）")
                
                # 更新前一个内容标识
                previous_content_key = content_key
            
            # 等待一段时间再检查
            import time
            time.sleep(interval)
            
    except KeyboardInterrupt:
        print("\n👋 剪贴板监控已停止")

if __name__ == "__main__":
    monitor_clipboard()