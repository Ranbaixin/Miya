"""
AstrBot Sandbox 配置
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SandboxConfig:
    """沙盒执行配置"""

    runtime: str = "local"
    """运行时类型: none, local, sandbox"""

    workspace_path: Optional[str] = None
    """工作区路径"""

    max_execution_time: int = 120
    """最大执行时间(秒)"""

    max_memory_mb: int = 512
    """最大内存(MB)"""

    allowed_commands: list = field(
        default_factory=lambda: ["ls", "pwd", "cat", "echo", "grep", "find", "cd"]
    )
    """允许的命令列表"""

    blocked_commands: list = field(
        default_factory=lambda: ["rm", "mkfs", "dd", "fdisk"]
    )
    """禁止的命令列表"""

    enable_network: bool = True
    """是否允许网络访问"""

    enable_filesystem_write: bool = True
    """是否允许文件系统写操作"""

    python_env: str = "python3"
    """Python环境"""

    bay_endpoint: Optional[str] = None
    """Bay服务endpoint (浏览器自动化)"""

    bay_api_key: Optional[str] = None
    """Bay API Key"""

    enable_browser: bool = False
    """是否启用浏览器自动化"""
