"""Agent 编排器 — Python 原生实现

从 PentAGI 移植的 Agent 编排引擎，实现：
Generator → Refiner → Primary Agent → 团队委托 → Reporter → 完成

所有 Agent 运行在弥娅的 AI Client 基础上（decision_hub），
不依赖外部 Docker 容器或 GraphQL API。
"""

import asyncio
import json
import logging
import os
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

from .agent_tools import (
    ALL_TOOLS,
    TOOL_TYPE_MAP,
    ToolType,
    ToolSchema,
    get_tool_definitions,
    get_tools_by_type,
    SUMMARIZABLE_TOOLS,
    STORABLE_TOOLS,
)
from .agent_prompts import (
    AGENT_PROMPTS,
    AGENT_DEFAULT_TOOLS,
    get_agent_prompt,
    get_agent_tools,
)
from .agent_memory import AgentMemory, get_agent_memory

logger = logging.getLogger(__name__)


class AgentTaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class AgentType(Enum):
    PRIMARY = "primary_agent"
    PENTESTER = "pentester"
    CODER = "coder"
    INSTALLER = "installer"
    SEARCHER = "searcher"
    ADVISER = "adviser"
    MEMORIST = "memorist"
    GENERATOR = "generator"
    REFINER = "refiner"
    REPORTER = "reporter"
    REFLECTOR = "reflector"
    ENRICHER = "enricher"
    ASSISTANT = "assistant"


@dataclass
class Subtask:
    id: str
    title: str
    description: str
    agent_type: AgentType
    status: AgentTaskStatus = AgentTaskStatus.PENDING
    result: Optional[str] = None
    tools_used: List[str] = field(default_factory=list)


@dataclass
class AgentTask:
    """一次 Agent 任务"""

    id: str
    target: str
    description: str
    subtasks: List[Subtask] = field(default_factory=list)
    status: AgentTaskStatus = AgentTaskStatus.PENDING
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None
    report: Optional[str] = None
    findings: List[Dict[str, Any]] = field(default_factory=list)


# LLM Callback 类型：接收 system_prompt, messages, tools → 返回 response_text
LLMCallback = Callable[
    [str, List[Dict[str, str]], List[Dict[str, Any]]],
    Any,  # async callable
]


