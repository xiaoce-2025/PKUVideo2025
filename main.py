import sys
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout,
    QFileDialog, QListWidget, QListWidgetItem, QTextEdit, QMessageBox
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QBrush, QColor, QPainter
from PyQt6.QtGui import QMovie
import asyncio
import os
import traceback
import json
from qasync import QEventLoop, asyncSlot
# 导入爬虫核心逻辑
from GetPKUVideoUrl import get_course_list, download_replay_links
import re

class SpinWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.angle = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.rotate)
        self.setFixedSize(40, 40)
        self.setVisible(False)

    def start(self):
        self.setVisible(True)
        self.timer.start(50)

    def stop(self):
        self.setVisible(False)
        self.timer.stop()

    def rotate(self):
        self.angle = (self.angle + 30) % 360
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.translate(self.width() / 2, self.height() / 2)
        painter.rotate(self.angle)
        for i in range(12):
            color = QColor(33, 150, 243)
            color.setAlphaF(i / 12)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(color)
            painter.drawEllipse(12, -3, 8, 8)
            painter.rotate(30)

class LoadingOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setStyleSheet("background:rgba(0,0,0,80);")
        self.spinner = SpinWidget(self)
        self.spinner.setParent(self)
        self.spinner.setVisible(True)
        self.setVisible(False)

    def resizeEvent(self, event):
        s = self.spinner.size()
        self.spinner.move((self.width() - s.width()) // 2, (self.height() - s.height()) // 2)
        super().resizeEvent(event)

    def show(self):
        parent = self.parent()
        if isinstance(parent, QWidget):
            self.setGeometry(0, 0, parent.width(), parent.height())
        self.raise_()
        self.setVisible(True)
        self.spinner.start()

    def hide(self):
        self.setVisible(False)
        self.spinner.stop()

class MainWindow(QWidget):
    CONFIG_FILE = 'config.json'

    def __init__(self):
        super().__init__()
        self.setWindowTitle('北大教学网回放批量下载工具')
        self.resize(600, 500)
        self.init_ui()
        self.course_map = {}  # name->key
        self.load_config()

    def load_config(self):
        try:
            with open(self.CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
            self.username_edit.setText(config.get('username', ''))
            self.password_edit.setText(config.get('password', ''))
            self.chrome_path_edit.setText(config.get('chrome_path', ''))
            self.save_path_edit.setText(config.get('save_path', ''))
            self.maxnum_edit.setText(str(config.get('max_num', '')))
        except Exception:
            pass

    def save_config(self):
        config = {
            'username': self.username_edit.text().strip(),
            'password': self.password_edit.text().strip(),
            'chrome_path': self.chrome_path_edit.text().strip(),
            'save_path': self.save_path_edit.text().strip(),
            'max_num': self.maxnum_edit.text().strip(),
        }
        try:
            with open(self.CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.log(f'保存配置失败: {e}')

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # 账号密码
        form_layout = QHBoxLayout()
        self.username_edit = QLineEdit()
        self.username_edit.setPlaceholderText('IAAA账号')
        self.username_edit.setMinimumWidth(120)
        self.password_edit = QLineEdit()
        self.password_edit.setPlaceholderText('IAAA密码')
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_edit.setMinimumWidth(120)
        form_layout.addWidget(QLabel('账号:'))
        form_layout.addWidget(self.username_edit)
        form_layout.addSpacing(10)
        form_layout.addWidget(QLabel('密码:'))
        form_layout.addWidget(self.password_edit)
        layout.addLayout(form_layout)

        # Chrome路径
        chrome_layout = QHBoxLayout()
        self.chrome_path_edit = QLineEdit()
        self.chrome_path_edit.setPlaceholderText('Chrome浏览器路径')
        self.chrome_path_edit.setMinimumWidth(200)
        chrome_btn = QPushButton('选择...')
        chrome_btn.clicked.connect(self.choose_chrome_path)
        chrome_layout.addWidget(QLabel('Chrome路径:'))
        chrome_layout.addWidget(self.chrome_path_edit)
        chrome_layout.addWidget(chrome_btn)
        layout.addLayout(chrome_layout)

        # 保存路径
        savepath_layout = QHBoxLayout()
        self.save_path_edit = QLineEdit()
        self.save_path_edit.setPlaceholderText('请选择保存路径')
        self.save_path_edit.setMinimumWidth(200)
        savepath_btn = QPushButton('选择...')
        savepath_btn.clicked.connect(self.choose_save_path)
        savepath_layout.addWidget(QLabel('保存路径:'))
        savepath_layout.addWidget(self.save_path_edit)
        savepath_layout.addWidget(savepath_btn)
        layout.addLayout(savepath_layout)

        # 获取课程列表按钮
        self.get_courses_btn = QPushButton('获取课程列表')
        self.get_courses_btn.setStyleSheet('font-weight:bold; background:#e0f7fa; height:32px;')
        self.get_courses_btn.clicked.connect(self.get_courses)
        layout.addWidget(self.get_courses_btn)

        # 课程列表
        self.course_list = QListWidget()
        # 设置多项选择和整行选择模式
        self.course_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        self.course_list.setStyleSheet("""
            QListWidget {
                background:#f9fbe7; 
                font-size:15px; 
                min-height:180px; 
                min-width:400px;
                outline: none; /* 去除焦点虚线框 */
            }
            QListWidget::item:selected {
                background-color: #2196F3; /* 选中项背景色 - 深蓝色 */
                color: white;
            }
        """)
        self.course_list.setMinimumHeight(220)
        self.course_list.setMinimumWidth(420)
        # 添加提示说明
        self.course_select_label = QLabel('课程列表：（已选择0项）')
        layout.addWidget(self.course_select_label)
        layout.addWidget(self.course_list)
        self.course_list.itemSelectionChanged.connect(self.update_selected_count)

        # 最大回放数
        maxnum_layout = QHBoxLayout()
        self.maxnum_edit = QLineEdit()
        self.maxnum_edit.setPlaceholderText('单课程最大回放数，-1为全部')
        self.maxnum_edit.setMaximumWidth(120)
        maxnum_layout.addWidget(QLabel('最大回放数:'))
        maxnum_layout.addWidget(self.maxnum_edit)
        layout.addLayout(maxnum_layout)

        # 开始获取按钮
        self.start_btn = QPushButton('开始获取回放下载链接')
        self.start_btn.setStyleSheet('font-weight:bold; background:#ffe082; height:36px;')
        self.start_btn.clicked.connect(self.start_download)
        layout.addWidget(self.start_btn)

        # 日志输出
        layout.addWidget(QLabel('日志输出：'))
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setStyleSheet('background:#f3e5f5; font-size:13px;')
        layout.addWidget(self.log_output)

        self.setLayout(layout)

        # 遮罩层加载动画
        self.loading_overlay = LoadingOverlay(self)
        self.loading_overlay.setGeometry(0, 0, self.width(), self.height())
        self.loading_overlay.hide()

    def choose_chrome_path(self):
        path, _ = QFileDialog.getOpenFileName(self, '选择Chrome浏览器', '', '可执行文件 (*.exe)')
        if path:
            self.chrome_path_edit.setText(path)

    def choose_save_path(self):
        path = QFileDialog.getExistingDirectory(self, '选择保存路径', '')
        if path:
            self.save_path_edit.setText(path)

    def select_all_courses(self):
        pass
    def deselect_all_courses(self):
        pass
    def invert_selection(self):
        pass
    def update_selected_count(self):
        count = len(self.course_list.selectedItems())
        self.course_select_label.setText(f'课程列表：（已选择{count}项）')

    def show_loading(self, show=True):
        if show:
            self.loading_overlay.show()
        else:
            self.loading_overlay.hide()

    @asyncSlot()
    async def get_courses(self):
        self.show_loading(True)
        self.save_config()
        username = self.username_edit.text().strip()
        password = self.password_edit.text().strip()
        chrome_path = self.chrome_path_edit.text().strip()
        save_path = self.save_path_edit.text().strip()
        if not username or not password or not chrome_path or not save_path:
            QMessageBox.warning(self, '提示', '请填写账号、密码、Chrome路径和保存路径')
            self.show_loading(False)
            return
        self.log('正在获取课程列表...')
        self.get_courses_btn.setEnabled(False)
        try:
            courses = await get_course_list(username, password, chrome_path)
            #self.log(f"DEBUG: courses={courses}")
            self.on_courses_ready(courses)
        except Exception as e:
            self.log(f"获取课程列表出错: {str(e)}\n{traceback.format_exc()}")
            self.on_courses_ready([])
        finally:
            self.show_loading(False)

    def on_courses_ready(self, courses):
        self.get_courses_btn.setEnabled(True)
        self.course_list.clear()
        self.course_map = {}
        if not courses:
            self.log('未获取到课程列表')
            return
        
        # 先处理并排序
        def parse_term_key(display_name):
            # 例：24-25学年第2学期: 课程名
            import re
            m = re.match(r"(\d{2})-(\d{2})学年第(\d)学期: ", display_name)
            if m:
                year1 = int(m.group(1))
                year2 = int(m.group(2))
                term = int(m.group(3))
                # 排序优先级：学年（大在前），学期（大在前）
                return (year1, year2, term)
            else:
                return (0, 0, 0)
        
        display_items = []
        for c in courses:
            name = c['name']
            match = re.match(r".*?:\s*(.*?)\((\d{2}-\d{2}学年第\d学期)\)", name)
            if match:
                course_name = match.group(1)
                term = match.group(2)
                display_name = f"{term}: {course_name}"
            else:
                display_name = name
            display_items.append((display_name, c['key']))
        
        # 排序，学年和学期大的排前面
        display_items.sort(key=lambda x: parse_term_key(x[0]), reverse=True)
        
        for display_name, key in display_items:
            item = QListWidgetItem(display_name)
            self.course_list.addItem(item)
            self.course_map[display_name] = key
        
        self.log(f'共获取到 {len(courses)} 门课程，已全部显示在列表中')
        self.log('提示：按住Ctrl或Shift可多选课程，点击后操作')

    @asyncSlot()
    async def start_download(self):
        self.show_loading(True)
        self.save_config()
        username = self.username_edit.text().strip()
        password = self.password_edit.text().strip()
        chrome_path = self.chrome_path_edit.text().strip()
        save_path = self.save_path_edit.text().strip()
        max_num = self.maxnum_edit.text().strip()
        if not username or not password or not chrome_path or not save_path:
            QMessageBox.warning(self, '提示', '请填写账号、密码、Chrome路径和保存路径')
            self.show_loading(False)
            return
        try:
            max_num = int(max_num)
        except:
            max_num = -1
        
        # 获取所有被选中的课程
        selected_items = self.course_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, '提示', '请至少选择一门课程')
            self.show_loading(False)
            return
        course_names = [item.text() for item in selected_items]
        course_keys = [self.course_map[name] for name in course_names]
        
        self.log(f'开始获取回放下载链接...')
        self.log(f'已选择 {len(selected_items)} 门课程：')
        for name in course_names:
            self.log(f'  - {name}')
        self.start_btn.setEnabled(False)
        self.log('-' * 50)
        
        def log_callback(msg):
            self.log(msg)
        
        try:
            await download_replay_links(username, password, chrome_path, course_keys, max_num, log_callback, save_path)
        except Exception as e:
            self.log(f"下载出错: {str(e)}\n{traceback.format_exc()}")
        finally:
            self.on_download_finished()
            self.show_loading(False)

    def on_download_finished(self):
        self.start_btn.setEnabled(True)
        self.log('-' * 50)
        self.log('全部任务完成！')
        self.log('提示：如果需要下载其他课程，请重新选择后再次点击获取')

    def log(self, text):
        self.log_output.append(text)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'loading_overlay'):
            self.loading_overlay.setGeometry(0, 0, self.width(), self.height())

if __name__ == '__main__':
    app = QApplication(sys.argv)
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)
    win = MainWindow()
    win.show()
    with loop:
        loop.run_forever()