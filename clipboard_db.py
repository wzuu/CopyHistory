#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
剪贴板数据库管理模块
"""

import sqlite3
import hashlib
import os
from datetime import datetime, timezone
import time

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
            # 不要删除已存在的数据库文件
            return True
        except Exception as e:
            print(f"测试数据库路径 {db_path} 失败: {e}")
            return False
    
    def init_database(self):
        """初始化数据库"""
        try:
            conn = sqlite3.connect(self.db_path)
            print(f"数据库连接成功: {self.db_path}")
        except sqlite3.OperationalError as e:
            print(f"数据库连接失败: {e}")
            raise
        cursor = conn.cursor()
        
        # 创建文本记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS text_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                char_count INTEGER
            )
        ''')
        
        # 检查并添加 md5_hash 字段（如果不存在）
        try:
            cursor.execute("ALTER TABLE text_records ADD COLUMN md5_hash TEXT")
        except sqlite3.OperationalError:
            # 字段已存在，忽略错误
            pass
            
        # 为md5_hash字段添加唯一性索引
        try:
            cursor.execute("CREATE UNIQUE INDEX idx_text_records_md5_hash ON text_records(md5_hash) WHERE md5_hash IS NOT NULL")
        except sqlite3.OperationalError:
            # 索引已存在，忽略错误
            pass
            
        # 检查并添加 number 字段（如果不存在）
        try:
            cursor.execute("ALTER TABLE text_records ADD COLUMN number INTEGER DEFAULT 1")
        except sqlite3.OperationalError:
            # 字段已存在，忽略错误
            pass
        
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
        
        # 检查并添加 number 字段（如果不存在）
        try:
            cursor.execute("ALTER TABLE file_records ADD COLUMN number INTEGER DEFAULT 1")
        except sqlite3.OperationalError:
            # 字段已存在，忽略错误
            pass
            
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
        
        # 检查并添加 retention_days 字段（如果不存在）
        try:
            cursor.execute("ALTER TABLE settings ADD COLUMN retention_days INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            # 字段已存在，忽略错误
            pass
            
        # 检查并添加 auto_start 字段（如果不存在）
        try:
            cursor.execute("ALTER TABLE settings ADD COLUMN auto_start INTEGER DEFAULT 1")
        except sqlite3.OperationalError:
            # 字段已存在，忽略错误
            pass
            
        # 检查并添加 float_icon 字段（如果不存在）
        try:
            cursor.execute("ALTER TABLE settings ADD COLUMN float_icon INTEGER DEFAULT 1")
        except sqlite3.OperationalError:
            # 字段已存在，忽略错误
            pass
        
        # 检查并添加 opacity 字段（如果不存在）
        try:
            cursor.execute("ALTER TABLE settings ADD COLUMN opacity INTEGER DEFAULT 15")
        except sqlite3.OperationalError:
            # 字段已存在，忽略错误
            pass
        
        # 检查并添加 clipboard_type 字段（如果不存在）
        try:
            cursor.execute("ALTER TABLE settings ADD COLUMN clipboard_type TEXT DEFAULT 'all'")
        except sqlite3.OperationalError:
            # 字段已存在，忽略错误
            pass
        
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

    def get_text_records(self, limit=None, offset=0, sort_by="timestamp", reverse=True):
        """获取文本记录，支持排序"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 确定排序方向
        order = "DESC" if reverse else "ASC"
        
        # 确定排序字段
        if sort_by == "content":
            sort_field = "content"
        elif sort_by == "char_count":
            sort_field = "char_count"
        elif sort_by == "number":
            sort_field = "number"
        else:
            sort_field = "timestamp"
        
        if limit is None:
            # 获取所有记录
            cursor.execute(f'''
                SELECT id, content, timestamp, char_count, md5_hash, number
                FROM text_records
                ORDER BY {sort_field} {order}
            ''')
        else:
            # 获取指定数量的记录
            cursor.execute(f'''
                SELECT id, content, timestamp, char_count, md5_hash, number
                FROM text_records
                ORDER BY {sort_field} {order}
                LIMIT ? OFFSET ?
            ''', (limit, offset))
        
        records = cursor.fetchall()
        conn.close()
        return records
    
    def get_file_records(self, limit=None, offset=0, sort_by="timestamp", reverse=True):
        """获取文件记录，支持排序"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 确定排序方向
        order = "DESC" if reverse else "ASC"
        
        # 确定排序字段
        if sort_by == "filename":
            sort_field = "filename"
        elif sort_by == "file_size":
            sort_field = "file_size"
        elif sort_by == "file_type":
            sort_field = "file_type"
        elif sort_by == "number":
            sort_field = "number"
        else:
            sort_field = "timestamp"
        
        if limit is None:
            # 获取所有记录
            cursor.execute(f'''
                SELECT id, original_path, saved_path, filename, file_size, file_type, md5_hash, timestamp, number
                FROM file_records
                ORDER BY {sort_field} {order}
            ''')
        else:
            # 获取指定数量的记录
            cursor.execute(f'''
                SELECT id, original_path, saved_path, filename, file_size, file_type, md5_hash, timestamp, number
                FROM file_records
                ORDER BY {sort_field} {order}
                LIMIT ? OFFSET ?
            ''', (limit, offset))
        
        records = cursor.fetchall()
        conn.close()
        return records
    
    def get_all_records(self):
        """获取所有记录"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 'text' as type, id, content as info, timestamp
            FROM text_records
            UNION ALL
            SELECT 'file' as type, id, filename as info, timestamp
            FROM file_records
            ORDER BY timestamp DESC
        ''')
        
        records = cursor.fetchall()
        conn.close()
        return records
    
    def search_records(self, keyword="", record_type="all"):
        """搜索记录"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if record_type == "text":
            cursor.execute('''
                SELECT 'text' as type, id, content as info, timestamp
                FROM text_records
                WHERE content LIKE ?
                ORDER BY timestamp DESC
            ''', (f"%{keyword}%",))
        elif record_type == "file":
            cursor.execute('''
                SELECT 'file' as type, id, filename as info, timestamp
                FROM file_records
                WHERE filename LIKE ?
                ORDER BY timestamp DESC
            ''', (f"%{keyword}%",))
        else:  # all
            cursor.execute('''
                SELECT 'text' as type, id, content as info, timestamp
                FROM text_records
                WHERE content LIKE ?
                UNION ALL
                SELECT 'file' as type, id, filename as info, timestamp
                FROM file_records
                WHERE filename LIKE ?
                ORDER BY timestamp DESC
            ''', (f"%{keyword}%", f"%{keyword}%"))
        
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
        cursor.execute('SELECT max_copy_size, max_copy_count, unlimited_mode, retention_days, auto_start, float_icon, opacity, clipboard_type FROM settings WHERE id = 1')
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                'max_copy_size': result[0],
                'max_copy_count': result[1],
                'unlimited_mode': bool(result[2]),
                'retention_days': result[3],
                'auto_start': bool(result[4]),
                'float_icon': bool(result[5]),
                'opacity': result[6],
                'clipboard_type': result[7]
            }
        else:
            # 返回默认设置
            return {
                'max_copy_size': 314572800,  # 300MB
                'max_copy_count': 100,
                'unlimited_mode': False,
                'retention_days': 0,  # 永久保存
                'auto_start': False,
                'float_icon': False,
                'opacity': 15,  # 默认透明度15%
                'clipboard_type': 'all'  # 默认记录所有类型
            }
    
    def update_settings(self, max_copy_size=None, max_copy_count=None, unlimited_mode=None, retention_days=None, auto_start=None, float_icon=None, opacity=None, clipboard_type=None):
        """更新设置"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if max_copy_size is not None:
            cursor.execute('UPDATE settings SET max_copy_size = ? WHERE id = 1', (max_copy_size,))
        
        if max_copy_count is not None:
            cursor.execute('UPDATE settings SET max_copy_count = ? WHERE id = 1', (max_copy_count,))
        
        if unlimited_mode is not None:
            cursor.execute('UPDATE settings SET unlimited_mode = ? WHERE id = 1', (int(unlimited_mode),))
            
        if retention_days is not None:
            cursor.execute('UPDATE settings SET retention_days = ? WHERE id = 1', (retention_days,))
            
        if auto_start is not None:
            cursor.execute('UPDATE settings SET auto_start = ? WHERE id = 1', (int(auto_start),))
            
        if float_icon is not None:
            cursor.execute('UPDATE settings SET float_icon = ? WHERE id = 1', (int(float_icon),))
            
        if opacity is not None:
            cursor.execute('UPDATE settings SET opacity = ? WHERE id = 1', (opacity,))
            
        if clipboard_type is not None:
            cursor.execute('UPDATE settings SET clipboard_type = ? WHERE id = 1', (clipboard_type,))
        
        conn.commit()
        conn.close()
    
    def delete_expired_records(self):
        """删除过期记录"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 获取保留天数设置
        settings = self.get_settings()
        retention_days = settings['retention_days']
        
        # 如果设置为永久保存（0天）则不删除任何记录
        if retention_days <= 0:
            conn.close()
            return
        
        # 计算过期时间
        from datetime import datetime, timedelta
        expired_date = datetime.now() - timedelta(days=retention_days)
        expired_date_str = expired_date.strftime("%Y-%m-%d %H:%M:%S")
        
        # 删除过期的文本记录
        cursor.execute('SELECT id FROM text_records WHERE timestamp < ?', (expired_date_str,))
        text_records_to_delete = cursor.fetchall()
        
        cursor.execute('DELETE FROM text_records WHERE timestamp < ?', (expired_date_str,))
        
        # 删除过期的文件记录
        cursor.execute('SELECT saved_path FROM file_records WHERE timestamp < ?', (expired_date_str,))
        file_paths_to_delete = cursor.fetchall()
        
        cursor.execute('DELETE FROM file_records WHERE timestamp < ?', (expired_date_str,))
        
        conn.commit()
        conn.close()
        
        # 删除对应的文件
        for row in file_paths_to_delete:
            file_path = row[0]
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except Exception as e:
                    print(f"删除文件时出错: {e}")
