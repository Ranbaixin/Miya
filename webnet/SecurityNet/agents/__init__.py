"""Agent 系统 — PentAGI 移植

13 个 AI Agent + 33 个 Agent 工具 + 记忆系统 + 编排引擎，
全部 Python 原生实现，可直接在弥娅中运行。

使用示例:
    from webnet.SecurityNet.agents import (
        AgentOrchestrator, get_agent_orchestrator,
        get_tool_definitions, get_agent_prompt,
    )

    # 获取工具定义（用于 OpenAI function calling）
    tools = get_tool_definitions()

    # 运行安全测试任务
    orchestrator = get_agent_orchestrator(llm_callback=your_ai_client)
    task = await orchestrator.execute_security_task("192.168.1.1")
    print(task.report)
"""

from .agent_tools import (
    ALL_TOOLS,
    TOOL_TYPE_MAP,
    ToolType,
    ToolSchema,
    get_tool_definitions,
    get_tools_by_type,
    get_all_tools,
    SUMMARIZABLE_TOOLS,
    STORABLE_TOOLS,
)

from .agent_prompts import (
    AGENT_PROMPTS,
    AGENT_DEFAULT_TOOLS,
    get_agent_prompt,
    get_agent_tools,
)

from .agent_memory import (
    AgentMemory,
    MemoryEntry,
    get_agent_memory,
)

from .agent_orchestrator import (
    AgentOrchestrator,
    AgentTask,
    AgentTaskStatus,
    AgentType,
    Subtask,
    get_agent_orchestrator,
)

__all__ = [
    # 工具
    "ALL_TOOLS",
    "TOOL_TYPE_MAP",
    "ToolType",
    "ToolSchema",
    "get_tool_definitions",
    "get_tools_by_type",
    "get_all_tools",
    "SUMMARIZABLE_TOOLS",
    "STORABLE_TOOLS",
    # 提示词
    "AGENT_PROMPTS",
    "AGENT_DEFAULT_TOOLS",
    "get_agent_prompt",
    "get_agent_tools",
    # 记忆
    "AgentMemory",
    "MemoryEntry",
    "get_agent_memory",
    # 编排
    "AgentOrchestrator",
    "AgentTask",
    "AgentTaskStatus",
    "AgentType",
    "Subtask",
    "get_agent_orchestrator",
]
