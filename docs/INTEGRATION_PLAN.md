# 弥娅系统AstrBot能力集成计划

## 一、背景概述

### 1.1 现状分析
- **弥娅系统**：已有完整核心架构（Hub决策层、Memory记忆层、人格系统、情感引擎等）
- **AstrBot**：成熟的多平台LLM聊天机器人框架，功能完备
- **已拆入**：AstrBot的astrbot/目录已复制到Miya项目，但集成度待提升

### 1.2 集成目标
让弥娅系统完整拥有AstrBot的核心能力，同时保持弥娅独有的特色功能（人格、情感、记忆系统等）

---

## 二、架构对接分析

### 2.1 现有对接点

```
Miya/hub/decision_hub.py          ← 核心决策入口
    ├── response_generator.py      ← 响应生成（已集成工具调用）
    ├── perception_handler.py       ← 感知处理
    └── emotion_controller.py     ← 情感控制

Miya/core/
    ├── model_pool.py             ← 模型池管理（已完成）
    ├── ai_client.py            ← AI客户端
    ├── mcp_manager.py          ← MCP管理器（已有框架）
    ├── knowledge_base.py        ← 知识库（简化版）
    └── personality.py           ← 人格系统（弥娅独有）

Miya/webnet/
    ├── ToolNet/                 ← 工具子网
    └── qq/                     ← QQ适配器
```

### 2.2 缺失能力对照

| 模块 | AstrBot实现 | 弥娅现状 | 集成方案 |
|------|-----------|---------|--------|---------|
| MCP Client | `mcp_client.py` (674行) | 仅有框架 | 深度集成 |
| Knowledge Base | `kb_mgr.py` (402行) | 简化版 | 对接AstrBot |
| TTS | Provider层 | GPT-SoVITS | 完善多引擎 |
| STT | Provider层 | 缺失 | 集成Whisper |
| Dashboard | Vue.js + Quart | 基础API | 完整对接 |
| Tools | computer_tools | 基础 | 扩展沙箱 |

---

## 三、集成方案详细

### 3.1 MCP Client 集成 ⭐⭐⭐

#### 3.1.1 目标
弥娅能够调用MCP协议服务，扩展工具生态

#### 3.1.2 对接方式
```
Miya/core/mcp_manager.py + AstrBot/astrbot/core/agent/mcp_client.py
```

#### 3.1.3 具体步骤

**Step 1: 复制核心MCP Client**
```bash
# 从AstrBot复制
copy astrbot\core\agent\mcp_client.py → Miya\core\agent\mcp_client.py
```

**Step 2: 创建MCP集成器**
```python
# Miya/core/mcp_integration.py
from astrbot.core.agent.mcp_client import MCPClient, validate_mcp_stdio_config
from typing import Dict, Any, Optional, List
import json

class MCPIntegration:
    """弥娅MCP集成器"""
    
    def __init__(self):
        self._clients: Dict[str, MCPClient] = {}
        self._config_path = "config/mcp.json"
    
    async def initialize(self):
        """从配置文件加载并连接所有MCP服务"""
        config = self._load_config()
        for name, mcp_config in config.get("mcpServers", {}).items():
            await self.connect(name, mcp_config)
    
    async def connect(self, name: str, mcp_config: dict):
        """连接MCP服务"""
        client = MCPClient()
        await client.connect_to_server(mcp_config, name)
        await client.list_tools_and_save()
        self._clients[name] = client
    
    async def call_tool(
        self, 
        server_name: str, 
        tool_name: str, 
        arguments: dict
    ) -> Any:
        """调用MCP工具"""
        client = self._clients.get(server_name)
        if not client:
            raise ValueError(f"MCP服务未连接: {server_name}")
        
        from datetime import timedelta
        result = await client.call_tool_with_reconnect(
            tool_name=tool_name,
            arguments=arguments,
            read_timeout_seconds=timedelta(seconds=30)
        )
        return result.content
    
    def get_available_tools(self, server_name: str) -> List[str]:
        """获取MCP可用工具列表"""
        client = self._clients.get(server_name)
        if not client:
            return []
        return [tool.name for tool in client.tools]
```

**Step 3: 创建MCP配置文件**
```json
// config/mcp.json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "D:/Data"]
    },
    "brave-search": {
      "url": "http://localhost:8080/mcp",
      "transport": "streamable_http"
    }
  }
}
```

**Step 4: 集成到ResponseGenerator**
```python
# 在 response_generator.py 中添加
async def _handle_mcp_tool(self, tool_call: dict) -> str:
    """处理MCP工具调用"""
    from core.mcp_integration import get_mcp_integration
    
    mcp = get_mcp_integration()
    server_name = tool_call.get("server")
    tool_name = tool_call.get("name")
    args = tool_call.get("arguments", {})
    
    result = await mcp.call_tool(server_name, tool_name, args)
    return str(result)
```

