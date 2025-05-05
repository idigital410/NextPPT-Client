import sys
import os
import json
import requests
import threading
import subprocess
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QListWidgetItem, QLabel, QScrollArea, QStackedWidget,
                             QGridLayout, QFrame, QProgressBar, QMessageBox, QFileDialog,
                             QDialog, QPushButton, QComboBox)
from PyQt5.QtCore import Qt, QSize, QThread, pyqtSignal, QUrl, QRect, QTimer, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import QIcon, QPixmap, QFont, QDesktopServices, QFontDatabase

# 导入QFluentWidgets库
from qfluentwidgets import (FluentWindow, NavigationInterface, NavigationItemPosition, 
                           ScrollArea, PushButton, ProgressBar, ListWidget, MessageBox,
                           FluentIcon, setTheme, Theme, isDarkTheme, FluentStyleSheet,
                           CardWidget, BodyLabel, CaptionLabel, StrongBodyLabel, TitleLabel,
                           FlowLayout, SmoothScrollArea, SubtitleLabel, TransparentPushButton)

# 服务器地址
SERVER_URL = ""

# 下载配置
DOWNLOAD_THREADS = 32
DOWNLOAD_DIR = "D:/NextPPT" if os.path.exists("D:/") else "C:/NextPPT"

# 确保下载目录存在
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

# 确保下载记录文件存在
DOWNLOAD_RECORD_FILE = os.path.join(DOWNLOAD_DIR, "Download.json")
# 确保下载目录存在
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)
# 确保下载记录文件存在
if not os.path.exists(DOWNLOAD_RECORD_FILE):
    with open(DOWNLOAD_RECORD_FILE, "w", encoding="utf-8") as f:
        json.dump([], f)

