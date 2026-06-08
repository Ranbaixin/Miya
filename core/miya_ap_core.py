"""
弥娅 v10.0 认知核心 — APV2.1 驱动的一等公民

⚠️ DEPRECATED (2026-06-08):
  此模块已被 MiyaPsyArchBridge (core/miya_psyarch_bridge.py) 统一替代。
  MiyaAPCore 从未被任何生产代码使用，保留仅作设计参考。
  所有新功能请直接在 MiyaPsyArchBridge 中扩展。

APV2.1 Runtime 是弥娅的唯一认知引擎。
此模块负责:
1. 包装 MiyaEngine 为标准 process_message API
2. 桥接 AP MemoryStore ↔ MiyaMemoryCore (双向同步)
3. 整合 ToolNet → ActionPlanner (工具作为行动选项)
4. 建立 Education 反馈闭环 (对话 → 教学 → 下次Tick)
5. 接入平台适配器 (多平台统一的对话入口)
"""

from __future__ import annotations

import asyncio
import logging
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional

logger = logging.getLogger("miya.ap_core")


@dataclass
class MiyaResponse:
    """弥娅的标准响应"""

    text: str
    soul_state: dict[str, Any] = field(default_factory=dict)
    emotion_nt: dict[str, float] = field(default_factory=dict)
    feelings: dict[str, float] = field(default_factory=dict)
    focus_labels: list[str] = field(default_factory=list)
    memory_recalled: list[str] = field(default_factory=list)
    latency_ms: float = 0.0
    model: str = ""


