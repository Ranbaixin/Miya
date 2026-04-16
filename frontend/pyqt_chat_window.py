import sys, os, time; sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + '/..'))
from .styles.button_factory import ButtonFactory
from nagaagent_core.vendors.PyQt5.QtWidgets import QWidget, QTextEdit, QSizePolicy, QHBoxLayout, QLabel, QVBoxLayout, QStackedWidget, QDesktopWidget, QScrollArea, QSplitter, QFrame
from nagaagent_core.vendors.PyQt5.QtCore import Qt, QEvent
from nagaagent_core.vendors.PyQt5.QtGui import QColor, QPainter, QBrush
from system.config import config, logger
from ui.utils.ui_style_hot_reload import register_window as register_ui_style_window
from ui.components.title_bar import TitleBar
from .components.widget_progress import EnhancedProgressWidget
from .components.widget_live2d_side import Live2DSideWidget
from .components.widget_settings import SettingWidget
from .components.widget_sidebar import SidebarWidget
from .controller import *

# 使用统一配置系统
def get_ui_config():
    """获取UI配置，确保使用最新的配置值"""
    return {
        'BG_ALPHA': config.ui.bg_alpha,
        'WINDOW_BG_ALPHA': config.ui.window_bg_alpha,
        'USER_NAME': config.ui.user_name,
        'MAC_BTN_SIZE': config.ui.mac_btn_size,
        'MAC_BTN_MARGIN': config.ui.mac_btn_margin,
        'MAC_BTN_GAP': config.ui.mac_btn_gap,
        'ANIMATION_DURATION': config.ui.animation_duration
    }


def refresh_ui_constants():
    global BG_ALPHA, WINDOW_BG_ALPHA, USER_NAME, MAC_BTN_SIZE, MAC_BTN_MARGIN, MAC_BTN_GAP, ANIMATION_DURATION
    ui_config = get_ui_config()
    BG_ALPHA = ui_config['BG_ALPHA']
    WINDOW_BG_ALPHA = ui_config['WINDOW_BG_ALPHA']
    USER_NAME = ui_config['USER_NAME']
    MAC_BTN_SIZE = ui_config['MAC_BTN_SIZE']
    MAC_BTN_MARGIN = ui_config['MAC_BTN_MARGIN']
    MAC_BTN_GAP = ui_config['MAC_BTN_GAP']
    ANIMATION_DURATION = ui_config['ANIMATION_DURATION']


refresh_ui_constants()

