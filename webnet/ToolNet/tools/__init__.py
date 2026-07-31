"""
ToolNet 工具包 - 弥娅统一工具服务

> 惰性加载设计（P8 Step4 校准 2026-07-31）：
> 原实现用 16 个 star import 强制加载所有工具子模块，导致 `import webnet`
> 就强制依赖所有可选依赖组（office→pandas、network→bs4、visualization→matplotlib 等），
> 任一缺失即整个 webnet 无法导入。改为 `__getattr__` 按需加载：仅访问具体
> 工具时才 import 对应子包；可选依赖缺失的子包在未使用其工具时不阻塞导入。
"""

import importlib
import logging

logger = logging.getLogger(__name__)

_SUBMODULES = [
    "auth",
    "basic",
    "bilibili",
    "cognitive",
    "core",
    "entertainment",
    "group",
    "knowledge",
    "life",
    "memory",
    "message",
    "network",
    "office",
    "reporting",
    "scheduler",
    "social",
    "visualization",
]

__all__ = [
    # 核心服务
    "TaskScheduler",
    "BackupManager",
    "SystemMonitor",
    "WorkflowEngine",
    "FileClassifier",
    # 网络交互
    "WebSearch",
    "WebResearch",
    "APIClient",
    # 社交平台
    "SocialBase",
    # 办公文档
    "ExcelProcessor",
    "PDFDocxProcessor",
    "InvoiceParser",
    # 可视化
    "ChartGenerator",
    "DataAnalyzer",
    # 报表生成
    "ReportGenerator",
    # 认证
    "AddUser",
    "RemoveUser",
    "CheckPermission",
    "GrantPermission",
    "RevokePermission",
    "ListPermissions",
    "ListGroups",
    # 基础功能
    "GetCurrentTime",
    "GetUserInfo",
    "PythonInterpreter",
    # 生活记忆
    "LifeAddMemory",
    "LifeDeleteMemory",
    "LifeListNodes",
    "LifeSearchMemory",
    "LifeGetSummary",
    "LifeGetMood",
    "LifeSetMood",
    "LifeGetHealth",
    "LifeSetHealth",
    "LifeGetState",
    # 记忆管理
    "MemoryAdd",
    "MemoryDelete",
    "MemoryUpdate",
    "MemoryList",
    "AutoExtractMemory",
    # 消息工具
    "SendMessageTool",
    "SendTextFileTool",
    "SendUrlFileTool",
    "GetRecentMessagesTool",
    # 任务调度
    "CreateScheduleTask",
    "DeleteScheduleTask",
    "ListScheduleTasks",
    # 娱乐
    "GetLeaderboard",
    "GetStats",
    "GetAchievements",
    "CheckBalance",
    "TransferCurrency",
    # 群组
    "ListMembers",
    "AddMember",
    "RemoveMember",
    "SetGroupName",
    "GetGroupInfo",
    # 知识库
    "AddKnowledge",
    "SearchKnowledge",
    "DeleteKnowledge",
    # 认知
    "GetProfile",
    "SearchProfiles",
    "SearchEvents",
    # B站
    "BilibiliVideo",
]


def __getattr__(name):
    """按需加载子模块中的工具（PEP 562，P8 惰性化）。"""
    for sub in _SUBMODULES:
        try:
            mod = importlib.import_module(f".{sub}", __name__)
        except ImportError:
            continue  # 可选依赖缺失的子包：未使用时跳过，不阻塞其他工具
        if hasattr(mod, name):
            return getattr(mod, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