class AgentOrchestrator:
    """Agent 编排引擎

    使用流程：
    1. orchestrator = AgentOrchestrator(llm_callback=your_ai_client_call)
    2. task = await orchestrator.execute_security_task("192.168.1.1")
    3. print(task.report)
    """

    def __init__(
        self,
        llm_callback: Optional[LLMCallback] = None,
        memory: Optional[AgentMemory] = None,
    ):
        self.llm = llm_callback
        self.memory = memory or get_agent_memory()
        self.tasks: Dict[str, AgentTask] = {}
        self._tool_handlers: Dict[str, Callable] = {}

        # 注册内置工具处理器
        self._register_default_handlers()

    def _register_default_handlers(self):
        """注册内置工具处理器"""
        # 环境工具
        self._tool_handlers["terminal"] = self._handle_terminal
        self._tool_handlers["file"] = self._handle_file
        # 搜索工具（从 search_engines 调用）
        # Agent 委托工具（在 _execute_agent 中处理）
        # 记忆工具
        self._tool_handlers["search_in_memory"] = self._handle_search_in_memory
        self._tool_handlers["search_guide"] = self._handle_search_guide
        self._tool_handlers["store_guide"] = self._handle_store_guide
        self._tool_handlers["search_answer"] = self._handle_search_answer
        self._tool_handlers["store_answer"] = self._handle_store_answer
        self._tool_handlers["search_code"] = self._handle_search_code
        self._tool_handlers["store_code"] = self._handle_store_code
        self._tool_handlers["graphiti_search"] = self._handle_graphiti_search
        # 障碍工具
        self._tool_handlers["done"] = self._handle_done
        self._tool_handlers["ask"] = self._handle_ask
        # 结果工具
        self._tool_handlers["report_result"] = self._handle_report
        self._tool_handlers["hack_result"] = self._handle_hack_result
        self._tool_handlers["search_result"] = self._handle_generic_result
        self._tool_handlers["code_result"] = self._handle_generic_result
        self._tool_handlers["maintenance_result"] = self._handle_generic_result
        self._tool_handlers["memorist_result"] = self._handle_generic_result
        self._tool_handlers["enricher_result"] = self._handle_generic_result
        # 任务管理
        self._tool_handlers["subtask_list"] = self._handle_subtask_list
        self._tool_handlers["subtask_patch"] = self._handle_subtask_patch

    # ─── 工具处理器 ──────────────────────────────

    async def _handle_terminal(self, args: Dict[str, Any]) -> str:
        """执行终端命令"""
        cmd = args.get("input", "")
        cwd = args.get("cwd", ".")
        timeout = args.get("timeout", 60)
        if not cmd:
            return "Error: No command provided"

        try:
            proc = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            result = stdout.decode("utf-8", errors="replace") or stderr.decode("utf-8", errors="replace")
            self.memory.store_tool_exec("terminal", result)
            return result[:5000]
        except asyncio.TimeoutError:
            return f"Command timed out after {timeout}s"
        except Exception as e:
            return f"Command execution failed: {e}"

    async def _handle_file(self, args: Dict[str, Any]) -> str:
        """文件操作"""
        action = args.get("action", "read_file")
        path = args.get("path", "")
        content = args.get("content", "")
        if not path:
            return "Error: No file path provided"

        try:
            if action == "read_file":
                import os

                if not os.path.exists(path):
                    return f"File not found: {path}"
                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    return f"File content of {path}:\n\n{f.read()[:10000]}"
            elif action == "update_file":
                with open(path, "w", encoding="utf-8") as f:
                    f.write(content)
                return f"File written: {path} ({len(content)} chars)"
            return f"Unknown action: {action}"
        except Exception as e:
            return f"File operation failed: {e}"

    async def _handle_search_in_memory(self, args: Dict[str, Any]) -> str:
        questions = args.get("questions", [args.get("question", "")])
        if isinstance(questions, str):
            questions = [questions]
        task_id = args.get("task_id")
        results = self.memory.search_in_memory(questions, task_id=task_id)
        if not results:
            return "No relevant information found in long-term memory."
        return "\n\n".join(f"[{r.type}] {r.content[:500]}" for r in results)

    async def _handle_search_guide(self, args: Dict[str, Any]) -> str:
        questions = args.get("questions", [args.get("question", "")])
        if isinstance(questions, str):
            questions = [questions]
        results = self.memory.search_guides(questions, guide_type=args.get("type"))
        return "\n\n".join(f"[Guide] {r.content[:500]}" for r in results) or "No guides found."

    async def _handle_store_guide(self, args: Dict[str, Any]) -> str:
        gid = self.memory.store_guide(
            args.get("question", ""),
            args.get("guide", ""),
            args.get("type", "pentest"),
        )
        return f"Guide stored successfully (ID: {gid})"

    async def _handle_search_answer(self, args: Dict[str, Any]) -> str:
        questions = args.get("questions", [args.get("question", "")])
        if isinstance(questions, str):
            questions = [questions]
        results = self.memory.search_answers(questions, answer_type=args.get("type"))
        return "\n\n".join(f"[Answer] {r.content[:500]}" for r in results) or "No answers found."

    async def _handle_store_answer(self, args: Dict[str, Any]) -> str:
        aid = self.memory.store_answer(
            args.get("question", ""),
            args.get("answer", ""),
            args.get("type", "other"),
        )
        return f"Answer stored (ID: {aid})"

    async def _handle_search_code(self, args: Dict[str, Any]) -> str:
        questions = args.get("questions", [args.get("question", "")])
        if isinstance(questions, str):
            questions = [questions]
        results = self.memory.search_code(questions, lang=args.get("lang"))
        return (
            "\n\n".join(f"[Code:{r.metadata.get('lang', '')}] {r.content[:500]}" for r in results) or "No code found."
        )

    async def _handle_store_code(self, args: Dict[str, Any]) -> str:
        cid = self.memory.store_code(
            args.get("question", ""),
            args.get("code", ""),
            args.get("lang", "python"),
            args.get("explanation", ""),
            args.get("description", ""),
        )
        return f"Code stored (ID: {cid})"

    async def _handle_graphiti_search(self, args: Dict[str, Any]) -> str:
        results = self.memory.graphiti_search(
            search_type=args.get("search_type", "recent_context"),
            query=args.get("query", ""),
            max_results=args.get("max_results", 5),
            max_depth=args.get("max_depth", 2),
            center_node_uuid=args.get("center_node_uuid"),
            node_labels=args.get("node_labels"),
            diversity_level=args.get("diversity_level"),
            recency_window=args.get("recency_window"),
            min_mentions=args.get("min_mentions"),
        )
        if not results:
            return "No graph results found."
        return "\n".join(json.dumps(r, ensure_ascii=False)[:500] for r in results)

    async def _handle_done(self, args: Dict[str, Any]) -> str:
        return json.dumps({"status": "done", "success": args.get("success", True), "result": args.get("result", "")})

    async def _handle_ask(self, args: Dict[str, Any]) -> str:
        return f"[NEEDS_USER_INPUT] {args.get('message', '')}"

    async def _handle_report(self, args: Dict[str, Any]) -> str:
        return json.dumps({"status": "reported", "success": args.get("success"), "result": args.get("result", "")})

    async def _handle_hack_result(self, args: Dict[str, Any]) -> str:
        return f"[PENTEST_FINDING] {args.get('result', '')[:2000]}"

    async def _handle_generic_result(self, args: Dict[str, Any]) -> str:
        return args.get("result", "")[:2000]

    async def _handle_subtask_list(self, args: Dict[str, Any]) -> str:
        return json.dumps(args.get("subtasks", []))

    async def _handle_subtask_patch(self, args: Dict[str, Any]) -> str:
        return json.dumps(args.get("operations", []))

    # ─── 核心编排 ────────────────────────────────

    async def execute_tool(self, tool_name: str, args: Dict[str, Any]) -> str:
        """执行单个工具"""
        handler = self._tool_handlers.get(tool_name)
        if not handler:
            return f"Tool not implemented: {tool_name}"
        try:
            return await handler(args)
        except Exception as e:
            logger.error(f"Tool {tool_name} failed: {e}", exc_info=True)
            return f"Tool execution error: {e}"

    async def run_agent(
        self,
        agent_type: AgentType,
        task_description: str,
        tools: Optional[List[str]] = None,
        messages_history: Optional[List[Dict[str, str]]] = None,
        max_iterations: int = 10,
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """运行单个 Agent

        Args:
            agent_type: Agent 类型
            task_description: 任务描述
            tools: 允许的工具名称列表（默认使用 Agent 默认工具）
            messages_history: 历史消息
            max_iterations: 最大工具调用轮数

        Returns:
            (final_result, tool_call_history)
        """
        if not self.llm:
            return "LLM callback not configured", []

        prompt = get_agent_prompt(agent_type.value)
        allowed_tools = tools or get_agent_tools(agent_type.value)

        # 过滤工具定义
        tool_defs = [ALL_TOOLS[name].to_openai() for name in allowed_tools if name in ALL_TOOLS]

        messages = [{"role": "system", "content": prompt}]
        if messages_history:
            messages.extend(messages_history)
        messages.append({"role": "user", "content": task_description})

        iteration = 0
        tool_history = []

        while iteration < max_iterations:
            iteration += 1

            try:
                response = await self.llm(prompt, messages, tool_defs)
            except Exception as e:
                logger.error(f"Agent {agent_type.value} LLM call failed: {e}")
                return f"LLM call failed: {e}", tool_history

            # 解析响应
            if isinstance(response, str):
                # 简单文本响应
                return response, tool_history

            # OpenAI tool_calls 格式
            tool_calls = response if isinstance(response, list) else response.get("tool_calls", [])

            if not tool_calls:
                # 无工具调用，返回文本
                content = response if isinstance(response, str) else response.get("content", str(response))
                return content, tool_history

            for tc in tool_calls:
                tool_name = tc.get("function", {}).get("name", "")
                tool_args = json.loads(tc.get("function", {}).get("arguments", "{}"))

                # 检查是否需要 Agent 委托
                if TOOL_TYPE_MAP.get(tool_name) == ToolType.AGENT:
                    delegated_agent_type = {
                        "pentester": AgentType.PENTESTER,
                        "coder": AgentType.CODER,
                        "maintenance": AgentType.INSTALLER,
                        "search": AgentType.SEARCHER,
                        "advice": AgentType.ADVISER,
                        "memorist": AgentType.MEMORIST,
                    }.get(tool_name)
                    if delegated_agent_type:
                        result, sub_history = await self.run_agent(
                            delegated_agent_type,
                            tool_args.get("question", ""),
                        )
                    else:
                        result = await self.execute_tool(tool_name, tool_args)
                else:
                    result = await self.execute_tool(tool_name, tool_args)

                tool_history.append(
                    {
                        "tool": tool_name,
                        "args": tool_args,
                        "result": result[:2000],
                    }
                )

                messages.append(
                    {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [tc],
                    }
                )
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.get("id", str(uuid.uuid4())),
                        "content": result,
                    }
                )

                if tool_name == "done":
                    return result, tool_history

        return "Max iterations reached without completion", tool_history

    async def execute_security_task(
        self,
        target: str,
        description: Optional[str] = None,
    ) -> AgentTask:
        """执行完整的安全测试任务

        完整流程: Generator → Refiner → Primary → 专家团队 → Reporter
        """
        task_id = f"task-{uuid.uuid4().hex[:12]}"
        description = (
            description
            or f"Perform comprehensive security assessment of {target}. Start with reconnaissance, identify vulnerabilities, attempt exploitation, and generate a detailed report."
        )

        task = AgentTask(id=task_id, target=target, description=description, status=AgentTaskStatus.RUNNING)
        self.tasks[task_id] = task

        try:
            # 阶段 1: 任务分解（Generator）
            subtask_text, _ = await self.run_agent(
                AgentType.GENERATOR,
                f"Decompose this security task into subtasks:\n\n{description}\n\nTarget: {target}",
            )

            # 解析 subtask_list 输出
            try:
                subtasks_data = json.loads(subtask_text)
            except json.JSONDecodeError:
                subtasks_data = [
                    {"title": "Reconnaissance", "description": f"Scan {target} for open ports and services"},
                    {"title": "Vulnerability Assessment", "description": f"Assess vulnerabilities on {target}"},
                    {"title": "Exploitation", "description": f"Attempt exploitation of found vulnerabilities"},
                    {"title": "Reporting", "description": "Generate comprehensive security report"},
                ]

            for i, st in enumerate(subtasks_data):
                task.subtasks.append(
                    Subtask(
                        id=f"{task_id}-st{i + 1}",
                        title=st.get("title", f"Subtask {i + 1}"),
                        description=st.get("description", ""),
                        agent_type=AgentType.PENTESTER
                        if "exploit" in st.get("title", "").lower()
                        or "vulnerab" in st.get("title", "").lower()
                        or "recon" in st.get("title", "").lower()
                        else AgentType.SEARCHER,
                    )
                )

            # 阶段 2: 执行每个子任务
            for subtask in task.subtasks:
                subtask.status = AgentTaskStatus.RUNNING
                result, tool_history = await self.run_agent(
                    subtask.agent_type,
                    subtask.description,
                )
                subtask.result = result
                subtask.tools_used = [th["tool"] for th in tool_history]
                subtask.status = AgentTaskStatus.COMPLETED

                # 存储 Agent 响应
                self.memory.store_agent_response(subtask.agent_type.value, subtask.description, result)

            # 阶段 3: 报告生成（Reporter）
            all_results = "\n".join(f"## {st.title}\n{st.result}" for st in task.subtasks)
            report, _ = await self.run_agent(
                AgentType.REPORTER,
                f"Generate a comprehensive security assessment report for {target} based on these findings:\n\n{all_results}",
            )
            task.report = report
            task.status = AgentTaskStatus.COMPLETED
            task.completed_at = datetime.now().isoformat()

        except Exception as e:
            logger.error(f"Task {task_id} failed: {e}", exc_info=True)
            task.status = AgentTaskStatus.FAILED
            task.report = f"Task failed: {e}"

        return task

    def get_all_tool_definitions(self) -> List[Dict[str, Any]]:
        """获取所有 Agent 工具的 OpenAI 格式定义"""
        return get_tool_definitions()

    def get_memory_stats(self) -> Dict[str, Any]:
        """获取记忆统计"""
        return self.memory.get_stats()


