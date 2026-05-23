"""
记忆管理器 (Memory Manager)

职责：
1. 用户消息存储
2. AI响应存储
3. 统一跨平台记忆存储
4. 对话历史管理
5. 记忆压缩
"""

import contextlib
import logging
import re
from typing import Any, Dict, List, Optional

from memory import (
    get_memory_core,
    store_dialogue,
    store_important,
)
from memory.historian import get_historian

logger = logging.getLogger(__name__)


class MemoryManager:
    """
    记忆管理器

    单一职责：处理所有与记忆存储和管理相关的逻辑
    """

    def __init__(
        self,
        memory_net: Optional[Any] = None,
        memory_engine: Optional[Any] = None,
    ):
        self.memory_net = memory_net
        self.memory_engine = memory_engine
        self.historian = get_historian()
        logger.info("[记忆管理器] 初始化完成 (使用新版统一记忆API)")

    async def store_user_message(self, perception: Dict) -> None:
        """
        存储用户消息到记忆系统

        Args:
            perception: 感知数据
        """
        try:
            content = perception.get("content", "")
            if isinstance(content, list):
                text_parts = []
                for item in content:
                    if isinstance(item, dict):
                        item_type = item.get("type", "")
                        item_data = item.get("data", {})
                        if item_type == "text":
                            text_parts.append(item_data.get("text", ""))
                        elif item_type == "image":
                            text_parts.append("[图片]")
                    elif isinstance(item, str):
                        text_parts.append(item)
                content = " ".join(text_parts) if text_parts else ""

            user_id = str(perception.get("user_id", "unknown"))
            group_id = str(perception.get("group_id", ""))
            platform = perception.get("platform", "qq")
            sender_name = perception.get("sender_name", "用户")
            message_type = perception.get("message_type", "")
            session_id = f"{platform}_{user_id}"

            logger.info(f"[记忆管理器] 收到消息: {content[:50]}...")

            # 存储到 MemoryNet 对话历史
            if self.memory_net and self.memory_net.conversation_history:
                metadata = {
                    "user_id": user_id,
                    "group_id": group_id,
                    "message_type": message_type,
                    "sender": sender_name,
                    "chat_label": f"群聊_{group_id}"
                    if message_type == "group" and group_id
                    else "私聊",
                }
                await self.memory_net.conversation_history.add_message(
                    session_id=session_id,
                    role="user",
                    content=content,
                    metadata=metadata,
                )

                # 每 3 条消息强制 flush 到磁盘
                self._conv_save_counter = getattr(self, "_conv_save_counter", 0) + 1
                if self._conv_save_counter % 3 == 0:
                    with contextlib.suppress(Exception):
                        await self.memory_net.conversation_history.flush()

            # 存储到统一记忆系统 (新版 API)
            await store_dialogue(
                content=content,
                role="user",
                user_id=user_id,
                session_id=session_id,
                platform=platform,
                metadata={
                    "sender_name": sender_name,
                    "message_type": message_type,
                    "group_id": group_id,
                },
            )

            # 自动检测重要信息并存储
            important_patterns = [
                (r"生日", "生日"),
                (r"我喜欢", "喜好"),
                (r"喜欢(.+)", "喜好"),
                (r"我叫", "名字"),
                (r"讨厌", "厌恶"),
                (r"星座", "星座"),
                (r"电话", "电话"),
                (r"邮箱", "邮箱"),
                (r"记住", "明确要求"),
                (r"你记着", "明确要求"),
                (r"帮我记住", "明确要求"),
            ]

            for pattern, info_type in important_patterns:
                if re.search(pattern, content):
                    priority = (
                        0.9
                        if info_type in ["生日", "电话", "邮箱", "明确要求"]
                        else 0.7
                    )
                    await store_important(
                        content=content,
                        user_id=user_id,
                        tags=[info_type],
                        priority=priority,
                        metadata={
                            "source": "auto_extract",
                            "info_type": info_type,
                        },
                    )
                    logger.info(f"[记忆管理器] 已自动存储重要信息: {info_type}")
                    break

        except Exception as e:
            logger.error(f"[记忆管理器] 存储用户消息失败: {e}", exc_info=True)

    async def store_assistant_response(self, perception: Dict, response: str) -> None:
        """
        存储 AI 响应到记忆系统

        【星璇增强】
        - 弥娅的承诺、观点、建议等会自动升级为 LONG_TERM
        - 使用 ASSISTANT_SELF 来源类型标识弥娅自记忆
        - 通过 Historian 双向分析（用户 + 弥娅）

        Args:
            perception: 感知数据
            response: AI 响应内容
        """
        try:
            user_id = str(perception.get("user_id", "unknown"))
            group_id = str(perception.get("group_id", ""))
            message_type = perception.get("message_type", "")
            platform = perception.get("platform", "qq")
            session_id = f"{platform}_{user_id}"

            # 存储到 MemoryNet
            if self.memory_net and self.memory_net.conversation_history:
                metadata = {
                    "user_id": user_id,
                    "group_id": group_id,
                    "message_type": message_type,
                    "sender": "弥娅",
                    "chat_label": f"群聊_{group_id}"
                    if message_type == "group" and group_id
                    else "私聊",
                }
                await self.memory_net.conversation_history.add_message(
                    session_id=session_id,
                    role="assistant",
                    content=response,
                    metadata=metadata,
                )

                # 每 3 条消息强制 flush 到磁盘
                self._conv_save_counter = getattr(self, "_conv_save_counter", 0) + 1
                if self._conv_save_counter % 3 == 0:
                    with contextlib.suppress(Exception):
                        await self.memory_net.conversation_history.flush()

            # 存储到统一记忆系统 (新版 API)
            await store_dialogue(
                content=response,
                role="assistant",
                user_id=user_id,
                session_id=session_id,
                platform=platform,
                metadata={
                    "sender_name": "弥娅",
                    "message_type": message_type,
                    "group_id": group_id,
                },
            )

            # 【星璇增强】分析弥娅回复中的重要内容，自动升级存储
            user_content = perception.get("content", "")
            try:
                await self._analyze_and_upgrade_assistant_memory(
                    user_input=user_content,
                    ai_response=response,
                    user_id=user_id,
                    group_id=group_id,
                    message_type=message_type,
                )
            except Exception as e:
                logger.debug(f"[记忆管理器] 弥娅自记忆分析失败: {e}")

            # 使用 Historian 自动提取重要记忆
            try:
                await self.historian.process_conversation(
                    user_input=user_content,
                    ai_response=response,
                    user_id=user_id,
                    group_id=group_id,
                    message_type=message_type,
                )
            except Exception as e:
                logger.debug(f"[记忆管理器] Historian 提取失败: {e}")

            # 【LifeBook 集成】自动记录到多视角日记系统
            try:
                from memory.lifebook import get_lifebook

                lifebook = get_lifebook()
                if lifebook and user_content:
                    emotion_val = perception.get("emotion", "平静")
                    if isinstance(emotion_val, dict):
                        emotion_val = emotion_val.get("primary", "平静")
                    await lifebook.record_interaction(
                        user_message=user_content,
                        lover_response=response,
                        topics=[message_type],
                        emotion=str(emotion_val) if emotion_val else "平静",
                    )
            except Exception as e:
                logger.debug(f"[记忆管理器] LifeBook 记录失败: {e}")

            # 【每日摘要】跨天时自动生昨日摘要
            try:
                from datetime import datetime as dt
                from datetime import timedelta

                today = dt.now().strftime("%Y-%m-%d")
                self._last_summary_date = getattr(self, "_last_summary_date", "")
                if self._last_summary_date and self._last_summary_date != today:
                    core = await get_memory_core()
                    yesterday = (dt.now() - timedelta(days=1)).strftime("%Y-%m-%d")
                    daily = await core.get_daily_dialogues(yesterday)
                    if daily and len(daily) >= 3:
                        lines = [
                            f"- {m.content[:80]}..."
                            if len(m.content) > 80
                            else f"- {m.content}"
                            for m in daily[:20]
                        ]
                        summary_text = "\n".join(lines)
                        await core.store_daily_summary(
                            date_key=yesterday,
                            summary=summary_text,
                            user_id="global",
                            dialogue_count=len(daily),
                        )
                        logger.info(
                            f"[记忆管理器] 已生成 {yesterday} 每日摘要 ({len(daily)} 条对话)"
                        )
                self._last_summary_date = today
            except Exception as e:
                logger.debug(f"[记忆管理器] 每日摘要生成跳过: {e}")

            # 对话历史压缩
            try:
                if self.memory_net and self.memory_net.conversation_history:
                    messages = await self.memory_net.conversation_history.get_history(
                        session_id, limit=100
                    )
                    if len(messages) > 50:
                        if hasattr(self.memory_net, "compress_conversation_to_tide"):
                            await self.memory_net.compress_conversation_to_tide(
                                session_id=session_id, recent_count=30
                            )
                            logger.info(f"[记忆管理器] 已触发对话压缩: {session_id}")
            except Exception as e:
                logger.debug(f"[记忆管理器] 对话压缩失败: {e}")

        except Exception as e:
            logger.error(f"[记忆管理器] 存储 AI 响应失败: {e}")

    async def _analyze_and_upgrade_assistant_memory(
        self,
        user_input: str,
        ai_response: str,
        user_id: str,
        group_id: str,
        message_type: str,
    ) -> None:
        """
        【星璇增强】分析弥娅回复，自动识别并升级重要自记忆

        模式从 text_config.json 的 assistant_self.patterns 加载
        """
        import json
        import re
        from pathlib import Path

        # 从配置文件加载模式
        assistant_patterns = []
        try:
            config_path = Path(__file__).parent.parent / "config" / "text_config.json"
            if config_path.exists():
                with open(config_path, "r", encoding="utf-8") as f:
                    full_config = json.load(f)
                self_config = full_config.get("assistant_self", {})
                patterns = self_config.get("patterns", {})
                base_importance = self_config.get("base_importance", {})

                # 扁平化所有模式: (pattern, mem_type, importance, tags)
                type_label_map = {
                    "commitment": "承诺",
                    "opinion": "观点",
                    "emotion": "情感",
                    "knowledge": "知识",
                    "self_awareness": "自我认知",
                }

                for category, pattern_list in patterns.items():
                    importance = base_importance.get(category, 0.5)
                    mem_type = type_label_map.get(category, category)
                    for item in pattern_list:
                        if isinstance(item, list) and len(item) >= 2:
                            pattern_regex = item[0]
                            tag_name = item[1]
                            assistant_patterns.append(
                                (pattern_regex, mem_type, importance, [tag_name])
                            )
        except Exception as e:
            logger.warning(f"[记忆管理器] 加载自记忆配置失败: {e}")
            return

        if not assistant_patterns:
            logger.debug("[记忆管理器] 自记忆配置为空，跳过分析")
            return

        for pattern, mem_type, base_importance, tags in assistant_patterns:
            match = re.search(pattern, ai_response)
            if match:
                content = match.group(0).strip()
                if len(content) < 5:
                    continue

                # 构建记忆内容
                memory_content = f"[弥娅{mem_type}] {content}"

                # 存储为 LONG_TERM（自动升级）
                try:
                    await store_important(
                        content=memory_content,
                        user_id=user_id,
                        tags=tags + ["星璇自记忆", f"类型_{mem_type}"],
                        priority=min(1.0, base_importance),
                        metadata={
                            "source": "assistant_self",
                            "memory_type": mem_type,
                            "role": "assistant",
                            "group_id": group_id,
                            "message_type": message_type,
                            "original_context": user_input[:100] if user_input else "",
                        },
                    )
                    logger.info(
                        f"[星璇·自记忆升级] {mem_type}: {content[:30]}... "
                        f"(priority={base_importance})"
                    )
                except Exception as e:
                    logger.debug(f"[星璇·自记忆升级] 存储失败: {e}")

                # 每个回复只记录一条最重要的，避免刷屏
                break

    async def store_unified_memory(self, perception: Dict, role: str = "user") -> None:
        """
        存储统一记忆（跨平台）

        【星璇增强】当 role="assistant" 时，自动分析弥娅回复中的
        承诺、观点、建议等重要内容，升级为 LONG_TERM 自记忆

        Args:
            perception: 感知数据
            role: 角色 ('user' 或 'assistant')
        """
        try:
            platform = perception.get("platform", "terminal")
            user_id = str(perception.get("user_id", "unknown"))

            if role == "user":
                content = perception.get("content", "") or perception.get("input", "")
                sender_name = perception.get("sender_name", "用户")
            else:
                content = perception.get("response", "")
                sender_name = "弥娅"

            session_id = f"{platform}_{user_id}"

            # 存储到统一记忆系统
            await store_dialogue(
                content=content,
                role=role,
                user_id=user_id,
                session_id=session_id,
                platform=platform,
                metadata={
                    "sender_name": sender_name,
                    "group_id": perception.get("group_id", ""),
                    "message_type": perception.get("message_type", ""),
                },
            )

            # 存储到 MemoryNet
            if self.memory_net and self.memory_net.conversation_history:
                await self.memory_net.conversation_history.add_message(
                    session_id=session_id,
                    role=role,
                    content=content,
                    metadata={
                        "platform": platform,
                        "user_id": user_id,
                        "sender_name": sender_name,
                    },
                )

            # 【星璇增强】弥娅回复时，自动分析并升级重要自记忆
            if role == "assistant" and content and len(content.strip()) >= 5:
                user_input = perception.get("content", "") or perception.get(
                    "input", ""
                )
                group_id = perception.get("group_id", "")
                message_type = perception.get("message_type", "")
                try:
                    await self._analyze_and_upgrade_assistant_memory(
                        user_input=user_input,
                        ai_response=content,
                        user_id=user_id,
                        group_id=group_id,
                        message_type=message_type,
                    )
                except Exception as e:
                    logger.debug(f"[记忆管理器] 弥娅自记忆分析失败: {e}")

        except Exception as e:
            logger.error(f"[记忆管理器] 存储统一记忆失败: {e}")

    async def get_conversation_history(
        self, session_id: str, current_input: str = "", max_tokens: int = 2000
    ) -> List[Dict]:
        """
        获取对话历史上下文

        Args:
            session_id: 会话ID
            current_input: 当前用户输入
            max_tokens: 最大token数

        Returns:
            对话历史列表
        """
        if not self.memory_net or not self.memory_net.conversation_history:
            return []

        needs_recall = self._check_needs_recall(current_input)
        max_messages = 30 if needs_recall else 8

        try:
            messages = await self.memory_net.conversation_history.get_history(
                session_id, limit=max_messages
            )

            if not messages:
                return []

            recent_messages = (
                messages[-max_messages:] if len(messages) > max_messages else messages
            )

            context = []
            total_tokens = 0

            for msg in recent_messages:
                token_estimate = len(msg.content) // 4
                if total_tokens + token_estimate > max_tokens:
                    break

                context.append(
                    {
                        "role": msg.role,
                        "content": msg.content,
                        "timestamp": msg.timestamp if hasattr(msg, "timestamp") else "",
                    }
                )
                total_tokens += token_estimate

            return context

        except Exception as e:
            logger.error(f"[记忆管理器] 获取对话历史失败: {e}")
            return []

    def _check_needs_recall(self, user_input: str) -> bool:
        """检测用户是否在问关于过去的问题"""
        if not user_input:
            return False

        recall_patterns = [
            r"你记得",
            r"你还记得",
            r"记得.*吗",
            r"上次",
            r"上次我们",
            r"之前.*聊",
            r"昨天",
            r"前天",
            r"以前.*怎么样",
            r"我们.*聊过",
            r"过去.*事",
            r"曾经",
            r"记得.*什么",
            r"回忆.*一下",
            r"想起.*什么",
        ]

        for pattern in recall_patterns:
            if re.search(pattern, user_input):
                logger.info(f"[记忆管理器] 检测到回忆请求: {user_input[:30]}")
                return True

        return False

    async def get_memory_stats(self) -> Dict:
        """获取记忆统计信息"""
        try:
            from memory import get_memory_stats

            return await get_memory_stats()
        except Exception as e:
            logger.error(f"[记忆管理器] 获取统计失败: {e}")
            return {}
