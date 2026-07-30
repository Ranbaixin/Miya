"""
权限检查工具
"""

import json
import logging
from typing import Any, Dict

from webnet.ToolNet.base import BaseTool

logger = logging.getLogger(__name__)


class CheckPermissionTool(BaseTool):
    """检查权限工具"""

    @property
    def config(self) -> Dict[str, Any]:
        return {
            'name': 'check_permission',
            'description': '检查用户是否有指定权限。用于在执行敏感操作前验证用户权限。',
            'parameters': {
                'type': 'object',
                'properties': {
                    'user_id': {
                        'type': 'string',
                        'description': '用户ID（格式: platform_id，如: qq_123, web_user456）'
                    },
                    'permission': {
                        'type': 'string',
                        'description': '权限节点（如: tool.web_search, agent.task.execute）'
                    },
                    'list_mode': {
                        'type': 'boolean',
                        'description': '是否返回所有权限列表（默认为False，只检查是否有权限）',
                        'default': False
                    }
                },
                'required': ['user_id', 'permission']
            }
        }

    async def execute(self, args: Dict[str, Any], context) -> str:
        """执行权限检查

        安全性: fail-closed 默认拒绝。
        真实现接入前 (P6)，所有权限检查返回 False。
        最坏后果是自动化流程被阻止，而不是越权执行。
        """
        user_id = args.get('user_id', 'unknown')
        permission = args.get('permission', 'unknown')
        logger.warning(
            f"[SECURITY] 权限检查不可用, 默认拒绝: user={user_id} perm={permission}"
        )
        return json.dumps({
            "success": False,
            "allowed": False,
            "error": "permission_check_unavailable",
            "message": (
                "权限检查服务暂不可用，出于安全默认拒绝此操作。"
                "请人工确认后再执行。"
            ),
        }, ensure_ascii=False)
