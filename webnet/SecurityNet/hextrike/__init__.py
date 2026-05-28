"""HexStrike 移植模块

从 Online_tools (hexstrike_server.py) 提取的核心模块，
全部自包含，不依赖 Flask，可在弥娅 SecurityNet 中直接调用。
"""

from .decision_engine import (
    IntelligentDecisionEngine,
    TargetType,
    TechnologyStack,
    TargetProfile,
    AttackStep,
    AttackChain,
)

from .error_handler import (
    ErrorType,
    RecoveryAction,
    ErrorContext,
    RecoveryStrategy,
    IntelligentErrorHandler,
    GracefulDegradation,
    error_handler,
    degradation_manager,
)

from .bugbounty import (
    BugBountyTarget,
    BugBountyWorkflowManager,
    FileUploadTestingFramework,
)

from .process_manager import (
    ProcessPool,
    EnhancedProcessManager,
    ResourceMonitor,
    PerformanceDashboard,
    AdvancedCache,
    enhanced_process_manager as hexstrike_process_manager,
)

from .browser_agent import BrowserAgent
from .ai_exploit import (
    AIExploitGenerator,
    VulnerabilityCorrelator,
)
from .ctf_automation import (
    CTFChallenge,
    CTFWorkflowManager,
    CTFToolManager,
    CTFChallengeAutomator,
    CTFTeamCoordinator,
)

__all__ = [
    "IntelligentDecisionEngine",
    "TargetType",
    "TechnologyStack",
    "TargetProfile",
    "AttackStep",
    "AttackChain",
    "ErrorType",
    "RecoveryAction",
    "ErrorContext",
    "RecoveryStrategy",
    "IntelligentErrorHandler",
    "GracefulDegradation",
    "error_handler",
    "degradation_manager",
    "BugBountyTarget",
    "BugBountyWorkflowManager",
    "FileUploadTestingFramework",
    "ProcessPool",
    "EnhancedProcessManager",
    "ResourceMonitor",
    "PerformanceDashboard",
    "AdvancedCache",
    "hexstrike_process_manager",
    "BrowserAgent",
    "AIExploitGenerator",
    "VulnerabilityCorrelator",
    "CTFChallenge",
    "CTFWorkflowManager",
    "CTFToolManager",
    "CTFChallengeAutomator",
    "CTFTeamCoordinator",
]