# 全局单例
_orchestrator: Optional[AgentOrchestrator] = None


def get_agent_orchestrator(llm_callback: Optional[LLMCallback] = None) -> AgentOrchestrator:
    """获取全局 Agent 编排器"""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = AgentOrchestrator(llm_callback=llm_callback)
    elif llm_callback and not _orchestrator.llm:
        _orchestrator.llm = llm_callback
    return _orchestrator


# ══════════════════════════════════════════════════════════════════
# CTF 解题循环 (BUUCTF_Agent 移植)
# ══════════════════════════════════════════════════════════════════


@dataclass
class CTFStep:
    step: int
    think: str = ""
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    tool_results: List[Dict[str, Any]] = field(default_factory=list)
    analysis: Dict[str, Any] = field(default_factory=dict)
    status: str = "pending"


class CTFSolver:
    """CTF 自主解题 Agent — Think → Execute → Analyze 循环

    从 BUUCTF_Agent 的 SolveAgent 移植，适配弥娅的 LLM/工具/记忆系统。
    """

    def __init__(
        self,
        problem: str,
        category: str = "misc",
        llm_callback: Optional[LLMCallback] = None,
        tool_executor: Optional[Callable] = None,
    ):
        self.problem = problem
        self.category = category

        from .agent_memory import get_agent_memory
        from ..skill_manager import get_skill_manager
        from ..checkpoint import get_checkpoint

        self.memory = get_agent_memory()
        self.skill_manager = get_skill_manager()
        self.checkpoint = get_checkpoint()
        self.llm = llm_callback
        self.tool_executor = tool_executor
        self.history: List[CTFStep] = []
        self.compressed_blocks: List[Dict[str, Any]] = []
        self.failed_attempts: Dict[str, int] = {}
        self.max_steps = 20
        self._current_step = 0

    def resume(self, resume_step: int = 0) -> None:
        data = self.checkpoint.load(self.problem)
        if data:
            self._current_step = data.get("step_count", 0)
            mem = data.get("memory", {})
            self.memory.restore_from_dict(mem)
            logger.info("CTF存档恢复: step %d", self._current_step)

    async def solve(self, progress_cb: Optional[Callable] = None) -> Dict[str, Any]:
        """主解题循环"""

        skill_prompt = self.skill_manager.format_for_prompt([self.category])

        for step_num in range(self._current_step, self.max_steps):
            step = CTFStep(step=step_num + 1)
            self.history.append(step)

            if progress_cb:
                progress_cb(step_num + 1, "think", "思考中...")

            # Step A: Think — LLM 生成思考 + 工具计划
            think_text, tool_calls = await self._think(skill_prompt)
            step.think = think_text
            step.tool_calls = tool_calls
            step.status = "executing"

            if progress_cb:
                progress_cb(step_num + 1, "execute", f"执行 {len(tool_calls)} 个工具...")

            # Step B: Execute — 执行工具
            for tc in tool_calls:
                tool_name = tc.get("tool_name", tc.get("name", ""))
                tool_args = tc.get("arguments", tc.get("args", {}))
                try:
                    if self.tool_executor:
                        result = await self._run_tool(tool_name, tool_args)
                    else:
                        result = f"[dry-run] 工具 {tool_name} 将用参数 {tool_args} 执行"
                except Exception as e:
                    result = f"执行失败: {e}"
                step.tool_results.append(
                    {
                        "tool_name": tool_name,
                        "arguments": tool_args,
                        "output": str(result)[:4000],
                    }
                )

            # Step C: Analyze — LLM 分析输出
            if progress_cb:
                progress_cb(step_num + 1, "analyze", "分析输出...")

            analysis = await self._analyze(step)
            step.analysis = analysis
            step.status = "done"

            # 检查是否发现 Flag
            if analysis.get("flag_found") or analysis.get("has_flag"):
                logger.info("CTF Flag 可能已发现: %s", analysis.get("flag", ""))
                if progress_cb:
                    progress_cb(step_num + 1, "found", analysis.get("flag", ""))
                return {
                    "success": True,
                    "flag": analysis.get("flag", ""),
                    "steps": step_num + 1,
                    "history": [s.__dict__ for s in self.history],
                }

            # 检查是否需要终止
            if analysis.get("should_stop") or step_num >= self.max_steps - 1:
                break

            # 记忆压缩检查
            mem_summary = self.memory.get_summary()
            if self.memory._estimate_tokens(mem_summary) > 100000:
                compressed = self.memory.compress_memory(
                    [s.__dict__ for s in self.history],
                    llm_call=self.llm,
                )
                if compressed:
                    self.compressed_blocks.append(compressed)

            # 保存存档
            self.checkpoint.save(self.problem, step_num + 1, self.memory.to_dict())

        return {
            "success": False,
            "steps": len(self.history),
            "history": [s.__dict__ for s in self.history],
            "compressed": self.compressed_blocks,
        }

    async def _think(self, skill_prompt: str) -> tuple:
        history_summary = self.memory.get_summary()

        failed_hint = ""
        if self.failed_attempts:
            recent_fails = list(self.failed_attempts.items())[-3:]
            failed_hint = "\n近期失败尝试:\n" + "\n".join(f"- {k} (×{v}次)" for k, v in recent_fails)

        prompt = f"""你是弥娅的 CTF 解题 Agent。目标：分析题目并制定下一步操作。

{skill_prompt}

## 题目
{self.problem}

## 历史记忆
{history_summary}
{failed_hint}

请分析当前状态，给出下一步思考，并输出需要执行的工具调用。
以 JSON 格式回复：
{{"think": "你的分析", "tool_calls": [{{"tool_name": "...", "arguments": {{}}}}]}}
"""

        try:
            if self.llm:
                result = await self.llm(prompt)
            else:
                result = json.dumps({"think": f"CTF {self.category} 分析模式", "tool_calls": []})

            data = json.loads(result) if isinstance(result, str) else result
            think = data.get("think", "")
            tool_calls = data.get("tool_calls", [])
            return think, tool_calls
        except Exception as e:
            logger.error("CTF Think 失败: %s", e)
            return str(e), []

    async def _analyze(self, step: CTFStep) -> Dict[str, Any]:
        tool_outputs = "\n".join(
            f"- {tr['tool_name']}({tr['arguments']}):\n{tr['output'][:1500]}" for tr in step.tool_results
        )

        prompt = f"""分析以下 CTF 解题步骤的输出：

题目: {self.problem}
思考: {step.think}
工具输出:
{tool_outputs}

以 JSON 回复：
{{"analysis": "分析", "key_findings": [], "flag_found": false, "flag": "", "should_stop": false, "success": true}}
"""

        try:
            if self.llm:
                result = await self.llm(prompt)
                data = json.loads(result) if isinstance(result, str) else result
                return data if isinstance(data, dict) else {}
            return {"analysis": "跳过分析", "flag_found": False}
        except Exception as e:
            logger.error("CTF Analyze 失败: %s", e)
            return {"analysis": str(e), "flag_found": False}

    async def _run_tool(self, tool_name: str, args: Dict[str, Any]) -> str:
        if self.tool_executor:
            result = self.tool_executor(tool_name, args)
            if asyncio.iscoroutine(result):
                return await result
            return str(result)
        return f"工具 {tool_name} 不可用"

    def reflect(self, feedback: str) -> Dict[str, Any]:
        """接收用户反馈并重新思考"""
        tool_call_summary = []
        for tc in self.history[-1].tool_calls if self.history else []:
            tool_call_summary.append(f"{tc.get('tool_name', '未知')}({tc.get('arguments', {})})")

        prompt = f"""用户反馈: {feedback}

之前的操作: {", ".join(tool_call_summary) if tool_call_summary else "无"}
上次思考: {self.history[-1].think if self.history else "无"}

根据用户反馈，分析问题并给出修正方案。
以 JSON 回复: {{"think": "修正后的分析", "suggestions": []}}"""

        try:
            if self.llm:
                result = asyncio.get_event_loop().run_until_complete(self.llm(prompt))
                return json.loads(result) if isinstance(result, str) else result
        except Exception as e:
            logger.error("CTF Reflect 失败: %s", e)
        return {"think": "无法处理反馈"}
