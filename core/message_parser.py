"""
弥娅消息处理系统 (Message Parser)

功能：
1. 引用消息解析
2. 消息链解析
3. 消息类型转换
4. 消息cq码解析

参考 AstrBot 消息处理

作者: MIYA
日期: 2026-04-28
"""

import re
import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


# ==================== 枚举定义 ====================


class MessageType(str, Enum):
    """消息类型"""

    TEXT = "text"
    IMAGE = "image"
    VOICE = "voice"
    VIDEO = "video"
    FILE = "file"
    AT = "at"
    REPLY = "reply"
    FACE = "face"
    RECORD = "record"
    LOCATION = "location"
    POKER = "poker"
    SHARE = "share"


# ==================== 消息链 ====================


@dataclass
class MessageChain:
    """消息链"""

    elements: List["MessageSegment"] = field(default_factory=list)

    def __str__(self) -> str:
        return "".join(str(e) for e in self.elements)

    def __len__(self) -> int:
        return len(self.elements)

    def to_text(self) -> str:
        """转换为纯文本"""
        return "".join(e.text for e in self.elements if hasattr(e, "text") and e.text)

    def to_dict(self) -> List[Dict]:
        """转换为字典列表"""
        return [e.to_dict() for e in self.elements]

    @classmethod
    def from_list(cls, data: List[Dict]) -> "MessageChain":
        """从字典列表创建"""
        elements = []
        for item in data:
            msg_type = item.get("type", "text")
            segment = MessageSegment.create(msg_type, item)
            if segment:
                elements.append(segment)
        return cls(elements=elements)


@dataclass
class MessageSegment:
    """消息段"""

    type: MessageType
    data: Dict[str, Any] = field(default_factory=dict)

    @property
    def text(self) -> str:
        """获取文本内容"""
        if self.type == MessageType.TEXT:
            return self.data.get("text", "")
        return ""

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "type": self.type.value,
            "data": self.data,
        }

    @classmethod
    def create(cls, msg_type: str, data: Dict) -> Optional["MessageSegment"]:
        """创建消息段"""
        try:
            return cls(
                type=MessageType(msg_type),
                data=data,
            )
        except ValueError:
            return cls(
                type=MessageType.TEXT,
                data={"text": str(data)},
            )


# ==================== CQ码解析器 ====================


class CQCodeParser:
    """
    CQ码解析器

    支持解析：
    - [CQ:face,id=123]
    - [CQ:image,file=xxx,url=xxx]
    - [CQ:at,qq=123456]
    - [CQ:reply,id=123]
    - [CQ:record,file=xxx]
    - 等等
    """

    CQ_PATTERN = re.compile(r"\[CQ:([^,\]]+)(?:,([^\]]+))?\]")

    @staticmethod
    def parse(cq_string: str) -> MessageChain:
        """解析CQ码字符串"""
        elements = []

        # 分割文本和CQ码
        parts = CQCodeParser.CQ_PATTERN.split(cq_string)

        for part in parts:
            if not part:
                continue

            if CQCodeParser.CQ_PATTERN.match(f"[CQ:{part}]"):
                # 这是CQ码
                segment = CQCodeParser._parse_cq_segment(part)
                if segment:
                    elements.append(segment)
            else:
                # 这是普通文本
                if part.strip():
                    elements.append(
                        MessageSegment(
                            type=MessageType.TEXT,
                            data={"text": part},
                        )
                    )

        return MessageChain(elements=elements)

    @staticmethod
    def _parse_cq_segment(cq_data: str) -> Optional[MessageSegment]:
        """解析单个CQ码段"""
        # 解析类型和参数
        parts = cq_data.split(",")
        cq_type = parts[0].strip()

        # 解析参数
        data = {}
        for param in parts[1:]:
            if "=" in param:
                key, value = param.split("=", 1)
                data[key.strip()] = value.strip()

        # 映射到消息类型
        type_map = {
            "face": MessageType.FACE,
            "image": MessageType.IMAGE,
            "voice": MessageType.VOICE,
            "video": MessageType.VIDEO,
            "file": MessageType.FILE,
            "at": MessageType.AT,
            "reply": MessageType.REPLY,
            "record": MessageType.RECORD,
            "location": MessageType.LOCATION,
            "poker": MessageType.POKER,
            "share": MessageType.SHARE,
        }

        msg_type = type_map.get(cq_type, MessageType.TEXT)

        return MessageSegment(type=msg_type, data=data)

    @staticmethod
    def to_cq_code(segment: MessageSegment) -> str:
        """将消息段转换为CQ码"""
        if segment.type == MessageType.TEXT:
            return segment.data.get("text", "")

        params = ",".join(f"{k}={v}" for k, v in segment.data.items())
        return f"[CQ:{segment.type.value},{params}]"

    @staticmethod
    def to_cq_string(chain: MessageChain) -> str:
        """将消息链转换为CQ码字符串"""
        return "".join(CQCodeParser.to_cq_code(s) for s in chain.elements)


