# 剪贴板管理器

![GitHub](https://img.shields.io/badge/license-MIT-blue.svg)
![Platform](https://img.shields.io/badge/platform-Windows-blue.svg)
![Version](https://img.shields.io/badge/version-1.1.0-brightgreen.svg)

## 📋 项目简介

剪贴板管理器是一个功能强大的Windows平台剪贴板历史记录工具，能够监控、保存和管理您的剪贴板内容。它可以自动记录您复制的文本和文件，并提供便捷的查询界面来查看和管理历史记录。

### 主要功能

1. **实时监控剪贴板变化** - 自动检测您复制的文本和文件
2. **智能保存内容** - 文本直接保存到数据库，文件保存到分类文件夹并计算MD5
3. **内容去重机制** - 避免重复保存相同MD5的文件或相同内容的文本
4. **图形化查询界面** - 提供直观的GUI界面查询历史记录
5. **系统托盘运行** - 默认在系统托盘后台运行，节省系统资源
6. **文件分类管理** - 根据文件扩展名自动分类保存（文档、图片、视频等）
7. **复制限制控制** - 支持设置复制文件的数量和大小限制

## 🖼️ 界面预览

### 主界面

![主界面](screenshots/main_interface.png)
*主界面展示文本和文件记录*

### 设置界面

![设置界面](screenshots/settings_interface.png)
*设置界面可配置复制限制、保存天数等参数*

### 搜索功能

![搜索功能](screenshots/search_function.png)
*支持按关键词搜索历史记录*

## 🚀 快速开始

### 环境要求

- Windows 7/8/10/11 操作系统
- Python 3.6+ (源码运行)
- 或直接运行打包好的exe文件（无需Python环境）

### 安装方式

#### 方式一：直接运行（推荐）

下载打包好的exe文件，直接运行即可：

1. 下载最新版本的 `剪贴板管理器.exe`
2. 双击运行程序
3. 程序将在系统托盘运行，点击托盘图标可打开界面

#### 方式二：源码运行

```
# 克隆项目
git clone https://github.com/your-username/clipboard-manager.git
cd clipboard-manager

# 安装依赖
pip install -r requirements.txt

# 运行程序
python run_clipboard_manager.py
```

#### 方式三：自行打包

```
# 安装打包工具
pip install cx_Freeze

# 执行打包脚本
python build_exe.py build
```

## 📖 使用说明

### 基本操作

1. **启动程序** - 程序启动后默认在系统托盘运行
2. **查看历史** - 点击系统托盘图标打开主界面
3. **搜索记录** - 在搜索框中输入关键词进行搜索
4. **复制内容** - 双击记录或使用右键菜单复制内容
5. **删除记录** - 选中记录后按Delete键或使用右键菜单删除

### 使用示例

#### 示例1：监控文本复制
1. 运行剪贴板管理器
2. 在任意应用程序中复制一段文本
3. 程序会自动检测并保存该文本
4. 点击系统托盘图标查看历史记录

#### 示例2：文件复制管理
1. 复制一个或多个文件
2. 程序会自动保存文件到分类目录
3. 在文件记录标签页中查看复制的文件
4. 右键点击文件记录可打开文件所在位置

#### 示例3：设置复制限制
1. 打开设置标签页
2. 设置最大复制文件数量（如10个）
3. 设置最大复制总大小（如100MB）
4. 启用无限模式可取消所有限制

### 功能特性

#### 文本记录管理
- 自动保存复制的文本内容
- 显示文本字符数
- 支持全文本查看和复制

#### 文件记录管理
- 自动保存复制的文件
- 按文件类型分类保存（文档、图片、视频等）
- 记录文件大小、MD5值等信息
- 支持打开文件所在位置

#### 设置功能
- **复制限制**：设置单次复制文件的数量和大小限制
- **保存天数**：设置历史记录保留天数
- **开机自启**：设置程序开机自动启动
- **悬浮图标**：在桌面显示悬浮图标方便快速访问

## ⚙️ 技术架构

### 核心组件

- **剪贴板监控** - 使用win32clipboard库监控剪贴板变化
- **数据存储** - SQLite数据库存储文本记录和文件元信息
- **GUI界面** - tkinter构建的图形用户界面
- **系统托盘** - pystray实现系统托盘图标功能

### 项目结构

```
clipboard_manager/
├── clipboard_manager_main.py    # 主程序入口和核心逻辑
├── clipboard_gui.py             # GUI界面实现
├── clipboard_db.py              # 数据库操作模块
├── clipboard_content_detector.py # 剪贴板内容检测工具
├── run_clipboard_manager.py     # 程序启动脚本
├── build_exe.py                 # 打包脚本
├── setup.py                     # 安装配置
└── clipboard_history.db         # SQLite数据库文件
```

## 🔧 配置说明

### 数据库路径

程序会按照以下优先级选择数据库存储位置：
1. 程序所在目录
2. 用户数据目录
3. AppData目录
4. 临时目录

### 文件保存路径

复制的文件将保存在 `clipboard_files` 文件夹中，按日期和文件类型分类：
```
clipboard_files/
├── images/
│   └── 2023-12-01/
├── documents/
├── videos/
└── others/
```

## 🛠️ 开发指南

### 依赖库

- `tkinter` - GUI界面
- `sqlite3` - 数据库操作
- `win32clipboard` - 剪贴板访问
- `PIL/pystray` - 系统托盘图标
- `hashlib` - MD5计算

### 打包发布

使用cx_Freeze进行打包：

```
python build_exe.py build
```

### 生成截图

为了更好地展示程序功能，建议在README中添加实际运行界面截图：

1. 运行程序并执行各种操作
2. 截取主界面、设置界面、搜索界面等关键功能截图
3. 将截图保存到`screenshots`目录中
4. 在README中引用这些截图

## 📄 许可证

本项目采用MIT许可证，详情请见 [LICENSE](LICENSE) 文件。

## 🤝 贡献

欢迎提交Issue和Pull Request来改进这个项目。

## 🙏 致谢

- 感谢所有开源库的贡献者
- 特别感谢pystray和Pillow库提供的系统托盘功能

## 📞 联系方式

如有任何问题或建议，请通过以下方式联系：

- 提交Issue
- 发送邮件至 clipboard.manager@example.com
- 项目地址: https://github.com/your-username/clipboard-manager