"""
QQ交互子网 - 数据模型
从原 qq.py 中拆分出来的数据模型定义
"""

import json
import logging
from typing import Any, Callable, Dict, List, Optional, Set, Union
from datetime import datetime
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class ReplySegment:
    """引用消息段"""

    message_id: int = 0
    sender_name: str = ""
    content: str = ""
    sender_id: int = 0
    image_url: Optional[str] = None


@dataclass
class FileSegment:
    """文件消息段"""

    file_id: str = ""
    name: str = ""
    size: int = 0
    file_type: str = ""  # image, file, record, video


@dataclass
class QQMessage:
    """QQ消息数据类"""

    post_type: str = ""
    message_type: str = ""
    group_id: int = 0
    user_id: int = 0
    sender_id: int = 0
    message: str = ""
    raw_message: Union[str, List[Dict[str, Any]]] = field(default_factory=list)
    sender_name: str = ""
    group_name: str = ""
    sender_role: str = "member"
    sender_title: str = ""
    message_id: int = 0
    is_at_bot: bool = False
    reply_to_bot: bool = False
    time: datetime = field(default_factory=datetime.now)
    at_list: List[int] = field(default_factory=list)
    is_emoji_request: bool = False
    emoji_request_result: str = ""
    # 新增：引用消息和文件
    reply: Optional[ReplySegment] = None
    files: List[FileSegment] = field(default_factory=list)
    has_media: bool = False
    # 新增：图片分析相关属性
    image_data: Optional[bytes] = None
    image_info: Optional[Dict[str, Any]] = None
    image_analysis: Optional[Dict[str, Any]] = None
    has_image: bool = False
    # 新增：图片分析回复（用于直接发送而不经过decision_hub）
    image_response: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "post_type": self.post_type,
            "message_type": self.message_type,
            "group_id": self.group_id,
            "user_id": self.user_id,
            "sender_id": self.sender_id,
            "message": self.message,
            "raw_message": self.raw_message,
            "sender_name": self.sender_name,
            "group_name": self.group_name,
            "sender_role": self.sender_role,
            "sender_title": self.sender_title,
            "message_id": self.message_id,
            "is_at_bot": self.is_at_bot,
            "time": self.time.isoformat()
            if isinstance(self.time, datetime)
            else self.time,
            "at_list": self.at_list,
            "is_emoji_request": self.is_emoji_request,
            "emoji_request_result": self.emoji_request_result,
            "reply": {
                "message_id": self.reply.message_id,
                "sender_name": self.reply.sender_name,
                "content": self.reply.content,
            }
            if self.reply
            else None,
            "files": [
                {
                    "file_id": f.file_id,
                    "name": f.name,
                    "size": f.size,
                    "file_type": f.file_type,
                }
                for f in self.files
            ]
            if self.files
            else [],
            "has_media": self.has_media,
            "has_image": self.has_image,
            "image_analysis": self.image_analysis,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "QQMessage":
        """从字典创建"""
        time_str = data.get("time")
        time = None
        if time_str:
            if isinstance(time_str, datetime):
                time = time_str
            else:
                try:
                    time = datetime.fromisoformat(time_str)
                except:
                    time = datetime.now()

        reply_data = data.get("reply")
        reply = None
        if reply_data:
            reply = ReplySegment(
                message_id=reply_data.get("message_id", 0),
                sender_name=reply_data.get("sender_name", ""),
                content=reply_data.get("content", ""),
            )

        files_data = data.get("files", [])
        files = []
        for f in files_data:
            files.append(
                FileSegment(
                    file_id=f.get("file_id", ""),
                    name=f.get("name", ""),
                    size=f.get("size", 0),
                    file_type=f.get("file_type", ""),
                )
            )

        return cls(
            post_type=data.get("post_type", ""),
            message_type=data.get("message_type", ""),
            group_id=data.get("group_id", 0),
            user_id=data.get("user_id", 0),
            sender_id=data.get("sender_id", 0),
            message=data.get("message", ""),
            raw_message=data.get("raw_message", []),
            sender_name=data.get("sender_name", ""),
            group_name=data.get("group_name", ""),
            sender_role=data.get("sender_role", "member"),
            sender_title=data.get("sender_title", ""),
            message_id=data.get("message_id", 0),
            is_at_bot=data.get("is_at_bot", False),
            time=time or datetime.now(),
            at_list=data.get("at_list", []),
            is_emoji_request=data.get("is_emoji_request", False),
            emoji_request_result=data.get("emoji_request_result", ""),
            reply=reply,
            files=files,
            has_media=data.get("has_media", False),
        )


@dataclass
class QQNotice:
    """QQ通知事件数据类"""

    notice_type: str = ""
    sub_type: str = ""
    group_id: int = 0
    user_id: int = 0
    target_id: int = 0
    sender_id: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "notice_type": self.notice_type,
            "sub_type": self.sub_type,
            "group_id": self.group_id,
            "user_id": self.user_id,
            "target_id": self.target_id,
            "sender_id": self.sender_id,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "QQNotice":
        """从字典创建"""
        return cls(
            notice_type=data.get("notice_type", ""),
            sub_type=data.get("sub_type", ""),
            group_id=data.get("group_id", 0),
            user_id=data.get("user_id", 0),
            target_id=data.get("target_id", 0),
            sender_id=data.get("sender_id", 0),
        )
