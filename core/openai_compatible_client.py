"""
OpenAI 兼容客户端基类

提取 OpenAIClient 和 DeepSeekClient 的公共逻辑。
"""

import logging
import json
import re
from typing import Optional, Dict, List, Any, AsyncIterator
from abc import abstractmethod

from .ai_client import BaseAIClient, AIMessage

logger = logging.getLogger(__name__)


class OpenAICompatibleClient(BaseAIClient):
    """
    OpenAI 兼容客户端基类

    提取 OpenAIClient 和 DeepSeekClient 的公共逻辑：
    - 初始化 AsyncOpenAI 客户端
    - 消息转换
    - 工具调用处理
    - 思考过程过滤
    - 流式响应处理
    """

    def __init__(
        self, api_key: str, model: str, base_url: Optional[str] = None, **kwargs
    ):
        super().__init__(api_key, model, **kwargs)
        self.base_url = base_url
        self.client = None
        self._init_client()

    def _init_client(self):
        """初始化 AsyncOpenAI 客户端"""
        try:
            from openai import AsyncOpenAI

            self.client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)
        except ImportError:
            logger.warning("OpenAI库未安装，请运行: pip install openai")
            self.client = None

    @property
    def provider_name(self) -> str:
        """获取 Provider 名称（子类可覆盖）"""
        return "OpenAI"

    async def chat(
        self,
        messages: List[AIMessage],
        tools: Optional[List[Dict]] = None,
        max_iterations: int = 20,
        use_miya_prompt: bool = True,
        tool_choice: str = "auto",
    ) -> str:
        """调用聊天接口（支持工具调用）"""
        if not self.client:
            raise RuntimeError(f"{self.provider_name}客户端未初始化，请安装openai库")

        # 复制消息列表以避免修改原始数据
        if use_miya_prompt:
            messages = self._copy_messages(messages)

        # 使用传入的工具或工具注册表
        if tools is None and self.tool_registry:
            tools = self.tool_registry()

        # 记录日志
        self._log_chat_start(tools, tool_choice)

        iteration = 0
        current_messages = messages.copy()

        while iteration < max_iterations:
            try:
                # 转换为OpenAI格式
                openai_messages = self._convert_messages_to_openai_format(
                    current_messages
                )

                # 构建请求参数
                request_params = self._build_request_params(
                    openai_messages, tools, tool_choice
                )

                # 发送请求
                response = await self._send_request(request_params)

                # 处理响应
                choice = response.choices[0]
                message = choice.message

                # 记录响应日志
                self._log_response(message)

                # 如果没有工具调用，处理纯文本响应
                if not message.tool_calls:
                    return await self._handle_text_response(
                        message, current_messages, tool_choice, iteration
                    )

                # 处理工具调用
                should_continue, result = await self._handle_tool_calls(
                    message, current_messages, tools, tool_choice, iteration
                )

                if not should_continue:
                    return result

                iteration += 1

            except Exception as e:
                logger.error(f"[{self.provider_name}] 请求失败: {e}")
                raise

        # 超过最大迭代次数
        return self._handle_max_iterations_exceeded()

    async def chat_stream(
        self,
        messages: List[AIMessage],
        tools: Optional[List[Dict]] = None,
        max_iterations: int = 20,
        use_miya_prompt: bool = True,
        tool_choice: str = "auto",
    ) -> AsyncIterator[str]:
        """流式聊天（支持工具调用）"""
        if not self.client:
            raise RuntimeError(f"{self.provider_name}客户端未初始化，请安装openai库")

        # 复制消息列表
        if use_miya_prompt:
            messages = self._copy_messages(messages)

        # 使用传入的工具或工具注册表
        if tools is None and self.tool_registry:
            tools = self.tool_registry()

        iteration = 0
        current_messages = messages.copy()

        while iteration < max_iterations:
            try:
                # 转换为OpenAI格式
                openai_messages = self._convert_messages_to_openai_format(
                    current_messages
                )

                # 构建请求参数
                request_params = self._build_request_params(
                    openai_messages, tools, tool_choice
                )
                request_params["stream"] = True

                # 发送流式请求
                response = await self._send_stream_request(request_params)

                # 处理流式响应
                full_content = ""
                tool_calls = []

                async for chunk in response:
                    if not chunk.choices:
                        continue

                    delta = chunk.choices[0].delta

                    # 处理文本内容
                    if delta.content:
                        full_content += delta.content
                        yield delta.content

                    # 处理工具调用
                    if delta.tool_calls:
                        for tc in delta.tool_calls:
                            if len(tool_calls) <= tc.index:
                                tool_calls.append(
                                    {
                                        "id": "",
                                        "type": "function",
                                        "function": {"name": "", "arguments": ""},
                                    }
                                )

                            if tc.id:
                                tool_calls[tc.index]["id"] = tc.id
                            if tc.function:
                                if tc.function.name:
                                    tool_calls[tc.index]["function"]["name"] = (
                                        tc.function.name
                                    )
                                if tc.function.arguments:
                                    tool_calls[tc.index]["function"]["arguments"] += (
                                        tc.function.arguments
                                    )

                # 如果有工具调用，执行工具
                if tool_calls:
                    # 添加助手消息
                    current_messages.append(
                        AIMessage(
                            role="assistant",
                            content=full_content,
                            tool_calls=tool_calls,
                        )
                    )

                    # 执行工具
                    for tc in tool_calls:
                        tool_name = tc["function"]["name"]
                        tool_args = tc["function"]["arguments"]

                        # 执行工具并获取结果
                        tool_result = await self._execute_tool(tool_name, tool_args)

                        # 添加工具结果消息
                        current_messages.append(
                            AIMessage(
                                role="tool", content=tool_result, tool_call_id=tc["id"]
                            )
                        )

                    iteration += 1
                    continue

                # 没有工具调用，结束
                break

            except Exception as e:
                logger.error(f"[{self.provider_name}] 流式请求失败: {e}")
                raise

    def _copy_messages(self, messages: List[AIMessage]) -> List[AIMessage]:
        """复制消息列表"""
        return [
            AIMessage(
                role=msg.role,
                content=msg.content,
                tool_calls=msg.tool_calls,
                tool_call_id=msg.tool_call_id,
            )
            for msg in messages
        ]

    def _log_chat_start(self, tools: Optional[List[Dict]], tool_choice: str):
        """记录聊天开始日志"""
        logger.info(
            f"[{self.provider_name}] 开始聊天 (模型: {self.model})，"
            f"工具数量: {len(tools) if tools else 0}, tool_choice={tool_choice}"
        )

        if tools:
            tool_names = [t.get("function", {}).get("name", "unknown") for t in tools]
            logger.info(f"[{self.provider_name}] 可用工具: {tool_names}")

    def _log_response(self, message):
        """记录响应日志"""
        has_tool_calls = bool(message.tool_calls)
        content_len = len(message.content) if message.content else 0

        logger.info(
            f"[{self.provider_name}] 响应 - "
            f"有工具调用: {has_tool_calls}, content长度: {content_len}"
        )

    def _build_request_params(
        self,
        messages: List[Dict],
        tools: Optional[List[Dict]],
        tool_choice: str,
    ) -> Dict[str, Any]:
        """构建请求参数"""
        params = {
            "model": self.model,
            "messages": messages,
            "temperature": self.config.get("temperature", 0.7),
            "max_tokens": self.config.get("max_tokens", 2000),
        }

        if tools:
            params["tools"] = tools
            params["tool_choice"] = self._normalize_tool_choice(tool_choice)

        return params

    async def _send_request(self, params: Dict[str, Any]):
        """发送请求（子类可覆盖）"""
        return await self.client.chat.completions.create(**params)

    async def _send_stream_request(self, params: Dict[str, Any]):
        """发送流式请求（子类可覆盖）"""
        return await self.client.chat.completions.create(**params)

    async def _execute_tool(self, tool_name: str, tool_args: str) -> str:
        """执行工具（需要子类实现）"""
        raise NotImplementedError("子类需要实现 _execute_tool 方法")

    async def _handle_text_response(
        self,
        message,
        current_messages: List[AIMessage],
        tool_choice: str,
        iteration: int,
    ) -> str:
        """处理纯文本响应"""
        # 提取思考过程
        reasoning_content = getattr(message, "reasoning_content", None) or getattr(
            message, "reasoning", None
        )

        # 检查是否需要强制调用工具
        user_message = self._get_last_user_message(current_messages)
        needs_action = self._check_needs_tool_action(user_message)
        force_retry_count = sum(
            1
            for msg in current_messages
            if msg.role == "user" and "【系统提醒】" in msg.content
        )

        if needs_action and tool_choice == "auto" and force_retry_count < 2:
            logger.info(
                f"[{self.provider_name}] 检测到需要执行操作但AI未调用工具，强制重新请求... "
                f"(重试 {force_retry_count + 1}/2)"
            )
            force_message = AIMessage(
                role="user",
                content="【系统提醒】你刚才没有执行用户请求的操作。请用自然语言描述你正在做什么，不要输出代码格式。",
            )
            current_messages.append(force_message)
            # 返回 None 表示需要重试
            return None

        # 记录工具选择策略问题
        if tool_choice == "required":
            logger.error(
                f"[{self.provider_name}] tool_choice='required'但模型未调用工具，"
                f"可能是工具描述或系统提示词问题"
            )

        # 记录思考过程
        if reasoning_content:
            logger.info(
                f"[{self.provider_name}] 检测到思考过程，长度: {len(reasoning_content)}"
            )

        # 过滤思考过程
        final_content = message.content or ""
        if reasoning_content:
            final_content, thinking_content = self._filter_thinking_content(
                final_content, reasoning_content
            )

            # 打印思考过程到终端
            if thinking_content:
                self._print_thinking(thinking_content)

        return final_content

    async def _handle_tool_calls(
        self,
        message,
        current_messages: List[AIMessage],
        tools: Optional[List[Dict]],
        tool_choice: str,
        iteration: int,
    ) -> tuple[bool, str]:
        """处理工具调用"""
        tool_calls = message.tool_calls
        logger.info(
            f"[{self.provider_name}] AI请求调用工具: {[tc.function.name for tc in tool_calls]}"
        )

        # 添加助手消息
        reasoning_content = getattr(message, "reasoning_content", None) or getattr(
            message, "reasoning", None
        )
        current_messages.append(
            AIMessage(
                role="assistant",
                content=message.content or "",
                tool_calls=[
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in tool_calls
                ],
                reasoning_content=reasoning_content,
            )
        )

        # 执行工具
        for tc in tool_calls:
            tool_name = tc.function.name
            tool_args_str = tc.function.arguments

            # 解析参数
            tool_args = self._fix_json_arguments(tool_args_str)

            # 记录工具调用
            safe_args = self._sanitize_args_for_log(tool_args)
            logger.info(f"[{self.provider_name}] 调用工具: {tool_name}({safe_args})")

            # 执行工具
            try:
                tool_result = await self._execute_tool(tool_name, tool_args_str)
            except Exception as e:
                tool_result = f"工具执行失败: {str(e)}"
                logger.error(f"[{self.provider_name}] 工具执行失败: {e}")

            # 添加工具结果消息
            current_messages.append(
                AIMessage(
                    role="tool",
                    content=tool_result,
                    tool_call_id=tc.id,
                )
            )

        # 检查是否需要继续
        if iteration >= 19:  # 接近最大迭代次数
            logger.warning(f"[{self.provider_name}] 接近最大工具调用次数限制，强制结束")
            return False, self._handle_max_iterations_exceeded()

        return True, None

    def _get_last_user_message(self, messages: List[AIMessage]) -> str:
        """获取最后一条用户消息"""
        for msg in reversed(messages):
            if msg.role == "user" and "【系统提醒】" not in msg.content:
                return msg.content
        return ""

    def _handle_max_iterations_exceeded(self) -> str:
        """处理超过最大迭代次数"""
        from core.text_loader import get_error_message

        return get_error_message("tool_call_limit_exceeded")

    def _print_thinking(self, thinking_content: str):
        """打印思考过程到终端"""
        try:
            from core.terminal_formatter import TerminalFormatter

            thinking_lines = thinking_content.split("\n")[:10]
            print(TerminalFormatter.thinking_block("\n".join(thinking_lines)))
        except ImportError:
            pass

    @abstractmethod
    async def _execute_tool(self, tool_name: str, tool_args: str) -> str:
        """执行工具（子类必须实现）"""
        pass


# 导出
__all__ = ["OpenAICompatibleClient"]