**Step 5: 更新ToolNet注册MCP工具**
```python
# 在 webnet/ToolNet/registry.py 中添加
def register_mcp_tools(self, mcp_integration: MCPIntegration):
    """注册MCP工具到ToolNet"""
    for server_name, tools in mcp_integration.get_all_tools().items():
        for tool in tools:
            self.register(tool)
```

#### 3.1.4 优先级
- **Phase 1**: 文件系统MCP + Brave搜索MCP
- **Phase 2**: 自定义MCP服务
- **Phase 3**: 动态MCP加载

---

### 3.2 RAG 知识库集成 ⭐⭐⭐

#### 3.2.1 目标
弥娅能够上传文档、创建知识库、智能问答

#### 3.2.2 对接方式
```
Miya/core/knowledge_base.py + AstrBot/astrbot/core/knowledge_base/
```

#### 3.2.3 具体步骤

**Step 1: 创建知识库管理器适配器**
```python
# Miya/core/kb_integration.py
from astrbot.core.knowledge_base.kb_mgr import KnowledgeBaseManager
from astrbot.core.provider.manager import ProviderManager
from pathlib import Path

class KBIntegration:
    """弥娅知识库集成器"""
    
    def __init__(self, provider_manager: ProviderManager):
        self._kb_manager = KnowledgeBaseManager(provider_manager)
        self._storage_path = Path("data/knowledge_base")
    
    async def initialize(self):
        """初始化知识库"""
        self._storage_path.mkdir(parents=True, exist_ok=True)
        await self._kb_manager.initialize()
    
    async def create_kb(
        self, 
        name: str, 
        description: str,
        embedding_provider: str = "openai_embedding"
    ) -> str:
        """创建知识库"""
        kb = await self._kb_manager.create_kb(
            kb_name=name,
            description=description,
            embedding_provider_id=embedding_provider
        )
        return kb.kb.kb_id
    
    async def add_document(
        self, 
        kb_id: str, 
        file_path: str,
        doc_name: str = None
    ):
        """添加文档"""
        kb = await self._kb_manager.get_kb(kb_id)
        if not kb:
            raise ValueError(f"知识库不存在: {kb_id}")
        
        from astrbot.core.knowledge_base.models import KBDocument
        doc = await kb.upload_from_file(file_path, doc_name)
        return doc.doc_id
    
    async def search(
        self, 
        query: str, 
        kb_names: List[str],
        top_k: int = 5
    ) -> str:
        """知识检索"""
        results = await self._kb_manager.retrieve(
            query=query,
            kb_names=kb_names,
            top_m_final=top_k
        )
        return results.get("context_text", "") if results else ""
```

**Step 2: 集成到DecisionHub**
```python
# 在 decision_hub.py 中添加
async def _init_knowledge_base(self):
    """初始化知识库"""
    try:
        from core.kb_integration import KBIntegration
        from core.provider_manager import get_provider_manager
        
        provider_mgr = get_provider_manager()
        self.kb_integration = KBIntegration(provider_mgr)
        await self.kb_integration.initialize()
        logger.info("[决策层] 知识库系统已初始化")
    except Exception as e:
        logger.warning(f"[决策层] 知识库初始化失败: {e}")
        self.kb_integration = None
```

**Step 3: 添加知识库工具到ToolNet**
```python
# 定义工具schema
KNOWLEDGE_BASE_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "knowledge_search",
            "description": "从知识库中搜索相关内容",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "搜索query"},
                    "kb_names": {"type": "array", "items": {"type": "string"}},
                    "top_k": {"type": "integer", "default": 5}
                },
                "required": ["query", "kb_names"]
            }
        }
    },
    {
        "type": "function", 
        "function": {
            "name": "knowledge_create",
            "description": "创建新知识库",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "description": {"type": "string"}
                },
                "required": ["name"]
            }
        }
    }
]
```

**Step 4: 添加文档解析器依赖**
```bash
# requirements/kb.txt
pypdf>=3.0.0
aiofiles>=23.0.0
Pillow>=10.0.0
rank-bm25>=0.2.0
```

#### 3.2.4 支持的文档格式
- PDF
- EPUB
- TXT/MD
- URL网页
- Word文档

---

### 3.3 TTS 语音合成 ⭐⭐

#### 3.3.1 现状
- 弥娅已有GPT-SoVITS配置
- 已有tts_wrapper.py框架

#### 3.3.2 补充方案

