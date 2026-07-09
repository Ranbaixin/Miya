"""
平台消息处理辅助 Mixin

提供所有平台共享的消息转换、路由逻辑和通用后处理。
每个平台只需：解析消息 → route_to_decision_hub() → 拆分发送
"""

from __future__ import annotations

import asyncio
import contextlib
import json as _json
import logging
import os
from datetime import datetime
from typing import Any, Dict, Optional

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

        # v4.5.1: 移除英文/代码风格前缀（如 [Paste..., [Write..., etc）
        lines = text.split("\n")
        if lines:
            first_line = lines[0].strip()
            if (first_line.startswith("[") and not re.search(r"[\u4e00-\u9fff]", first_line)) or (
                re.match(r"^[A-Za-z][a-z]+\s", first_line) and not re.search(r"[\u4e00-\u9fff]", first_line)
            ):
                lines.pop(0)
                while lines and not lines[0].strip():
                    lines.pop(0)
                text = "\n".join(lines).strip()

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

            config_path = Path(__file__).parent.parent.parent / "config" / "text_config.json"
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
                await miya.decision_hub.handle_session_end(session_id=user_id, platform=self.platform_id)
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
        """按自然段落拆分——只有双换行(\n\n)视为分条信号，单换行保持在同一消息内"""
        if "\n\n" not in text:
            return [text]

        chunks = []
        paragraphs = text.split("\n\n")
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            if len(para) <= max_len:
                chunks.append(para)
            else:
                chunks.extend(MessageMixin._split_long_line(para, max_len))

        return chunks

    @staticmethod
    def _split_long_line(line: str, max_len: int) -> list:
        """拆分超长单行——按标点找断点"""

        chunks = []
        remaining = line
        while remaining:
            if len(remaining) <= max_len:
                chunks.append(remaining.strip())
                break
            segment = remaining[:max_len]
            break_points = []
            for punct in ["。", "！", "？", "；", "，"]:
                pb = segment.rfind(punct)
                if pb > max_len // 3:
                    break_points.append(pb + 1)
            if break_points:
                split_at = max(break_points)
            else:
                # 没有任何标点，回退到空格或硬切
                space = segment.rfind(" ")
                split_at = space + 1 if space > max_len // 2 else max_len
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
                with contextlib.suppress(ValueError):
                    group_id_int = int(group_id)

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
                    for _person, info in engine._config.get("superadmins", {}).items():
                        perception_data["owner_name"] = info.get("name", "")
                        # 获取规范用户ID（第一个有值的平台ID作为标准）
                        canonical_id = str(user_id)
                        ids = info.get("ids", {})
                        for _pid, raw_ids in ids.items():
                            if isinstance(raw_ids, list) and raw_ids:
                                canonical_id = str(raw_ids[0])
                                break
                            elif isinstance(raw_ids, str) and raw_ids:
                                canonical_id = str(raw_ids)
                                break
                        perception_data["canonical_user_id"] = canonical_id
                        perception_data["sender_name"] = info.get("name", "") or user_name or user_id
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
                # ── 新斜杠命令系统 (在路由到 DecisionHub 之前) ──
                cmd_response = await _dispatch_slash_command(
                    self, content, user_id, group_id, message_type
                )
                if cmd_response:
                    await _send_cmd_reply(self, cmd_response, user_id, group_id, message_type)
                    return

                # ── 兼容旧版斜杠命令 (兜底) ──
                cmd_response = _handle_slash_command(self, content, user_id, group_id)
                if cmd_response:
                    await _send_cmd_reply(self, cmd_response, user_id, group_id, message_type)
                    return

                # ── 内容自动检测管线（B站/arXiv/GitHub）──
                try:
                    from webnet.ToolNet.pipelines.content_pipeline import get_pipeline

                    pipeline = get_pipeline()
                    pipeline_results = await pipeline.detect_and_process(content)
                    if pipeline_results:
                        pipeline_texts = []
                        for pr in pipeline_results:
                            pipeline_texts.append(pr["content"])
                        pipeline_context = "\n\n".join(pipeline_texts)

                        # 注入到 perception_data，追加到 content 后（不干扰谛听前置匹配）
                        perception_data["content"] = (
                            f"{content}\n\n{pipeline_context}"
                        )
                        perception_data["pipeline_detections"] = pipeline_context
                        mlink_msg.content["content"] = perception_data["content"]
                        mlink_msg.content["pipeline_detections"] = pipeline_context
                        logger.info(f"[Pipeline] 检测到 {len(pipeline_results)} 个内容，已注入上下文")
                except Exception as e:
                    logger.debug(f"[Pipeline] 检测失败: {e}")

                # ── AP 聆听：先让弥娅"听到"消息，产生实时内心反应 ──
                try:
                    from core.miya_psyarch_bridge import get_psyarch_bridge
                    from miya_psyarch.action_bridge import get_action_bridge

                    bridge = get_psyarch_bridge()
                    if bridge and bridge._initialized:
                        bridge.hear_message(content)
                        action_bridge = get_action_bridge(bridge._engine)
                        action_bridge.set_platform_context(
                            {"platform": self.platform_id, "user_id": user_id, "group_id": group_id}
                        )
                except Exception:
                    pass

                # ── 统一路由：DecisionHub 融合 AP 认知状态处理所有消息 ──
                response = await miya.decision_hub.process_perception_cross_platform(mlink_msg)

                # ── AP 教育闭环：LLM 回复 → 教育信号 → AP 学习对话模式 ──
                if response and content:
                    try:
                        from core.miya_psyarch_bridge import get_psyarch_bridge

                        bridge = get_psyarch_bridge()
                        if bridge and bridge._initialized:
                            bridge.feed_education(content, response)
                    except Exception:
                        pass

                # ── AP 离线兜底：LLM 不可用时，白箱认知引擎自主回应 ──
                # 群聊消息已由决策层处理跳过逻辑，离线兜底仅用于私聊
                if not response and content and message_type != "group":
                    try:
                        from core.miya_psyarch_bridge import get_psyarch_bridge

                        bridge = get_psyarch_bridge()
                        if bridge and bridge._initialized:
                            response = bridge.hear_and_respond(content)
                    except Exception:
                        pass

                # === 通用后处理 ===
                if response:
                    response = self._filter_thinking(response)
                    response = self._filter_output(response)
                # TTS 本地播放 (fire-and-forget, 所有平台)
                if response and self._tts_should_local():
                    asyncio.ensure_future(self._tts_play_response(response))
                # 副作用 (fire-and-forget)
                asyncio.ensure_future(self._after_route(content, response or "", user_id))
                return response  # None → 不回复, 空字符串 → 平台自行兜底
            else:
                return "决策系统未就绪"

        except Exception as e:
            logger.error(f"[{self.platform_id}] 消息处理异常: {e}", exc_info=True)
            try:
                from core.miya_psyarch_bridge import get_psyarch_bridge

                bridge = get_psyarch_bridge()
                if bridge and bridge._initialized and content:
                    return bridge.hear_and_respond(content)
            except Exception:
                pass
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

        def _play_blocking():
            import wave

            import simpleaudio as sa

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


