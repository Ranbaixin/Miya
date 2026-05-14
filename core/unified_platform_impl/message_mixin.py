"""
平台消息处理辅助 Mixin

提供所有平台共享的消息转换、路由逻辑和通用后处理。
每个平台只需：解析消息 → route_to_decision_hub() → 拆分发送
"""

from __future__ import annotations

import asyncio
import os
import logging
from datetime import datetime
from typing import Dict, Any, Optional

logger = logging.getLogger("Miya.PlatformMessageMixin")


class MessageMixin:
    """消息处理辅助：将平台消息转换为 M-Link 格式并路由到 DecisionHub"""

    _miya_core: Any = None
    platform_id: str = ""

    def set_miya_core(self, miya):
        self._miya_core = miya

    # ============ 通用后处理 (所有平台自动享有) ============

    @staticmethod
    def _filter_thinking(text: str) -> str:
        """过滤思考过程（DeepSeek R1 等推理模型的残留）"""
        import re

        patterns = [
            r"^好的，用户是在.*?\n",
            r"^首先，用户.*?\n",
            r"^接下来，我需要.*?\n",
            r"^在之前的对话中.*?\n",
            r"^所以我的回答.*?\n",
            r"^综上所述.*?\n",
            r"^嗯，我是弥娅.*?\n",
            r"^这个问题的回答.*?\n",
            r"^根据设定，我.*?\n",
            r"^作为.*?我.*?\n",
        ]
        for p in patterns:
            text = re.sub(p, "", text, flags=re.IGNORECASE)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    @staticmethod
    def _filter_output(text: str) -> str:
        """感叹号刷屏过滤"""
        try:
            import json
            import random
            from pathlib import Path

            config_path = (
                Path(__file__).parent.parent.parent / "config" / "text_config.json"
            )
            if not config_path.exists():
                return text

            with open(config_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            of = cfg.get("output_filter", {})
            if not of.get("enabled", False):
                return text

            threshold = of.get("exclamation_threshold", 0)
            if threshold > 0:
                count = text.count("!")
                if count >= threshold:
                    fallbacks = of.get("fallback_responses", ["好的~"])
                    logger.info(f"[MessageMixin] 刷屏过滤: {count}个感叹号 → 替换")
                    return random.choice(fallbacks)
        except Exception:
            pass
        return text

    async def _after_route(self, content: str, response: str, user_id: str) -> None:
        """路由后副作用: 离别检测 + LifeBook 记录"""
        if not response or not content:
            return
        try:
            miya = getattr(self, "_miya_core", None)
            if not miya or not hasattr(miya, "decision_hub"):
                return

            from core.qq_command_config import is_farewell_keyword

            if is_farewell_keyword(content):
                logger.info(f"[{self.platform_id}] 检测到离别语")
                await miya.decision_hub.handle_session_end(
                    session_id=user_id, platform=self.platform_id
                )
        except Exception:
            pass

        try:
            from memory.lifebook import get_lifebook

            lifebook = get_lifebook()
            await lifebook.record_interaction(
                user_message=content,
                lover_response=response,
                topics=[],
                emotion="平静",
            )
        except Exception:
            pass

    @staticmethod
    def _split_message(text: str, max_len: int = 200) -> list:
        """按句子边界拆分长消息"""
        if len(text) <= max_len:
            return [text]
        chunks = []
        remaining = text
        while remaining:
            if len(remaining) <= max_len:
                chunks.append(remaining)
                break
            segment = remaining[:max_len]
            break_points = [
                segment.rfind("\n\n"),
                segment.rfind("\n"),
                segment.rfind("。"),
                segment.rfind("！"),
                segment.rfind("？"),
                segment.rfind("."),
                segment.rfind("! "),
                segment.rfind("? "),
                segment.rfind(" "),
            ]
            best = max(break_points)
            if best > max_len // 2:
                split_at = best + 1
            else:
                split_at = max_len
            chunks.append(remaining[:split_at].strip())
            remaining = remaining[split_at:].strip()
        return chunks

    # ============ 核心路由 ============

    async def route_to_decision_hub(
        self,
        content: str,
        user_id: str,
        user_name: str = "",
        message_type: str = "private",
        group_id: str = "",
        group_name: str = "",
        sender_role: str = "member",
        is_at_bot: bool = True,
        extra: Optional[Dict] = None,
    ) -> str:
        """
        将平台消息路由到 DecisionHub 并返回响应

        Args:
            content: 消息文本
            user_id: 用户ID
            user_name: 用户名
            message_type: 消息类型 (private/group/c2c/channel)
            group_id: 群组ID
            group_name: 群组名称
            sender_role: 发送者角色
            is_at_bot: 是否 @ 了机器人
            extra: 额外数据

        Returns:
            弥娅的响应文本
        """
        miya = self._miya_core
        if not miya:
            return "弥娅系统未就绪"

        try:
            from mlink.message import Message

            group_id_int = 0
            if group_id:
                try:
                    group_id_int = int(group_id)
                except ValueError:
                    pass

            perception_data = {
                "content": content,
                "input": content,
                "sender_name": user_name or user_id,
                "user_id": user_id,
                "sender_id": user_id,
                "unified_user_id": f"{self.platform_id}_{user_id}",
                "message_type": message_type,
                "group_id": group_id_int,
                "group_name": group_name,
                "sender_role": sender_role,
                "platform": self.platform_id,
                "source": self.platform_id,
                "is_at_bot": is_at_bot,
                "reply_to_bot": False,
                "timestamp": datetime.now().isoformat(),
                "is_owner": False,
                "owner_name": "",
            }

            # 注入身份信息：检查发送者是否是超管/所有者
            try:
                from core.unified_permission import get_permission_engine

                engine = get_permission_engine()
                if engine.is_superadmin(str(user_id), platform=self.platform_id):
                    perception_data["is_owner"] = True
                    # 从 superadmins 配置中获取名字和规范ID
                    for person, info in engine._config.get("superadmins", {}).items():
                        perception_data["owner_name"] = info.get("name", "")
                        # 获取规范用户ID（第一个有值的平台ID作为标准）
                        canonical_id = str(user_id)
                        ids = info.get("ids", {})
                        for pid, raw_ids in ids.items():
                            if isinstance(raw_ids, list) and raw_ids:
                                canonical_id = str(raw_ids[0])
                                break
                            elif isinstance(raw_ids, str) and raw_ids:
                                canonical_id = str(raw_ids)
                                break
                        perception_data["canonical_user_id"] = canonical_id
                        perception_data["sender_name"] = (
                            info.get("name", "") or user_name or user_id
                        )
                        # 关键：统一 user_id 为规范ID，确保记忆存储在同一桶内
                        perception_data["user_id"] = canonical_id
                        break
            except Exception:
                pass

            if extra:
                perception_data.update(extra)

            mlink_msg = Message(
                msg_type="data",
                content=perception_data,
                source=self.platform_id,
            )

            if hasattr(miya, "decision_hub"):
                response = await miya.decision_hub.process_perception_cross_platform(
                    mlink_msg
                )
                # === 通用后处理 ===
                if response:
                    response = self._filter_thinking(response)
                    response = self._filter_output(response)
                # TTS 本地播放 (fire-and-forget, 所有平台)
                if response and self._tts_should_local():
                    asyncio.ensure_future(self._tts_play_response(response))
                # 副作用 (fire-and-forget)
                asyncio.ensure_future(
                    self._after_route(content, response or "", user_id)
                )
                return response  # None → 不回复, 空字符串 → 平台自行兜底
            else:
                return "决策系统未就绪"

        except Exception as e:
            logger.error(f"[{self.platform_id}] 消息处理异常: {e}", exc_info=True)
            return f"处理消息时出错了: {e}"

    # ============ TTS 通用处理 ============

    _tts_cache: Dict[str, str] = {}  # text_hash → audio_path, 短 TTL 缓存

    def _tts_should_voice(self) -> bool:
        """是否应发送语音到平台（仅支持语音的平台）"""
        try:
            import json

            with open("config/tts_config.json", "r", encoding="utf-8") as f:
                c = json.load(f)
            return c.get("enabled", False) and c.get("qq_default_mode") == "voice"
        except Exception:
            return False

    def _tts_should_local(self) -> bool:
        """是否应本地电脑播放"""
        try:
            import json

            with open("config/tts_config.json", "r", encoding="utf-8") as f:
                c = json.load(f)
            return c.get("local_playback_enabled", False)
        except Exception:
            return False

    def _tts_platform_supports_voice(self) -> bool:
        """当前平台是否支持发送语音消息"""
        return self.platform_id in ("aiocqhttp", "qqofficial")

    async def _tts_process(self, text: str) -> tuple[str | None, bool]:
        """
        通用 TTS 处理：合成 + 可选发送语音 + 本地播放
        返回 (audio_path, sent_as_voice)
        平台发送端据此决定是否跳过文字发送
        """
        should_voice = self._tts_should_voice() and self._tts_platform_supports_voice()
        should_local = self._tts_should_local()
        if not should_voice and not should_local:
            return None, False
        if not text or not text.strip():
            return None, False

        try:
            from core.tts.engine_router import synthesize

            audio_path = await synthesize(text)
        except Exception as e:
            logger.debug(f"[{self.platform_id}] TTS 合成失败: {e}")
            return None, False

        if not audio_path:
            return None, False

        sent = False
        if should_voice:
            try:
                sent = await self._tts_send_voice(audio_path, text)
            except Exception as e:
                logger.warning(f"[{self.platform_id}] TTS 语音发送失败: {e}")

        if should_local:
            await self._tts_play_local(audio_path)

        return audio_path, sent

    async def _tts_send_voice(self, audio_path: str, text: str) -> bool:
        """发送语音到平台，子类可覆写"""
        return False

    async def _tts_play_local(self, audio_path: str):
        """本地电脑播放"""
        import concurrent.futures

        def _play_blocking():
            import simpleaudio as sa
            import wave

            with wave.open(audio_path, "rb") as wf:
                wave_obj = sa.WaveObject.from_wave_read(wf)
                play_obj = wave_obj.play()
                play_obj.wait_done()

        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, _play_blocking)
        except ImportError:
            logger.debug("simpleaudio 不可用，跳过本地播放")
        except Exception as e:
            logger.debug(f"本地播放异常: {e}")

    async def _tts_play_response(self, text: str):
        """TTS 本地播放响应 (fire-and-forget, 所有平台共享)"""
        # 支持语音的平台自己处理本地播放（发送语音后直接播同一文件）
        if self._tts_should_voice() and self._tts_platform_supports_voice():
            return

        try:
            from core.tts.engine_router import synthesize

            logger.info(f"[{self.platform_id}] TTS 本地合成中... ({len(text)} chars)")
            audio_path = await synthesize(text)
            if audio_path:
                logger.info(f"[{self.platform_id}] TTS 本地播放中...")
                await self._tts_play_local(audio_path)
                logger.info(f"[{self.platform_id}] TTS 本地播放完成")
            else:
                logger.warning(f"[{self.platform_id}] TTS 合成返回空路径")
        except Exception as e:
            logger.warning(f"[{self.platform_id}] TTS 本地播放失败: {e}")
