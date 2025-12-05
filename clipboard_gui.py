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
        # PyInstaller创建临时文件夹,将路径存储在_MEIPASS中
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
        self.root.geometry("750x500")
        self.root.minsize(700, 400)  # 设置最小尺寸
        
        # 设置窗口图标
        try:
            icon_path = resource_path("mini.ico")
            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
        except Exception as e:
            print(f"设置窗口图标失败: {e}")

        # 居中显示窗口
        self.center_window(750, 500)
        # 创建UI
        self.setup_ui()
        # 在UI创建完成后加载第一页记录
        self.root.after(100, self.load_records)

        # 检查开机自启设置
        self.check_auto_start()

        # 检查并创建悬浮图标
        self.check_float_icon()

        # 更新悬浮图标透明度
        self.update_float_icon_opacity()

        # 开始定期更新
        self.start_auto_update()

        # 设置窗口关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self.hide_window)

        # 绑定焦点事件
        self.root.bind("<FocusIn>", self.on_focus_in)
        self.root.bind("<FocusOut>", self.on_focus_out)

        # 如果支持系统托盘,创建托盘图标
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
        """清理文本内容,移除换行符并截断过长内容"""
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
            # 使用mini.ico文件作为图标
            icon_path = resource_path("mini.ico")
            if os.path.exists(icon_path):
                image = Image.open(icon_path)
            else:
                # 如果图标文件不存在,创建一个简单的图标
                image = Image.new('RGB', (64, 64), color=(73, 109, 137))
                draw = ImageDraw.Draw(image)
                draw.ellipse((10, 10, 54, 54), fill=(255, 255, 255))
                draw.text((20, 20), "C", fill=(0, 0, 0))

            # 创建菜单
            menu = pystray.Menu(
                pystray.MenuItem("显示界面", self.show_window, default=True),
                pystray.MenuItem("退出", self.quit_application)
            )

            self.tray_icon = pystray.Icon(
                "clipboard_manager", image, "剪贴板管理器", menu)

            # 在单独线程中运行托盘图标
            tray_thread = threading.Thread(
                target=self.tray_icon.run, daemon=True)
            tray_thread.start()
        except Exception as e:
            print(f"创建系统托盘图标失败: {e}")

    def setup_ui(self):
        """设置UI界面"""
        # 设置样式
        self.setup_styles()
        
        # 创建主框架
        main_frame = ttk.Frame(self.root, style='Main.TFrame')
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # 创建笔记本控件(标签页)
        self.notebook = ttk.Notebook(main_frame, style='Main.TNotebook')
        self.notebook.grid(row=0, column=0, columnspan=2,
                           sticky=(tk.W, tk.E, tk.N, tk.S))

        # 记录标签页
        self.records_frame = ttk.Frame(self.notebook, style='Tab.TFrame')
        self.notebook.add(self.records_frame, text="记录(L)")
        self.setup_records_tab()

        # 设置标签页
        self.settings_frame = ttk.Frame(self.notebook, style='Tab.TFrame')
        self.notebook.add(self.settings_frame, text="设置(S)")
        self.setup_settings_tab()

        # 配置网格权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(0, weight=1)
        self.records_frame.columnconfigure(0, weight=1)
        self.records_frame.rowconfigure(0, weight=0)  # 搜索框行不扩展
        self.records_frame.rowconfigure(1, weight=1)  # 记录列表行扩展
        self.records_frame.rowconfigure(2, weight=0)  # 状态标签行不扩展
        self.settings_frame.columnconfigure(0, weight=1)
        self.settings_frame.rowconfigure(0, weight=1)

        # 绑定快捷键 Alt+C
        self.root.bind('<Alt-c>', self.toggle_window)
        self.root.bind('<Alt-C>', self.toggle_window)

        # 绑定快捷键 Ctrl+L 和 Ctrl+S 切换标签页
        self.root.bind('<Control-l>', self.switch_to_records_tab)
        self.root.bind('<Control-L>', self.switch_to_records_tab)
        self.root.bind('<Control-s>', self.switch_to_settings_tab)
        self.root.bind('<Control-S>', self.switch_to_settings_tab)

        # 设置焦点以确保快捷键生效
        self.root.focus_set()

    def setup_styles(self):
        """设置界面样式"""
        style = ttk.Style()
        
        # 配置整体主题
        style.theme_use('clam')
        
        # 主框架样式 - 使用浅灰色背景
        style.configure('Main.TFrame', background='#f0f0f0')
        
        # 笔记本控件样式
        style.configure('Main.TNotebook', background='#f0f0f0', tabmargins=[0, 0, 0, 0])
        style.configure('Main.TNotebook.Tab', 
                        padding=[15, 8], 
                        font=('Segoe UI', 10, 'bold'),
                        background='#e1e1e1',
                        foreground='#333333',
                        borderwidth=0)
        style.map('Main.TNotebook.Tab',
                  background=[('selected', '#ffffff')],
                  foreground=[('selected', '#000000')])
        
        # 标签页框架样式 - 使用白色背景
        style.configure('Tab.TFrame', background='#ffffff')
        
        # 搜索框样式
        style.configure('Search.TEntry', 
                        padding=8,
                        fieldbackground='#ffffff',
                        borderwidth=1,
                        relief='solid')
        
        # 树状视图样式
        style.configure('Records.Treeview',
                        background='#ffffff',
                        foreground='#333333',
                        rowheight=30,
                        fieldbackground='#ffffff',
                        borderwidth=1,
                        relief='solid')
        style.configure('Records.Treeview.Heading',
                        font=('Segoe UI', 9, 'bold'),
                        background='#f5f5f5',
                        foreground='#000000',
                        padding=10)
        style.map('Records.Treeview.Heading',
                  background=[('active', '#e0e0e0')])
        
        # 滚动条样式
        style.configure('Vertical.TScrollbar',
                        gripcount=0,
                        background='#c0c0c0',
                        troughcolor='#f0f0f0',
                        borderwidth=0,
                        relief='flat')
        style.map('Vertical.TScrollbar',
                  background=[('active', '#a0a0a0'), ('pressed', '#808080')])
        
        # 状态标签样式
        style.configure('Status.TLabel',
                        background='#ffffff',
                        foreground='#666666',
                        font=('Segoe UI', 9),
                        padding=[10, 10])
        
        # 设置页面标题样式
        style.configure('SettingsTitle.TLabel',
                        font=('Segoe UI', 16, 'bold'),
                        foreground='#2c3e50',
                        padding=[0, 15],
                        background='#ffffff')
        
        # 设置页面组标题样式
        style.configure('SettingsGroup.TLabel',
                        font=('Segoe UI', 12, 'bold'),
                        foreground='#3498db',
                        padding=[0, 15],
                        background='#ffffff')
        
        # 设置页面选项样式
        style.configure('SettingsOption.TCheckbutton',
                        background='#ffffff',
                        foreground='#333333',
                        font=('Segoe UI', 10),
                        padding=[5, 5])
        style.configure('SettingsOption.TRadiobutton',
                        background='#ffffff',
                        foreground='#333333',
                        font=('Segoe UI', 10),
                        padding=[5, 5])
        style.configure('SettingsOption.TLabel',
                        background='#ffffff',
                        foreground='#333333',
                        font=('Segoe UI', 10))
        
        # 设置页面输入框样式
        style.configure('Settings.TEntry',
                        padding=5,
                        fieldbackground='#ffffff',
                        relief='solid')

    def switch_to_records_tab(self, event=None):
        """切换到记录标签页"""
        self.notebook.select(self.records_frame)

    def switch_to_settings_tab(self, event=None):
        """切换到设置标签页"""
        self.notebook.select(self.settings_frame)

    def setup_records_tab(self):
        """设置记录标签页"""
        # 初始化排序参数
        self.sort_column = "时间"  # 默认排序列
        self.sort_reverse = True   # 默认倒序(最新的在前面)

        # 配置记录标签页的网格权重
        self.records_frame.columnconfigure(0, weight=1)
        self.records_frame.rowconfigure(0, weight=0)  # 搜索框行不扩展
        self.records_frame.rowconfigure(1, weight=1)  # 记录列表行扩展
        self.records_frame.rowconfigure(2, weight=0)  # 状态标签行不扩展

        # 创建搜索输入框，与记录列表宽度一致
        search_frame = ttk.Frame(self.records_frame, style='Tab.TFrame')
        search_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=10, padx=15)
        
        ttk.Label(search_frame, text="🔍", style='SettingsOption.TLabel').pack(side=tk.LEFT, padx=(0, 8))
        self.search_entry = ttk.Entry(search_frame, style='Search.TEntry', width=30)
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # 绑定实时搜索事件
        self.search_entry.bind('<KeyRelease>', self.on_search_input)

        # 创建树形视图,显示记录名称或内容、类型、大小、时间、次数
        tree_frame = ttk.Frame(self.records_frame, style='Tab.TFrame')
        tree_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=15, pady=(0, 10))
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)
        
        columns = ("名称或内容", "类型", "大小", "时间", "次数")
        self.records_tree = ttk.Treeview(
            tree_frame, columns=columns, show="headings", height=15, style='Records.Treeview')

        # 设置列标题和点击事件
        for col in columns:
            # 使用functools.partial解决闭包问题
            self.records_tree.heading(
                col, text=col, command=functools.partial(self.sort_by_column, col))

        # 初始化排序指示器
        self.update_sort_indicators()

        # 设置列宽和对齐方式
        self.records_tree.column("名称或内容", width=250, anchor="w")  # 左对齐
        self.records_tree.column("类型", width=80, anchor="center")  # 居中对齐
        self.records_tree.column("大小", width=80, anchor="center")  # 居中对齐
        self.records_tree.column("时间", width=130, anchor="center")  # 居中对齐
        self.records_tree.column("次数", width=50, anchor="center")  # 居中对齐

        # 添加垂直滚动条,取消横向滚动条
        records_scrollbar_y = ttk.Scrollbar(
            tree_frame, orient=tk.VERTICAL, command=self.records_tree.yview, style='Vertical.TScrollbar')
        self.records_tree.configure(yscrollcommand=records_scrollbar_y.set)

        # 布局
        self.records_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        records_scrollbar_y.grid(row=0, column=1, sticky=(tk.N, tk.S))

        # 添加提示信息标签
        self.status_label = ttk.Label(self.records_frame, text="0条记录，累计大小0B", style='Status.TLabel')
        self.status_label.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), padx=15, pady=(0, 15))

        # 添加双击事件复制内容到剪贴板
        self.records_tree.bind("<Double-1>", self.copy_record_on_double_click)
      

        # 添加单击事件处理
        self.records_tree.bind("<Button-1>", self.copy_record_on_single_click)

        # 添加Delete键事件删除选中记录
        self.records_tree.bind("<Delete>", self.delete_selected_record_on_key)

        # 绑定滚动事件以实现自动加载更多
        self.records_tree.bind("<<TreeviewSelect>>", self.on_tree_select)
        self.records_tree.bind("<MouseWheel>", self.on_mouse_wheel)

    def sort_by_column(self, col):
        """根据点击的列进行排序"""
        # 如果点击的是同一列,则切换排序方向;否则默认倒序(与原始行为一致)
        if self.sort_column == col:
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_column = col
            self.sort_reverse = True  # 默认倒序,与原始行为一致

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
            self.records_tree.heading(
                col, text=heading_text, command=lambda c=col: self.sort_by_column(c))

    def setup_settings_tab(self):
        """设置标签页 - 简洁行布局,支持滚动"""
        # 创建外部容器框架
        container = tk.Frame(self.settings_frame, bg='#ffffff')
        container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 创建内部带阴影效果的框架
        inner_frame = tk.Frame(container, bg='#ffffff', relief='solid', bd=1)
        inner_frame.pack(fill=tk.BOTH, expand=True)
        
        # 添加顶部装饰条
        top_bar = tk.Frame(inner_frame, bg='#3498db', height=4)
        top_bar.pack(fill=tk.X)
        top_bar.pack_propagate(False)
        
        # 创建画布和滚动条以支持滚动，去除边框
        canvas = tk.Canvas(inner_frame, highlightthickness=0, bd=0, bg='#ffffff')
        scrollbar = tk.Scrollbar(
            inner_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, relief="flat", bd=0, bg='#ffffff')

        # 配置滚动区域
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(
                scrollregion=canvas.bbox("all")
            )
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # 绑定鼠标滚轮事件，使整个画布区域都支持滚动
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")

        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        scrollable_frame.bind("<MouseWheel>", _on_mousewheel)

        # 在窗口关闭时解绑事件
        def _on_closing():
            canvas.unbind_all("<MouseWheel>")

        # 打包画布和滚动条
        canvas.pack(side="left", fill="both", expand=True, padx=1, pady=1)
        scrollbar.pack(side="right", fill="y", padx=1, pady=1)

        # 标题区域
        title_frame = tk.Frame(scrollable_frame, bg='#ffffff')
        title_frame.pack(fill=tk.X, pady=(20, 10), padx=20)
        ttk.Label(title_frame, text="⚙️ 剪贴板管理器设置", style='SettingsTitle.TLabel').pack(side=tk.LEFT)

        # 分隔线
        separator = tk.Frame(scrollable_frame, height=1, bg='#e0e0e0')
        separator.pack(fill=tk.X, padx=20, pady=10)

        # 复制限制设置
        limit_frame = tk.Frame(scrollable_frame, bg='#ffffff')
        limit_frame.pack(fill=tk.X, pady=5, padx=20)
        ttk.Label(limit_frame, text="📋 复制限制设置", style='SettingsGroup.TLabel').pack(anchor=tk.W)

        # 无限模式复选框
        self.unlimited_var = tk.BooleanVar()
        unlimited_check = ttk.Checkbutton(
            limit_frame, text="无限模式(无限制)", variable=self.unlimited_var, style='SettingsOption.TCheckbutton')
        unlimited_check.pack(anchor=tk.W, pady=5)

        # 最大大小和数量设置
        size_count_container = tk.Frame(limit_frame, bg='#ffffff')
        size_count_container.pack(fill=tk.X, pady=10)
        
        tk.Label(size_count_container, text="📏 最大复制大小和数量", bg='#ffffff', font=("Segoe UI", 10, 'bold')).pack(
            anchor=tk.W, pady=(0, 10))
            
        size_count_frame = tk.Frame(size_count_container, relief="flat", bd=0, bg='#ffffff')
        size_count_frame.pack(fill=tk.X, pady=5)

        # 最大大小设置
        size_frame = tk.Frame(size_count_frame, bg='#ffffff')
        size_frame.pack(side=tk.LEFT, padx=(0, 20))
        tk.Label(size_frame, text="💾 大小:", bg='#ffffff', font=("Segoe UI", 10)).pack(side=tk.LEFT, padx=(0, 5))
        self.size_var = tk.StringVar()
        size_entry = ttk.Entry(
            size_frame, textvariable=self.size_var, width=10, style='Settings.TEntry')
        size_entry.pack(side=tk.LEFT, padx=(0, 5))
        tk.Label(size_frame, text="MB", bg='#ffffff', font=("Segoe UI", 10)).pack(side=tk.LEFT, padx=(0, 5))

        # 最大数量设置
        count_frame = tk.Frame(size_count_frame, bg='#ffffff')
        count_frame.pack(side=tk.LEFT)
        tk.Label(count_frame, text="🔢 数量:", bg='#ffffff', font=("Segoe UI", 10)).pack(side=tk.LEFT, padx=(0, 5))
        self.count_var = tk.StringVar()
        count_entry = ttk.Entry(
            count_frame, textvariable=self.count_var, width=10, style='Settings.TEntry')
        count_entry.pack(side=tk.LEFT, padx=(0, 5))
        tk.Label(count_frame, text="个", bg='#ffffff', font=("Segoe UI", 10)).pack(side=tk.LEFT, padx=(0, 5))

        # 保存天数设置
        retention_frame = tk.Frame(scrollable_frame, bg='#ffffff')
        retention_frame.pack(fill=tk.X, pady=5, padx=20)
        ttk.Label(retention_frame, text="💾 记录保存设置", style='SettingsGroup.TLabel').pack(
            anchor=tk.W, pady=(10, 0))

        # 永久保存选项
        self.retention_var = tk.StringVar()
        permanent_radio = ttk.Radiobutton(
            retention_frame, text="♾️ 永久保存", variable=self.retention_var, value="permanent", style='SettingsOption.TRadiobutton')
        permanent_radio.pack(anchor=tk.W, pady=8)

        # 自定义天数选项
        custom_frame = tk.Frame(retention_frame, relief="flat", bd=0, bg='#ffffff')
        custom_frame.pack(fill=tk.X, pady=5)

        custom_radio = ttk.Radiobutton(
            custom_frame, text="📆 自定义天数:", variable=self.retention_var, value="custom", style='SettingsOption.TRadiobutton')
        custom_radio.pack(side=tk.LEFT)

        self.days_var = tk.StringVar()
        self.days_entry = ttk.Entry(
            custom_frame, textvariable=self.days_var, width=10, style='Settings.TEntry')
        self.days_entry.pack(side=tk.LEFT, padx=(10, 5))
        tk.Label(custom_frame, text="天", bg='#ffffff', font=("Segoe UI", 10)).pack(side=tk.LEFT, padx=(5, 0))

        # 系统设置
        system_frame = tk.Frame(scrollable_frame, bg='#ffffff')
        system_frame.pack(fill=tk.X, pady=5, padx=20)
        ttk.Label(system_frame, text="🖥️ 系统设置", style='SettingsGroup.TLabel').pack(
            anchor=tk.W, pady=(10, 0))

        # 剪贴板类型保存机制
        type_frame = tk.Frame(system_frame, bg='#ffffff')
        type_frame.pack(fill=tk.X, pady=5)
        tk.Label(type_frame, text="📄 剪贴板记录类型", bg='#ffffff', font=("Segoe UI", 10, 'bold')).pack(
            anchor=tk.W, pady=(0, 8))

        self.clipboard_type_var = tk.StringVar(value="all")
        all_types_radio = ttk.Radiobutton(type_frame, text="📝 记录所有类型（文本和文件）",
                                         variable=self.clipboard_type_var, value="all", style='SettingsOption.TRadiobutton')
        all_types_radio.pack(anchor=tk.W, pady=3)

        text_only_radio = ttk.Radiobutton(
            type_frame, text="🔤 仅记录纯文本", variable=self.clipboard_type_var, value="text_only", style='SettingsOption.TRadiobutton')
        text_only_radio.pack(anchor=tk.W, pady=3)

        # 开机自启设置
        self.autostart_var = tk.BooleanVar()
        autostart_check = ttk.Checkbutton(
            system_frame, text="🚀 允许程序开机自启", variable=self.autostart_var, style='SettingsOption.TCheckbutton')
        autostart_check.pack(anchor=tk.W, pady=8)

        # 悬浮图标设置
        self.float_icon_var = tk.BooleanVar()
        float_icon_check = ttk.Checkbutton(
            system_frame, text="📍 启用悬浮图标", variable=self.float_icon_var, style='SettingsOption.TCheckbutton')
        float_icon_check.pack(anchor=tk.W, pady=3)

        # 悬浮图标透明度设置
        opacity_frame_container = tk.Frame(system_frame, bg='#ffffff')
        opacity_frame_container.pack(fill=tk.X, pady=5)
        tk.Label(opacity_frame_container, text="👁️ 悬浮图标透明度", bg='#ffffff', font=("Segoe UI", 10, 'bold')).pack(
            anchor=tk.W, pady=(0, 8))
        opacity_frame = tk.Frame(opacity_frame_container, relief="flat", bd=0, bg='#ffffff')
        opacity_frame.pack(fill=tk.X, pady=5)

        tk.Label(opacity_frame, text=" Transparency:", bg='#ffffff', font=("Segoe UI", 10)).pack(side=tk.LEFT, padx=(0, 5))
        self.opacity_var = tk.StringVar()
        opacity_entry = ttk.Entry(
            opacity_frame, textvariable=self.opacity_var, width=10, style='Settings.TEntry')
        opacity_entry.pack(side=tk.LEFT, padx=(0, 5))
        tk.Label(opacity_frame, text="%", bg='#ffffff', font=("Segoe UI", 10)).pack(side=tk.LEFT, padx=(0, 5))

        # 悬浮图标说明
        tk.Label(system_frame, text="💡 悬浮图标大小: 50×50, 可自由拖动, 点击显示页面",
                 bg='#ffffff', font=("Segoe UI", 9), fg='#777777').pack(anchor=tk.W, pady=(0, 15))

        # 数据管理
        data_frame = tk.Frame(scrollable_frame, bg='#ffffff')
        data_frame.pack(fill=tk.X, pady=5, padx=20)
        ttk.Label(data_frame, text="🗑️ 数据管理", style='SettingsGroup.TLabel').pack(
            anchor=tk.W, pady=(10, 0))

        # 重置所有记录
        reset_frame = tk.Frame(data_frame, relief="flat", bd=0, bg='#ffffff')
        reset_frame.pack(fill=tk.X, pady=10)

        tk.Label(reset_frame, text="⚠️ 此操作将删除所有记录和本地缓存文件!", bg='#ffffff', font=("Segoe UI", 10), fg='#e74c3c').pack(
            side=tk.LEFT, pady=5)
        tk.Button(reset_frame, text="🔄 重置所有记录", command=self.reset_all_records, 
                  bg='#e74c3c', fg='white', relief='flat', font=("Segoe UI", 10, 'bold'), cursor='hand2',
                  bd=0, highlightthickness=0).pack(
            side=tk.RIGHT, pady=5)

        # 按钮框架
        button_frame = tk.Frame(scrollable_frame, relief="flat", bd=0, bg='#ffffff')
        button_frame.pack(pady=30, padx=20)

        tk.Button(button_frame, text="✅ 保存设置", command=self.save_settings,
                  bg='#3498db', fg='white', relief='flat', font=("Segoe UI", 11, 'bold'), cursor='hand2',
                  bd=0, highlightthickness=0, padx=20, pady=8).pack(
            side=tk.LEFT, padx=(0, 15))
        tk.Button(button_frame, text="🔄 恢复默认",
                  command=self.reset_to_default_settings, 
                  bg='#95a5a6', fg='white', relief='flat', font=("Segoe UI", 11, 'bold'), cursor='hand2',
                  bd=0, highlightthickness=0, padx=20, pady=8).pack(side=tk.LEFT)

        # 初始化设置显示
        self.load_settings_display()

        # 绑定无限模式复选框事件
        self.unlimited_var.trace("w", lambda *args: self.toggle_entries())

        # 绑定窗口关闭事件
        self.root.protocol("WM_DELETE_WINDOW", _on_closing)

    def load_settings_display(self):
        """加载设置显示"""
        # 获取当前设置
        settings = self.db.get_settings()

        # 更新界面显示
        self.unlimited_var.set(settings['unlimited_mode'])
        max_size_mb = settings['max_copy_size'] / (1024 * 1024)
        self.size_var.set(str(max_size_mb))
        self.count_var.set(str(settings['max_copy_count']))
        self.retention_var.set(
            "permanent" if settings['retention_days'] == 0 else "custom")
        self.days_var.set(
            str(settings['retention_days']) if settings['retention_days'] > 0 else "30")
        self.days_entry.config(
            state="normal" if settings['retention_days'] > 0 else "disabled")
        self.autostart_var.set(settings['auto_start'])

        # 检查是否有悬浮图标设置,如果没有则添加默认值
        if 'float_icon' in settings:
            self.float_icon_var.set(settings['float_icon'])
        else:
            self.float_icon_var.set(True)

        # 检查是否有透明度设置,如果没有则添加默认值
        if 'opacity' in settings:
            self.opacity_var.set(str(settings['opacity']))
        else:
            self.opacity_var.set("15")  # 默认15%

        # 检查是否有剪贴板类型设置,如果没有则添加默认值
        if 'clipboard_type' in settings:
            self.clipboard_type_var.set(settings['clipboard_type'])
        else:
            self.clipboard_type_var.set("all")  # 默认记录所有类型

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

            # 如果不是无限模式,验证数值
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

            # 保存悬浮图标透明度设置
            try:
                opacity = int(self.opacity_var.get())
                # 限制透明度范围在5-100之间
                opacity = max(5, min(100, opacity))
            except ValueError:
                opacity = 15  # 默认值

            # 保存剪贴板类型设置
            clipboard_type = self.clipboard_type_var.get()

            # 更新所有设置
            self.db.update_settings(
                retention_days=retention_days,
                auto_start=auto_start,
                float_icon=float_icon,
                opacity=opacity,
                clipboard_type=clipboard_type
            )

            # 如果设置了自定义天数,检查并删除过期记录
            if retention_days > 0:
                self.db.delete_expired_records()

            # 设置开机自启
            self.set_auto_start(auto_start)

            # 处理悬浮图标
            self.handle_float_icon(float_icon)

            # 更新悬浮图标透明度
            self.update_float_icon_opacity()

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
            auto_start=False,
            float_icon=False,
            opacity=15,  # 默认透明度15%
            clipboard_type='all'  # 默认记录所有类型
        )

        # 更新界面显示
        self.unlimited_var.set(False)
        self.size_var.set("300")
        self.count_var.set("100")
        self.retention_var.set("permanent")
        self.days_entry.config(state="disabled")
        self.autostart_var.set(False)
        self.float_icon_var.set(False)
        self.opacity_var.set("15")
        self.clipboard_type_var.set("all")

        # 更新悬浮图标透明度
        self.update_float_icon_opacity()

        messagebox.showinfo("提示", "已恢复默认设置")

    def update_statistics_display(self):
        """更新统计信息显示"""
        # 获取统计信息
        text_count, file_count, total_size = self.db.get_statistics()
        total_count = text_count + file_count
        formatted_size = self.format_file_size(total_size)

        # 构造统计信息文本
        stats_info = f"{total_count}条记录，累计大小{formatted_size}"

        # 更新显示
        self.status_label.config(text=stats_info)

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

        # 加载所有记录(包括文本和文件)
        text_records = self.db.get_text_records(
            sort_by=db_sort_field, reverse=self.sort_reverse)
        file_records = self.db.get_file_records(
            sort_by=db_sort_field, reverse=self.sort_reverse)

        # 创建一个包含所有记录的列表
        all_records = []

        # 添加文本记录
        for record in text_records:
            # 记录格式:(id, content, timestamp, char_count, md5_hash, number)
            record_id, content, timestamp, char_count, md5_hash, number = record
            content_preview = self.sanitize_text_for_display(content, 50)
            all_records.append((content_preview, "文本", "-",
                               timestamp, str(number), "text", record_id))

        # 添加文件记录
        for record in file_records:
            # 记录格式:(id, original_path, saved_path, filename, file_size, file_type, md5_hash, timestamp, number)
            record_id, original_path, saved_path, filename, file_size, file_type, md5_hash, timestamp, number = record
            size_str = self.format_file_size(file_size)
            # 获取文件后缀作为类型显示
            file_extension = file_type if file_type else "未知"
            all_records.append(
                (filename, file_extension, size_str, timestamp, str(number), "file", record_id))

        # 显示记录
        for record in all_records:
            if record[5] == 'text':  # 文本记录
                self.records_tree.insert("", tk.END, values=(
                    record[0], record[1], record[2], record[3], record[4]), tags=("text", record[6]))
            else:  # 文件记录
                self.records_tree.insert("", tk.END, values=(
                    record[0], record[1], record[2], record[3], record[4]), tags=("file", record[6]))

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
        """加载下一页记录(已废弃)"""
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
        records = self.db.search_records(
            keyword=keyword, record_type=record_type)

        # 对搜索结果进行排序
        self.sort_search_results(records)

    def on_search_input(self, event):
        """处理搜索输入事件，实现实时搜索"""
        # 获取输入内容
        keyword = self.search_entry.get().strip()

        # 如果有搜索关键词，则执行搜索
        if keyword:
            self.search_records()
        else:
            # 如果搜索框为空，则显示所有记录
            self.load_records()

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
                cursor.execute(
                    'SELECT number FROM text_records WHERE id = ?', (record[1],))
                result = cursor.fetchone()
                number = str(result[0]) if result else "1"
                conn.close()
                all_records.append(
                    (content_preview, "文本", "-", record[3], number, "text", record[1]))
            else:
                # 文件记录(需要从数据库获取完整信息)
                conn = sqlite3.connect(self.db.db_path)
                cursor = conn.cursor()
                cursor.execute(
                    'SELECT file_size, number FROM file_records WHERE id = ?', (record[1],))
                file_info = cursor.fetchone()
                conn.close()

                if file_info:
                    file_size, number = file_info
                    size_str = self.format_file_size(file_size)
                    all_records.append(
                        (record[2], "文件", size_str, record[3], str(number), "file", record[1]))
                else:
                    all_records.append(
                        (record[2], "文件", "-", record[3], "1", "file", record[1]))

        # 根据当前排序列进行排序
        try:
            # 确定排序索引
            sort_index = 0  # 默认按第一列(名称或内容)排序
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
                # 对于大小和次数字段,尝试数值排序
                def get_numeric_value(record):
                    try:
                        if self.sort_column == "大小":
                            # 从第三列获取大小值,转换为数值
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
                all_records.sort(key=get_numeric_value,
                                 reverse=self.sort_reverse)
            else:
                # 文本类型字段使用文本排序
                all_records.sort(
                    key=lambda x: x[sort_index] if x[sort_index] is not None else "", reverse=self.sort_reverse)
        except (ValueError, TypeError):
            # 如果排序失败,回退到按时间排序
            all_records.sort(
                key=lambda x: x[3] if x[3] is not None else "", reverse=True)

        # 在记录标签页中显示排序后的结果
        for record in all_records:
            self.records_tree.insert("", tk.END, values=(
                record[0], record[1], record[2], record[3], record[4]), tags=(record[5], record[6]))

    def copy_record_on_double_click(self, event):
        """双击记录复制内容到剪贴板"""
        selection = self.records_tree.selection()
        if selection:
            item = selection[0]
            tags = self.records_tree.item(item, "tags")
            values = self.records_tree.item(item, "values")

            if len(tags) >= 2:
                record_type = tags[0]  # 记录类型(text或file)
                record_id = tags[1]    # 记录ID

                if record_type == "text":
                    # 从数据库获取完整文本内容
                    conn = sqlite3.connect(self.db.db_path)
                    cursor = conn.cursor()
                    cursor.execute(
                        'SELECT content FROM text_records WHERE id = ?', (record_id,))
                    result = cursor.fetchone()
                    conn.close()

                    if result:
                        full_text = result[0]
                        self.root.clipboard_clear()
                        self.root.clipboard_append(full_text)
                        # 显示提示信息
                        display_text = full_text[:20] + \
                            "..." if len(full_text) > 20 else full_text
                        self.status_label.config(
                            text=f"已复制：\"{display_text}\"")
                else:
                    # 对于文件类型，复制文件名
                    if len(values) > 0:
                        filename = values[0]  # 名称或内容列(文件名)
                        self.root.clipboard_clear()
                        self.root.clipboard_append(filename)
                        # 显示提示信息
                        display_text = filename[:20] + \
                            "..." if len(filename) > 20 else filename
                        self.status_label.config(
                            text=f"已复制文件名：\"{display_text}\"")

    def copy_record_on_single_click(self, event):
        """单击记录复制内容到剪贴板"""
        # 添加详细调试信息
        print(f"==== 单击事件开始 ====\n单击事件触发: x={event.x}, y={event.y}")
        
        # 获取点击位置的项目
        item = self.records_tree.identify_row(event.y)
        print(f"点击的项目ID: {item}")
        
        if item:
            # 选中该项目
            self.records_tree.selection_set(item)
            print("项目已选中")
            
            # 获取项目信息
            item_info = self.records_tree.item(item)
            tags = item_info.get("tags", [])
            values = item_info.get("values", [])
            
            print(f"项目完整信息: {item_info}")
            print(f"项目标签: {tags}")
            print(f"项目值: {values}")

            if len(tags) >= 2:
                record_type = tags[0]  # 记录类型(text或file)
                record_id = tags[1]    # 记录ID
                
                print(f"记录类型: {record_type}, 记录ID: {record_id}")

                if record_type == "text":
                    print("开始处理文本记录...")
                    # 从数据库获取完整文本内容
                    try:
                        conn = sqlite3.connect(self.db.db_path)
                        cursor = conn.cursor()
                        print(f"执行SQL查询: SELECT content FROM text_records WHERE id = {record_id}")
                        cursor.execute(
                            'SELECT content FROM text_records WHERE id = ?', (record_id,))
                        result = cursor.fetchone()
                        conn.close()
                        print(f"数据库查询结果: {result}")

                        if result:
                            full_text = result[0]
                            print(f"原始文本内容长度: {len(full_text)} 字符")
                            self.root.clipboard_clear()
                            self.root.clipboard_append(full_text)
                            # 显示提示信息
                            display_text = full_text[:20] + \
                                "..." if len(full_text) > 20 else full_text
                            self.status_label.config(
                                text=f"已复制：\"{display_text}\"")
                            print(f"已复制文本: {repr(display_text)}")
                        else:
                            print("未找到文本记录")
                    except Exception as e:
                        print(f"处理文本记录时出错: {e}")
                else:
                    print("开始处理文件记录...")
                    # 对于文件类型，复制文件名
                    if len(values) > 0:
                        filename = values[0]  # 名称或内容列(文件名)
                        print(f"原始文件名: {filename}")
                        self.root.clipboard_clear()
                        self.root.clipboard_append(filename)
                        # 显示提示信息
                        display_text = filename[:20] + \
                            "..." if len(filename) > 20 else filename
                        self.status_label.config(
                            text=f"已复制文件名：\"{display_text}\"")
                        print(f"已复制文件名: {repr(display_text)}")
                    else:
                        print("文件记录缺少值")
            else:
                print(f"标签信息不足，标签数量: {len(tags)}")
        else:
            print("未点击到有效项目")
        print("==== 单击事件结束 ====\n")

    def delete_selected_record_on_key(self, event):
        """按Delete键删除选中记录"""
        selection = self.records_tree.selection()
        if selection:
            item = selection[0]
            tags = self.records_tree.item(item, "tags")

            if len(tags) >= 2:
                record_type = tags[0]  # 记录类型(text或file)
                record_id = tags[1]    # 记录ID

                # 删除记录
                if record_type == "text":
                    self.db.delete_text_record(record_id)
                else:
                    self.db.delete_file_record(record_id)

                # 从界面移除
                self.records_tree.delete(item)

                # 显示提示信息
                self.status_label.config(text="记录已删除")

                # 更新统计信息
                self.update_statistics_display()

    def show_full_record(self, event):
        """显示记录的完整内容"""
        selection = self.records_tree.selection()
        if selection:
            item = selection[0]
            tags = self.records_tree.item(item, "tags")

            if len(tags) >= 2:
                record_type = tags[0]  # 记录类型(text或file)
                record_id = tags[1]    # 记录ID

                if record_type == "text":
                    # 从数据库获取完整文本内容
                    conn = sqlite3.connect(self.db.db_path)
                    cursor = conn.cursor()
                    cursor.execute(
                        'SELECT id, content FROM text_records WHERE id = ?', (record_id,))
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

                        text_area = scrolledtext.ScrolledText(
                            text_window, wrap=tk.WORD)
                        text_area.pack(
                            fill=tk.BOTH, expand=True, padx=10, pady=10)
                        text_area.insert(tk.END, full_text)
                        text_area.config(state=tk.DISABLED)
                else:
                    # 对于文件类型,打开文件位置
                    conn = sqlite3.connect(self.db.db_path)
                    cursor = conn.cursor()
                    cursor.execute(
                        'SELECT saved_path FROM file_records WHERE id = ?', (record_id,))
                    result = cursor.fetchone()
                    conn.close()

                    if result and os.path.exists(result[0]):
                        import subprocess
                        subprocess.run(['explorer', '/select,', result[0]])
                    else:
                        messagebox.showwarning("警告", "文件不存在")

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

            ttk.Label(confirm_window, text="此操作将删除所有记录和本地缓存文件!", foreground="red", font=(
                "Arial", 10, "bold")).pack(pady=(20, 10))
            ttk.Label(confirm_window, text="请输入以下文本以确认操作:").pack()

            confirmation_text = "确认重置所有记录"
            ttk.Label(confirm_window, text=confirmation_text,
                      font=("Arial", 10, "bold")).pack(pady=(5, 10))

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
                    messagebox.showwarning("警告", "输入文本不匹配,请重新输入")

            def cancel_reset():
                confirm_window.destroy()

            ttk.Button(button_frame, text="确认", command=confirm_reset).pack(
                side=tk.LEFT, padx=(0, 10))
            ttk.Button(button_frame, text="取消",
                       command=cancel_reset).pack(side=tk.LEFT)
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
            ttk.Label(settings_window, text="复制限制设置", font=(
                "Arial", 12, "bold")).pack(pady=(20, 10))

            # 无限模式复选框
            unlimited_var = tk.BooleanVar(value=settings['unlimited_mode'])
            unlimited_check = ttk.Checkbutton(
                settings_window, text="无限模式(无限制)", variable=unlimited_var)
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
            count_entry = ttk.Entry(
                count_frame, textvariable=count_var, width=10)
            count_entry.pack(side=tk.LEFT, padx=(10, 5), pady=10)
            ttk.Label(count_frame, text="个").pack(side=tk.LEFT)

            # 保存天数设置
            ttk.Label(settings_window, text="记录保存设置", font=(
                "Arial", 12, "bold")).pack(pady=(10, 5))

            retention_frame = ttk.LabelFrame(settings_window, text="保存天数")
            retention_frame.pack(fill=tk.X, padx=20, pady=(0, 10))

            # 永久保存选项
            retention_var = tk.StringVar(
                value="permanent" if settings['retention_days'] == 0 else "custom")
            permanent_radio = ttk.Radiobutton(
                retention_frame, text="永久保存", variable=retention_var, value="permanent")
            permanent_radio.pack(anchor=tk.W, padx=10, pady=5)

            # 自定义天数选项
            custom_frame = ttk.Frame(retention_frame)
            custom_frame.pack(fill=tk.X, padx=10, pady=5)

            custom_radio = ttk.Radiobutton(
                custom_frame, text="自定义天数:", variable=retention_var, value="custom")
            custom_radio.pack(side=tk.LEFT)

            days_var = tk.StringVar(value=str(
                settings['retention_days']) if settings['retention_days'] > 0 else "30")
            days_entry = ttk.Entry(custom_frame, textvariable=days_var, width=10,
                                   state="normal" if settings['retention_days'] > 0 else "disabled")
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
            ttk.Label(settings_window, text="系统设置", font=(
                "Arial", 12, "bold")).pack(pady=(10, 5))

            autostart_frame = ttk.LabelFrame(settings_window, text="开机自启")
            autostart_frame.pack(fill=tk.X, padx=20, pady=(0, 10))

            autostart_var = tk.BooleanVar(value=settings['auto_start'])
            autostart_check = ttk.Checkbutton(
                autostart_frame, text="允许程序开机自启", variable=autostart_var)
            autostart_check.pack(anchor=tk.W, padx=10, pady=10)

            # 按钮框架
            button_frame = ttk.Frame(settings_window)
            button_frame.pack(pady=(20, 0))

            def save_settings():
                try:
                    # 获取用户输入
                    unlimited_mode = unlimited_var.get()

                    # 如果不是无限模式,验证数值
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

                    # 如果设置了自定义天数,检查并删除过期记录
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

            ttk.Button(button_frame, text="保存", command=save_settings).pack(
                side=tk.LEFT, padx=(0, 10))
            ttk.Button(button_frame, text="恢复默认", command=reset_to_default).pack(
                side=tk.LEFT, padx=(0, 10))
            ttk.Button(button_frame, text="取消",
                       command=settings_window.destroy).pack(side=tk.LEFT)

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
                key = winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
                winreg.SetValueEx(key, "ClipboardManager",
                                  0, winreg.REG_SZ, exe_path)
                winreg.CloseKey(key)
            else:
                # 取消开机自启
                try:
                    key = winreg.OpenKey(
                        winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
                    winreg.DeleteValue(key, "ClipboardManager")
                    winreg.CloseKey(key)
                except FileNotFoundError:
                    # 如果值不存在,忽略错误
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

    def update_float_icon_opacity(self):
        """更新悬浮图标透明度"""
        if self.float_window:
            # 获取设置中的透明度值
            settings = self.db.get_settings()
            opacity = settings.get('opacity', 15)  # 默认15%
            # 将百分比转换为0-1之间的值
            alpha = opacity / 100.0
            # 更新透明度
            self.float_window.attributes("-alpha", alpha)

    def create_float_icon(self):
        """创建悬浮图标"""
        # 如果悬浮图标已经存在,先销毁
        self.destroy_float_icon()

        # 获取设置中的透明度值
        settings = self.db.get_settings()
        opacity = settings.get('opacity', 15)  # 默认15%
        # 将百分比转换为0-1之间的值
        alpha = opacity / 100.0

        # 创建悬浮窗口
        self.float_window = tk.Toplevel(self.root)
        self.float_window.title("悬浮图标")
        self.float_window.geometry("50x50")  # 改为80x80大小,符合需求说明
        self.float_window.overrideredirect(True)  # 去除窗口边框
        self.float_window.attributes("-topmost", True)  # 置顶显示
        self.float_window.attributes("-alpha", alpha)  # 设置透明度

        # 获取屏幕尺寸
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()

        # 设置默认位置为右下角(右边像素60,底部120)
        x = screen_width - 50 - 60  # 距离右边60像素
        y = screen_height - 50 - 120  # 距离底部120像素
        self.float_window.geometry(f"50x50+{x}+{y}")

        try:
            # 尝试加载mini.ico图片
            image_path = resource_path("mini.ico")
            image = Image.open(image_path)
            image = image.resize((50, 50), Image.LANCZOS)  # 调整图片大小

            # 创建圆角遮罩
            mask = Image.new('L', (50, 50), 0)
            draw = ImageDraw.Draw(mask)
            draw.rounded_rectangle((0, 0, 50, 50), radius=10, fill=255)
            
            # 应用遮罩以创建圆角效果
            image.putalpha(mask)

            photo = ImageTk.PhotoImage(image)

            # 创建标签显示图片
            label = tk.Label(self.float_window, image=photo, bg='#000000', bd=0)
            label.image = photo  # 保持引用防止被垃圾回收
            label.pack(fill=tk.BOTH, expand=True)
        except Exception as e:
            # 如果图片加载失败,使用默认的蓝色背景和文本
            print(f"加载mini.ico图片失败: {e}")
            self.float_window.configure(bg="#496D89")

            # 在窗口中央添加文本
            label = tk.Label(self.float_window, text="C", font=(
                "Arial", 24), bg="#496D89", fg="white")
            label.pack(expand=True)

        # 绑定鼠标事件以支持拖动
        self.float_window.bind("<Button-1>", self.start_move_float_icon)
        self.float_window.bind("<B1-Motion>", self.move_float_icon)

        # 绑定鼠标进入和点击事件
        # 绑定鼠标进入和点击事件
        self.float_window.bind("<Enter>", self.show_float_panel_on_hover)
        self.float_window.bind("<Leave>", self.check_and_hide_float_panel)
        self.float_window.bind("<ButtonRelease-1>",
                               self.handle_float_icon_click)
        self.float_window.bind("<Double-Button-1>",
                               self.show_main_window_from_float_icon)

        # 记录鼠标位置
        self.float_icon_x = 0
        self.float_icon_y = 0
        self.float_panel = None  # 悬浮面板引用
        self.float_click_count = 0  # 点击计数器

    def handle_float_icon_click(self, event):
        """处理悬浮图标点击事件"""
        # 检查是否是点击而不是拖动
        if abs(event.x - self.float_icon_x) < 5 and abs(event.y - self.float_icon_y) < 5:
            # 直接显示悬浮面板,不需要延迟
            self.show_float_panel(center_on_icon=True)

    def show_float_panel_on_hover(self, event):
        """鼠标移入时显示悬浮面板"""
        self.show_float_panel(center_on_icon=True)

    def show_float_panel_delayed(self):
        """延迟显示悬浮面板, 用于区分单击和双击"""
        self.show_float_panel(center_on_icon=True)

    def show_main_window_from_float_icon(self, event):
        """双击悬浮图标显示主窗口"""
        self.show_window()

    def show_float_panel(self, event=None, center_on_icon=False):
        """显示最近记录悬浮面板"""
        print(f"==== 显示悬浮面板 ====\ncenter_on_icon: {center_on_icon}")
        
        # 销毁已存在的面板
        if self.float_panel:
            self.float_panel.destroy()

        # 获取最近记录(增加到50条)
        text_records = self.db.get_text_records(50)  # 最多50条记录
        file_records = self.db.get_file_records(50)

        # 合并记录并按时间排序
        all_records = []
        for record in text_records:
            # 类型, 内容, 时间, ID
            all_records.append(("text", record[1], record[2], record[0]))

        for record in file_records:
            # 类型, 文件名, 时间, ID
            all_records.append(("file", record[3], record[7], record[0]))

        # 按时间排序(最新的在前面)
        all_records.sort(key=lambda x: x[2], reverse=True)

        # 只取前50条
        all_records = all_records[:50]

        # 创建悬浮面板 (200x400像素)
        self.float_panel = tk.Toplevel(self.float_window)
        self.float_panel.title("最近记录")
        self.float_panel.geometry("240x440")
        self.float_panel.overrideredirect(True)  # 去除窗口边框
        self.float_panel.attributes("-topmost", True)  # 置顶显示
        # 移除透明度设置，因为Tkinter的透明度支持有限

        # 设置面板样式
        self.float_panel.configure(bg="#f0f0f0")

        # 确保面板在屏幕范围内,并根据需要居中显示
        if center_on_icon:
            self.position_float_panel_above_icon(440)
        else:
            self.position_float_panel_within_screen(440)

        # 创建带圆角的面板背景
        # 简化背景创建过程
        bg_frame = tk.Frame(self.float_panel, bg="#ffffff", relief='solid', bd=1)
        bg_frame.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        # 创建标题栏
        header_frame = tk.Frame(bg_frame, bg="#3498db", height=40)
        header_frame.pack(fill=tk.X, side=tk.TOP)
        header_frame.pack_propagate(False)  # 固定高度

        # 标题文本
        header_label = tk.Label(header_frame, text="📋 最近记录", bg="#3498db", fg="white",
                                font=("Segoe UI", 11, "bold"))
        header_label.pack(expand=True)

        # 创建内容区域
        content_frame = tk.Frame(bg_frame, bg="#ffffff")
        content_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        # 创建Canvas和滚动条来显示记录
        canvas = tk.Canvas(content_frame, bg="#ffffff", highlightthickness=0)
        scrollbar = tk.Scrollbar(content_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg="#ffffff")
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(
                scrollregion=canvas.bbox("all")
            )
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # 打包Canvas和滚动条
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # 为Canvas添加鼠标滚轮支持
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        canvas.bind("<MouseWheel>", _on_mousewheel)
        scrollable_frame.bind("<MouseWheel>", _on_mousewheel)
        
        # 保存对滚动框架和canvas的引用
        self.scrollable_records_frame = scrollable_frame
        self.records_canvas = canvas

        # 存储记录信息用于双击处理
        self.float_panel_records = []

        for i, record in enumerate(all_records):
            record_type, content, timestamp, record_id = record
            if record_type == "text":
                # 文本记录
                display_text = content
            else:
                # 文件记录
                display_text = content

            # 处理文本,确保只显示一行并去除换行符
            display_text = display_text.replace('\n', ' ').replace('\r', ' ')
            # 如果文本过长,截取并添加省略号（超出截断隐藏符号）
            if len(display_text) > 50:
                display_text = display_text[:50] + "..."

            # 存储记录信息
            record_info = {
                'type': record_type,
                'id': record_id,
                'content': content if record_type == "text" else content
            }
            self.float_panel_records.append(record_info)
            
            # 为每条记录创建一个按钮
            record_button = tk.Button(
                self.scrollable_records_frame, 
                text=display_text,
                command=functools.partial(self._handle_float_panel_single_click, index=i),
                bd=0,
                relief="flat",
                fg="#333333",
                bg="#f8f9fa",
                activeforeground="#0066cc",
                activebackground="#e8f4fc",
                cursor="hand2",
                anchor="w",
                justify="left",
                wraplength=190,
                font=("Segoe UI", 9)
            )
            record_button.pack(fill="x", padx=0, pady=2)
            
            # 添加悬停效果
            def on_enter(e, btn=record_button):
                btn.config(bg="#e0f0ff")
                
            def on_leave(e, btn=record_button):
                btn.config(bg="#f8f9fa")
                
            record_button.bind("<Enter>", on_enter)
            record_button.bind("<Leave>", on_leave)
            
            # 为按钮添加鼠标滚轮支持
            record_button.bind("<MouseWheel>", _on_mousewheel)
            
            # 为按钮绑定双击事件
            record_button.bind("<Double-Button-1>", functools.partial(self._handle_float_panel_double_click, index=i))
            
        # 更新Canvas的滚动区域
        self.scrollable_records_frame.update_idletasks()
        self.records_canvas.configure(scrollregion=self.records_canvas.bbox("all"))
        
        # 创建底部"查看更多记录"
        footer_frame = tk.Frame(bg_frame, bg="#f0f0f0", height=40)
        footer_frame.pack(fill=tk.X, side=tk.BOTTOM)
        footer_frame.pack_propagate(False)

        footer_label = tk.Label(footer_frame, text="🔍 查看更多记录", bg="#f0f0f0", fg="#5c6bc0",
                                font=("Segoe UI", 10), cursor="hand2")
        footer_label.pack(expand=True)

        # 绑定底部点击事件,显示主窗口
        footer_frame.bind("<Button-1>", self.show_window_and_hide_panel)
        footer_label.bind("<Button-1>", self.show_window_and_hide_panel)

        # 绑定焦点事件,鼠标移出时隐藏面板
        self.float_panel.bind("<FocusOut>", self.hide_float_panel)
        self.float_panel.bind("<Leave>", self.hide_float_panel_on_leave)

        # 设置面板获取焦点
        self.float_panel.focus_set()
        
        # 添加调试信息确认面板创建完成
        print("悬浮面板创建完成")

    def create_rounded_panel_bg(self, parent, width, height, radius, color):
        """创建带圆角的面板背景"""
        try:
            # 创建一个图像作为背景
            image = Image.new('RGBA', (width, height), (0, 0, 0, 0))
            draw = ImageDraw.Draw(image)

            # 绘制圆角矩形
            draw.rounded_rectangle(
                [(0, 0), (width, height)], radius=radius, fill=color)

            # 转换为PhotoImage
            photo = ImageTk.PhotoImage(image)

            # 创建标签显示背景
            bg_label = tk.Label(parent, image=photo, bg=parent.cget('bg'))
            bg_label.image = photo  # 保持引用防止被垃圾回收
            bg_label.place(x=0, y=0, relwidth=1, relheight=1)
        except Exception as e:
            print(f"创建圆角背景失败: {e}")
            # 如果创建圆角背景失败,使用普通背景色
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

        # 按时间排序(最新的在前面)
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

    def copy_record_and_hide_panel_from_text(self, index):
        """从Text控件复制记录并隐藏面板"""
        print(f"==== copy_record_and_hide_panel_from_text函数开始 ====\n单击索引: {index}")
        print(f"==== 悬浮面板单击事件开始 ====\n单击索引: {index}")
        
        if hasattr(self, 'float_panel_records') and index < len(self.float_panel_records):
            record = self.float_panel_records[index]
            record_type = record['type']
            record_id = record['id']
            
            print(f"记录信息 - 类型: {record_type}, ID: {record_id}")

            if record_type == "text":
                print("开始处理文本记录...")
                # 从数据库获取完整文本内容
                try:
                    conn = sqlite3.connect(self.db.db_path)
                    cursor = conn.cursor()
                    print(f"执行SQL查询: SELECT content FROM text_records WHERE id = {record_id}")
                    cursor.execute(
                        'SELECT content FROM text_records WHERE id = ?', (record_id,))
                    result = cursor.fetchone()
                    conn.close()
                    print(f"数据库查询结果: {result}")

                    if result:
                        full_text = result[0]
                        print(f"原始文本内容长度: {len(full_text)} 字符")
                        self.root.clipboard_clear()
                        self.root.clipboard_append(full_text)
                        # 显示提示信息
                        display_text = full_text[:20] + \
                            "..." if len(full_text) > 20 else full_text
                        # 在状态栏显示复制成功的消息
                        if hasattr(self, 'status_label'):
                            self.status_label.config(text=f"已复制：\"{display_text}\"")
                            print(f"已在状态栏显示: 已复制：\"{display_text}\"")
                        else:
                            # 如果没有状态栏，在面板上显示提示
                            print(f"已复制：\"{display_text}\"")
                    else:
                        print("未找到文本记录")
                except Exception as e:
                    print(f"处理文本记录时出错: {e}")
            else:
                print("开始处理文件记录...")
                # 对于文件类型，复制文件名
                filename = record['content']
                print(f"原始文件名: {filename}")
                self.root.clipboard_clear()
                self.root.clipboard_append(filename)
                # 显示提示信息
                display_text = filename[:20] + \
                    "..." if len(filename) > 20 else filename
                # 在状态栏显示复制成功的消息
                if hasattr(self, 'status_label'):
                    self.status_label.config(text=f"已复制文件名：\"{display_text}\"")
                    print(f"已在状态栏显示: 已复制文件名：\"{display_text}\"")
                else:
                    # 如果没有状态栏，在面板上显示提示
                    print(f"已复制文件名：\"{display_text}\"")

        else:
            print(f"无效索引或缺少float_panel_records属性. 索引: {index}, float_panel_records存在: {hasattr(self, 'float_panel_records')}")
            if hasattr(self, 'float_panel_records'):
                print(f"float_panel_records长度: {len(self.float_panel_records)}")

        self.hide_float_panel()
        print("==== 悬浮面板单击事件结束 ====\n")
        print("==== copy_record_and_hide_panel_from_text函数结束 ====\n")
        
    def _handle_float_panel_single_click(self, event=None, index=None):
        """处理悬浮面板记录单击事件"""
        print(f"==== 悬浮面板记录单击事件触发 ====\n索引: {index}")
        print(f"事件对象: {event}")
        print(f"float_panel_records是否存在: {hasattr(self, 'float_panel_records')}")
        if hasattr(self, 'float_panel_records'):
            print(f"float_panel_records长度: {len(self.float_panel_records)}")
            if index < len(self.float_panel_records):
                print(f"记录信息: {self.float_panel_records[index]}")
        print(f"准备调用copy_record_and_hide_panel_from_text({index})")
        try:
            self.copy_record_and_hide_panel_from_text(index)
            print("copy_record_and_hide_panel_from_text调用完成")
        except Exception as e:
            print(f"调用copy_record_and_hide_panel_from_text时出错: {e}")
            import traceback
            traceback.print_exc()
        print("==== 悬浮面板记录单击事件处理完成 ====\n")
        
    def _handle_float_panel_double_click(self, event=None, index=None):
        """处理悬浮面板记录双击事件"""
        print(f"==== 悬浮面板记录双击事件触发 ====\n索引: {index}")
        print(f"事件对象: {event}")
        print(f"float_panel_records是否存在: {hasattr(self, 'float_panel_records')}")
        if hasattr(self, 'float_panel_records'):
            print(f"float_panel_records长度: {len(self.float_panel_records)}")
            if index < len(self.float_panel_records):
                print(f"记录信息: {self.float_panel_records[index]}")
        print(f"准备调用copy_record_and_hide_panel_from_text({index})")
        try:
            self.copy_record_and_hide_panel_from_text(index)
            print("copy_record_and_hide_panel_from_text调用完成")
        except Exception as e:
            print(f"调用copy_record_and_hide_panel_from_text时出错: {e}")
            import traceback
            traceback.print_exc()
        print("==== 悬浮面板记录双击事件处理完成 ====\n")
    def _test_click(self, event=None, index=None):
        """测试点击事件"""
        print(f"测试点击事件触发，记录{index}")
        
    def _debug_text_click(self, event=None):
        """调试Text控件点击事件"""
        print(f"Text控件点击事件触发，位置: ({event.x}, {event.y})")
        # 获取点击位置的索引
        index = self.records_text.index(f"@{event.x},{event.y}")
        print(f"点击位置索引: {index}")
        
    def _test_tag_bindings(self):
        """测试标签事件绑定"""
        if hasattr(self, 'records_text'):
            # 获取标签
            tags = self.records_text.tag_names()
            for tag in tags:
                if tag.startswith('record_'):
                    # 获取标签范围
                    ranges = self.records_text.tag_ranges(tag)
                    if not ranges:
                        print(f"警告: 标签 {tag} 没有设置范围!")
        else:
            print("records_text不存在")
            
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

        # 计算面板位置(默认在图标上方)
        panel_x = icon_x + (icon_width // 2) - (panel_width // 2)  # 水平居中对齐
        panel_y = icon_y - panel_height - 5  # 在图标上方5px处

        # 边界检查,确保面板在屏幕内
        # X轴边界检查
        if panel_x < 0:
            panel_x = 0
        elif panel_x + panel_width > screen_width:
            panel_x = screen_width - panel_width

        # Y轴边界检查
        if panel_y < 0:
            # 如果上方空间不足,显示在图标下方
            panel_y = icon_y + icon_height + 5

        # 确保面板底部也在屏幕内
        if panel_y + panel_height > screen_height:
            panel_y = screen_height - panel_height

        self.float_panel.geometry(
            f"{panel_width}x{panel_height}+{panel_x}+{panel_y}")

    def position_float_panel_centered(self, panel_height):
        """将悬浮面板居中显示在悬浮图标上, 完全覆盖图标"""
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

        # 计算面板位置,使其完全覆盖图标并居中
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

        self.float_panel.geometry(
            f"{panel_width}x{panel_height}+{panel_x}+{panel_y}")

    def position_float_panel_above_icon(self, panel_height):
        """将悬浮面板显示在悬浮图标上方,确保面板在屏幕内且不覆盖图标"""
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

        # 计算面板位置(在图标上方)
        panel_x = icon_x + (icon_width // 2) - (panel_width // 2)  # 水平居中对齐
        panel_y = icon_y - panel_height - 5  # 在图标上方5px处

        # 边界检查,确保面板在屏幕内
        # X轴边界检查
        if panel_x < 0:
            panel_x = 0
        elif panel_x + panel_width > screen_width:
            panel_x = screen_width - panel_width

        # Y轴边界检查
        if panel_y < 0:
            # 如果上方空间不足,显示在图标下方
            panel_y = icon_y + icon_height + 5

        # 确保面板底部也在屏幕内
        if panel_y + panel_height > screen_height:
            panel_y = screen_height - panel_height

        self.float_panel.geometry(
            f"{panel_width}x{panel_height}+{panel_x}+{panel_y}")

    def hide_float_panel(self, event=None):
        """隐藏悬浮面板"""
        # 延迟隐藏,避免焦点切换时立即隐藏
        self.float_window.after(100, self._hide_float_panel)

    def hide_float_panel_on_leave(self, event=None):
        """鼠标移出面板时隐藏面板"""
        # 延迟隐藏,避免意外触发
        self.float_panel.after(200, self._check_and_hide_float_panel)

    def check_and_hide_float_panel(self, event=None):
        """检查鼠标位置并决定是否隐藏面板(处理悬浮图标和面板之间的移动)"""
        # 延迟检查,给鼠标时间移动到面板上
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

                # 如果鼠标不在面板区域内,则隐藏面板
                if not (x1 <= mouse_x <= x2 and y1 <= mouse_y <= y2):
                    self.hide_float_panel()
        except Exception as e:
            # 出现异常时直接隐藏面板
            self.hide_float_panel()

    def _check_mouse_position_and_hide(self):
        """检查鼠标是否在悬浮图标或面板上,否则隐藏面板"""
        try:
            # 如果面板不存在,直接返回
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

            # 如果鼠标不在悬浮图标和面板上,则隐藏面板
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
        """移动悬浮图标,增加边界检查确保图标在屏幕内"""
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
        # 只在没有用户操作进行时才更新
        # 当窗口有焦点时不更新,避免干扰用户操作
        if not self.user_action_in_progress and not self.has_focus:
            # 如果窗口显示,更新所有记录
            if not self.is_hidden:
                self.load_records()
            else:
                # 如果窗口隐藏,只更新统计数据
                self.update_statistics_display()

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