def _handle_slash_command(self, content: str, user_id: str, group_id: str) -> str | None:
    """拦截并处理斜杠命令，返回响应字符串，不匹配时返回 None"""
    import json
    from pathlib import Path

    text = content.strip().lower()

    # 加载命令配置
    cfg = {}
    try:
        cp = Path(__file__).resolve().parent.parent.parent / "config" / "text_config.json"
        cfg = json.loads(cp.read_text(encoding="utf-8"))
    except Exception:
        pass

    slash = cfg.get("slash_commands", {})
    responses = cfg.get("command_responses", {})

    # /train
    train_cfg = slash.get("train", {})
    if text in [a.lower() for a in train_cfg.get("aliases", [])] or text.startswith("/train"):
        from core.miya_psyarch_bridge import get_psyarch_bridge

        bridge = get_psyarch_bridge()
        if not bridge or not bridge._initialized:
            return responses.get("train", {}).get("not_ready", "AP 未就绪")
        mode = text.replace("/train", "").strip() or "all"
        if mode not in train_cfg.get("modes", ["all", "distill", "pretrain"]):
            return responses.get("train", {}).get("unsupported_mode", "").format(mode=mode)
        result = bridge.train(mode)
        if result.get("error"):
            return f"训练失败: {result['error']}"
        summary = bridge.training_summary()
        return (
            responses.get("train", {})
            .get("success", "")
            .format(
                mode=mode,
                distilled=result.get("distill", {}).get("rules_adjusted", 0) or summary.get("distilled_rules", 0),
                pretrained=result.get("pretrain", {}).get("anchors", summary.get("pretrain_anchors", 0)) or 0,
                rl=summary.get("rl_events", 0),
            )
        )

    # /ap
    ap_cfg = slash.get("ap", {})
    if text in [a.lower() for a in ap_cfg.get("aliases", [])]:
        from core.miya_psyarch_bridge import get_psyarch_bridge

        bridge = get_psyarch_bridge()
        if not bridge:
            return "AP 未就绪"
        emo = bridge.emotion_snapshot()
        nt = emo.get("nt_channels", {})
        mf = emo.get("miya_feelings", {})
        top = sorted(mf.items(), key=lambda x: -x[1])[:3]
        mp = "locked" if bridge.memory_protection else "unlocked"
        summary = bridge.training_summary()
        return (
            f"◆ APV2.1 | OXY={nt.get('OXY', 0):.0%} DA={nt.get('DA', 0):.0%} "
            f"COR={nt.get('COR', 0):.0%} NOV={nt.get('NOV', 0):.0%}\n"
            f"  感受: {', '.join(f'{k}:{v:.1f}' for k, v in top) if top else '平静'}\n"
            f"  训练: {summary.get('distilled_rules', 0)}规则 {summary.get('rl_events', 0)}RL\n"
            f"  记忆: {mp}"
        )

    # /状态
    status_cfg = slash.get("status", {})
    if text in [a.lower() for a in status_cfg.get("aliases", [])]:
        from config.config_utils import get_text_message
        return get_text_message("command_responses", "status", default="弥娅系统运行中 | APV2.1 激活")

    # /帮助
    help_cfg = slash.get("help", {})
    if text in [a.lower() for a in help_cfg.get("aliases", [])]:
        from config.config_utils import get_text_message
        return responses.get("help", {}).get("all",
            get_text_message("command_responses", "help", "all", default="可用: /ap /train /状态 /帮助"))

    return None