class MiyaAPCore:
    """
    弥娅 v10.0 认知核心

    AP Runtime 是唯一的认知引擎。所有感知、记忆、情感、
    决策、生成都通过 AP 的 StatePool 统一进行。
    """

    def __init__(
        self,
        *,
        personality_form: str = "default",
        enable_cortex: bool = True,
        enable_heartbeat: bool = True,
        heartbeat_interval: float = 5.0,
        enable_education: bool = True,
        enable_tools: bool = True,
    ):
        self._personality_form = personality_form
        self._enable_cortex = enable_cortex
        self._enable_heartbeat = enable_heartbeat
        self._heartbeat_interval = heartbeat_interval
        self._enable_education = enable_education
        self._enable_tools = enable_tools

        self._engine: Any = None
        self._initialized = False
        self._start_time = time.time()

        # 平台回调
        self._response_callback: Optional[Callable] = None

        # 心跳线程
        self._heartbeat_thread: Optional[threading.Thread] = None
        self._heartbeat_running = False

        # 统计
        self._message_count: int = 0
        self._total_latency_ms: float = 0.0
        self._tool_calls: int = 0

        # 工具注册表
        self._tool_registry: dict[str, Any] = {}

        # Education 累积
        self._education_buffer: list[dict] = []
        self._last_response: str = ""
        self._last_user_input: str = ""

        # 人设缓存
        self._persona: dict[str, Any] | None = None

    # ===== 生命周期 =====

    def start(self) -> "MiyaAPCore":
        self._warmup()
        self._init_engine()
        self._init_memory_bridge()
        self._init_tools()
        self._init_backfill()

        if self._enable_heartbeat:
            self._start_heartbeat()

        self._initialized = True
        logger.info("弥娅 AP 认知核心启动完成 ✓")
        return self

    def _warmup(self) -> None:
        """预热：Jieba 分词 + AI 客户端预连接"""
        try:
            import jieba

            jieba.lcut("弥娅 在 这里 等 佳")
            logger.info("  ✓ Jieba 预热完成")
        except Exception:
            pass

        if self._enable_cortex:
            try:
                from core.model_pool_manager import get_model_pool

                get_model_pool()
                logger.info("  ✓ 模型池预热完成")
            except Exception:
                pass

        self._init_engine()
        self._init_memory_bridge()
        self._init_tools()

        if self._enable_heartbeat:
            self._start_heartbeat()

        self._initialized = True
        logger.info("弥娅 AP 认知核心启动完成 ✓")
        return self

    def stop(self) -> None:
        """停止认知核心"""
        self._heartbeat_running = False
        if hasattr(self, "_backfill") and self._backfill:
            self._backfill.stop()
        if self._heartbeat_thread:
            self._heartbeat_thread.join(timeout=2.0)
        self._save_state()
        self._initialized = False
        logger.info("弥娅 AP 认知核心已停止")

    def _init_engine(self) -> None:
        """初始化 APV2.1 引擎"""
        try:
            from miya_psyarch.engine import MiyaEngine

            self._engine = MiyaEngine(
                trace_mode="summary",
                enable_cortex=self._enable_cortex,
                personality_form=self._personality_form,
            )
            self._engine.start()
            logger.info("  ✓ APV2.1 引擎就绪")
        except Exception as e:
            logger.error(f"AP 引擎初始化失败: {e}")
            raise

    def _init_memory_bridge(self) -> None:
        """初始化记忆桥接 —— AP StatePool ↔ MiyaMemoryCore 双向同步"""
        try:
            from miya_psyarch.memory.miya_memory_bridge import get_memory_bridge

            bridge = get_memory_bridge()
            bridge.warmup(limit=50)
            logger.info("  ✓ 记忆桥接就绪")
        except Exception as e:
            logger.warning(f"记忆桥接初始化跳过: {e}")

    def _init_tools(self) -> None:
        """初始化工具注册表 —— ToolNet 工具接入 ActionPlanner"""
        if not self._enable_tools:
            return
        try:
            from webnet.ToolNet.registry import get_tool_registry

            self._tool_registry = get_tool_registry() or {}
        except ImportError:
            logger.info("  ✓ 工具注册表跳过 (ToolNet registry 不可用)")
        except Exception as e:
            logger.warning("工具注册表初始化跳过: " + str(e))
        else:
            logger.info("  ✓ 工具注册表就绪 (" + str(len(self._tool_registry)) + " 工具)")

    def _init_backfill(self) -> None:
        """初始化记忆回填 —— 从 SQLite/JSON 批量注入历史记忆到 StatePool"""
        try:
            from core.memory_backfill import MemoryBackfill

            self._backfill = MemoryBackfill(ap_engine=self._engine)
            n = self._backfill.load_recent_conversations(limit=100)
            c = self._backfill.load_cognitive_memories(limit=50)
            self._backfill.start_incremental(interval=30.0, batch=10)
            logger.info("  ✓ 记忆回填就绪 (" + str(n) + " 对话 + " + str(c) + " 认知)")
        except Exception as e:
            logger.warning("记忆回填跳过: " + str(e))
            self._backfill = None

    def _start_heartbeat(self) -> None:
        """启动 AP 心跳 —— 持续的自主认知"""
        self._heartbeat_running = True

        def _loop():
            logger.info(f"AP 心跳已启动 (间隔 {self._heartbeat_interval}s)")
            while self._heartbeat_running:
                try:
                    if self._engine:
                        # 空闲 tick
                        idle_state = self._engine.idle_tick()

                        # 检查主动说话
                        if idle_state and idle_state.get("has_active_intent") and self._response_callback:
                            response = self._engine._generate_proactive_message()
                            if response:
                                self._response_callback(response)
                                logger.info(f"主动说话: {response[:50]}...")

                except Exception as e:
                    logger.debug(f"心跳异常: {e}")
                threading.Event().wait(self._heartbeat_interval)

        self._heartbeat_thread = threading.Thread(target=_loop, daemon=True)
        self._heartbeat_thread.start()

    def _save_state(self) -> None:
        """保存引擎状态"""
        try:
            if self._engine and hasattr(self._engine, "_ticks"):
                stats = {
                    "tick_count": len(self._engine._ticks),
                    "message_count": self._message_count,
                    "avg_latency_ms": self._total_latency_ms / max(self._message_count, 1),
                    "tool_calls": self._tool_calls,
                }
                logger.info(f"状态已保存: {stats}")
        except Exception:
            pass

    # ===== 消息处理 API =====

    def process_message(
        self,
        content: str,
        *,
        platform: str = "terminal",
        user_id: str = "default",
        sender_name: str = "用户",
        group_id: str = "",
        extra_context: dict[str, Any] | None = None,
    ) -> MiyaResponse:
        """
        处理一条消息 —— AP 认知 + LLM 渲染
        """
        if not self._initialized:
            self.start()

        t0 = time.perf_counter()
        self._message_count += 1

        # Step 1: AP 认知 tick
        education_interventions = []
        if self._enable_education and self._message_count > 1:
            education_interventions = self._build_education_feedback()

        trace = self._engine.tick(
            text=content,
            education_interventions=education_interventions if education_interventions else None,
        )

        # Step 2: 记忆提取 + 增强上下文
        self._engine._tick_memory_context(content)
        memory_recalled = self._extract_recalled_memories(trace)

        # Step 3: LLM 渲染 — 使用增强的 Cortex prompt
        if self._enable_cortex:
            soul = self._engine._current_soul
            response_text = self._render_with_enhanced_prompt(content, soul, memory_recalled)
        else:
            soul = self._engine._current_soul
            response_text = self._extract_ap_text(trace)

        # Step 4: 教育反馈闭环
        if self._enable_education and response_text:
            self._engine._generate_education(content, response_text)
            self._accumulate_education(content, response_text)

        latency_ms = (time.perf_counter() - t0) * 1000
        self._total_latency_ms += latency_ms

        # Step 5: 记忆写入
        self._save_conversation_to_memory(content, response_text, user_id, platform)

        # Step 6: 工具检测
        response_text, tool_used = self._handle_tool_calls(response_text)
        if tool_used:
            self._tool_calls += 1

        return MiyaResponse(
            text=response_text,
            soul_state=self._extract_soul_dict(soul),
            emotion_nt=getattr(soul, "emotion_nt", {}),
            feelings=getattr(soul, "feelings", {}),
            focus_labels=getattr(soul, "focus_labels", []),
            memory_recalled=memory_recalled,
            latency_ms=latency_ms,
            model=getattr(soul, "llm_model", "AP"),
        )

    def process_message_async(
        self,
        content: str,
        **kwargs,
    ) -> MiyaResponse:
        """同步包装的异步处理"""
        return self.process_message(content, **kwargs)

    # ===== 内部辅助 =====

    def _extract_soul_dict(self, soul: Any) -> dict[str, Any]:
        if soul is None:
            return {}
        return {
            "tick_index": getattr(soul, "tick_index", 0),
            "focus_labels": getattr(soul, "focus_labels", []),
            "focus_texts": getattr(soul, "focus_texts", []),
            "feelings": getattr(soul, "feelings", {}),
            "miya_feelings": getattr(soul, "miya_feelings", {}),
            "emotion_nt": getattr(soul, "emotion_nt", {}),
            "has_active_intent": getattr(soul, "has_active_intent", False),
        }

    def _extract_recalled_memories(self, trace: dict) -> list[str]:
        memories = []
        try:
            att_items = trace.get("attention", {}).get("selected_items", [])
            for item in att_items[:5]:
                if str(item.get("family", "")).startswith("miya_memory"):
                    content = item.get("anchor_meta", {}).get("full_content", "") or item.get("display_text", "")
                    if content:
                        memories.append(content[:100])
        except Exception:
            pass
        return memories

    def _extract_ap_text(self, trace: dict) -> str:
        """纯 AP 模式：从状态提取文本"""
        try:
            tops = trace.get("state_snapshot", {}).get("top_items", [])[:5]
            texts = [t.get("display_text", "") for t in tops if t.get("display_text")]
            if texts:
                return "当前思绪: " + "; ".join(texts)
        except Exception:
            pass
        return "..."

    # ===== 增强 prompt 构建 =====

    def _render_with_enhanced_prompt(self, user_message: str, soul: Any, recalled: list[str]) -> str:
        """用增强 prompt 调用 LLM —— 注入完整的 AP 认知状态"""
        try:
            engine = self._engine
            if not engine or not engine._cortex:
                return engine._render_response(user_message)

            cortex = engine._cortex
            nt = soul.emotion_nt if hasattr(soul, "emotion_nt") else {}
            feelings = soul.miya_feelings if hasattr(soul, "miya_feelings") else {}
            focus = soul.focus_labels[:5] if hasattr(soul, "focus_labels") else []

            system_prompt = self._build_rich_prompt(nt, feelings, focus, recalled)

            from miya_psyarch.cortex.llm_cortex import CortexResult

            import asyncio

            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
            result = loop.run_until_complete(cortex.render(system_prompt=system_prompt, user_message=user_message))
            if isinstance(result, CortexResult):
                return result.text
            return str(result)

        except Exception as e:
            logger.warning("增强 prompt 失败, 降级: " + str(e))
            return self._engine._render_response(user_message)

    def _build_rich_prompt(
        self,
        nt: dict[str, float],
        feelings: dict[str, float],
        focus: list[str],
        recalled: list[str],
    ) -> str:
        """从 YAML 人设 + AP 状态构建 system prompt"""
        persona = getattr(self, "_persona", None)
        if persona is None:
            from core.persona_loader import load_persona

            self._persona = load_persona(self._personality_form)
            persona = self._persona

        from core.persona_loader import build_system_prompt

        return build_system_prompt(
            persona=persona,
            nt=nt,
            feelings=feelings,
            recalled=recalled,
        )

    # ===== Education 闭环 =====

    def _build_education_feedback(self) -> list[dict]:
        """基于上一轮对话构建 Education 干预"""
        if not self._last_user_input or not self._last_response:
            return []
        return [
            {
                "type": "conversation_feedback",
                "user_input": self._last_user_input[:200],
                "assistant_response": self._last_response[:300],
                "intent": "improve_naturalness",
            }
        ]

    def _accumulate_education(self, user_input: str, response: str) -> None:
        """积累本轮对话，供下一轮 Education 使用"""
        self._last_user_input = user_input
        self._last_response = response

        # 自动生成 cognitive_memory
        if len(response) > 30 and self._message_count % 5 == 0:
            try:
                self._save_cognitive_memory(user_input, response)
            except Exception:
                pass

    def _save_cognitive_memory(self, user_input: str, response: str) -> None:
        """自动生成认知记忆条目"""
        import json
        from pathlib import Path
        from datetime import datetime
        import uuid

        path = Path("data/memory/cognitive_memories.json")
        if not path.exists():
            return

        try:
            with open(path, "r", encoding="utf-8") as f:
                memories = json.load(f)
        except Exception:
            memories = []

        entry = {
            "id": uuid.uuid4().hex[:16],
            "timestamp": datetime.now().isoformat(),
            "user_id": "auto",
            "thinking": "弥娅在AP认知循环中自然生成的回应。用户说: " + user_input[:100],
            "emotions": {},
            "inner_thought": response[:80],
            "attribution": "自然对话",
            "reflection": "这是弥娅对" + user_input[:30] + "的真实回应",
        }

        memories.append(entry)
        if len(memories) > 200:
            memories = memories[-200:]

        with open(path, "w", encoding="utf-8") as f:
            json.dump(memories, f, ensure_ascii=False, indent=2)

    def _save_conversation_to_memory(self, user_input: str, response: str, user_id: str, platform: str) -> None:
        """保存对话到记忆系统"""
        try:
            from memory import store_dialogue

            asyncio.get_event_loop().run_until_complete(
                store_dialogue(
                    content=user_input,
                    user_id=user_id,
                    platform=platform,
                    role="user",
                    tags=["ap_dialogue"],
                )
            )
            if response:
                asyncio.get_event_loop().run_until_complete(
                    store_dialogue(
                        content=response,
                        user_id="miya",
                        platform=platform,
                        role="assistant",
                        tags=["ap_response"],
                    )
                )
        except Exception as e:
            logger.debug(f"记忆写入跳过: {e}")

    def _handle_tool_calls(self, response: str) -> tuple[str, bool]:
        """检测并处理响应中的工具调用"""
        if not self._enable_tools or not self._tool_registry:
            return response, False

        import re

        tool_pattern = re.compile(r"\[\[tool:(\w+)\((.*?)\)\]\]")
        match = tool_pattern.search(response)

        if match:
            tool_name = match.group(1)
            tool_args = match.group(2)
            if tool_name in self._tool_registry:
                try:
                    result = self._tool_registry[tool_name].execute(tool_args)
                    processed = tool_pattern.sub(f"[工具结果: {result[:200]}]", response)
                    return processed, True
                except Exception as e:
                    logger.warning(f"工具调用失败 [{tool_name}]: {e}")

        return response, False

    # ===== 状态查询 =====

    def get_status(self) -> dict[str, Any]:
        return {
            "version": "10.0.0",
            "engine": "APV2.1",
            "initialized": self._initialized,
            "uptime_s": time.time() - self._start_time,
            "message_count": self._message_count,
            "avg_latency_ms": self._total_latency_ms / max(self._message_count, 1),
            "tool_calls": self._tool_calls,
            "cortex_enabled": self._enable_cortex,
            "heartbeat_running": self._heartbeat_running,
            "personality": self._personality_form,
        }

    def get_soul_state(self) -> dict[str, Any]:
        """获取当前灵魂状态"""
        if self._engine and hasattr(self._engine, "_current_soul"):
            return self._extract_soul_dict(self._engine._current_soul)
        return {}

    def set_personality(self, form: str) -> None:
        """切换人格"""
        self._personality_form = form
        self._persona = None  # 清除缓存，下次重新加载
        from core.persona_loader import clear_cache

        clear_cache()
        if self._engine and hasattr(self._engine, "set_form"):
            self._engine.set_form(form)

    def train_skill(self, skill_name: str, teacher_mode: str = "auto") -> dict:
        """训练一项技能"""
        try:
            from miya_psyarch.trainer import MiyaTrainer

            trainer = MiyaTrainer(self._engine)
            result = trainer.train_skill(
                skill_name=skill_name,
                teacher_name="LLMTeacher",
                stages=["demonstrate", "strong_scaffold", "weak_scaffold", "feedback_only"],
            )
            return {"success": True, "result": str(result)[:500]}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def on_response(self, callback: Callable) -> None:
        """设置响应回调（心跳/主动说话时调用）"""
        self._response_callback = callback


# ===== 全局单例 =====

_ap_core: Optional[MiyaAPCore] = None


def get_ap_core(
    *,
    personality_form: str = "default",
    enable_cortex: bool = True,
    enable_heartbeat: bool = True,
    enable_education: bool = True,
    enable_tools: bool = True,
) -> MiyaAPCore:
    """获取 AP 认知核心单例"""
    global _ap_core
    if _ap_core is None:
        _ap_core = MiyaAPCore(
            personality_form=personality_form,
            enable_cortex=enable_cortex,
            enable_heartbeat=enable_heartbeat,
            enable_education=enable_education,
            enable_tools=enable_tools,
        )
    return _ap_core


def reset_ap_core() -> None:
    global _ap_core
    if _ap_core:
        _ap_core.stop()
    _ap_core = None
