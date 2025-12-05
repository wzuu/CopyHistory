#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
改进版剪贴板监听器
使用Windows剪贴板监听API替代轮询方式
"""

import ctypes
from ctypes import wintypes
import win32gui
import win32con
import threading
from datetime import datetime
from clipboard_manager_main import ClipboardManager

# Windows API常量和结构体定义
WM_CLIPBOARDUPDATE = 0x031D

# 定义WNDPROC类型
WNDPROC = ctypes.WINFUNCTYPE(ctypes.c_long, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)

# Windows API函数声明
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

user32.AddClipboardFormatListener.argtypes = [wintypes.HWND]
user32.AddClipboardFormatListener.restype = wintypes.BOOL

user32.RemoveClipboardFormatListener.argtypes = [wintypes.HWND]
user32.RemoveClipboardFormatListener.restype = wintypes.BOOL

# 确保正确的类型定义
if ctypes.sizeof(ctypes.c_long) != ctypes.sizeof(ctypes.c_void_p):
    LRESULT = ctypes.c_int64 if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_long
else:
    LRESULT = ctypes.c_long

DefWindowProcW = user32.DefWindowProcW
DefWindowProcW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
DefWindowProcW.restype = LRESULT

class WNDCLASS(ctypes.Structure):
    _fields_ = [("style", wintypes.UINT),
                ("lpfnWndProc", WNDPROC),
                ("cbClsExtra", wintypes.INT),
                ("cbWndExtra", wintypes.INT),
                ("hInstance", wintypes.HANDLE),
                ("hIcon", wintypes.HANDLE),
                ("hCursor", wintypes.HANDLE),
                ("hbrBackground", wintypes.HBRUSH),
                ("lpszMenuName", wintypes.LPCWSTR),
                ("lpszClassName", wintypes.LPCWSTR)]

class MSG(ctypes.Structure):
    _fields_ = [("hwnd", wintypes.HWND),
                ("message", wintypes.UINT),
                ("wParam", wintypes.WPARAM),
                ("lParam", wintypes.LPARAM),
                ("time", wintypes.DWORD),
                ("pt", wintypes.POINT)]

class ClipboardMonitorWindow:
    """
    剪贴板监听窗口类
    创建一个隐藏窗口来接收剪贴板更新消息
    """
    
    def __init__(self, clipboard_manager):
        self.clipboard_manager = clipboard_manager
        self.hwnd = None
        self.class_atom = None
        self._window_class = None
        self._wnd_proc = None
        
    def _window_proc(self, hwnd, msg, wparam, lparam):
        """窗口过程回调函数"""
        if msg == WM_CLIPBOARDUPDATE:
            # 剪贴板内容发生变化
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 剪贴板内容发生变化")
            # 处理剪贴板内容
            self.clipboard_manager.process_clipboard_content()
            return 0
        return DefWindowProcW(hwnd, msg, wparam, lparam)
        
    def create_window(self):
        """创建隐藏的消息窗口"""
        # 创建窗口过程回调
        self._wnd_proc = WNDPROC(self._window_proc)
        
        # 定义窗口类
        self._window_class = WNDCLASS()
        self._window_class.lpfnWndProc = self._wnd_proc
        self._window_class.hInstance = kernel32.GetModuleHandleW(None)
        self._window_class.lpszClassName = "ClipboardMonitorWindow"
        
        # 注册窗口类
        self.class_atom = user32.RegisterClassW(ctypes.byref(self._window_class))
        if not self.class_atom:
            raise Exception("Failed to register window class")
            
        # 创建隐藏窗口
        self.hwnd = user32.CreateWindowExW(
            0,                              # dwExStyle
            self._window_class.lpszClassName, # lpClassName
            "Clipboard Monitor",            # lpWindowName
            0,                              # dwStyle (WS_OVERLAPPEDWINDOW)
            0, 0, 0, 0,                     # X, Y, nWidth, nHeight
            None,                           # hWndParent
            None,                           # hMenu
            self._window_class.hInstance,   # hInstance
            None                            # lpParam
        )
        
        if not self.hwnd:
            raise Exception("Failed to create window")
            
        # 添加剪贴板格式监听器
        if not user32.AddClipboardFormatListener(self.hwnd):
            raise Exception("Failed to add clipboard format listener")
            
        print("📋 剪贴板监听器已启动 (基于事件监听机制)")
        print("即时发生剪贴板变化时才会处理，无需轮询")
        print("=" * 50)
        
    def destroy_window(self):
        """销毁窗口和监听器"""
        if self.hwnd:
            # 移除剪贴板格式监听器
            user32.RemoveClipboardFormatListener(self.hwnd)
            # 销毁窗口
            user32.DestroyWindow(self.hwnd)
            self.hwnd = None
            
        if self.class_atom:
            # 注销窗口类
            user32.UnregisterClassW(self._window_class.lpszClassName, self._window_class.hInstance)
            self.class_atom = None

def monitor_clipboard_with_events(clipboard_manager):
    """
    使用事件监听方式监控剪贴板
    替代原来的轮询方式
    """
    # 创建监听窗口
    monitor_window = ClipboardMonitorWindow(clipboard_manager)
    
    try:
        # 创建窗口
        monitor_window.create_window()
        
        # 消息循环
        msg = MSG()
        while True:
            # 获取消息
            ret = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
            if ret == -1:  # 错误
                break
            elif ret == 0:  # WM_QUIT
                break
            else:
                # 翻译和分发消息
                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))
                
    except KeyboardInterrupt:
        print("\n👋 剪贴板监听器已停止")
    finally:
        # 清理资源
        monitor_window.destroy_window()

def main():
    """主函数"""
    # 创建剪贴板管理器
    manager = ClipboardManager()
    
    # 使用事件驱动方式监控剪贴板
    monitor_clipboard_with_events(manager)

if __name__ == "__main__":
    main()