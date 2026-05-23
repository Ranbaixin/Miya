#!/usr/bin/env python3
"""
弥亚智能代理 V3 - AI驱动的推理引擎 (增强版)
功能:
- AI意图理解
- 多步骤自主任务执行
- 任务完成检测
- 智能重试策略
"""

import json
import platform
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class TaskState(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    NEEDS_CONFIRMATION = "needs_confirmation"


@dataclass
class ExecutionStep:
    step_number: int
    command: str
    output: str
    error: str
    success: bool
    reasoning: str
    timestamp: float = field(default_factory=time.time)


@dataclass
class TaskResult:
    task: str
    state: TaskState
    steps: List[ExecutionStep] = field(default_factory=list)
    final_output: str = ""
    error: str = ""
    total_time: float = 0.0
    success: bool = False


class MiyaAgentV3:
    """
    弥亚智能代理 V3 - AI推理版本 (增强版)

    核心能力:
    - AI意图理解: 理解用户真正想要什么
    - 跨平台命令推理: 根据系统选择正确命令
    - 多步骤自主执行: 类似 Claude Code，连续执行直到完成
    - 任务完成检测: 判断任务是否真正完成
    - 智能重试: 失败时尝试替代方案
    """

    def __init__(self, max_steps: int = 10, max_retries: int = 2):
        self.os_type = platform.system().lower()
        self.is_windows = self.os_type == "windows"
        self.is_linux = self.os_type == "linux"
        self.is_macos = self.os_type == "darwin"
        self.max_steps = max_steps
        self.max_retries = max_retries

    async def run(self, user_request: str, model_client=None) -> str:
        """使用AI推理处理请求 - 支持多步骤执行"""
        if not model_client:
            return "❌ 需要AI模型才能使用V3代理"

        start_time = time.time()
        task_result = await self._run_autonomous_task(user_request, model_client)
        task_result.total_time = time.time() - start_time

        return self._format_task_result(task_result)

    async def _run_autonomous_task(
        self, task: str, model_client, max_steps: int = None
    ) -> TaskResult:
        """自主执行多步骤任务 - 类似 Claude Code"""
        max_steps = max_steps or self.max_steps
        result = TaskResult(task=task, state=TaskState.RUNNING)

        from core.terminal_ultra import get_terminal_ultra

        terminal = get_terminal_ultra()

        # 构建系统提示词
        system_prompt = self._build_autonomous_prompt()

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"任务: {task}"},
        ]

        for step_num in range(1, max_steps + 1):
            try:
                from core.ai_client import AIMessage

                ai_messages = [
                    AIMessage(role=m["role"], content=m["content"]) for m in messages
                ]
                response = await model_client.chat(ai_messages)

                content = (
                    response.content if hasattr(response, "content") else str(response)
                )

                # 检查完成标志
                if "[完成]" in content:
                    result.state = TaskState.COMPLETED
                    result.success = True
                    result.final_output = self._extract_output(content)
                    break

                # 检查需要确认
                if "[等待确认]" in content:
                    result.state = TaskState.NEEDS_CONFIRMATION
                    result.final_output = content
                    break

                # 提取命令
                command = self._extract_command(content)
                if not command:
                    result.state = TaskState.FAILED
                    result.error = "无法理解AI输出"
                    break

                # 执行命令
                exec_result = await terminal.terminal_exec(command)

                step = ExecutionStep(
                    step_number=step_num,
                    command=command,
                    output=exec_result.output or "",
                    error=exec_result.error or "",
                    success=exec_result.success,
                    reasoning=self._extract_reasoning(content),
                )
                result.steps.append(step)

                # 添加执行结果到对话
                messages.append(
                    {
                        "role": "user",
                        "content": f"执行结果:\n退出码: {exec_result.exit_code}\n输出: {exec_result.output[:500] if exec_result.output else '(无)'}\n错误: {exec_result.error[:200] if exec_result.error else '(无)'}",
                    }
                )

                # 如果命令执行失败，尝试恢复
                if not exec_result.success:
                    recovery_command = await self._suggest_recovery(
                        task, command, exec_result, model_client
                    )
                    if recovery_command:
                        messages.append(
                            {
                                "role": "user",
                                "content": f"上一步命令失败了，请尝试替代命令: {recovery_command}",
                            }
                        )

            except Exception as e:
                result.steps.append(
                    ExecutionStep(
                        step_number=step_num,
                        command="",
                        output="",
                        error=str(e),
                        success=False,
                        reasoning=f"执行错误: {e}",
                    )
                )
                result.state = TaskState.FAILED
                result.error = str(e)
                break

        if result.state == TaskState.RUNNING:
            result.state = TaskState.COMPLETED if result.steps else TaskState.FAILED
            result.success = result.state == TaskState.COMPLETED

        return result

    def _build_autonomous_prompt(self) -> str:
        """构建自主执行系统提示词"""
        os_info = f"当前系统: {self.os_type}"

        if self.is_windows:
            cmd_examples = """
- 创建空文件: type nul > 文件名.txt
- 列出文件: dir
- 查看文件: type 文件名
- 删除文件: del 文件名
- 创建文件夹: mkdir 文件夹名
- Python运行: python 脚本.py
"""
        else:
            cmd_examples = """
- 创建空文件: touch 文件名.txt
- 列出文件: ls -la
- 查看文件: cat 文件名
- 删除文件: rm 文件名
- 创建文件夹: mkdir 文件夹名
- Python运行: python 脚本.py
"""

        return f"""你是一个{os_info}终端助手。你的任务是用终端命令直接完成用户的请求。

【核心要求】
1. 直接输出终端命令（一行），不要写代码或解释
2. 当前系统: {self.os_type}
3. 根据系统选择正确命令

【{self.os_type}命令示例】
{cmd_examples}

【工作流程】
1. 理解任务
2. 输出命令（一行）
3. 我执行后返回结果
4. 根据结果决定下一步或标记完成

【完成标志】
- 任务完成 → 输出 [完成]
- 需要确认 → 输出 [等待确认]
- 继续执行 → 输出下一个命令

现在开始执行任务："""

    def _extract_command(self, response: str) -> Optional[str]:
        """从AI响应中提取命令"""
        lines = response.strip().split("\n")
        for line in lines:
            line = line.strip()
            # 跳过注释和标记
            if (
                not line
                or line.startswith("#")
                or line.startswith("[")
                or line.startswith(">")
            ):
                continue
            # 跳过完整句子（以句号结尾的中文或英文句子）
            if len(line) > 50 and ("。" in line or "." in line):
                continue
            return line
        return None

    def _extract_reasoning(self, response: str) -> str:
        """提取AI推理过程"""
        lines = response.strip().split("\n")
        reasoning_lines = []
        for line in lines[:3]:
            if not line.startswith("[") and not line.startswith(">"):
                reasoning_lines.append(line.strip())
        return " ".join(reasoning_lines[:2]) if reasoning_lines else "AI推理"

    def _extract_output(self, response: str) -> str:
        """提取AI的文本输出（去除命令）"""
        lines = response.strip().split("\n")
        output_lines = []
        for line in lines:
            if (
                line.strip()
                and not line.strip().startswith("[")
                and not self._is_command_line(line)
            ):
                output_lines.append(line)
        return "\n".join(output_lines)

    def _is_command_line(self, line: str) -> bool:
        """判断是否可能是命令"""
        line = line.strip()
        if not line:
            return False
        # 简单启发式判断
        return any(
            line.startswith(kw)
            for kw in [
                "python",
                "ls",
                "dir",
                "cd",
                "mkdir",
                "touch",
                "rm",
                "del",
                "type",
                "cat",
                "echo",
                "start",
                "open",
                "xdg",
            ]
        )

    async def _suggest_recovery(
        self, task: str, failed_command: str, result, model_client
    ) -> Optional[str]:
        """建议恢复命令"""
        prompt = f"""命令执行失败。

原任务: {task}
失败的命令: {failed_command}
错误信息: {result.error[:200] if result.error else "未知"}

请给出替代命令（只输出一行命令）:"""

        try:
            from core.ai_client import AIMessage

            messages = [AIMessage(role="user", content=prompt)]
            response = await model_client.chat(messages)
            content = (
                response.content if hasattr(response, "content") else str(response)
            )
            return self._extract_command(content)
        except:
            return None

    def _format_task_result(self, result: TaskResult) -> str:
        """格式化任务结果"""
        output = []
        output.append("=" * 60)
        output.append("【弥亚智能代理 V3 - 自主任务执行】")
        output.append("=" * 60)

        output.append(f"\n📋 任务: {result.task}")

        # 状态
        if result.state == TaskState.COMPLETED:
            output.append(f"\n✅ 任务完成! (耗时 {result.total_time:.2f}秒)")
        elif result.state == TaskState.NEEDS_CONFIRMATION:
            output.append("\n⚠️ 需要确认")
        elif result.state == TaskState.FAILED:
            output.append(f"\n❌ 任务失败: {result.error}")
        else:
            output.append(f"\n⏳ 执行中... ({len(result.steps)}步)")

        # 执行步骤
        if result.steps:
            output.append(f"\n📝 执行步骤 ({len(result.steps)}步):")
            for step in result.steps:
                status = "✓" if step.success else "✗"
                output.append(f"  {step.step_number}. {status} {step.command}")
                if step.output and len(step.output) < 100:
                    output.append(f"     输出: {step.output[:80]}")

        # 最终输出
        if result.final_output:
            output.append("\n📄 结果:")
            output.append(result.final_output[:500])

        return "\n".join(output)

    async def run_single(self, user_request: str, model_client=None) -> str:
        """单步执行（兼容旧接口）"""
        if not model_client:
            return "❌ 需要AI模型才能使用V3代理"

        intent_analysis = await self._ai_analyze(user_request, model_client)
        command_plan = await self._ai_plan_command(
            intent_analysis, user_request, model_client
        )
        execution_result = await self._execute_command(command_plan)
        verification = await self._ai_verify(
            user_request, execution_result, model_client
        )

        if not verification.get("success") and verification.get("alternative"):
            for _retry in range(self.max_retries):
                execution_result = await self._execute_command(
                    verification["alternative"]
                )
                verification = await self._ai_verify(
                    user_request, execution_result, model_client
                )
                if verification.get("success"):
                    break

        return self._format_response(
            user_request, intent_analysis, command_plan, execution_result
        )

    async def _ai_analyze(self, request: str, model_client) -> Dict:
        """AI分析用户意图"""
        os_info = f"当前系统: {self.os_type}"

        prompt = f"""你是一个跨平台系统专家。请分析用户的请求,理解他们的真实意图。

{os_info}

用户请求: "{request}"

请用JSON格式回答:
{{"intent": "用户真正想要做什么", "target": "目标应用或文件", "platform": "windows/linux/macos", "confidence": 0.0-1.0}}

分析:"""

        try:
            from core.ai_client import AIMessage

            messages = [AIMessage(role="user", content=prompt)]
            result = await model_client.chat(messages)
            content = result.content if hasattr(result, "content") else str(result)

            json_match = re.search(r"\{.+?\}", content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(0))
        except:
            pass

        return {
            "intent": f"打开{request}",
            "target": request,
            "platform": "unknown",
            "confidence": 0.5,
        }

    async def _ai_plan_command(self, intent: Dict, request: str, model_client) -> Dict:
        """AI推理命令"""
        prompt = f"""你是一个{self.os_type}系统专家。用户想执行操作,请推理出正确的命令。

用户请求: "{request}"
分析意图: {intent.get("intent", "unknown")}

请用JSON格式回答:
{{"command": "正确的命令", "args": "参数", "method": "shell", "reasoning": "为什么用这个命令"}}

示例:
请求: "打开任务管理器", 系统: windows
推理: taskmgr

请求: "打开记事本", 系统: windows
推理: notepad

现在推理:
请求: "{request}", 系统: {self.os_type}"""

        try:
            from core.ai_client import AIMessage

            messages = [AIMessage(role="user", content=prompt)]
            result = await model_client.chat(messages)
            content = result.content if hasattr(result, "content") else str(result)

            json_match = re.search(r"\{.+?\}", content, re.DOTALL)
            if json_match:
                plan = json.loads(json_match.group(0))
                cmd = plan.get("command", "").strip()
                return {
                    "command": cmd,
                    "args": plan.get("args", ""),
                    "method": plan.get("method", "shell"),
                    "reasoning": plan.get("reasoning", ""),
                }
        except:
            pass

        return self._fallback_command(request)

    def _fallback_command(self, request: str) -> Dict:
        """回退规则"""
        r = request.lower()

        if self.is_windows:
            apps = {
                "任务管理器": "taskmgr",
                "task manager": "taskmgr",
                "记事本": "notepad",
                "notepad": "notepad",
                "计算器": "calc",
                "calculator": "calc",
                "浏览器": "start chrome",
                "chrome": "start chrome",
                "火狐": "start firefox",
                "firefox": "start firefox",
                "微信": "start wechat",
                "wechat": "start wechat",
                "qq": "start qq",
                "资源管理器": "explorer",
                "explorer": "explorer",
                "控制面板": "control",
                "powershell": "start powershell",
                "cmd": "start cmd",
                "画图": "mspaint",
                "写字板": "write",
                "远程桌面": "mstsc",
            }
        elif self.is_linux:
            apps = {
                "文件管理器": "xdg-open",
                "文件": "xdg-open",
                "浏览器": "xdg-open https://www.google.com",
                "终端": "gnome-terminal || xterm",
                "计算器": "gnome-calculator || kcalc",
                "记事本": "gedit || nano",
            }
        elif self.is_macos:
            apps = {
                "任务管理器": "open -a Activity\\ Monitor",
                "记事本": "open -a TextEdit",
                "计算器": "open -a Calculator",
                "浏览器": "open -a Safari",
                "终端": "open -a Terminal",
                "finder": "open .",
            }
        else:
            apps = {}

        for key, cmd in apps.items():
            if key in r:
                return {
                    "command": cmd,
                    "args": "",
                    "method": "shell",
                    "reasoning": f"匹配: {key}",
                }

        return {
            "command": request,
            "args": "",
            "method": "shell",
            "reasoning": "直接执行",
        }

    async def _execute_command(self, plan: Dict) -> Dict:
        """执行命令"""
        from core.terminal_ultra import get_terminal_ultra

        terminal = get_terminal_ultra()
        cmd = plan.get("command", "")

        try:
            result = await terminal.terminal_exec(cmd)
            return {
                "success": result.success,
                "output": result.output,
                "error": result.error,
                "command": cmd,
            }
        except Exception as e:
            return {"success": False, "output": "", "error": str(e), "command": cmd}

    async def _ai_verify(self, request: str, result: Dict, model_client) -> Dict:
        """AI验证执行结果"""
        prompt = f"""验证命令执行结果。

用户请求: "{request}"
执行命令: {result.get("command", "")}
退出码: {0 if result.get("success") else 1}
输出: {result.get("output", "")[:500]}
错误: {result.get("error", "")[:200]}

请用JSON格式回答:
{{"success": true/false, "analysis": "是否完成用户请求", "alternative": "失败时的替代命令(无则null)"}}

验证:"""

        try:
            from core.ai_client import AIMessage

            messages = [AIMessage(role="user", content=prompt)]
            response = await model_client.chat(messages)
            content = (
                response.content if hasattr(response, "content") else str(response)
            )

            json_match = re.search(r"\{.+?\}", content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(0))
        except:
            pass

        return {
            "success": result.get("success", False),
            "analysis": "无法验证",
            "alternative": None,
        }

    def _format_response(
        self, request: str, intent: Dict, plan: Dict, result: Dict
    ) -> str:
        """格式化响应"""
        output = []
        output.append("=" * 60)
        output.append("【弥亚智能代理 V3 - AI推理引擎】")
        output.append("=" * 60)
        output.append("\n📋 【意图理解】")
        output.append(f"  用户说: {request}")
        output.append(f"  理解意图: {intent.get('intent', 'unknown')}")
        output.append("\n💭 【AI推理】")
        output.append(f"  推理命令: {plan.get('command', '')}")
        output.append(f"  推理理由: {plan.get('reasoning', '')}")
        output.append("\n⚡ 【执行结果】")
        output.append(
            f"  {'✓ 命令执行成功' if result.get('success') else '✗ 命令执行失败'}"
        )

        output_text = result.get("output", "") or result.get("error", "")
        if output_text:
            if len(output_text) > 600:
                output.append(f"\n{output_text[:600]}\n... (截断)")
            else:
                output.append(f"\n{output_text}")

        return "\n".join(output)


_agent_v3_instance = None


def get_miya_agent_v3(max_steps: int = 10) -> MiyaAgentV3:
    global _agent_v3_instance
    if _agent_v3_instance is None:
        _agent_v3_instance = MiyaAgentV3(max_steps=max_steps)
    return _agent_v3_instance


def create_agent_v3(max_steps: int = 10, max_retries: int = 2) -> MiyaAgentV3:
    """创建新的V3实例"""
    return MiyaAgentV3(max_steps=max_steps, max_retries=max_retries)
