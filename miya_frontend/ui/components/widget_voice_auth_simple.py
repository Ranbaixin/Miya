#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
语音认证UI面板（简化版）
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

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QCheckBox, QSlider, QGroupBox, QScrollArea,
    QTextEdit, QProgressBar, QFrame, QGridLayout, QMessageBox
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QThread, pyqtSlot
from PyQt5.QtGui import QFont, QPalette, QColor

from system.config import config
from ui.styles.settings_styles import SAVE_BUTTON_STYLE, RESET_BUTTON_STYLE
import logging

logger = logging.getLogger("VoiceAuthUI")

class VoiceAuthWidget(QWidget):
    """语音认证主界面（简化版）"""

    # 信号
    auth_status_changed = pyqtSignal(bool, str)  # 是否认证通过, 用户名
    voiceprint_registered = pyqtSignal(str)  # 声纹注册成功
    active_comm_triggered = pyqtSignal(str)  # 主动交流触发

    def __init__(self, parent=None):
        super().__init__(parent)

        # 录音状态
        self.is_recording = False
        self.audio_data = []

        # 导入认证模块
        try:
            from voice.auth import get_voiceprint_auth, get_active_comm_manager
            self.voiceprint_auth = get_voiceprint_auth()
            self.active_comm = get_active_comm_manager()
            logger.info("语音认证模块加载成功")
        except Exception as e:
            logger.error(f"导入语音认证模块失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            self.voiceprint_auth = None
            self.active_comm = None
            self._init_error = str(e)
        else:
            self._init_error = None

        # 最后初始化UI
        self.setup_ui()

    def _show_error_message(self, message):
        """显示错误信息"""
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setWindowTitle("警告")
        msg_box.setText(message)
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.exec_()

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
            # 1. 声纹录入区域（简化版）
            self.create_simple_voiceprint_section(content_layout)

            # 2. 主动交流区域（简化版）
            self.create_simple_active_comm_section(content_layout)

            # 3. 状态显示区域
            self.create_simple_status_section(content_layout)

        except Exception as e:
            import traceback
            logger.error(f"创建UI组件失败: {e}")
            logger.error(traceback.format_exc())
            error_label = QLabel(f"❌ UI初始化失败: {str(e)}")
            error_label.setStyleSheet("color: red; font-size: 14px; padding: 20px;")
            content_layout.addWidget(error_label)

        # 如果初始化时有错误，显示警告
        if hasattr(self, '_init_error') and self._init_error:
            warn_label = QLabel(f"⚠️ 语音认证模块加载失败: {self._init_error}")
            warn_label.setStyleSheet("color: #856404; font-size: 12px; padding: 10px; background: #fff3cd; border: 1px solid #ffc107; border-radius: 5px;")
            warn_label.setWordWrap(True)
            content_layout.insertWidget(0, warn_label)

        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)

    def create_simple_voiceprint_section(self, parent_layout):
        """创建声纹录入区域（简化版）"""
        group = QGroupBox("🎙️ 声纹认证")
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

        # 说明文本
        info_label = QLabel("声纹认证功能需要numpy库支持。如果不可用，可以跳过此功能。")
        info_label.setStyleSheet("color: #666; font-size: 12px; padding: 10px;")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        # 用户名输入
        name_layout = QHBoxLayout()
        name_label = QLabel("用户名:")
        name_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #1a1a2e;")
        self.voiceprint_name_input = QLineEdit()
        self.voiceprint_name_input.setPlaceholderText("输入您的姓名")
        self.voiceprint_name_input.setStyleSheet("""
            QLineEdit {
                padding: 8px;
                border: 1px solid #dee2e6;
                border-radius: 5px;
                background: white;
                font-size: 14px;
            }
        """)
        name_layout.addWidget(name_label)
        name_layout.addWidget(self.voiceprint_name_input)
        layout.addLayout(name_layout)

        # 录制按钮
        self.record_btn = QPushButton("🎤 录制声纹")
        self.record_btn.setFixedSize(200, 50)
        self.record_btn.setStyleSheet(SAVE_BUTTON_STYLE)
        self.record_btn.clicked.connect(self.toggle_recording)
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(self.record_btn)
        button_layout.addStretch()
        layout.addLayout(button_layout)

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

    def create_simple_active_comm_section(self, parent_layout):
        """创建主动交流区域（简化版）"""
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
        self.active_enable_checkbox.setStyleSheet("""
            QCheckBox {
                font-size: 14px;
                spacing: 8px;
            }
        """)
        self.active_enable_checkbox.stateChanged.connect(self.on_active_enable_changed)
        enable_layout.addWidget(enable_label)
        enable_layout.addWidget(self.active_enable_checkbox)
        enable_layout.addStretch()
        layout.addLayout(enable_layout)

        parent_layout.addWidget(group)

    def create_simple_status_section(self, parent_layout):
        """创建状态显示区域（简化版）"""
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
        voiceprint_status = QLabel(f"声纹认证: {'启用' if getattr(config.system, 'voiceprint_enabled', False) else '禁用'}")
        voiceprint_status.setStyleSheet(f"""
            QLabel {{
                background: #f8f9fa;
                border: 1px solid #{'28a745' if getattr(config.system, 'voiceprint_enabled', False) else '#dc3545'};
                border-radius: 5px;
                padding: 10px;
                font-size: 14px;
                font-weight: bold;
                color: #{'155724' if getattr(config.system, 'voiceprint_enabled', False) else '#721c24'};
            }}
        """)
        layout.addWidget(voiceprint_status)

        # 主动交流状态
        active_status = QLabel(f"主动交流: {'启用' if getattr(config.system, 'active_communication', False) else '禁用'}")
        active_status.setStyleSheet(f"""
            QLabel {{
                background: #f8f9fa;
                border: 1px solid #{'28a745' if getattr(config.system, 'active_communication', False) else '#dc3545'};
                border-radius: 5px;
                padding: 10px;
                font-size: 14px;
                font-weight: bold;
                color: #{'155724' if getattr(config.system, 'active_communication', False) else '#721c24'};
            }}
        """)
        layout.addWidget(active_status)

        parent_layout.addWidget(group)

    def toggle_recording(self):
        """切换录制状态"""
        if not self.voiceprint_auth:
            self._show_error_message("声纹认证模块未初始化")
            return

        username = self.voiceprint_name_input.text().strip()
        if not username:
            self._show_error_message("请输入用户名")
            return

        # 检查numpy是否可用
        try:
            import numpy as np
        except ImportError:
            self._show_error_message("声纹认证需要numpy库，请先安装: pip install numpy")
            return

        # 检查麦克风是否可用
        try:
            from voice.input.microphone_recorder import MicrophoneRecorder
            recorder = MicrophoneRecorder()

            # 获取音频设备信息
            devices = recorder.get_audio_devices()
            if not devices:
                self._show_error_message("未检测到麦克风设备。请检查麦克风是否已连接，或安装pyaudio: pip install pyaudio")
                return

            # 显示检测到的设备
            logger.info(f"检测到 {len(devices)} 个麦克风设备")
            for device in devices[:3]:
                logger.info(f"  - {device['name']}")

        except Exception as e:
            logger.error(f"检查麦克风失败: {e}")
            self._show_error_message(f"检查麦克风失败: {e}")
            return

        # 使用真实麦克风录音进行声纹录入
        try:
            # 创建录制对话框
            from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QProgressBar

            dialog = QDialog(self)
            dialog.setWindowTitle(f"录制声纹 - {username}")
            dialog.setMinimumSize(450, 350)
            dialog.setStyleSheet("""
                QDialog {
                    background: #f8f9fa;
                }
            """)

            layout = QVBoxLayout(dialog)
            layout.setSpacing(20)
            layout.setContentsMargins(20, 20, 20, 20)

            # 说明
            info_label = QLabel(f"请清晰朗读以下内容进行声纹录入：\n\n\"我是{username}，这是我的声纹认证\"")
            info_label.setStyleSheet("""
                font-size: 14px;
                color: #495057;
                padding: 15px;
                background: white;
                border: 1px solid #dee2e6;
                border-radius: 5px;
            """)
            info_label.setWordWrap(True)
            layout.addWidget(info_label)

            # 进度条
            progress_bar = QProgressBar()
            progress_bar.setRange(0, 100)
            progress_bar.setValue(0)
            progress_bar.setStyleSheet("""
                QProgressBar {
                    border: 2px solid #0078d7;
                    border-radius: 5px;
                    text-align: center;
                    background: #f0f0f0;
                    font-size: 12px;
                }
                QProgressBar::chunk {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #0078d7, stop:1 #00a2ff);
                    border-radius: 3px;
                }
            """)
            layout.addWidget(progress_bar)

            # 状态标签
            status_label = QLabel("准备开始录制...")
            status_label.setStyleSheet("""
                font-size: 14px;
                font-weight: bold;
                color: #0078d7;
                padding: 10px;
                background: #e3f2fd;
                border-radius: 5px;
            """)
            layout.addWidget(status_label)

            # 按钮区域
            button_layout = QHBoxLayout()
            button_layout.addStretch()

            start_btn = QPushButton("开始录制")
            start_btn.setStyleSheet(SAVE_BUTTON_STYLE)
            button_layout.addWidget(start_btn)

            cancel_btn = QPushButton("取消")
            cancel_btn.setStyleSheet(RESET_BUTTON_STYLE)
            button_layout.addWidget(cancel_btn)

            button_layout.addStretch()
            layout.addLayout(button_layout)

            # 录制逻辑
            mic_recorder = None
            record_duration = 5.0  # 5秒录制时间

            def start_recording():
                try:
                    from voice.input.microphone_recorder import MicrophoneRecorder

                    mic_recorder = MicrophoneRecorder()

                    # 开始录制
                    status_label.setText("正在录音...请清晰朗读提示内容")
                    status_label.setStyleSheet("""
                        font-size: 14px;
                        font-weight: bold;
                        color: #dc3545;
                        padding: 10px;
                        background: #fff3cd;
                        border-radius: 5px;
                    """)
                    start_btn.setEnabled(False)
                    cancel_btn.setEnabled(False)

                    # 启动录音
                    success = mic_recorder.start_recording(duration=record_duration)

                    if success:
                        # 模拟进度条更新
                        import time
                        start_time = time.time()

                        while time.time() - start_time < record_duration:
                            progress = int((time.time() - start_time) / record_duration * 100)
                            progress_bar.setValue(progress)
                            status_label.setText(f"正在录音... {record_duration - (time.time() - start_time):.1f} 秒后自动停止")
                            self.parent().parent().parent().processEvents() if hasattr(self.parent(), 'parent') else None
                            time.sleep(0.05)

                        # 等待录音完成
                        time.sleep(0.5)

                        # 获取音频数据
                        audio_array = mic_recorder.get_audio_array()

                        if audio_array is not None and len(audio_array) > 0:
                            # 提取声纹特征
                            features = self.voiceprint_auth.extract_audio_features(audio_array)

                            # 注册声纹
                            success = self.voiceprint_auth.register_voiceprint(username, features, record_duration)

                            if success:
                                self.voiceprint_registered.emit(username)
                                self.update_voiceprint_list()
                                status_label.setText("✓ 声纹录入成功！")
                                status_label.setStyleSheet("""
                                    font-size: 14px;
                                    font-weight: bold;
                                    color: #155724;
                                    padding: 10px;
                                    background: #d4edda;
                                    border-radius: 5px;
                                """)
                                progress_bar.setValue(100)

                                # 延迟关闭对话框
                                QTimer.singleShot(2000, dialog.accept)
                            else:
                                status_label.setText("✗ 声纹录入失败")
                                status_label.setStyleSheet("""
                                    font-size: 14px;
                                    font-weight: bold;
                                    color: #721c24;
                                    padding: 10px;
                                    background: #f8d7da;
                                    border-radius: 5px;
                                """)
                        else:
                            status_label.setText("✗ 未录制到音频")
                            status_label.setStyleSheet("""
                                font-size: 14px;
                                font-weight: bold;
                                color: #721c24;
                                padding: 10px;
                                background: #f8d7da;
                                border-radius: 5px;
                            """)
                    else:
                        status_label.setText("✗ 录音启动失败")
                        status_label.setStyleSheet("""
                            font-size: 14px;
                            font-weight: bold;
                            color: #721c24;
                            padding: 10px;
                            background: #f8d7da;
                            border-radius: 5px;
                        """)

                    start_btn.setEnabled(True)
                    cancel_btn.setEnabled(True)

                except Exception as e:
                    import traceback
                    logger.error(f"声纹录制失败: {e}\n{traceback.format_exc()}")
                    status_label.setText(f"✗ 录制失败: {e}")
                    status_label.setStyleSheet("""
                        font-size: 14px;
                        font-weight: bold;
                        color: #721c24;
                        padding: 10px;
                        background: #f8d7da;
                        border-radius: 5px;
                    """)
                    start_btn.setEnabled(True)
                    cancel_btn.setEnabled(True)

            def cancel_recording():
                if mic_recorder:
                    mic_recorder.stop_recording()
                dialog.reject()

            start_btn.clicked.connect(start_recording)
            cancel_btn.clicked.connect(cancel_recording)

            # 显示对话框
            dialog.exec_()

        except Exception as e:
            import traceback
            logger.error(f"声纹录入失败: {e}\n{traceback.format_exc()}")
            self._show_error_message(f"声纹录入失败: {e}")

    def _show_success_message(self, message):
        """显示成功消息"""
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Information)
        msg_box.setWindowTitle("成功")
        msg_box.setText(message)
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.exec_()

    def trigger_active_comm(self):
        """触发主动交流"""
        if not self.active_comm:
            self._show_error_message("主动交流模块未初始化")
            return

        message = self.active_comm.get_initiated_message()
        if message:
            self._show_success_message(f"主动交流触发: {message}")
            self.active_comm_triggered.emit(message)
        else:
            self._show_error_message("暂无可用的主动交流话题")

    def on_active_enable_changed(self, state):
        """主动交流启用状态改变"""
        config.system.active_communication = (state == Qt.Checked)
        if self.active_comm:
            self.active_comm.enabled = (state == Qt.Checked)

    def update_voiceprint_list(self):
        """更新声纹列表"""
        if self.voiceprint_auth:
            try:
                voiceprints = self.voiceprint_auth.list_voiceprints()
                text = "\n".join([f"• {vp}" for vp in voiceprints])
                self.voiceprint_list.setPlainText(text if text else "暂无已注册声纹")
            except Exception as e:
                self.voiceprint_list.setPlainText(f"无法加载声纹列表: {e}")


# 测试代码
if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication
    app = QApplication(sys.argv)
    widget = VoiceAuthWidget()
    widget.setWindowTitle("语音认证面板（简化版）")
    widget.resize(600, 800)
    widget.show()
    sys.exit(app.exec_())
