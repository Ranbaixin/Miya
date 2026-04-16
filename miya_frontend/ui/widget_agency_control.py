#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自主性控制面板 - Agency Control Panel
用户可以控制弥娅的自主性行为
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, 
    QLabel, QSlider, QComboBox, QPushButton,
    QCheckBox, QScrollArea, QTextEdit, QFrame,
    QGridLayout, QMessageBox, QSpinBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont

from system.config import config, logger
import json
from datetime import datetime


class AgencyControlPanel(QWidget):
    """自主性控制面板"""
    
    # 信号
    status_updated = pyqtSignal(dict)  # 状态更新
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        
        # 定时刷新状态
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.refresh_status)
        self.status_timer.start(5000)  # 每5秒刷新
        
        self.refresh_status()
    
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # 标题
        title = QLabel("🤔 弥娅自主性控制")
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # 分隔线
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(separator)
        
        # 滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)
        
        # 1. 自主性等级控制
        level_group = QGroupBox("自主性等级")
        level_layout = QVBoxLayout()
        
        self.level_combo = QComboBox()
        self.level_combo.addItems(["OFF", "LOW", "MEDIUM", "HIGH", "PAUSED"])
        self.level_combo.setCurrentText("HIGH")
        self.level_combo.currentTextChanged.connect(self.on_level_changed)
        level_layout.addWidget(QLabel("当前等级："))
        level_layout.addWidget(self.level_combo)
        
        # 等级说明
        level_info = QLabel()
        level_info.setWordWrap(True)
        level_info.setText("""
        • OFF：关闭所有自主行为，只响应指令
        • LOW：只提供建议，不主动行动
        • MEDIUM：可执行高分行动，重要行动需确认
        • HIGH：完全自主决策和行动
        • PAUSED：暂停所有自主行为
        """)
        level_info.setStyleSheet("color: gray; font-size: 11px;")
        level_layout.addWidget(level_info)
        
        level_group.setLayout(level_layout)
        scroll_layout.addWidget(level_group)
        
        # 2. 价值观权重调整
        values_group = QGroupBox("价值观权重 (总和应为1.0)")
        values_layout = QGridLayout()
        
        # 滑块创建函数
        def create_slider(label, key, default_value, description):
            container = QWidget()
            container_layout = QVBoxLayout(container)
            
            # 标签和当前值
            header_layout = QHBoxLayout()
            name_label = QLabel(label)
            name_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
            
            value_label = QLabel(f"{default_value*100:.0f}%")
            value_label.setFixedWidth(50)
            value_label.setStyleSheet("font-weight: bold; color: #0078d4;")
            
            header_layout.addWidget(name_label)
            header_layout.addStretch()
            header_layout.addWidget(value_label)
            container_layout.addLayout(header_layout)
            
            # 滑块
            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setRange(0, 100)
            slider.setValue(int(default_value * 100))
            
            # 滑块变化回调
            def on_value_changed(value):
                new_weight = value / 100.0
                value_label.setText(f"{new_weight*100:.0f}%")
                self.update_value_weight(key, new_weight)
            
            slider.valueChanged.connect(on_value_changed)
            container_layout.addWidget(slider)
            
            # 描述
            desc_label = QLabel(description)
            desc_label.setWordWrap(True)
            desc_label.setStyleSheet("color: gray; font-size: 10px;")
            container_layout.addWidget(desc_label)
            
            return container, slider
        
        # 创建所有价值观滑块
        self.sliders = {}
        
        self.sliders["efficiency"], slider1 = create_slider(
            "用户效率",
            "user_efficiency",
            0.35,
            "帮助用户更高效地完成任务，减少认知负担"
        )
        values_layout.addWidget(self.sliders["efficiency"], 0, 0)
        
        self.sliders["wellbeing"], slider2 = create_slider(
            "用户福祉",
            "user_wellbeing",
            0.30,
            "关注用户身体健康和心理状态，提醒适当休息"
        )
        values_layout.addWidget(self.sliders["wellbeing"], 0, 1)
        
        self.sliders["helpful"], slider3 = create_slider(
            "有帮助性",
            "helpful",
            0.25,
            "在需要时主动提供帮助和有价值的信息"
        )
        values_layout.addWidget(self.sliders["helpful"], 1, 0)
        
        self.sliders["non_intrusive"], slider4 = create_slider(
            "非打扰性",
            "non_intrusive",
            0.10,
            "在不合适的时候不打扰用户，优先后台任务"
        )
        values_layout.addWidget(self.sliders["non_intrusive"], 1, 1)
        
        # 权重总和显示
        self.weight_sum_label = QLabel("当前总和: 100.0%")
        self.weight_sum_label.setStyleSheet("font-weight: bold; color: #0078d4;")
        values_layout.addWidget(self.weight_sum_label, 2, 0, 1, 2)
        
        values_group.setLayout(values_layout)
        scroll_layout.addWidget(values_group)
        
        # 3. 功能开关
        features_group = QGroupBox("功能开关")
        features_layout = QGridLayout()
        
        self.feature_checks = {}
        features = [
            ("predict_needs", "预测用户需求", "基于历史和情境预测可能的需求"),
            ("late_night_reminders", "深夜提醒", "在深夜工作时提醒休息"),
            ("learning_help", "学习帮助", "学习时主动询问是否需要帮助"),
            ("task_suggestions", "任务建议", "多任务时建议规划和整理"),
            ("proactive_communication", "主动交流", "长时间无互动时主动关心")
        ]
        
        for i, (key, name, desc) in enumerate(features):
            checkbox = QCheckBox(name)
            checkbox.setChecked(True)
            checkbox.stateChanged.connect(lambda state, k=key: self.toggle_feature(k, state))
            
            container = QWidget()
            container_layout = QVBoxLayout(container)
            container_layout.addWidget(checkbox)
            
            desc_label = QLabel(desc)
            desc_label.setWordWrap(True)
            desc_label.setStyleSheet("color: gray; font-size: 10px;")
            container_layout.addWidget(desc_label)
            
            self.feature_checks[key] = checkbox
            features_layout.addWidget(container, i // 2, i % 2)
        
        features_group.setLayout(features_layout)
        scroll_layout.addWidget(features_group)
        
        # 4. 静音时段设置
        quiet_group = QGroupBox("静音时段")
        quiet_layout = QGridLayout()
        
        self.quiet_enabled = QCheckBox("启用静音时段")
        self.quiet_enabled.setChecked(True)
        quiet_layout.addWidget(self.quiet_enabled, 0, 0, 1, 2)
        
        quiet_layout.addWidget(QLabel("开始时间:"), 1, 0)
        self.quiet_start = QSpinBox()
        self.quiet_start.setRange(0, 23)
        self.quiet_start.setValue(23)
        quiet_layout.addWidget(self.quiet_start, 1, 1)
        
        quiet_layout.addWidget(QLabel("结束时间:"), 2, 0)
        self.quiet_end = QSpinBox()
        self.quiet_end.setRange(0, 23)
        self.quiet_end.setValue(7)
        quiet_layout.addWidget(self.quiet_end, 2, 1)
        
        apply_quiet_btn = QPushButton("应用静音设置")
        apply_quiet_btn.clicked.connect(self.apply_quiet_hours)
        quiet_layout.addWidget(apply_quiet_btn, 3, 0, 1, 2)
        
        quiet_group.setLayout(quiet_layout)
        scroll_layout.addWidget(quiet_group)
        
        # 5. 快捷操作
        actions_group = QGroupBox("快捷操作")
        actions_layout = QHBoxLayout()
        
        pause_btn = QPushButton("⏸️ 暂停自主性")
        pause_btn.clicked.connect(self.pause_agency)
        actions_layout.addWidget(pause_btn)
        
        resume_btn = QPushButton("▶️ 恢复自主性")
        resume_btn.clicked.connect(self.resume_agency)
        actions_layout.addWidget(resume_btn)
        
        clear_history_btn = QPushButton("🗑️ 清除历史")
        clear_history_btn.clicked.connect(self.clear_history)
        actions_layout.addWidget(clear_history_btn)
        
        actions_group.setLayout(actions_layout)
        scroll_layout.addWidget(actions_group)
        
        # 6. 状态显示
        status_group = QGroupBox("当前状态")
        status_layout = QVBoxLayout()
        
        self.status_text = QTextEdit()
        self.status_text.setReadOnly(True)
        self.status_text.setMaximumHeight(200)
        self.status_text.setStyleSheet("""
            QTextEdit {
                background-color: #f5f5f5;
                border: 1px solid #ccc;
                border-radius: 4px;
                padding: 8px;
                font-family: Consolas;
                font-size: 11px;
            }
        """)
        status_layout.addWidget(self.status_text)
        
        status_group.setLayout(status_layout)
        scroll_layout.addWidget(status_group)
        
        # 添加弹性空间
        scroll_layout.addStretch()
    
    def on_level_changed(self, level: str):
        """自主性等级改变"""
        logger.info(f"[自主性控制] 等级改变: {level}")
        
        # TODO: 调用API设置等级
        # await agency_manager.set_level(level)
        
        QMessageBox.information(
            self,
            "自主等级设置",
            f"自主性等级已设置为: {level}\n\n"
            "这将影响弥娅的决策行为。"
        )
    
    def update_value_weight(self, key: str, weight: float):
        """更新价值观权重"""
        total = sum(
            self.sliders[k].value() / 100.0 
            for k in self.sliders.keys()
        )
        
        self.weight_sum_label.setText(f"当前总和: {total*100:.0f}%")
        
        if abs(total - 1.0) < 0.01:
            self.weight_sum_label.setStyleSheet("font-weight: bold; color: #28a745;")
        else:
            self.weight_sum_label.setStyleSheet("font-weight: bold; color: #dc3545;")
        
        # TODO: 实时更新权重
        # if total 接近 1.0:
        #     await agency_manager.adjust_value_weight(key, weight)
    
    def toggle_feature(self, feature: str, state: int):
        """开关功能"""
        enabled = state == 2  # Qt.Checked
        logger.info(f"[自主性控制] 功能{'启用' if enabled else '禁用'}: {feature}")
        
        # TODO: 调用API切换功能
        # await agency_manager.toggle_feature(feature, enabled)
    
    def apply_quiet_hours(self):
        """应用静音时段"""
        start = self.quiet_start.value()
        end = self.quiet_end.value()
        enabled = self.quiet_enabled.isChecked()
        
        logger.info(f"[自主性控制] 静音时段: {enabled}, {start}:00-{end}:00")
        
        QMessageBox.information(
            self,
            "静音时段设置",
            f"静音时段已设置: {start}:00 - {end}:00\n"
            f"在此期间，弥娅将减少主动行为。"
        )
    
    def pause_agency(self):
        """暂停自主性"""
        reply = QMessageBox.question(
            self,
            "暂停自主性",
            "确定要暂停弥娅的自主性吗？\n\n"
            "暂停后，弥娅将不再主动行动，但仍会响应你的指令。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # TODO: 调用API暂停
            # await agency_manager.pause()
            
            self.level_combo.setCurrentText("PAUSED")
            QMessageBox.information(self, "已暂停", "自主性已暂停")
    
    def resume_agency(self):
        """恢复自主性"""
        # TODO: 调用API恢复
        # await agency_manager.resume()
        
        self.level_combo.setCurrentText("HIGH")
        QMessageBox.information(self, "已恢复", "自主性已恢复")
    
    def clear_history(self):
        """清除历史"""
        reply = QMessageBox.question(
            self,
            "清除历史",
            "确定要清除所有自主性行动历史吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # TODO: 调用API清除
            # await agency_manager.clear_history()
            
            QMessageBox.information(self, "已清除", "历史记录已清除")
    
    def refresh_status(self):
        """刷新状态显示"""
        status = {
            "level": "HIGH",
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "action_queue": 0,
            "recent_actions": [
                {"time": "00:11:25", "action": "学习建议", "result": "✅"},
                {"time": "00:09:30", "action": "健康检查", "result": "✅"}
            ]
        }
        
        # 格式化显示
        status_str = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 弥娅自主性状态
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔹 自主等级: {status['level']}
🔹 更新时间: {status['timestamp']}
🔹 待执行行动: {status['action_queue']} 个

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 最近行动:
"""
        
        for action in status.get("recent_actions", []):
            status_str += f"  {action['time']} - {action['action']} {action['result']}\n"
        
        status_str += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        
        self.status_text.setText(status_str)


# 测试代码
if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    panel = AgencyControlPanel()
    panel.setWindowTitle("弥娅自主性控制")
    panel.resize(600, 800)
    panel.show()
    
    sys.exit(app.exec())
