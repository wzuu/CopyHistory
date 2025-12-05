#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
剪贴板管理器启动脚本
同时运行监控器和GUI界面
"""

import threading
import sys
import os
# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from clipboard_manager_main import ClipboardManager, monitor_clipboard_loop
# 导入改进的事件驱动剪贴板监听器
from improved_clipboard_monitor import monitor_clipboard_with_events, ClipboardMonitorWindow
# 使用PySide6版本的GUI
from clipboard_pyside_gui import main as gui_main
import win32gui
import win32con
import win32api
import win32event

def is_already_running():
    """检查程序是否已经运行"""
    mutex_name = "ClipboardManager_Mutex"
    try:
        # 创建一个互斥锁
        mutex = win32event.CreateMutex(None, False, mutex_name)
        # 检查是否已经存在同名互斥锁
        if win32api.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
            win32api.CloseHandle(mutex)
            return True
        return False
    except Exception as e:
        print(f"检查程序是否已运行时出错: {e}")
        return False

def main():
    """主函数"""
    # 检查程序是否已经运行
    if is_already_running():
        print("📋 剪贴板管理器已经在运行中!")
        # 尝试激活已运行的窗口
        try:
            hwnd = win32gui.FindWindow(None, "剪贴板管理器")
            if hwnd:
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                win32gui.SetForegroundWindow(hwnd)
        except:
            pass
        return
    
    # 创建剪贴板管理器
    manager = ClipboardManager()
    
    # 使用事件驱动方式监听剪贴板变化（替代轮询方式）
    monitor_thread = threading.Thread(
        target=monitor_clipboard_with_events, 
        args=(manager,), 
        daemon=True
    )
    monitor_thread.start()
    print("📋 剪贴板监控已在后台启动 (事件驱动模式)")
    
    # 运行PySide6 GUI应用
    print("🖥️  剪贴板管理器已在系统托盘运行")
    print("点击系统托盘图标显示界面，或按 Alt+C")
    
    # 直接调用PySide6 GUI主函数
    gui_main()
    
    print("👋 应用已退出")

if __name__ == "__main__":
    main()