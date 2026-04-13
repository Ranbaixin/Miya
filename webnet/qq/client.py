"""
QQ交互子网 - OneBot WebSocket客户端
从原 qq.py 中拆分出来的客户端逻辑
"""

import asyncio
import json
import logging
import os
import aiohttp
import mimetypes
from typing import Any, Callable, Dict, List, Optional, Set

import websockets
from mlink.message import Message, MessageType
from core.constants import NetworkTimeout

from .models import QQMessage

logger = logging.getLogger(__name__)


class QQOneBotClient:
    """OneBot WebSocket客户端 - 完全吸收Undefined的实现"""

    def __init__(self, ws_url: str, token: str = ""):
        self.ws_url = ws_url
        self.token = token
        self.ws: Optional[websockets.asyncio.client.ClientConnection] = None
        self._message_id = 0
        self._pending_responses: Dict[str, asyncio.Future] = {}
        self._message_handler: Optional[Callable] = None
        self._running = False
        self._tasks: set = set()

    def set_message_handler(self, handler: Callable) -> None:
        """设置消息处理器"""
        self._message_handler = handler

    def connection_status(self) -> Dict[str, Any]:
        """返回连接状态"""
        return {
            "connected": bool(self.ws) and self._running,
            "running": self._running,
            "ws_url": self.ws_url,
        }

    async def connect(self) -> None:
        """连接到OneBot WebSocket"""
        url = self.ws_url
        if self.token:
            separator = "&" if "?" in url else "?"
            url = f"{url}{separator}access_token={self.token}"

        extra_headers = {}
        if self.token:
            extra_headers["Authorization"] = f"Bearer {self.token}"

        logger.info("正在建立WebSocket连接...")
        logger.info(f"  地址: {self.ws_url}")
        logger.info(f"  Token: {'已配置' if self.token else '未配置'}")
        logger.info(f"  超时: {NetworkTimeout.WEBSOCKET_PING_TIMEOUT}秒")

        try:
            self.ws = await websockets.connect(
                url,
                ping_interval=20,
                ping_timeout=NetworkTimeout.WEBSOCKET_PING_TIMEOUT,
                max_size=100 * 1024 * 1024,
                additional_headers=extra_headers if extra_headers else None,
            )
            logger.info("WebSocket连接已建立")
            logger.info("")

        except Exception as e:
            logger.error(f"WebSocket连接失败: {e}")
            raise

    async def disconnect(self) -> None:
        """断开连接"""
        self._running = False
        if self.ws:
            await self.ws.close()
            self.ws = None
            logger.info("[🔌] WebSocket连接已断开")

    async def _call_api(
        self,
        action: str,
        params: Optional[Dict] = None,
        *,
        suppress_error_retcodes: Optional[set] = None,
    ) -> Dict[str, Any]:
        """调用OneBot API"""
        if not self.ws:
            raise RuntimeError("WebSocket未连接")

        self._message_id += 1
        echo = str(self._message_id)

        request = {
            "action": action,
            "params": params or {},
            "echo": echo,
        }

        future = asyncio.Future()
        self._pending_responses[echo] = future

        try:
            await self.ws.send(json.dumps(request))
            response = await asyncio.wait_for(future, timeout=480.0)

            status = response.get("status")
            if status == "failed":
                retcode = response.get("retcode", -1)
                msg = response.get("message", "未知错误")
                if suppress_error_retcodes and retcode in suppress_error_retcodes:
                    logger.warning(f"[QQ] API预期失败: {action} retcode={retcode}")
                else:
                    logger.error(f"[QQ] API失败: {action} retcode={retcode} msg={msg}")
                    raise RuntimeError(f"API调用失败: {msg} (retcode={retcode})")

            return response
        except asyncio.TimeoutError:
            logger.error(f"[QQ] API超时: {action}")
            raise
        finally:
            self._pending_responses.pop(echo, None)

    async def send_group_message(
        self,
        group_id: int,
        message: str | List[Dict],
        *,
        auto_escape: bool = False,
    ) -> Dict[str, Any]:
        """发送群消息"""
        return await self._call_api(
            "send_group_msg",
            {
                "group_id": group_id,
                "message": message,
                "auto_escape": auto_escape,
            },
        )

    async def send_private_message(
        self,
        user_id: int,
        message: str | List[Dict],
        *,
        auto_escape: bool = False,
    ) -> Dict[str, Any]:
        """发送私聊消息"""
        return await self._call_api(
            "send_private_msg",
            {
                "user_id": user_id,
                "message": message,
                "auto_escape": auto_escape,
            },
        )

    async def get_group_msg_history(
        self,
        group_id: int,
        message_seq: Optional[int] = None,
        count: int = 500,
    ) -> List[Dict]:
        """获取群消息历史"""
        params: Dict = {
            "group_id": group_id,
            "count": count,
        }
        if message_seq is not None:
            params["message_seq"] = message_seq

        result = await self._call_api("get_group_msg_history", params)

        if not result:
            return []

        data = result.get("data", {})
        return data.get("messages", [])

    async def get_group_info(self, group_id: int) -> Optional[Dict]:
        """获取群信息"""
        try:
            result = await self._call_api("get_group_info", {"group_id": group_id})
            return result.get("data", {})
        except Exception as e:
            logger.error(f"[QQ] 获取群信息失败: {e}")
            return None

    async def get_stranger_info(
        self, user_id: int, no_cache: bool = False
    ) -> Optional[Dict]:
        """获取陌生人信息"""
        try:
            params = {"user_id": user_id}
            if no_cache:
                params["no_cache"] = no_cache
            result = await self._call_api("get_stranger_info", params)
            return result.get("data", {})
        except Exception as e:
            logger.error(f"[QQ] 获取用户信息失败: {e}")
            return None

    async def get_group_member_info(
        self, group_id: int, user_id: int, no_cache: bool = False
    ) -> Optional[Dict]:
        """获取群成员信息"""
        try:
            result = await self._call_api(
                "get_group_member_info",
                {"group_id": group_id, "user_id": user_id, "no_cache": no_cache},
            )
            return result.get("data", {})
        except Exception as e:
            logger.error(f"[QQ] 获取群成员信息失败: {e}")
            return None

    async def get_group_member_list(self, group_id: int) -> List[Dict]:
        """获取群成员列表"""
        try:
            result = await self._call_api(
                "get_group_member_list", {"group_id": group_id}
            )
            return result.get("data", [])
        except Exception as e:
            logger.error(f"[QQ] 获取群成员列表失败: {e}")
            return []

    async def get_friend_list(self) -> List[Dict]:
        """获取好友列表"""
        try:
            result = await self._call_api("get_friend_list")
            return result.get("data", [])
        except Exception as e:
            logger.error(f"[QQ] 获取好友列表失败: {e}")
            return []

    async def get_group_list(self) -> List[Dict]:
        """获取群列表"""
        try:
            result = await self._call_api("get_group_list")
            return result.get("data", [])
        except Exception as e:
            logger.error(f"[QQ] 获取群列表失败: {e}")
            return []

    async def get_group_file_system_info(self, group_id: int) -> Optional[Dict]:
        """获取群文件系统信息"""
        try:
            result = await self._call_api(
                "get_group_file_system_info", {"group_id": group_id}
            )
            return result.get("data")
        except Exception as e:
            logger.error(f"[QQ] 获取群文件系统信息失败: {e}")
            return None

    async def get_group_root_files(self, group_id: int) -> Dict:
        """获取群根目录文件列表"""
        try:
            result = await self._call_api(
                "get_group_root_files", {"group_id": group_id}
            )
            return result.get("data", {})
        except Exception as e:
            logger.error(f"[QQ] 获取群文件列表失败: {e}")
            return {"files": [], "folders": []}

    async def get_group_files(self, group_id: int, folder_id: str) -> Dict:
        """获取群文件夹内的文件列表"""
        try:
            result = await self._call_api(
                "get_group_files", {"group_id": group_id, "folder_id": folder_id}
            )
            return result.get("data", {})
        except Exception as e:
            logger.error(f"[QQ] 获取群文件夹文件列表失败: {e}")
            return {"files": [], "folders": []}

    async def get_group_file_url(self, group_id: int, file_id: str) -> Optional[str]:
        """获取群文件下载链接"""
        try:
            result = await self._call_api(
                "get_group_file_url", {"group_id": group_id, "file_id": file_id}
            )
            data = result.get("data", {})
            return data.get("url")
        except Exception as e:
            logger.error(f"[QQ] 获取群文件下载链接失败: {e}")
            return None

    async def download_group_file(self, url: str, save_path: str) -> bool:
        """下载群文件到本地"""
        import aiohttp

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        with open(save_path, "wb") as f:
                            async for chunk in response.content.iter_chunked(8192):
                                f.write(chunk)
                        logger.info(f"[QQ] 群文件已下载: {save_path}")
                        return True
                    else:
                        logger.error(f"[QQ] 文件下载失败，状态码: {response.status}")
                        return False
        except Exception as e:
            logger.error(f"[QQ] 群文件下载失败: {e}")
            return False

    async def send_group_poke(self, group_id: int, user_id: int) -> Dict[str, Any]:
        """群聊拍一拍"""
        try:
            return await self._call_api(
                "group_poke", {"group_id": group_id, "user_id": user_id}
            )
        except RuntimeError:
            # 回退到 send_poke
            return await self._call_api(
                "send_poke",
                {"group_id": group_id, "user_id": user_id, "target_id": user_id},
            )

    async def send_private_poke(self, user_id: int) -> Dict[str, Any]:
        """私聊拍一拍"""
        try:
            return await self._call_api("friend_poke", {"user_id": user_id})
        except RuntimeError:
            # 回退到 send_poke
            return await self._call_api(
                "send_poke",
                {"user_id": user_id, "target_id": user_id},
            )

    async def send_like(self, user_id: int, times: int = 1) -> Dict[str, Any]:
        """发送好友点赞"""
        try:
            return await self._call_api(
                "send_like",
                {"user_id": user_id, "times": times},
            )
        except Exception as e:
            logger.error(f"[QQ] 点赞失败: {e}")
            raise

    async def download_image(self, url: str) -> Optional[bytes]:
        """下载图片 - 从URL下载图片数据"""
        try:
            import httpx

            # 直接从URL下载图片
            async with httpx.AsyncClient(follow_redirects=True) as client:
                response = await client.get(url, timeout=30.0)
                if response.status_code == 200:
                    logger.info(f"[QQ] 图片下载成功: {len(response.content)} bytes")
                    return response.content
                else:
                    logger.error(f"[QQ] 图片下载失败: HTTP {response.status_code}")
                    return None
        except Exception as e:
            logger.error(f"[QQ] 图片下载失败: {e}")
            return None

    async def get_msg(self, message_id: int) -> Optional[Dict]:
        """获取单条消息"""
        try:
            result = await self._call_api("get_msg", {"message_id": message_id})
            return result.get("data")
        except Exception as e:
            logger.error(f"[QQ] 获取消息失败: {e}")
            return None

    async def get_forward_msg(self, id: str) -> List[Dict]:
        """获取合并转发消息"""
        try:
            result = await self._call_api(
                "get_forward_msg",
                {"message_id": id},
                suppress_error_retcodes={1200},
            )
            data = result.get("data", {})
            if isinstance(data, dict):
                return data.get("messages", [])
            elif isinstance(data, list):
                return data
            return []
        except Exception as e:
            logger.error(f"[QQ] 获取转发消息失败: {e}")
            return []

    async def run(self) -> None:
        """运行消息接收循环"""
        if not self.ws:
            raise RuntimeError("WebSocket未连接")

        self._running = True
        logger.info("[🚀] 消息接收循环已启动")
        logger.info("[👂] 正在监听QQ消息...")

        try:
            while self._running:
                try:
                    message_data = await self.ws.recv()
                    if isinstance(message_data, bytes):
                        message_data = message_data.decode("utf-8")

                    data = json.loads(message_data)
                    await self._dispatch_message(data)
                except json.JSONDecodeError as e:
                    logger.error(f"JSON解析失败: {e}")
                except websockets.ConnectionClosed:
                    logger.warning("连接已关闭")
                    break
                except Exception as e:
                    logger.exception(f"接收消息异常: {e}")
        finally:
            self._running = False
            if self._tasks:
                await asyncio.gather(*self._tasks, return_exceptions=True)
            logger.info("[🛑] 消息接收循环已停止")

    async def _dispatch_message(self, data: Dict) -> None:
        """分发消息"""
        echo = data.get("echo")
        if echo is not None:
            echo_str = str(echo)
            if echo_str in self._pending_responses:
                self._pending_responses[echo_str].set_result(data)
            return

        post_type = data.get("post_type")
        if post_type == "message":
            msg_type = data.get("message_type", "unknown")
            sender_info = data.get("sender", {})
            sender_id = sender_info.get("user_id", "unknown")
            sender_name = sender_info.get("nickname", "unknown")

            # 获取原始消息内容用于日志
            raw_message = data.get("raw_message", "")
            if isinstance(raw_message, list):
                # 处理数组格式的消息
                msg_parts = []
                for seg in raw_message[:3]:  # 只取前3段
                    if seg.get("type") == "text":
                        msg_parts.append(seg.get("data", {}).get("text", ""))
                    elif seg.get("type") == "image":
                        msg_parts.append("[图片]")
                    elif seg.get("type") == "at":
                        msg_parts.append(f"@{seg.get('data', {}).get('qq', 'unknown')}")
                    else:
                        msg_parts.append(f"[{seg.get('type')}]")
                msg_preview = "".join(msg_parts)[:50]
            else:
                msg_preview = str(raw_message)[:50] if raw_message else "无文本内容"

            logger.info(
                f"收到消息: {msg_type} - {sender_id} ({sender_name}) - {msg_preview}..."
            )

            if self._message_handler:
                task = asyncio.create_task(self._safe_handle_message(data))
                self._tasks.add(task)
                task.add_done_callback(self._tasks.discard)

        elif post_type == "notice":
            self._handle_notice(data)

        elif post_type == "meta_event":
            # 心跳事件，不输出详细日志避免刷屏
            pass

        else:
            logger.debug(f"[?] 未知post_type: {post_type}, data: {data}")

    def _handle_notice(self, data: Dict) -> None:
        """处理通知事件"""
        notice_type = data.get("notice_type", "")
        sub_type = data.get("sub_type", "")

        if notice_type == "notify" and sub_type == "poke":
            target_id = data.get("target_id", 0)
            sender_id = data.get("user_id", 0)
            group_id = data.get("group_id", 0)

            logger.info(
                f"收到拍一拍通知: 发送者={sender_id}, 被拍者={target_id}, 群号={group_id if group_id else '私聊'}"
            )

            if self._message_handler:
                poke_event = {
                    "post_type": "notice",
                    "notice_type": "poke",
                    "group_id": group_id,
                    "user_id": sender_id,
                    "sender": {"user_id": sender_id},
                    "target_id": target_id,
                    "message": [],
                }
                task = asyncio.create_task(self._safe_handle_message(poke_event))
                self._tasks.add(task)
                task.add_done_callback(self._tasks.discard)

        elif notice_type == "group_increase":
            # 成员入群通知
            user_id = data.get("user_id", 0)
            group_id = data.get("group_id", 0)
            logger.info(f"新成员入群: 用户={user_id}, 群号={group_id}")

        elif notice_type == "group_decrease":
            # 成员退群通知
            user_id = data.get("user_id", 0)
            group_id = data.get("group_id", 0)
            leave_type = data.get("sub_type", "leave")
            logger.info(
                f"成员{'退群' if leave_type == 'leave' else '被移除'}: 用户={user_id}, 群号={group_id}"
            )

        elif notice_type == "friend":
            # 好友通知
            logger.info(f"[👥 好友通知] {sub_type}")

        else:
            logger.debug(f"[📢 通知类型] {notice_type}.{sub_type}")

    async def _safe_handle_message(self, data: Dict) -> None:
        """安全处理消息"""
        try:
            if self._message_handler:
                await self._message_handler(data)
        except Exception as e:
            logger.exception(f"处理消息出错: {type(e).__name__}: {e}")

    async def run_with_reconnect(self, reconnect_interval: float = 5.0) -> None:
        """带自动重连运行"""
        self._should_stop = False
        reconnect_count = 0

        while not self._should_stop:
            try:
                if reconnect_count > 0:
                    logger.info(f"[QQ] 尝试第 {reconnect_count} 次重连...")
                await self.connect()
                reconnect_count = 0
                await self.run()
            except websockets.ConnectionClosed:
                logger.warning("[QQ] 连接断开")
            except Exception as e:
                logger.error(f"[QQ] 运行错误: {e}")

            if self._should_stop:
                break

            reconnect_count += 1
            logger.info(f"{reconnect_interval}秒后重连...")
            await asyncio.sleep(reconnect_interval)

    def stop(self) -> None:
        """停止运行"""
        self._should_stop = True
        self._running = False

    # ========== 多媒体API扩展 ==========

    async def upload_image(self, file_path: str) -> Optional[str]:
        """
        上传图片到OneBot服务，返回file_id

        Args:
            file_path: 本地文件路径

        Returns:
            file_id字符串，用于后续发送图片消息
        """
        try:
            import os

            # 检查文件是否存在
            if not os.path.exists(file_path):
                logger.error(f"[QQ] 图片文件不存在: {file_path}")
                return None

            # 上传图片
            result = await self._call_api(
                "upload_image", {"file": f"file:///{file_path.replace(os.sep, '/')}"}
            )

            data = result.get("data", {})
            file_id = data.get("file_id")

            if file_id:
                logger.info(f"[QQ] 图片上传成功: {file_path} -> {file_id}")
                return file_id
            else:
                logger.error(f"[QQ] 图片上传失败，未返回file_id: {result}")
                return None

        except Exception as e:
            logger.error(f"[QQ] 图片上传失败: {e}")
            return None

    async def upload_file(self, file_path: str) -> Optional[str]:
        """
        上传文件到OneBot服务，返回file_id

        Args:
            file_path: 本地文件路径

        Returns:
            file_id字符串，用于后续发送文件消息
        """
        try:
            import os

            # 检查文件是否存在
            if not os.path.exists(file_path):
                logger.error(f"[QQ] 文件不存在: {file_path}")
                return None

            # 检查文件大小（限制50MB）
            file_size = os.path.getsize(file_path)
            if file_size > 50 * 1024 * 1024:  # 50MB
                logger.error(f"[QQ] 文件过大: {file_path} ({file_size} bytes)")
                return None

            # 上传文件
            result = await self._call_api(
                "upload_file", {"file": f"file:///{file_path.replace(os.sep, '/')}"}
            )

            data = result.get("data", {})
            file_id = data.get("file_id")

            if file_id:
                logger.info(f"[QQ] 文件上传成功: {file_path} -> {file_id}")
                return file_id
            else:
                logger.error(f"[QQ] 文件上传失败，未返回file_id: {result}")
                return None

        except Exception as e:
            logger.error(f"[QQ] 文件上传失败: {e}")
            return None

    async def send_group_image(
        self, group_id: int, image_path: str, caption: str = ""
    ) -> Dict[str, Any]:
        """
        发送群图片消息

        Args:
            group_id: 群号
            image_path: 图片文件路径
            caption: 图片说明文字

        Returns:
            API调用结果
        """
        # 先上传图片
        file_id = await self.upload_image(image_path)
        if not file_id:
            raise RuntimeError(f"图片上传失败: {image_path}")

        # 构建图片消息
        from .utils import create_image_message, QQMessageBuilder
        import os

        # 提取文件名
        filename = os.path.basename(image_path)

        # 使用消息构建器
        builder = QQMessageBuilder()
        if caption:
            builder.add_text(f"{caption}\n")
        builder.add_image(f"file:///{file_id}")

        # 发送消息
        return await self.send_group_message(
            group_id,
            builder.build_list() if self._supports_array_format() else builder.build(),
        )

    async def send_private_image(
        self, user_id: int, image_path: str, caption: str = ""
    ) -> Dict[str, Any]:
        """
        发送私聊图片消息

        Args:
            user_id: 用户QQ号
            image_path: 图片文件路径
            caption: 图片说明文字

        Returns:
            API调用结果
        """
        # 先上传图片
        file_id = await self.upload_image(image_path)
        if not file_id:
            raise RuntimeError(f"图片上传失败: {image_path}")

        # 构建图片消息
        from .utils import create_image_message, QQMessageBuilder

        builder = QQMessageBuilder()
        if caption:
            builder.add_text(f"{caption}\n")
        builder.add_image(f"file:///{file_id}")

        # 发送消息
        return await self.send_private_message(
            user_id,
            builder.build_list() if self._supports_array_format() else builder.build(),
        )

    async def send_group_file(
        self, group_id: int, file_path: str, caption: str = ""
    ) -> Dict[str, Any]:
        """
        发送群文件消息

        Args:
            group_id: 群号
            file_path: 文件路径
            caption: 文件说明文字

        Returns:
            API调用结果
        """
        # 先上传文件
        file_id = await self.upload_file(file_path)
        if not file_id:
            raise RuntimeError(f"文件上传失败: {file_path}")

        # 构建文件消息
        from .utils import QQMessageBuilder

        builder = QQMessageBuilder()
        if caption:
            builder.add_text(f"{caption}\n")
        builder.add_text(f"[CQ:file,file=file:///{file_id}]")

        # 发送消息
        return await self.send_group_message(
            group_id,
            builder.build_list() if self._supports_array_format() else builder.build(),
        )

    async def send_private_file(
        self, user_id: int, file_path: str, caption: str = ""
    ) -> Dict[str, Any]:
        """
        发送私聊文件消息

        Args:
            user_id: 用户QQ号
            file_path: 文件路径
            caption: 文件说明文字

        Returns:
            API调用结果
        """
        # 先上传文件
        file_id = await self.upload_file(file_path)
        if not file_id:
            raise RuntimeError(f"文件上传失败: {file_path}")

        # 构建文件消息
        from .utils import QQMessageBuilder

        builder = QQMessageBuilder()
        if caption:
            builder.add_text(f"{caption}\n")
        builder.add_text(f"[CQ:file,file=file:///{file_id}]")

        # 发送消息
        return await self.send_private_message(
            user_id,
            builder.build_list() if self._supports_array_format() else builder.build(),
        )

    async def send_face_message(
        self, target_type: str, target_id: int, face_id: int
    ) -> Dict[str, Any]:
        """
        发送表情消息

        Args:
            target_type: 目标类型，'group' 或 'private'
            target_id: 目标ID（群号或用户QQ号）
            face_id: 表情ID

        Returns:
            API调用结果
        """
        from .utils import QQMessageBuilder

        builder = QQMessageBuilder()
        builder.add_text(f"[CQ:face,id={face_id}]")

        if target_type == "group":
            return await self.send_group_message(
                target_id,
                builder.build_list()
                if self._supports_array_format()
                else builder.build(),
            )
        else:
            return await self.send_private_message(
                target_id,
                builder.build_list()
                if self._supports_array_format()
                else builder.build(),
            )

    def _supports_array_format(self) -> bool:
        """
        检查OneBot实现是否支持数组格式消息

        Returns:
            True如果支持数组格式，False如果只支持字符串格式
        """
        # 这里可以根据实际检测结果调整
        # 默认假设支持数组格式（标准OneBot）
        return True
