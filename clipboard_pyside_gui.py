#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
剪贴板历史记录GUI界面 (PySide6版本)
"""

import sys
import os
import sqlite3
import hashlib
import shutil
import functools
from datetime import datetime
from pathlib import Path

# PySide6 imports
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QTabWidget, QTreeView, QAbstractItemView, QHeaderView, 
    QLineEdit, QLabel, QPushButton, QGroupBox, QRadioButton, 
    QCheckBox, QSpinBox, QScrollArea, QMessageBox, QFileDialog,
    QSystemTrayIcon, QMenu, QTextEdit, QDialog, QFrame
)
from PySide6.QtCore import Qt, QTimer, QModelIndex, Signal, QAbstractTableModel, QRect, QPoint
from PySide6.QtGui import QIcon, QAction, QStandardItemModel, QStandardItem, QPixmap

# Import our modules
from clipboard_db import ClipboardDatabase
from clipboard_content_detector import format_file_size

# Try to import system tray icon support
try:
    import pystray
    TRAY_ICON_AVAILABLE = True
except ImportError:
    TRAY_ICON_AVAILABLE = False
    print("提示: 安装 pystray 可以启用系统托盘图标功能")


def resource_path(relative_path):
    """获取资源文件的绝对路径"""
    try:
        # PyInstaller创建临时文件夹,将路径存储在_MEIPASS中
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


class ClipboardRecordModel(QAbstractTableModel):
    """剪贴板记录模型"""
    
    def __init__(self, db):
        super().__init__()
        self.db = db
        self.records = []
        self.headers = ["名称或内容", "类型", "大小", "时间"]  # 移除了"次数"
        
    def loadData(self, sort_column="时间", sort_reverse=True):
        """加载数据"""
        # 清空现有记录
        self.beginResetModel()
        self.records = []
        
        # 获取文本记录
        text_records = self.db.get_text_records()
        for record in text_records:
            # 记录格式:(id, content, timestamp, char_count, md5_hash, number)
            record_id, content, timestamp, char_count, md5_hash, number = record
            content_preview = self.sanitizeText(content, 50)
            self.records.append({
                'name_or_content': content_preview,    # 名称或内容
                'type': '文本',                        # 类型
                'size': '-',                          # 大小
                'timestamp': timestamp,               # 时间
                'id': record_id,
                'record_type': 'text'
            })
        
        # 获取文件记录
        file_records = self.db.get_file_records()
        for record in file_records:
            # 记录格式:(id, original_path, saved_path, filename, file_size, file_type, md5_hash, timestamp, number)
            record_id, original_path, saved_path, filename, file_size, file_type, md5_hash, timestamp, number = record
            size_str = format_file_size(file_size)
            file_extension = file_type if file_type else "未知"
            self.records.append({
                'name_or_content': filename,          # 名称或内容
                'type': file_extension,               # 类型
                'size': size_str,                     # 大小
                'timestamp': timestamp,               # 时间
                'id': record_id,
                'record_type': 'file'
            })
        
        # 排序
        sort_index = self.headers.index(sort_column) if sort_column in self.headers else 3  # 默认按时间排序
        
        def sort_key(record):
            if sort_column == "大小":
                # 特殊处理大小排序
                size_str = record['size']
                if size_str == "-":
                    return 0
                if "GB" in size_str:
                    return float(size_str.replace("GB", "")) * 1024 * 1024 * 1024
                elif "MB" in size_str:
                    return float(size_str.replace("MB", "")) * 1024 * 1024
                elif "KB" in size_str:
                    return float(size_str.replace("KB", "")) * 1024
                else:
                    return float(size_str.replace("B", ""))
            else:
                return record[list(record.keys())[sort_index]]
        
        self.records.sort(key=sort_key, reverse=sort_reverse)
        self.endResetModel()
    
    def sanitizeText(self, text, max_length=100):
        """清理文本内容,移除换行符并截断过长内容"""
        # 将换行符替换为空格
        sanitized = text.replace('\n', ' ').replace('\r', ' ')
        # 截断过长内容
        if len(sanitized) <= max_length:
            return sanitized
        else:
            return sanitized[:max_length] + "..."
    
    def rowCount(self, parent=None):
        return len(self.records)
    
    def columnCount(self, parent=None):
        return len(self.headers)
    
    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or index.row() >= len(self.records):
            return None
            
        record = self.records[index.row()]
        
        if role == Qt.DisplayRole:
            # 按列索引返回正确的数据显示
            if index.column() == 0:
                return record['name_or_content']  # 名称或内容
            elif index.column() == 1:
                return record['type']              # 类型
            elif index.column() == 2:
                return record['size']              # 大小
            elif index.column() == 3:
                return record['timestamp']         # 时间
                
        elif role == Qt.UserRole:
            # 返回记录ID
            return record['id']
        elif role == Qt.UserRole + 1:
            # 返回记录类型
            return record['record_type']
            
        return None
    
    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.headers[section]
        return None


class RecordsTab(QWidget):
    """记录标签页"""
    
    recordDoubleClicked = Signal(str, int)  # record_type, record_id
    
    def __init__(self, db):
        super().__init__()
        self.db = db
        self.model = ClipboardRecordModel(db)
        self.sort_column = "时间"
        self.sort_reverse = True
        self.setupUI()
        self.loadData()
        
    def setupUI(self):
        """设置UI界面"""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # 搜索框
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("🔍"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("搜索记录...")
        self.search_edit.textChanged.connect(self.onSearchTextChanged)
        search_layout.addWidget(self.search_edit)
        layout.addLayout(search_layout)
        
        # 记录表格
        self.tree_view = QTreeView()
        self.tree_view.setModel(self.model)
        self.tree_view.setRootIsDecorated(False)
        self.tree_view.setAlternatingRowColors(True)
        self.tree_view.setSortingEnabled(True)
        self.tree_view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tree_view.doubleClicked.connect(self.onRecordDoubleClicked)
        
        # 设置列宽按百分比
        header = self.tree_view.header()
        header.setSectionResizeMode(0, QHeaderView.Stretch)  # 名称或内容列占剩余空间
        header.setSectionResizeMode(1, QHeaderView.Fixed)    # 类型列固定宽度
        header.setSectionResizeMode(2, QHeaderView.Fixed)    # 大小列固定宽度
        header.setSectionResizeMode(3, QHeaderView.Fixed)    # 时间列固定宽度
        
        # 设置固定列的具体宽度（基于800px窗口宽度的大致百分比）
        self.tree_view.setColumnWidth(1, 80)   # 类型列约占10%
        self.tree_view.setColumnWidth(2, 90)   # 大小列约占11%
        self.tree_view.setColumnWidth(3, 150)  # 时间列约占19%
        # 名称或内容列将自动填充剩余约60%的空间
        
        layout.addWidget(self.tree_view)
        
        # 状态标签
        self.status_label = QLabel("0条记录，累计大小0B")
        self.status_label.setStyleSheet("color: #666666;")
        layout.addWidget(self.status_label)
        
    def loadData(self):
        """加载数据"""
        self.model.loadData(self.sort_column, self.sort_reverse)
        self.updateStatistics()
        
    def updateStatistics(self):
        """更新统计信息"""
        text_count, file_count, total_size = self.db.get_statistics()
        total_count = text_count + file_count
        formatted_size = format_file_size(total_size)
        self.status_label.setText(f"{total_count}条记录，累计大小{formatted_size}")
        
    def onSearchTextChanged(self, text):
        """搜索文本改变事件"""
        # TODO: 实现搜索功能
        pass
        
    def onRecordDoubleClicked(self, index):
        """记录双击事件"""
        record_type = self.model.data(self.tree_view.currentIndex(), Qt.UserRole + 1)
        record_id = self.model.data(self.tree_view.currentIndex(), Qt.UserRole)
        self.recordDoubleClicked.emit(record_type, record_id)
        
    def sortByColumn(self, column):
        """根据列排序"""
        headers = ["名称或内容", "类型", "大小", "时间"]  # 更新了列标题列表
        if column < len(headers):
            column_name = headers[column]
            if self.sort_column == column_name:
                self.sort_reverse = not self.sort_reverse
            else:
                self.sort_column = column_name
                self.sort_reverse = True
            self.loadData()


class SettingsTab(QWidget):
    """设置标签页"""
    
    settingsChanged = Signal()  # 设置改变信号
    
    def __init__(self, db):
        super().__init__()
        self.db = db
        self.setupUI()
        self.loadSettings()
        
    def setupUI(self):
        """设置UI界面"""
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_widget = QWidget()
        layout = QVBoxLayout(scroll_widget)
        layout.setSpacing(15)
        
        # 标题
        title_label = QLabel("⚙️ 剪贴板管理器设置")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #2c3e50;")
        layout.addWidget(title_label)
        
        # 分隔线
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        layout.addWidget(separator)
        
        # 复制限制设置组
        limit_group = QGroupBox("📋 复制限制设置")
        limit_layout = QVBoxLayout(limit_group)
        
        # 无限模式复选框
        self.unlimited_checkbox = QCheckBox("无限模式(无限制)")
        self.unlimited_checkbox.stateChanged.connect(self.onUnlimitedChanged)
        limit_layout.addWidget(self.unlimited_checkbox)
        
        # 大小和数量设置
        size_count_layout = QHBoxLayout()
        
        size_count_layout.addWidget(QLabel("💾 大小:"))
        self.size_spinbox = QSpinBox()
        self.size_spinbox.setRange(1, 10000)
        self.size_spinbox.setSuffix(" MB")
        self.size_spinbox.setMinimumHeight(30)  # 增加高度以便更好地显示按钮
        self.size_spinbox.setStyleSheet("QSpinBox::up-button, QSpinBox::down-button { width: 0px; height: 0px; }")
        size_count_layout.addWidget(self.size_spinbox)
        
        size_count_layout.addSpacing(20)
        
        size_count_layout.addWidget(QLabel("🔢 数量:"))
        self.count_spinbox = QSpinBox()
        self.count_spinbox.setRange(1, 1000)
        self.count_spinbox.setSuffix(" 个")
        self.count_spinbox.setMinimumHeight(30)  # 增加高度以便更好地显示按钮
        self.count_spinbox.setStyleSheet("QSpinBox::up-button, QSpinBox::down-button { width: 0px; height: 0px; }")
        size_count_layout.addWidget(self.count_spinbox)
        
        limit_layout.addLayout(size_count_layout)
        layout.addWidget(limit_group)
        
        # 记录保存设置组
        retention_group = QGroupBox("💾 记录保存设置")
        retention_layout = QVBoxLayout(retention_group)
        
        # 永久保存选项
        self.permanent_radio = QRadioButton("♾️ 永久保存")
        retention_layout.addWidget(self.permanent_radio)
        
        # 自定义天数选项
        custom_layout = QHBoxLayout()
        self.custom_radio = QRadioButton("📆 自定义天数:")
        custom_layout.addWidget(self.custom_radio)
        
        self.days_spinbox = QSpinBox()
        self.days_spinbox.setRange(1, 3650)
        self.days_spinbox.setSuffix(" 天")
        self.days_spinbox.setMinimumHeight(30)  # 增加高度以便更好地显示按钮
        self.days_spinbox.setStyleSheet("QSpinBox::up-button, QSpinBox::down-button { width: 0px; height: 0px; }")
        custom_layout.addWidget(self.days_spinbox)
        
        retention_layout.addLayout(custom_layout)
        
        # 连接单选按钮
        self.permanent_radio.toggled.connect(self.onRetentionChanged)
        self.custom_radio.toggled.connect(self.onRetentionChanged)
        
        layout.addWidget(retention_group)
        
        # 系统设置组
        system_group = QGroupBox("🖥️ 系统设置")
        system_layout = QVBoxLayout(system_group)
        
        # 剪贴板类型保存机制
        type_label = QLabel("📄 剪贴板记录类型")
        type_label.setStyleSheet("font-weight: bold;")
        system_layout.addWidget(type_label)
        
        self.all_types_radio = QRadioButton("📝 记录所有类型（文本和文件）")
        system_layout.addWidget(self.all_types_radio)
        
        self.text_only_radio = QRadioButton("🔤 仅记录纯文本")
        system_layout.addWidget(self.text_only_radio)
        
        # 开机自启设置
        self.autostart_checkbox = QCheckBox("🚀 允许程序开机自启")
        system_layout.addWidget(self.autostart_checkbox)
        
        # 悬浮图标设置
        self.float_icon_checkbox = QCheckBox("📍 启用悬浮图标")
        system_layout.addWidget(self.float_icon_checkbox)
        
        # 悬浮图标透明度设置
        opacity_layout = QHBoxLayout()
        opacity_label = QLabel("👁️ 悬浮图标透明度")
        opacity_label.setStyleSheet("font-weight: bold;")
        opacity_layout.addWidget(opacity_label)
        
        self.opacity_spinbox = QSpinBox()
        self.opacity_spinbox.setRange(5, 100)
        self.opacity_spinbox.setSuffix(" %")
        self.opacity_spinbox.setMinimumHeight(30)  # 增加高度以便更好地显示按钮
        self.opacity_spinbox.setStyleSheet("QSpinBox::up-button, QSpinBox::down-button { width: 0px; height: 0px; }")
        opacity_layout.addWidget(self.opacity_spinbox)
        
        system_layout.addLayout(opacity_layout)
        
        # 悬浮图标说明
        opacity_note = QLabel("💡 悬浮图标大小: 50×50, 可自由拖动, 点击显示页面")
        opacity_note.setStyleSheet("color: #777777; font-size: 12px;")
        system_layout.addWidget(opacity_note)
        
        layout.addWidget(system_group)
        
        # 数据管理组
        data_group = QGroupBox("🗑️ 数据管理")
        data_layout = QVBoxLayout(data_group)
        
        # 重置所有记录
        reset_layout = QHBoxLayout()
        warning_label = QLabel("⚠️ 此操作将删除所有记录和本地缓存文件!")
        warning_label.setStyleSheet("color: #e74c3c;")
        reset_layout.addWidget(warning_label)
        
        self.reset_button = QPushButton("🔄 重置所有记录")
        self.reset_button.setStyleSheet("background-color: #e74c3c; color: white; font-weight: bold;")
        self.reset_button.clicked.connect(self.resetAllRecords)
        reset_layout.addWidget(self.reset_button)
        
        data_layout.addLayout(reset_layout)
        layout.addWidget(data_group)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.save_button = QPushButton("✅ 保存设置")
        self.save_button.setStyleSheet("background-color: #3498db; color: white; font-weight: bold; padding: 8px 20px;")
        self.save_button.clicked.connect(self.saveSettings)
        button_layout.addWidget(self.save_button)
        
        self.reset_button = QPushButton("🔄 恢复默认")
        self.reset_button.setStyleSheet("background-color: #95a5a6; color: white; font-weight: bold; padding: 8px 20px;")
        self.reset_button.clicked.connect(self.resetToDefault)
        button_layout.addWidget(self.reset_button)
        
        layout.addLayout(button_layout)
        layout.addStretch()
        
        scroll_area.setWidget(scroll_widget)
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(scroll_area)
        
    def loadSettings(self):
        """加载设置"""
        settings = self.db.get_settings()
        
        # 更新界面显示
        self.unlimited_checkbox.setChecked(settings['unlimited_mode'])
        max_size_mb = settings['max_copy_size'] / (1024 * 1024)
        self.size_spinbox.setValue(int(max_size_mb))
        self.count_spinbox.setValue(settings['max_copy_count'])
        
        retention_days = settings['retention_days']
        if retention_days == 0:
            self.permanent_radio.setChecked(True)
        else:
            self.custom_radio.setChecked(True)
            self.days_spinbox.setValue(retention_days)
            
        self.days_spinbox.setEnabled(retention_days > 0)
        
        self.autostart_checkbox.setChecked(settings['auto_start'])
        
        # 悬浮图标设置
        if 'float_icon' in settings:
            self.float_icon_checkbox.setChecked(settings['float_icon'])
        else:
            self.float_icon_checkbox.setChecked(True)
            
        # 透明度设置
        if 'opacity' in settings:
            self.opacity_spinbox.setValue(settings['opacity'])
        else:
            self.opacity_spinbox.setValue(15)
            
        # 剪贴板类型设置
        if 'clipboard_type' in settings:
            if settings['clipboard_type'] == 'all':
                self.all_types_radio.setChecked(True)
            else:
                self.text_only_radio.setChecked(True)
        else:
            self.all_types_radio.setChecked(True)
            
        # 更新控件状态
        self.onUnlimitedChanged()
        
    def onUnlimitedChanged(self):
        """无限模式改变事件"""
        enabled = not self.unlimited_checkbox.isChecked()
        self.size_spinbox.setEnabled(enabled)
        self.count_spinbox.setEnabled(enabled)
        
    def onRetentionChanged(self):
        """保存天数改变事件"""
        self.days_spinbox.setEnabled(self.custom_radio.isChecked())
        
    def saveSettings(self):
        """保存设置"""
        try:
            # 获取用户输入
            unlimited_mode = self.unlimited_checkbox.isChecked()
            
            # 如果不是无限模式,获取数值
            if not unlimited_mode:
                max_size_mb = self.size_spinbox.value()
                max_count = self.count_spinbox.value()
                
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
            if self.permanent_radio.isChecked():
                retention_days = 0
            else:
                retention_days = self.days_spinbox.value()
                
            # 保存其他设置
            auto_start = self.autostart_checkbox.isChecked()
            float_icon = self.float_icon_checkbox.isChecked()
            opacity = self.opacity_spinbox.value()
            
            if self.all_types_radio.isChecked():
                clipboard_type = 'all'
            else:
                clipboard_type = 'text_only'
                
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
                
            QMessageBox.information(self, "提示", "设置已保存")
            self.settingsChanged.emit()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存设置时出错: {str(e)}")
            
    def resetToDefault(self):
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
        self.loadSettings()
        QMessageBox.information(self, "提示", "已恢复默认设置")
        self.settingsChanged.emit()
        
    def resetAllRecords(self):
        """重置所有记录"""
        reply = QMessageBox.question(
            self, 
            "确认重置", 
            "此操作将删除所有记录和本地缓存文件!\n\n请输入'确认重置所有记录'以继续:",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                # 删除所有数据库记录
                self.db.clear_all_records()
                
                # 删除所有缓存文件
                clipboard_dir = "clipboard_files"
                if os.path.exists(clipboard_dir):
                    try:
                        shutil.rmtree(clipboard_dir)
                        os.makedirs(clipboard_dir, exist_ok=True)
                    except Exception as e:
                        QMessageBox.warning(self, "警告", f"删除缓存文件时出错: {str(e)}")
                        
                QMessageBox.information(self, "提示", "所有记录已重置")
                self.settingsChanged.emit()
            except Exception as e:
                QMessageBox.critical(self, "错误", f"重置记录时出错: {str(e)}")


class ClipboardManagerGUI(QMainWindow):
    """剪贴板管理器主窗口"""
    
    def __init__(self):
        super().__init__()
        self.db = ClipboardDatabase()
        self.tray_icon = None
        self.is_hidden = False
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.updateRecords)
        self.float_window = None  # 悬浮窗口引用
        self.setupUI()
        self.setupSystemTray()
        self.checkAutoStart()
        self.checkFloatIcon()  # 检查并创建悬浮图标
        
        # 开始定期更新
        self.update_timer.start(2000)  # 每2秒更新一次
        
    def setupUI(self):
        """设置UI界面"""
        self.setWindowTitle("剪贴板历史记录")
        self.setGeometry(100, 100, 800, 500)
        self.setMinimumSize(700, 400)
        
        # 设置窗口样式
        self.setStyleSheet("""
            QMainWindow {
                background: #f0f0f0;
            }
            QTabWidget::pane {
                background: white;
                border: 1px solid #ccc;
            }
            QTabBar::tab {
                background: #e0e0e0;
                border: 1px solid #ccc;
                border-bottom-color: #ccc;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                min-width: 8ex;
                padding: 8px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background: white;
                border-bottom-color: white;
            }
            QTabBar::tab:!selected {
                margin-top: 2px;
            }
            QGroupBox {
                background: white;
                border: 1px solid #ccc;
                border-radius: 4px;
                margin-top: 1ex;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 5px;
                background: #f0f0f0;
            }
            QLineEdit, QSpinBox {
                background: white;
                border: 1px solid #ccc;
                border-radius: 4px;
                padding: 4px;
            }
            QPushButton {
                background: #3498db;
                border: 1px solid #2980b9;
                border-radius: 4px;
                color: white;
                padding: 6px 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #2980b9;
            }
            QPushButton:pressed {
                background: #1c6ea4;
            }
            QCheckBox, QRadioButton {
                background: transparent;
                spacing: 5px;
            }
            QCheckBox::indicator, QRadioButton::indicator {
                width: 16px;
                height: 16px;
            }
            QCheckBox::indicator:unchecked, QRadioButton::indicator:unchecked {
                border: 1px solid #ccc;
                background: white;
            }
            QCheckBox::indicator:checked, QRadioButton::indicator:checked {
                border: 1px solid #3498db;
                background: #3498db;
            }
            QRadioButton::indicator {
                border-radius: 8px;
            }
            QRadioButton::indicator:checked {
                border-radius: 8px;
            }
            QLabel {
                background: transparent;
            }
            QHeaderView::section {
                background: #f0f0f0;
                border: 1px solid #ccc;
                padding: 4px;
                font-weight: bold;
            }
            QTreeView {
                background: white;
                alternate-background-color: #f9f9f9;
                border: 1px solid #ccc;
            }
            QTreeView::item:selected {
                background: #3498db;
                color: white;
            }
            QScrollBar:vertical {
                background: #f0f0f0;
                width: 15px;
                border-radius: 4px;
                margin: 4px 0px 4px 0px;
            }
            QScrollBar::handle:vertical {
                background: #c0c0c0;
                border-radius: 4px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: #a0a0a0;
            }
        """)
        
        # 设置窗口图标
        try:
            icon_path = resource_path("mini.ico")
            if os.path.exists(icon_path):
                self.setWindowIcon(QIcon(icon_path))
        except Exception as e:
            print(f"设置窗口图标失败: {e}")
            
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建标签页
        self.tab_widget = QTabWidget()
        self.records_tab = RecordsTab(self.db)
        self.settings_tab = SettingsTab(self.db)
        
        self.tab_widget.addTab(self.records_tab, "记录(L)")
        self.tab_widget.addTab(self.settings_tab, "设置(S)")
        
        # 连接信号
        self.records_tab.recordDoubleClicked.connect(self.copyRecordToClipboard)
        self.settings_tab.settingsChanged.connect(self.onSettingsChanged)
        
        # 布局
        layout = QVBoxLayout(central_widget)
        layout.addWidget(self.tab_widget)
        
    def setupSystemTray(self):
        """设置系统托盘"""
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray_icon = QSystemTrayIcon(self)
            
            # 设置图标
            try:
                icon_path = resource_path("mini.ico")
                if os.path.exists(icon_path):
                    self.tray_icon.setIcon(QIcon(icon_path))
                else:
                    # 创建一个简单的图标
                    pixmap = QPixmap(64, 64)
                    pixmap.fill(Qt.blue)
                    self.tray_icon.setIcon(QIcon(pixmap))
            except Exception as e:
                print(f"创建系统托盘图标失败: {e}")
                
            # 创建菜单
            tray_menu = QMenu()
            show_action = QAction("显示界面", self)
            show_action.triggered.connect(self.showWindow)
            tray_menu.addAction(show_action)
            
            quit_action = QAction("退出", self)
            quit_action.triggered.connect(self.quitApplication)
            tray_menu.addAction(quit_action)
            
            self.tray_icon.setContextMenu(tray_menu)
            self.tray_icon.activated.connect(self.onTrayIconActivated)
            self.tray_icon.show()
            
    def onTrayIconActivated(self, reason):
        """托盘图标激活事件"""
        if reason == QSystemTrayIcon.Trigger:
            self.toggleWindow()
            
    def checkAutoStart(self):
        """检查并应用开机自启设置"""
        try:
            settings = self.db.get_settings()
            if settings['auto_start']:
                self.setAutoStart(True)
        except Exception as e:
            print(f"检查开机自启设置时出错: {e}")
            
    def setAutoStart(self, enable):
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
                    # 如果值不存在,忽略错误
                    pass
        except Exception as e:
            print(f"设置开机自启时出错: {e}")
            
    def checkFloatIcon(self):
        """检查并根据设置创建悬浮图标"""
        try:
            settings = self.db.get_settings()
            if settings['float_icon']:
                self.createFloatIcon()
        except Exception as e:
            print(f"检查悬浮图标设置时出错: {e}")
            
    def createFloatIcon(self):
        """创建悬浮图标"""
        # 如果悬浮图标已经存在,先销毁
        self.destroyFloatIcon()
        
        # 获取设置中的透明度值
        settings = self.db.get_settings()
        opacity = settings.get('opacity', 30)  # 默认30%，比之前更不透明
        # 将百分比转换为0-1之间的值
        alpha = opacity / 100.0
        
        # 创建悬浮窗口
        from PySide6.QtWidgets import QLabel, QWidget
        from PySide6.QtCore import Qt
        self.float_window = QWidget()
        self.float_window.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.float_window.setAttribute(Qt.WA_TranslucentBackground)
        self.float_window.setFixedSize(60, 60)  # 稍大一些的窗口容纳背景
        
        # 设置背景样式（在窗口上添加一个背景层）
        self.background_label = QLabel(self.float_window)
        self.background_label.setGeometry(5, 5, 50, 50)  # 稍微偏移，创造一种浮动感
        self.background_label.setStyleSheet(f"""
            background-color: rgba(30, 144, 255, {alpha * 0.7});  /* 道奇蓝，稍微透明一些 */
            border: 1px solid rgba(0, 191, 255, {alpha});
            border-radius: 25px;
        """)
        
        # 设置圆形主图标
        self.icon_label = QLabel("C", self.float_window)
        self.icon_label.setGeometry(5, 5, 50, 50)
        self.icon_label.setStyleSheet(f"""
            background-color: rgba(30, 144, 255, {alpha});  /* 道奇蓝 */
            border: 2px solid rgba(0, 191, 255, {alpha});   /* 深天蓝 */
            border-radius: 25px;
            color: white;
            font-size: 24px;
            font-weight: bold;
        """)
        self.icon_label.setAlignment(Qt.AlignCenter)
        
        # 获取屏幕尺寸
        screens = QApplication.screens()
        if screens:
            screen = screens[0].geometry()
            screen_width = screen.width()
            screen_height = screen.height()
        else:
            # 默认屏幕尺寸
            screen_width = 1920
            screen_height = 1080
        
        # 设置默认位置为右上角(距离右边60像素, 距离顶部120像素)
        x = screen_width - 60 - 60  # 距离右边60像素
        y = 120  # 距离顶部120像素
        self.float_window.move(x, y)
        
        # 绑定鼠标事件到整个窗口
        self.float_window.enterEvent = self.onFloatIconEnter
        self.float_window.leaveEvent = self.onFloatIconLeave
        self.float_window.mousePressEvent = self.startMoveFloatIcon
        self.float_window.mouseMoveEvent = self.moveFloatIcon
        self.float_window.mouseReleaseEvent = self.handleFloatIconClick
        self.float_window.mouseDoubleClickEvent = self.showMainWindowFromFloatIcon
        
        # 记录鼠标位置
        self.float_icon_pos = QPoint(0, 0)
        
        # 悬浮面板引用
        self.float_panel = None
        self.hide_panel_timer = None  # 隐藏面板的定时器
        
        # 显示悬浮图标
        self.float_window.show()
        
    def onFloatIconEnter(self, event):
        """鼠标进入悬浮图标区域"""
        # 如果有隐藏面板的定时器，取消它
        if self.hide_panel_timer and self.hide_panel_timer.isActive():
            self.hide_panel_timer.stop()
        self.showFloatPanel()
        
    def onFloatIconLeave(self, event):
        """鼠标离开悬浮图标区域"""
        # 添加延迟隐藏，防止鼠标移动到面板上时立即消失
        self.scheduleHideFloatPanel()
        
    def scheduleHideFloatPanel(self):
        """安排隐藏悬浮面板"""
        if self.hide_panel_timer is None:
            self.hide_panel_timer = QTimer()
            self.hide_panel_timer.setSingleShot(True)
            self.hide_panel_timer.timeout.connect(self.checkAndHideFloatPanel)
        self.hide_panel_timer.start(300)  # 300毫秒延迟隐藏
        
    def checkAndHideFloatPanel(self):
        """检查并隐藏悬浮面板"""
        # 只有当面板存在且鼠标不在面板上时才隐藏
        if self.float_panel:
            self.hideFloatPanel()
            
    def showFloatPanel(self):
        """显示最近记录悬浮面板"""
        # 销毁已存在的面板
        self.hideFloatPanel()
        
        # 获取最近5条记录
        text_records = self.db.get_text_records(5)
        file_records = self.db.get_file_records(5)
        
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
        
        # 只取前5条
        all_records = all_records[:5]
        
        if not all_records:
            return  # 没有记录则不显示面板
            
        # 创建悬浮面板
        from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QFrame
        self.float_panel = QWidget()
        self.float_panel.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.float_panel.setAttribute(Qt.WA_TranslucentBackground)
        self.float_panel.setStyleSheet("""
            QWidget {
                background-color: rgba(255, 255, 255, 0.95);
                border: 1px solid rgba(0, 0, 0, 0.1);
                border-radius: 10px;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
            }
        """)
        
        # 标题栏
        title_bar = QFrame()
        title_bar.setStyleSheet("""
            QFrame {
                background-color: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1, stop: 0 #4A90E2, stop: 1 #1C5FAF);
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
                border: none;
            }
        """)
        title_bar.setFixedHeight(35)
        title_label = QLabel("📋 剪贴板历史")
        title_label.setStyleSheet("""
            QLabel {
                color: white;
                font-weight: bold;
                font-size: 12px;
                background: transparent;
            }
        """)
        title_label.setAlignment(Qt.AlignCenter)
        
        title_layout = QHBoxLayout(title_bar)
        title_layout.addWidget(title_label)
        title_layout.setContentsMargins(0, 0, 0, 0)
        
        # 内容区域
        content_layout = QVBoxLayout()
        content_layout.setSpacing(3)
        content_layout.setContentsMargins(8, 8, 8, 8)
        
        # 添加记录项
        for record_type, content, timestamp, record_id in all_records:
            item_widget = QFrame()
            item_widget.setStyleSheet("""
                QFrame {
                    background-color: rgba(255, 255, 255, 0.8);
                    border: 1px solid rgba(0, 0, 0, 0.05);
                    border-radius: 6px;
                }
                QFrame:hover {
                    background-color: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1, stop: 0 #E3F2FD, stop: 1 #BBDEFB);
                    border: 1px solid rgba(74, 144, 226, 0.3);
                }
            """)
            item_widget.setFixedHeight(45)
            
            item_layout = QHBoxLayout(item_widget)
            item_layout.setContentsMargins(10, 5, 10, 5)
            
            # 内容预览
            preview = content[:35] + "..." if len(content) > 35 else content
            content_label = QLabel(preview)
            content_label.setStyleSheet("""
                QLabel {
                    color: #333;
                    font-size: 11px;
                    background: transparent;
                }
            """)
            
            # 类型图标
            type_icon = "📝" if record_type == "text" else "📁"
            type_label = QLabel(type_icon)
            type_label.setStyleSheet("""
                QLabel {
                    font-size: 14px;
                    background: transparent;
                }
            """)
            
            item_layout.addWidget(type_label)
            item_layout.addWidget(content_label)
            item_layout.addStretch()
            
            content_layout.addWidget(item_widget)
            
            # 绑定点击事件
            item_widget.mousePressEvent = lambda e, rt=record_type, rid=record_id: self.copyRecordFromFloatPanel(rt, rid)
        
        # 主布局
        main_layout = QVBoxLayout(self.float_panel)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addWidget(title_bar)
        main_layout.addLayout(content_layout)
        
        # 设置面板位置（在悬浮图标旁边）
        icon_pos = self.float_window.pos()
        panel_x = icon_pos.x() - 210  # 在图标左侧，留出一些间隙
        panel_y = icon_pos.y()
        self.float_panel.move(panel_x, panel_y)
        self.float_panel.setFixedSize(220, 35 + len(all_records) * 51)  # 标题栏+记录项高度
        
        # 绑定面板的鼠标事件
        self.float_panel.enterEvent = self.onFloatPanelEnter
        self.float_panel.leaveEvent = self.onFloatPanelLeave
        
        # 显示面板
        self.float_panel.show()
        
    def onFloatPanelEnter(self, event):
        """鼠标进入悬浮面板"""
        # 如果有隐藏面板的定时器，取消它
        if self.hide_panel_timer and self.hide_panel_timer.isActive():
            self.hide_panel_timer.stop()
        
    def onFloatPanelLeave(self, event):
        """鼠标离开悬浮面板"""
        self.scheduleHideFloatPanel()
        
    def hideFloatPanel(self):
        """隐藏悬浮面板"""
        if self.float_panel:
            self.float_panel.close()
            self.float_panel = None
        # 停止隐藏面板的定时器
        if self.hide_panel_timer and self.hide_panel_timer.isActive():
            self.hide_panel_timer.stop()
        
    def copyRecordFromFloatPanel(self, record_type, record_id):
        """从悬浮面板复制记录"""
        clipboard = QApplication.clipboard()
        
        if record_type == "text":
            # 从数据库获取完整文本内容
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT content FROM text_records WHERE id = ?', (record_id,))
            result = cursor.fetchone()
            conn.close()
            
            if result:
                full_text = result[0]
                clipboard.setText(full_text)
        else:
            # 对于文件类型，复制文件名
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT filename FROM file_records WHERE id = ?', (record_id,))
            result = cursor.fetchone()
            conn.close()
            
            if result:
                filename = result[0]
                clipboard.setText(filename)
                
        # 隐藏面板
        self.hideFloatPanel()
        
    def startMoveFloatIcon(self, event):
        """开始移动悬浮图标"""
        self.float_icon_pos = event.pos()
        
    def moveFloatIcon(self, event):
        """移动悬浮图标"""
        if event.buttons() == Qt.LeftButton:
            # 计算新位置
            new_pos = self.float_window.pos() + event.pos() - self.float_icon_pos
            
            # 获取屏幕尺寸
            screens = QApplication.screens()
            if screens:
                screen = screens[0].geometry()
                screen_width = screen.width()
                screen_height = screen.height()
            else:
                # 默认屏幕尺寸
                screen_width = 1920
                screen_height = 1080
            
            # 边界检查
            if new_pos.x() < 0:
                new_pos.setX(0)
            elif new_pos.x() + self.float_window.width() > screen_width:
                new_pos.setX(screen_width - self.float_window.width())
                
            if new_pos.y() < 0:
                new_pos.setY(0)
            elif new_pos.y() + self.float_window.height() > screen_height:
                new_pos.setY(screen_height - self.float_window.height())
                
            # 移动图标
            self.float_window.move(new_pos)
            
    def handleFloatIconClick(self, event):
        """处理悬浮图标点击事件"""
        # 检查是否是点击而不是拖动
        if abs(event.pos().x() - self.float_icon_pos.x()) < 5 and abs(event.pos().y() - self.float_icon_pos.y()) < 5:
            # 显示主窗口
            self.showWindow()
            
    def showMainWindowFromFloatIcon(self, event):
        """双击悬浮图标显示主窗口"""
        self.showWindow()
        
    def destroyFloatIcon(self):
        """销毁悬浮图标"""
        if self.float_window:
            self.float_window.close()
            self.float_window = None
            
    def copyRecordToClipboard(self, record_type, record_id):
        """复制记录到剪贴板"""
        clipboard = QApplication.clipboard()
        
        if record_type == "text":
            # 从数据库获取完整文本内容
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT content FROM text_records WHERE id = ?', (record_id,))
            result = cursor.fetchone()
            conn.close()
            
            if result:
                full_text = result[0]
                clipboard.setText(full_text)
                
                # 显示提示信息
                display_text = full_text[:20] + "..." if len(full_text) > 20 else full_text
                self.statusBar().showMessage(f'已复制："{display_text}"', 3000)
        else:
            # 对于文件类型，复制文件名
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT filename FROM file_records WHERE id = ?', (record_id,))
            result = cursor.fetchone()
            conn.close()
            
            if result:
                filename = result[0]
                clipboard.setText(filename)
                
                # 显示提示信息
                display_text = filename[:20] + "..." if len(filename) > 20 else filename
                self.statusBar().showMessage(f'已复制文件名："{display_text}"', 3000)
                
    def updateRecords(self):
        """更新记录显示"""
        self.records_tab.loadData()
        
    def onSettingsChanged(self):
        """设置改变事件"""
        # 检查并处理悬浮图标设置
        try:
            settings = self.db.get_settings()
            if settings['float_icon']:
                self.createFloatIcon()
            else:
                self.destroyFloatIcon()
        except Exception as e:
            print(f"处理悬浮图标设置时出错: {e}")
        
    def hideWindow(self):
        """隐藏窗口"""
        self.hide()
        self.is_hidden = True
        
    def showWindow(self):
        """显示窗口"""
        self.show()
        self.raise_()
        self.activateWindow()
        self.is_hidden = False
        self.records_tab.loadData()
        
    def toggleWindow(self):
        """切换窗口显示状态"""
        if self.is_hidden:
            self.showWindow()
        else:
            self.hideWindow()
            
    def quitApplication(self):
        """退出应用程序"""
        self.update_timer.stop()
        if self.tray_icon:
            self.tray_icon.hide()
        QApplication.quit()


def main():
    """主函数"""
    app = QApplication(sys.argv)
    
    # 启用高DPI缩放
    app.setAttribute(Qt.AA_EnableHighDpiScaling)
    app.setAttribute(Qt.AA_UseHighDpiPixmaps)
    
    # 设置应用程序信息
    app.setApplicationName("剪贴板管理器")
    app.setApplicationVersion("1.0")
    
    # 创建并显示主窗口
    window = ClipboardManagerGUI()
    window.show()
    
    # 运行应用程序
    sys.exit(app.exec())


if __name__ == "__main__":
    main()