# ==================== 引用消息处理器 ====================


class QuoteMessageHandler:
    """
    引用消息处理器

    功能：
    - 解析引用消息
    - 获取引用消息内容
    - 处理引用回复
    """

    @staticmethod
    def parse_quote(chain: MessageChain) -> Optional[Dict]:
        """解析引用消息"""
        for segment in chain.elements:
            if segment.type == MessageType.REPLY:
                return {
                    "message_id": segment.data.get("id"),
                    "qq": segment.data.get("qq"),
                    "time": segment.data.get("time"),
                }
        return None

    @staticmethod
    def extract_quoted_text(chain: MessageChain) -> str:
        """提取引用中的文本"""
        text_parts = []
        in_quote = False

        for segment in chain.elements:
            if segment.type == MessageType.REPLY:
                in_quote = True
            elif segment.type == MessageType.TEXT:
                if in_quote:
                    text_parts.append(segment.text)

            # 遇到新消息段结束引用
            if (
                in_quote
                and segment.type != MessageType.REPLY
                and segment.type != MessageType.TEXT
            ):
                in_quote = False

        return "".join(text_parts)

    @staticmethod
    def create_quote_message(
        message_id: str,
        message: str,
        user_id: str = None,
    ) -> MessageChain:
        """创建引用消息"""
        data = {"id": message_id}
        if user_id:
            data["qq"] = user_id

        elements = [
            MessageSegment(type=MessageType.REPLY, data=data),
            MessageSegment(type=MessageType.TEXT, data={"text": message}),
        ]

        return MessageChain(elements=elements)


# ==================== 消息解析器 ====================


class MessageParser:
    """
    消息解析器

    统一入口：
    - 解析CQ码
    - 解析JSON消息
    - 解析纯文本
    """

    @staticmethod
    def parse(message: Any) -> MessageChain:
        """
        解析消息为MessageChain

        支持：
        - str: 尝试CQ码解析
        - list: 视为消息段列表
        - dict: 转换为消息段
        """
        if isinstance(message, str):
            return CQCodeParser.parse(message)

        elif isinstance(message, list):
            return MessageChain.from_list(message)

        elif isinstance(message, dict):
            return MessageChain.from_list([message])

        elif isinstance(message, MessageChain):
            return message

        else:
            return MessageChain(
                elements=[
                    MessageSegment(
                        type=MessageType.TEXT,
                        data={"text": str(message)},
                    )
                ]
            )

    @staticmethod
    def extract_mentions(chain: MessageChain) -> List[str]:
        """提取@的用户列表"""
        mentions = []
        for segment in chain.elements:
            if segment.type == MessageType.AT:
                qq = segment.data.get("qq")
                if qq:
                    mentions.append(qq)
        return mentions

    @staticmethod
    def extract_images(chain: MessageChain) -> List[Dict]:
        """提取图片列表"""
        images = []
        for segment in chain.elements:
            if segment.type == MessageType.IMAGE:
                images.append(
                    {
                        "file": segment.data.get("file"),
                        "url": segment.data.get("url"),
                        "path": segment.data.get("path"),
                    }
                )
        return images

    @staticmethod
    def extract_files(chain: MessageChain) -> List[Dict]:
        """提取文件列表"""
        files = []
        for segment in chain.elements:
            if segment.type == MessageType.FILE:
                files.append(
                    {
                        "name": segment.data.get("name"),
                        "file": segment.data.get("file"),
                        "size": segment.data.get("size"),
                    }
                )
        return files

    @staticmethod
    def is_contains_keyword(chain: MessageChain, keyword: str) -> bool:
        """检查是否包含关键词"""
        text = chain.to_text()
        return keyword in text

    @staticmethod
    def extract_command(chain: MessageChain) -> Optional[Dict]:
        """
        提取命令

        返回: {"command": "/help", "args": ["arg1"]} 或 None
        """
        text = chain.to_text().strip()

        if not text.startswith("/"):
            return None

        parts = text.split(maxsplit=1)
        command = parts[0]
        args = parts[1].split() if len(parts) > 1 else []

        return {
            "command": command,
            "args": args,
            "full": text,
        }


# ==================== 全局实例 ====================


_message_parser: Optional[MessageParser] = None


def get_message_parser() -> MessageParser:
    """获取消息解析器"""
    global _message_parser
    if _message_parser is None:
        _message_parser = MessageParser()
    return _message_parser


__all__ = [
    "MessageType",
    "MessageChain",
    "MessageSegment",
    "CQCodeParser",
    "QuoteMessageHandler",
    "MessageParser",
    "get_message_parser",
]