**Step 1: 集成Edge TTS备选**
```python
# Miya/core/voice/edge_tts.py
import asyncio
import httpx
from edge_tts import Communicate

class EdgeTTSEngine:
    """Edge TTS引擎"""
    
    VOICES = {
        "zh-CN-XiaoxiaoNeural": "晓晓",
        "zh-CN-YunxiNeural": "云希", 
        "zh-CN-YunyangNeural": "云扬",
        "en-US-JennyNeural": "Jenny"
    }
    
    def __init__(self, voice: str = "zh-CN-XiaoxiaoNeural"):
        self.voice = voice
    
    async def synthesize(self, text: str, output_path: str):
        """合成语音"""
        communicate = Communicate(text, self.voice)
        await communicate.save(output_path)
```

**Step 2: 配置多引擎支持**
```json
// config/tts_config.json
{
  "enabled": true,
  "engines": {
    "gpt_sovits": {
      "enabled": true,
      "is_default": true,
      "api_url": "http://127.0.0.1:9880"
    },
    "edge_tts": {
      "enabled": true,
      "voice": "zh-CN-XiaoxiaoNeural"
    },
    "openai_tts": {
      "enabled": false,
      "voice": "alloy"
    }
  }
}
```

**Step 3: 添加语音工具**
```python
# 添加到 PLATFORM_TOOL_MAP
"tts_speak": {
    "description": "用语音回复用户",
    "parameters": {
        "text": "string",
        "voice": "string (optional)"
    }
}
```

---

### 3.4 STT 语音转文字 ⭐⭐

#### 3.4.1 目标
弥娅能够接收语音消息并转文字理解

#### 3.4.2 集成方案

**Step 1: 创建STT管理器**
```python
# Miya/core/voice/stt_manager.py
import asyncio
from functools import lru_cache

class STTManager:
    """语音转文字管理器"""
    
    ENGINES = {
        "whisper": "OpenAI Whisper",
        "sensevoice": "FunAudioLLM SenseVoice",
        "minimax": "MiniMax T2A"
    }
    
    def __init__(self):
        self._default_engine = "whisper"
    
    async def transcribe(self, audio_path: str, engine: str = None) -> str:
        """语音转文字"""
        engine = engine or self._default_engine
        
        if engine == "whisper":
            return await self._whisper_transcribe(audio_path)
        elif engine == "sensevoice":
            return await self._sensevoice_transcribe(audio_path)
        else:
            raise ValueError(f"未知STT引擎: {engine}")
    
    async def _whisper_transcribe(self, audio_path: str) -> str:
        """使用OpenAI Whisper转写"""
        from openai import AsyncOpenAI
        client = AsyncOpenAI()
        
        with open(audio_path, "rb") as audio:
            result = await client.audio.transcriptions.create(
                model="whisper-1",
                file=audio
            )
        return result.text
```

**Step 2: 集成到消息处理**
```python
# 在 QQ 消息处理中检测语音
async def process_qq_message(self, message: dict):
    # 检测语音消息
    if message.get("message_type") == "voice":
        audio_path = message.get("file")
        text = await stt_manager.transcribe(audio_path)
        message["content"] = text
```

**Step 3: 添加依赖**
```bash
# requirements/stt.txt
openai>=1.0.0
aiofiles>=23.0.0
```

---

### 3.5 Dashboard Web UI 集成 ⭐⭐

#### 3.5.1 目标
完整可视化管理界面

#### 3.5.2 集成方案

**Step 1: 共享AstrBot Dashboard**
```bash
# 使用软链接或复制
AstrBot/dashboard → Miya/miya_dashboard
```

**Step 2: 创建Dashboard API适配器**
```python
# Miya/core/dashboard_api.py
from quart import Quart, jsonify, request
from astrbot.dashboard.server import create_app as create_astrbot_app

class MiyaDashboardAPI:
    """弥娅Dashboard API"""
    
    def __init__(self):
        self.app = Quart(__name__)
        self._register_routes()
    
    def _register_routes(self):
        """注册弥娅特定路由"""
        
        @self.app.route("/api/miya/status")
        async def get_status():
            return jsonify({
                "name": "弥娅",
                "version": "4.3.4",
                "personality": self.personality.get_profile() if self.personality else None,
                "memory_stats": self.memory_engine.get_stats() if self.memory_engine else None
            })
        
        @self.app.route("/api/miya/personality", methods=["POST"])
        async def set_personality():
            data = await request.json
            form = data.get("form", "normal")
            self.personality.set_form(form)
            return jsonify({"success": True})
        
        @self.app.route("/api/miya/memory", methods=["GET"])
        async def get_memories():
            return jsonify(self.memory_engine.get_recent_memories(20))
    
    def run(self, host="0.0.0.0", port=8848):
        self.app.run(host=host, port=port)
```

**Step 3: 添加CORS支持**
```python
# 添加跨域支持
from quart_cors import cors, route_cors

@app.before_serving]
async def add_cors():
    await cors(self.app)
```

**Step 4: 启动脚本**
```python
# run_dashboard.py
from core.dashboard_api import MiyaDashboardAPI

if __name__ == "__main__":
    dashboard = MiyaDashboardAPI()
    dashboard.run(port=8848)
```