# 下载线程类
class DownloadThread(QThread):
    progress_signal = pyqtSignal(int, int)  # 当前进度, 总大小
    complete_signal = pyqtSignal(str)  # 下载完成的文件路径
    error_signal = pyqtSignal(str)  # 错误信息
    
    def __init__(self, url, save_path, start_byte, end_byte, thread_id):
        super().__init__()
        self.url = url
        self.save_path = save_path
        self.start_byte = start_byte
        self.end_byte = end_byte
        self.thread_id = thread_id
        
    def run(self):
        try:
            headers = {"Range": f"bytes={self.start_byte}-{self.end_byte}"}
            response = requests.get(self.url, headers=headers, stream=True)
            
            # 计算当前线程需要下载的总大小
            total_size = self.end_byte - self.start_byte + 1
            downloaded = 0
            
            # 创建临时文件
            temp_file = f"{self.save_path}.part{self.thread_id}"
            with open(temp_file, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        self.progress_signal.emit(downloaded, total_size)
            
            self.complete_signal.emit(temp_file)
        except Exception as e:
            self.error_signal.emit(str(e))

# 下载管理器类
class DownloadManager(QThread):
    progress_signal = pyqtSignal(int, int)  # 当前进度, 总大小
    complete_signal = pyqtSignal(str)  # 下载完成的文件路径
    error_signal = pyqtSignal(str)  # 错误信息
    
    def __init__(self, url, save_path, material_id, material_title):
        super().__init__()
        self.url = url
        self.save_path = save_path
        self.material_id = material_id
        self.material_title = material_title
        self.threads = []
        self.completed_parts = []
        self.total_size = 0
        self.downloaded = 0
        
    def run(self):
        try:
            # 获取文件大小
            response = requests.head(self.url)
            self.total_size = int(response.headers.get("Content-Length", 0))
            
            if self.total_size == 0:
                self.error_signal.emit("无法获取文件大小")
                return
            
            # 计算每个线程下载的大小
            part_size = self.total_size // DOWNLOAD_THREADS
            
            # 创建并启动下载线程
            for i in range(DOWNLOAD_THREADS):
                start_byte = i * part_size
                end_byte = (i + 1) * part_size - 1 if i < DOWNLOAD_THREADS - 1 else self.total_size - 1
                
                thread = DownloadThread(self.url, self.save_path, start_byte, end_byte, i)
                thread.progress_signal.connect(self.update_progress)
                thread.complete_signal.connect(self.part_completed)
                thread.error_signal.connect(self.thread_error)
                
                self.threads.append(thread)
                thread.start()
        except Exception as e:
            self.error_signal.emit(str(e))
    
    def update_progress(self, part_progress, part_total):
        # 这里不应该累加part_progress，因为part_progress是当前已下载的总量，而不是增量
        # 修改为直接发送当前线程的进度，让DownloadDialog处理总进度的计算
        self.progress_signal.emit(part_progress, part_total)
    
    def part_completed(self, temp_file):
        self.completed_parts.append(temp_file)
        
        # 检查是否所有部分都已下载完成
        if len(self.completed_parts) == DOWNLOAD_THREADS:
            self.merge_parts()
    
    def thread_error(self, error):
        self.error_signal.emit(error)
    
    def merge_parts(self):
        try:
            # 按照线程ID排序
            self.completed_parts.sort(key=lambda x: int(x.split("part")[1]))
            
            # 合并文件
            with open(self.save_path, "wb") as outfile:
                for part in self.completed_parts:
                    with open(part, "rb") as infile:
                        outfile.write(infile.read())
            
            # 删除临时文件
            for part in self.completed_parts:
                os.remove(part)
            
            # 更新下载记录
            self.update_download_record()
            
            # 发送完成信号
            self.complete_signal.emit(self.save_path)
        except Exception as e:
            self.error_signal.emit(str(e))
    
    def update_download_record(self):
        try:
            # 读取现有记录
            with open(DOWNLOAD_RECORD_FILE, "r", encoding="utf-8") as f:
                records = json.load(f)
            
            # 添加新记录
            records.append({
                "id": self.material_id,
                "title": self.material_title,
                "path": self.save_path,
                "date": self.get_current_date()
            })
            
            # 保存记录
            with open(DOWNLOAD_RECORD_FILE, "w", encoding="utf-8") as f:
                json.dump(records, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"更新下载记录失败: {e}")
    
    def get_current_date(self):
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# 课件卡片组件
class MaterialCard(CardWidget):
    def __init__(self, material, parent=None):
        super().__init__(parent)
        self.material = material
        self.downloaded = False
        # 设置卡片大小，可根据窗口大小自动调整
        self.setMinimumSize(350, 180)  # 设置更宽的卡片宽度
        self.setMaximumWidth(400)
        self.setup_ui()
        self.check_if_downloaded()
        # 添加飞入动画效果
        self.setup_animation()
    
    def setup_animation(self):
        # 创建卡片的飞入动画效果
        self.animation = QPropertyAnimation(self, b"geometry")
        self.animation.setDuration(500)  # 持续时间500毫秒
        screen_geometry = self.screen().availableGeometry()
        start_y = screen_geometry.bottom() + 500  # 起始位置在屏幕下方500像素
        end_y = (screen_geometry.height() - self.height()) // 2  # 屏幕垂直居中
        self.animation.setStartValue(QRect(
            (screen_geometry.width() - self.width()) // 2,
            start_y,
            self.width(),
            self.height()
        ))
        self.animation.setEndValue(QRect(
            (screen_geometry.width() - self.width()) // 2,
            end_y,
            self.width(),
            self.height()
        ))
        self.animation.setEasingCurve(QEasingCurve.InOutCirc)  # 使用InOutCirc缓动曲线
        self.animation.start()
    
    def showEvent(self, event):
        super().showEvent(event)
        # 获取当前几何信息
        current_geometry = self.geometry()
        
        # 设置起始位置（从下方飞入）
        start_geometry = QRect(
            current_geometry.x(), 
            current_geometry.y() + 500,  # 从下方500像素处开始
            current_geometry.width(), 
            current_geometry.height()
        )
        
        # 设置结束位置（当前位置）
        self.animation.setStartValue(start_geometry)
        self.animation.setEndValue(current_geometry)
        
        # 设置缓动曲线，使动画更平滑
        self.animation.setEasingCurve(QEasingCurve.InOutCirc)  # 使用与cw程序相同的缓动曲线
        
        # 启动动画
        self.animation.start()
    
    def setup_ui(self):
        # 创建布局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)
        
        # 顶部布局（标题和科目标签）
        top_layout = QHBoxLayout()
        top_layout.setSpacing(10)
        
        # 标题
        title_label = StrongBodyLabel(self.material["title"])
        title_label.setWordWrap(True)
        title_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        
        # 科目标签 - 使用Fluent样式
        category_layout = QHBoxLayout()
        category_layout.setContentsMargins(6, 2, 6, 2)
        category_layout.setSpacing(4)
        
        category_widget = QWidget()
        category_widget.setObjectName("categoryWidget")
        category_widget.setStyleSheet("""
            #categoryWidget {
                background-color: #e1f5fe;
                border-radius: 4px;
            }
        """)
        
        category_label = CaptionLabel(self.material["category"])
        category_label.setStyleSheet("color: #0277bd;")
        category_layout.addWidget(category_label)
        category_widget.setLayout(category_layout)
        category_widget.setFixedHeight(22)
        
        top_layout.addWidget(title_label, 1)  # 1表示伸展因子
        top_layout.addWidget(category_widget, 0)  # 0表示不伸展
        layout.addLayout(top_layout)
        
        # 副标题（使用description作为副标题）
        if "description" in self.material and self.material["description"]:
            subtitle_label = BodyLabel(self.material["description"])
            subtitle_label.setWordWrap(True)
            layout.addWidget(subtitle_label)
        
        # 添加弹性空间
        layout.addStretch(1)
        
        # 底部信息和下载按钮
        bottom_layout = QHBoxLayout()
        
        # 文件大小和日期信息
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        
        # 文件大小
        size_label = CaptionLabel(self.format_size(self.material["fileSize"]))
        info_layout.addWidget(size_label)
        
        # 日期
        date_label = CaptionLabel(self.material["uploadDate"])
        info_layout.addWidget(date_label)
        
        bottom_layout.addLayout(info_layout)
        bottom_layout.addStretch(1)  # 添加弹性空间
        
        # 下载按钮 - 使用Fluent样式按钮
        self.download_btn = PushButton("下载文件")
        self.download_btn.setFixedWidth(120)  # 增加按钮宽度
        self.download_btn.clicked.connect(self.download_material)
        # 设置按钮样式，与图片中一致
        self.download_btn.setStyleSheet("""
            PushButton {
                border: 1px solid #0078d4;
                border-radius: 4px;
                padding: 5px 10px;
                background-color: #ffffff;
                color: #0078d4;
            }
            PushButton:hover {
                background-color: #e6f7ff;
            }
        """)
        bottom_layout.addWidget(self.download_btn)
        
        layout.addLayout(bottom_layout)
        
        # 进度条 - 使用Fluent样式进度条
        self.progress_bar = ProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setFixedHeight(6)  # 设置进度条高度
        layout.addWidget(self.progress_bar)
        
    def format_size(self, size_in_bytes):
        # 转换文件大小为可读格式
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_in_bytes < 1024.0:
                return f"{size_in_bytes:.2f} {unit}"
            size_in_bytes /= 1024.0
        return f"{size_in_bytes:.2f} TB"
    
    def check_if_downloaded(self):
        """检查课件是否已下载"""
        try:
            # 读取下载记录
            with open(DOWNLOAD_RECORD_FILE, "r", encoding="utf-8") as f:
                records = json.load(f)
            
            # 检查当前课件是否已下载
            for record in records:
                if record["id"] == self.material["id"]:
                    self.download_btn.setText("打开文件")
                    # 不使用图标，避免重叠问题
                    # 更新按钮样式，与图片中一致
                    self.download_btn.setStyleSheet("""
                        PushButton {
                            border: 1px solid #0078d4;
                            border-radius: 4px;
                            padding: 5px 10px;
                            background-color: #e6f7ff;
                            color: #0078d4;
                        }
                        PushButton:hover {
                            background-color: #cce9ff;
                        }
                    """)
                    self.download_btn.clicked.disconnect()
                    self.download_btn.clicked.connect(lambda: self.open_file(record["path"]))
                    return
        except Exception as e:
            print(f"检查下载记录失败: {e}")
    
    def download_material(self):
        file_url = f"{SERVER_URL}{self.material['fileUrl']}"
        file_name = os.path.basename(self.material["fileUrl"])
        save_path = os.path.join(DOWNLOAD_DIR, file_name)
    
        self.download_manager = DownloadManager(file_url, save_path, 
                                          self.material["id"], self.material["title"])
        
        self.download_dialog = DownloadDialog(self.material["title"], file_name, self)
        # 设置下载对话框的下载管理器引用，确保能够正确计算进度
        self.download_dialog.download_manager = self.download_manager
        self.download_dialog.show()
        
        # 连接信号
        self.download_manager.progress_signal.connect(self.download_dialog.update_progress)
        self.download_manager.complete_signal.connect(self.download_completed)
        self.download_manager.error_signal.connect(self.download_dialog.download_error)
        
        # 开始下载
        self.download_btn.setEnabled(False)
        self.download_btn.setText("下载中...")
        self.download_manager.start()
    
    # 下载弹窗类
class DownloadDialog(QDialog):
    def __init__(self, title, filename, parent=None):
        super().__init__(parent)
        self.setWindowTitle("文件下载")
        self.resize(400, 200)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setWindowModality(Qt.WindowModal)
        
        # 禁用动画效果
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        self.setAttribute(Qt.WA_NoSystemBackground, False)
        
        # 创建布局
        layout = QVBoxLayout(self)
        
        # 文件信息
        info_label = QLabel(f"正在下载: {title}")
        layout.addWidget(info_label)
        
        filename_label = QLabel(f"文件名: {filename}")
        layout.addWidget(filename_label)
        
        # 进度条
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)
        
        # 下载信息
        self.info_label = QLabel("准备下载...")
        layout.addWidget(self.info_label)
        
        # 初始化变量，确保它们在类实例中存在
        self.download_start_time = None
        self.last_update_time = None
        self.last_downloaded = 0
        
        # 用于跟踪每个线程的下载进度
        self.thread_progress = {}
        
        # 下载管理器引用
        self.download_manager = None
        
        # 取消按钮
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)
        layout.addWidget(self.cancel_btn, alignment=Qt.AlignRight)
    
    def update_progress(self, current, total):
        # 获取线程ID（从调用堆栈中获取）
        thread_id = self.sender().thread_id if hasattr(self.sender(), 'thread_id') else 0
        
        # 确保self.thread_progress已初始化
        if not hasattr(self, 'thread_progress') or self.thread_progress is None:
            self.thread_progress = {}
            
        # 更新此线程的进度
        self.thread_progress[thread_id] = current
        
        # 计算所有线程的总进度
        total_downloaded = sum(self.thread_progress.values())
        
        # 确保download_manager和total_size有效，避免除零错误
        if not hasattr(self, 'download_manager') or not self.download_manager or not hasattr(self.download_manager, 'total_size') or self.download_manager.total_size <= 0:
            return
            
        # 计算总进度百分比，使用浮点数计算以获得更平滑的进度
        progress_percent = (total_downloaded / self.download_manager.total_size) * 100.0
        
        # 确保总进度不超过100%，并保留一位小数以使进度更平滑
        progress = min(progress_percent, 100.0)
        
        # 使用QProgressBar的setValue方法设置进度值（整数）
        self.progress_bar.setValue(int(progress))
        
        # 在标签中显示更精确的进度值（保留一位小数）
        progress_text = f"{progress:.1f}%"
        
        # 确保时间相关变量已初始化
        if not hasattr(self, 'download_start_time') or self.download_start_time is None:
            self.download_start_time = datetime.now()
        if not hasattr(self, 'last_update_time') or self.last_update_time is None:
            self.last_update_time = self.download_start_time
        if not hasattr(self, 'last_downloaded') or self.last_downloaded is None:
            self.last_downloaded = 0
        
        # 计算下载速度（每秒）
        now = datetime.now()
        time_diff = (now - self.last_update_time).total_seconds()
        if time_diff > 0.5:  # 每0.5秒更新一次速度
            bytes_diff = total_downloaded - self.last_downloaded
            speed = bytes_diff / time_diff if time_diff > 0 else 0  # 字节/秒，避免除零错误
            
            # 计算剩余时间，确保使用正确的total_size
            if speed > 0 and self.download_manager.total_size > 0:
                remaining_bytes = self.download_manager.total_size - total_downloaded
                remaining_seconds = remaining_bytes / speed
                remaining_time = self.format_time(remaining_seconds)
            else:
                remaining_time = "计算中..."
            
            # 更新信息标签
            speed_text = self.format_size(speed) + "/s"
            self.info_label.setText(f"进度: {progress_text} | 速度: {speed_text} | 剩余: {remaining_time} | 线程: {DOWNLOAD_THREADS}")
            
            # 更新上次记录的时间和下载量
            self.last_update_time = now
            self.last_downloaded = total_downloaded
    
    def format_time(self, seconds):
        """将秒数格式化为时分秒"""
        if seconds < 60:
            return f"{int(seconds)}秒"
        elif seconds < 3600:
            minutes = int(seconds / 60)
            seconds = int(seconds % 60)
            return f"{minutes}分{seconds}秒"
        else:
            hours = int(seconds / 3600)
            minutes = int((seconds % 3600) / 60)
            return f"{hours}时{minutes}分"
    
    def format_size(self, size_bytes):
        """将字节数格式化为KB/MB/GB"""
        if size_bytes < 1024:
            return f"{size_bytes}B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes/1024:.2f}KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes/(1024*1024):.2f}MB"
        else:
            return f"{size_bytes/(1024*1024*1024):.2f}GB"
    
    def download_error(self, error):
        self.progress_bar.setValue(0)
        self.info_label.setText(f"下载失败: {error}")
        self.cancel_btn.setText("关闭")
        
        QMessageBox.critical(
            self,
            "下载错误",
            f"下载失败: {error}"
        )

    def download_completed(self):
        self.progress_bar.setValue(100)
        self.info_label.setText("下载完成!")
        self.cancel_btn.setText("关闭")
        
        # 3秒后自动关闭
        QTimer.singleShot(3000, self.accept)

