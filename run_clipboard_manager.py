#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
剪贴板管理器启动脚本
同时运行监控器和GUI界面
"""

import threading
import tkinter as tk
from clipboard_manager_main import ClipboardManager, monitor_clipboard_loop
from clipboard_gui import ClipboardGUI
import win32gui
import win32con
import win32api
import win32event
import sys

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
    
    # 在单独线程中运行剪贴板监控
    monitor_thread = threading.Thread(target=monitor_clipboard_loop, args=(manager, 1), daemon=True)
    monitor_thread.start()
    print("📋 剪贴板监控已在后台启动")
    
    # 运行GUI应用（默认隐藏主窗口，显示系统托盘图标）
    root = tk.Tk()
    app = ClipboardGUI(root)
    
    # 默认隐藏主窗口，只显示系统托盘图标
    root.withdraw()
    app.is_hidden = True
    
    print("🖥️  剪贴板管理器已在系统托盘运行")
    print("点击系统托盘图标显示界面，或按 Alt+C")
    
    root.mainloop()
    
    print("👋 应用已退出")

if __name__ == "__main__":
    main()