---

### 3.6 工具系统扩展 ⭐⭐

#### 3.6.1 目标
扩展弥娅的工具能力

#### 3.6.2 具体方案

**1. Cron定时任务**
```python
# Miya/core/cron_manager.py
import asyncio
from croniter import croniter

class CronManager:
    """定时任务管理器"""
    
    def __init__(self):
        self._tasks: Dict[str, dict] = {}
    
    def register(
        self, 
        name: str, 
        cron_expr: str, 
        handler: callable,
        enabled: bool = True
    ):
        """注册定时任务"""
        self._tasks[name] = {
            "cron": croniter(cron_expr),
            "handler": handler,
            "enabled": enabled,
            "last_run": None
        }
    
    async def start(self):
        """启动定时任务调度"""
        while True:
            for name, task in self._tasks.items():
                if not task["enabled"]:
                    continue
                
                if task["cron"].is_now():
                    await task["handler"]()
                    task["last_run"] = datetime.now()
            
            await asyncio.sleep(60)
```

**2. 浏览器操作工具**
```python
# 使用 AstrBot 的 Neo Skills
# 直接集成 web_search_tools.py
from astrbot.core.tools.web_search_tools import (
    web_search_baidu,
    web_search_tavily,
    tavily_extract_web_page
)

# 注册到 ToolNet
self.tool_subnet.register_tool(web_search_baidu)
self.tool_subnet.register_tool(web_search_tavily)
```

**3. 代码执行沙箱**
```python
# 使用 AstrBot 的 computer_tools
from astrbot.core.tools.computer_tools import (
    Python REPL,
    Shell Executor,
    File System
)

# 安全的代码执行
async def safe_python_execute(code: str, timeout: int = 30) -> str:
    """安全执行Python代码"""
    from astrbot.core.tools.computer_tools.python import PythonREPL
    
    repl = PythonREPL(timeout=timeout)
    result = await repl.execute(code)
    return result.stdout
```

---

## 四、实施路径

### 4.1 Phase 1: 核心能力 (1-2周)

```
Week 1: MCP Client集成
├── 复制 mcp_client.py
├── 创建 MCPIntegration
├── 配置 filesystem/brave MCP
└── 集成到 ResponseGenerator

Week 2: 知识库RAG
├── 复制 knowledge_base 模块
├── 创建 KBIntegration
├── 添加文档解析器依赖
└── 添加搜索工具到 ToolNet
```

### 4.2 Phase 2: 语音能力 (1周)

```
Week 3: TTS + STT
├── 完善 Edge TTS
├── 添加 STT Manager
├── 集成 Whisper/SenseVoice
└── 添加语音工具schema
```

### 4.3 Phase 3: 扩展功能 (1周)

```
Week 4: Dashboard + Tools
├── 共享 Dashboard
├── 创建 MiyaDashboardAPI
├── Cron Manager
└── 浏览器工具
```

---

## 五、配置文件更新

### 5.1 新增配置

```json
// config/mcp.json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "D:/Data"]
    }
  }
}
```

### 5.2 依赖更新

```
# requirements/kb.txt (新增)
pypdf>=3.0.0
aiofiles>=23.0.0
Pillow>=10.0.0
rank-bm25>=0.2.0

# requirements/stt.txt (新增)
openai>=1.0.0

# requirements/mcp.txt (新增)
mcp>=1.0.0
anyio>=4.0.0
```

---

## 六、验证清单

### 6.1 MCP集成验证
- [ ] MCP配置文件加载成功
- [ ] 文件系统MCP可调用
- [ ] Brave搜索MCP可调用
- [ ] 工具正确注册到ToolNet

### 6.2 知识库验证
- [ ] 创建知识库成功
- [ ] PDF文档上传成功
- [ ] 搜索返回相关结果
- [ ] RRF混合检索工作正常

### 6.3 语音验证
- [ ] Edge TTS合成成功
- [ ] GPT-SoVITS工作正常
- [ ] Whisper转写成功
- [ ] 语音消息自动转文字

### 6.4 Dashboard验证
- [ ] Dashboard访问正常
- [ ] 状态页面显示正确
- [ ] 人格切换功能可用
- [ ] 记忆查看功能可用

---

## 七、注意事项

### 7.1 安全考虑
- MCP stdio命令白名单限制
- 代码执行沙箱隔离
- API密钥安全管理

### 7.2 性能优化
- MCP连接池管理
- 知识库缓存
- 向量索引优化

### 7.3 兼容性
- Python 3.10+ 兼容
- Windows/Linux双平台

---

## 八、联系人

如有问题，请查看：
- AstrBot文档: `AstrBot/docs/`
- 弥娅文档: `Miya/docs/`

---

*生成时间: 2026-04-28*
*版本: v1.0*