# 课件卡片组件
class MaterialCard(CardWidget):
    def __init__(self, material, parent=None):
        super().__init__(parent)
        self.material = material
        self.downloaded = False
        # 设置卡片大小，可根据窗口大小自动调整
        self.setMinimumSize(350, 180)  # 设置更宽的卡片宽度
        self.setMaximumWidth(400)
        self.setup_ui()
        self.check_if_downloaded()
    
    def setup_ui(self):
        # 创建布局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)
        
        # 顶部布局（标题和科目标签）
        top_layout = QHBoxLayout()
        top_layout.setSpacing(10)
        
        # 标题
        title_label = StrongBodyLabel(self.material["title"])
        title_label.setWordWrap(True)
        title_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        
        # 科目标签 - 使用Fluent样式
        category_layout = QHBoxLayout()
        category_layout.setContentsMargins(6, 2, 6, 2)
        category_layout.setSpacing(4)
        
        category_widget = QWidget()
        category_widget.setObjectName("categoryWidget")
        category_widget.setStyleSheet("""
            #categoryWidget {
                background-color: #e1f5fe;
                border-radius: 4px;
            }
        """)
        
        category_label = CaptionLabel(self.material["category"])
        category_label.setStyleSheet("color: #0277bd;")
        category_layout.addWidget(category_label)
        category_widget.setLayout(category_layout)
        category_widget.setFixedHeight(22)
        
        top_layout.addWidget(title_label, 1)  # 1表示伸展因子
        top_layout.addWidget(category_widget, 0)  # 0表示不伸展
        layout.addLayout(top_layout)
        
        # 副标题（使用description作为副标题）
        if "description" in self.material and self.material["description"]:
            subtitle_label = BodyLabel(self.material["description"])
            subtitle_label.setWordWrap(True)
            layout.addWidget(subtitle_label)
        
        # 添加弹性空间
        layout.addStretch(1)
        
        # 底部信息和下载按钮
        bottom_layout = QHBoxLayout()
        
        # 文件大小和日期信息
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        
        # 文件大小
        size_label = CaptionLabel(self.format_size(self.material["fileSize"]))
        info_layout.addWidget(size_label)
        
        # 日期
        date_label = CaptionLabel(self.material["uploadDate"])
        info_layout.addWidget(date_label)
        
        bottom_layout.addLayout(info_layout)
        bottom_layout.addStretch(1)  # 添加弹性空间
        
        # 下载按钮 - 使用Fluent样式按钮
        self.download_btn = PushButton("下载文件")
        self.download_btn.setFixedWidth(120)  # 增加按钮宽度
        self.download_btn.clicked.connect(self.download_material)
        # 设置按钮样式，与图片中一致
        self.download_btn.setStyleSheet("""
            PushButton {
                border: 1px solid #0078d4;
                border-radius: 4px;
                padding: 5px 10px;
                background-color: #ffffff;
                color: #0078d4;
            }
            PushButton:hover {
                background-color: #e6f7ff;
            }
        """)
        bottom_layout.addWidget(self.download_btn)
        
        layout.addLayout(bottom_layout)
        
        # 进度条 - 使用Fluent样式进度条
        self.progress_bar = ProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setFixedHeight(6)  # 设置进度条高度
        layout.addWidget(self.progress_bar)
        
    def format_size(self, size_in_bytes):
        # 转换文件大小为可读格式
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_in_bytes < 1024.0:
                return f"{size_in_bytes:.2f} {unit}"
            size_in_bytes /= 1024.0
        return f"{size_in_bytes:.2f} TB"
    
    def check_if_downloaded(self):
        """检查课件是否已下载"""
        try:
            # 读取下载记录
            with open(DOWNLOAD_RECORD_FILE, "r", encoding="utf-8") as f:
                records = json.load(f)
            
            # 检查当前课件是否已下载
            for record in records:
                if record["id"] == self.material["id"]:
                    self.download_btn.setText("打开文件")
                    # 不使用图标，避免重叠问题
                    # 更新按钮样式，与图片中一致
                    self.download_btn.setStyleSheet("""
                        PushButton {
                            border: 1px solid #0078d4;
                            border-radius: 4px;
                            padding: 5px 10px;
                            background-color: #e6f7ff;
                            color: #0078d4;
                        }
                        PushButton:hover {
                            background-color: #cce9ff;
                        }
                    """)
                    self.download_btn.clicked.disconnect()
                    self.download_btn.clicked.connect(lambda: self.open_file(record["path"]))
                    return
        except Exception as e:
            print(f"检查下载记录失败: {e}")
    
    def download_material(self):
        # 获取文件URL
        file_url = f"{SERVER_URL}{self.material['fileUrl']}"
        
        # 获取文件名
        file_name = os.path.basename(self.material["fileUrl"])
        save_path = os.path.join(DOWNLOAD_DIR, file_name)
        
        # 创建下载管理器
        self.download_manager = DownloadManager(file_url, save_path, 
                                              self.material["id"], self.material["title"])
        
        # 创建并显示下载弹窗
        self.download_dialog = DownloadDialog(self.material["title"], file_name, self)
        # 传递download_manager引用给对话框
        self.download_dialog.download_manager = self.download_manager
        self.download_dialog.show()
        
        # 连接信号
        self.download_manager.progress_signal.connect(self.download_dialog.update_progress)
        self.download_manager.complete_signal.connect(self.download_completed)
        self.download_manager.error_signal.connect(self.download_dialog.download_error)
        
        # 开始下载
        self.download_btn.setEnabled(False)
        self.download_btn.setText("下载中...")
        self.download_manager.start()
    
    def download_completed(self, file_path):
        # 关闭下载弹窗
        if hasattr(self, 'download_dialog') and self.download_dialog:
            self.download_dialog.download_completed()
        
        self.download_btn.setText("打开文件")
        self.download_btn.setEnabled(True)
        self.download_btn.clicked.disconnect()
        self.download_btn.clicked.connect(lambda: self.open_file(file_path))
        
        # 更新按钮样式，与图片中一致
        self.download_btn.setStyleSheet("""
            PushButton {
                border: 1px solid #0078d4;
                border-radius: 4px;
                padding: 5px 10px;
                background-color: #e6f7ff;
                color: #0078d4;
            }
            PushButton:hover {
                background-color: #cce9ff;
            }
        """)
        
        # 自动打开文件
        QTimer.singleShot(500, lambda: self.open_file(file_path))
    
    def open_file(self, file_path):
        try:
            if os.path.exists(file_path):
                # 使用系统默认程序打开文件
                QDesktopServices.openUrl(QUrl.fromLocalFile(file_path))
            else:
                QMessageBox.warning(self, "文件不存在", "文件不存在或已被移动")
                # 重置按钮状态
                self.download_btn.setText("下载文件")
                self.download_btn.clicked.disconnect()
                self.download_btn.clicked.connect(self.download_material)
        except Exception as e:
            QMessageBox.critical(self, "打开文件错误", f"无法打开文件: {str(e)}")
            print(f"打开文件错误: {e}")
            # 重置按钮状态
            self.download_btn.setText("下载文件")
            self.download_btn.clicked.disconnect()
            self.download_btn.clicked.connect(self.download_material)
        
        # 自动打开文件
        QTimer.singleShot(500, lambda: self.open_file(file_path))
    
    def open_file(self, file_path):
        try:
            if os.path.exists(file_path):
                # 使用系统默认程序打开文件
                QDesktopServices.openUrl(QUrl.fromLocalFile(file_path))
            else:
                QMessageBox.warning(self, "文件不存在", "文件不存在或已被移动")
                # 重置按钮状态
                self.download_btn.setText("下载文件")
                self.download_btn.clicked.disconnect()
                self.download_btn.clicked.connect(self.download_material)
        except Exception as e:
            QMessageBox.critical(self, "打开文件错误", f"无法打开文件: {str(e)}")
            print(f"打开文件错误: {e}")
            # 重置按钮状态
            self.download_btn.setText("下载文件")
            self.download_btn.clicked.disconnect()
            self.download_btn.clicked.connect(self.download_material)

