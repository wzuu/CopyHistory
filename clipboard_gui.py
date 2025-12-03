#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
剪贴板历史记录GUI界面
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import os
import sqlite3
import threading
import shutil
import sys
import functools
from clipboard_db import ClipboardDatabase

# 导入系统托盘相关库
try:
    from PIL import Image, ImageTk, ImageDraw
    import pystray
    TRAY_ICON_AVAILABLE = True
except ImportError:
    TRAY_ICON_AVAILABLE = False
    print("提示: 安装 pystray 和 Pillow 可以启用系统托盘图标功能")
    print("安装命令: pip install pystray pillow")

def resource_path(relative_path):
    """获取资源文件的绝对路径"""
    try:
        # PyInstaller创建临时文件夹，将路径存储在_MEIPASS中
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path)

class ClipboardGUI:
    def __init__(self, root):
        self.root = root
        self.db = ClipboardDatabase()
        self.tray_icon = None
        self.is_hidden = False
        self.update_job = None  # 用于定期更新的作业
        self.user_action_in_progress = False  # 标记是否有用户操作正在进行
        self.has_focus = False  # 标记窗口是否有焦点
        self.float_window = None  # 悬浮窗口引用
        
        # 设置窗口属性
        self.root.title("剪贴板历史记录")
        self.root.geometry("640x950")
        
        # 居中显示窗口
        self.center_window(640, 950)
        
        # 创建UI
        self.setup_ui()
        # 在UI创建完成后加载第一页记录
        self.root.after(100, self.load_records)
        
        # 检查开机自启设置
        self.check_auto_start()
        
        # 检查并创建悬浮图标
        self.check_float_icon()
        
        # 开始定期更新
        self.start_auto_update()
        
        # 设置窗口关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self.hide_window)
        
        # 绑定焦点事件
        self.root.bind("<FocusIn>", self.on_focus_in)
        self.root.bind("<FocusOut>", self.on_focus_out)
        
        # 如果支持系统托盘，创建托盘图标
        if TRAY_ICON_AVAILABLE:
            self.create_tray_icon()
    
    def check_float_icon(self):
        """检查并根据设置创建悬浮图标"""
        try:
            settings = self.db.get_settings()
            if settings['float_icon']:
                self.create_float_icon()
        except Exception as e:
            print(f"检查悬浮图标设置时出错: {e}")
    
    def check_auto_start(self):
        """检查并应用开机自启设置"""
        try:
            settings = self.db.get_settings()
            if settings['auto_start']:
                self.set_auto_start(True)
        except Exception as e:
            print(f"检查开机自启设置时出错: {e}")
    
    def center_window(self, width, height):
        """居中显示窗口"""
        # 获取屏幕尺寸
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # 计算居中位置
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        
        # 设置窗口位置和大小
        self.root.geometry(f'{width}x{height}+{x}+{y}')
    
    def center_child_window(self, window, width, height):
        """居中显示子窗口"""
        # 获取屏幕尺寸
        screen_width = window.winfo_screenwidth()
        screen_height = window.winfo_screenheight()
        
        # 计算居中位置
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        
        # 设置窗口位置和大小
        window.geometry(f'{width}x{height}+{x}+{y}')
    
    def sanitize_text_for_display(self, text, max_length=100):
        """清理文本内容，移除换行符并截断过长内容"""
        # 将换行符替换为空格
        sanitized = text.replace('\n', ' ').replace('\r', ' ')
        # 截断过长内容
        if len(sanitized) <= max_length:
            return sanitized
        else:
            return sanitized[:max_length] + "..."
    
    def on_focus_in(self, event):
        """窗口获得焦点事件"""
        self.has_focus = True
    
    def on_focus_out(self, event):
        """窗口失去焦点事件"""
        # 检查是否是真的失去焦点而不是切换到子窗口
        if event.widget == self.root:
            self.has_focus = False
    
    def create_tray_icon(self):
        """创建系统托盘图标"""
        try:
            # 使用2.ico文件作为图标
            icon_path = resource_path("2.ico")
            if os.path.exists(icon_path):
                image = Image.open(icon_path)
            else:
                # 如果图标文件不存在，创建一个简单的图标
                image = Image.new('RGB', (64, 64), color=(73, 109, 137))
                draw = ImageDraw.Draw(image)
                draw.ellipse((10, 10, 54, 54), fill=(255, 255, 255))
                draw.text((20, 20), "C", fill=(0, 0, 0))
            
            # 创建菜单
            menu = pystray.Menu(
                pystray.MenuItem("显示界面", self.show_window, default=True),
                pystray.MenuItem("退出", self.quit_application)
            )
            
            self.tray_icon = pystray.Icon("clipboard_manager", image, "剪贴板管理器", menu)
            
            # 在单独线程中运行托盘图标
            tray_thread = threading.Thread(target=self.tray_icon.run, daemon=True)
            tray_thread.start()
        except Exception as e:
            print(f"创建系统托盘图标失败: {e}")
    
    def setup_ui(self):
        """设置UI界面"""
        # 创建主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 搜索框架
        search_frame = ttk.LabelFrame(main_frame, text="搜索", padding="10")
        search_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Label(search_frame, text="关键词:").grid(row=0, column=0, padx=(0, 5))
        self.search_entry = ttk.Entry(search_frame, width=30)
        self.search_entry.grid(row=0, column=1, padx=(0, 10))
        
        ttk.Button(search_frame, text="搜索", command=self.search_records).grid(row=0, column=2, padx=(0, 10))
        ttk.Button(search_frame, text="刷新", command=self.load_records).grid(row=0, column=3)
        
        # 创建笔记本控件（标签页）
        notebook = ttk.Notebook(main_frame)
        notebook.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 记录标签页
        self.records_frame = ttk.Frame(notebook)
        notebook.add(self.records_frame, text="记录")
        self.setup_records_tab()
        
        # 统计标签页
        self.stats_frame = ttk.Frame(notebook)
        notebook.add(self.stats_frame, text="统计")
        self.setup_stats_tab()
        
        # 设置标签页
        self.settings_frame = ttk.Frame(notebook)
        notebook.add(self.settings_frame, text="设置")
        self.setup_settings_tab()
        
        # 配置网格权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(1, weight=1)
        self.records_frame.columnconfigure(0, weight=1)
        self.records_frame.rowconfigure(0, weight=1)
        self.stats_frame.columnconfigure(0, weight=1)
        self.stats_frame.rowconfigure(0, weight=1)
        self.settings_frame.columnconfigure(0, weight=1)
        self.settings_frame.rowconfigure(0, weight=1)
        
        # 绑定快捷键 Alt+C
        self.root.bind('<Alt-c>', self.toggle_window)
        self.root.bind('<Alt-C>', self.toggle_window)
        
        # 设置焦点以确保快捷键生效
        self.root.focus_set()

    def setup_records_tab(self):
        """设置记录标签页"""
        # 移除分页参数
        
        # 初始化排序参数
        self.sort_column = "时间"  # 默认排序列
        self.sort_reverse = True   # 默认倒序（最新的在前面）
        
        # 创建树形视图，显示记录名称或内容、类型、大小、时间、次数
        columns = ("名称或内容", "类型", "大小", "时间", "次数")
        self.records_tree = ttk.Treeview(self.records_frame, columns=columns, show="headings", height=20)
        
        # 设置列标题和点击事件
        for col in columns:
            # 使用functools.partial解决闭包问题
            self.records_tree.heading(col, text=col, command=functools.partial(self.sort_by_column, col))
        
        # 初始化排序指示器
        self.update_sort_indicators()
        
        # 设置列宽和对齐方式
        self.records_tree.column("名称或内容", width=250, anchor="w")  # 左对齐
        self.records_tree.column("类型", width=80, anchor="center")  # 居中对齐
        self.records_tree.column("大小", width=80, anchor="center")  # 居中对齐
        self.records_tree.column("时间", width=130, anchor="center")  # 居中对齐
        self.records_tree.column("次数", width=50, anchor="center")  # 居中对齐
        
        # 添加垂直滚动条，取消横向滚动条
        records_scrollbar_y = ttk.Scrollbar(self.records_frame, orient=tk.VERTICAL, command=self.records_tree.yview)
        self.records_tree.configure(yscrollcommand=records_scrollbar_y.set)
        
        # 布局
        self.records_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        records_scrollbar_y.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # 添加按钮框架
        records_button_frame = ttk.Frame(self.records_frame)
        records_button_frame.grid(row=2, column=0, columnspan=2, pady=(10, 0), sticky=(tk.W, tk.E))
        
        ttk.Button(records_button_frame, text="复制选中内容", command=self.copy_selected_record).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(records_button_frame, text="删除选中记录", command=self.delete_selected_record).pack(side=tk.LEFT)
        
        # 添加双击事件显示完整内容
        self.records_tree.bind("<Double-1>", self.show_full_record)
        
        # 绑定滚动事件以实现自动加载更多
        self.records_tree.bind("<<TreeviewSelect>>", self.on_tree_select)
        self.records_tree.bind("<MouseWheel>", self.on_mouse_wheel)
        
        # 配置网格权重
        self.records_frame.columnconfigure(0, weight=1)
        self.records_frame.rowconfigure(0, weight=1)
    
    def sort_by_column(self, col):
        """根据点击的列进行排序"""
        # 如果点击的是同一列，则切换排序方向；否则默认倒序（与原始行为一致）
        if self.sort_column == col:
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_column = col
            self.sort_reverse = True  # 默认倒序，与原始行为一致
        
        # 更新列标题显示排序方向
        self.update_sort_indicators()
        
        # 重新加载记录
        self.load_records()
    
    def update_sort_indicators(self):
        """更新列标题的排序指示器"""
        # 清除所有列的指示器
        columns = ["名称或内容", "类型", "大小", "时间", "次数"]
        for col in columns:
            heading_text = col
            if col == self.sort_column:
                # 添加排序箭头
                if self.sort_reverse:
                    heading_text += " ↓"  # 倒序
                else:
                    heading_text += " ↑"  # 正序
            self.records_tree.heading(col, text=heading_text, command=lambda c=col: self.sort_by_column(c))
    
    def setup_stats_tab(self):
        """设置统计标签页"""
        # 创建统计信息显示区域
        stats_text = tk.Text(self.stats_frame, wrap=tk.WORD)
        stats_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 添加滚动条
        stats_scrollbar = ttk.Scrollbar(self.stats_frame, orient=tk.VERTICAL, command=stats_text.yview)
        stats_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        stats_text.configure(yscrollcommand=stats_scrollbar.set)
        
        # 保存文本控件引用以便更新
        self.stats_text = stats_text
        
        # 添加刷新按钮
        refresh_button_frame = ttk.Frame(self.stats_frame)
        refresh_button_frame.pack(pady=(0, 10))
        ttk.Button(refresh_button_frame, text="刷新统计", command=self.update_statistics_display).pack()
    
    def setup_settings_tab(self):
        """设置标签页 - 简化版，无需滚动，充满宽度"""
        # 创建设置界面容器，填充整个标签页
        settings_container = ttk.Frame(self.settings_frame)
        settings_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 创建主设置框架，使用网格布局
        settings_main_frame = ttk.Frame(settings_container)
        settings_main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 配置网格权重，使内容可以扩展
        settings_main_frame.columnconfigure(0, weight=1)
        
        # 复制限制设置
        ttk.Label(settings_main_frame, text="复制限制设置", font=("Arial", 12, "bold")).grid(row=0, column=0, sticky=tk.W, pady=(0, 10))
        
        # 无限模式复选框
        self.unlimited_var = tk.BooleanVar()
        unlimited_check = ttk.Checkbutton(settings_main_frame, text="无限模式（无限制）", variable=self.unlimited_var)
        unlimited_check.grid(row=1, column=0, sticky=tk.W, pady=(0, 10))
        
        # 最大大小设置
        size_frame = ttk.LabelFrame(settings_main_frame, text="最大复制大小")
        size_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), padx=0, pady=(0, 10))
        size_frame.columnconfigure(1, weight=1)
        
        self.size_var = tk.StringVar()
        size_entry = ttk.Entry(size_frame, textvariable=self.size_var, width=10)
        size_entry.grid(row=0, column=0, padx=(10, 5), pady=10, sticky=tk.W)
        ttk.Label(size_frame, text="MB").grid(row=0, column=1, padx=(0, 10), pady=10, sticky=tk.W)
        
        # 最大数量设置
        count_frame = ttk.LabelFrame(settings_main_frame, text="最大复制文件数量")
        count_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), padx=0, pady=(0, 10))
        count_frame.columnconfigure(1, weight=1)
        
        self.count_var = tk.StringVar()
        count_entry = ttk.Entry(count_frame, textvariable=self.count_var, width=10)
        count_entry.grid(row=0, column=0, padx=(10, 5), pady=10, sticky=tk.W)
        ttk.Label(count_frame, text="个").grid(row=0, column=1, padx=(0, 10), pady=10, sticky=tk.W)
        
        # 保存天数设置
        ttk.Label(settings_main_frame, text="记录保存设置", font=("Arial", 12, "bold")).grid(row=4, column=0, sticky=tk.W, pady=(10, 5))
        
        retention_frame = ttk.LabelFrame(settings_main_frame, text="保存天数")
        retention_frame.grid(row=5, column=0, sticky=(tk.W, tk.E), padx=0, pady=(0, 10))
        retention_frame.columnconfigure(1, weight=1)
        
        # 永久保存选项
        self.retention_var = tk.StringVar()
        permanent_radio = ttk.Radiobutton(retention_frame, text="永久保存", variable=self.retention_var, value="permanent")
        permanent_radio.grid(row=0, column=0, sticky=tk.W, padx=10, pady=5)
        
        # 自定义天数选项
        custom_frame = ttk.Frame(retention_frame)
        custom_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), padx=10, pady=5)
        custom_frame.columnconfigure(1, weight=1)
        
        custom_radio = ttk.Radiobutton(custom_frame, text="自定义天数:", variable=self.retention_var, value="custom")
        custom_radio.grid(row=0, column=0, sticky=tk.W)
        
        self.days_var = tk.StringVar()
        self.days_entry = ttk.Entry(custom_frame, textvariable=self.days_var, width=10)
        self.days_entry.grid(row=0, column=1, padx=(5, 0), sticky=tk.W)
        ttk.Label(custom_frame, text="天").grid(row=0, column=2, padx=(5, 0), sticky=tk.W)
        
        # 开机自启设置
        ttk.Label(settings_main_frame, text="系统设置", font=("Arial", 12, "bold")).grid(row=6, column=0, sticky=tk.W, pady=(10, 5))
        
        autostart_frame = ttk.LabelFrame(settings_main_frame, text="开机自启")
        autostart_frame.grid(row=7, column=0, sticky=(tk.W, tk.E), padx=0, pady=(0, 10))
        
        self.autostart_var = tk.BooleanVar()
        autostart_check = ttk.Checkbutton(autostart_frame, text="允许程序开机自启", variable=self.autostart_var)
        autostart_check.grid(row=0, column=0, sticky=tk.W, padx=10, pady=10)
        
        # 悬浮图标设置
        ttk.Label(settings_main_frame, text="悬浮图标设置", font=("Arial", 12, "bold")).grid(row=8, column=0, sticky=tk.W, pady=(10, 5))
        
        float_icon_frame = ttk.LabelFrame(settings_main_frame, text="悬浮图标")
        float_icon_frame.grid(row=9, column=0, sticky=(tk.W, tk.E), padx=0, pady=(0, 10))
        
        self.float_icon_var = tk.BooleanVar()
        float_icon_check = ttk.Checkbutton(float_icon_frame, text="启用悬浮图标", variable=self.float_icon_var)
        float_icon_check.grid(row=0, column=0, sticky=tk.W, padx=10, pady=10)
        
        # 添加说明标签
        ttk.Label(float_icon_frame, text="悬浮图标大小: 50×50, 透明度: 15%, 可自由拖动, 点击显示页面", font=("Arial", 9)).grid(row=1, column=0, padx=10, pady=(0, 10), sticky=tk.W)
        
        # 重置所有记录按钮
        ttk.Label(settings_main_frame, text="数据管理", font=("Arial", 12, "bold")).grid(row=10, column=0, sticky=tk.W, pady=(10, 5))
        
        reset_frame = ttk.LabelFrame(settings_main_frame, text="重置所有记录")
        reset_frame.grid(row=11, column=0, sticky=(tk.W, tk.E), padx=0, pady=(0, 10))
        
        ttk.Label(reset_frame, text="此操作将删除所有记录和本地缓存文件！").grid(row=0, column=0, pady=10)
        ttk.Button(reset_frame, text="重置所有记录", command=self.reset_all_records).grid(row=1, column=0, pady=(0, 10))
        
        # 按钮框架
        button_frame = ttk.Frame(settings_main_frame)
        button_frame.grid(row=12, column=0, pady=(20, 0))
        
        ttk.Button(button_frame, text="保存设置", command=self.save_settings).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="恢复默认", command=self.reset_to_default_settings).pack(side=tk.LEFT, padx=(0, 10))
        
        # 初始化设置显示
        self.load_settings_display()
        
        # 绑定无限模式复选框事件
        self.unlimited_var.trace("w", lambda *args: self.toggle_entries())
    
    def load_settings_display(self):
        """加载设置显示"""
        # 获取当前设置
        settings = self.db.get_settings()
        
        # 更新界面显示
        self.unlimited_var.set(settings['unlimited_mode'])
        max_size_mb = settings['max_copy_size'] / (1024 * 1024)
        self.size_var.set(str(max_size_mb))
        self.count_var.set(str(settings['max_copy_count']))
        self.retention_var.set("permanent" if settings['retention_days'] == 0 else "custom")
        self.days_var.set(str(settings['retention_days']) if settings['retention_days'] > 0 else "30")
        self.days_entry.config(state="normal" if settings['retention_days'] > 0 else "disabled")
        self.autostart_var.set(settings['auto_start'])
        
        # 检查是否有悬浮图标设置，如果没有则添加默认值
        if 'float_icon' in settings:
            self.float_icon_var.set(settings['float_icon'])
        else:
            self.float_icon_var.set(True)
        
        # 应用初始状态
        self.toggle_entries()
    
    def toggle_entries(self):
        """切换输入框状态"""
        state = "disabled" if self.unlimited_var.get() else "normal"
        # 获取Entry控件并设置状态
        for child in self.settings_frame.winfo_children():
            if isinstance(child, tk.Canvas):
                canvas = child
                canvas_children = canvas.winfo_children()
                if canvas_children:
                    frame = canvas_children[0]
                    for widget in frame.winfo_children():
                        if isinstance(widget, ttk.Entry):
                            widget.config(state=state)
    
    def save_settings(self):
        """保存设置"""
        try:
            # 获取用户输入
            unlimited_mode = self.unlimited_var.get()
            
            # 如果不是无限模式，验证数值
            if not unlimited_mode:
                max_size_mb = float(self.size_var.get())
                max_count = int(self.count_var.get())
                
                # 转换MB到字节
                max_size_bytes = int(max_size_mb * 1024 * 1024)
                
                # 更新设置
                self.db.update_settings(
                    max_copy_size=max_size_bytes,
                    max_copy_count=max_count,
                    unlimited_mode=unlimited_mode
                )
            else:
                # 无限模式
                self.db.update_settings(unlimited_mode=unlimited_mode)
            
            # 保存天数设置
            if self.retention_var.get() == "permanent":
                retention_days = 0
            else:
                retention_days = int(self.days_var.get())
            
            # 保存开机自启设置
            auto_start = self.autostart_var.get()
            
            # 保存悬浮图标设置
            float_icon = self.float_icon_var.get()
            
            # 更新所有设置
            self.db.update_settings(
                retention_days=retention_days,
                auto_start=auto_start,
                float_icon=float_icon
            )
            
            # 如果设置了自定义天数，检查并删除过期记录
            if retention_days > 0:
                self.db.delete_expired_records()
            
            # 设置开机自启
            self.set_auto_start(auto_start)
            
            # 处理悬浮图标
            self.handle_float_icon(float_icon)
            
            messagebox.showinfo("提示", "设置已保存")
        except ValueError:
            messagebox.showerror("错误", "请输入有效的数字")
    
    def reset_to_default_settings(self):
        """恢复默认设置"""
        # 重置为默认设置
        self.db.update_settings(
            max_copy_size=314572800,  # 300MB
            max_copy_count=100,
            unlimited_mode=False,
            retention_days=0,  # 永久保存
            auto_start=False
        )
        
        # 更新界面显示
        self.unlimited_var.set(False)
        self.size_var.set("300")
        self.count_var.set("100")
        self.retention_var.set("permanent")
        self.days_entry.config(state="disabled")
        self.autostart_var.set(False)
        
        messagebox.showinfo("提示", "已恢复默认设置")
    
    def update_statistics_display(self):
        """更新统计信息显示"""
        # 获取统计信息
        text_count, file_count, total_size = self.db.get_statistics()
        total_count = text_count + file_count
        formatted_size = self.format_file_size(total_size)
        
        # 构造统计信息文本
        stats_info = f"""
统计信息
{'='*50}

文本记录: {text_count} 条
文件记录: {file_count} 条
总计: {total_count} 条
累计大小: {formatted_size}

数据库文件: {self.db.db_path}
"""
        
        # 更新显示
        self.stats_text.config(state=tk.NORMAL)
        self.stats_text.delete(1.0, tk.END)
        self.stats_text.insert(tk.END, stats_info)
        self.stats_text.config(state=tk.DISABLED)
    
    def load_records(self):
        """加载所有记录"""
        self.load_all_records()
    
    def load_all_records(self):
        """加载所有记录"""
        # 清空现有记录
        for item in self.records_tree.get_children():
            self.records_tree.delete(item)
        
        # 确定数据库排序字段
        db_sort_field = self.get_db_sort_field(self.sort_column)
        
        # 加载所有记录（包括文本和文件）
        text_records = self.db.get_text_records(sort_by=db_sort_field, reverse=self.sort_reverse)
        file_records = self.db.get_file_records(sort_by=db_sort_field, reverse=self.sort_reverse)
        
        # 创建一个包含所有记录的列表
        all_records = []
        
        # 添加文本记录
        for record in text_records:
            # 记录格式：(id, content, timestamp, char_count, md5_hash, number)
            record_id, content, timestamp, char_count, md5_hash, number = record
            content_preview = self.sanitize_text_for_display(content, 50)
            all_records.append((content_preview, "文本", "-", timestamp, str(number), "text", record_id))
                    
        # 添加文件记录
        for record in file_records:
            # 记录格式：(id, original_path, saved_path, filename, file_size, file_type, md5_hash, timestamp, number)
            record_id, original_path, saved_path, filename, file_size, file_type, md5_hash, timestamp, number = record
            size_str = self.format_file_size(file_size)
            # 获取文件后缀作为类型显示
            file_extension = file_type if file_type else "未知"
            all_records.append((filename, file_extension, size_str, timestamp, str(number), "file", record_id))
        
        # 显示记录
        for record in all_records:
            if record[5] == 'text':  # 文本记录
                self.records_tree.insert("", tk.END, values=(record[0], record[1], record[2], record[3], record[4]), tags=("text", record[6]))
            else:  # 文件记录
                self.records_tree.insert("", tk.END, values=(record[0], record[1], record[2], record[3], record[4]), tags=("file", record[6]))
        
        # 更新统计信息显示
        self.update_statistics_display()
    
    def get_db_sort_field(self, column_name):
        """将界面列名转换为数据库字段名"""
        column_mapping = {
            "名称或内容": "content",
            "类型": "file_type",
            "大小": "file_size",
            "时间": "timestamp",
            "次数": "number"
        }
        return column_mapping.get(column_name, "timestamp")
    
    def load_next_page(self):
        """加载下一页记录（已废弃）"
        pass
    
    def on_mouse_wheel(self, event):
        """处理鼠标滚轮事件"""
        # 传递事件给默认处理程序
        return
    
    def on_tree_select(self, event):
        """处理树形视图选择事件"""
        # 不再需要处理分页逻辑
        pass
    
    def search_records(self):
        """搜索记录"""
        keyword = self.search_entry.get()
        # 默认搜索全部类型
        record_type = "all"
        
        # 清空现有记录
        for item in self.records_tree.get_children():
            self.records_tree.delete(item)
        
        # 搜索记录
        records = self.db.search_records(keyword=keyword, record_type=record_type)
        
        # 对搜索结果进行排序
        self.sort_search_results(records)
    
    def sort_search_results(self, records):
        """对搜索结果进行排序并在记录标签页中显示"""
        # 创建一个包含所有记录的列表
        all_records = []
        
        for record in records:
            if record[0] == 'text':
                # 文本记录
                content_preview = self.sanitize_text_for_display(record[2], 50)
                # 获取该记录的number值
                conn = sqlite3.connect(self.db.db_path)
                cursor = conn.cursor()
                cursor.execute('SELECT number FROM text_records WHERE id = ?', (record[1],))
                result = cursor.fetchone()
                number = str(result[0]) if result else "1"
                conn.close()
                all_records.append((content_preview, "文本", "-", record[3], number, "text", record[1]))
            else:
                # 文件记录（需要从数据库获取完整信息）
                conn = sqlite3.connect(self.db.db_path)
                cursor = conn.cursor()
                cursor.execute('SELECT file_size, number FROM file_records WHERE id = ?', (record[1],))
                file_info = cursor.fetchone()
                conn.close()
                
                if file_info:
                    file_size, number = file_info
                    size_str = self.format_file_size(file_size)
                    all_records.append((record[2], "文件", size_str, record[3], str(number), "file", record[1]))
                else:
                    all_records.append((record[2], "文件", "-", record[3], "1", "file", record[1]))
        
        # 根据当前排序列进行排序
        try:
            # 确定排序索引
            sort_index = 0  # 默认按第一列（名称或内容）排序
            if self.sort_column == "类型":
                sort_index = 1
            elif self.sort_column == "大小":
                sort_index = 2
            elif self.sort_column == "时间":
                sort_index = 3
            elif self.sort_column == "次数":
                sort_index = 4
            
            # 特殊处理数值型字段
            if self.sort_column in ["大小", "次数"]:
                # 对于大小和次数字段，尝试数值排序
                def get_numeric_value(record):
                    try:
                        if self.sort_column == "大小":
                            # 从第三列获取大小值，转换为数值
                            size_str = record[2]
                            if size_str == "-":
                                return 0
                            # 简单解析大小字符串
                            if "GB" in size_str:
                                return float(size_str.replace("GB", "")) * 1024 * 1024 * 1024
                            elif "MB" in size_str:
                                return float(size_str.replace("MB", "")) * 1024 * 1024
                            elif "KB" in size_str:
                                return float(size_str.replace("KB", "")) * 1024
                            else:
                                return float(size_str.replace("B", ""))
                        elif self.sort_column == "次数":
                            # 从第五列获取次数值
                            return int(record[4])
                    except (ValueError, TypeError):
                        return 0
                all_records.sort(key=get_numeric_value, reverse=self.sort_reverse)
            else:
                # 文本类型字段使用文本排序
                all_records.sort(key=lambda x: x[sort_index] if x[sort_index] is not None else "", reverse=self.sort_reverse)
        except (ValueError, TypeError):
            # 如果排序失败，回退到按时间排序
            all_records.sort(key=lambda x: x[3] if x[3] is not None else "", reverse=True)
        
        # 在记录标签页中显示排序后的结果
        for record in all_records:
            self.records_tree.insert("", tk.END, values=(record[0], record[1], record[2], record[3], record[4]), tags=(record[5], record[6]))
    
    def show_full_record(self, event):
        """显示记录的完整内容"""
        selection = self.records_tree.selection()
        if selection:
            item = selection[0]
            tags = self.records_tree.item(item, "tags")
            
            if len(tags) >= 2:
                record_type = tags[0]  # 记录类型（text或file）
                record_id = tags[1]    # 记录ID
                
                if record_type == "text":
                    # 从数据库获取完整文本内容
                    conn = sqlite3.connect(self.db.db_path)
                    cursor = conn.cursor()
                    cursor.execute('SELECT id, content FROM text_records WHERE id = ?', (record_id,))
                    result = cursor.fetchone()
                    conn.close()
                    
                    if result:
                        record_id, full_text = result
                        # 创建新窗口显示完整内容
                        text_window = tk.Toplevel(self.root)
                        text_window.title(f"文本记录详情 - ID: {record_id}")
                        text_window.geometry("600x400")
                        
                        # 居中显示
                        self.center_child_window(text_window, 600, 400)
                        
                        text_area = scrolledtext.ScrolledText(text_window, wrap=tk.WORD)
                        text_area.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
                        text_area.insert(tk.END, full_text)
                        text_area.config(state=tk.DISABLED)
                else:
                    # 对于文件类型，打开文件位置
                    conn = sqlite3.connect(self.db.db_path)
                    cursor = conn.cursor()
                    cursor.execute('SELECT saved_path FROM file_records WHERE id = ?', (record_id,))
                    result = cursor.fetchone()
                    conn.close()
                    
                    if result and os.path.exists(result[0]):
                        import subprocess
                        subprocess.run(['explorer', '/select,', result[0]])
                    else:
                        messagebox.showwarning("警告", "文件不存在")
    
    def copy_selected_record(self):
        """复制选中的记录内容到剪贴板"""
        # 标记用户操作正在进行
        self.user_action_in_progress = True
        try:
            selection = self.records_tree.selection()
            if selection:
                item = selection[0]
                tags = self.records_tree.item(item, "tags")
                
                if len(tags) >= 2:
                    record_type = tags[0]  # 记录类型（text或file）
                    record_id = tags[1]    # 记录ID
                    
                    if record_type == "text":
                        # 从数据库获取完整文本内容
                        conn = sqlite3.connect(self.db.db_path)
                        cursor = conn.cursor()
                        cursor.execute('SELECT content FROM text_records WHERE id = ?', (record_id,))
                        result = cursor.fetchone()
                        conn.close()
                        
                        if result:
                            full_text = result[0]
                            self.root.clipboard_clear()
                            self.root.clipboard_append(full_text)
                            messagebox.showinfo("提示", "文本已复制到剪贴板")
                        else:
                            messagebox.showwarning("警告", "无法获取文本内容")
                    else:
                        # 复制文件名
                        values = self.records_tree.item(item, "values")
                        if len(values) > 0:
                            filename = values[0]  # 名称或内容列（文件名）
                            self.root.clipboard_clear()
                            self.root.clipboard_append(filename)
                            messagebox.showinfo("提示", "文件名已复制到剪贴板")
            else:
                messagebox.showwarning("警告", "请先选择一条记录")
        finally:
            # 标记用户操作完成
            self.user_action_in_progress = False
    
    def delete_selected_record(self):
        """删除选中的记录"""
        # 标记用户操作正在进行
        self.user_action_in_progress = True
        try:
            selection = self.records_tree.selection()
            if selection:
                if messagebox.askyesno("确认", "确定要删除这条记录吗？"):
                    item = selection[0]
                    tags = self.records_tree.item(item, "tags")
                    
                    if len(tags) >= 2:
                        record_type = tags[0]  # 记录类型（text或file）
                        record_id = tags[1]    # 记录ID
                        
                        conn = sqlite3.connect(self.db.db_path)
                        cursor = conn.cursor()
                        
                        if record_type == "text":
                            # 删除文本记录
                            self.db.delete_text_record(record_id)
                        else:
                            # 删除文件记录
                            cursor.execute('SELECT saved_path FROM file_records WHERE id = ?', (record_id,))
                            result = cursor.fetchone()
                            if result:
                                saved_path = result[0]
                                self.db.delete_file_record(record_id)
                                # 尝试删除文件（如果不再被引用）
                                self.check_and_delete_file(saved_path)
                        
                        conn.close()
                        self.load_records()
                        messagebox.showinfo("提示", "记录已删除")
            else:
                messagebox.showwarning("警告", "请先选择一条记录")
        finally:
            # 标记用户操作完成
            self.user_action_in_progress = False

    def format_file_size(self, size_bytes):
        """格式化文件大小"""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"
    
    def reset_all_records(self):
        """重置所有记录"""
        # 标记用户操作正在进行
        self.user_action_in_progress = True
        try:
            # 弹出确认对话框
            confirm_window = tk.Toplevel(self.root)
            confirm_window.title("确认重置")
            confirm_window.geometry("400x200")
            
            # 居中显示
            self.center_child_window(confirm_window, 400, 200)
            
            # 居中显示
            confirm_window.transient(self.root)
            confirm_window.grab_set()
            
            ttk.Label(confirm_window, text="此操作将删除所有记录和本地缓存文件！", foreground="red", font=("Arial", 10, "bold")).pack(pady=(20, 10))
            ttk.Label(confirm_window, text="请输入以下文本以确认操作:").pack()
            
            confirmation_text = "确认重置所有记录"
            ttk.Label(confirm_window, text=confirmation_text, font=("Arial", 10, "bold")).pack(pady=(5, 10))
            
            entry = ttk.Entry(confirm_window, width=30)
            entry.pack(pady=(0, 10))
            entry.focus()
            
            button_frame = ttk.Frame(confirm_window)
            button_frame.pack()
            
            def confirm_reset():
                if entry.get() == confirmation_text:
                    # 删除所有数据库记录
                    self.db.clear_all_records()
                    
                    # 删除所有缓存文件
                    clipboard_dir = "clipboard_files"
                    if os.path.exists(clipboard_dir):
                        try:
                            shutil.rmtree(clipboard_dir)
                            os.makedirs(clipboard_dir, exist_ok=True)
                        except Exception as e:
                            messagebox.showerror("错误", f"删除缓存文件时出错: {e}")
                    
                    # 重新加载记录
                    self.load_records()
                    confirm_window.destroy()
                    messagebox.showinfo("提示", "所有记录已重置")
                else:
                    messagebox.showwarning("警告", "输入文本不匹配，请重新输入")
            
            def cancel_reset():
                confirm_window.destroy()
            
            ttk.Button(button_frame, text="确认", command=confirm_reset).pack(side=tk.LEFT, padx=(0, 10))
            ttk.Button(button_frame, text="取消", command=cancel_reset).pack(side=tk.LEFT)
        finally:
            # 标记用户操作完成
            self.user_action_in_progress = False
    
    def open_settings(self):
        """打开设置窗口"""
        # 标记用户操作正在进行
        self.user_action_in_progress = True
        try:
            # 获取当前设置
            settings = self.db.get_settings()
            
            # 创建设置窗口
            settings_window = tk.Toplevel(self.root)
            settings_window.title("设置")
            settings_window.geometry("450x400")
            
            # 居中显示
            self.center_child_window(settings_window, 450, 400)
            
            # 居中显示
            settings_window.transient(self.root)
            settings_window.grab_set()
            
            # 创建设置界面
            ttk.Label(settings_window, text="复制限制设置", font=("Arial", 12, "bold")).pack(pady=(20, 10))
            
            # 无限模式复选框
            unlimited_var = tk.BooleanVar(value=settings['unlimited_mode'])
            unlimited_check = ttk.Checkbutton(settings_window, text="无限模式（无限制）", variable=unlimited_var)
            unlimited_check.pack(pady=(0, 10))
            
            # 最大大小设置
            size_frame = ttk.LabelFrame(settings_window, text="最大复制大小")
            size_frame.pack(fill=tk.X, padx=20, pady=(0, 10))
            
            # 转换字节到MB
            max_size_mb = settings['max_copy_size'] / (1024 * 1024)
            size_var = tk.StringVar(value=str(max_size_mb))
            size_entry = ttk.Entry(size_frame, textvariable=size_var, width=10)
            size_entry.pack(side=tk.LEFT, padx=(10, 5), pady=10)
            ttk.Label(size_frame, text="MB").pack(side=tk.LEFT)
            
            # 最大数量设置
            count_frame = ttk.LabelFrame(settings_window, text="最大复制文件数量")
            count_frame.pack(fill=tk.X, padx=20, pady=(0, 10))
            
            count_var = tk.StringVar(value=str(settings['max_copy_count']))
            count_entry = ttk.Entry(count_frame, textvariable=count_var, width=10)
            count_entry.pack(side=tk.LEFT, padx=(10, 5), pady=10)
            ttk.Label(count_frame, text="个").pack(side=tk.LEFT)
            
            # 保存天数设置
            ttk.Label(settings_window, text="记录保存设置", font=("Arial", 12, "bold")).pack(pady=(10, 5))
            
            retention_frame = ttk.LabelFrame(settings_window, text="保存天数")
            retention_frame.pack(fill=tk.X, padx=20, pady=(0, 10))
            
            # 永久保存选项
            retention_var = tk.StringVar(value="permanent" if settings['retention_days'] == 0 else "custom")
            permanent_radio = ttk.Radiobutton(retention_frame, text="永久保存", variable=retention_var, value="permanent")
            permanent_radio.pack(anchor=tk.W, padx=10, pady=5)
            
            # 自定义天数选项
            custom_frame = ttk.Frame(retention_frame)
            custom_frame.pack(fill=tk.X, padx=10, pady=5)
            
            custom_radio = ttk.Radiobutton(custom_frame, text="自定义天数:", variable=retention_var, value="custom")
            custom_radio.pack(side=tk.LEFT)
            
            days_var = tk.StringVar(value=str(settings['retention_days']) if settings['retention_days'] > 0 else "30")
            days_entry = ttk.Entry(custom_frame, textvariable=days_var, width=10, state="normal" if settings['retention_days'] > 0 else "disabled")
            days_entry.pack(side=tk.LEFT, padx=(5, 0))
            ttk.Label(custom_frame, text="天").pack(side=tk.LEFT, padx=(5, 0))
            
            # 绑定单选按钮事件
            def on_retention_change(*args):
                if retention_var.get() == "custom":
                    days_entry.config(state="normal")
                else:
                    days_entry.config(state="disabled")
            
            retention_var.trace("w", on_retention_change)
            
            # 开机自启设置
            ttk.Label(settings_window, text="系统设置", font=("Arial", 12, "bold")).pack(pady=(10, 5))
            
            autostart_frame = ttk.LabelFrame(settings_window, text="开机自启")
            autostart_frame.pack(fill=tk.X, padx=20, pady=(0, 10))
            
            autostart_var = tk.BooleanVar(value=settings['auto_start'])
            autostart_check = ttk.Checkbutton(autostart_frame, text="允许程序开机自启", variable=autostart_var)
            autostart_check.pack(anchor=tk.W, padx=10, pady=10)
            
            # 按钮框架
            button_frame = ttk.Frame(settings_window)
            button_frame.pack(pady=(20, 0))
            
            def save_settings():
                try:
                    # 获取用户输入
                    unlimited_mode = unlimited_var.get()
                    
                    # 如果不是无限模式，验证数值
                    if not unlimited_mode:
                        max_size_mb = float(size_var.get())
                        max_count = int(count_var.get())
                        
                        # 转换MB到字节
                        max_size_bytes = int(max_size_mb * 1024 * 1024)
                        
                        # 更新设置
                        self.db.update_settings(
                            max_copy_size=max_size_bytes,
                            max_copy_count=max_count,
                            unlimited_mode=unlimited_mode
                        )
                    else:
                        # 无限模式
                        self.db.update_settings(unlimited_mode=unlimited_mode)
                    
                    # 保存天数设置
                    if retention_var.get() == "permanent":
                        retention_days = 0
                    else:
                        retention_days = int(days_var.get())
                    
                    # 保存开机自启设置
                    auto_start = autostart_var.get()
                    
                    # 更新所有设置
                    self.db.update_settings(
                        retention_days=retention_days,
                        auto_start=auto_start
                    )
                    
                    # 如果设置了自定义天数，检查并删除过期记录
                    if retention_days > 0:
                        self.db.delete_expired_records()
                    
                    # 设置开机自启
                    self.set_auto_start(auto_start)
                    
                    settings_window.destroy()
                    messagebox.showinfo("提示", "设置已保存")
                except ValueError:
                    messagebox.showerror("错误", "请输入有效的数字")
            
            def reset_to_default():
                # 重置为默认设置
                self.db.update_settings(
                    max_copy_size=314572800,  # 300MB
                    max_copy_count=100,
                    unlimited_mode=False,
                    retention_days=0,  # 永久保存
                    auto_start=False
                )
                
                # 更新界面显示
                unlimited_var.set(False)
                size_var.set("300")
                count_var.set("100")
                retention_var.set("permanent")
                days_entry.config(state="disabled")
                autostart_var.set(False)
                
                messagebox.showinfo("提示", "已恢复默认设置")
            
            ttk.Button(button_frame, text="保存", command=save_settings).pack(side=tk.LEFT, padx=(0, 10))
            ttk.Button(button_frame, text="恢复默认", command=reset_to_default).pack(side=tk.LEFT, padx=(0, 10))
            ttk.Button(button_frame, text="取消", command=settings_window.destroy).pack(side=tk.LEFT)
            
            # 绑定无限模式复选框事件
            def toggle_entries():
                state = "disabled" if unlimited_var.get() else "normal"
                size_entry.config(state=state)
                count_entry.config(state=state)
            
            unlimited_var.trace("w", lambda *args: toggle_entries())
            toggle_entries()  # 初始化状态
            
        finally:
            # 标记用户操作完成
            self.user_action_in_progress = False

    def set_auto_start(self, enable):
        """设置开机自启"""
        try:
            import winreg
            
            # 获取当前脚本路径
            if getattr(sys, 'frozen', False):
                # 如果是打包后的exe
                exe_path = sys.executable
            else:
                # 如果是python脚本
                exe_path = os.path.abspath(__file__)
            
            # 注册表路径
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            
            if enable:
                # 设置开机自启
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
                winreg.SetValueEx(key, "ClipboardManager", 0, winreg.REG_SZ, exe_path)
                winreg.CloseKey(key)
            else:
                # 取消开机自启
                try:
                    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
                    winreg.DeleteValue(key, "ClipboardManager")
                    winreg.CloseKey(key)
                except FileNotFoundError:
                    # 如果值不存在，忽略错误
                    pass
        except Exception as e:
            print(f"设置开机自启时出错: {e}")
    
    def handle_float_icon(self, enable):
        """处理悬浮图标"""
        if enable:
            # 启用悬浮图标
            self.create_float_icon()
        else:
            # 禁用悬浮图标
            self.destroy_float_icon()
    
    def create_float_icon(self):
        """创建悬浮图标"""
        # 如果悬浮图标已经存在，先销毁
        self.destroy_float_icon()
        
        # 创建悬浮窗口
        self.float_window = tk.Toplevel(self.root)
        self.float_window.title("悬浮图标")
        self.float_window.geometry("50x50")  # 改为80x80大小，符合需求说明
        self.float_window.overrideredirect(True)  # 去除窗口边框
        self.float_window.attributes("-topmost", True)  # 置顶显示
        self.float_window.attributes("-alpha", 0.15)  # 设置透明度为30%，符合需求说明
        
        # 获取屏幕尺寸
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # 设置默认位置为右下角（右边像素60，底部120）
        x = screen_width - 50 - 60  # 距离右边60像素
        y = screen_height - 50 - 120  # 距离底部120像素
        self.float_window.geometry(f"50x50+{x}+{y}")
        
        try:
            # 尝试加载2.jpg图片
            image_path = resource_path("2.jpg")
            image = Image.open(image_path)
            image = image.resize((50, 50), Image.LANCZOS)  # 调整图片大小
            
            # 移除了圆形遮罩，使用原始图片
            
            photo = ImageTk.PhotoImage(image)
            
            # 创建标签显示图片
            label = tk.Label(self.float_window, image=photo, bg="white")
            label.image = photo  # 保持引用防止被垃圾回收
            label.pack(fill=tk.BOTH, expand=True)
        except Exception as e:
            # 如果图片加载失败，使用默认的蓝色背景和文本
            print(f"加载2.jpg图片失败: {e}")
            self.float_window.configure(bg="#496D89")
            
            # 在窗口中央添加文本
            label = tk.Label(self.float_window, text="C", font=("Arial", 24), bg="#496D89", fg="white")
            label.pack(expand=True)
        
        # 绑定鼠标事件以支持拖动
        self.float_window.bind("<Button-1>", self.start_move_float_icon)
        self.float_window.bind("<B1-Motion>", self.move_float_icon)
        
        # 绑定鼠标进入和点击事件
        # 绑定鼠标进入和点击事件
        self.float_window.bind("<Enter>", self.show_float_panel_on_hover)
        self.float_window.bind("<Leave>", self.check_and_hide_float_panel)
        self.float_window.bind("<ButtonRelease-1>", self.handle_float_icon_click)
        self.float_window.bind("<Double-Button-1>", self.show_main_window_from_float_icon)
        
        # 记录鼠标位置
        self.float_icon_x = 0
        self.float_icon_y = 0
        self.float_panel = None  # 悬浮面板引用
        self.float_click_count = 0  # 点击计数器
    
    def handle_float_icon_click(self, event):
        """处理悬浮图标点击事件"""
        # 检查是否是点击而不是拖动
        if abs(event.x - self.float_icon_x) < 5 and abs(event.y - self.float_icon_y) < 5:
            # 直接显示悬浮面板，不需要延迟
            self.show_float_panel(center_on_icon=True)
    
    def show_float_panel_on_hover(self, event):
        """鼠标移入时显示悬浮面板"""
        self.show_float_panel(center_on_icon=True)
    
    def show_float_panel_delayed(self):
        """延迟显示悬浮面板，用于区分单击和双击"""
        self.show_float_panel(center_on_icon=True)
    
    def show_main_window_from_float_icon(self, event):
        """双击悬浮图标显示主窗口"""
        self.show_window()
    
    def show_float_panel(self, event=None, center_on_icon=False):
        """显示最近记录悬浮面板"""
        # 销毁已存在的面板
        if self.float_panel:
            self.float_panel.destroy()
        
        # 获取最近记录（增加到50条）
        text_records = self.db.get_text_records(50)  # 最多50条记录
        file_records = self.db.get_file_records(50)
        
        # 合并记录并按时间排序
        all_records = []
        for record in text_records:
            all_records.append(("text", record[1], record[2]))  # 类型, 内容, 时间
        
        for record in file_records:
            all_records.append(("file", record[3], record[7]))  # 类型, 文件名, 时间
        
        # 按时间排序（最新的在前面）
        all_records.sort(key=lambda x: x[2], reverse=True)
        
        # 只取前50条
        all_records = all_records[:50]
        
        # 创建悬浮面板 (200x400像素)
        self.float_panel = tk.Toplevel(self.float_window)
        self.float_panel.title("最近记录")
        self.float_panel.geometry("200x400")
        self.float_panel.overrideredirect(True)  # 去除窗口边框
        self.float_panel.attributes("-topmost", True)  # 置顶显示
        
        # 设置面板样式
        self.float_panel.configure(bg="white")
        
        # 确保面板在屏幕范围内，并根据需要居中显示
        if center_on_icon:
            self.position_float_panel_above_icon(400)
        else:
            self.position_float_panel_within_screen(400)
        
        # 创建带圆角的面板背景
        self.create_rounded_panel_bg(self.float_panel, 200, 400, 8, "#ffffff")
        
        # 创建主框架
        main_frame = tk.Frame(self.float_panel, bg="white", relief="solid", bd=0)  # 移除边框
        main_frame.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)  # 添加一点padding以显示圆角效果
        
        # 创建标题栏
        header_frame = tk.Frame(main_frame, bg="#f8f9fa", height=36)
        header_frame.pack(fill=tk.X, side=tk.TOP)
        header_frame.pack_propagate(False)  # 固定高度
        
        # 标题文本
        header_label = tk.Label(header_frame, text="最近记录", bg="#f8f9fa", fg="#2c3e50", 
                              font=("Arial", 10, "bold"))
        header_label.pack(expand=True)
        
        # 创建内容区域
        content_frame = tk.Frame(main_frame, bg="white")
        content_frame.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)
        
        # 创建Text控件和滚动条来显示记录
        self.records_text = tk.Text(content_frame, bg="white", fg="#000000", font=("Arial", 9), 
                                  wrap=tk.WORD, state=tk.DISABLED, relief=tk.FLAT, spacing1=2, spacing3=2)
        scrollbar = tk.Scrollbar(content_frame, orient="vertical", command=self.records_text.yview)
        self.records_text.configure(yscrollcommand=scrollbar.set)
        
        # 打包Text控件和滚动条
        self.records_text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # 添加记录到Text控件
        self.records_text.config(state=tk.NORMAL)  # 允许编辑以插入内容
        self.records_text.delete(1.0, tk.END)  # 清空现有内容
        
        for i, (record_type, content, timestamp) in enumerate(all_records):
            if record_type == "text":
                # 文本记录
                display_text = content
            else:
                # 文件记录
                display_text = content
            
            # 处理文本，确保只显示一行并去除换行符
            display_text = display_text.replace('\n', ' ').replace('\r', ' ')
            # 如果文本过长，截取并添加省略号
            if len(display_text) > 50:
                display_text = display_text[:50] + "..."
            
            # 插入记录到Text控件，减小记录之间的间距
            self.records_text.insert(tk.END, display_text)
            
            # 移除记录之间的额外换行符，使记录更紧密
            # 只在记录之间添加最小的分隔
            if i < len(all_records) - 1:  # 不为最后一个元素添加分隔
                self.records_text.insert(tk.END, "\n")
        
        self.records_text.config(state=tk.DISABLED)  # 禁止编辑
        
        # 如果没有记录，显示提示信息
        if not all_records:
            self.records_text.config(state=tk.NORMAL)
            self.records_text.delete(1.0, tk.END)
            self.records_text.insert(tk.END, "暂无剪贴板记录\n请复制一些文本或文件\n记录将显示在这里")
            self.records_text.config(state=tk.DISABLED)
        
        # 创建底部"查看更多记录"
        footer_frame = tk.Frame(main_frame, bg="#f8f9fa", height=34)
        footer_frame.pack(fill=tk.X, side=tk.BOTTOM)
        footer_frame.pack_propagate(False)
        
        footer_label = tk.Label(footer_frame, text="查看更多记录", bg="#f8f9fa", fg="#5c6bc0",
                               font=("Arial", 9), cursor="hand2")
        footer_label.pack(expand=True)
        
        # 绑定底部点击事件，显示主窗口
        footer_frame.bind("<Button-1>", self.show_window_and_hide_panel)
        footer_label.bind("<Button-1>", self.show_window_and_hide_panel)
        
        # 绑定焦点事件，鼠标移出时隐藏面板
        self.float_panel.bind("<FocusOut>", self.hide_float_panel)
        self.float_panel.bind("<Leave>", self.hide_float_panel_on_leave)
        
        # 设置面板获取焦点
        self.float_panel.focus_set()
    
    def create_rounded_panel_bg(self, parent, width, height, radius, color):
        """创建带圆角的面板背景"""
        try:
            # 创建一个图像作为背景
            image = Image.new('RGBA', (width, height), (0, 0, 0, 0))
            draw = ImageDraw.Draw(image)
            
            # 绘制圆角矩形
            draw.rounded_rectangle([(0, 0), (width, height)], radius=radius, fill=color)
            
            # 转换为PhotoImage
            photo = ImageTk.PhotoImage(image)
            
            # 创建标签显示背景
            bg_label = tk.Label(parent, image=photo, bg=parent.cget('bg'))
            bg_label.image = photo  # 保持引用防止被垃圾回收
            bg_label.place(x=0, y=0, relwidth=1, relheight=1)
        except Exception as e:
            print(f"创建圆角背景失败: {e}")
            # 如果创建圆角背景失败，使用普通背景色
            parent.configure(bg=color)
    
    def on_item_enter(self, frame, label):
        """鼠标进入记录项时的处理"""
        frame.configure(bg="#f0f7ff")
        label.configure(bg="#f0f7ff")
    
    def on_item_leave(self, frame, label):
        """鼠标离开记录项时的处理"""
        frame.configure(bg="white")
        label.configure(bg="white")
    
    def copy_record_from_float_panel(self, index):
        """从悬浮面板复制指定索引的记录"""
        # 获取完整内容
        text_records = self.db.get_text_records(15)
        file_records = self.db.get_file_records(15)
        
        # 合并记录并按时间排序
        all_records = []
        for record in text_records:
            all_records.append(("text", record[1], record[2]))  # 类型, 内容, 时间
        
        for record in file_records:
            all_records.append(("file", record[3], record[7]))  # 类型, 文件名, 时间
        
        # 按时间排序（最新的在前面）
        all_records.sort(key=lambda x: x[2], reverse=True)
        
        # 只取前15条
        all_records = all_records[:15]
        
        if index < len(all_records):
            record_type, full_content, timestamp = all_records[index]
            if record_type == "text":
                # 复制完整文本内容
                self.root.clipboard_clear()
                self.root.clipboard_append(full_content)
            else:
                # 复制文件名
                self.root.clipboard_clear()
                self.root.clipboard_append(full_content)
    
    def copy_record_and_hide_panel(self, index):
        """复制记录并隐藏面板"""
        self.copy_record_from_float_panel(index)
        self.hide_float_panel()
    
    def show_window_and_hide_panel(self, event=None):
        """显示主窗口并隐藏面板"""
        self.show_window()
        self.hide_float_panel()
    
    def position_float_panel_within_screen(self, panel_height):
        """确保悬浮面板在屏幕范围内"""
        # 获取屏幕尺寸
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # 获取悬浮图标位置和尺寸
        icon_x = self.float_window.winfo_x()
        icon_y = self.float_window.winfo_y()
        icon_width = self.float_window.winfo_width()
        icon_height = self.float_window.winfo_height()
        
        # 面板尺寸
        panel_width = 200
        
        # 计算面板位置（默认在图标上方）
        panel_x = icon_x + (icon_width // 2) - (panel_width // 2)  # 水平居中对齐
        panel_y = icon_y - panel_height - 5  # 在图标上方5px处
        
        # 边界检查，确保面板在屏幕内
        # X轴边界检查
        if panel_x < 0:
            panel_x = 0
        elif panel_x + panel_width > screen_width:
            panel_x = screen_width - panel_width
        
        # Y轴边界检查
        if panel_y < 0:
            # 如果上方空间不足，显示在图标下方
            panel_y = icon_y + icon_height + 5
        
        # 确保面板底部也在屏幕内
        if panel_y + panel_height > screen_height:
            panel_y = screen_height - panel_height
        
        self.float_panel.geometry(f"{panel_width}x{panel_height}+{panel_x}+{panel_y}")
    
    def position_float_panel_centered(self, panel_height):
        """将悬浮面板居中显示在悬浮图标上，完全覆盖图标"""
        # 获取屏幕尺寸
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # 获取悬浮图标位置和尺寸
        icon_x = self.float_window.winfo_x()
        icon_y = self.float_window.winfo_y()
        icon_width = self.float_window.winfo_width()
        icon_height = self.float_window.winfo_height()
        
        # 面板尺寸
        panel_width = 200
        
        # 计算面板位置，使其完全覆盖图标并居中
        panel_x = icon_x + (icon_width // 2) - (panel_width // 2)
        panel_y = icon_y + (icon_height // 2) - (panel_height // 2)
        
        # 确保面板在屏幕范围内
        if panel_x < 0:
            panel_x = 0
        elif panel_x + panel_width > screen_width:
            panel_x = screen_width - panel_width
            
        if panel_y < 0:
            panel_y = 0
        elif panel_y + panel_height > screen_height:
            panel_y = screen_height - panel_height
        
        self.float_panel.geometry(f"{panel_width}x{panel_height}+{panel_x}+{panel_y}")
    
    def position_float_panel_above_icon(self, panel_height):
        """将悬浮面板显示在悬浮图标上方，确保面板在屏幕内且不覆盖图标"""
        # 获取屏幕尺寸
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # 获取悬浮图标位置和尺寸
        icon_x = self.float_window.winfo_x()
        icon_y = self.float_window.winfo_y()
        icon_width = self.float_window.winfo_width()
        icon_height = self.float_window.winfo_height()
        
        # 面板尺寸
        panel_width = 200
        
        # 计算面板位置（在图标上方）
        panel_x = icon_x + (icon_width // 2) - (panel_width // 2)  # 水平居中对齐
        panel_y = icon_y - panel_height - 5  # 在图标上方5px处
        
        # 边界检查，确保面板在屏幕内
        # X轴边界检查
        if panel_x < 0:
            panel_x = 0
        elif panel_x + panel_width > screen_width:
            panel_x = screen_width - panel_width
        
        # Y轴边界检查
        if panel_y < 0:
            # 如果上方空间不足，显示在图标下方
            panel_y = icon_y + icon_height + 5
        
        # 确保面板底部也在屏幕内
        if panel_y + panel_height > screen_height:
            panel_y = screen_height - panel_height
        
        self.float_panel.geometry(f"{panel_width}x{panel_height}+{panel_x}+{panel_y}")
    
    def hide_float_panel(self, event=None):
        """隐藏悬浮面板"""
        # 延迟隐藏，避免焦点切换时立即隐藏
        self.float_window.after(100, self._hide_float_panel)
    
    def hide_float_panel_on_leave(self, event=None):
        """鼠标移出面板时隐藏面板"""
        # 延迟隐藏，避免意外触发
        self.float_panel.after(200, self._check_and_hide_float_panel)
    
    def check_and_hide_float_panel(self, event=None):
        """检查鼠标位置并决定是否隐藏面板（处理悬浮图标和面板之间的移动）"""
        # 延迟检查，给鼠标时间移动到面板上
        self.float_window.after(100, self._check_mouse_position_and_hide)
    
    def _check_and_hide_float_panel(self):
        """检查鼠标位置并决定是否隐藏面板"""
        try:
            # 检查鼠标是否仍在面板内
            if self.float_panel and self.float_panel.winfo_exists():
                # 获取面板坐标和尺寸
                x1 = self.float_panel.winfo_rootx()
                y1 = self.float_panel.winfo_rooty()
                x2 = x1 + self.float_panel.winfo_width()
                y2 = y1 + self.float_panel.winfo_height()
                
                # 获取鼠标当前位置
                import pyautogui
                mouse_x, mouse_y = pyautogui.position()
                
                # 如果鼠标不在面板区域内，则隐藏面板
                if not (x1 <= mouse_x <= x2 and y1 <= mouse_y <= y2):
                    self.hide_float_panel()
        except Exception as e:
            # 出现异常时直接隐藏面板
            self.hide_float_panel()
    
    def _check_mouse_position_and_hide(self):
        """检查鼠标是否在悬浮图标或面板上，否则隐藏面板"""
        try:
            # 如果面板不存在，直接返回
            if not self.float_panel or not self.float_panel.winfo_exists():
                return
            
            # 获取鼠标当前位置
            import pyautogui
            mouse_x, mouse_y = pyautogui.position()
            
            # 检查鼠标是否在悬浮图标上
            icon_x1 = self.float_window.winfo_rootx()
            icon_y1 = self.float_window.winfo_rooty()
            icon_x2 = icon_x1 + self.float_window.winfo_width()
            icon_y2 = icon_y1 + self.float_window.winfo_height()
            
            # 检查鼠标是否在面板上
            panel_x1 = self.float_panel.winfo_rootx()
            panel_y1 = self.float_panel.winfo_rooty()
            panel_x2 = panel_x1 + self.float_panel.winfo_width()
            panel_y2 = panel_y1 + self.float_panel.winfo_height()
            
            # 如果鼠标不在悬浮图标和面板上，则隐藏面板
            if not ((icon_x1 <= mouse_x <= icon_x2 and icon_y1 <= mouse_y <= icon_y2) or 
                   (panel_x1 <= mouse_x <= panel_x2 and panel_y1 <= mouse_y <= panel_y2)):
                self.hide_float_panel()
        except Exception as e:
            # 出现异常时直接隐藏面板
            self.hide_float_panel()
    
    def _hide_float_panel(self):
        """实际隐藏悬浮面板"""
        if self.float_panel:
            self.float_panel.destroy()
            self.float_panel = None
    
    def destroy_float_icon(self):
        """销毁悬浮图标"""
        if hasattr(self, 'float_window') and self.float_window:
            self.float_window.destroy()
            self.float_window = None
    
    def start_move_float_icon(self, event):
        """开始移动悬浮图标"""
        self.float_icon_x = event.x
        self.float_icon_y = event.y
    
    def move_float_icon(self, event):
        """移动悬浮图标，增加边界检查确保图标在屏幕内"""
        # 计算新位置
        new_x = self.float_window.winfo_x() + event.x - self.float_icon_x
        new_y = self.float_window.winfo_y() + event.y - self.float_icon_y
        
        # 获取屏幕尺寸和图标尺寸
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        icon_width = self.float_window.winfo_width()
        icon_height = self.float_window.winfo_height()
        
        # 边界检查
        if new_x < 0:
            new_x = 0
        elif new_x + icon_width > screen_width:
            new_x = screen_width - icon_width
            
        if new_y < 0:
            new_y = 0
        elif new_y + icon_height > screen_height:
            new_y = screen_height - icon_height
        
        # 移动图标
        self.float_window.geometry(f"+{new_x}+{new_y}")
    
    def show_main_window_from_float(self, event):
        """从悬浮图标显示主窗口"""
        # 检查是否是点击而不是拖动
        if abs(event.x - self.float_icon_x) < 5 and abs(event.y - self.float_icon_y) < 5:
            self.show_window()
    
    def start_auto_update(self):
        """开始自动更新"""
        self.update_job = self.root.after(2000, self.update_records)  # 每2秒更新一次
    
    def stop_auto_update(self):
        """停止自动更新"""
        if self.update_job:
            self.root.after_cancel(self.update_job)
            self.update_job = None
    
    def update_records(self):
        """更新记录显示"""
        # 只在窗口显示时更新，避免不必要的资源消耗
        # 并且只有在没有用户操作进行时才更新
        # 当窗口有焦点时不更新，避免干扰用户操作
        if not self.is_hidden and not self.user_action_in_progress and not self.has_focus:
            self.load_records()
        
        # 继续定期更新
        self.update_job = self.root.after(2000, self.update_records)
    
    def hide_window(self):
        """隐藏窗口而不是关闭"""
        self.root.withdraw()  # 隐藏窗口
        self.is_hidden = True
        
    def show_window(self):
        """显示窗口"""
        self.root.deiconify()  # 显示窗口
        self.root.lift()  # 将窗口置于顶层
        self.is_hidden = False
        self.load_records()  # 显示时立即刷新
    
    def quit_application(self):
        """退出应用程序"""
        self.stop_auto_update()  # 停止自动更新
        if self.tray_icon:
            self.tray_icon.stop()
        self.root.quit()
        
    def toggle_window(self, event=None):
        """切换窗口显示状态"""
        if self.is_hidden:
            self.show_window()
        else:
            self.hide_window()

def main():
    """主函数"""
    root = tk.Tk()
    app = ClipboardGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()