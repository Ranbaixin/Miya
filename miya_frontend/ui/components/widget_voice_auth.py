#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
语音认证UI面板
包含声纹录入、检测和主动交流控制
"""
import sys
import os
import json
import time
from pathlib import Path

# 添加项目根目录到path
project_root = os.path.abspath(os.path.dirname(__file__) + '/..')
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 延迟导入numpy，避免初始化失败
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False
    print("警告：numpy未安装，声纹认证功能将不可用")

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QCheckBox, QSlider, QGroupBox, QScrollArea,
    QTextEdit, QProgressBar, QFrame, QGridLayout
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QThread, pyqtSlot
from PyQt5.QtGui import QFont, QPalette, QColor

from system.config import config
from ui.styles.settings_styles import (
    SETTING_CARD_BASE_STYLE, SETTING_CARD_TITLE_STYLE,
    SETTING_CARD_DESC_STYLE, CHECKBOX_STYLE,
    INPUT_STYLE, SAVE_BUTTON_STYLE
)
import logging

logger = logging.getLogger("VoiceAuthUI")

class VoiceAuthWidget(QWidget):
    """语音认证主界面"""

    # 信号
    auth_status_changed = pyqtSignal(bool, str)  # 是否认证通过, 用户名
    voiceprint_registered = pyqtSignal(str)  # 声纹注册成功
    active_comm_triggered = pyqtSignal(str)  # 主动交流触发

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

        # 导入认证模块
        try:
            from voice.auth import get_voiceprint_auth, get_active_comm_manager
            self.voiceprint_auth = get_voiceprint_auth()
            self.active_comm = get_active_comm_manager()
        except Exception as e:
            logger.error(f"导入语音认证模块失败: {e}")
            self.voiceprint_auth = None
            self.active_comm = None

        # 录音状态
        self.is_recording = False
        self.audio_data = []

    def setup_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # 创建滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(20)

        try:
            # 1. 声纹录入区域
            self.create_voiceprint_section(content_layout)

            # 2. 声纹检测区域
            self.create_verify_section(content_layout)

            # 3. 主动交流区域
            self.create_active_comm_section(content_layout)

            # 4. 状态显示区域
            self.create_status_section(content_layout)
        except Exception as e:
            import traceback
            logger.error(f"创建UI组件失败: {e}")
            logger.error(traceback.format_exc())
            error_label = QLabel(f"❌ UI初始化失败: {str(e)}")
            error_label.setStyleSheet("color: red; font-size: 14px; padding: 20px;")
            content_layout.addWidget(error_label)

        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)

    def create_voiceprint_section(self, parent_layout):
        """创建声纹录入区域"""
        group = QGroupBox("🎙️ 声纹录入")
        group.setStyleSheet("""
            QGroupBox {
                font-size: 16px;
                font-weight: bold;
                border: 2px solid #0078d7;
                border-radius: 10px;
                margin-top: 12px;
                padding: 15px;
                color: #1a1a2e;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 8px;
                background: #0078d7;
                color: white;
                border-radius: 5px;
            }
        """)

        layout = QVBoxLayout(group)
        layout.setSpacing(12)

        # 用户名输入
        name_layout = QHBoxLayout()
        name_label = QLabel("用户名:")
        name_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #1a1a2e;")
        self.voiceprint_name_input = QLineEdit()
        self.voiceprint_name_input.setPlaceholderText("输入您的姓名")
        self.voiceprint_name_input.setStyleSheet(INPUT_STYLE)
        name_layout.addWidget(name_label)
        name_layout.addWidget(self.voiceprint_name_input)
        layout.addLayout(name_layout)

        # 录制按钮和进度条
        self.record_btn = QPushButton("🎤 开始录制声纹")
        self.record_btn.setFixedSize(200, 50)
        self.record_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #0078d7, stop:1 #00a2ff);
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #00a2ff, stop:1 #00c4ff);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #0056b3, stop:1 #0078d7);
            }
        """)
        self.record_btn.clicked.connect(self.toggle_recording)

        self.recording_progress = QProgressBar()
        self.recording_progress.setRange(0, 100)
        self.recording_progress.setValue(0)
        self.recording_progress.setStyleSheet("""
            QProgressBar {
                border: 2px solid #0078d7;
                border-radius: 5px;
                text-align: center;
                background: #f0f0f0;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #0078d7, stop:1 #00a2ff);
                border-radius: 3px;
            }
        """)

        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(self.record_btn)
        button_layout.addStretch()
        layout.addLayout(button_layout)
        layout.addWidget(self.recording_progress)

        # 已注册声纹列表
        layout.addWidget(QLabel("已注册声纹:"))
        self.voiceprint_list = QTextEdit()
        self.voiceprint_list.setReadOnly(True)
        self.voiceprint_list.setMaximumHeight(100)
        self.voiceprint_list.setStyleSheet("""
            QTextEdit {
                background: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 5px;
                padding: 10px;
                font-family: 'Microsoft YaHei UI', sans-serif;
                font-size: 12px;
            }
        """)
        self.update_voiceprint_list()
        layout.addWidget(self.voiceprint_list)

        parent_layout.addWidget(group)

    def create_verify_section(self, parent_layout):
        """创建声纹检测区域"""
        group = QGroupBox("🔍 声纹检测")
        group.setStyleSheet("""
            QGroupBox {
                font-size: 16px;
                font-weight: bold;
                border: 2px solid #28a745;
                border-radius: 10px;
                margin-top: 12px;
                padding: 15px;
                color: #1a1a2e;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 8px;
                background: #28a745;
                color: white;
                border-radius: 5px;
            }
        """)

        layout = QVBoxLayout(group)
        layout.setSpacing(12)

        # 启用开关
        enable_layout = QHBoxLayout()
        enable_label = QLabel("启用声纹检测:")
        enable_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #1a1a2e;")
        self.verify_enable_checkbox = QCheckBox("只响应声纹主人")
        self.verify_enable_checkbox.setChecked(getattr(config.system, 'voiceprint_enabled', False))
        self.verify_enable_checkbox.setStyleSheet(CHECKBOX_STYLE)
        self.verify_enable_checkbox.stateChanged.connect(self.on_verify_enable_changed)
        enable_layout.addWidget(enable_label)
        enable_layout.addWidget(self.verify_enable_checkbox)
        enable_layout.addStretch()
        layout.addLayout(enable_layout)

        # 检测按钮
        self.verify_btn = QPushButton("🎤 开始声纹检测")
        self.verify_btn.setFixedSize(200, 50)
        self.verify_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #28a745, stop:1 #34d399);
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #34d399, stop:1 #40c157);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #1e7e34, stop:1 #28a745);
            }
        """)
        self.verify_btn.clicked.connect(self.start_verification)
        self.verify_btn.setEnabled(getattr(config.system, 'voiceprint_enabled', False))

        # 检测结果显示
        self.verify_result_label = QLabel("⏸️ 等待检测...")
        self.verify_result_label.setStyleSheet("""
            QLabel {
                background: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 5px;
                padding: 15px;
                font-size: 14px;
                font-weight: bold;
                text-align: center;
            }
        """)
        self.verify_result_label.setAlignment(Qt.AlignCenter)

        verify_layout = QHBoxLayout()
        verify_layout.addStretch()
        verify_layout.addWidget(self.verify_btn)
        verify_layout.addStretch()
        layout.addLayout(verify_layout)
        layout.addWidget(self.verify_result_label)

        parent_layout.addWidget(group)

    def create_active_comm_section(self, parent_layout):
        """创建主动交流区域"""
        group = QGroupBox("💬 主动交流")
        group.setStyleSheet("""
            QGroupBox {
                font-size: 16px;
                font-weight: bold;
                border: 2px solid #6610f2;
                border-radius: 10px;
                margin-top: 12px;
                padding: 15px;
                color: #1a1a2e;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 8px;
                background: #6610f2;
                color: white;
                border-radius: 5px;
            }
        """)

        layout = QVBoxLayout(group)
        layout.setSpacing(12)

        # 启用开关
        enable_layout = QHBoxLayout()
        enable_label = QLabel("启用主动交流:")
        enable_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #1a1a2e;")
        self.active_enable_checkbox = QCheckBox("允许AI主动发起对话")
        self.active_enable_checkbox.setChecked(getattr(config.system, 'active_communication', False))
        self.active_enable_checkbox.setStyleSheet(CHECKBOX_STYLE)
        self.active_enable_checkbox.stateChanged.connect(self.on_active_enable_changed)
        enable_layout.addWidget(enable_label)
        enable_layout.addWidget(self.active_enable_checkbox)
        enable_layout.addStretch()
        layout.addLayout(enable_layout)

        # 检测间隔滑块
        interval_layout = QHBoxLayout()
        interval_label = QLabel("检测间隔(分钟):")
        interval_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #1a1a2e;")
        self.interval_slider = QSlider(Qt.Horizontal)
        self.interval_slider.setRange(1, 30)
        self.interval_slider.setValue(5)
        self.interval_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                height: 8px;
                background: #dee2e6;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #6610f2;
                border: 2px solid #5100cc;
                width: 20px;
                height: 20px;
                margin: -8px 0;
                border-radius: 10px;
            }
        """)
        self.interval_value_label = QLabel("5 分钟")
        self.interval_value_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #6610f2;")
        self.interval_slider.valueChanged.connect(self.on_interval_changed)

        interval_layout.addWidget(interval_label)
        interval_layout.addWidget(self.interval_slider)
        interval_layout.addWidget(self.interval_value_label)
        layout.addLayout(interval_layout)

        # 触发测试按钮
        self.trigger_btn = QPushButton("🔔 立即触发主动交流")
        self.trigger_btn.setFixedSize(250, 50)
        self.trigger_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #6610f2, stop:1 #8257fa);
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #8257fa, stop:1 #9d4edd);
            }
        """)
        self.trigger_btn.clicked.connect(self.trigger_active_comm)
        self.trigger_btn.setEnabled(getattr(config.system, 'active_communication', False))

        # 话题显示
        layout.addWidget(QLabel("话题库:"))
        self.topics_display = QTextEdit()
        self.topics_display.setReadOnly(True)
        self.topics_display.setMaximumHeight(120)
        self.topics_display.setStyleSheet("""
            QTextEdit {
                background: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 5px;
                padding: 10px;
                font-family: 'Microsoft YaHei UI', sans-serif;
                font-size: 12px;
            }
        """)
        self.update_topics_display()

        # 添加话题
        add_topic_layout = QHBoxLayout()
        self.add_topic_input = QLineEdit()
        self.add_topic_input.setPlaceholderText("添加新话题...")
        self.add_topic_input.setStyleSheet(INPUT_STYLE)
        add_topic_btn = QPushButton("添加")
        add_topic_btn.setFixedWidth(80)
        add_topic_btn.setStyleSheet(SAVE_BUTTON_STYLE)
        add_topic_btn.clicked.connect(self.add_topic)

        add_topic_layout.addWidget(self.add_topic_input)
        add_topic_layout.addWidget(add_topic_btn)
        layout.addLayout(add_topic_layout)

        # 触发按钮布局
        trigger_layout = QHBoxLayout()
        trigger_layout.addStretch()
        trigger_layout.addWidget(self.trigger_btn)
        trigger_layout.addStretch()
        layout.addLayout(trigger_layout)

        parent_layout.addWidget(group)

    def create_status_section(self, parent_layout):
        """创建状态显示区域"""
        group = QGroupBox("📊 运行状态")
        group.setStyleSheet("""
            QGroupBox {
                font-size: 16px;
                font-weight: bold;
                border: 2px solid #17a2b8;
                border-radius: 10px;
                margin-top: 12px;
                padding: 15px;
                color: #1a1a2e;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 8px;
                background: #17a2b8;
                color: white;
                border-radius: 5px;
            }
        """)

        layout = QVBoxLayout(group)
        layout.setSpacing(8)

        # 声纹状态
        voiceprint_status = self.create_status_item(
            "声纹认证:",
            getattr(config.system, 'voiceprint_enabled', False),
            "启用" if getattr(config.system, 'voiceprint_enabled', False) else "禁用",
            "#28a745" if getattr(config.system, 'voiceprint_enabled', False) else "#dc3545"
        )
        layout.addWidget(voiceprint_status)

        # 主动交流状态
        active_status = self.create_status_item(
            "主动交流:",
            getattr(config.system, 'active_communication', False),
            "启用" if getattr(config.system, 'active_communication', False) else "禁用",
            "#28a745" if getattr(config.system, 'active_communication', False) else "#dc3545"
        )
        layout.addWidget(active_status)

        # 当前检测的说话人
        speaker_status = self.create_status_item(
            "当前说话人:",
            True,
            "未知" if not hasattr(self, 'current_speaker_name') else getattr(self, 'current_speaker_name', '未知'),
            "#ffc107"
        )
        layout.addWidget(speaker_status)

        # 上次交互时间
        last_interaction = self.create_status_item(
            "上次交互:",
            True,
            "无",
            "#6c757d"
        )
        layout.addWidget(last_interaction)

        parent_layout.addWidget(group)

        # 启动状态更新定时器
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.update_status_display)
        self.status_timer.start(2000)  # 每2秒更新一次

    def create_status_item(self, label_text: str, is_active: bool, value_text: str, color: str):
        """创建状态项"""
        item = QFrame()
        item.setStyleSheet(f"""
            QFrame {{
                background: #f8f9fa;
                border: 1px solid {color};
                border-radius: 5px;
                padding: 10px;
            }}
        """)
        layout = QHBoxLayout(item)
        layout.setSpacing(10)

        label = QLabel(label_text)
        label.setStyleSheet("font-size: 13px; font-weight: bold; color: #495057;")
        label.setFixedWidth(100)

        value = QLabel(value_text)
        value.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {color};")

        layout.addWidget(label)
        layout.addWidget(value)
        layout.addStretch()

        return item

    def toggle_recording(self):
        """切换录制状态"""
        if not self.voiceprint_auth:
            self.show_error("声纹认证模块未初始化")
            return

        if self.is_recording:
            self.stop_recording()
        else:
            self.start_recording()

    def start_recording(self):
        """开始录制声纹"""
        username = self.voiceprint_name_input.text().strip()
        if not username:
            self.show_error("请输入用户名")
            return

        self.is_recording = True
        self.record_btn.setText("🔴 录制中...")
        self.record_btn.setEnabled(False)

        # 模拟录制进度（实际应用中应使用真实的录音功能）
        self.recording_progress.setValue(0)
        self.recording_timer = QTimer()
        self.recording_timer.timeout.connect(self.update_recording_progress)
        self.recording_timer.start(50)  # 每50ms更新一次

        logger.info(f"开始录制声纹: {username}")

    def update_recording_progress(self):
        """更新录制进度"""
        current = self.recording_progress.value()
        if current < 100:
            self.recording_progress.setValue(current + 1)
        else:
            self.finish_recording()

    def finish_recording(self):
        """完成录制"""
        self.recording_timer.stop()
        self.is_recording = False
        self.record_btn.setText("🎤 开始录制声纹")
        self.record_btn.setEnabled(True)
        self.recording_progress.setValue(0)

        # 模拟声纹特征（实际应用中应从音频提取）
        username = self.voiceprint_name_input.text().strip()
        if not HAS_NUMPY:
            self.show_error("声纹认证需要numpy库，请先安装")
            return

        fake_features = np.random.rand(256)  # 模拟特征向量

        # 注册声纹
        if self.voiceprint_auth:
            success = self.voiceprint_auth.register_voiceprint(username, fake_features)
            if success:
                self.voiceprint_registered.emit(username)
                self.update_voiceprint_list()
                self.show_info(f"声纹 '{username}' 录入成功！")
            else:
                self.show_error(f"声纹 '{username}' 录入失败")

    def stop_recording(self):
        """停止录制"""
        if self.recording_timer:
            self.recording_timer.stop()
        self.is_recording = False
        self.record_btn.setText("🎤 开始录制声纹")
        self.record_btn.setEnabled(True)
        self.recording_progress.setValue(0)

    def start_verification(self):
        """开始声纹检测"""
        if not self.voiceprint_auth:
            self.show_error("声纹认证模块未初始化")
            return

        self.verify_result_label.setText("🎤 正在检测声纹...")

        # 模拟检测过程（实际应用中应录制并识别）
        QTimer.singleShot(2000, lambda: self.verify_speaker())

    def verify_speaker(self):
        """验证说话人"""
        if not HAS_NUMPY:
            self.show_error("声纹认证需要numpy库，请先安装")
            return

        # 模拟检测结果（实际应用中应从音频提取特征并比对）
        fake_features = np.random.rand(256)

        is_matched, name, score = self.voiceprint_auth.verify_voiceprint(fake_features)

        if is_matched and name:
            self.verify_result_label.setText(f"✅ 认证通过: {name} (相似度: {score:.1%})")
            self.verify_result_label.setStyleSheet("""
                QLabel {
                    background: #d4edda;
                    border: 2px solid #28a745;
                    border-radius: 5px;
                    padding: 15px;
                    font-size: 14px;
                    font-weight: bold;
                    text-align: center;
                    color: #155724;
                }
            """)
            self.current_speaker_name = name
            self.auth_status_changed.emit(True, name)
        else:
            self.verify_result_label.setText("❌ 认证失败: 声纹不匹配")
            self.verify_result_label.setStyleSheet("""
                QLabel {
                    background: #f8d7da;
                    border: 2px solid #dc3545;
                    border-radius: 5px;
                    padding: 15px;
                    font-size: 14px;
                    font-weight: bold;
                    text-align: center;
                    color: #721c24;
                }
            """)
            self.current_speaker_name = None
            self.auth_status_changed.emit(False, "")

    def trigger_active_comm(self):
        """触发主动交流"""
        if not self.active_comm:
            self.show_error("主动交流模块未初始化")
            return

        message = self.active_comm.get_initiated_message()
        if message:
            self.show_info(f"主动交流触发: {message}")
            self.active_comm_triggered.emit(message)
        else:
            self.show_warning("暂无可用的主动交流话题")

    def add_topic(self):
        """添加话题"""
        topic = self.add_topic_input.text().strip()
        if topic:
            if self.active_comm:
                self.active_comm.add_topic(topic)
                self.update_topics_display()
                self.add_topic_input.clear()
                self.show_info(f"已添加话题: {topic}")
            else:
                self.show_error("主动交流模块未初始化")

    def on_verify_enable_changed(self, state):
        """声纹检测启用状态改变"""
        config.system.voiceprint_enabled = (state == Qt.Checked)
        self.verify_btn.setEnabled(state == Qt.Checked)

    def on_active_enable_changed(self, state):
        """主动交流启用状态改变"""
        config.system.active_communication = (state == Qt.Checked)
        self.trigger_btn.setEnabled(state == Qt.Checked)
        if self.active_comm:
            self.active_comm.enabled = (state == Qt.Checked)

    def on_interval_changed(self, value):
        """检测间隔改变"""
        self.interval_value_label.setText(f"{value} 分钟")
        if self.active_comm:
            self.active_comm.check_interval = value * 60

    def update_voiceprint_list(self):
        """更新声纹列表"""
        if self.voiceprint_auth:
            voiceprints = self.voiceprint_auth.list_voiceprints()
            text = "\n".join([f"• {vp}" for vp in voiceprints])
            self.voiceprint_list.setPlainText(text if text else "暂无已注册声纹")

    def update_topics_display(self):
        """更新话题显示"""
        if self.active_comm:
            topics = self.active_comm.topics
            text = "\n".join([f"• {topic}" for topic in topics])
            self.topics_display.setPlainText(text if text else "暂无话题")

    def update_status_display(self):
        """更新状态显示"""
        # 这里可以实时更新各个状态项
        pass

    def show_error(self, message: str):
        """显示错误消息"""
        self.verify_result_label.setText(f"❌ {message}")
        self.verify_result_label.setStyleSheet("""
            QLabel {
                background: #f8d7da;
                border: 2px solid #dc3545;
                border-radius: 5px;
                padding: 15px;
                font-size: 14px;
                font-weight: bold;
                text-align: center;
                color: #721c24;
            }
        """)

    def show_info(self, message: str):
        """显示信息消息"""
        self.verify_result_label.setText(f"✅ {message}")
        self.verify_result_label.setStyleSheet("""
            QLabel {
                background: #d4edda;
                border: 2px solid #28a745;
                border-radius: 5px;
                padding: 15px;
                font-size: 14px;
                font-weight: bold;
                text-align: center;
                color: #155724;
            }
        """)

    def show_warning(self, message: str):
        """显示警告消息"""
        self.verify_result_label.setText(f"⚠️ {message}")
        self.verify_result_label.setStyleSheet("""
            QLabel {
                background: #fff3cd;
                border: 2px solid #ffc107;
                border-radius: 5px;
                padding: 15px;
                font-size: 14px;
                font-weight: bold;
                text-align: center;
                color: #856404;
            }
        """)


# 测试代码
if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication
    app = QApplication(sys.argv)
    widget = VoiceAuthWidget()
    widget.setWindowTitle("语音认证面板")
    widget.resize(600, 800)
    widget.show()
    sys.exit(app.exec_())