async def _dispatch_slash_command(
    platform: Any, content: str, user_id: str, group_id: str, message_type: str
) -> str | None:
    """新版统一斜杠命令分发"""
    try:
        from core.command_system import CommandContext, get_command_registry

        registry = get_command_registry()
        match = registry.match(content)
        if not match:
            return None

        command_name, subcommand, args = match

        # 构建上下文
        ctx = CommandContext(
            sender_id=int(user_id) if user_id.isdigit() else 0,
            user_id=user_id,
            group_id=int(group_id) if group_id and group_id.isdigit() else 0,
            scope="private" if message_type == "private" else "group",
        )

        # 注入平台能力
        ctx.onebot_client = getattr(platform, "_ws", None)

        async def send_group_msg(gid, text):
            if hasattr(platform, "_send_onebot_reply"):
                await platform._send_onebot_reply(
                    str(gid), text, message_type="group", group_id=str(gid)
                )

        async def send_private_msg(uid, text):
            if hasattr(platform, "_send_onebot_reply"):
                await platform._send_onebot_reply(
                    str(uid), text, message_type="private", user_id=str(uid)
                )

        ctx.send_group_message = send_group_msg
        ctx.send_private_message = send_private_msg

        # 注入系统组件
        try:
            from webnet.ToolNet.tools.knowledge.knowledge_store import get_knowledge_store
            ctx.knowledge_store = get_knowledge_store()
        except Exception:
            pass

        miya = getattr(platform, "_miya_core", None)
        if miya:
            ctx.ai_client = getattr(miya, "ai_client", None)
            ctx.cognitive_service = getattr(miya, "cognitive_service", None)

        # 权限信息 — 从 permissions.json 读取
        ctx.superadmin_qq = int(os.getenv("QQ_SUPERADMIN_QQ", "0"))
        ctx.bot_qq = int(os.getenv("QQ_BOT_QQ", "0"))
        try:
            from core.unified_permission import get_permission_engine
            engine = get_permission_engine()
            if engine.is_superadmin(str(ctx.sender_id), platform=getattr(platform, "platform_id", "aiocqhttp")):
                ctx.superadmin_qq = ctx.sender_id
        except Exception:
            pass

        # 检查权限
        cmd = registry._commands.get(command_name, {})
        required_permission = cmd.get("permission", "public")

        # 子命令权限
        if subcommand and cmd.get("subcommands", {}).get(subcommand, {}).get("permission"):
            required_permission = cmd["subcommands"][subcommand]["permission"]

        if not ctx.check_permission(required_permission):
            from config.config_utils import get_command_message
            return get_command_message("permission_denied", command=command_name, permission=required_permission)

        # 限流检查
        allowed, remaining = registry.check_rate_limit(command_name, user_id, required_permission)
        if not allowed:
            from config.config_utils import get_command_message
            return get_command_message("rate_limited", seconds=f"{remaining:.0f}")

        # 执行
        result = await registry.execute(command_name, subcommand, args, ctx)
        return result

    except Exception as e:
        logger.warning(f"[Commands] 分发失败: {e}", exc_info=True)
        return None


async def _send_cmd_reply(platform: Any, response: str, user_id: str, group_id: str, message_type: str) -> None:
    """根据消息来源发送命令回复到正确的会话"""
    try:
        import json as _json
        ws = getattr(platform, "_ws", None)
        if not ws:
            await _send_private(platform, response, user_id)
            return

        if message_type == "group" and group_id:
            payload = {
                "action": "send_group_msg",
                "params": {
                    "group_id": int(group_id),
                    "message": str(response),
                },
            }
        else:
            payload = {
                "action": "send_private_msg",
                "params": {
                    "user_id": int(user_id),
                    "message": str(response),
                },
            }
        await ws.send_str(_json.dumps(payload))
    except Exception as e:
        logger.warning(f"[Commands] 回复发送失败: {e}")
        await _send_private(platform, response, user_id)


async def _send_private(platform: Any, response: str, user_id: str) -> None:
    import inspect
    if hasattr(platform, "send_private_message"):
        result = platform.send_private_message(user_id, response)
        if inspect.isawaitable(result):
            await result
