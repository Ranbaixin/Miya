from nagaagent_core.vendors.PyQt5.QtWidgets import QLabel
from ..utils.response_util import extract_message
from ui.utils.message_renderer import MessageRenderer
from ui.utils.simple_http_client import SimpleHttpClient, SimpleBatchClient
from system.config import config, AI_NAME, logger
from nagaagent_core.vendors.PyQt5.QtCore import QThread, QCoreApplication, Qt, QTimer, QMetaObject, QObject, pyqtSignal
import time
from typing import Dict, Optional


def get_api_url(endpoint: str) -> str:
    """获取API URL，本地调用时使用127.0.0.1而非0.0.0.0"""
    host = config.api_server.host
    # 如果是0.0.0.0，本地调用时使用127.0.0.1
    if host == "0.0.0.0":
        host = "127.0.0.1"
    return f"http://{host}:{config.api_server.port}{endpoint}"


class ChatTool(QObject):
    # 定义信号用于线程间通信
    tool_ai_response_received = pyqtSignal(str)
    active_message_received = pyqtSignal(str, str, str)  # 消息内容, 消息类型, 原始内容

    def __init__(self, window):
        super().__init__()
        self.window = window
        self.current_response = ""  # 当前响应缓冲
        self.scroll_timer = QTimer(window)
        self.last_send_time = 0  # 上次发送消息的时间戳
        self.send_debounce_time = 500  # 防抖动时间（毫秒）
        # 外部依赖
        self.chat_layout = window.chat_layout
        self.chat_scroll_area = window.chat_scroll_area
        self.progress_widget = window.progress_widget
        self.user_name = config.ui.user_name
        self.ai_name = AI_NAME
        self.streaming_mode = config.system.stream_mode

        # 消息管理
        self._messages: Dict[str, Dict] = {}  # 消息存储：ID -> 消息信息
        self.message_counter = 0  # 消息ID计数器

        # 流式处理状态
        self.current_message_id: Optional[str] = None  # 当前处理的消息ID
        self.current_response = ""  # 当前响应内容
        self.last_update_time = 0  # 上次UI更新时间（用于节流）

        # 打字机效果相关
        self.stream_typewriter_buffer = ""
        self.stream_typewriter_index = 0
        self.stream_typewriter_timer: Optional[QTimer] = None
        self.non_stream_timer: Optional[QTimer] = None
        self.non_stream_text = ""
        self.non_stream_index = 0
        self.non_stream_message_id = None

        self.current_ai_voice_message_id = None
        # HTTP客户端管理
        self.http_client = None

        # 工具调用状态
        self.in_tool_call_mode = False

        # 连接信号
        self.tool_ai_response_received.connect(self._handle_tool_ai_response_safe)
        self.active_message_received.connect(self._handle_active_message_safe)

    def adjust_input_height(self):
        window = self.window
        doc = window.input.document()
        h = int(doc.size().height()) + 10
        window.input.setFixedHeight(min(max(60, h), 150))  # 增加最小高度，与字体大小匹配
        window.input_wrap.setFixedHeight(window.input.height())

    def add_user_message(self, name, content, is_streaming=False):
        window = self.window
        """添加用户消息"""
        msg = extract_message(content)
        content_html = str(msg).replace('\n', '\n\n')#.replace('\n', '<br>')

        # 生成消息ID
        if not self.message_counter:
            self.message_counter = 0
        self.message_counter += 1
        message_id = f"msg_{self.message_counter}"

        # 初始化消息存储
        if self._messages:
            self._messages = {}

        # 存储消息信息
        self._messages[message_id] = {
            'name': name,
            'content': content_html,
            'full_content': content,
            'dialog_widget': None
        }

        # 使用消息渲染器创建对话框
        if name == "系统":
            message_dialog = MessageRenderer.create_system_message(name, content_html, window.chat_content)
        else:
            message_dialog = MessageRenderer.create_user_message(name, content_html, window.chat_content)

        # 存储对话框引用
        self._messages[message_id]['dialog_widget'] = message_dialog

        # 先移除stretch
        stretch_found = False
        stretch_index = -1
        for i in reversed(range(window.chat_layout.count())):
            item = window.chat_layout.itemAt(i)
            if item and not item.widget():  # 找到stretch
                window.chat_layout.removeItem(item)
                stretch_found = True
                stretch_index = i
                break

        # 添加消息
        window.chat_layout.addWidget(message_dialog)

        # 重新添加stretch到最后
        window.chat_layout.addStretch()

        # 滚动到底部
        self.smart_scroll_to_bottom()

        # 记录用户交互时间（用于主动交流功能）
        self._record_interaction_time()

        return message_id

    def _record_interaction_time(self):
        """记录用户交互时间"""
        try:
            if hasattr(self.window, 'active_comm_manager') and self.window.active_comm_manager:
                self.window.active_comm_manager.record_interaction()
        except Exception as e:
            logger.error(f"记录交互时间失败: {e}")

    def on_send(self):
        # 0. 防止重复提交 - 检查时间间隔
        current_time = time.time() * 1000  # 转换为毫秒
        if current_time - self.last_send_time < self.send_debounce_time:
            logger.debug(f"忽略重复提交（距离上次仅 {current_time - self.last_send_time:.0f}ms）")
            return

        # 1. 获取并验证用户输入
        user_input = self.window.input.toPlainText().strip()
        if not user_input:
            return

        # 记录发送时间
        self.last_send_time = current_time

        # 处理日记命令
        if user_input.startswith('/写日记 ') or user_input == '/写日记':
            # 提取日记内容（去除命令前缀）
            if user_input == '/写日记':
                # 让AI自己生成日记
                diary_prompt = f"请用{config.system.ai_name}的人设口吻，根据最近的对话内容写一篇简短的日记。"
                self.window.input.clear()
                self.add_user_message(config.ui.user_name, diary_prompt)
                # 发送这个提示词让AI写日记
                if self.streaming_mode:
                    self._send_stream_request(diary_prompt)
                else:
                    self._send_non_stream_request(diary_prompt)
            else:
                # 用户提供了日记内容
                diary_content = user_input[4:].strip()  # 去掉 "/写日记 "
                self.window.input.clear()
                self.add_user_message(config.ui.user_name, user_input)

                # 保存日记
                if hasattr(self.window, 'write_ai_diary'):
                    self.window.write_ai_diary(diary_content)
            return

        # 2. 清理所有历史状态（合并关联的清理逻辑）
        self._cleanup_all_states()

        # 3. 显示用户消息并清空输入框
        self.add_user_message(config.ui.user_name, user_input)
        self.window.input.clear()

        # 4. 根据模式分发请求（核心分支逻辑）
        from .tool_game import game
        if game.self_game_enabled:
            self._send_self_game_request(user_input)
        else:
            if self.streaming_mode:
                self._send_stream_request(user_input)
            else:
                self._send_non_stream_request(user_input)

    def _cleanup_all_states(self):
        """合并：清理打字机、消息ID、运行中任务等所有状态"""
        # 清理非流式打字机
        if self.non_stream_timer and self.non_stream_timer.isActive():
            self.non_stream_timer.stop()
            # 不调用deleteLater，直接设为None避免重复清理
            self.non_stream_timer = None
            # 完成显示剩余文本（仅一次）
            if self.non_stream_text and self.non_stream_message_id and self.current_message_id == self.non_stream_message_id:
                self.update_last_message(self.non_stream_text)
        # 重置非流式状态变量
        self.non_stream_timer = self.non_stream_text = self.non_stream_index = self.non_stream_message_id = None

        # 清理流式打字机
        if self.stream_typewriter_timer and self.stream_typewriter_timer.isActive():
            self.stream_typewriter_timer.stop()
            self.stream_typewriter_timer.deleteLater()
        self.stream_typewriter_timer = None  # 重置流式状态

        # 清理消息ID和响应缓冲
        self.current_message_id = self.current_ai_voice_message_id = None
        self.current_response = ""

        # 终止运行中的HTTP客户端
        if self.http_client and self.http_client.isRunning():
            self.cancel_current_task()
            self.http_client.deleteLater()
            self.http_client = None

    def _send_self_game_request(self, user_input):
        """博弈论模式（非流式）请求"""
        api_url = get_api_url("/chat")
        data = self._build_request_data(user_input, stream=False, use_self_game=True)

        self.http_client = SimpleBatchClient(api_url, data)
        self._bind_batch_client_signals(self.http_client, "博弈论")
        self.progress_widget.set_thinking_mode()
        self.http_client.start()

    def _send_stream_request(self, user_input):
        """普通流式请求"""
        api_url = get_api_url("/chat/stream")
        data = self._build_request_data(user_input, stream=True, use_self_game=False)

        self.http_client = SimpleHttpClient(api_url, data)
        self._bind_stream_client_signals(self.http_client)
        self.progress_widget.set_thinking_mode()
        self.http_client.start()

    def _send_non_stream_request(self, user_input):
        """普通非流式请求"""
        api_url = get_api_url("/chat")
        data = self._build_request_data(user_input, stream=False, use_self_game=False)

        self.http_client = SimpleBatchClient(api_url, data)
        self._bind_batch_client_signals(self.http_client, "非流式")
        self.progress_widget.set_thinking_mode()
        self.http_client.start()

    # 保留必要的工具方法（未过度拆分）
    def _build_request_data(self, user_input, stream, use_self_game):
        """构建请求数据（复用逻辑）"""
        data = {
            "message": user_input,
            "stream": stream,
            "use_self_game": use_self_game,
            "session_id": self._get_current_session_id()
        }
        from system.config import config as _cfg
        if _cfg.system.voice_enabled and _cfg.voice_realtime.voice_mode in ["hybrid", "end2end"]:
            data["return_audio"] = True
        return data

    def _bind_batch_client_signals(self, client, error_prefix):
        """绑定批量HTTP客户端的信号"""
        client.status_changed.connect(lambda st: self.progress_widget.status_label.setText(st))
        client.error_occurred.connect(lambda err: (
            self.progress_widget.stop_loading(),
            self.add_user_message("系统", f"❌ {error_prefix}调用错误: {err}")
        ))
        client.response_received.connect(lambda text: (
            self.progress_widget.stop_loading(),
            self.start_non_stream_typewriter(text)
        ))
        
    def _bind_stream_client_signals(self, client):
        """绑定流式HTTP客户端的信号"""
        client.status_changed.connect(lambda st: self.progress_widget.status_label.setText(st))
        client.error_occurred.connect(lambda err: (
            self.progress_widget.stop_loading(),
            self.add_user_message("系统", f"❌ 流式调用错误: {err}")
        ))
        client.chunk_received.connect(self._handle_stream_chunk)
        client.response_complete.connect(self.finalize_streaming_response)

    def _handle_stream_chunk(self, text):
        """处理流式响应片段（文本已经由HTTP客户端解码）"""
        if text.startswith(('session_id: ', 'audio_url: ')):
            return
        self.append_response_chunk(text)

    def add_system_message(self, content: str) -> str:
        """添加系统消息到聊天界面"""
        msg = extract_message(content)
        content_html = str(msg)  # .replace('\\n', '\n').replace('\n', '<br>')

        # 生成消息ID
        self.message_counter += 1
        message_id = f"msg_{self.message_counter}"

        # 创建系统消息对话框
        parent_widget = self.chat_layout.parentWidget()
        message_dialog = MessageRenderer.create_system_message(
            "系统", content_html, parent_widget
        )

        # 存储消息信息
        self._messages[message_id] = {
            'name': "系统",
            'content': content_html,
            'full_content': content,
            'dialog_widget': message_dialog,
            'is_ai': False,
            'is_system': True
        }

        # 添加到布局
        self._remove_layout_stretch()
        self.chat_layout.addWidget(message_dialog)
        self.chat_layout.addStretch()

        # 滚动到底部
        self.smart_scroll_to_bottom()
        return message_id

    def add_ai_message(self, content: str = "") -> str:
        """添加AI消息到聊天界面（流式处理时初始化为空消息）"""
        # 对于AI回复，直接使用原始内容，不经过extract_message处理
        # 因为AI回复通常是纯文本或Markdown格式，不是JSON格式
        content_html = content

        logger.info(f"[UI] 添加AI消息，内容长度: {len(content_html)}")

        # 生成消息ID
        self.message_counter += 1
        message_id = f"msg_{self.message_counter}"

        # 创建AI消息对话框 - 使用窗口作为父组件
        parent_widget = self.window  # 直接使用窗口作为父组件
        message_dialog = MessageRenderer.create_assistant_message(
            self.ai_name, content_html, parent_widget
        )

        # 存储消息信息
        self._messages[message_id] = {
            'name': self.ai_name,
            'content': content_html,
            'full_content': content,
            'dialog_widget': message_dialog,
            'is_ai': True
        }

        # 添加到布局
        self._remove_layout_stretch()
        self.chat_layout.addWidget(message_dialog)
        self.chat_layout.addStretch()

        # 滚动到底部
        self.smart_scroll_to_bottom()

        return message_id

    def update_last_message(self, new_text):
        """更新最后一条消息的内容"""
        line=new_text.count('\n')
        # 处理消息格式化
        msg = extract_message(new_text)
        from nagaagent_core.vendors.markdown import markdown
        content_html = str(msg).replace('\n', '<br>')
        content_html = markdown(content_html, extensions=['extra', 'codehilite'])

        # 优先使用当前消息ID（流式更新时设置的）
        message_id = None
        message_source = ""
        if self.current_message_id and self.current_message_id:
            message_id = self.current_message_id
            message_source = "text"
        elif self.current_ai_voice_message_id and self.current_ai_voice_message_id:
            message_id = self.current_ai_voice_message_id
            message_source = "voice"
        elif self._messages:
            # 如果没有当前消息ID，查找最后一个消息
            message_id = max(self._messages.keys(), key=lambda x: int(x.split('_')[-1]) if '_' in x else 0)
            message_source = "last"

        # 更新消息内容
        if message_id and message_id in self._messages:
            message_info = self._messages[message_id]

            # 更新存储的消息信息
            message_info['content'] = content_html
            message_info['full_content'] = new_text

            # 尝试使用MessageRenderer更新（更可靠）
            if 'dialog_widget' in message_info and message_info['dialog_widget']:
                try:
                    from ui.utils.message_renderer import MessageRenderer
                    MessageRenderer.update_message_content(message_info['dialog_widget'], content_html)
                except Exception as e:
                    # 如果MessageRenderer失败，使用备用方法
                    content_label = message_info['dialog_widget'].findChild(QLabel)
                    if content_label:
                        content_label.setText(content_html)
                        content_label.setTextFormat(1)  # Qt.RichText
                        content_label.setWordWrap(True)
            # 或者直接更新widget
            elif 'widget' in message_info:
                content_label = message_info['widget'].findChild(QLabel)
                if content_label:
                    # 使用HTML格式化的内容
                    content_label.setText(content_html)
                    # 确保标签可以正确显示HTML
                    content_label.setTextFormat(1)  # Qt.RichText
                    content_label.setWordWrap(True)

        # 自动滚动到底部，确保最新消息可见（使用智能滚动，不打扰正在查看历史的用户）
        self.smart_scroll_to_bottom()

    def clear_chat_history(self):
        """清除所有聊天历史"""
        # 清除UI组件
        for msg_id, msg_info in self._messages.items():
            if msg_info['dialog_widget']:
                msg_info['dialog_widget'].deleteLater()

        # 清除布局
        while self.chat_layout.count() > 0:
            item = self.chat_layout.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()

        # 重置状态
        self._messages.clear()
        self.message_counter = 0
        self.current_message_id = None
        self.current_response = ""

        # 恢复stretch
        self.chat_layout.addStretch()

    def load_persistent_history(self, max_messages: int = 20):
        """从持久化存储加载历史对话"""
        try:
            # 调用MessageRenderer加载历史
            ui_messages = MessageRenderer.load_persistent_context_to_ui(
                parent_widget=self.chat_layout.parentWidget(),
                max_messages=max_messages
            )

            if not ui_messages:
                logger.info("未加载到历史对话")
                return

            # 清空现有布局
            self._remove_layout_stretch()
            while self.chat_layout.count() > 0:
                item = self.chat_layout.takeAt(0)
                if item and item.widget():
                    item.widget().deleteLater()

            # 加载历史消息到UI和存储
            for message_id, message_info, dialog in ui_messages:
                self.chat_layout.addWidget(dialog)
                self._messages[message_id] = message_info
                self.message_counter = max(self.message_counter, int(message_id.split('_')[-1]))

            # 恢复stretch并滚动到底部
            self.chat_layout.addStretch()
            self.smart_scroll_to_bottom()
            logger.info(f"加载完成 {len(ui_messages)} 条历史对话")

        except Exception as e:
            logger.error(f"加载历史对话失败: {str(e)}")
            self.add_system_message(f"❌ 加载历史对话失败: {str(e)}")

        # ------------------------------
        # 工具调用处理
        # ------------------------------

    def handle_tool_call(self, notification: str):
        """处理工具调用通知"""
        # 标记进入工具调用模式
        self.in_tool_call_mode = True

        # 创建专门的工具调用内容对话框
        parent_widget = self.chat_layout.parentWidget()
        tool_call_dialog = MessageRenderer.create_tool_call_content_message(notification, parent_widget)

        # 设置嵌套对话框内容
        nested_title = "工具调用详情"
        nested_content = f"""
工具名称: {notification}
状态: 正在执行...
时间: {time.strftime('%H:%M:%S')}
        """.strip()
        tool_call_dialog.set_nested_content(nested_title, nested_content)

        # 生成消息ID
        self.message_counter += 1
        message_id = f"tool_call_{self.message_counter}"

        # 存储工具调用消息信息
        self._messages[message_id] = {
            'name': '工具调用',
            'content': notification,
            'full_content': notification,
            'dialog_widget': tool_call_dialog,
            'is_tool_call': True
        }

        # 添加到布局
        self._remove_layout_stretch()
        self.chat_layout.addWidget(tool_call_dialog)
        self.chat_layout.addStretch()

        # 滚动到底部
        self.smart_scroll_to_bottom()

        # 在状态栏显示工具调用状态
        self.progress_widget.status_label.setText(f"🔧 {notification}")
        logger.debug(f"工具调用: {notification}")

    def handle_tool_result(self, result: str):
        """处理工具执行结果"""
        # 查找最近的工具调用对话框并更新
        tool_call_updated = False
        if self._messages:
            for message_id, message_info in reversed(list(self._messages.items())):
                if message_id.startswith('tool_call_'):
                    dialog_widget = message_info.get('dialog_widget')
                    if dialog_widget:
                        # 更新工具调用对话框显示结果
                        MessageRenderer.update_message_content(dialog_widget, f"✅ {result}")

                        # 更新嵌套对话框内容
                        if dialog_widget.set_nested_content:
                            nested_title = "工具调用结果"
                            nested_content = f"""
工具名称: {message_info.get('content', '未知工具')}
状态: 执行完成 ✅
时间: {time.strftime('%H:%M:%S')}
结果: {result[:200]}{'...' if len(result) > 200 else ''}
                            """.strip()
                            dialog_widget.set_nested_content(nested_title, nested_content)
                    tool_call_updated = True
                    break

        # 工具调用完成，退出工具调用模式
        self.in_tool_call_mode = False

        # 在状态栏显示工具执行结果
        self.progress_widget.status_label.setText(f"✅ {result[:50]}...")
        logger.debug(f"工具结果: {result}")

        # 如果更新了工具调用对话框，强制刷新UI显示
        if tool_call_updated:
            # 确保UI刷新显示最新的工具结果
            self.smart_scroll_to_bottom()
            # 触发UI重绘
            self.window.update()

    def handle_tool_completed_with_ai_response(self, ai_response: str):
        """处理工具执行完成后的AI回复（线程安全入口）"""
        # 通过信号机制确保在主线程中执行
        self.tool_ai_response_received.emit(ai_response)

    def _handle_tool_ai_response_safe(self, ai_response: str):
        """线程安全地处理工具执行完成后的AI回复"""
        try:
            logger.info(f"[UI] 收到工具完成后的AI回复，内容长度: {len(ai_response)}")
            logger.info(f"[UI] 当前线程: {QThread.currentThread()}")

            # 停止加载状态
            self.progress_widget.stop_loading()

            # 添加AI回复到聊天界面
            if ai_response and ai_response.strip():
                # 直接显示完整的AI回复，不使用打字机效果
                logger.info(f"[UI] 直接显示完整AI回复")
                self.add_ai_message(ai_response)
                logger.info(f"[UI] AI回复已直接添加到聊天界面")

                # 保存对话历史到API服务器
                self._save_tool_conversation_to_history(ai_response)
            else:
                logger.warning(f"[UI] 收到空的AI回复")

        except Exception as e:
            logger.error(f"[UI] 处理工具完成后的AI回复失败: {e}")
            self.add_system_message(f"❌ 显示工具结果失败: {str(e)}")

    def _handle_active_message_safe(self, message: str, message_type: str, original_content: str):
        """线程安全地处理自主消息"""
        try:
            logger.info(f"[UI] 收到自主消息，类型: {message_type}, 长度: {len(message)}")
            logger.info(f"[UI] 当前线程: {QThread.currentThread()}")

            # 添加AI回复到聊天界面
            if message and message.strip():
                logger.info(f"[UI] 直接显示自主消息")
                self.add_ai_message(message)
                logger.info(f"[UI] 自主消息已添加到聊天界面")

                # 播放TTS语音
                self._play_active_message_tts(message)

        except Exception as e:
            logger.error(f"[UI] 处理自主消息失败: {e}")
            self.add_system_message(f"❌ 显示自主消息失败: {str(e)}")

    def _play_active_message_tts(self, message: str):
        """播放自主消息的TTS语音"""
        try:
            # 检查是否启用了语音功能
            from system.config import config as _cfg
            if not _cfg.system.voice_enabled:
                logger.debug(f"[UI] 语音功能未启用，跳过TTS播放")
                return

            voice_mode = _cfg.voice_realtime.voice_mode
            # 自主消息支持所有语音模式（包括 auto/local/hybrid/end2end）
            # 与用户交互的实时语音不同，自主消息可以独立播放
            if voice_mode not in ["auto", "local", "hybrid", "end2end"]:
                logger.warning(f"[UI] 未知的语音模式: {voice_mode}")
                return

            logger.info(f"[UI] 准备播放自主消息TTS，模式: {voice_mode}")

            # 直接播放音频URL（使用apiserver生成）
            try:
                import httpx
                import asyncio
                from system.config import get_server_port

                # 调用apiserver生成音频
                api_url = f"http://localhost:{get_server_port('api_server')}/v1/audio/speech"

                async def _generate_and_play_audio():
                    try:
                        async with httpx.AsyncClient(timeout=30.0) as client:
                            # 根据语音模式选择TTS引擎
                            # auto模式会根据配置自动选择，local使用本地引擎，end2end使用端到端引擎
                            engine_map = {
                                "auto": "gpt_sovits",      # auto模式默认使用GPT-SoVITS
                                "local": "edge_tts",       # local模式使用Edge TTS
                                "hybrid": "gpt_sovits",    # hybrid模式使用GPT-SoVITS
                                "end2end": "gpt_sovits"    # end2end模式使用GPT-SoVITS
                            }
                            engine = engine_map.get(voice_mode, "gpt_sovits")

                            logger.info(f"[UI] 自主消息使用TTS引擎: {engine}")

                            # 根据引擎选择不同的voice参数
                            if engine == "edge_tts":
                                voice = _cfg.tts.voice if hasattr(_cfg.tts, 'voice') else "zh-CN-XiaoxiaoNeural"
                            else:  # gpt_sovits
                                voice = _cfg.tts.voice if hasattr(_cfg.tts, 'voice') else "default"

                            response = await client.post(
                                api_url,
                                json={
                                    "text": message,
                                    "voice": voice
                                },
                                params={"engine": engine}
                            )

                            if response.status_code == 200:
                                # 音频以MP3/WAV格式返回
                                audio_data = response.content

                                logger.info(f"[UI] 自主消息音频已生成，大小: {len(audio_data)} bytes")

                                # 使用VoiceIntegration播放
                                from voice.output.voice_integration import VoiceIntegration
                                voice_integration = VoiceIntegration()
                                voice_integration._play_audio_data_sync(audio_data)
                                logger.info(f"[UI] 自主消息TTS播放已提交")
                            else:
                                logger.warning(f"[UI] 音频生成失败: {response.status_code}")
                    except Exception as e:
                        logger.error(f"[UI] 生成音频失败: {e}")
                        import traceback
                        traceback.print_exc()

                # 在事件循环中运行
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(_generate_and_play_audio())
                else:
                    loop.run_until_complete(_generate_and_play_audio())

            except ImportError as e:
                logger.warning(f"[UI] 无法导入模块: {e}")
            except Exception as e:
                logger.error(f"[UI] 播放TTS失败: {e}")
                import traceback
                traceback.print_exc()

        except Exception as e:
            logger.error(f"[UI] _play_active_message_tts失败: {e}")
            import traceback
            traceback.print_exc()

    def _save_tool_conversation_to_history(self, ai_response: str):
        """保存工具对话历史到API服务器"""
        try:
            import httpx
            import asyncio

            # 获取当前会话ID
            session_id = self._get_current_session_id()
            if not session_id:
                logger.warning("[UI] 无法获取会话ID，跳过历史记录保存")
                return

            # 构建保存请求
            save_data = {
                "session_id": session_id,
                "user_message": "[工具执行结果]",  # 占位用户消息
                "assistant_response": ai_response
            }

            api_url = get_api_url("/save_tool_conversation")

            # 异步发送保存请求
            async def _save_async():
                async with httpx.AsyncClient(timeout=5.0) as client:
                    response = await client.post(api_url, json=save_data)
                    if response.status_code == 200:
                        logger.info(f"[UI] 工具对话历史已保存到API服务器")
                    else:
                        logger.error(f"[UI] 保存工具对话历史失败: {response.status_code}")

            # 在事件循环中运行异步任务
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(_save_async())
            else:
                loop.run_until_complete(_save_async())

        except Exception as e:
            logger.error(f"[UI] 保存工具对话历史失败: {e}")

    def _get_current_session_id(self) -> str:
        """获取当前会话ID"""
        try:
            # 从窗口对象获取会话ID
            if hasattr(self.window, 'session_id') and self.window.session_id:
                return self.window.session_id

            # 如果窗口没有会话ID，尝试从HTTP客户端响应中获取
            if hasattr(self, 'http_client') and self.http_client:
                # 检查HTTP客户端是否有会话ID
                if hasattr(self.http_client, 'last_session_id') and self.http_client.last_session_id:
                    # 保存到窗口对象以便后续使用
                    self.window.session_id = self.http_client.last_session_id
                    return self.http_client.last_session_id

            # 如果都没有，生成一个新的会话ID
            import uuid
            new_session_id = str(uuid.uuid4())
            # 保存到窗口对象
            self.window.session_id = new_session_id
            return new_session_id

        except Exception as e:
            logger.warning(f"[UI] 获取会话ID失败: {e}")
            # 生成一个默认会话ID
            import uuid
            return str(uuid.uuid4())