class ChatWindow(QWidget):
    def __init__(self):
        super().__init__()
        config.window=self

        # 消息缓存队列 - 用于在没有会话时缓存主动消息（已禁用）
        self._cached_qq_messages = []
        # 记录上一次的QQ会话数量，用于检测新会话建立（已禁用）
        self._last_qq_session_count = 0
        logger.info("[缓存消息] 缓存消息功能已禁用，初始化时清空缓存")

        self._init_windows()
        self._init_Layout()
        self._init_buttons()
        self._init_side()
        self._init_end()
        register_ui_style_window(self)
        
    def _init_windows(self):
        # 设置为屏幕大小的80%
        desktop = QDesktopWidget()
        self.screen_rect = desktop.screenGeometry()
        self.window_width = int(self.screen_rect.width() * 0.8)
        self.window_height = int(self.screen_rect.height() * 0.8)
        self._offset = None
        # 获取屏幕大小并自适应
        self.resize(self.window_width, self.window_height)
        
        # 窗口居中显示
        x = (self.screen_rect.width() - self.window_width) // 2
        y = (self.screen_rect.height() - self.window_height) // 2
        self.move(x, y)
        
        # 移除置顶标志，保留无边框
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # 添加窗口背景和拖动支持
        self.setStyleSheet(f"""
            ChatWindow {{
                background: rgba(25, 25, 25, {WINDOW_BG_ALPHA});
                border-radius: 20px;
                border: 1px solid rgba(255, 255, 255, 30);
            }}
        """)
        self.titlebar = TitleBar('NAGA AGENT', self)
        self.titlebar.setGeometry(0,0,self.width(),100)
    
      
    def _init_Layout(self):
        fontfam,fontsize='Lucida Console',16
        
        # 创建主分割器，替换原来的HBoxLayout
        self.main_splitter = QSplitter(Qt.Horizontal, config.window)
        self.main_splitter.setStyleSheet("""
            QSplitter {
                background: transparent;
            }
            QSplitter::handle {
                background: rgba(255, 255, 255, 30);
                width: 2px;
                border-radius: 1px;
            }
            QSplitter::handle:hover {
                background: rgba(255, 255, 255, 60);
                width: 3px;
            }
        """)

        # 左侧侧边栏容器
        self.sidebar = SidebarWidget()
        self.sidebar_width = 80
        self.sidebar.setMinimumWidth(self.sidebar_width)
        self.sidebar.setMaximumWidth(self.sidebar_width)  # 固定宽度
        self.main_splitter.addWidget(self.sidebar)

        # 聊天区域容器
        self.chat_area=QWidget()
        self.chat_area.setMinimumWidth(400)
        self.vlay=QVBoxLayout(self.chat_area)
        self.vlay.setContentsMargins(0,0,0,0)
        self.vlay.setSpacing(10)

        self.chat_stack = QStackedWidget(self.chat_area)
        self.chat_stack.setStyleSheet("""
            QStackedWidget {
                background: transparent;
                border: none;
            }
        """)
        self.chat_page = QWidget()
        self.chat_page.setStyleSheet("""
            QWidget {
                background: transparent;
                border: none;
            }
        """)
        
        # 创建滚动区域来容纳消息对话框
        self.chat_scroll_area = QScrollArea(self.chat_page)
        self.chat_scroll_area.setWidgetResizable(True)
        self.chat_scroll_area.setStyleSheet("""
            QScrollArea {
                background: transparent;
                border: none;
                outline: none;
            }
            QScrollBar:vertical {
                background: rgba(255, 255, 255, 30);
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: rgba(255, 255, 255, 80);
                border-radius: 4px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(255, 255, 255, 120);
            }
        """)
        
        # 创建滚动内容容器
        self.chat_content = QWidget()
        self.chat_content.setStyleSheet("""
            QWidget {
                background: transparent;
                border: none;
            }
        """)
        
        # 创建垂直布局来排列消息对话框
        self.chat_layout = QVBoxLayout(self.chat_content)
        self.chat_layout.setContentsMargins(10, 10, 10, 10)
        self.chat_layout.setSpacing(10)
        self.chat_layout.addStretch()  # 添加弹性空间，让消息从顶部开始
        self.chat_scroll_area.setWidget(self.chat_content)
        
        # 创建聊天页面布局
        self.chat_page_layout = QVBoxLayout(self.chat_page)
        self.chat_page_layout.setContentsMargins(0, 0, 0, 0)
        self.chat_page_layout.addWidget(self.chat_scroll_area)

        self.chat_stack.addWidget(self.chat_page) # index 0 聊天页
        self.settings_page = SettingWidget()
        self.chat_stack.addWidget(self.settings_page) # index 1 设置页
        self.game_page = QWidget()
        self.chat_stack.addWidget(self.game_page) # index 2 博弈页
        self.mindmap_page = QWidget()
        self.chat_stack.addWidget(self.mindmap_page) # index 3 心智云图页
        self.galgame_page = QWidget()
        self.chat_stack.addWidget(self.galgame_page) # index 4 恋爱冒险页
        self.vlay.addWidget(self.chat_stack, 1)

        self.sidebar[0] = lambda: self.chat_stack.setCurrentIndex(0)
        # 1: 心智云图 - 切换到心智云图组件
        self.sidebar[1] = lambda: self.chat_stack.setCurrentIndex(2)
        # 2: 性格博弈 - 切换到性格博弈组件
        self.sidebar[2] = lambda: self.chat_stack.setCurrentIndex(3)
        # 3: 恋爱冒险 - 切换到恋爱冒险组件
        self.sidebar[3] = lambda: self.chat_stack.setCurrentIndex(4)
        
        # 添加进度显示组件
        self.progress_widget = EnhancedProgressWidget(self.chat_area)
        self.vlay.addWidget(self.progress_widget)
        # 连接进度组件信号
        self.progress_widget.cancel_requested.connect(chat.cancel_current_task)
        
        self.input_wrap=QWidget(self.chat_area)
        self.input_wrap.setFixedHeight(60)  # 增加输入框包装器的高度，与字体大小匹配
        self.hlay=QHBoxLayout(self.input_wrap)
        self.hlay.setContentsMargins(0,0,0,0)
        self.hlay.setSpacing(8)
        self.prompt=QLabel('>',self.input_wrap)
        self.prompt.setStyleSheet(f"color:#fff;font:{fontsize}pt '{fontfam}';background:transparent;")
        self.hlay.addWidget(self.prompt)
        self.input = QTextEdit(self.input_wrap)
        self.input.setStyleSheet(f"""
            QTextEdit {{
                background: rgba(17,17,17,{int(config.ui.bg_alpha*255)});
                color: #fff;
                border-radius: 15px;
                border: 1px solid rgba(255, 255, 255, 50);
                font: {fontsize}pt '{fontfam}';
                padding: 8px;
            }}
        """)
        self.input.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.hlay.addWidget(self.input)
        
    def _init_buttons(self):
        # 初始化消息存储
        self._messages = {}
        self._message_counter = 0

        self.input.textChanged.connect(chat.adjust_input_height)
        self.input.installEventFilter(self)
        
        # 添加文档上传按钮
        self.upload_btn = ButtonFactory.create_action_button("upload", self.input_wrap)
        self.hlay.addWidget(self.upload_btn)
        # 连接文档上传按钮
        self.upload_btn.clicked.connect(document.upload_document)
        
        # 添加心智云图按钮
        self.mind_map_btn = ButtonFactory.create_action_button("mind_map", self.input_wrap)
        self.hlay.addWidget(self.mind_map_btn)
        # 连接心智云图按钮
        self.mind_map_btn.clicked.connect(mindmap.open_mind_map)

        # 添加博弈论启动/关闭按钮
        self.self_game_btn = ButtonFactory.create_action_button("self_game", self.input_wrap)
        self.self_game_btn.setToolTip("启动/关闭博弈论流程")
        self.hlay.addWidget(self.self_game_btn)
        # 连接博弈论按钮
        self.self_game_btn.clicked.connect(game.toggle_self_game)

        # 添加实时语音按钮
        self.voice_realtime_btn = ButtonFactory.create_action_button("voice_realtime", self.input_wrap)
        self.voice_realtime_btn.setToolTip("启动/关闭实时语音对话")
        self.hlay.addWidget(self.voice_realtime_btn)
        # 连接实时语音按钮
        self.voice_realtime_btn.clicked.connect(voice.toggle_voice_realtime)

        
    def _init_side(self):
        self.vlay.addWidget(self.input_wrap,0)
        # 将聊天区域添加到分割器
        self.main_splitter.addWidget(self.chat_area)
        
        # 侧栏（Live2D/图片显示区域）- 使用Live2D侧栏Widget
        self.side = Live2DSideWidget()
        self.collapsed_width = 480  # 收缩状态宽度
        self.expanded_width = 800  # 展开状态宽度
        self.side.setMinimumWidth(self.collapsed_width)  # 设置最小宽度为收缩状态
        self.side.setMaximumWidth(self.collapsed_width)  # 初始状态为收缩
        
        def _enter(e):
            self.side.set_background_alpha(int(BG_ALPHA * 0.5 * 255))
            self.side.set_border_alpha(80)
        # 优化侧栏的悬停效果，使用QPainter绘制
        self.side.enterEvent = _enter
        
        def _leave(e):
            self.side.set_background_alpha(int(BG_ALPHA * 255))
            self.side.set_border_alpha(50)
        self.side.leaveEvent = _leave
        
        # 设置鼠标指针，提示可点击
        self.side.setCursor(Qt.PointingHandCursor)

        # 创建包装函数，在编辑模式下不触发toggle_full_img
        original_toggle = side.toggle_full_img
        def wrapped_mouse_press(e):
            # 如果在编辑模式下，调用侧边栏自己的mousePressEvent
            if hasattr(self.side, 'edit_mode') and self.side.edit_mode:
                Live2DSideWidget.mousePressEvent(self.side, e)
            else:
                original_toggle(e)

        self.side.mousePressEvent = wrapped_mouse_press # 侧栏点击切换聊天/设置
        
        # 设置默认图片
        default_image = os.path.join(os.path.dirname(__file__), 'img/standby.png')
        if os.path.exists(default_image):
            self.side.set_fallback_image(default_image)
        
        # 连接Live2D侧栏的信号
        self.side.model_loaded.connect(live2d.on_live2d_model_loaded)
        self.side.error_occurred.connect(live2d.on_live2d_error)
        
        # 将侧栏添加到分割器
        self.main_splitter.addWidget(self.side)
        
        # 设置分割器的初始比例 - 侧栏收缩状态
        self.main_splitter.setSizes([self.sidebar_width, self.window_width - self.sidebar_width - self.collapsed_width - 20, self.collapsed_width])  # 大部分给聊天区域
        
        # 创建包含分割器的主布局
        self.main=QVBoxLayout(self)
        self.main.setContentsMargins(10,110,10,10)
        self.main.addWidget(self.main_splitter)
        self.setLayout(self.main)

        # 初始化Live2D
        self.side.initialize_live2d()

    def _init_end(self):
        self.resizeEvent(None)  # 强制自适应一次，修复图片初始尺寸
        # 加载历史记录（替换原_self_load_persistent_context_to_ui）
        chat.load_persistent_history(
            max_messages=config.api.max_history_rounds * 2
        )

        # 初始化主动交流功能
        self._init_active_communication()

        # 初始化AI日记功能
        self._init_ai_diary()

    def _init_active_communication(self):
        """初始化主动交流功能"""
        try:
            from voice.auth import get_active_comm_manager
            from nagaagent_core.vendors.PyQt5.QtCore import QTimer

            self.active_comm_manager = get_active_comm_manager()

            # 启动主动交流管理器
            if getattr(config.system, 'active_communication', False):
                self.active_comm_manager.start()

            # 创建定时器检查主动交流
            self.active_comm_timer = QTimer()
            self.active_comm_timer.timeout.connect(self._check_active_communication)

            # 每分钟检查一次（配置的检查间隔）
            interval = getattr(self.active_comm_manager, 'check_interval', 300) * 1000
            self.active_comm_timer.start(interval)

            # 初始化上次检查时间
            self._last_active_comm_check = 0

        except Exception as e:
            logger.error(f"初始化主动交流功能失败: {e}")
            self.active_comm_manager = None

    def _check_active_communication(self):
        """检查是否需要主动发起对话"""
        try:
            if not getattr(config.system, 'active_communication', False):
                return

            if not hasattr(self, 'active_comm_manager') or self.active_comm_manager is None:
                return

            # 检查是否应该发起主动交流（添加防重复检查）
            current_time = time.time()
            last_check = getattr(self, '_last_active_comm_check', 0)
            time_since_last_check = current_time - last_check

            # 至少间隔60秒才检查一次，避免频繁触发
            if time_since_last_check < 60:
                return

            self._last_active_comm_check = current_time

            # 检查是否应该发起主动交流
            message = self.active_comm_manager.get_initiated_message()
            if message:
                # 记录交互时间
                self.active_comm_manager.record_interaction()

                # 显示AI主动发起的消息
                try:
                    from ui.controller.tool_chat import chat
                    chat.add_user_message(config.system.ai_name, message)
                except Exception as inner_e:
                    logger.error(f"显示主动交流消息失败: {inner_e}")

        except Exception as e:
            logger.error(f"检查主动交流失败: {e}")

    def _init_ai_diary(self):
        """初始化AI日记功能"""
        try:
            from voice.auth import get_ai_diary_manager
            from nagaagent_core.vendors.PyQt5.QtCore import QTimer

            self.ai_diary_manager = get_ai_diary_manager()

            # 创建日记定时器（每天检查一次是否需要写日记）
            self.ai_diary_timer = QTimer()
            self.ai_diary_timer.timeout.connect(self._check_ai_diary)

            # 每24小时检查一次（86400000毫秒）
            self.ai_diary_timer.start(86400000)

            logger.info("AI日记功能初始化完成")

        except Exception as e:
            logger.error(f"初始化AI日记功能失败: {e}")
            self.ai_diary_manager = None

    def _check_ai_diary(self):
        """检查是否需要写日记"""
        try:
            if not getattr(config.system, 'diary_enabled', False):
                return

            if not hasattr(self, 'ai_diary_manager') or self.ai_diary_manager is None:
                return

            # 这里可以根据对话历史自动生成日记
            # 暂时不实现自动写日记，用户可以手动触发
            logger.debug("AI日记检查")

        except Exception as e:
            logger.error(f"检查AI日记失败: {e}")

    def write_ai_diary(self, content: str):
        """手动触发AI写日记"""
        try:
            from ui.controller.tool_chat import chat

            if not hasattr(self, 'ai_diary_manager') or self.ai_diary_manager is None:
                return

            auto_save = getattr(config.system, 'diary_auto_save', True)
            success = self.ai_diary_manager.write_diary(content, auto_save)

            if success:
                chat.add_user_message("系统", f"✅ AI日记已保存（共 {self.ai_diary_manager.get_diary_count()} 条）")
            else:
                chat.add_user_message("系统", "❌ AI日记保存失败")

        except Exception as e:
            logger.error(f"写AI日记失败: {e}")
            try:
                from ui.controller.tool_chat import chat
                chat.add_user_message("系统", f"❌ 写AI日记失败: {e}")
            except:
                pass
                return

            auto_save = getattr(config.system, 'diary_auto_save', True)
            success = self.ai_diary_manager.write_diary(content, auto_save)

            if success:
                chat.add_user_message("系统", f"✅ AI日记已保存（共 {self.ai_diary_manager.get_diary_count()} 条）")
            else:
                chat.add_user_message("系统", "❌ AI日记保存失败")

        except Exception as e:
            logger.error(f"写AI日记失败: {e}")
            chat.add_user_message("系统", f"❌ 写AI日记失败: {e}")

    def apply_ui_style(self):
        """根据最新配置刷新窗口外观"""
        refresh_ui_constants()
        self.setStyleSheet(f"""
            ChatWindow {{
                background: rgba(25, 25, 25, {WINDOW_BG_ALPHA});
                border-radius: 20px;
                border: 1px solid rgba(255, 255, 255, 30);
            }}
        """)

        alpha_px = int(BG_ALPHA * 255)
        fontfam, fontsize = 'Lucida Console', 16
        self.input.setStyleSheet(f"""
            QTextEdit {{
                background: rgba(17,17,17,{alpha_px});
                color: #fff;
                border-radius: 15px;
                border: 1px solid rgba(255, 255, 255, 50);
                font: {fontsize}pt '{fontfam}';
                padding: 8px;
            }}
        """)

        if hasattr(self.side, 'set_background_alpha'):
            self.side.set_background_alpha(alpha_px)
        if hasattr(self.side, 'set_border_alpha'):
            self.side.set_border_alpha(50)

        try:
            from ui.utils import message_renderer as mr
            mr.refresh_style_constants()
        except Exception:
            pass

        if hasattr(self.titlebar, 'update_style'):
            self.titlebar.update_style()

        try:
            from ui.controller.tool_chat import apply_config as apply_chat_tool_config
            apply_chat_tool_config()
        except Exception:
            pass

        self.update()



