"""
平台消息处理辅助 Mixin

提供所有平台共享的消息转换和路由逻辑。
"""

from __future__ import annotations

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
                return response if response else "弥娅暂无回复"
            else:
                return "决策系统未就绪"

        except Exception as e:
            logger.error(f"[{self.platform_id}] 消息处理异常: {e}", exc_info=True)
            return f"处理消息时出错了: {e}"
