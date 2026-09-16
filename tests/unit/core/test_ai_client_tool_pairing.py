"""AI 客户端工具循环配对回归测试。

事故：DeepSeek 400 "An assistant message with 'tool_calls' must be followed by
tool messages responding to each 'tool_call_id'"——模型在一条 assistant 消息里
并发多个工具调用时，FINAL/直接返回分支提前 return，未补全 tool 消息，且
最终回复 create 用了丢失 tool_calls/tool_call_id 的有损序列化。
"""

import pytest
from types import SimpleNamespace

from core.ai_client import AIMessage, DeepSeekClient, OpenAIClient


def _tc(call_id, name, args_json='{"message":"x"}'):
    return SimpleNamespace(id=call_id, type="function", function=SimpleNamespace(name=name, arguments=args_json))


def _resp(content=None, tool_calls=None):
    msg = SimpleNamespace(content=content, tool_calls=tool_calls)
    return SimpleNamespace(choices=[SimpleNamespace(message=msg)])


class FakeCompletions:
    """按序弹出预设响应，并记录每次 create 的请求参数"""

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        return self.responses.pop(0)


def _make_client(cls, responses):
    client = cls(api_key="sk-test", model="deepseek-flash", base_url="https://example.com/v1")
    fake = FakeCompletions(responses)
    client.client = SimpleNamespace(chat=SimpleNamespace(completions=fake))
    return client, fake


def _patch_exec(client, results_by_id):
    async def fake_exec(tool_call, tool_context=None):
        return tool_call, results_by_id[tool_call.id]

    client._execute_tool_call = fake_exec


TOOLS = [{"type": "function", "function": {"name": "send_message", "parameters": {"type": "object"}}}]


class TestMultiToolCallPairing:
    @pytest.mark.parametrize("cls", [OpenAIClient, DeepSeekClient])
    async def test_final_after_multiple_tool_calls_keeps_pairing(self, cls):
        """一轮 3 个 tool_calls、最后一个结果带 [FINAL]：三个 tool 消息必须全部补全，
        且最终回复 create 的 payload 保留 tool_calls/tool_call_id 配对（DeepSeek 400 回归）。"""
        client, fake = _make_client(
            cls,
            [
                _resp(tool_calls=[_tc("call_1", "send_message"), _tc("call_2", "send_message"), _tc("call_3", "send_message")]),
                _resp(content="最终回复"),
            ],
        )
        _patch_exec(
            client,
            {"call_1": "已发送", "call_2": "已发送", "call_3": "[FINAL] 消息已发送"},
        )

        result = await client.chat(
            messages=[AIMessage(role="user", content="讲讲修仙")],
            tools=TOOLS,
            use_miya_prompt=False,
        )

        assert result == "最终回复"
        # 第二次 create 是 FINAL 分支的最终回复生成
        final_payload = fake.calls[1]
        msgs = final_payload["messages"]
        assert final_payload["tool_choice"] == "none"
        # 带工具调用的 assistant 消息保留了 tool_calls 字段
        assistants = [m for m in msgs if m["role"] == "assistant" and "tool_calls" in m]
        assert len(assistants) == 1
        assert len(assistants[0]["tool_calls"]) == 3
        # 三个 tool_call_id 都有配对的 tool 消息（无孤儿）
        tool_ids = [m.get("tool_call_id") for m in msgs if m["role"] == "tool"]
        assert sorted(tool_ids) == ["call_1", "call_2", "call_3"]
        assert all(tool_ids)

    async def test_openai_single_tool_call_final_pairs(self):
        """单个 tool_call + FINAL：assistant(tool_calls) 与 tool 消息成对出现。"""
        client, fake = _make_client(
            OpenAIClient,
            [_resp(tool_calls=[_tc("call_1", "send_message")]), _resp(content="好的")],
        )
        _patch_exec(client, {"call_1": "[FINAL] 已发送"})

        result = await client.chat(
            messages=[AIMessage(role="user", content="hi")],
            tools=TOOLS,
            use_miya_prompt=False,
        )
        assert result == "好的"
        msgs = fake.calls[1]["messages"]
        assistants = [m for m in msgs if m["role"] == "assistant" and "tool_calls" in m]
        tools_msgs = [m for m in msgs if m["role"] == "tool"]
        assert len(assistants) == 1 and len(tools_msgs) == 1
        assert tools_msgs[0]["tool_call_id"] == "call_1"


class TestDirectReturnWithSiblings:
    async def test_direct_return_fills_placeholder_for_remaining(self):
        """直接返回工具在同轮还有兄弟调用：补占位 tool 消息后直接返回，不孤儿。"""
        client, fake = _make_client(
            OpenAIClient,
            [
                _resp(
                    tool_calls=[
                        _tc("call_1", "horoscope"),
                        _tc("call_2", "send_message"),
                        _tc("call_3", "send_message"),
                    ]
                )
            ],
        )
        _patch_exec(client, {"call_1": "今日运势：大吉"})

        result = await client.chat(
            messages=[AIMessage(role="user", content="占卜")],
            tools=TOOLS,
            use_miya_prompt=False,
        )
        assert result == "今日运势：大吉"
        # 直接返回，不应再发起第二次 create
        assert len(fake.calls) == 1

    def test_fill_pending_tool_results_helper(self):
        """占位补全辅助方法：从指定下标起为剩余 tool_calls 补 tool 消息。"""
        from core.ai_client import AIMessage

        tcs = [_tc("a", "t1"), _tc("b", "t2"), _tc("c", "t3")]
        current = [AIMessage(role="assistant", content="", tool_calls=[{"id": "a"}])]
        OpenAIClient._fill_pending_tool_results(current, tcs, 1)
        tool_msgs = [m for m in current if m.role == "tool"]
        assert [m.tool_call_id for m in tool_msgs] == ["b", "c"]
        assert all("已跳过" in m.content for m in tool_msgs)


class TestIsAiErrorReply:
    def test_error_prefixes_detected(self):
        from core.ai_client import is_ai_error_reply

        assert is_ai_error_reply("抱歉，AI服务暂时不可用：Error code: 400 ...") is True
        assert is_ai_error_reply("抱歉，工具调用次数过多，无法完成请求。") is True
        assert is_ai_error_reply("抱歉亲爱的，当前模型认证出现问题，可能是密钥已过期。请检查API密钥是否有效~") is True

    def test_normal_reply_not_flagged(self):
        from core.ai_client import is_ai_error_reply

        assert is_ai_error_reply("今天天气不错，出去走走？") is False
        assert is_ai_error_reply("抱歉来晚了，刚看到消息") is False
        assert is_ai_error_reply("") is False
        assert is_ai_error_reply(None) is False