# 主窗口类
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        # 设置应用主题
        setTheme(Theme.LIGHT)
        # 设置窗口标题
        self.setWindowTitle("NextPPT Client")
        # 设置默认窗口大小，与截图中一致
        self.resize(1127, 675)  # 调整为与截图一致的窗口大小
        self.setMinimumSize(750, 500)  # 设置最小窗口大小
        # 禁用动画效果
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        self.setAttribute(Qt.WA_NoSystemBackground, False)
        # 设置窗口居中显示
        self.center_window()
        # 加载字体
        self.load_fonts()
        # 初始化UI
        self.init_ui()
        # 不再需要单独加载分类，因为已经在init_ui中加载到ComboBox
    
    def center_window(self):
        """使窗口在屏幕中央显示"""
        screen_geo = QApplication.desktop().screenGeometry()
        window_geo = self.geometry()
        x = (screen_geo.width() - window_geo.width()) // 2
        y = (screen_geo.height() - window_geo.height()) // 2
        self.move(x, y)
    
    def load_fonts(self):
        """加载字体"""
        # 设置应用字体为微软雅黑
        app_font = QFont("Microsoft YaHei", 10)
        QApplication.setFont(app_font)
        
        # 设置全局样式表，确保所有控件都使用微软雅黑字体
        self.setStyleSheet("""
            * {
                font-family: "Microsoft YaHei";
            }
        """)
    
    def init_ui(self):
        # 创建主布局
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 创建课件页面
        self.materials_page = self.materials_widget()
        
        # 将课件页面添加到主布局
        main_layout.addWidget(self.materials_page)
        
        # 设置中央部件 - 使用 QMainWindow 的方式
        self.setCentralWidget(central_widget)
        
        # 加载分类到ComboBox
        self.load_categories_to_combobox()
    
    def materials_widget(self):
        """创建课件列表界面"""
        # 创建主界面
        widget = QWidget()
        widget.setObjectName("materialsInterface")
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)
        
        # 顶部区域
        top_layout = QHBoxLayout()
        
        # 标题
        title_label = TitleLabel("课件列表")
        top_layout.addWidget(title_label)
        top_layout.addStretch(1)
        
        # 右上角添加ComboBox分类选择器
        from qfluentwidgets import ComboBox
        self.category_combobox = ComboBox()
        self.category_combobox.setFixedWidth(180)
        self.category_combobox.currentTextChanged.connect(self.load_materials)
        top_layout.addWidget(self.category_combobox)
        
        layout.addLayout(top_layout)
        
        # 课件卡片滚动区域
        scroll_area = SmoothScrollArea()
        scroll_area.setWidgetResizable(True)
        
        # 课件卡片容器
        self.materials_container = QWidget()
        # 使用FlowLayout替代QGridLayout，实现自适应布局，并启用动画效果
        self.materials_layout = FlowLayout(self.materials_container, needAni=True)
        self.materials_layout.setContentsMargins(0, 0, 0, 0)
        self.materials_layout.setHorizontalSpacing(15)
        self.materials_layout.setVerticalSpacing(15)
        
        scroll_area.setWidget(self.materials_container)
        layout.addWidget(scroll_area)
        
        return widget
    
    def load_categories(self):
        try:
            # 获取分类列表
            response = requests.get(f"{SERVER_URL}/api/categories")
            categories = response.json()
            
            # 添加"全部"选项
            self.category_list.addItem("全部")
            
            # 添加分类
            for category in categories:
                self.category_list.addItem(category["name"])
            
            # 默认选中"全部"
            self.category_list.setCurrentRow(0)
        except Exception as e:
            QMessageBox.critical(self, "加载失败", f"加载分类失败: {e}")
            
    def load_categories_to_combobox(self):
        """将分类加载到ComboBox中"""
        try:
            response = requests.get(f"{SERVER_URL}/api/categories")
            categories = response.json()
            
            # 清空ComboBox
            self.category_combobox.clear()
            
            # 添加全部分类
            self.category_combobox.addItem("全部")
            
            # 添加其他分类
            for category in categories:
                self.category_combobox.addItem(category["name"])
                
            # 设置默认选中全部
            self.category_combobox.setCurrentText("全部")
            
            # 默认加载全部分类的课件
            self.load_materials("全部")
        except Exception as e:
            print(f"加载分类到ComboBox失败: {e}")
    
    def category_selected(self, item):
        # 获取选中的分类
        if isinstance(item, str):
            selected_category = item
        elif isinstance(item, bool):
            # 如果是布尔值，说明是从导航栏点击触发的，忽略这个参数
            # 实际的分类名称已经通过lambda函数传递
            return
        else:
            # 如果是 QListWidgetItem 对象
            selected_category = item.text()
        # 重新加载课件列表
        self.load_materials(selected_category)
    
    def load_materials(self, category="全部"):
        try:
            # 清空现有课件
            self.clear_materials()
            
            # 获取课件列表
            response = requests.get(f"{SERVER_URL}/api/materials")
            materials = response.json()
            
            # 根据分类筛选
            if category != "全部":
                materials = [m for m in materials if m["category"] == category]
            
            # 添加课件卡片 - 使用FlowLayout自动排列
            for material in materials:
                card = MaterialCard(material)
                self.materials_layout.addWidget(card)
        except Exception as e:
            QMessageBox.critical(
                self,
                "加载失败",
                f"加载课件失败: {e}"
            )
    
    def clear_materials(self):
        # 清空课件布局
        for i in range(self.materials_layout.count()):
            widget = self.materials_layout.itemAt(0).widget()
            if widget:
                widget.deleteLater()
                self.materials_layout.removeWidget(widget)

# 程序入口
if __name__ == "__main__":
    # 设置高DPI缩放 - 必须在创建QApplication之前设置
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)
    
    # 创建应用程序
    app = QApplication(sys.argv)
    
    # 设置应用程序主题
    setTheme(Theme.DARK)
    
    # 创建并显示主窗口
    window = MainWindow()
    window.show()
    
    # 运行应用程序
    sys.exit(app.exec_())