#==========MouseEvents==========
    # 添加整个窗口的拖动支持
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._offset = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._offset and event.buttons() & Qt.LeftButton:
            self.move(event.globalPos() - self._offset)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._offset = None
        event.accept()

    def paintEvent(self, event):
        """绘制窗口背景"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 绘制主窗口背景 - 使用可调节的透明度
        painter.setBrush(QBrush(QColor(25, 25, 25, WINDOW_BG_ALPHA)))
        painter.setPen(QColor(255, 255, 255, 30))
        painter.drawRoundedRect(self.rect(), 20, 20)
        
    def showEvent(self, event):
        """窗口显示事件"""
        super().showEvent(event)

        # 初始化任务服务的UI回调
        try:
            from system.task_service_manager import get_task_service_manager
            from ui.controller.tool_chat import chat

            task_service = get_task_service_manager()
            # chat 是 lazy 对象，直接访问其方法会触发初始化并返回实例
            chat_tool = chat  # 不需要调用 chat()，直接使用

            # 定义异步发送QQ消息的辅助函数
            async def _send_qq_message(message: str, sender_id: str, qq_wechat_agent):
                """异步发送QQ消息（旧函数，已弃用）- 保持向后兼容"""
                await _send_qq_message_with_mode(message, sender_id, qq_wechat_agent, enable_voice=True, reply_mode="both")

            async def _send_qq_message_with_mode(message: str, sender_id: str, qq_wechat_agent,
                                                  enable_voice: bool = True, reply_mode: str = "both"):
                """
                异步发送QQ消息，支持语音/文本模式

                参数:
                    message: 消息内容
                    sender_id: 发送者QQ号
                    qq_wechat_agent: QQ Agent实例
                    enable_voice: 是否启用语音
                    reply_mode: 回复模式 ("voice"/"text"/"both")
                """
                import sys
                import os
                import tempfile

                try:
                    logger.info(f"[任务服务] 发送消息模式: reply_mode={reply_mode}, enable_voice={enable_voice}")

                    # 根据配置决定发送方式
                    if reply_mode == "voice" and enable_voice:
                        # 纯语音模式：只发送语音
                        logger.info(f"[任务服务] 纯语音模式，发送语音消息")
                        await _send_qq_voice(message, sender_id, qq_wechat_agent)
                        return
                    elif reply_mode == "text":
                        # 纯文本模式：只发送文本
                        logger.info(f"[任务服务] 纯文本模式，发送文本消息")
                        await qq_wechat_agent.qq_adapter.send_message(int(sender_id), message)
                        logger.info(f"[任务服务] 文本消息已发送: {sender_id}")
                        return
                    elif reply_mode == "both" and enable_voice:
                        # 混合模式：语音+文本
                        logger.info(f"[任务服务] 混合模式，发送语音+文本")
                        await _send_qq_voice(message, sender_id, qq_wechat_agent)
                        await qq_wechat_agent.qq_adapter.send_message(int(sender_id), message)
                        logger.info(f"[任务服务] 语音+文本消息已发送: {sender_id}")
                        return
                    else:
                        # 默认：只发送文本
                        logger.info(f"[任务服务] 默认模式，发送文本消息")
                        await qq_wechat_agent.qq_adapter.send_message(int(sender_id), message)
                        logger.info(f"[任务服务] 文本消息已发送: {sender_id}")
                        return

                except Exception as e:
                    logger.error(f"[任务服务] 发送QQ消息失败: {e}")
                    import traceback
                    traceback.print_exc()

            async def _send_qq_voice(message: str, sender_id: str, qq_wechat_agent):
                """
                发送QQ语音消息

                参数:
                    message: 消息内容
                    sender_id: 发送者QQ号
                    qq_wechat_agent: QQ Agent实例
                """
                import sys
                import os
                import tempfile

                try:
                    # 生成音频
                    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
                    from voice.output.voice_integration import VoiceIntegration
                    voice_integration = VoiceIntegration()
                    audio_data = voice_integration._generate_audio_sync(message)

                    if audio_data:
                        # 保存为临时文件
                        audio_path = tempfile.mktemp(suffix=".mp3")
                        with open(audio_path, 'wb') as f:
                            f.write(audio_data)

                        logger.info(f"[任务服务] 音频已生成: {audio_path}")

                        # 发送语音
                        success = await qq_wechat_agent.qq_adapter.send_record_audio(int(sender_id), audio_path)
                        if success:
                            logger.info(f"[任务服务] 语音提醒已发送到QQ: {sender_id}")
                            # 删除临时文件
                            try:
                                os.unlink(audio_path)
                            except:
                                pass
                        else:
                            # 语音发送失败，回退到文本
                            await qq_wechat_agent.qq_adapter.send_message(int(sender_id), message)
                            logger.info(f"[任务服务] 文本提醒已发送到QQ: {sender_id}")
                    else:
                        # 音频生成失败，发送文本
                        await qq_wechat_agent.qq_adapter.send_message(int(sender_id), message)
                        logger.info(f"[任务服务] 文本提醒已发送到QQ: {sender_id}")
                except Exception as e:
                    logger.error(f"[任务服务] 发送QQ语音提醒失败: {e}")
                    import traceback
                    traceback.print_exc()

            async def _send_cached_qq_message(message: str, message_type: str, original_content: str, sender_id: str, qq_wechat_agent):
                """发送缓存的QQ消息"""
                await _send_qq_message(message, sender_id, qq_wechat_agent)
                logger.info(f"[任务服务] 缓存消息已发送到QQ: {sender_id}")

            def on_active_message(message):
                """处理主动消息（如提醒）- 支持ActiveMessage对象或旧式参数"""
                from system.active_communication import ActiveMessage

                # 兼容旧式调用和新式调用
                if isinstance(message, ActiveMessage):
                    # 新式：ActiveMessage对象
                    msg_content = message.content
                    msg_type = message.message_type.value
                    original_input = message.context.get("original_input", "") if message.context else ""
                elif isinstance(message, (str, dict)):
                    # 旧式：message是字符串或dict
                    # 兼容不同参数数量
                    args = message if isinstance(message, (list, tuple)) else [message, "suggestion"]
                    
                    if len(args) >= 1:
                        msg_content = args[0]
                    else:
                        msg_content = ""
                    
                    if len(args) >= 2:
                        msg_type = args[1]
                    else:
                        msg_type = "suggestion"
                    
                    if len(args) >= 3:
                        original_input = args[2]
                    else:
                        original_input = msg_content
                else:
                    logger.warning(f"[任务服务] 未知的消息类型: {type(message)}")
                    return

                logger.info(f"[任务服务] on_active_message 被调用: msg_type={msg_type}")

                # original_content 是原始任务内容，可能包含 [发送者QQ:xxx]
                task_content = original_input

                logger.info(f"[任务服务] task_content: {task_content}")

                # 1. 通过信号机制安全地显示到UI（确保在主线程执行）
                if msg_content and msg_content.strip():
                    # 使用信号机制，确保在主线程中更新UI
                    chat_tool.active_message_received.emit(msg_content, msg_type or "suggestion", task_content)
                    logger.info(f"[任务服务] 自主消息已通过信号发送到UI")

                # 2. 如果最近有QQ会话，也发送到QQ（根据配置发送语音或文本）
                logger.info(f"[任务服务] 开始尝试发送到QQ...")
                try:
                    # 从MCP_REGISTRY获取QQ/微信 Agent实例
                    from mcpserver.mcp_registry import MCP_REGISTRY
                    qq_wechat_agent = MCP_REGISTRY.get("QQ/微信集成")

                    if qq_wechat_agent and hasattr(qq_wechat_agent, 'qq_adapter') and qq_wechat_agent.qq_adapter:
                        # 从任务内容中提取QQ号码（格式：[发送者QQ:xxx]）
                        import re
                        qq_match = re.search(r'\[发送者QQ:(\d+)\]', task_content)
                        if qq_match:
                            sender_id = qq_match.group(1)
                            logger.info(f"[任务服务] 从任务内容中提取到QQ号: {sender_id}")
                        else:
                            # 回退：获取最近的QQ会话ID
                            from apiserver.message_manager import message_manager
                            sessions = message_manager.get_all_sessions_api()
                            logger.info(f"[任务服务] 当前会话列表: {len(sessions.get('sessions', []))} 个")
                            
                            # 安全检查：确保sessions是字典类型
                            if not isinstance(sessions, dict):
                                logger.warning(f"[任务服务] sessions类型错误: {type(sessions)}, 期望dict")
                                sender_id = None
                            else:
                                # 获取会话字典并转换为列表
                                sessions_dict = sessions.get('sessions', {})
                                # 将字典转换为列表，包含session_id信息
                                sessions_list = []
                                if isinstance(sessions_dict, dict):
                                    for sid, sinfo in sessions_dict.items():
                                        sinfo_copy = sinfo.copy()
                                        sinfo_copy['session_id'] = sid
                                        sessions_list.append(sinfo_copy)
                                elif isinstance(sessions_dict, list):
                                    sessions_list = sessions_dict

                                qq_sessions = [s for s in sessions_list if isinstance(s, dict) and s.get('session_id', '').startswith('qq_')]
                                logger.info(f"[任务服务] QQ会话数量: {len(qq_sessions)}, 总会话数: {len(sessions_list)}")

                            # 检查是否有新的QQ会话建立
                            current_qq_count = len(qq_sessions)
                            has_new_session = current_qq_count > config.window._last_qq_session_count

                            if qq_sessions:
                                # 使用最近的QQ会话（根据last_activity排序）
                                latest_session = max(qq_sessions, key=lambda s: s.get('last_activity', 0))
                                session_id = latest_session.get('session_id', '')
                                sender_id = session_id.replace('qq_', '')
                                logger.info(f"[任务服务] 使用最近的QQ会话: {session_id}, last_activity: {latest_session.get('last_activity', 0)}")

                                # 暂时禁用缓存消息发送（避免发送过期的自主消息）
                                # if has_new_session and config.window._cached_qq_messages:
                                #     logger.info(f"[任务服务] 检测到新会话，准备发送 {len(config.window._cached_qq_messages)} 条缓存消息...")
                                #     import asyncio
                                #     loop = asyncio.get_event_loop()
                                #     for cached_msg in config.window._cached_qq_messages.copy():
                                #         try:
                                #             asyncio.run_coroutine_threadsafe(
                                #                 _send_qq_message(cached_msg['message'], sender_id, qq_wechat_agent),
                                #                 loop
                                #             ).add_done_callback(
                                #                 lambda fut, msg=cached_msg: (
                                #                     config.window._cached_qq_messages.remove(msg),
                                #                     logger.info(f"[任务服务] 缓存消息已发送: {msg['message'][:30]}...")
                                #                 ) if not fut.exception() else logger.error(f"[任务服务] 发送缓存消息失败: {fut.exception()}")
                                #             )
                                #         except Exception as e:
                                #             logger.error(f"[任务服务] 发送缓存消息失败: {e}")
                                logger.debug(f"[任务服务] 缓存消息发送已禁用")

                                # 当前消息也发送 - 支持语音/文本模式
                                if sender_id and sender_id.isdigit():
                                    import asyncio
                                    loop = asyncio.get_event_loop()
                                    if loop and loop.is_running():
                                        # 检查QQ配置，决定发送模式 - 直接读取config.json
                                        from pathlib import Path
                                        from nagaagent_core.vendors import json5
                                        from nagaagent_core.vendors.charset_normalizer import from_path

                                        config_path = Path(__file__).parent.parent / "config.json"
                                        qq_config = {}
                                        enable_voice = True
                                        reply_mode = "both"

                                        try:
                                            charset_results = from_path(str(config_path))
                                            encoding = charset_results.best().encoding if charset_results else "utf-8"

                                            with open(config_path, 'r', encoding=encoding) as f:
                                                config_data = json5.load(f)

                                            qq_config = config_data.get("qq_wechat", {}).get("qq", {})
                                            enable_voice = qq_config.get("enable_voice", True)
                                            reply_mode = qq_config.get("reply_mode", "both")
                                        except Exception as e:
                                            logger.error(f"[任务服务] 读取QQ配置失败: {e}")

                                        logger.info(f"[任务服务] QQ配置: enable_voice={enable_voice}, reply_mode={reply_mode}")

                                        # 使用新的发送函数，支持语音/文本模式
                                        asyncio.run_coroutine_threadsafe(
                                            _send_qq_message_with_mode(
                                                msg_content, sender_id, qq_wechat_agent,
                                                enable_voice=enable_voice,
                                                reply_mode=reply_mode
                                            ),
                                            loop
                                        )
                                        logger.info(f"[任务服务] 提醒已提交到QQ队列: {sender_id}")

                                # 更新会话计数
                                config.window._last_qq_session_count = current_qq_count
                            else:
                                # 没有QQ会话，不再缓存消息（避免发送过期的自主消息）
                                logger.warning("[任务服务] 没有找到QQ会话，消息不会缓存")
                                # config.window._cached_qq_messages.append({
                                #     'message': message,
                                #     'message_type': message_type,
                                #     'original_content': task_content,
                                #     'timestamp': time.time()
                                # })
                                # logger.info(f"[任务服务] 消息已缓存，当前缓存数量: {len(config.window._cached_qq_messages)}")
                                sender_id = None

                            # 更新会话计数（即使没有会话也要更新）
                            config.window._last_qq_session_count = current_qq_count
                    else:
                        logger.warning(f"[任务服务] qq_wechat_agent或qq_adapter不可用")
                except Exception as e:
                    logger.error(f"[任务服务] 发送提醒到QQ失败: {e}")
                    import traceback
                    traceback.print_exc()

            task_service.set_ui_message_callback(on_active_message)
            print(f"[任务服务] UI回调已设置")
        except Exception as e:
            print(f"[任务服务] 设置UI回调失败: {e}")
            import traceback
            traceback.print_exc()

        # 其他初始化代码...

        self.setFocus()
        self.input.setFocus()
        # 图片初始化现在由Live2DSideWidget处理
        self._img_inited = True

    async def _send_cached_qq_messages_async(self, sender_id: str, qq_wechat_agent):
        """发送所有缓存的QQ消息（供外部调用）- 已禁用"""
        try:
            # 暂时禁用缓存消息发送（避免发送过期的自主消息）
            logger.info(f"[缓存消息] 缓存消息发送功能已禁用")
            return

            # 原始实现（已禁用）
            # if not hasattr(self, '_cached_qq_messages') or not self._cached_qq_messages:
            #     logger.info(f"[缓存消息] 没有待发送的缓存消息")
            #     return
            #
            # logger.info(f"[缓存消息] 准备发送 {len(self._cached_qq_messages)} 条缓存消息到QQ: {sender_id}")
            #
            # # 发送所有缓存消息
            # for cached_msg in self._cached_qq_messages.copy():
            #     try:
            #         # 生成音频并发送
            #         import asyncio
            #         import os
            #         import tempfile
            #
            #         # 生成音频
            #         from voice.output.voice_integration import VoiceIntegration
            #         voice_integration = VoiceIntegration()
            #         audio_data = voice_integration._generate_audio_sync(cached_msg['message'])
            #
            #         if audio_data:
            #             # 保存为临时文件
            #             audio_path = tempfile.mktemp(suffix=".mp3")
            #             with open(audio_path, 'wb') as f:
            #                 f.write(audio_data)
            #
            #             logger.info(f"[缓存消息] 音频已生成: {audio_path}")
            #
            #             # 发送语音
            #             success = await qq_wechat_agent.qq_adapter.send_record_audio(int(sender_id), audio_path)
            #             if success:
            #                 logger.info(f"[缓存消息] 语音已发送到QQ: {sender_id}")
            #                 # 删除临时文件
            #                 try:
            #                     os.unlink(audio_path)
            #                 except:
            #                     pass
            #             else:
            #                 # 语音发送失败，回退到文本
            #                 await qq_wechat_agent.qq_adapter.send_message(int(sender_id), cached_msg['message'])
            #                 logger.info(f"[缓存消息] 文本已发送到QQ: {sender_id}")
            #         else:
            #             # 音频生成失败，发送文本
            #             await qq_wechat_agent.qq_adapter.send_message(int(sender_id), cached_msg['message'])
            #             logger.info(f"[缓存消息] 文本已发送到QQ: {sender_id}")
            #
            #         self._cached_qq_messages.remove(cached_msg)
            #         logger.info(f"[缓存消息] 已发送: {cached_msg['message'][:30]}...")
            #     except Exception as e:
            #         logger.error(f"[缓存消息] 发送失败: {e}")

            logger.info(f"[缓存消息] 已完成，剩余缓存消息: {len(self._cached_qq_messages)} 条")

        except Exception as e:
            logger.error(f"[缓存消息] 处理失败: {e}")
            import traceback
            traceback.print_exc()
        
    def resizeEvent(self, e):
        if getattr(self, '_animating', False):  # 动画期间跳过所有重绘操作，避免卡顿
            return
        # 图片调整现在由Live2DSideWidget内部处理
        super().resizeEvent(e)
    
    def eventFilter(self, obj, event):
        """事件过滤器：处理输入框的键盘事件，实现回车发送、Shift+回车换行"""
        # 仅处理输入框（self.input）的事件
        if obj != self.input:
            return super().eventFilter(obj, event)

        # 仅处理「键盘按下」事件
        if event.type() == QEvent.KeyPress:
            # 捕获两种回车按键：主键盘回车（Key_Return）、小键盘回车（Key_Enter）
            is_enter_key = event.key() in (Qt.Key_Return, Qt.Key_Enter)
            # 判断是否按住了Shift键
            is_shift_pressed = event.modifiers() & Qt.ShiftModifier

            if is_enter_key:
                if not is_shift_pressed:
                    # 纯回车：发送消息，阻止默认换行
                    chat.on_send()
                    return True  # 返回True表示事件已处理，不传递给输入框
                else:
                    # Shift+回车：放行事件，让输入框正常换行
                    return False  # 返回False表示事件继续传递

        # 其他事件（如普通输入）：正常放行
        return super().eventFilter(obj, event)
    
    
#====================
