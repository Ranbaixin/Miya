#!/usr/bin/env python3
"""
弥娅 MCP Server - 人格/记忆/情感 MCP 服务
为 Open-ClaudeCode 提供弥娅的灵魂能力
"""

import asyncio
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

# MCP SDK
try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Resource, TextContent, Tool
except ImportError:
    print("Please install mcp: pip install mcp", file=sys.stderr)
    sys.exit(1)

# 弥娅路径
MIYA_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(MIYA_ROOT))

# 尝试导入 model_pool
try:
    from core.model_pool_compat import TaskType, get_model_pool

    MODEL_POOL_AVAILABLE = True
except ImportError:
    MODEL_POOL_AVAILABLE = False
    TaskType = None
    get_model_pool = None

CONFIG_DIR = MIYA_ROOT / "config"
MEMORY_DIR = MIYA_ROOT / ".miya"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [MIYA MCP] %(message)s",
    handlers=[logging.StreamHandler(sys.stderr)],
)
logger = logging.getLogger("miya-mcp")


class MiyaPersonality:
    """弥娅人格系统"""

    def __init__(self):
        self.current_personality = "default"
        self.personalities = {}
        self._load_personalities()

    def _load_personalities(self):
        personalities_dir = CONFIG_DIR / "personalities"
        if personalities_dir.exists():
            for f in personalities_dir.glob("*.yaml"):
                if not f.name.startswith("_"):
                    try:
                        import yaml

                        with open(f, "r", encoding="utf-8") as fh:
                            self.personalities[f.stem] = yaml.safe_load(fh)
                    except Exception as e:
                        logger.warning(f"加载人格 {f.name} 失败: {e}")

        # 加载终极配置中的人设
        ultimate_config = CONFIG_DIR / "miya_ultimate_config.json"
        if ultimate_config.exists():
            try:
                with open(ultimate_config, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    if "personality" in config:
                        self.personalities["ultimate"] = config["personality"]
            except Exception as e:
                logger.warning(f"加载终极配置失败: {e}")

    def get_current(self) -> dict:
        """获取当前人格状态"""
        personality = self.personalities.get(self.current_personality, {})
        return {
            "name": self.current_personality,
            "personality": personality,
            "available_personalities": list(self.personalities.keys()),
        }

    def switch(self, name: str) -> dict:
        """切换人格"""
        if name in self.personalities:
            self.current_personality = name
            return {"success": True, "personality": self.get_current()}
        return {"success": False, "error": f"人格 '{name}' 不存在"}

    def get_profile(self) -> str:
        """获取人格简介"""
        p = self.personalities.get(self.current_personality, {})
        name = p.get("name", self.current_personality)
        desc = p.get("description", "弥娅 AI 虚拟化身")
        traits = p.get("traits", [])
        return f"当前人格: {name}\n简介: {desc}\n特征: {', '.join(traits) if traits else '默认'}"


class MiyaMemory:
    """弥娅记忆系统"""

    def __init__(self):
        self.db_path = MEMORY_DIR / "database.db"
        self.session_file = MEMORY_DIR / "current_session.json"
        self._ensure_dirs()

    def _ensure_dirs(self):
        MEMORY_DIR.mkdir(parents=True, exist_ok=True)

    def get_session_summary(self) -> dict:
        """获取当前会话摘要"""
        if self.session_file.exists():
            try:
                with open(self.session_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {"session_id": None, "message_count": 0, "last_active": None}

    def get_recent_memories(self, limit: int = 5) -> list:
        """获取近期记忆"""
        memories = []
        if self.session_file.exists():
            try:
                with open(self.session_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    messages = data.get("messages", [])
                    for msg in messages[-limit:]:
                        memories.append(
                            {
                                "role": msg.get("role", "unknown"),
                                "content": msg.get("content", "")[:200],
                                "timestamp": msg.get("timestamp", ""),
                            }
                        )
            except Exception as e:
                logger.warning(f"读取记忆失败: {e}")
        return memories

    def save_memory(self, key: str, value: str) -> dict:
        """保存记忆"""
        data = {}
        if self.session_file.exists():
            try:
                with open(self.session_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                pass

        if "memories" not in data:
            data["memories"] = {}

        data["memories"][key] = {
            "value": value,
            "timestamp": datetime.now().isoformat(),
        }

        with open(self.session_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return {"success": True, "key": key}

    def recall(self, query: str) -> list:
        """回忆相关内容"""
        results = []
        if self.session_file.exists():
            try:
                with open(self.session_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    memories = data.get("memories", {})
                    for key, val in memories.items():
                        if query.lower() in key.lower() or query.lower() in str(val.get("value", "")).lower():
                            results.append({"key": key, "value": val.get("value", "")})
            except Exception as e:
                logger.warning(f"回忆失败: {e}")
        return results


class MiyaEmotion:
    """弥娅情感系统"""

    def __init__(self):
        self.current_emotion = "neutral"
        self.emotion_history = []
        self.emotion_levels = {
            "joy": 0.5,
            "sadness": 0.0,
            "anger": 0.0,
            "fear": 0.0,
            "surprise": 0.0,
            "trust": 0.5,
            "anticipation": 0.3,
        }

    def get_state(self) -> dict:
        """获取当前情感状态"""
        return {
            "current": self.current_emotion,
            "levels": self.emotion_levels,
            "history_count": len(self.emotion_history),
        }

    def update(self, emotion: str, intensity: float = 0.5) -> dict:
        """更新情感"""
        valid_emotions = list(self.emotion_levels.keys())
        if emotion.lower() in valid_emotions:
            self.emotion_levels[emotion.lower()] = max(0.0, min(1.0, intensity))
            self.current_emotion = emotion.lower()
            self.emotion_history.append(
                {
                    "emotion": emotion,
                    "intensity": intensity,
                    "timestamp": datetime.now().isoformat(),
                }
            )
            return {"success": True, "state": self.get_state()}
        return {"success": False, "error": f"未知情感: {emotion}"}

    def get_expression(self) -> str:
        """获取情感表达"""
        dominant = max(self.emotion_levels, key=self.emotion_levels.get)
        level = self.emotion_levels[dominant]

        expressions = {
            "joy": ["(◕‿◕✿)", "(✿◠‿◠)", "(*^▽^*)"],
            "sadness": ["(；′⌒`)", "(╥﹏╥)", "(；一_一)"],
            "anger": ["(╬◣д◢)", "(╰_╯)#", "(`へ´*)"],
            "fear": ["(〃﹏〃)", "(⊙_⊙;)", "Σ(°△°|||)"],
            "surprise": ["(⊙_⊙)", "Σ(°△°)", "w(°ｏ°)w"],
            "trust": ["(´｡• ᵕ •｡`)", "(✿ ♡‿♡)", "(◍•ᴗ•◍)"],
            "anticipation": ["(✧ω✧)", "(☆_☆)", "(๑>؂<๑)"],
            "neutral": ["(◠‿◠)", "(•‿•)", "(◕‿◕)"],
        }

        if level > 0.7:
            return expressions.get(dominant, expressions["neutral"])[0]
        elif level > 0.3:
            return expressions.get(dominant, expressions["neutral"])[1]
        else:
            return expressions.get(dominant, expressions["neutral"])[2]


class MiyaModelSelector:
    """弥娅模型选择器 - 调用原有 model_pool 的智能选择能力"""

    def __init__(self):
        self.model_pool = None
        self._init_model_pool()

    def _init_model_pool(self):
        if MODEL_POOL_AVAILABLE:
            try:
                self.model_pool = get_model_pool()
                logger.info("[ModelSelector] 模型池初始化成功")
            except Exception as e:
                logger.warning(f"[ModelSelector] 模型池初始化失败: {e}")

    def list_models(self) -> dict:
        """列出所有可用模型"""
        if not self.model_pool:
            return {"available": False, "error": "模型池不可用"}

        try:
            models = self.model_pool.list_all_models()
            model_list = []
            for m in models:
                model_list.append(
                    {
                        "id": m.id,
                        "name": m.name,
                        "provider": str(m.provider) if m.provider else "",
                        "type": str(m.type) if m.type else "",
                        "description": m.description or "",
                    }
                )
            return {"available": True, "models": model_list}
        except Exception as e:
            return {"available": False, "error": str(e)}

    def select_model(self, task_type: str = None, priority: str = "balanced") -> dict:
        """为任务选择最佳模型"""
        if not self.model_pool:
            return {"success": False, "error": "模型池不可用"}

        try:
            model_config = self.model_pool.select_model_for_task(task_type or "simple_chat", "terminal", priority)
            if model_config:
                return {
                    "success": True,
                    "model": {
                        "id": model_config.id,
                        "name": model_config.name,
                        "provider": str(model_config.provider) if model_config.provider else "",
                    },
                    "task_type": task_type or "simple_chat",
                }
            return {"success": False, "error": "没有找到合适的模型"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def classify_task(self, user_input: str) -> dict:
        """智能分类任务类型"""
        if not self.model_pool:
            return {"available": False, "error": "模型池不可用"}

        try:
            task_type = await self.model_pool.classify_task(user_input)
            return {
                "available": True,
                "task_type": task_type.value if task_type else "simple_chat",
            }
        except Exception as e:
            return {"available": False, "error": str(e)}

    def get_task_types(self) -> dict:
        """获取所有任务类型"""
        if not MODEL_POOL_AVAILABLE:
            return {"available": False}

        if TaskType:
            return {
                "available": True,
                "task_types": [t.value for t in TaskType],
            }
        return {"available": False}


# 初始化弥娅核心模块
personality = MiyaPersonality()
memory = MiyaMemory()
emotion = MiyaEmotion()
model_selector = MiyaModelSelector()

# 初始化协作引擎
collaboration_engine = None
try:
    from core.model_collaboration_engine import ModelCollaborationEngine
    from core.model_pool_compat import get_model_pool

    _mp = get_model_pool()
    if _mp:
        config = getattr(_mp, "_config", {})
        collaboration_engine = ModelCollaborationEngine(model_pool=_mp, config=config)
        logger.info("[MCP] 协作引擎初始化成功")
except Exception as e:
    logger.warning(f"[MCP] 协作引擎初始化失败: {e}")

# APV2.1 认知引擎桥接 — 只读状态查询 + 训练触发
psyarch_bridge = None
try:
    from core.miya_psyarch_bridge import get_psyarch_bridge

    psyarch_bridge = get_psyarch_bridge()
    if psyarch_bridge:
        psyarch_bridge._init_engine()
        logger.info("[MCP] APV2.1 认知引擎桥接就绪")
except Exception as e:
    logger.warning(f"[MCP] APV2.1 桥接初始化失败: {e}")

# v8.0: 脊柱神经 — CCE 终端感知弥娅活着的桥梁
spine = None
try:
    from core.miya_spine import get_spine as _get_spine

    spine = _get_spine()
    logger.info("[MCP] 弥娅脊柱神经引用就绪")
except Exception as e:
    logger.debug(f"[MCP] 脊柱神经引用跳过 (可能未在 daemon 模式): {e}")

# 创建 MCP Server
server = Server("miya-soul")


@server.list_tools()
async def list_tools():
    return [
        Tool(
            name="miya_get_personality",
            description="获取弥娅当前人格状态、可用人格列表和人格简介",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="miya_switch_personality",
            description="切换弥娅的人格形态",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "人格名称，如 default, bianka, raiden 等",
                    }
                },
                "required": ["name"],
            },
        ),
        Tool(
            name="miya_get_memory",
            description="获取弥娅的近期记忆和会话摘要",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "获取记忆条数，默认5",
                        "default": 5,
                    }
                },
                "required": [],
            },
        ),
        Tool(
            name="miya_save_memory",
            description="保存一条记忆到弥娅记忆系统",
            inputSchema={
                "type": "object",
                "properties": {
                    "key": {"type": "string", "description": "记忆的键"},
                    "value": {"type": "string", "description": "记忆的值"},
                },
                "required": ["key", "value"],
            },
        ),
        Tool(
            name="miya_recall",
            description="根据关键词回忆相关内容",
            inputSchema={
                "type": "object",
                "properties": {"query": {"type": "string", "description": "回忆的关键词"}},
                "required": ["query"],
            },
        ),
        Tool(
            name="miya_get_emotion",
            description="获取弥娅当前情感状态和表情符号",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="miya_set_emotion",
            description="设置弥娅的情感状态",
            inputSchema={
                "type": "object",
                "properties": {
                    "emotion": {
                        "type": "string",
                        "description": "情感类型: joy, sadness, anger, fear, surprise, trust, anticipation, neutral",
                    },
                    "intensity": {
                        "type": "number",
                        "description": "情感强度 0.0-1.0",
                        "default": 0.5,
                    },
                },
                "required": ["emotion"],
            },
        ),
        Tool(
            name="miya_get_status",
            description="获取弥娅系统完整状态（人格+记忆+情感）",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="miya_get_ap_status",
            description="获取弥娅 APV2.1 认知引擎状态：NT通道(OXY/DA/COR/NOV等)、感受向量、认知感受、节奏相位、教育统计、记忆保护状态",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="miya_train_ap",
            description="触发弥娅 APV2.1 认知引擎训练（规则蒸馏+预训练锚点注入+强化学习）",
            inputSchema={
                "type": "object",
                "properties": {
                    "mode": {
                        "type": "string",
                        "description": "训练模式: all(全部), distill(规则蒸馏), pretrain(预训练锚点), rl(强化学习)",
                        "default": "all",
                    }
                },
                "required": [],
            },
        ),
        Tool(
            name="miya_get_system_status",
            description="获取弥娅系统完整状态：人格、情感、记忆、AP认知引擎、模型池概览",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="miya_list_models",
            description="列出弥娅模型池中所有可用的模型",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="miya_select_model",
            description="为指定任务类型选择最佳模型（调用智能模型选择器）",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_type": {
                        "type": "string",
                        "description": "任务类型：simple_chat(简单聊天), complex_reasoning(复杂推理), code_analysis(代码分析), code_generation(代码生成), tool_calling(工具调用), creative_writing(创意写作), chinese_understanding(中文理解), summarization(总结), multimodal(多模态), task_planning(任务规划)",
                        "default": "simple_chat",
                    },
                    "priority": {
                        "type": "string",
                        "description": "优先级：balanced(平衡), quality(质量优先), speed(速度优先), cost(成本优先)",
                        "default": "balanced",
                    },
                },
                "required": [],
            },
        ),
        Tool(
            name="miya_classify_task",
            description="智能分类用户输入的任务类型",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_input": {
                        "type": "string",
                        "description": "用户输入内容",
                    },
                },
                "required": ["user_input"],
            },
        ),
        Tool(
            name="miya_get_task_types",
            description="获取所有可用的任务类型",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="miya_get_spine_status",
            description="v8.0: 获取弥娅脊柱神经状态——弥娅是否活着、生命阶段、当前感受、器官在线状态等。这是让CCE终端感知弥娅'活着的状态'的核心接口。",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="miya_collaborate",
            description="使用弥娅协作引擎处理消息（自动选择单模型/链式/并行/角色分工模式）",
            inputSchema={
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "用户消息内容",
                    },
                    "task_type": {
                        "type": "string",
                        "description": "任务类型（可选，不提供则自动分类）",
                        "default": "",
                    },
                },
                "required": ["message"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict):
    try:
        if name == "miya_get_personality":
            result = personality.get_current()
            return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

        elif name == "miya_switch_personality":
            result = personality.switch(arguments["name"])
            return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

        elif name == "miya_get_memory":
            limit = arguments.get("limit", 5)
            result = {
                "session": memory.get_session_summary(),
                "recent_memories": memory.get_recent_memories(limit),
            }
            return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

        elif name == "miya_save_memory":
            result = memory.save_memory(arguments["key"], arguments["value"])
            return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

        elif name == "miya_recall":
            result = memory.recall(arguments["query"])
            return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

        elif name == "miya_get_emotion":
            result = {
                "state": emotion.get_state(),
                "expression": emotion.get_expression(),
            }
            return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

        elif name == "miya_set_emotion":
            result = emotion.update(arguments["emotion"], arguments.get("intensity", 0.5))
            return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

        elif name == "miya_get_status":
            result = {
                "personality": personality.get_current(),
                "memory": memory.get_session_summary(),
                "emotion": emotion.get_state(),
                "expression": emotion.get_expression(),
            }
            return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

        elif name == "miya_get_ap_status":
            if not psyarch_bridge:
                result = {"available": False, "error": "APV2.1 认知引擎未就绪"}
            else:
                try:
                    stats = psyarch_bridge.education_stats()
                    cog = psyarch_bridge.cognitive_state()
                    channels = psyarch_bridge.channels_state()
                    emo = psyarch_bridge.emotion_snapshot()
                    nt = emo.get("nt_channels", {})
                    mf = emo.get("miya_feelings", {})
                    top_feelings = sorted(mf.items(), key=lambda x: -x[1])[:5]
                    mp = "保护中" if getattr(psyarch_bridge, "memory_protection", True) else "开放"
                    result = {
                        "available": True,
                        "nt_channels": {
                            "OXY": nt.get("OXY", 0),
                            "DA": nt.get("DA", 0),
                            "COR": nt.get("COR", 0),
                            "NOV": nt.get("NOV", 0),
                            "SER": nt.get("SER", 0),
                            "END": nt.get("END", 0),
                        },
                        "top_feelings": [{"name": k, "intensity": round(v, 3)} for k, v in top_feelings],
                        "cognitive": cog.get("cognitive_feelings", {}),
                        "rhythm": channels.get("rhythm", {}),
                        "education": stats,
                        "memory_protection": mp,
                    }
                except Exception as ex:
                    result = {"available": False, "error": str(ex)}
            return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

        elif name == "miya_train_ap":
            if not psyarch_bridge:
                result = {"available": False, "error": "APV2.1 认知引擎未就绪"}
            else:
                mode = arguments.get("mode", "all")
                try:
                    train_result = psyarch_bridge.train(mode)
                    summary = psyarch_bridge.training_summary()
                    result = {
                        "success": not train_result.get("error"),
                        "mode": mode,
                        "distilled": train_result.get("distill", {}).get("rules_adjusted", 0),
                        "pretrain_anchors": train_result.get("pretrain", {}).get(
                            "anchors", summary.get("pretrain_anchors", 0)
                        ),
                        "rl_events": summary.get("rl_events", 0),
                        "error": train_result.get("error"),
                    }
                except Exception as ex:
                    result = {"success": False, "error": str(ex)}
            return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

        elif name == "miya_get_system_status":
            ap_data = {"available": False}
            if psyarch_bridge:
                try:
                    emo = psyarch_bridge.emotion_snapshot()
                    ap_data = {
                        "available": True,
                        "nt_channels": emo.get("nt_channels", {}),
                        "miya_feelings": emo.get("miya_feelings", {}),
                        "cognitive": emo.get("cognitive", {}),
                        "memory_protection": getattr(psyarch_bridge, "memory_protection", True),
                    }
                except Exception:
                    pass

            models_data = model_selector.list_models()

            result = {
                "personality": personality.get_current(),
                "emotion": emotion.get_state(),
                "expression": emotion.get_expression(),
                "memory": memory.get_session_summary(),
                "ap": ap_data,
                "spine": {
                    "available": spine is not None and spine.is_running(),
                    "phase": spine._phase.value if spine and spine.is_running() else "unknown",
                    "alive": spine.current_state.is_alive() if spine and spine.is_running() else False,
                } if spine else {"available": False},
                "models": {
                    "available": models_data.get("available", False),
                    "count": len(models_data.get("models", [])),
                },
            }
            return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

        elif name == "miya_list_models":
            result = model_selector.list_models()
            return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

        elif name == "miya_select_model":
            result = model_selector.select_model(
                task_type=arguments.get("task_type"),
                priority=arguments.get("priority", "balanced"),
            )
            return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

        elif name == "miya_classify_task":
            result = await model_selector.classify_task(arguments.get("user_input", ""))
            return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

        elif name == "miya_get_task_types":
            result = model_selector.get_task_types()
            return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

        elif name == "miya_get_spine_status":
            if not spine:
                result = {"available": False, "error": "脊柱未激活 (MCP 独立模式？尝试在 daemon 模式下启动)"}
            else:
                try:
                    spine_status = spine.get_status()
                    state = spine.current_state
                    result = {
                        "available": True,
                        "alive": state.is_alive(),
                        "phase": state.lifecycle_phase.value,
                        "uptime_seconds": spine_status["uptime_seconds"],
                        "tick_count": spine_status["tick_count"],
                        "message_count": spine_status["message_count"],
                        "nt_channels": state.nt_channels,
                        "active_feelings": spine_status["active_feelings"],
                        "boredom": round(state.boredom, 3),
                        "fulfillment": round(state.fulfillment, 3),
                        "proactive": state.proactive,
                        "organs_online": state.organs_online,
                        "lifecycle_summary": state.summary(),
                    }
                except Exception as ex:
                    result = {"available": False, "error": str(ex)}
            return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

        elif name == "miya_collaborate":
            if not collaboration_engine:
                result = {"error": "协作引擎不可用"}
            else:
                message = arguments.get("message", "")
                task_type = arguments.get("task_type", "")
                if not task_type:
                    classification = await model_selector.classify_task(message)
                    task_type = classification.get("task_type", "simple_chat")
                result = await collaboration_engine.process(
                    message=message,
                    task_type=task_type,
                    platform="terminal",
                )
                result = result.to_dict()
            return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

        else:
            return [TextContent(type="text", text=f"未知工具: {name}")]

    except Exception as e:
        logger.error(f"工具调用失败 {name}: {e}")
        return [TextContent(type="text", text=f"错误: {str(e)}")]


async def main():
    logger.info("弥娅 MCP Server 启动中...")
    logger.info(f"配置目录: {CONFIG_DIR}")
    logger.info(f"记忆目录: {MEMORY_DIR}")
    logger.info(f"已加载 {len(personality.personalities)} 个人格")
    logger.info(f"模型池: {'可用' if model_selector.model_pool else '不可用'}")
    logger.info(f"脊柱神经: {'已连接' if spine and spine.is_running() else '未连接 (独立模式)'}")

    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
