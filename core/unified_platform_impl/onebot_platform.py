"""
OneBot / NapCat 平台适配器

基于 OneBot v11 反向 WebSocket 协议。
支持 QQ (NapCat、LLOneBot、Lagrange 等)。
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Dict, Any, Optional

from core.unified_platform.base import BasePlatform
from .message_mixin import MessageMixin

logger = logging.getLogger("Miya.Platform.OneBot")


class OneBotPlatform(MessageMixin, BasePlatform):
    """OneBot / NapCat 平台"""

    platform_id = "aiocqhttp"
    platform_name = "OneBot/NapCat"
    health_check_interval = 30.0
    auto_reconnect = False  # OneBot 监听循环自带重连，不触发系统级重连

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        BasePlatform.__init__(self, config)
        self._ws_url = self.config.get("ws_url", "ws://127.0.0.1:3001")
        self._bot_qq = self.config.get("bot_qq", "")
        self._ws: Optional[Any] = None
        self._connected = False
        self._pending_echoes: Dict[str, asyncio.Future] = {}
        self._loaded_config: dict = {}
        self._process_lock = asyncio.Lock()
        self._poke_cooldown: Dict[str, float] = {}  # user_id → last_poke_time
        self._hub_refs_set = False
        self._queue_initialized = False
        self._min_process_interval = 1.0
        self._last_process_time = 0.0
        # 群聊消息批处理缓冲: group_id → [messages]
        self._batch_buffers: Dict[str, list] = {}
        self._batch_timers: Dict[str, asyncio.Task] = {}

    @property
    def _config_data(self) -> dict:
        if not self._loaded_config:
            self._loaded_config = self._load_qq_config()
        return self._loaded_config

    def _load_qq_config(self) -> dict:
        """加载 qq_config.yaml 配置"""
        try:
            from pathlib import Path
            import yaml

            config_path = (
                Path(__file__).parent.parent.parent / "config" / "qq_config.yaml"
            )
            if config_path.exists():
                with open(config_path, "r", encoding="utf-8") as f:
                    full = yaml.safe_load(f) or {}
                    qq = full.get("qq", {})
                    return {
                        "superadmin_qq": str(
                            qq.get("connection", {}).get("superadmin_qq", "")
                        ),
                        "group_whitelist": qq.get("access_control", {}).get(
                            "group_whitelist", []
                        ),
                        "group_blacklist": qq.get("access_control", {}).get(
                            "group_blacklist", []
                        ),
                        "user_whitelist": qq.get("access_control", {}).get(
                            "user_whitelist", []
                        ),
                        "user_blacklist": qq.get("access_control", {}).get(
                            "user_blacklist", []
                        ),
                        "access_control_enabled": qq.get("access_control", {}).get(
                            "enabled", False
                        ),
                        "max_message_length": qq.get("commands", {}).get(
                            "qq_max_message_length", 200
                        ),
                        "image_analysis_enabled": qq.get("image_recognition", {})
                        .get("ai_analysis", {})
                        .get("enabled", True),
                        "image_analysis_timeout": qq.get("image_recognition", {})
                        .get("ai_analysis", {})
                        .get("timeout", 30),
                    }
        except Exception as e:
            logger.debug(f"[{self.platform_id}] 加载 qq_config.yaml 失败: {e}")
        return {}

    # ============ 决策中心引用登记 ============

    def _ensure_decision_hub_refs(self):
        """一次性设置决策中心引用 & 启动调度器 & 注册 M-Link 节点"""
        self._hub_refs_set = True
        try:
            miya = getattr(self, "_miya_core", None)
            if not miya or not hasattr(miya, "decision_hub"):
                return
            miya.decision_hub.onebot_client = self
            miya.decision_hub.qq_net = self
            logger.info(f"[{self.platform_id}] DecisionHub 引用已登记")
        except Exception as e:
            logger.debug(f"[{self.platform_id}] DecisionHub 引用登记失败: {e}")

        # 启动调度器（定时任务 / 主动聊天 / 时段问候）
        try:
            miya = getattr(self, "_miya_core", None)
            if miya and hasattr(miya, "scheduler") and miya.scheduler:
                from hub.scheduler import set_global_scheduler

                miya.scheduler.onebot_client = self
                set_global_scheduler(miya.scheduler)
                if not getattr(miya.scheduler, "_started", False):
                    miya.scheduler.start_background()
                    logger.info(f"[{self.platform_id}] 调度器已启动")
        except Exception as e:
            logger.debug(f"[{self.platform_id}] 调度器启动失败: {e}")

        # 注册 M-Link 节点
        try:
            miya = getattr(self, "_miya_core", None)
            if miya and hasattr(miya, "mlink") and miya.mlink:
                miya.mlink.register_node(
                    "onebot_platform",
                    [
                        "onebot_group_chat",
                        "onebot_private_chat",
                        "onebot_command",
                        "onebot_message_history",
                        "onebot_poke",
                        "onebot_multimedia",
                        "onebot_image_analysis",
                    ],
                )
                logger.info(f"[{self.platform_id}] M-Link 节点已注册")
        except Exception as e:
            logger.debug(f"[{self.platform_id}] M-Link 节点注册失败: {e}")

    # ============ 访问控制 ============

    def _is_group_allowed(self, group_id: str) -> bool:
        cfg = self._config_data
        if not cfg.get("access_control_enabled", False):
            return True
        try:
            gid = int(group_id)
        except ValueError:
            return True
        blacklist = cfg.get("group_blacklist", [])
        if gid in blacklist:
            logger.debug(f"[{self.platform_id}] 群黑名单拦截: {gid}")
            return False
        whitelist = cfg.get("group_whitelist", [])
        if whitelist:
            return gid in whitelist
        return True

    def _is_user_allowed(self, user_id: str) -> bool:
        cfg = self._config_data
        if not cfg.get("access_control_enabled", False):
            return True
        try:
            uid = int(user_id)
        except ValueError:
            return True
        blacklist = cfg.get("user_blacklist", [])
        if uid in blacklist:
            logger.debug(f"[{self.platform_id}] 用户黑名单拦截: {uid}")
            return False
        whitelist = cfg.get("user_whitelist", [])
        if whitelist:
            return uid in whitelist
        return True

    # ============ @ 检测 ============

    def _is_at_bot(self, message, bot_qq: str) -> bool:
        if isinstance(message, str):
            return f"@{bot_qq}" in message
        for seg in message:
            if isinstance(seg, dict) and seg.get("type") == "at":
                at_qq = str(seg.get("data", {}).get("qq", ""))
                if at_qq == bot_qq:
                    return True
        return False

    def _extract_at_list(self, message) -> list:
        at_list = []
        if isinstance(message, str):
            return at_list
        for seg in message:
            if isinstance(seg, dict) and seg.get("type") == "at":
                at_qq = seg.get("data", {}).get("qq")
                if at_qq:
                    try:
                        at_list.append(int(at_qq))
                    except (ValueError, TypeError):
                        pass
        return at_list

    # ============ 消息拆分 ============

    def _split_message(self, text: str, max_len: int = 200) -> list:
        """按句子边界拆分长消息"""
        if len(text) <= max_len:
            return [text]
        chunks = []
        remaining = text
        while remaining:
            if len(remaining) <= max_len:
                chunks.append(remaining)
                break
            # 在 max_len 范围内找最佳断点（优先段落 → 换行 → 句号 → 空格）
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

    # ============ 群名解析 ============

    async def _resolve_group_name(self, group_id: str) -> str:
        try:
            info = await self._call_onebot_api(
                "get_group_info", {"group_id": int(group_id)}
            )
            if isinstance(info, dict):
                return info.get("group_name", "")
        except Exception:
            pass
        return ""

    # ============ 全局记忆持久化 ============

    async def _persist_to_global_memory(
        self,
        msg_type: str,
        chat_id: str,
        sender_id: str,
        text: str,
        sender_name: str,
        group_name: str,
    ):
        try:
            miya = getattr(self, "_miya_core", None)
            if not miya or not hasattr(miya, "memory_net"):
                return
            memory_net = miya.memory_net
            session_id = f"{msg_type}_{chat_id}" if chat_id else f"private_{sender_id}"
            await memory_net.conversation_history.add_message(
                session_id=session_id,
                role="user",
                content=text,
                agent_id="miya_default",
                metadata={
                    "source": self.platform_id,
                    "msg_type": msg_type,
                    "sender_id": sender_id,
                    "sender_name": sender_name,
                    "group_name": group_name,
                },
            )
        except Exception:
            pass

    # ============ 输出过滤 ============

    def _filter_thinking(self, text: str) -> str:
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

    def _filter_output(self, text: str) -> str:
        """感叹号刷屏过滤"""
        try:
            import json
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
                    import random

                    logger.info(
                        f"[{self.platform_id}] 刷屏过滤: {count}个感叹号 → 替换"
                    )
                    return random.choice(fallbacks)
        except Exception:
            pass
        return text

    # ============ 离别检测 ============

    async def _detect_farewell(self, content: str, user_id: str):
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

    # ============ LifeBook 记录 ============

    async def _record_lifebook(self, user_msg: str, response: str):
        try:
            miya = getattr(self, "_miya_core", None)
            if not miya or not hasattr(miya, "decision_hub"):
                return
            from memory.lifebook import get_lifebook

            lifebook = get_lifebook()
            await lifebook.record_interaction(
                user_message=user_msg,
                lover_response=response,
                topics=[],
                emotion="平静",
            )
        except Exception:
            pass

    async def _do_connect(self) -> bool:
        try:
            import aiohttp

            # 如果已有后台任务在运行，不重复创建
            existing_tasks = [t for t in self._tasks if not t.done()]
            if existing_tasks:
                self._connected = True
                return True

            self._ws = None
            self._connected = True  # 乐观标记，实际连接由后台任务管理

            async def listen_loop():
                retry_delay = 1
                while self._connected is not False:
                    try:
                        async with aiohttp.ClientSession() as session:
                            async with session.ws_connect(self._ws_url) as ws:
                                self._ws = ws
                                self._connected = True
                                logger.info(
                                    f"[{self.platform_id}] 已连接到 {self._ws_url}"
                                )
                                retry_delay = 1

                                async for msg in ws:
                                    if msg.type == aiohttp.WSMsgType.TEXT:
                                        data = json.loads(msg.data)
                                        # 处理 echo 响应
                                        echo = data.get("echo")
                                        if echo and echo in self._pending_echoes:
                                            self._pending_echoes.pop(echo).set_result(
                                                data
                                            )
                                            continue
                                        await self._handle_onebot_message(data)
                                    elif msg.type == aiohttp.WSMsgType.ERROR:
                                        logger.error(
                                            f"[{self.platform_id}] WebSocket 错误"
                                        )
                                        break

                    except Exception as e:
                        logger.warning(
                            f"[{self.platform_id}] 连接断开: {e}, {retry_delay}s 后重连"
                        )
                        self._connected = False
                        self._ws = None
                        await asyncio.sleep(retry_delay)
                        retry_delay = min(retry_delay * 2, 30)

            self._tasks.append(asyncio.create_task(listen_loop()))
            await asyncio.sleep(0.5)
            return True

        except ImportError:
            logger.error(f"[{self.platform_id}] 请安装 aiohttp")
            return False
        except Exception as e:
            logger.error(f"[{self.platform_id}] 连接异常: {e}", exc_info=True)
            return False

    async def _handle_onebot_message(self, data: Dict):
        """处理 OneBot 消息"""
        try:
            post_type = data.get("post_type", "")
            if post_type == "message":
                await self._handle_chat_message(data)
            elif post_type == "notice":
                await self._handle_notice(data)
            elif post_type == "request":
                logger.debug(f"[{self.platform_id}] 请求: {data.get('request_type')}")
        except Exception as e:
            logger.error(f"[{self.platform_id}] 消息处理异常: {e}")

    async def _handle_notice(self, data: Dict):
        """处理通知事件（拍一拍等）"""
        notice_type = data.get("notice_type", "")
        if notice_type == "notify":
            sub_type = data.get("sub_type", "")
            if sub_type == "poke":
                target_id = str(data.get("target_id", ""))
                user_id = str(data.get("user_id", ""))
                self_id = str(data.get("self_id", ""))
                group_id = str(data.get("group_id", "")) if data.get("group_id") else ""

                bot_qq = self.config.get("bot_qq", "") or self_id
                is_bot_poked = str(target_id) == str(bot_qq) or str(target_id) == str(
                    self_id
                )

                logger.info(
                    f"[{self.platform_id}] 拍一拍: target={target_id}, bot_qq={bot_qq}, is_bot={is_bot_poked}"
                )

                if is_bot_poked:
                    # 拍一拍冷却 (15s)
                    now = asyncio.get_event_loop().time()
                    last = self._poke_cooldown.get(user_id, 0)
                    if now - last < 15:
                        logger.debug(f"[{self.platform_id}] 拍一拍冷却: {user_id}")
                        return
                    self._poke_cooldown[user_id] = now

                    # 第一层：瞬间回复固定文字 + 随机表情包
                    from core.config_loader import load_text_config

                    poke_text = (
                        load_text_config()
                        .get("poke_responses", {})
                        .get("local_emoji", "")
                    )
                    await self._send_onebot_poke_reply(user_id, group_id, poke_text)

                    # 第二层：异步走 AI 生成情感回复
                    content = f"[拍一拍] 用户 {user_id} 拍了拍你"
                    ai_response = await self.route_to_decision_hub(
                        content=content,
                        user_id=user_id,
                        user_name=user_id,
                        message_type="private" if not group_id else "group",
                        group_id=group_id,
                    )
                    if ai_response and self._ws and self._connected:
                        action = "send_group_msg" if group_id else "send_private_msg"
                        target = "group_id" if group_id else "user_id"
                        target_val = int(group_id) if group_id else int(user_id)
                        await self._ws.send_str(
                            json.dumps(
                                {
                                    "action": action,
                                    "params": {
                                        target: target_val,
                                        "message": [
                                            {
                                                "type": "text",
                                                "data": {"text": ai_response},
                                            }
                                        ],
                                    },
                                }
                            )
                        )
            else:
                logger.info(f"[{self.platform_id}] notify: {sub_type}")
        elif notice_type in ("group_increase", "group_decrease"):
            logger.info(f"[{self.platform_id}] 群变动: {notice_type}")
        else:
            logger.info(f"[{self.platform_id}] 通知: {notice_type}")

    async def _send_onebot_poke_reply(self, user_id: str, group_id: str, text: str):
        """拍一拍回复：文字 + data/emoji 随机图"""
        import random
        from pathlib import Path

        is_group = bool(group_id)
        action = "send_group_msg" if is_group else "send_private_msg"
        target = "group_id" if is_group else "user_id"
        target_val = int(group_id) if is_group else int(user_id)

        logger.info(f"[{self.platform_id}] 发送拍一拍回复: {text[:30]}...")
        await self._ws.send_str(
            json.dumps(
                {
                    "action": action,
                    "params": {
                        target: target_val,
                        "message": [{"type": "text", "data": {"text": text}}],
                    },
                }
            )
        )
        try:
            emoji_dir = Path(__file__).parent.parent.parent / "data" / "emoji"
            images = (
                [
                    p
                    for ext in ("*.png", "*.jpg", "*.jpeg", "*.gif")
                    for p in emoji_dir.rglob(ext)
                ]
                if emoji_dir.exists()
                else []
            )
            if images:
                img = str(random.choice(images).absolute())
                logger.info(f"[{self.platform_id}] 发送随机表情: {img[-30:]}")
                await self._ws.send_str(
                    json.dumps(
                        {
                            "action": action,
                            "params": {
                                target: target_val,
                                "message": [{"type": "image", "data": {"file": img}}],
                            },
                        }
                    )
                )
        except Exception as e:
            logger.warning(f"[{self.platform_id}] emoji发送失败: {e}")

    async def _call_onebot_api(self, action: str, params: Dict) -> Optional[Dict]:
        """调用 OneBot API — 优先 WebSocket echo，失败回退 HTTP"""
        if not self._ws or not self._connected:
            return None
        echo = f"miya_{action}_{id(params)}"
        future: asyncio.Future = asyncio.get_event_loop().create_future()
        self._pending_echoes[echo] = future
        try:
            await self._ws.send_str(
                json.dumps(
                    {
                        "action": action,
                        "params": params,
                        "echo": echo,
                    }
                )
            )
            result = await asyncio.wait_for(future, timeout=3.0)
            if result and result.get("status") == "ok":
                return result.get("data")
        except (asyncio.TimeoutError, Exception):
            pass
        finally:
            self._pending_echoes.pop(echo, None)

        # WS 失败，回退 HTTP API (NapCat 默认 port 3000)
        try:
            import aiohttp

            http_url = f"http://127.0.0.1:3000/{action}"
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    http_url, json=params, timeout=aiohttp.ClientTimeout(total=3)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if data.get("status") == "ok":
                            return data.get("data")
        except Exception:
            pass
        return None
        echo = f"miya_{action}_{id(params)}"
        future: asyncio.Future = asyncio.get_event_loop().create_future()
        self._pending_echoes[echo] = future
        try:
            await self._ws.send_str(
                json.dumps(
                    {
                        "action": action,
                        "params": params,
                        "echo": echo,
                    }
                )
            )
            result = await asyncio.wait_for(future, timeout=5.0)
            if not result or result.get("status") != "ok":
                logger.warning(
                    f"[{self.platform_id}] API 失败: {action}, response={result}"
                )
                self._pending_echoes.pop(echo, None)
                return None
            return result.get("data")
        except asyncio.TimeoutError:
            self._pending_echoes.pop(echo, None)
            return None
        except Exception:
            self._pending_echoes.pop(echo, None)
            return None

    async def _handle_chat_message(self, data: Dict):
        """处理聊天消息 (v2 — 完整功能迁移自 qq_main.py)"""
        import re as _re

        msg_type = data.get("message_type", "private")
        sender = data.get("sender", {})
        raw_message = data.get("raw_message", data.get("message", ""))

        # === 1. 基础信息 ===
        user_id = str(sender.get("user_id", ""))
        sender_card = sender.get("card", "")
        sender_nickname = sender.get("nickname", "")
        user_name = sender_card or sender_nickname or user_id
        group_id_str = str(data.get("group_id", ""))
        bot_qq = str(self.config.get("bot_qq") or data.get("self_id", "") or "")

        # === 2. 自身消息过滤 ===
        if user_id and bot_qq and str(user_id) == str(bot_qq):
            return

        # === 2.5. 决策中心引用登记（一次性） ===
        if not self._hub_refs_set:
            self._ensure_decision_hub_refs()

        # === 3. 群聊 / 用户黑白名单 ===
        if group_id_str and not self._is_group_allowed(group_id_str):
            return
        if not self._is_user_allowed(user_id):
            return

        # === 4. 发送者角色 ===
        sender_role = sender.get("role", "member")
        sender_title = sender.get("title", "")

        # === 5. @检测 + at列表 ===
        is_at_bot = self._is_at_bot(raw_message, bot_qq) if bot_qq else True
        at_list = self._extract_at_list(raw_message)

        # === 6. 消息段解析（text / reply / image / file / face） ===
        reply_id = ""
        image_segments = []
        file_segments = []
        face_only = False
        content = ""

        if isinstance(raw_message, list):
            face_seg_count = 0
            for p in raw_message:
                seg_type = p.get("type", "")
                seg_data = p.get("data", {})
                if seg_type == "text":
                    content += seg_data.get("text", "")
                elif seg_type == "reply":
                    reply_id = str(seg_data.get("id", ""))
                elif seg_type == "image":
                    image_segments.append(p)
                elif seg_type == "file":
                    file_segments.append(
                        {
                            "file_id": seg_data.get("id", seg_data.get("file", "")),
                            "name": seg_data.get("name", ""),
                            "size": seg_data.get("size", 0),
                            "file_type": seg_data.get("type", ""),
                        }
                    )
                elif seg_type == "face":
                    face_seg_count += 1
                elif seg_type == "video":
                    image_segments.append(p)  # 视频同图片处理
            # 是否纯表情消息
            non_face = [p for p in raw_message if p.get("type") != "face"]
            face_only = face_seg_count > 0 and not non_face
        else:
            content = str(raw_message)
            reply_match = _re.search(r"\[CQ:reply,id=(\d+)\]", content)
            if reply_match:
                reply_id = reply_match.group(1)
            # 从 CQ 字符串提取图片
            if "[CQ:image" in content:
                cq_images = _re.findall(r"\[CQ:image,file=([^,\]]+)", content)
                for fid in cq_images:
                    image_segments.append({"type": "image", "data": {"file": fid}})
            content = _re.sub(r"\[CQ:[^\]]+\]", "", content).strip()

        content = content.strip()

        # === 7. 超级管理员检测 ===
        is_owner = False
        try:
            from core.unified_permission import get_permission_engine

            is_owner = get_permission_engine().is_superadmin(
                user_id, platform=self.platform_id
            )
        except Exception:
            pass

        # === 8. 图片 / 表情预过滤（纯图片且非@非超管的群消息跳过） ===
        has_direct_images = bool(image_segments)
        if (
            msg_type == "group"
            and not is_at_bot
            and not is_owner
            and has_direct_images
            and (not content or content in ("[图片]", "[动画表情]", ""))
        ):
            logger.debug(
                f"[{self.platform_id}] 预过滤纯图片群消息: group={group_id_str}"
            )
            return
        if (
            msg_type == "group"
            and not is_at_bot
            and not is_owner
            and face_only
            and not content
        ):
            logger.debug(
                f"[{self.platform_id}] 预过滤纯表情群消息: group={group_id_str}"
            )
            return

        # === 9. 直接图片 AI 视觉分析 ===
        extra = {}
        has_media = has_direct_images

        if has_direct_images and not reply_id:
            # 直接发送的图片（非引用）→ 下载 + 视觉分析
            for seg in image_segments[:2]:
                img_data = seg.get("data", {})
                image_bytes = await self._download_reference_image(img_data)
                if not image_bytes:
                    continue
                asyncio.ensure_future(
                    self._auto_save_image_bytes(image_bytes, user_id, img_data)
                )
                try:
                    from core.multi_vision_analyzer import get_vision_analyzer

                    analyzer = await get_vision_analyzer()
                    result = await analyzer.analyze_image(image_bytes)
                    if result.success:
                        extra["image_analysis"] = {
                            "success": True,
                            "description": result.description,
                            "labels": result.labels,
                            "model": result.model_used,
                            "provider": result.provider,
                            "nsfw_score": result.nsfw_score,
                            "has_text": result.has_text,
                            "text": result.text,
                            "confidence": result.confidence,
                            "processing_time_ms": result.processing_time_ms,
                        }
                        extra["has_image"] = True
                        extra["has_media"] = True
                        has_media = True
                        if not content:
                            content = f"[图片: {result.description[:100]}]"
                        break
                except Exception as e:
                    logger.debug(f"[{self.platform_id}] 直接图片分析失败: {e}")

        # === 10. 自动保存直接图片 ===
        if has_direct_images:
            asyncio.ensure_future(self._auto_save_images(image_segments, user_id))

        # === 11. 文件附件 ===
        if file_segments:
            extra["files"] = file_segments
            has_media = True

        if not content and not has_media and not reply_id:
            return

        # === 12. 引用消息处理（文本 / 图片视觉分析） ===
        if reply_id:
            logger.info(f"[{self.platform_id}] 尝试获取引用: id={reply_id}")
            reply_data = await self._call_onebot_api(
                "get_msg", {"message_id": int(reply_id)}
            )
            if reply_data:
                logger.info(
                    f"[{self.platform_id}] 引用获取成功: {str(reply_data)[:80]}"
                )
                reply_sender = reply_data.get("sender", {}).get("nickname", "")
                reply_raw = reply_data.get("message", "")
                # 调试日志
                logger.debug(
                    f"[{self.platform_id}] reply_raw type={type(reply_raw).__name__}, "
                    f"len={len(reply_raw) if hasattr(reply_raw, '__len__') else 'N/A'}"
                )
                # reply_to_bot 检测
                reply_sender_id = str(reply_data.get("sender", {}).get("user_id", ""))
                extra["reply_to_bot"] = reply_sender_id == bot_qq
                # 提取引用文本
                reply_content = ""
                if isinstance(reply_raw, list):
                    reply_content = "".join(
                        s.get("data", {}).get("text", "")
                        for s in reply_raw
                        if s.get("type") == "text"
                    )
                else:
                    reply_content = _re.sub(
                        r"\[CQ:[^\]]+\]", "", str(reply_raw)
                    ).strip()
                if reply_content:
                    extra["reply_to_id"] = reply_id
                    extra["reply_content"] = reply_content
                    content = f'[回复"{reply_content}"] {content}'
                elif isinstance(reply_raw, list) and any(
                    s.get("type") in ("image", "video") for s in reply_raw
                ):
                    reply_image_segs = [
                        s for s in reply_raw if s.get("type") in ("image", "video")
                    ]
                    analyzed = False
                    for seg in reply_image_segs[:2]:
                        img_data = seg.get("data", {})
                        image_bytes = await self._download_reference_image(img_data)
                        if not image_bytes:
                            continue
                        asyncio.ensure_future(
                            self._auto_save_image_bytes(image_bytes, user_id, img_data)
                        )
                        try:
                            from core.multi_vision_analyzer import (
                                get_vision_analyzer,
                            )

                            analyzer = await get_vision_analyzer()
                            result = await analyzer.analyze_image(image_bytes)
                            if result.success:
                                extra["image_analysis"] = {
                                    "success": True,
                                    "description": result.description,
                                    "labels": result.labels,
                                    "model": result.model_used,
                                    "provider": result.provider,
                                    "nsfw_score": result.nsfw_score,
                                    "has_text": result.has_text,
                                    "text": result.text,
                                    "confidence": result.confidence,
                                    "processing_time_ms": result.processing_time_ms,
                                }
                                extra["has_image"] = True
                                has_media = True
                                desc = result.description or f"图片({result.format})"
                                content = f"[回复图片: {desc[:100]}] {content}"
                                analyzed = True
                                logger.info(
                                    f"[{self.platform_id}] 引用图片分析完成: {desc[:50]}..."
                                )
                                break
                        except Exception as e:
                            logger.warning(
                                f"[{self.platform_id}] 引用图片视觉分析失败: {e}"
                            )
                    if not analyzed:
                        content = f"[回复图片] {content}"
                elif "[CQ:image" in str(reply_raw):
                    # 字符串格式的引用图片 — 也尝试下载分析
                    cq_files = _re.findall(r"\[CQ:image,file=([^,\]]+)", str(reply_raw))
                    analyzed_str = False
                    for fid in cq_files[:2]:
                        image_bytes = await self._download_reference_image(
                            {"file": fid}
                        )
                        if not image_bytes:
                            continue
                        asyncio.ensure_future(
                            self._auto_save_image_bytes(
                                image_bytes, user_id, {"file": fid}
                            )
                        )
                        try:
                            from core.multi_vision_analyzer import (
                                get_vision_analyzer,
                            )

                            analyzer = await get_vision_analyzer()
                            result = await analyzer.analyze_image(image_bytes)
                            if result.success:
                                extra["image_analysis"] = {
                                    "success": True,
                                    "description": result.description,
                                    "labels": result.labels,
                                    "model": result.model_used,
                                    "provider": result.provider,
                                    "nsfw_score": result.nsfw_score,
                                    "has_text": result.has_text,
                                    "text": result.text,
                                    "confidence": result.confidence,
                                    "processing_time_ms": result.processing_time_ms,
                                }
                                extra["has_image"] = True
                                has_media = True
                                desc = result.description or f"图片({result.format})"
                                content = f"[回复图片: {desc[:100]}] {content}"
                                analyzed_str = True
                                logger.info(
                                    f"[{self.platform_id}] 引用图片(CQ)分析完成: {desc[:50]}..."
                                )
                                break
                        except Exception as e:
                            logger.warning(
                                f"[{self.platform_id}] 引用图片(CQ)视觉分析失败: {e}"
                            )
                    if not analyzed_str:
                        content = f"[回复图片] {content}"
            else:
                logger.warning(f"[{self.platform_id}] 引用获取失败: id={reply_id}")

        if not content and not has_media:
            return

        # === 13. 群名解析 ===
        group_name = ""
        if group_id_str and msg_type == "group":
            group_name = await self._resolve_group_name(group_id_str)

        # === 13. 谛听旁观监听（decision_hub 已内置，此层不重复调用，
        # 仅传递必要的元数据给 route_to_decision_hub）===

        # === 15. 全局记忆持久化 ===
        asyncio.ensure_future(
            self._persist_to_global_memory(
                msg_type, group_id_str, user_id, content, user_name, group_name
            )
        )

        if has_media:
            extra["has_media"] = True

        logger.debug(
            f"[{self.platform_id}] 收到消息: {content[:50]}, reply_id={reply_id}, is_at={is_at_bot}"
        )

        # === 16. 路由到决策中心（加锁防并发） ===
        async with self._process_lock:
            response = await self.route_to_decision_hub(
                content=content,
                user_id=user_id,
                user_name=user_name,
                message_type=msg_type,
                group_id=group_id_str,
                group_name=group_name,
                sender_role=sender_role,
                is_at_bot=is_at_bot,
                extra=extra,
            )

        if response:
            # === 17. 响应后处理 ===
            response = self._filter_thinking(response)
            response = self._filter_output(response)

            # 离别检测
            asyncio.ensure_future(self._detect_farewell(content, user_id))

            # LifeBook 记录
            asyncio.ensure_future(self._record_lifebook(content, response))

            await self._send_onebot_reply(data, response)
        elif has_media and not is_at_bot:
            # 群聊非@图片：AI 不回复，只做存储
            pass

    async def _send_onebot_reply(self, original: Dict, text: str):
        """发送 OneBot 回复（自动拆分长消息）"""
        if not self._ws or not self._connected:
            return

        max_len = self._config_data.get("max_message_length", 200)
        msg_type = original.get("message_type", "private")

        for chunk in self._split_message(text, max_len):
            reply_data = {
                "action": "send_msg",
                "params": {
                    "message_type": msg_type,
                    "message": chunk,
                },
            }
            if msg_type == "private":
                reply_data["params"]["user_id"] = original.get("sender", {}).get(
                    "user_id"
                )
            elif msg_type == "group":
                reply_data["params"]["group_id"] = original.get("group_id")
                reply_data["params"]["message"] = chunk
            try:
                await self._ws.send_str(json.dumps(reply_data))
                if len(chunk) < len(text):
                    await asyncio.sleep(0.3)  # 分段间短暂间隔
            except Exception as e:
                logger.error(f"[{self.platform_id}] 发送回复异常: {e}")
                break

    # ============ OneBot API 辅助 ============

    async def send_like(self, user_id: int, times: int = 1):
        """给用户点赞"""
        await self._call_onebot_api("send_like", {"user_id": user_id, "times": times})

    async def send_poke(self, user_id: int, group_id: int = 0):
        """拍一拍用户"""
        if group_id:
            await self._call_onebot_api(
                "group_poke", {"group_id": group_id, "user_id": user_id}
            )
        else:
            await self._call_onebot_api("friend_poke", {"user_id": user_id})

    async def upload_image(self, file_path: str) -> Optional[str]:
        """上传图片到 OneBot，返回 file_id"""
        import os as _os

        if not _os.path.exists(file_path):
            logger.warning(f"[{self.platform_id}] 图片文件不存在: {file_path}")
            return None
        result = await self._call_onebot_api(
            "upload_image",
            {"file": f"file:///{file_path.replace(_os.sep, '/')}"},
        )
        if isinstance(result, dict):
            return result.get("file_id") or result.get("file")
        return None

    async def send_image(
        self, file_path: str, msg_type: str = "private", target_id: int = 0
    ):
        """发送图片：自动上传 + 发送"""
        file_id = await self.upload_image(file_path)
        if not file_id:
            return
        cq = f"[CQ:image,file={file_id}]"
        if self._ws and self._connected:
            params = {"message_type": msg_type, "message": cq}
            if msg_type == "private":
                params["user_id"] = target_id
            else:
                params["group_id"] = target_id
            await self._ws.send_str(
                json.dumps({"action": "send_msg", "params": params})
            )

    @staticmethod
    def cq_at(qq: int) -> str:
        return f"[CQ:at,qq={qq}]"

    @staticmethod
    def cq_image(file: str) -> str:
        return f"[CQ:image,file={file}]"

    @staticmethod
    def cq_face(face_id: int) -> str:
        return f"[CQ:face,id={face_id}]"

    # ============ 扩展 OneBot API ============

    async def get_group_info(self, group_id: int) -> Optional[dict]:
        return await self._call_onebot_api("get_group_info", {"group_id": group_id})

    async def get_group_list(self) -> Optional[list]:
        result = await self._call_onebot_api("get_group_list", {})
        return result if isinstance(result, list) else None

    async def get_group_member_list(self, group_id: int) -> Optional[list]:
        result = await self._call_onebot_api(
            "get_group_member_list", {"group_id": group_id}
        )
        return result if isinstance(result, list) else None

    async def get_group_member_info(
        self, group_id: int, user_id: int, no_cache: bool = False
    ) -> Optional[dict]:
        return await self._call_onebot_api(
            "get_group_member_info",
            {"group_id": group_id, "user_id": user_id, "no_cache": no_cache},
        )

    async def get_friend_list(self) -> Optional[list]:
        result = await self._call_onebot_api("get_friend_list", {})
        return result if isinstance(result, list) else None

    async def get_stranger_info(
        self, user_id: int, no_cache: bool = False
    ) -> Optional[dict]:
        return await self._call_onebot_api(
            "get_stranger_info", {"user_id": user_id, "no_cache": no_cache}
        )

    async def get_group_msg_history(
        self, group_id: int, message_seq: int = 0, count: int = 20
    ) -> Optional[dict]:
        return await self._call_onebot_api(
            "get_group_msg_history",
            {"group_id": group_id, "message_seq": message_seq, "count": count},
        )

    async def get_msg(self, message_id: int) -> Optional[dict]:
        return await self._call_onebot_api("get_msg", {"message_id": message_id})

    async def get_forward_msg(self, forward_id: str) -> Optional[dict]:
        return await self._call_onebot_api("get_forward_msg", {"id": forward_id})

    async def send_face_message(
        self, face_id: int, msg_type: str = "private", target_id: int = 0
    ):
        """发送 QQ 内置表情"""
        cq = self.cq_face(face_id)
        if self._ws and self._connected:
            params = {"message_type": msg_type, "message": cq}
            if msg_type == "private":
                params["user_id"] = target_id
            else:
                params["group_id"] = target_id
            await self._ws.send_str(
                json.dumps({"action": "send_msg", "params": params})
            )

    def _find_named_emoji(self, name: str) -> Optional[Path]:
        """在本地表情包仓库中按名称查找"""
        from pathlib import Path as _Path

        emoji_dirs = ["data/emoji", "data"]
        name_lower = name.lower()
        for d in emoji_dirs:
            root = _Path(d)
            if not root.exists():
                continue
            for img_file in root.rglob("*"):
                if not img_file.suffix.lower() in (
                    ".gif",
                    ".jpg",
                    ".jpeg",
                    ".png",
                    ".webp",
                    ".bmp",
                ):
                    continue
                stem = img_file.stem.lower()
                # 忽略 tmp 前缀的自动保存文件
                if stem.startswith("tmp"):
                    continue
                if name_lower in stem or stem in name_lower:
                    return img_file
        return None

    async def _download_reference_image(self, image_data: dict) -> Optional[bytes]:
        """下载引用消息中的图片

        OneBot 图片消息段: {"type": "image", "data": {"url": "...", "file": "..."}}
        优先 OneBot get_image API（返回 base64），失败回退直接 HTTP 下载 url
        """
        import base64 as _base64

        file_id = image_data.get("file", "")
        url = image_data.get("url", "")

        # 方案1: 通过 OneBot API get_image（最可靠，返回 base64 编码的文件）
        if file_id:
            result = await self._call_onebot_api("get_image", {"file": file_id})
            if isinstance(result, dict):
                b64 = result.get("file") or result.get("data")
                if b64:
                    try:
                        raw = _base64.b64decode(b64)
                        if len(raw) > 1024:  # 至少 1KB 才算是有效图片
                            logger.debug(
                                f"[{self.platform_id}] OneBot get_image 成功: {len(raw) / 1024:.1f}KB"
                            )
                            return raw
                    except Exception as e:
                        logger.debug(f"[{self.platform_id}] base64 解码失败: {e}")

        # 方案2: 直接 HTTP 下载 url（QQ 内部 url 可能过期或需要特定 header）
        if url:
            try:
                import aiohttp

                headers = {
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                    ),
                    "Referer": "https://qun.qq.com/",
                }
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        url,
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=15),
                    ) as resp:
                        if resp.status == 200:
                            raw = await resp.read()
                            if len(raw) > 1024:
                                logger.debug(
                                    f"[{self.platform_id}] HTTP 下载成功(url): {len(raw) / 1024:.1f}KB"
                                )
                                return raw
                            else:
                                logger.debug(
                                    f"[{self.platform_id}] HTTP 下载数据过小: {len(raw)}B"
                                )
            except Exception as e:
                logger.debug(f"[{self.platform_id}] 直接下载图片失败(url): {e}")

        logger.debug(
            f"[{self.platform_id}] 图片下载失败: file={file_id[:30] if file_id else '-'}"
        )
        return None

    async def _auto_save_images(self, image_segments: list, user_id: str):
        """自动保存消息中的图片到表情包仓库（消息段格式）"""
        for seg in image_segments[:3]:  # 单条消息最多保存3张
            img_data = seg.get("data", {})
            image_bytes = await self._download_reference_image(img_data)
            if image_bytes:
                try:
                    from utils.auto_emoji_saver import get_auto_emoji_saver

                    saver = get_auto_emoji_saver()
                    await saver.auto_save_emoji(
                        int(user_id), image_bytes, image_info=img_data
                    )
                except Exception as e:
                    logger.debug(f"[{self.platform_id}] 自动保存图片失败: {e}")

    async def _auto_save_string_images(self, raw_message: str, user_id: str):
        """自动保存 CQ 字符串格式消息中的图片"""
        import re as _re

        cq_images = _re.findall(r"\[CQ:image,file=([^,\]]+)", raw_message)
        for file_id in cq_images[:3]:
            image_bytes = await self._download_reference_image({"file": file_id})
            if image_bytes:
                try:
                    from utils.auto_emoji_saver import get_auto_emoji_saver

                    saver = get_auto_emoji_saver()
                    await saver.auto_save_emoji(
                        int(user_id),
                        image_bytes,
                        image_info={"file_name": file_id},
                    )
                except Exception as e:
                    logger.debug(f"[{self.platform_id}] 自动保存图片失败(CQ): {e}")

    async def _auto_save_image_bytes(
        self, image_bytes: bytes, user_id: str, image_info: Optional[Dict] = None
    ):
        """保存已下载的图片字节到表情包仓库"""
        try:
            from utils.auto_emoji_saver import get_auto_emoji_saver

            saver = get_auto_emoji_saver()
            await saver.auto_save_emoji(
                int(user_id), image_bytes, image_info=image_info
            )
        except Exception as e:
            logger.debug(f"[{self.platform_id}] 自动保存图片失败(bytes): {e}")

    async def _do_disconnect(self):
        self._connected = False
        if self._ws:
            try:
                await self._ws.close()
            except Exception:
                pass
        self._ws = None

    async def _do_health_check(self) -> bool:
        return self._connected and self._ws is not None
