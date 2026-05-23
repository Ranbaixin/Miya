"""
QQ消息解析器
统一处理消息段：引用、文件、语音、图片、合并转发等
参考 Undefined 项目实现，符合弥娅系统架构
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ParsedSegment:
    """解析后的消息段"""

    type: str
    content: str
    raw_data: Dict[str, Any]


@dataclass
class ReplyInfo:
    """引用消息信息"""

    message_id: int
    sender_name: str
    content: str
    sender_id: int = 0  # 【新增】保存发送者ID


@dataclass
class FileInfo:
    """文件信息"""

    file_id: str
    name: str
    size: int
    file_type: str


class QQMessageParser:
    """QQ消息解析器"""

    def __init__(self, qq_client=None):
        self.qq_client = qq_client

    def set_client(self, client):
        """设置QQ客户端用于获取引用消息"""
        self.qq_client = client

    def normalize_message(self, message: Any) -> List[Dict[str, Any]]:
        """将消息归一化为消息段数组"""
        if isinstance(message, list):
            return [item for item in message if isinstance(item, dict)]
        if isinstance(message, dict):
            return [message]
        if isinstance(message, str):
            return self._parse_cq_codes(message)
        return []

    def _parse_cq_codes(self, text: str) -> List[Dict[str, Any]]:
        """解析CQ码字符串为消息段数组"""
        import re

        segments = []

        cq_pattern = re.compile(r"\[CQ:([^,]+),([^\]]+)\]")

        last_end = 0
        for match in cq_pattern.finditer(text):
            if match.start() > last_end:
                text_content = text[last_end : match.start()]
                if text_content:
                    segments.append({"type": "text", "data": {"text": text_content}})

            cq_type = match.group(1)
            cq_data_str = match.group(2)

            data = {}
            for item in cq_data_str.split(","):
                if "=" in item:
                    key, value = item.split("=", 1)
                    data[key] = value

            segments.append({"type": cq_type, "data": data})
            last_end = match.end()

        if last_end < len(text):
            remaining_text = text[last_end:]
            if remaining_text:
                segments.append({"type": "text", "data": {"text": remaining_text}})

        return segments

    def extract_text(
        self, message_content: List[Dict[str, Any]], skip_image: bool = True
    ) -> str:
        """提取消息中的纯文本"""
        texts = []
        for segment in message_content:
            seg_type = segment.get("type")
            data = segment.get("data", {})

            if seg_type == "text":
                texts.append(data.get("text", ""))
            elif seg_type == "at":
                qq = data.get("qq", "")
                texts.append(f"[@{qq}]")
            elif seg_type == "image":
                if skip_image:
                    texts.append("[图片]")
            elif seg_type == "file":
                name = data.get("name", "文件")
                texts.append(f"[文件: {name}]")
            elif seg_type == "record":
                texts.append("[语音]")
            elif seg_type == "video":
                texts.append("[视频]")
            elif seg_type == "forward":
                fid = data.get("id", "")
                texts.append(f"[合并转发: {fid}]")
            elif seg_type == "reply":
                rid = data.get("id", "")
                texts.append(f"[引用消息: {rid}]")

        return "".join(texts).strip()

    async def parse_for_history(
        self, message_content: List[Dict[str, Any]], bot_qq: int = 0
    ) -> str:
        """解析消息内容用于历史记录（支持引用消息展开）"""
        texts = []

        for segment in message_content:
            seg_type = segment.get("type")
            data = segment.get("data", {})

            if seg_type == "reply":
                reply_info = await self._parse_reply(data)
                if reply_info:
                    # 【修复】包含发送者ID
                    sender_id_str = (
                        str(reply_info.sender_id) if reply_info.sender_id else "未知"
                    )
                    texts.append(
                        f'<quote sender="{reply_info.sender_name}" sender_id="{sender_id_str}">{reply_info.content}</quote>'
                    )
                else:
                    rid = data.get("id", "")
                    texts.append(f"[引用消息: {rid}]")
            elif seg_type == "text":
                texts.append(data.get("text", ""))
            elif seg_type == "at":
                qq = data.get("qq", "")
                if int(qq) == bot_qq:
                    texts.append("[@弥娅]")
                else:
                    texts.append(f"[@{qq}]")
            elif seg_type == "image":
                texts.append("[图片]")
            elif seg_type == "file":
                name = data.get("name", "文件")
                texts.append(f"[文件: {name}]")
            elif seg_type == "record":
                texts.append("[语音]")
            elif seg_type == "video":
                texts.append("[视频]")
            elif seg_type == "forward":
                texts.append("[合并转发]")

        return "".join(texts).strip()

    async def _parse_reply(self, data: Dict[str, Any]) -> Optional[ReplyInfo]:
        """解析引用消息"""
        if not self.qq_client:
            return None

        msg_id = data.get("id") or data.get("message_id")
        if not msg_id:
            return None

        try:
            msg_id = int(msg_id)
            reply_msg = await self.qq_client.get_msg(msg_id)

            if not reply_msg:
                return None

            sender = reply_msg.get("sender", {})
            # 【修复】正确获取发送者ID和名称
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

            content = self.extract_text(
                self.normalize_message(reply_msg.get("message", [])), skip_image=True
            )

            return ReplyInfo(
                message_id=msg_id, sender_name=sender_name, content=content[:100]
            )
        except Exception as e:
            logger.warning(f"解析引用消息失败: {e}")
            return None

    def has_segment_type(
        self, message_content: List[Dict[str, Any]], segment_type: str
    ) -> bool:
        """检查消息是否包含指定类型的段"""
        return any(segment.get("type") == segment_type for segment in message_content)

    def get_reply_id(self, message_content: List[Dict[str, Any]]) -> Optional[int]:
        """获取引用消息的ID"""
        for segment in message_content:
            if segment.get("type") == "reply":
                msg_id = segment.get("data", {}).get("id") or segment.get(
                    "data", {}
                ).get("message_id")
                if msg_id:
                    try:
                        return int(msg_id)
                    except (ValueError, TypeError):
                        pass
        return None

    def get_files(self, message_content: List[Dict[str, Any]]) -> List[FileInfo]:
        """获取消息中的所有文件信息"""
        files = []
        for segment in message_content:
            if segment.get("type") == "file":
                data = segment.get("data", {})
                files.append(
                    FileInfo(
                        file_id=data.get("file", ""),
                        name=data.get("name", "未知文件"),
                        size=data.get("size", 0),
                        file_type="file",
                    )
                )
            elif segment.get("type") == "record":
                data = segment.get("data", {})
                files.append(
                    FileInfo(
                        file_id=data.get("file", ""),
                        name="语音消息",
                        size=data.get("size", 0),
                        file_type="record",
                    )
                )
        return files

    def has_media(self, message_content: List[Dict[str, Any]]) -> bool:
        """检查消息是否包含多媒体"""
        media_types = {"image", "file", "record", "video", "audio"}
        return any(segment.get("type") in media_types for segment in message_content)


def get_message_parser(qq_client=None) -> QQMessageParser:
    """获取消息解析器实例"""
    return QQMessageParser(qq_client)
