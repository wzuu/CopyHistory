#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
剪贴板管理器主程序
功能：
1. 监控剪贴板变化
2. 保存文本到数据库
3. 保存文件到分类文件夹并计算MD5
4. 避免重复保存相同MD5的文件
5. 提供GUI界面查询历史记录
"""

import sqlite3
import hashlib
import os
import time
import threading
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import win32clipboard
import win32con

def calculate_file_md5(file_path):
    """计算文件的MD5值"""
    hash_md5 = hashlib.md5()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except Exception as e:
        print(f"计算文件MD5时出错: {e}")
        return None

def get_file_type_category(filename):
    """根据文件扩展名确定文件类型分类"""
    ext = os.path.splitext(filename)[1].lower()
    if ext in ['.txt', '.log', '.md', '.rst']:
        return 'documents'
    elif ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp']:
        return 'images'
    elif ext in ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv']:
        return 'videos'
    elif ext in ['.mp3', '.wav', '.flac', '.aac', '.ogg']:
        return 'audio'
    elif ext in ['.pdf']:
        return 'pdf'
    elif ext in ['.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx']:
        return 'office'
    elif ext in ['.zip', '.rar', '.7z', '.tar', '.gz']:
        return 'archives'
    else:
        return 'others'

class ClipboardDatabase:
    def __init__(self, db_path=None):
        # 如果没有指定数据库路径，则使用智能路径选择
        if db_path is None:
            db_path = self._get_appropriate_db_path()
        
        # 确保数据库路径存在
        import os
        db_dir = os.path.dirname(os.path.abspath(db_path))
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
        
        self.db_path = db_path
        self.init_database()
    
    def _get_appropriate_db_path(self):
        """
        获取适当的数据库路径
        优先级：
        1. 程序所在目录
        2. 用户数据目录
        3. 临时目录
        """
        import os
        import sys
        # 获取程序所在目录
        if getattr(sys, 'frozen', False):
            # 如果是打包后的exe文件
            program_dir = os.path.dirname(sys.executable)
        else:
            # 如果是python脚本
            program_dir = os.path.dirname(os.path.abspath(__file__))
        
        # 尝试在程序目录创建数据库
        db_path = os.path.join(program_dir, "clipboard_history.db")
        if self._test_db_path(db_path):
            return db_path
        
        # 尝试在用户数据目录创建
        try:
            import appdirs
            user_data_dir = appdirs.user_data_dir("ClipboardManager", "ClipboardManager")
            os.makedirs(user_data_dir, exist_ok=True)
            db_path = os.path.join(user_data_dir, "clipboard_history.db")
            if self._test_db_path(db_path):
                return db_path
        except ImportError:
            pass
        
        # 尝试在AppData目录创建
        appdata_dir = os.environ.get('APPDATA')
        if appdata_dir:
            clipboard_dir = os.path.join(appdata_dir, "ClipboardManager")
            os.makedirs(clipboard_dir, exist_ok=True)
            db_path = os.path.join(clipboard_dir, "clipboard_history.db")
            if self._test_db_path(db_path):
                return db_path
        
        # 尝试在临时目录创建
        temp_dir = os.environ.get('TEMP', os.environ.get('TMP', '/tmp'))
        clipboard_dir = os.path.join(temp_dir, "ClipboardManager")
        os.makedirs(clipboard_dir, exist_ok=True)
        db_path = os.path.join(clipboard_dir, "clipboard_history.db")
        if self._test_db_path(db_path):
            return db_path
        
        # 最后回退到程序目录
        return os.path.join(program_dir, "clipboard_history.db")
    
    def _test_db_path(self, db_path):
        """
        测试数据库路径是否可用
        """
        try:
            import sqlite3
            conn = sqlite3.connect(db_path)
            conn.close()
            # 如果文件已存在，删除测试文件
            if os.path.exists(db_path):
                os.remove(db_path)
            return True
        except Exception as e:
            print(f"测试数据库路径 {db_path} 失败: {e}")
            return False
    
    def init_database(self):
        """初始化数据库"""
        try:
            conn = sqlite3.connect(self.db_path)
        except sqlite3.OperationalError as e:
            # 如果数据库文件无法创建，尝试在程序目录下创建
            import os
            program_dir_db = os.path.join(os.path.dirname(os.path.abspath(__file__)), "clipboard_history.db")
            print(f"无法在原路径创建数据库，尝试在程序目录创建: {program_dir_db}")
            conn = sqlite3.connect(program_dir_db)
            self.db_path = program_dir_db
        cursor = conn.cursor()
        
        # 创建文本记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS text_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                char_count INTEGER,
                md5_hash TEXT UNIQUE,
                number INTEGER DEFAULT 1
            )
        ''')
        
        # 创建文件记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS file_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                original_path TEXT,
                saved_path TEXT,
                filename TEXT,
                file_size INTEGER,
                file_type TEXT,
                md5_hash TEXT UNIQUE,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                number INTEGER DEFAULT 1
            )
        ''')
        
        # 创建设置表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                max_copy_size INTEGER DEFAULT 314572800,  -- 300MB in bytes
                max_copy_count INTEGER DEFAULT 100,
                unlimited_mode INTEGER DEFAULT 0  -- 0: limited, 1: unlimited
            )
        ''')
        
        # 插入默认设置（如果不存在）
        cursor.execute('''
            INSERT OR IGNORE INTO settings (id, max_copy_size, max_copy_count, unlimited_mode)
            VALUES (1, 314572800, 100, 0)
        ''')
        
        conn.commit()
        conn.close()
    
    def save_text_record(self, content):
        """保存文本记录到数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 计算文本内容的MD5值
        md5_hash = hashlib.md5(content.encode('utf-8')).hexdigest()
        
        # 使用本地时间而不是UTC时间
        local_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        try:
            cursor.execute('''
                INSERT INTO text_records (content, timestamp, char_count, md5_hash, number)
                VALUES (?, ?, ?, ?, ?)
            ''', (content, local_time, len(content), md5_hash, 1))
            
            record_id = cursor.lastrowid
            conn.commit()
            conn.close()
            return record_id
        except sqlite3.IntegrityError:
            # MD5已存在，更新记录并增加计数
            cursor.execute('''
                UPDATE text_records 
                SET timestamp = ?, number = number + 1
                WHERE md5_hash = ?
            ''', (local_time, md5_hash))
            
            cursor.execute('SELECT id FROM text_records WHERE md5_hash = ?', (md5_hash,))
            result = cursor.fetchone()
            record_id = result[0] if result else None
            conn.commit()
            conn.close()
            return record_id
    
    def save_file_record(self, original_path, saved_path, filename, file_size, file_type, md5_hash):
        """保存文件记录到数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 使用本地时间而不是UTC时间
        local_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        try:
            cursor.execute('''
                INSERT INTO file_records (original_path, saved_path, filename, file_size, file_type, md5_hash, timestamp, number)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (original_path, saved_path, filename, file_size, file_type, md5_hash, local_time, 1))
            
            record_id = cursor.lastrowid
            conn.commit()
            conn.close()
            return record_id
        except sqlite3.IntegrityError:
            # MD5已存在，更新记录并增加计数
            cursor.execute('''
                UPDATE file_records 
                SET original_path = ?, timestamp = ?, number = number + 1
                WHERE md5_hash = ?
            ''', (original_path, local_time, md5_hash))
            
            cursor.execute('SELECT id FROM file_records WHERE md5_hash = ?', (md5_hash,))
            result = cursor.fetchone()
            record_id = result[0] if result else None
            conn.commit()
            conn.close()
            return record_id

    def get_text_records(self, limit=30):
        """获取文本记录，默认只显示30条"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, content, timestamp, char_count, md5_hash, number
            FROM text_records
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (limit,))
        
        records = cursor.fetchall()
        conn.close()
        return records
    
    def get_file_records(self, limit=30):
        """获取文件记录，默认只显示30条"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, original_path, saved_path, filename, file_size, file_type, md5_hash, timestamp, number
            FROM file_records
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (limit,))
        
        records = cursor.fetchall()
        conn.close()
        return records
    
    def search_records(self, keyword="", record_type="all", start_date=None, end_date=None):
        """搜索记录"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = ""
        params = []
        
        if record_type == "text":
            query = '''
                SELECT 'text' as type, id, content as info, timestamp, char_count as size_md5
                FROM text_records
                WHERE content LIKE ?
            '''
            params.append(f"%{keyword}%")
        elif record_type == "file":
            query = '''
                SELECT 'file' as type, id, filename as info, timestamp, md5_hash as size_md5
                FROM file_records
                WHERE filename LIKE ?
            '''
            params.append(f"%{keyword}%")
        else:  # all
            query = '''
                SELECT 'text' as type, id, content as info, timestamp, char_count as size_md5
                FROM text_records
                WHERE content LIKE ?
                UNION ALL
                SELECT 'file' as type, id, filename as info, timestamp, md5_hash as size_md5
                FROM file_records
                WHERE filename LIKE ?
            '''
            params.extend([f"%{keyword}%", f"%{keyword}%"])
        
        if start_date:
            query += " AND timestamp >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND timestamp <= ?"
            params.append(end_date)
        
        query += " ORDER BY timestamp DESC LIMIT 30"
        
        cursor.execute(query, params)
        records = cursor.fetchall()
        conn.close()
        return records
    
    def get_statistics(self):
        """获取统计信息"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 获取文本记录数量
        cursor.execute('SELECT COUNT(*) FROM text_records')
        text_count = cursor.fetchone()[0]
        
        # 获取文件记录数量和总大小
        cursor.execute('SELECT COUNT(*), SUM(file_size) FROM file_records')
        file_result = cursor.fetchone()
        file_count = file_result[0]
        total_size = file_result[1] if file_result[1] else 0
        
        conn.close()
        return text_count, file_count, total_size
    
    def delete_text_record(self, record_id):
        """删除文本记录"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM text_records WHERE id = ?', (record_id,))
        conn.commit()
        conn.close()
    
    def delete_file_record(self, record_id):
        """删除文件记录"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM file_records WHERE id = ?', (record_id,))
        conn.commit()
        conn.close()
    
    def clear_all_records(self):
        """清除所有记录"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM text_records')
        cursor.execute('DELETE FROM file_records')
        conn.commit()
        conn.close()
    
    def get_settings(self):
        """获取设置"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT max_copy_size, max_copy_count, unlimited_mode FROM settings WHERE id = 1')
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                'max_copy_size': result[0],
                'max_copy_count': result[1],
                'unlimited_mode': bool(result[2])
            }
        else:
            # 返回默认设置
            return {
                'max_copy_size': 314572800,  # 300MB
                'max_copy_count': 100,
                'unlimited_mode': False
            }
    
    def update_settings(self, max_copy_size=None, max_copy_count=None, unlimited_mode=None):
        """更新设置"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if max_copy_size is not None:
            cursor.execute('UPDATE settings SET max_copy_size = ? WHERE id = 1', (max_copy_size,))
        
        if max_copy_count is not None:
            cursor.execute('UPDATE settings SET max_copy_count = ? WHERE id = 1', (max_copy_count,))
        
        if unlimited_mode is not None:
            cursor.execute('UPDATE settings SET unlimited_mode = ? WHERE id = 1', (int(unlimited_mode),))
        
        conn.commit()
        conn.close()

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

