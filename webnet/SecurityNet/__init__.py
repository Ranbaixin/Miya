"""
SecurityNet - 弥娅网络安全子网

弥娅的智能安全中枢，提供完整的网络安全能力：

原生模块:
- IntelligentOrchestrator: 5 阶段全链路自动化 (侦察 → 分析 → 利用 → 情报 → 报告)
- SecuritySubnet: 14 个安全工具
- search_engines: 6 个搜索引擎 (DuckDuckGo / Google / Sploitus / NVD / SearXNG / Tavily)

移植模块 (hextrike/):
- IntelligentDecisionEngine: AI 智能决策引擎（目标分析/工具推荐/攻击链编排）
- IntelligentErrorHandler: 10 种错误分类 + 7 种恢复策略
- BugBountyWorkflowManager: 赏金猎人 5 阶段工作流
- EnhancedProcessManager: 进程池 + 自动扩缩容
- BrowserAgent: 浏览器安全检测代理

Agent 系统 (agents/):
- 13 个 AI Agent 角色 + 35 个 Agent 工具
- Agent 编排引擎 (Generator→Refiner→Primary→Reporter)
- 记忆系统 (JSON + 知识图谱)

工具执行 (tool_wrappers.py):
- 100+ 安全命令行工具 wrapper
- 10 个类别：network_recon / subdomain / web_recon / dir_enum / vuln_scan / exploitation / password / reverse_eng / forensics / cloud

桥接模块（可选外部服务）:
- online_tools_bridge: HexStrike 160+ REST API
- pentagi_bridge: PentAGI GraphQL API
"""

from .subnet import SecuritySubnet, SecurityConfig
from .orchestrator import IntelligentOrchestrator, SecurityOrchestrator, get_security_orchestrator
from .search_engines import (
    search,
    search_sync,
    security_search,
    search_duckduckgo,
    search_google,
    search_sploitus,
    search_cve,
    search_searxng,
    search_tavily,
    SEARCH_ENGINES,
)
from .online_tools_bridge import (
    HexStrikeClient,
    get_hexstrike_client,
    try_hexstrike_tool,
    MIYA_TO_HEXSTRIKE,
)
from .pentagi_bridge import (
    PentAGIClient,
    get_pentagi_client,
    try_pentagi_penetration_test,
)
from .hextrike import (
    IntelligentDecisionEngine,
    TargetType,
    TechnologyStack,
    TargetProfile,
    AttackStep,
    AttackChain,
    IntelligentErrorHandler,
    GracefulDegradation,
    ErrorType,
    RecoveryAction,
    BugBountyTarget,
    BugBountyWorkflowManager,
    FileUploadTestingFramework,
    ProcessPool,
    EnhancedProcessManager,
    ResourceMonitor,
    PerformanceDashboard,
    BrowserAgent,
    AIExploitGenerator,
    VulnerabilityCorrelator,
    CTFChallenge,
    CTFWorkflowManager,
    CTFToolManager,
    CTFChallengeAutomator,
    CTFTeamCoordinator,
)

from .anonymizer import anonymize, anonymize_for_storage

from .skill_manager import SkillManager, SkillInfo, get_skill_manager
from .checkpoint import CheckpointManager, get_checkpoint
from .agents.agent_orchestrator import CTFSolver, CTFStep
from .engine import MiyaEngine, get_engine
from .ctf_tool_matcher import CTFToolMatcher, get_ctf_matcher
from .http_session import HTTPSessionManager, get_http_manager
from .knowledge_graph import KnowledgeGraph, get_knowledge_graph

from .tool_wrappers import (
    TOOLS as SECURITY_TOOLS,
    ToolCommand,
    execute_tool,
    execute_tool_sync,
    get_tool,
    list_tools,
    get_categories,
    get_tools_status,
    check_installed_tools,
)

__all__ = [
    # 原生模块
    "SecuritySubnet",
    "SecurityConfig",
    "IntelligentOrchestrator",
    "SecurityOrchestrator",
    "get_security_orchestrator",
    # 搜索引擎
    "search",
    "search_sync",
    "security_search",
    "search_duckduckgo",
    "search_google",
    "search_sploitus",
    "search_cve",
    "search_searxng",
    "search_tavily",
    "SEARCH_ENGINES",
    # 桥接
    "HexStrikeClient",
    "get_hexstrike_client",
    "try_hexstrike_tool",
    "MIYA_TO_HEXSTRIKE",
    "PentAGIClient",
    "get_pentagi_client",
    "try_pentagi_penetration_test",
    # 移植模块
    "IntelligentDecisionEngine",
    "TargetType",
    "TechnologyStack",
    "TargetProfile",
    "AttackStep",
    "AttackChain",
    "IntelligentErrorHandler",
    "GracefulDegradation",
    "ErrorType",
    "RecoveryAction",
    "BugBountyTarget",
    "BugBountyWorkflowManager",
    "FileUploadTestingFramework",
    "ProcessPool",
    "EnhancedProcessManager",
    "ResourceMonitor",
    "PerformanceDashboard",
    "BrowserAgent",
    "AIExploitGenerator",
    "VulnerabilityCorrelator",
    "CTFChallenge",
    "CTFWorkflowManager",
    "CTFToolManager",
    "CTFChallengeAutomator",
    "CTFTeamCoordinator",
    # 脱敏
    "anonymize",
    "anonymize_for_storage",
    # 工具包装器
    "SECURITY_TOOLS",
    "ToolCommand",
    "execute_tool",
    "execute_tool_sync",
    "get_tool",
    "list_tools",
    "get_categories",
    "get_tools_status",
    "check_installed_tools",
    # BUUCTF_Agent 融合模块
    "SkillManager",
    "SkillInfo",
    "get_skill_manager",
    "CheckpointManager",
    "get_checkpoint",
    "CTFSolver",
    "CTFStep",
    # 统一引擎
    "MiyaEngine",
    "get_engine",
    # CTF 工具匹配器
    "CTFToolMatcher",
    "get_ctf_matcher",
    # HTTP 会话管理
    "HTTPSessionManager",
    "get_http_manager",
    # 知识图谱
    "KnowledgeGraph",
    "get_knowledge_graph",
]