# 工具执行结果已通过LLM总结并保存到对话历史中
# UI可以通过查询历史获取工具执行结果

    # ------------------------------
    # 滚动控制
    # ------------------------------

    def smart_scroll_to_bottom(self):
        """智能滚动到底部（如果用户正在查看历史消息，则不滚动）"""
        # 如果不在 Qt 主线程，重新投递
        if QThread.currentThread() != QCoreApplication.instance().thread():
            logger.debug(
                f"不在qt线程。当前线程：{QThread.currentThread()} QT线程：{QCoreApplication.instance().thread()} ")
            QMetaObject.invokeMethod(self, "smart_scroll_to_bottom", Qt.QueuedConnection)
            return

        scrollbar = self.chat_scroll_area.verticalScrollBar()
        is_at_bottom = (scrollbar.value() >= (scrollbar.maximum() - 500))  # 修改距离阈值从1000改为500
        logger.debug(f"移动到末尾的距离检测：{is_at_bottom} 数值：{scrollbar.maximum() - scrollbar.value()} ")
        if is_at_bottom:
            def to_bottom():
                scrollbar.setValue(scrollbar.maximum())

            self.scroll_timer.singleShot(10, to_bottom)

    def _remove_layout_stretch(self):
        """移除布局中最后一个stretch"""
        for i in reversed(range(self.chat_layout.count())):
            item = self.chat_layout.itemAt(i)
            if item and not item.widget():  # 识别stretch/spacer
                self.chat_layout.removeItem(item)
                break

    # ------------------------------
    # 流式响应处理
    # ------------------------------


    def append_response_chunk(self, chunk: str):
        """追加响应片段（流式模式）- 实时显示到消息框"""
        # 检查是否为工具调用相关标记
        if any(marker in chunk for marker in ["[TOOL_CALL]", "[TOOL_START]", "[TOOL_RESULT]", "[TOOL_ERROR]"]):
            return

        logger.debug(f"收到chunk：{chunk}")

        # 检查是否在工具调用过程中
        if self.in_tool_call_mode:
            # 工具调用模式结束，创建新的消息框
            self.in_tool_call_mode = False
            self.current_message_id = None

        # 实时更新显示
        if not self.current_message_id:
            # 第一次收到chunk时，创建新消息
            self.current_message_id = self.add_ai_message(chunk)
            self.current_response = chunk
        else:
            # 后续chunk，追加到当前消息
            self.current_response += chunk
            #
            # # 限制更新频率（节流）
            # current_time = time.time()
            # # 每50毫秒更新一次UI，减少闪动
            # if current_time - self.last_update_time >= 0.05:
            self.update_last_message(self.current_response)
            # self.last_update_time = current_time

    def finalize_streaming_response(self):
        """完成流式响应处理"""
        if self.current_response:
            # 对累积的完整响应进行消息提取
            final_message = extract_message(self.current_response)

            # 更新最终消息
            if self.current_message_id:
                self.update_last_message(final_message)

        # 重置状态
        self.current_response = None
        self.current_message_id = None
        self.last_update_time = 0

        # 停止加载状态
        self.progress_widget.stop_loading()

    # ------------------------------
    # 打字机效果
    # ------------------------------

    def _start_stream_typewriter(self):
        """启动流式聊天的打字机效果"""
        if self.stream_typewriter_timer and self.stream_typewriter_timer.isActive():
            return

        self.stream_typewriter_timer = QTimer()
        self.stream_typewriter_timer.timeout.connect(self._stream_typewriter_tick)
        self.stream_typewriter_timer.start(100)  # 100ms一个字符

    def _stream_typewriter_tick(self):
        """流式聊天的打字机效果tick"""
        if self.stream_typewriter_index >= len(self.stream_typewriter_buffer):
            self._stop_stream_typewriter()
            return

        # 每次显示1-3个字符
        next_char = self.stream_typewriter_buffer[self.stream_typewriter_index]
        chars_to_add = 1

        # 如果是英文字符或空格，可以一次显示多个
        if next_char and ord(next_char) < 128:  # ASCII字符
            chars_to_add = min(3, len(self.stream_typewriter_buffer) - self.stream_typewriter_index)

        self.stream_typewriter_index += chars_to_add
        displayed_text = self.stream_typewriter_buffer[:self.stream_typewriter_index]

        # 更新消息显示
        self.update_last_message(displayed_text)

    def _stop_stream_typewriter(self):
        """停止流式打字机效果"""
        if self.stream_typewriter_timer and self.stream_typewriter_timer.isActive():
            self.stream_typewriter_timer.stop()
            self.stream_typewriter_timer.deleteLater()
            self.stream_typewriter_timer = None

    def start_non_stream_typewriter(self, full_text: str):
        """为非流式响应启动打字机效果"""
        # 创建空消息
        message_id = self.add_ai_message("")
        self.non_stream_message_id = message_id
        self.current_message_id = message_id  # 让update_last_message能找到这个消息

        # 初始化打字机变量
        self.non_stream_text = full_text
        self.non_stream_index = 0

        if not self.non_stream_timer:
            self.non_stream_timer = QTimer()
            self.non_stream_timer.timeout.connect(self._non_stream_typewriter_tick)

        # 启动定时器
        self.non_stream_timer.start(100)  # 100ms一个字符

    def _non_stream_typewriter_tick(self):
        """非流式响应的打字机效果tick"""
        if self.non_stream_index >= len(self.non_stream_text):
            # 所有字符都显示完了，停止定时器并清理
            self.non_stream_timer.stop()
            self.non_stream_timer.deleteLater()
            self.non_stream_timer = None

            # 清理临时变量
            self.non_stream_text = None
            self.non_stream_index = None
            self.non_stream_message_id = None
            self.current_message_id = None
            return

        # 每次显示1-3个字符
        next_char = self.non_stream_text[self.non_stream_index]
        chars_to_add = 1

        # 如果是英文字符或空格，可以一次显示多个
        if next_char and ord(next_char) < 128:  # ASCII字符
            chars_to_add = min(3, len(self.non_stream_text) - self.non_stream_index)

        self.non_stream_index += chars_to_add
        displayed_text = self.non_stream_text[:self.non_stream_index]

        # 更新消息显示
        self.update_last_message(displayed_text)


    def cancel_current_task(self):
        """取消当前任务"""
        # 停止所有打字机效果
        self._stop_stream_typewriter()

        if self.non_stream_timer and self.non_stream_timer.isActive():
            self.non_stream_timer.stop()
            self.non_stream_timer.deleteLater()
            self.non_stream_timer = None

            # 清理非流式打字机变量
            self.non_stream_text = None
            self.non_stream_index = None
            self.non_stream_message_id = None

        # 处理HTTP客户端
        if self.http_client and self.http_client.isRunning():
            # 立即设置取消标志
            self.http_client.cancel()

            # 非阻塞方式处理线程清理
            self.progress_widget.stop_loading()
            self.add_system_message("🚫 操作已取消")

            # 清空当前响应缓冲
            self.current_response = ""
            self.current_message_id = None

            # 使用QTimer延迟处理线程清理，避免UI卡顿
            QTimer.singleShot(50, self._cleanup_http_client)
        else:
            self.progress_widget.stop_loading()

    def _cleanup_http_client(self):
        """清理HTTP客户端资源"""
        if self.http_client:
            self.http_client.quit()
            if not self.http_client.wait(500):  # 只等待500ms
                self.http_client.terminate()
                self.http_client.wait(200)  # 再等待200ms
            self.http_client.deleteLater()
            self.http_client = None

    # ------------------------------
    # 属性访问器
    # ------------------------------

    @property
    def messages(self) -> Dict[str, Dict]:
        """获取所有消息"""
        return self._messages.copy()  # 返回副本，防止外部修改


from ..utils.lazy import lazy


@lazy
def chat():
    return ChatTool(config.window)