class ClipboardManager:
    def __init__(self):
        self.db = ClipboardDatabase()
        self.previous_content = None
        self.base_save_folder = "clipboard_files"
        os.makedirs(self.base_save_folder, exist_ok=True)
    
    def check_copy_limits(self, files):
        """检查复制限制"""
        # 获取当前设置
        settings = self.db.get_settings()
        
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
                        return False, f"文件 '{os.path.basename(file_path)}' 大小({format_file_size(file_size)})超过了限制({format_file_size(settings['max_copy_size'])})"
                except Exception as e:
                    print(f"获取文件大小时出错: {e}")
        
        # 检查总大小是否超过限制
        if total_size > settings['max_copy_size']:
            return False, f"一次复制的总大小({format_file_size(total_size)})超过了限制({format_file_size(settings['max_copy_size'])})"
        
        return True, ""
    
    def process_clipboard_content(self):
        """处理剪贴板内容"""
        try:
            win32clipboard.OpenClipboard()
            
            # 获取设置
            settings = self.db.get_settings()
            clipboard_type = settings.get('clipboard_type', 'all')  # 默认记录所有类型
            
            # 检查是否有文件列表
            has_file_list = win32clipboard.IsClipboardFormatAvailable(win32con.CF_HDROP)
            # 检查是否有文本内容
            has_text_content = win32clipboard.IsClipboardFormatAvailable(win32con.CF_UNICODETEXT)
            
            # 处理文件列表
            if has_file_list:
                # 如果设置为仅记录文本，则跳过文件处理（除非没有文本内容）
                if clipboard_type == 'text_only' and has_text_content:
                    # 有文本内容，跳过文件处理
                    pass
                else:
                    try:
                        files = win32clipboard.GetClipboardData(win32con.CF_HDROP)
                        if files:
                            # 检查复制限制
                            allowed, message = self.check_copy_limits(files)
                            if not allowed:
                                print(f"🚫 复制限制: {message}")
                                win32clipboard.CloseClipboard()
                                return
                            
                            # 处理文件
                            current_content_key = f"files:{';'.join(sorted(files))}"
                            if current_content_key != self.previous_content:
                                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                
                                for file_path in files:
                                    if os.path.exists(file_path):
                                        try:
                                            # 计算文件MD5
                                            md5_hash = calculate_file_md5(file_path)
                                            if not md5_hash:
                                                continue
                                            
                                            # 获取文件信息
                                            filename = os.path.basename(file_path)
                                            file_size = os.path.getsize(file_path)
                                            file_type = get_file_type_category(filename)
                                            
                                            # 构建保存路径
                                            date_folder = datetime.now().strftime("%Y-%m-%d")
                                            type_folder = file_type
                                            save_folder = os.path.join(self.base_save_folder, type_folder, date_folder)
                                            os.makedirs(save_folder, exist_ok=True)
                                            
                                            # 生成唯一文件名
                                            name, ext = os.path.splitext(filename)
                                            saved_filename = f"{name}_{md5_hash[:8]}{ext}"
                                            saved_path = os.path.join(save_folder, saved_filename)
                                            
                                            # 如果文件不存在则复制
                                            if not os.path.exists(saved_path):
                                                import shutil
                                                shutil.copy2(file_path, saved_path)
                                            
                                            # 保存到数据库
                                            record_id = self.db.save_file_record(
                                                file_path, saved_path, filename, file_size, file_type, md5_hash
                                            )
                                            
                                            if record_id:
                                                print(f"[{timestamp}] 保存文件记录 (ID: {record_id}): {filename}")
                                                if saved_path != file_path:
                                                    print(f"    文件已保存到: {saved_path}")
                                        except Exception as e:
                                            print(f"[{timestamp}] 处理文件 {file_path} 时出错: {e}")
                                
                                self.previous_content = current_content_key
                    
                    except Exception as e:
                        print(f"读取剪贴板文件列表时出错: {e}")
            
            # 处理文本内容
            if has_text_content:
                try:
                    text_content = win32clipboard.GetClipboardData(win32con.CF_UNICODETEXT)
                    if text_content and text_content.strip():
                        current_content_key = f"text:{hash(text_content)}"
                        if current_content_key != self.previous_content:
                            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            
                            # 检查文本大小限制（虽然一般不会超过限制）
                            text_size = len(text_content.encode('utf-8'))
                            settings = self.db.get_settings()
                            if not settings['unlimited_mode'] and text_size > settings['max_copy_size']:
                                print(f"🚫 文本大小({text_size}字节)超过了限制({settings['max_copy_size']}字节)")
                                win32clipboard.CloseClipboard()
                                return
                            
                            # 保存到数据库
                            record_id = self.db.save_text_record(text_content)
                            if record_id:
                                print(f"[{timestamp}] 保存文本记录 (ID: {record_id}), 字符数: {len(text_content)}")
                            
                            self.previous_content = current_content_key
                
                except Exception as e:
                    print(f"读取剪贴板文本时出错: {e}")
            
        except Exception as e:
            if "OpenClipboard" not in str(e):
                print(f"访问剪贴板时出错: {e}")
        finally:
            try:
                win32clipboard.CloseClipboard()
            except:
                pass

