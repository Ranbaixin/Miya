"""
QQ交互子网 - 消息处理逻辑
从原 qq.py 中拆分出来的消息处理功能
"""

import asyncio
import logging
import re
import time
from typing import Dict, List, Optional, Any, Set, Union
from datetime import datetime

from .models import QQMessage, ReplySegment, FileSegment
from .image_handler import QQImageHandler
from .message_parser import QQMessageParser
from core.text_loader import get_text

logger = logging.getLogger(__name__)


class QQMessageHandler:
    """QQ消息处理器"""

    def __init__(self, qq_net):
        self.qq_net = qq_net
        # 消息解析器
        self.message_parser = QQMessageParser()

        # 访问控制
        self.group_whitelist: Set[int] = set()
        self.group_blacklist: Set[int] = set()
        self.user_whitelist: Set[int] = set()
        self.user_blacklist: Set[int] = set()
        self.bot_qq: int = 0

        # 图片处理器 - 将在configure中设置
        self.image_handler: Optional[QQImageHandler] = None

        # 拍一拍冷却 (sender_id -> last_poke_time)
        self._poke_cooldown: Dict[int, float] = {}
        self._poke_cooldown_seconds: float = 15.0  # 同一用户15秒内只能拍一次

    def configure(
        self,
        group_whitelist: Optional[Set[int]] = None,
        group_blacklist: Optional[Set[int]] = None,
        user_whitelist: Optional[Set[int]] = None,
        user_blacklist: Optional[Set[int]] = None,
        bot_qq: int = 0,
        enable_image_ocr: bool = True,
        enable_ai_image_analysis: bool = False,
        image_handler: Optional[QQImageHandler] = None,
        onebot_client=None,
    ) -> None:
        """配置消息处理器"""
        # 设置消息解析器的客户端
        if onebot_client:
            self.message_parser.set_client(onebot_client)
        elif hasattr(self.qq_net, "onebot_client"):
            self.message_parser.set_client(self.qq_net.onebot_client)

        if group_whitelist:
            self.group_whitelist = group_whitelist
        if group_blacklist:
            self.group_blacklist = group_blacklist
        if user_whitelist:
            self.user_whitelist = user_whitelist
        if user_blacklist:
            self.user_blacklist = user_blacklist
        self.bot_qq = bot_qq

        # 设置图片处理器（从QQNet传入）
        if image_handler:
            self.image_handler = image_handler
            logger.info("[QQMessageHandler] 图片处理器已设置")

            # 配置图片处理器（注意：我们的新处理器忽略OCR参数，仅使用AI分析）
            self.image_handler.configure()

    async def handle_event(self, event: Dict[str, Any]) -> Optional[QQMessage]:
        """处理QQ消息事件"""
        post_type = event.get("post_type", "")

        # 处理拍一拍
        if post_type == "notice" and event.get("notice_type") == "poke":
            return await self._handle_poke(event)

        # 处理消息
        if post_type == "message":
            # 检查是否是图片消息
            if self._has_image_message(event):
                logger.info("[QQMessageHandler] 检测到图片消息")
                return await self._handle_image_message(event)

            # 普通文本消息
            message_type = event.get("message_type", "")
            logger.info(f"[QQMessageHandler] 处理消息类型: {message_type}")

            if message_type == "group":
                return await self._handle_group_message(event)
            elif message_type == "private":
                return await self._handle_private_message(event)
            else:
                logger.warning(f"[QQMessageHandler] 未知消息类型: {message_type}")

        return None

    def _is_group_allowed(self, group_id: int) -> bool:
        """检查群是否允许处理"""
        if not self.group_whitelist and not self.group_blacklist:
            return True

        if group_id in self.group_blacklist:
            return False

        if self.group_whitelist:
            return group_id in self.group_whitelist

        return True

    def _is_user_allowed(self, user_id: int) -> bool:
        """检查用户是否允许处理"""
        if not self.user_whitelist and not self.user_blacklist:
            return True

        if user_id in self.user_blacklist:
            return False

        if self.user_whitelist:
            return user_id in self.user_whitelist

        return True

    async def _handle_poke(self, event: Dict[str, Any]) -> Optional[QQMessage]:
        """处理拍一拍事件"""
        target_id = event.get("target_id", 0)
        sender_id = event.get("user_id", 0)
        group_id = event.get("group_id", 0)

        # 只有拍机器人才响应
        if target_id != self.bot_qq:
            return None

        # 拍一拍冷却检查
        now = time.time()
        last_poke = self._poke_cooldown.get(sender_id, 0)
        if now - last_poke < self._poke_cooldown_seconds:
            remaining = self._poke_cooldown_seconds - (now - last_poke)
            logger.debug(
                f"[QQNet] 拍一拍冷却中: sender={sender_id}, 剩余{remaining:.1f}秒"
            )
            return None
        self._poke_cooldown[sender_id] = now

        logger.info(f"[QQNet] 收到拍一拍: sender={sender_id}, group={group_id}")

        # 访问控制
        if group_id == 0:
            if not self._is_user_allowed(sender_id):
                return None
        else:
            if not self._is_group_allowed(group_id):
                return None

        # 获取发送者信息
        sender_name = f"QQ{sender_id}"
        try:
            if group_id == 0:
                if self.qq_net.onebot_client:
                    user_info = await self.qq_net.onebot_client.get_stranger_info(
                        sender_id
                    )
                    if user_info:
                        sender_name = user_info.get("nickname", sender_name)
            else:
                if self.qq_net.onebot_client:
                    member_info = await self.qq_net.onebot_client.get_group_member_info(
                        group_id, sender_id
                    )
                    if member_info:
                        card = member_info.get("card", "")
                        nickname = member_info.get("nickname", "")
                        sender_name = card or nickname or sender_name
        except Exception as e:
            logger.warning(f"[QQNet] 获取用户信息失败: {e}")

        # 尝试发送表情包作为回应
        try:
            await self._send_emoji_response(group_id, sender_id)
        except Exception as e:
            logger.error(f"[QQNet] 发送表情包失败: {e}")

        # 构建拍一拍消息
        poke_message = QQMessage(
            post_type="notice",
            message_type="poke",
            group_id=group_id,
            user_id=sender_id,
            sender_id=sender_id,
            message=f"{sender_name} 拍了拍你",
            sender_name=sender_name,
            is_at_bot=True,
        )

        return poke_message

    async def _handle_group_message(self, event: Dict[str, Any]) -> Optional[QQMessage]:
        """处理群消息"""
        group_id = event.get("group_id", 0)
        # 【修复】优先从 sender 获取 user_id，如果为 0 则从 event 顶层获取
        sender_id = event.get("sender", {}).get("user_id", 0)
        if sender_id == 0:
            sender_id = event.get("user_id", 0)

        if not self._is_group_allowed(group_id):
            return None

        if sender_id == self.bot_qq:
            return None

        raw_message = event.get("message", [])
        logger.info(
            f"[QQMessageHandler] raw_message: {raw_message[:100] if raw_message else 'empty'}"
        )

        # 解析消息段
        message_segments = self.message_parser.normalize_message(raw_message)
        logger.info(f"[QQMessageHandler] parsed segments: {len(message_segments)}")

        # 检查是否有引用消息
        reply_id = self.message_parser.get_reply_id(message_segments)
        logger.info(f"[QQMessageHandler] reply_id: {reply_id}")

        reply_info = None
        if reply_id:
            if self.message_parser.qq_client:
                logger.info(f"[QQMessageHandler] 尝试获取引用消息: {reply_id}")
                reply_info = await self._get_reply_info(reply_id)
                logger.info(f"[QQMessageHandler] reply_info: {reply_info}")
            else:
                logger.warning("[QQMessageHandler] qq_client 未设置，无法获取引用消息")

        # 检查是否有文件
        files_info = self.message_parser.get_files(message_segments)
        files_segment = [
            FileSegment(
                file_id=f.file_id,
                name=f.name,
                size=f.size,
                file_type=f.file_type,
            )
            for f in files_info
        ]
        has_media = self.message_parser.has_media(message_segments)

        # 【修复】检查引用消息是否包含图片
        if reply_info and "[引用消息包含图片]" in reply_info.content:
            has_media = True
            logger.info(
                "[QQMessageHandler] 检测到引用消息中的图片，设置 has_media=True"
            )

        # 提取基本消息信息
        text = self._extract_text(raw_message, skip_image=True)
        sender_info = event.get("sender", {})
        sender_card = sender_info.get("card", "")
        sender_nickname = sender_info.get("nickname", "")
        sender_role = sender_info.get("role", "member")
        sender_title = sender_info.get("title", "")

        # 获取群名
        group_name = ""
        try:
            if self.qq_net.onebot_client:
                group_info = await self.qq_net.onebot_client.get_group_info(group_id)
                if group_info:
                    group_name = group_info.get("group_name", "")
        except Exception as e:
            logger.warning(f"[QQNet] 获取群名失败: {e}")

        # 检测@机器人
        is_at_bot = self._is_at_bot(raw_message)
        at_list = self._extract_at_list(raw_message)

        # 检测是否回复机器人消息
        reply_to_bot = False
        if reply_info and reply_info.sender_id == self.bot_qq:
            reply_to_bot = True

        # 【谛听】记录所有群消息（不触发大模型）
        try:
            from memory.diteng_listener import get_diting

            diteng = get_diting()
            diteng.on_group_message(
                group_id=str(group_id),
                group_name=group_name,
                user_id=str(sender_id),
                user_name=sender_card or sender_nickname,
                content=text,
                is_at_bot=is_at_bot,
                reply_to_bot=reply_to_bot,
            )
        except Exception as e:
            logger.debug(f"[QQMessageHandler] 谛听记录失败: {e}")

        # 保存历史
        self._save_history(
            "group",
            group_id,
            sender_id,
            text,
            sender_name=sender_card or sender_nickname,
            group_name=group_name,
            raw_message=raw_message,
        )

        # 构建消息对象
        qq_message = QQMessage(
            post_type="message",
            message_type="group",
            group_id=group_id,
            user_id=sender_id,
            sender_id=sender_id,
            message=text,
            raw_message=raw_message,
            sender_name=sender_card or sender_nickname,
            group_name=group_name,
            sender_role=sender_role,
            sender_title=sender_title,
            message_id=event.get("message_id", 0),
            is_at_bot=is_at_bot,
            reply_to_bot=reply_to_bot,
            at_list=at_list,
            reply=reply_info,
            files=files_segment,
            has_media=has_media,
        )

        return qq_message

    async def _get_reply_info(self, message_id: int) -> Optional[ReplySegment]:
        """获取引用消息信息"""
        try:
            reply_msg = await self.message_parser.qq_client.get_msg(message_id)
            if not reply_msg:
                return None

            sender = reply_msg.get("sender", {})
            # 【修复】正确获取发送者ID
            if isinstance(sender, dict):
                sender_id = sender.get("user_id", 0)
                sender_name = (
                    sender.get("nickname") or sender.get("card") or str(sender_id)
                    if sender_id
                    else "未知"
                )
            else:
                sender_id = 0
                sender_name = "未知"

            message_content = reply_msg.get("message", [])

            # 检查引用消息是否包含图片，提取图片URL
            has_image_in_reply = False
            image_url = None
            for seg in message_content:
                if isinstance(seg, dict) and seg.get("type") == "image":
                    has_image_in_reply = True
                    image_data = seg.get("data", {})
                    image_url = image_data.get("url", "")
                    logger.info(
                        f"[QQMessageHandler] 引用消息图片URL: {image_url[:50]}..."
                    )
                    break

            # 提取文本内容
            content = self.message_parser.extract_text(
                self.message_parser.normalize_message(message_content),
                skip_image=True,
            )

            # 如果有图片，在内容中添加标记
            if has_image_in_reply and content:
                content = f"[引用消息包含图片] {content}"
            elif has_image_in_reply:
                content = "[引用消息包含图片，但无法提取内容]"

            return ReplySegment(
                message_id=message_id,
                sender_name=sender_name,
                content=content[:200],
                sender_id=sender_id,  # 【修复】添加 sender_id
                image_url=image_url,
            )
        except Exception as e:
            logger.warning(f"获取引用消息失败: {e}")
            return None

    async def _handle_private_message(
        self, event: Dict[str, Any]
    ) -> Optional[QQMessage]:
        """处理私聊消息"""
        sender_id = event.get("sender", {}).get("user_id", 0)

        # 访问控制
        if not self._is_user_allowed(sender_id):
            return None

        # 忽略自己的消息
        if sender_id == self.bot_qq:
            return None

        # 解析消息
        raw_message = event.get("message", [])

        # 处理不同 OneBot 实现的消息格式
        if isinstance(raw_message, str):
            # 简报模式
            text = raw_message
        elif isinstance(raw_message, list):
            # 标准模式
            text = self._extract_text(raw_message)
        else:
            # 未知格式
            text = str(raw_message)
            raw_message = []

        sender_info = event.get("sender", {})
        sender_nickname = sender_info.get("nickname", "")

        # 获取用户名
        user_name = sender_nickname
        if not user_name and self.qq_net.onebot_client:
            try:
                user_info = await self.qq_net.onebot_client.get_stranger_info(sender_id)
                if user_info:
                    user_name = user_info.get("nickname", "")
            except Exception as e:
                logger.warning(f"[QQNet] 获取用户名失败: {e}")

        # 保存到历史
        self._save_history(
            "private",
            sender_id,
            sender_id,
            text,
            sender_name=sender_nickname,
            raw_message=raw_message,
        )

        # 私聊消息无@列表
        at_list = []

        # 【新增】检测是否为表情包请求
        emoji_request_result = None
        if text:
            # 检查是否包含表情包请求关键词
            emoji_keywords = [
                "表情包",
                "表情",
                "发图",
                "发图片",
                "发照片",
                "来张图",
                "来张图片",
                "发送表情",
                "发个表情",
                "来点表情",
            ]
            has_emoji_keyword = any(keyword in text for keyword in emoji_keywords)

            if has_emoji_keyword:
                logger.info(f"[QQNet-表情包请求] 检测到私聊表情包请求: '{text}'")
                # 直接处理表情包请求
                emoji_request_result = await self.handle_emoji_request(
                    0, sender_id, text
                )  # group_id=0表示私聊

                # 如果表情包请求处理成功，返回一个特殊的消息对象
                if emoji_request_result:
                    logger.info(
                        f"[QQNet-表情包请求] 私聊表情包请求处理完成: {emoji_request_result}"
                    )
                    # 返回一个特殊的消息对象，表示已处理表情包请求
                    return QQMessage(
                        post_type="message",
                        message_type="private",
                        user_id=sender_id,
                        sender_id=sender_id,
                        message=f"[表情包请求已处理] {emoji_request_result}",
                        raw_message=raw_message,
                        sender_name=user_name or sender_nickname,
                        message_id=event.get("message_id", 0),
                        at_list=at_list,
                        is_emoji_request=True,
                        emoji_request_result=emoji_request_result,
                    )

        # 解析消息段
        message_segments = self.message_parser.normalize_message(raw_message)

        # 检查是否有引用消息
        reply_id = self.message_parser.get_reply_id(message_segments)
        reply_info = None
        if reply_id and self.message_parser.qq_client:
            reply_info = await self._get_reply_info(reply_id)

        # 检查是否有文件
        files_info = self.message_parser.get_files(message_segments)
        files_segment = [
            FileSegment(
                file_id=f.file_id,
                name=f.name,
                size=f.size,
                file_type=f.file_type,
            )
            for f in files_info
        ]
        has_media = self.message_parser.has_media(message_segments)

        # 构建消息对象
        qq_message = QQMessage(
            post_type="message",
            message_type="private",
            user_id=sender_id,
            sender_id=sender_id,
            message=text,
            raw_message=raw_message,
            sender_name=user_name or sender_nickname,
            message_id=event.get("message_id", 0),
            at_list=at_list,
            reply=reply_info,
            files=files_segment,
            has_media=has_media,
        )

        return qq_message

    def _extract_text(self, message: Union[str, List[Dict[str, Any]]]) -> str:
        """从消息段中提取纯文本"""
        # 如果是字符串，直接返回
        if isinstance(message, str):
            return message

        text_parts = []
        for segment in message:
            if isinstance(segment, str):
                text_parts.append(segment)
            elif isinstance(segment, dict):
                if segment.get("type") == "text":
                    text_parts.append(segment.get("data", {}).get("text", ""))

        return "".join(text_parts)

    def _is_at_bot(self, message: Union[str, List[Dict[str, Any]]]) -> bool:
        """检测消息是否@了机器人"""
        if not self.bot_qq:
            logger.warning(f"[QQNet] bot_qq 未设置，无法检测@消息")
            return False

        logger.debug(f"[QQNet] 检测@消息: bot_qq={self.bot_qq}, message={message}")

        # 如果是字符串，检查是否包含@机器人
        if isinstance(message, str):
            bot_qq_str = str(self.bot_qq)
            return f"@{bot_qq_str}" in message

        # 检测 at 消息段（标准 OneBot 格式）
        for segment in message:
            if isinstance(segment, dict):
                seg_type = segment.get("type")
                if seg_type == "at":
                    at_qq = segment.get("data", {}).get("qq")
                    # 统一转换为字符串比较（兼容 OneBot 不同实现）
                    at_qq_str = str(at_qq) if at_qq is not None else None
                    bot_qq_str = str(self.bot_qq)
                    logger.info(
                        f"[QQNet] 发现@消息段: at_qq={at_qq}, bot_qq={self.bot_qq}, 匹配={at_qq_str == bot_qq_str}"
                    )
                    if at_qq_str == bot_qq_str:
                        return True

        return False

    def _extract_at_list(self, message: Union[str, List[Dict[str, Any]]]) -> List[int]:
        """提取消息中@的所有用户ID"""
        at_list = []

        # 如果是字符串，无法提取@列表
        if isinstance(message, str):
            return at_list

        # 方法1: 从消息段中提取（标准 OneBot 格式）
        for segment in message:
            if isinstance(segment, dict):
                seg_type = segment.get("type")
                if seg_type == "at":
                    at_qq = segment.get("data", {}).get("qq")
                    if at_qq is not None:
                        try:
                            at_list.append(int(at_qq))
                        except (ValueError, TypeError):
                            pass

        if at_list:
            logger.info(f"[QQNet] 从消息段提取到@列表: {at_list}")

        # 方法2: 如果没有找到@段，尝试从文本中提取（兼容某些 OneBot 实现）
        if not at_list:
            for segment in message:
                if isinstance(segment, dict):
                    seg_type = segment.get("type")
                    if seg_type == "text":
                        text_content = segment.get("data", {}).get("text", "")
                        logger.info(f"[QQNet] 尝试从文本提取@: {text_content}")

                        # 尝试匹配 @QQ号 格式（@12345678）
                        qq_pattern = r"@(\d{5,11})"
                        matches = re.findall(qq_pattern, text_content)
                        for match in matches:
                            try:
                                at_qq = int(match)
                                # 避免重复
                                if at_qq not in at_list:
                                    at_list.append(at_qq)
                            except ValueError:
                                pass

                        if at_list:
                            logger.info(f"[QQNet] 从文本提取到@列表: {at_list}")

        return at_list

    def _save_history(
        self,
        msg_type: str,
        chat_id: int,
        sender_id: int,
        text: str,
        sender_name: str = "",
        group_name: str = "",
        raw_message: Optional[Union[str, List[Dict[str, Any]]]] = None,
    ) -> None:
        """保存消息到QQCacheManager的历史缓存"""
        try:
            # 从缓存获取现有消息
            messages = self.qq_net.cache_manager.get_message_history(chat_id)
            if messages is None:
                messages = []

            # 添加新消息
            messages.append(
                {
                    "type": msg_type,
                    "sender_id": sender_id,
                    "text": text,
                    "sender_name": sender_name,
                    "group_name": group_name,
                    "raw_message": raw_message,
                    "timestamp": datetime.now(),
                }
            )

            # 限制消息数量到100条
            messages = messages[-100:]

            # 保存到缓存管理器
            self.qq_net.cache_manager.set_message_history(chat_id, messages)
        except Exception as e:
            logger.warning(f"[QQMessageHandler] 保存消息到缓存失败: {e}")

        # 异步保存到全局记忆系统
        asyncio.create_task(
            self._persist_to_global_memory(
                msg_type=msg_type,
                chat_id=chat_id,
                sender_id=sender_id,
                text=text,
                sender_name=sender_name,
                group_name=group_name,
            )
        )

    async def _persist_to_global_memory(
        self,
        msg_type: str,
        chat_id: int,
        sender_id: int,
        text: str,
        sender_name: str = "",
        group_name: str = "",
    ) -> None:
        """持久化保存到全局记忆系统"""
        memory_net = getattr(self.qq_net, "memory_net", None)
        if not memory_net:
            logger.warning("[QQNet] MemoryNet 未初始化，无法保存到全局记忆")
            return

        try:
            # 直接调用 MemoryNet 的对话历史管理器
            await memory_net.conversation_history.add_message(
                session_id=f"{msg_type}_{chat_id}",
                role="user",
                content=text,
                agent_id="miya_default",
                metadata={
                    "source": "qq",
                    "msg_type": msg_type,
                    "sender_id": sender_id,
                    "sender_name": sender_name,
                    "group_name": group_name,
                },
            )

            logger.debug(f"[QQNet] 消息已保存到全局记忆: {msg_type}_{chat_id}")

        except Exception as e:
            logger.error(f"[QQNet] 保存到全局记忆失败: {e}")

    def get_history(self, chat_id: int, limit: int = 20) -> List[Dict[str, Any]]:
        """从QQCacheManager获取历史消息"""
        try:
            messages = self.qq_net.cache_manager.get_message_history(chat_id)
            if messages is None or len(messages) == 0:
                return []
            return messages[-limit:]
        except Exception as e:
            logger.warning(f"[QQMessageHandler] 获取消息历史失败: {e}")
            return []

    def _has_image_message(self, event: Dict[str, Any]) -> bool:
        """检查消息是否包含图片"""
        message = event.get("message", [])
        logger.info(f"[QQMessageHandler] _has_image_message 检查: message={message}")

        # 检查标准消息段
        for segment in message:
            if isinstance(segment, dict):
                seg_type = segment.get("type")
                logger.info(f"[QQMessageHandler] segment type: {seg_type}")
                if seg_type == "image":
                    logger.info(f"[QQMessageHandler] 检测到图片段落")
                    return True

        # 检查原始消息字符串
        raw_message = event.get("raw_message", "")
        if isinstance(raw_message, str) and "[CQ:image" in raw_message:
            logger.info(f"[QQMessageHandler] 检测到图片在 raw_message")
            return True

        return False

    async def _handle_image_message(self, event: Dict[str, Any]) -> Optional[QQMessage]:
        """处理图片消息"""
        if not self.image_handler:
            logger.debug("[QQMessageHandler] 图片处理器未启用，跳过图片消息处理")
            return None

        try:
            # 使用图片处理器处理
            logger.info("[QQMessageHandler] 调用 image_handler.handle_image_message")
            enhanced_message = await self.image_handler.handle_image_message(event)
            logger.info(
                f"[QQMessageHandler] handle_image_message 返回: {enhanced_message}"
            )
            if enhanced_message:
                logger.info(f"[QQMessageHandler] 图片消息处理完成")
                return enhanced_message
            else:
                # 即使图片处理失败，也返回基本消息
                logger.warning(
                    "[QQMessageHandler] handle_image_message 返回 None，提取基本消息"
                )
                return await self._extract_basic_message(event)

        except Exception as e:
            logger.error(f"[QQMessageHandler] 图片消息处理失败: {e}", exc_info=True)
            # 失败时返回基本消息
            return await self._extract_basic_message(event)

    async def _extract_basic_message(
        self, event: Dict[str, Any]
    ) -> Optional[QQMessage]:
        """提取基本消息信息（不包含图片分析）"""
        # 这是现有消息处理的简化版本
        message_type = event.get("message_type", "")

        if message_type == "group":
            return await self._extract_group_message_full(event)
        elif message_type == "private":
            return await self._extract_private_message_full(event)

        return None

    async def _extract_group_message_full(
        self, event: Dict[str, Any]
    ) -> Optional[QQMessage]:
        """提取群消息信息（包含引用和文件解析）"""
        group_id = event.get("group_id", 0)
        sender_id = event.get("sender", {}).get("user_id", 0)

        if not self._is_group_allowed(group_id):
            return None

        if sender_id == self.bot_qq:
            return None

        raw_message = event.get("message", [])

        # 解析消息段
        message_segments = self.message_parser.normalize_message(raw_message)

        # 检查是否有引用消息
        reply_id = self.message_parser.get_reply_id(message_segments)
        reply_info = None
        if reply_id and self.message_parser.qq_client:
            reply_info = await self._get_reply_info(reply_id)

        # 检查是否有文件
        files_info = self.message_parser.get_files(message_segments)
        files_segment = [
            FileSegment(
                file_id=f.file_id,
                name=f.name,
                size=f.size,
                file_type=f.file_type,
            )
            for f in files_info
        ]
        has_media = self.message_parser.has_media(message_segments)

        text = self._extract_text(raw_message, skip_image=True)

        sender_info = event.get("sender", {})
        sender_card = sender_info.get("card", "")
        sender_nickname = sender_info.get("nickname", "")

        group_name = ""
        try:
            if self.qq_net.onebot_client:
                group_info = await self.qq_net.onebot_client.get_group_info(group_id)
                if group_info:
                    group_name = group_info.get("group_name", "")
        except Exception as e:
            logger.warning(f"[QQNet] 获取群名失败: {e}")

        is_at_bot = self._is_at_bot(raw_message)
        at_list = self._extract_at_list(raw_message)

        sender_role = sender_info.get("role", "member")
        sender_title = sender_info.get("title", "")

        return QQMessage(
            post_type="message",
            message_type="group",
            group_id=group_id,
            user_id=sender_id,
            sender_id=sender_id,
            message=text,
            raw_message=raw_message,
            sender_name=sender_card or sender_nickname,
            group_name=group_name,
            sender_role=sender_role,
            sender_title=sender_title,
            message_id=event.get("message_id", 0),
            is_at_bot=is_at_bot,
            at_list=at_list,
            reply=reply_info,
            files=files_segment,
            has_media=has_media,
        )

    async def _extract_private_message_full(
        self, event: Dict[str, Any]
    ) -> Optional[QQMessage]:
        """提取私聊消息信息（包含引用和文件解析）"""
        sender_id = event.get("sender", {}).get("user_id", 0)

        if not self._is_user_allowed(sender_id):
            return None

        if sender_id == self.bot_qq:
            return None

        raw_message = event.get("message", [])

        # 解析消息段
        message_segments = self.message_parser.normalize_message(raw_message)

        # 检查是否有引用消息
        reply_id = self.message_parser.get_reply_id(message_segments)
        reply_info = None
        if reply_id and self.message_parser.qq_client:
            reply_info = await self._get_reply_info(reply_id)

        # 检查是否有文件
        files_info = self.message_parser.get_files(message_segments)
        files_segment = [
            FileSegment(
                file_id=f.file_id,
                name=f.name,
                size=f.size,
                file_type=f.file_type,
            )
            for f in files_info
        ]
        has_media = self.message_parser.has_media(message_segments)

        text = self._extract_text(raw_message, skip_image=True)

        user_info = event.get("sender", {})
        user_name = user_info.get("nickname", "")

        return QQMessage(
            post_type="message",
            message_type="private",
            user_id=sender_id,
            sender_id=sender_id,
            message=text,
            raw_message=raw_message,
            sender_name=user_name,
            message_id=event.get("message_id", 0),
            reply=reply_info,
            files=files_segment,
            has_media=has_media,
        )

        # 访问控制
        if not self._is_group_allowed(group_id):
            return None

        # 忽略自己的消息
        if sender_id == self.bot_qq:
            return None

        # 提取文本（跳过图片处理）
        raw_message = event.get("message", [])
        text = self._extract_text(raw_message, skip_image=skip_image)

        # 构建基本消息对象
        sender_info = event.get("sender", {})
        sender_card = sender_info.get("card", "")
        sender_nickname = sender_info.get("nickname", "")

        # 检查是否@机器人
        is_at_bot = self._is_at_bot(raw_message) if not skip_image else False

        # 构建消息
        qq_message = QQMessage(
            post_type="message",
            message_type="group",
            group_id=group_id,
            user_id=sender_id,
            sender_id=sender_id,
            message=text,
            raw_message=raw_message,
            sender_name=sender_card or sender_nickname,
            sender_role=sender_info.get("role", "member"),
            sender_title=sender_info.get("title", ""),
            message_id=event.get("message_id", 0),
            is_at_bot=is_at_bot,
            at_list=self._extract_at_list(raw_message) if not skip_image else [],
        )

        return qq_message

    async def _extract_private_message(
        self, event: Dict[str, Any], skip_image: bool = False
    ) -> Optional[QQMessage]:
        """提取私聊消息信息（简化版本）"""
        sender_id = event.get("sender", {}).get("user_id", 0)

        # 访问控制
        if not self._is_user_allowed(sender_id):
            return None

        # 忽略自己的消息
        if sender_id == self.bot_qq:
            return None

        # 提取文本（跳过图片处理）
        raw_message = event.get("message", [])
        text = self._extract_text(raw_message, skip_image=skip_image)

        sender_info = event.get("sender", {})
        sender_nickname = sender_info.get("nickname", "")

        # 构建消息
        qq_message = QQMessage(
            post_type="message",
            message_type="private",
            user_id=sender_id,
            sender_id=sender_id,
            message=text,
            raw_message=raw_message,
            sender_name=sender_nickname,
            message_id=event.get("message_id", 0),
        )

        return qq_message

    def _extract_text(
        self, message: Union[str, List[Dict[str, Any]]], skip_image: bool = False
    ) -> str:
        """从消息段中提取纯文本，可选择跳过图片"""
        # 如果是字符串，直接返回
        if isinstance(message, str):
            return message

        text_parts = []
        for segment in message:
            if isinstance(segment, str):
                text_parts.append(segment)
            elif isinstance(segment, dict):
                seg_type = segment.get("type")
                if seg_type == "text":
                    text_parts.append(segment.get("data", {}).get("text", ""))
                elif skip_image and seg_type == "image":
                    # 跳过图片，添加占位符
                    text_parts.append("[图片]")

        return "".join(text_parts)

    async def _send_emoji_response(
        self, group_id: int, sender_id: int, emoji_name: Optional[str] = None
    ) -> bool:
        """发送表情包作为回应

        Args:
            group_id: 群组ID（0表示私聊）
            sender_id: 发送者ID
            emoji_name: 表情包名称（可选），如果为None则随机选择

        Returns:
            True如果成功发送，False否则
        """
        try:
            logger.info(
                f"[QQNet] 准备发送表情包作为回应: group={group_id}, sender={sender_id}, emoji_name={emoji_name}"
            )

            # 优先尝试发送本地表情包
            local_emoji_result = await self._send_local_emoji(
                group_id, sender_id, emoji_name
            )
            if local_emoji_result:
                logger.info("[QQNet] 已发送本地表情包")
                return True

            # 如果本地表情包发送失败，回退到内置QQ表情
            logger.info("[QQNet] 本地表情包发送失败，回退到QQ内置表情")

            # 表情包列表（这里使用QQ内置表情ID）
            emojis = [
                {"type": "face", "data": {"id": "1"}},  # 微笑
                {"type": "face", "data": {"id": "2"}},  # 笑哭
                {"type": "face", "data": {"id": "3"}},  # 害羞
                {"type": "face", "data": {"id": "4"}},  # 发呆
                {"type": "face", "data": {"id": "5"}},  # 得意
                {"type": "face", "data": {"id": "6"}},  # 流汗
                {"type": "face", "data": {"id": "7"}},  # 亲亲
                {"type": "face", "data": {"id": "8"}},  # 调皮
                {"type": "face", "data": {"id": "9"}},  # 呲牙
                {"type": "face", "data": {"id": "10"}},  # 大哭
            ]

            # 随机选择一个表情
            import random

            emoji = random.choice(emojis)

            # 构建文字消息
            if not emoji_name:
                text_message = get_text(
                    "poke_responses.builtin_emoji",
                )
            else:
                text_message = get_text("poke_responses.named_emoji").format(
                    emoji_name=emoji_name
                )

            # 发送消息（文字和表情分开发送）
            if group_id == 0:
                # 私聊
                if self.qq_net.onebot_client:
                    # 先发送文字消息
                    text_result = await self.qq_net.onebot_client.send_private_message(
                        sender_id, [{"type": "text", "data": {"text": text_message}}]
                    )
                    logger.info(f"[QQNet] 私聊文字消息发送结果: {text_result}")

                    # 再发送表情消息
                    result = await self.qq_net.onebot_client.send_private_message(
                        sender_id, [emoji]
                    )
                    logger.info(f"[QQNet] 私聊内置表情发送结果: {result}")
                    return True
            else:
                # 群聊
                if self.qq_net.onebot_client:
                    # 先发送文字消息
                    text_result = await self.qq_net.onebot_client.send_group_message(
                        group_id, [{"type": "text", "data": {"text": text_message}}]
                    )
                    logger.info(f"[QQNet] 群聊文字消息发送结果: {text_result}")

                    # 再发送表情消息
                    result = await self.qq_net.onebot_client.send_group_message(
                        group_id, [emoji]
                    )
                    logger.info(f"[QQNet] 群聊内置表情发送结果: {result}")
                    return True

            logger.warning("[QQNet] 无法发送表情包：OneBot客户端不可用")
            return False
        except Exception as e:
            logger.error(f"[QQNet] 发送表情包失败: {e}", exc_info=True)
            return False

    async def _send_local_emoji(
        self, group_id: int, sender_id: int, emoji_name: Optional[str] = None
    ) -> bool:
        """发送本地表情包

        Args:
            group_id: 群组ID（0表示私聊）
            sender_id: 发送者ID
            emoji_name: 表情包名称（可选），如果为None则随机选择

        Returns:
            True如果成功发送，False否则
        """
        try:
            import os
            import random
            from pathlib import Path

            logger.info(
                f"[QQNet-本地表情] 开始发送本地表情包: group={group_id}, sender={sender_id}, emoji_name={emoji_name}"
            )

            # 获取配置的表情包目录（优先从 QQ 配置读取，回退到 text_config）
            from core.text_loader import get_text
            from webnet.qq.config_loader import get_tool_config

            tool_cfg = get_tool_config("qq_emoji")
            emoji_dir_path = tool_cfg.get("emoji_dir", None)
            if not emoji_dir_path:
                emoji_dir_path = get_text("emoji_settings.dir")
            logger.info(f"[QQNet-本地表情] 配置的表情包目录: {emoji_dir_path}")

            # 如果配置的目录不存在，检查是否有默认图片文件
            if not os.path.exists(emoji_dir_path):
                # 尝试在data目录中查找图片文件
                data_dir = "./data"
                if os.path.exists(data_dir):
                    # 查找data目录中的所有图片文件
                    image_extensions = [
                        ".jpg",
                        ".jpeg",
                        ".png",
                        ".gif",
                        ".bmp",
                        ".webp",
                    ]
                    image_files = []

                    for root, dirs, files in os.walk(data_dir):
                        for file in files:
                            file_path = Path(file)
                            if file_path.suffix.lower() in image_extensions:
                                image_files.append(os.path.join(root, file))

                    if not image_files:
                        logger.warning(
                            f"[QQNet-本地表情] 未在 {data_dir} 中找到任何图片文件"
                        )
                        return False

                    # 随机选择一个图片文件
                    image_path = random.choice(image_files)
                    logger.info(f"[QQNet-本地表情] 使用随机图片文件: {image_path}")
                    logger.info(f"[QQNet-本地表情] 找到 {len(image_files)} 个图片文件")
                else:
                    logger.warning("[QQNet] data目录不存在")
                    return False
            else:
                # 递归读取表情包目录中的文件（包括子目录）
                emoji_files = []
                emoji_files_map = {}  # 文件名（不含扩展名）到完整路径的映射

                for root, dirs, files in os.walk(emoji_dir_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        # 检查是否为图片文件
                        if file.lower().endswith(
                            (".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp")
                        ):
                            emoji_files.append(file_path)
                            # 存储文件名映射（不含扩展名）
                            file_name_without_ext = os.path.splitext(file)[0]
                            emoji_files_map[file_name_without_ext.lower()] = file_path

                if not emoji_files:
                    logger.warning(
                        f"[QQNet-本地表情] 表情包目录 {emoji_dir_path} 中没有图片文件"
                    )
                    return False

                # 选择表情包文件
                image_path = None
                if emoji_name:
                    # 尝试根据名称查找表情包
                    emoji_name_lower = emoji_name.lower()

                    # 1. 精确匹配文件名（不含扩展名）
                    if emoji_name_lower in emoji_files_map:
                        image_path = emoji_files_map[emoji_name_lower]
                        logger.info(
                            f"[QQNet-本地表情] 精确匹配到表情包: {emoji_name} -> {image_path}"
                        )

                    # 2. 模糊匹配（包含关系）
                    if not image_path:
                        for file_name, file_path_value in emoji_files_map.items():
                            if (
                                emoji_name_lower in file_name
                                or file_name in emoji_name_lower
                            ):
                                image_path = file_path_value
                                logger.info(
                                    f"[QQNet-本地表情] 模糊匹配到表情包: {emoji_name} -> {image_path}"
                                )
                                break

                    # 3. 文件名包含表情包名称
                    if not image_path:
                        for file_path_value in emoji_files:
                            file_name = os.path.basename(file_path_value).lower()
                            if emoji_name_lower in file_name:
                                image_path = file_path_value
                                logger.info(
                                    f"[QQNet-本地表情] 文件名包含匹配到表情包: {emoji_name} -> {image_path}"
                                )
                                break

                # 如果未找到指定名称的表情包，或未指定名称，则随机选择
                if not image_path:
                    image_path = random.choice(emoji_files)
                    if emoji_name:
                        logger.info(
                            f"[QQNet-本地表情] 未找到指定表情包 '{emoji_name}'，随机选择: {image_path}"
                        )
                    else:
                        logger.info(
                            f"[QQNet-本地表情] 使用随机表情包文件: {image_path}"
                        )

                logger.info(f"[QQNet-本地表情] 找到 {len(emoji_files)} 个表情包文件")

            # 读取图片文件
            with open(image_path, "rb") as f:
                image_data = f.read()

            # 构建图片消息段
            image_message = {
                "type": "image",
                "data": {
                    "file": image_path,
                    "url": f"file://{os.path.abspath(image_path)}",
                },
            }

            logger.info(f"[QQNet-本地表情] 构建图片消息: {image_path}")

            # 构建文字消息
            if not emoji_name:
                text_message = get_text("poke_responses.local_emoji")
            else:
                text_message = get_text("poke_responses.named_emoji").format(
                    emoji_name=emoji_name
                )

            # 发送消息（文字和图片分开发送）
            if group_id == 0:
                # 私聊
                if self.qq_net.onebot_client:
                    # 先发送文字消息
                    logger.info(f"[QQNet-本地表情] 发送私聊文字消息给用户 {sender_id}")
                    text_result = await self.qq_net.onebot_client.send_private_message(
                        sender_id, [{"type": "text", "data": {"text": text_message}}]
                    )
                    logger.info(f"[QQNet-本地表情] 私聊文字消息发送结果: {text_result}")

                    # 再发送图片消息（分开发送）
                    logger.info(
                        f"[QQNet-本地表情] 发送私聊本地表情包图片给用户 {sender_id}"
                    )
                    image_result = await self.qq_net.onebot_client.send_private_message(
                        sender_id, [image_message]
                    )
                    logger.info(
                        f"[QQNet-本地表情] 私聊本地表情包图片发送结果: {image_result}"
                    )

                    return True
                else:
                    logger.warning(
                        f"[QQNet-本地表情] OneBot客户端不可用，无法发送私聊表情包"
                    )
                    return False
            else:
                # 群聊
                if self.qq_net.onebot_client:
                    # 先发送文字消息
                    logger.info(f"[QQNet-本地表情] 发送群聊文字消息到群 {group_id}")
                    text_result = await self.qq_net.onebot_client.send_group_message(
                        group_id, [{"type": "text", "data": {"text": text_message}}]
                    )
                    logger.info(f"[QQNet-本地表情] 群聊文字消息发送结果: {text_result}")

                    # 再发送图片消息（分开发送）
                    logger.info(
                        f"[QQNet-本地表情] 发送群聊本地表情包图片到群 {group_id}"
                    )
                    image_result = await self.qq_net.onebot_client.send_group_message(
                        group_id, [image_message]
                    )
                    logger.info(
                        f"[QQNet-本地表情] 群聊本地表情包图片发送结果: {image_result}"
                    )

                    return True
                else:
                    logger.warning(
                        f"[QQNet-本地表情] OneBot客户端不可用，无法发送群聊表情包"
                    )
                    return False

            logger.warning(f"[QQNet-本地表情] 发送失败: 未处理的消息类型")
            return False

        except Exception as e:
            logger.error(f"[QQNet] 发送本地表情包失败: {e}", exc_info=True)
            return False

    async def handle_emoji_request(
        self, group_id: int, sender_id: int, message_text: str
    ) -> str:
        """
        处理自然语言的表情包请求

        Args:
            group_id: 群组ID（0表示私聊）
            sender_id: 发送者ID
            message_text: 用户消息文本

        Returns:
            处理结果描述
        """
        try:
            logger.info(
                f"[QQNet-表情包请求] 处理表情包请求: group={group_id}, sender={sender_id}, text='{message_text}'"
            )

            # 提取表情包名称
            emoji_name = self._extract_emoji_name_from_text(message_text)

            if not emoji_name:
                logger.info(f"[QQNet-表情包请求] 未提取到表情包名称，发送随机表情包")
                success = await self._send_emoji_response(group_id, sender_id)
                if success:
                    return get_text("emoji_responses.sent_random")
                else:
                    return get_text("error_messages.emoji_send_failed")

            logger.info(f"[QQNet-表情包请求] 提取到表情包名称: '{emoji_name}'")

            # 尝试发送指定名称的表情包
            success = await self._send_emoji_response(group_id, sender_id, emoji_name)

            if success:
                return get_text("emoji_responses.sent_success").format(
                    emoji_name=emoji_name
                )
            else:
                return get_text("emoji_responses.sent_fallback").format(
                    emoji_name=emoji_name
                )

        except Exception as e:
            logger.error(f"[QQNet-表情包请求] 处理失败: {e}", exc_info=True)
            return get_text("emoji_responses.error").format(error=str(e))

    def _extract_emoji_name_from_text(self, text: str) -> str:
        """
        从文本中提取表情包名称

        Args:
            text: 用户消息文本

        Returns:
            提取的表情包名称，如果未提取到则返回空字符串
        """
        import re

        # 先检查是否包含表情包关键词
        emoji_keywords = [
            "表情包",
            "表情",
            "发图",
            "发图片",
            "发照片",
            "来张图",
            "来张图片",
        ]
        has_emoji_keyword = any(keyword in text for keyword in emoji_keywords)

        if not has_emoji_keyword:
            logger.info(f"[QQNet-表情包请求] 未检测到表情包关键词: '{text}'")
            return ""

        # 1. 处理常见无具体名称的请求 - 直接返回空字符串
        common_empty_requests = [
            "发个表情包",
            "表情包",
            "发个表情",
            "发送表情包",
            "来点表情",
            "给我个表情",
            "给我发个表情包",
        ]
        if text in common_empty_requests:
            logger.info(
                f"[QQNet-表情包请求] 常见无具体名称请求，返回空字符串: '{text}'"
            )
            return ""

        # 2. 尝试提取表情包名称的模式 - 更精确的版本
        # 先处理"给我来个开心表情"这种情况 - 移除"来"字
        text_for_pattern = (
            text.replace("来个", "")
            .replace("来张", "")
            .replace("来点", "")
            .replace("来一个", "")
        )

        patterns = [
            r"(?:发送|发)([一-龥]{2,})(?:表情|表情包)",  # 发送开心表情包，至少2个字符
            r"(?:给我|想要)([一-龥]{2,})(?:表情|表情包)",  # 给我开心表情包，至少2个字符
        ]

        for pattern in patterns:
            match = re.search(pattern, text_for_pattern)
            if match:
                emoji_name = match.group(1).strip()
                # 清理量词
                emoji_name = (
                    emoji_name.replace("一个", "")
                    .replace("一张", "")
                    .replace("个", "")
                    .replace("张", "")
                    .strip()
                )
                if emoji_name and len(emoji_name) >= 2:  # 至少2个字符，避免匹配到单个字
                    logger.info(
                        f"[QQNet-表情包请求] 从文本中提取到表情包名称: '{emoji_name}' (模式: {pattern})"
                    )
                    return emoji_name

        # 3. 处理直接说表情包名称的情况，如"开心表情包"
        if "表情包" in text or "表情" in text:
            # 提取"表情包"或"表情"前面的词
            before_emoji = text.split("表情包")[0].split("表情")[0].strip()
            # 检查是否是请求词
            request_words = [
                "发个",
                "发",
                "发送",
                "来",
                "给我",
                "想要",
                "来个",
                "发个",
                "给我发个",
            ]
            if (
                before_emoji
                and len(before_emoji) > 0
                and before_emoji not in request_words
            ):
                logger.info(
                    f"[QQNet-表情包请求] 从文本中直接提取到表情包名称: '{before_emoji}'"
                )
                return before_emoji

        # 4. 如果有关键词但没有具体名称，返回空字符串
        logger.info(
            f"[QQNet-表情包请求] 检测到表情包关键词，但未提取到具体名称: '{text}'"
        )
        return ""  # 返回空字符串表示需要随机表情包