class ClipboardGUIMain:
    def __init__(self, root, manager):
        self.root = root
        self.manager = manager
        self.setup_ui()
        self.load_records()
    
    def setup_ui(self):
        """设置UI界面"""
        self.root.title("剪贴板历史记录管理器")
        self.root.geometry("1000x700")
        
        # 创建主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 搜索框架
        search_frame = ttk.LabelFrame(main_frame, text="搜索", padding="10")
        search_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Label(search_frame, text="关键词:").grid(row=0, column=0, padx=(0, 5))
        self.search_entry = ttk.Entry(search_frame, width=30)
        self.search_entry.grid(row=0, column=1, padx=(0, 10))
        
        ttk.Label(search_frame, text="类型:").grid(row=0, column=2, padx=(0, 5))
        self.type_var = tk.StringVar(value="all")
        type_combo = ttk.Combobox(search_frame, textvariable=self.type_var, 
                                 values=["all", "text", "file"], width=10)
        type_combo.grid(row=0, column=3, padx=(0, 10))
        
        ttk.Button(search_frame, text="搜索", command=self.search_records).grid(row=0, column=4, padx=(0, 10))
        ttk.Button(search_frame, text="刷新", command=self.load_records).grid(row=0, column=5)
        
        # 创建笔记本控件（标签页）
        notebook = ttk.Notebook(main_frame)
        notebook.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 文本记录标签页
        self.text_frame = ttk.Frame(notebook)
        notebook.add(self.text_frame, text="文本记录")
        self.setup_text_tab()
        
        # 文件记录标签页
        self.file_frame = ttk.Frame(notebook)
        notebook.add(self.file_frame, text="文件记录")
        self.setup_file_tab()
        
        # 配置网格权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(1, weight=1)
        self.text_frame.columnconfigure(0, weight=1)
        self.text_frame.rowconfigure(0, weight=1)
        self.file_frame.columnconfigure(0, weight=1)
        self.file_frame.rowconfigure(0, weight=1)
    
    def setup_text_tab(self):
        """设置文本记录标签页"""
        # 创建树形视图
        columns = ("ID", "内容", "时间", "字符数")
        self.text_tree = ttk.Treeview(self.text_frame, columns=columns, show="headings", height=20)
        
        # 设置列标题和宽度
        self.text_tree.heading("ID", text="ID")
        self.text_tree.heading("内容", text="内容")
        self.text_tree.heading("时间", text="时间")
        self.text_tree.heading("字符数", text="字符数")
        
        self.text_tree.column("ID", width=50)
        self.text_tree.column("内容", width=500)
        self.text_tree.column("时间", width=150)
        self.text_tree.column("字符数", width=80)
        
        # 添加滚动条
        text_scrollbar = ttk.Scrollbar(self.text_frame, orient=tk.VERTICAL, command=self.text_tree.yview)
        self.text_tree.configure(yscrollcommand=text_scrollbar.set)
        
        # 布局
        self.text_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        text_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # 绑定双击事件显示完整内容
        self.text_tree.bind("<Double-1>", self.show_full_text)
    
    def setup_file_tab(self):
        """设置文件记录标签页"""
        # 创建树形视图
        columns = ("ID", "文件名", "原路径", "保存路径", "大小", "类型", "MD5", "时间")
        self.file_tree = ttk.Treeview(self.file_frame, columns=columns, show="headings", height=20)
        
        # 设置列标题
        for col in columns:
            self.file_tree.heading(col, text=col)
        
        # 设置列宽
        self.file_tree.column("ID", width=50)
        self.file_tree.column("文件名", width=150)
        self.file_tree.column("原路径", width=200)
        self.file_tree.column("保存路径", width=200)
        self.file_tree.column("大小", width=80)
        self.file_tree.column("类型", width=80)
        self.file_tree.column("MD5", width=100)
        self.file_tree.column("时间", width=150)
        
        # 添加滚动条
        file_scrollbar = ttk.Scrollbar(self.file_frame, orient=tk.VERTICAL, command=self.file_tree.yview)
        self.file_tree.configure(yscrollcommand=file_scrollbar.set)
        
        # 布局
        self.file_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        file_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # 添加右键菜单
        self.file_menu = tk.Menu(self.root, tearoff=0)
        self.file_menu.add_command(label="打开文件位置", command=self.open_file_location)
        self.file_tree.bind("<Button-3>", self.show_file_menu)
    
    def show_file_menu(self, event):
        """显示文件右键菜单"""
        item = self.file_tree.identify_row(event.y)
        if item:
            self.file_tree.selection_set(item)
            self.file_menu.post(event.x_root, event.y_root)
    
    def open_file_location(self):
        """打开文件位置"""
        selection = self.file_tree.selection()
        if selection:
            item = selection[0]
            values = self.file_tree.item(item, "values")
            if len(values) > 3:
                saved_path = values[3]  # 保存路径列
                if os.path.exists(saved_path):
                    import subprocess
                    subprocess.run(['explorer', '/select,', saved_path])
                else:
                    messagebox.showwarning("警告", "文件不存在")
    
    def show_full_text(self, event):
        """显示完整文本内容"""
        selection = self.text_tree.selection()
        if selection:
            item = selection[0]
            values = self.text_tree.item(item, "values")
            if len(values) > 1:
                full_text = values[1]
                # 如果内容被截断，从数据库获取完整内容
                record_id = values[0]
                conn = sqlite3.connect(self.manager.db.db_path)
                cursor = conn.cursor()
                cursor.execute('SELECT content FROM text_records WHERE id = ?', (record_id,))
                result = cursor.fetchone()
                conn.close()
                
                if result:
                    full_text = result[0]
                
                # 创建新窗口显示完整内容
                text_window = tk.Toplevel(self.root)
                text_window.title(f"文本记录详情 - ID: {record_id}")
                text_window.geometry("600x400")
                
                text_area = tk.Text(text_window, wrap=tk.WORD)
                text_area.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
                text_area.insert(tk.END, full_text)
                text_area.config(state=tk.DISABLED)
    
    def load_records(self):
        """加载记录"""
        # 清空现有记录
        for item in self.text_tree.get_children():
            self.text_tree.delete(item)
        
        for item in self.file_tree.get_children():
            self.file_tree.delete(item)
        
        # 加载文本记录
        text_records = self.manager.db.get_text_records()
        for record in text_records:
            # 内容预览
            content_preview = record[1][:50] + "..." if len(record[1]) > 50 else record[1]
            self.text_tree.insert("", tk.END, values=(record[0], content_preview, record[2], record[3]))
        
        # 加载文件记录
        file_records = self.manager.db.get_file_records()
        for record in file_records:
            # 文件大小格式化
            size_str = format_file_size(record[4])
            self.file_tree.insert("", tk.END, values=(
                record[0], record[3], record[1], record[2], 
                size_str, record[5], record[6][:8], record[7]
            ))
    
    def search_records(self):
        """搜索记录"""
        keyword = self.search_entry.get()
        record_type = self.type_var.get()
        
        # 清空现有记录
        for item in self.text_tree.get_children():
            self.text_tree.delete(item)
        
        for item in self.file_tree.get_children():
            self.file_tree.delete(item)
        
        # 搜索记录
        records = self.manager.db.search_records(keyword=keyword, record_type=record_type)
        
        for record in records:
            if record[0] == 'text':
                # 文本记录
                content_preview = record[2][:50] + "..." if len(record[2]) > 50 else record[2]
                self.text_tree.insert("", tk.END, values=(record[1], content_preview, record[3], ""))
            else:
                # 文件记录
                self.file_tree.insert("", tk.END, values=(
                    record[1], record[2], "", "", "", "", "", record[3]
                ))

def monitor_clipboard_loop(manager, interval=1):
    """剪贴板监控循环"""
    print("📋 剪贴板监控已启动...")
    print(f"⏱  检测间隔: {interval}秒")
    print("按 Ctrl+C 停止监控")
    print("=" * 50)
    
    try:
        while True:
            manager.process_clipboard_content()
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\n👋 剪贴板监控已停止")

def main():
    """主函数"""
    # 创建剪贴板管理器
    manager = ClipboardManager()
    
    # 解析命令行参数
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--monitor":
        # 仅运行监控器
        interval = 1.0
        if len(sys.argv) > 3 and sys.argv[2] == "-i":
            try:
                interval = float(sys.argv[3])
            except ValueError:
                print("❌ 时间间隔必须是数字")
                sys.exit(1)
        monitor_clipboard_loop(manager, interval)
    else:
        # 运行GUI应用
        root = tk.Tk()
        app = ClipboardGUIMain(root, manager)
        
        # 在单独线程中运行剪贴板监控
        monitor_thread = threading.Thread(target=monitor_clipboard_loop, args=(manager, 1), daemon=True)
        monitor_thread.start()
        
        # 启动GUI
        root.mainloop()

if __name__ == "__main__":
    main()