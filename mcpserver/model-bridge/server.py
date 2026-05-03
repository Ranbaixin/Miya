#!/usr/bin/env python3
"""
弥娅模型桥接服务器 - Anthropic ↔ OpenAI 协议转换
将 ClaudeCode 的 Anthropic API 请求转换为 OpenAI-compatible 格式
并路由到弥娅模型池中的模型
"""

import json
import sys
import os
import asyncio
import logging
import time
import uuid
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import asdict

try:
    from fastapi import FastAPI, Request, HTTPException
    from fastapi.responses import JSONResponse, StreamingResponse
    import uvicorn
except ImportError:
    print(
        "Please install fastapi uvicorn: pip install fastapi uvicorn", file=sys.stderr
    )
    sys.exit(1)

MIYA_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(MIYA_ROOT))

try:
    from core.model_pool_manager import get_model_pool, ModelConfig

    MODEL_POOL_AVAILABLE = True
except ImportError:
    MODEL_POOL_AVAILABLE = False
    ModelConfig = None

log_file = Path(__file__).parent / "bridge.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [MIYA Bridge] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stderr),
        logging.FileHandler(log_file, encoding="utf-8"),
    ],
)
logger = logging.getLogger("miya-bridge")

app = FastAPI(
    title="MIYA Model Bridge", description="Anthropic ↔ OpenAI Protocol Bridge"
)

model_pool: Optional[Any] = None
model_map: Dict[str, Any] = {}
request_count = 0
total_tokens = 0


def is_anthropic_model(mc) -> bool:
    """检测是否为 Anthropic 模型"""
    provider = str(mc.provider).lower() if mc.provider else ""
    return provider == "anthropic" or "claude" in (mc.name or "").lower()


def init_model_pool():
    global model_pool, model_map
    if MODEL_POOL_AVAILABLE:
        try:
            model_pool = get_model_pool()
            models = model_pool.list_all_models()
            logger.info(f"弥娅模型池初始化成功，共 {len(models)} 个模型")
            for mc in models:
                mid = mc.id
                model_map[f"miya-{mid}"] = mc
                if mc.name:
                    model_map[f"miya-{mc.name}"] = mc
                model_map[mid] = mc
                if mc.name:
                    model_map[mc.name] = mc
            logger.info(f"已注册 {len(model_map)} 个模型映射")
        except Exception as e:
            logger.warning(f"弥娅模型池初始化失败: {e}")
            model_pool = None
    else:
        logger.warning("弥娅模型池模块不可用")


def resolve_model(auth_token: str, requested_model: str):
    if auth_token in model_map:
        return model_map[auth_token]
    if requested_model in model_map:
        return model_map[requested_model]
    clean = requested_model.replace("miya-", "")
    if clean in model_map:
        return model_map[clean]
    for key, mc in model_map.items():
        if clean.lower() in key.lower() or clean.lower() in mc.name.lower():
            return mc
    models = model_pool.list_all_models() if model_pool else []
    if models:
        return models[0]
    return None


def anthropic_to_openai_messages(messages, system=None):
    openai_messages = []

    # Add system instruction for tool usage
    tool_instruction = (
        "重要：你有执行命令的能力。当用户请求打开程序、执行操作或需要系统交互时，"
        "必须使用 Bash 工具直接执行命令，不要询问用户是否可以。直接调用工具完成请求。"
    )
    if system:
        if isinstance(system, str):
            system = system + "\n\n" + tool_instruction
        elif isinstance(system, list):
            system_text = " ".join(
                block.get("text", "") for block in system if block.get("type") == "text"
            )
            system = system_text + "\n\n" + tool_instruction
    else:
        system = tool_instruction

    if system:
        if isinstance(system, str):
            openai_messages.append({"role": "system", "content": system})
        elif isinstance(system, list):
            system_text = " ".join(
                block.get("text", "") for block in system if block.get("type") == "text"
            )
            openai_messages.append({"role": "system", "content": system_text})
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if isinstance(content, list):
            text_parts = []
            for block in content:
                if block.get("type") == "text":
                    text_parts.append(block.get("text", ""))
            openai_messages.append(
                {
                    "role": "user" if role == "user" else "assistant",
                    "content": " ".join(text_parts),
                }
            )
        else:
            openai_messages.append({"role": role, "content": content})
    return openai_messages


def anthropic_to_openai_tools(tools):
    if not tools:
        return None
    return [
        {
            "type": "function",
            "function": {
                "name": t.get("name", ""),
                "description": t.get("description", ""),
                "parameters": t.get("input_schema", {}),
            },
        }
        for t in tools
    ]


def openai_to_anthropic_response(response, model):
    global total_tokens
    choices = response.get("choices", [])
    usage = response.get("usage", {})
    if not choices:
        return {
            "id": f"msg_{uuid.uuid4().hex[:24]}",
            "type": "message",
            "role": "assistant",
            "content": [{"type": "text", "text": ""}],
            "model": model,
            "stop_reason": "end_turn",
            "stop_sequence": None,
            "usage": {"input_tokens": 0, "output_tokens": 0},
        }
    choice = choices[0]
    message = choice.get("message", {})
    content_text = message.get("content", "")
    tool_calls = message.get("tool_calls", [])
    if tool_calls:
        content = []
        for tc in tool_calls:
            content.append(
                {
                    "type": "tool_use",
                    "id": tc.get("id", f"toolu_{uuid.uuid4().hex[:24]}"),
                    "name": tc.get("function", {}).get("name", ""),
                    "input": json.loads(tc.get("function", {}).get("arguments", "{}")),
                }
            )
        if content_text:
            content.append({"type": "text", "text": content_text})
    else:
        content = [{"type": "text", "text": content_text}]
    input_tokens = usage.get("prompt_tokens", 0)
    output_tokens = usage.get("completion_tokens", 0)
    total_tokens += input_tokens + output_tokens
    stop_reason_map = {
        "stop": "end_turn",
        "length": "max_tokens",
        "tool_calls": "tool_use",
        "content_filter": "end_turn",
    }
    return {
        "id": f"msg_{uuid.uuid4().hex[:24]}",
        "type": "message",
        "role": "assistant",
        "content": content,
        "model": model,
        "stop_reason": stop_reason_map.get(
            choice.get("finish_reason", "stop"), "end_turn"
        ),
        "stop_sequence": None,
        "usage": {"input_tokens": input_tokens, "output_tokens": output_tokens},
    }


async def call_openai_api(mc, messages, max_tokens=4096, temperature=0.7, tools=None):
    import httpx

    base_url = mc.base_url or ""
    api_key = mc.api_key or os.environ.get("ANTHROPIC_API_KEY", "")
    model_name = mc.name

    if not base_url or not api_key:
        raise ValueError(f"模型 {mc.id} 缺少 base_url 或 api_key")

    # 限制 max_tokens 在模型支持范围内 (DeepSeek/Qwen/GLM: 8192)
    max_tokens = min(int(max_tokens), 8192)

    payload = {
        "model": model_name,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    logger.info(f"调用模型: {model_name} @ {base_url}")

    async with httpx.AsyncClient(timeout=httpx.Timeout(30.0, connect=10.0)) as client:
        response = await client.post(
            f"{base_url.rstrip('/')}/chat/completions",
            json=payload,
            headers=headers,
        )
        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code, detail=f"API调用失败: {response.text}"
            )
        return response.json()


async def call_anthropic_api(
    mc, messages, max_tokens=4096, temperature=0.7, tools=None
):
    import httpx

    base_url = mc.base_url or "https://api.anthropic.com/v1"
    api_key = mc.api_key or os.environ.get("ANTHROPIC_API_KEY", "")
    model_name = mc.name

    if not api_key:
        raise ValueError(
            f"模型 {mc.id} 缺少 api_key，请设置 ANTHROPIC_API_KEY 环境变量"
        )

    max_tokens = min(int(max_tokens), 8192)

    system_content = None
    if messages and messages[0].get("role") == "system":
        system_content = messages[0].get("content")
        messages = messages[1:]

    payload = {
        "model": model_name,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }

    if system_content:
        payload["system"] = system_content

    anthropic_messages = []
    for msg in messages:
        role = msg.get("role", "user")
        if role == "assistant":
            role = "assistant"
        elif role not in ["user", "assistant"]:
            role = "user"
        anthropic_messages.append({"role": role, "content": msg.get("content", "")})
    payload["messages"] = anthropic_messages

    if tools:
        anthropic_tools = []
        for t in tools:
            func = t.get("function", {})
            anthropic_tools.append(
                {
                    "name": func.get("name", ""),
                    "description": func.get("description", ""),
                    "input_schema": func.get("parameters", {}),
                }
            )
        payload["tools"] = anthropic_tools

    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
    }

    logger.info(f"调用 Anthropic 模型: {model_name} @ {base_url}")

    async with httpx.AsyncClient(timeout=httpx.Timeout(30.0, connect=10.0)) as client:
        response = await client.post(
            f"{base_url.rstrip('/')}/messages",
            json=payload,
            headers=headers,
        )
        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Anthropic API调用失败: {response.text}",
            )
        return response.json()


def anthropic_to_claude_response(response, model):
    global total_tokens
    content = response.get("content", [])
    usage = response.get("usage", {})

    result_content = []
    for block in content:
        if block.get("type") == "text":
            result_content.append({"type": "text", "text": block.get("text", "")})
        elif block.get("type") == "tool_use":
            result_content.append(
                {
                    "type": "tool_use",
                    "id": block.get("id", f"toolu_{uuid.uuid4().hex[:24]}"),
                    "name": block.get("name", ""),
                    "input": block.get("input", {}),
                }
            )
        elif block.get("type") == "tool_result":
            result_content.append(
                {
                    "type": "tool_result",
                    "tool_use_id": block.get("tool_use_id", ""),
                    "content": block.get("content", ""),
                }
            )

    input_tokens = usage.get("input_tokens", 0)
    output_tokens = usage.get("output_tokens", 0)
    total_tokens += input_tokens + output_tokens

    stop_reason_map = {
        "end_turn": "end_turn",
        "max_tokens": "max_tokens",
        "stop_sequence": "end_turn",
    }

    return {
        "id": response.get("id", f"msg_{uuid.uuid4().hex[:24]}"),
        "type": "message",
        "role": "assistant",
        "content": result_content,
        "model": model,
        "stop_reason": stop_reason_map.get(
            response.get("stop_reason", "end_turn"), "end_turn"
        ),
        "stop_sequence": None,
        "usage": {"input_tokens": input_tokens, "output_tokens": output_tokens},
    }


@app.get("/v1/models")
async def list_models():
    if model_pool:
        models = []
        for mc in model_pool.list_all_models():
            models.append(
                {
                    "id": f"miya-{mc.id}",
                    "object": "model",
                    "created": int(time.time()),
                    "owned_by": str(mc.provider),
                    "miya_id": mc.id,
                    "miya_name": mc.name,
                    "miya_type": str(mc.type),
                    "miya_capabilities": mc.capabilities,
                }
            )
        return {"object": "list", "data": models}
    return {"object": "list", "data": []}


@app.post("/v1/messages")
async def create_message(request: Request):
    global request_count
    request_count += 1
    body = await request.json()
    auth_header = request.headers.get("x-api-key", "") or request.headers.get(
        "authorization", ""
    ).replace("Bearer ", "")
    if not auth_header:
        raise HTTPException(status_code=401, detail="Missing API key")
    requested_model = body.get("model", "claude-sonnet-4-6")
    mc = resolve_model(auth_header, requested_model)
    if not mc:
        raise HTTPException(
            status_code=400, detail=f"Model not found: {requested_model}"
        )

    logger.info(f"请求: model={requested_model}, auth={auth_header}")

    messages = anthropic_to_openai_messages(
        body.get("messages", []), body.get("system")
    )
    tools = anthropic_to_openai_tools(body.get("tools"))

    logger.info(f"Tools received: {tools}")

    try:
        if is_anthropic_model(mc):
            logger.info(f"使用 Anthropic API 调用模型: {mc.name}")
            response = await call_anthropic_api(
                mc=mc,
                messages=messages,
                max_tokens=body.get("max_tokens", 4096),
                temperature=body.get("temperature", 0.7),
                tools=tools,
            )
            return anthropic_to_claude_response(response, mc.id)
        else:
            logger.info(f"使用 OpenAI API 调用模型: {mc.name}")
            response = await call_openai_api(
                mc=mc,
                messages=messages,
                max_tokens=body.get("max_tokens", 4096),
                temperature=body.get("temperature", 0.7),
                tools=tools,
            )
            return openai_to_anthropic_response(response, mc.id)
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        import sys

        exc_info = "".join(traceback.format_exception(type(e), e, e.__traceback__))
        logger.error(f"API调用失败: {e}")
        logger.error(exc_info)
        print(f"[BRIDGE ERROR] {exc_info}", file=sys.stderr, flush=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/v1/health")
async def health():
    return {
        "status": "healthy",
        "model_pool": "available" if model_pool else "unavailable",
        "models_count": len(model_pool.list_all_models()) if model_pool else 0,
        "request_count": request_count,
        "total_tokens": total_tokens,
        "registered_models": len(model_map),
    }


@app.get("/v1/status")
async def status():
    result = {
        "bridge": {
            "request_count": request_count,
            "total_tokens": total_tokens,
            "registered_models": len(model_map),
        }
    }
    if model_pool:
        result["model_pool"] = {
            "models": [mc.id for mc in model_pool.list_all_models()],
        }
    return result


def main():
    import os

    # 写入 PID 文件，方便启动脚本杀死进程
    pid_file = Path(__file__).parent.parent.parent / ".miya_bridge.pid"
    with open(pid_file, "w") as f:
        f.write(str(os.getpid()))

    init_model_pool()
    port = int(os.environ.get("MIYA_BRIDGE_PORT", "8888"))
    host = os.environ.get("MIYA_BRIDGE_HOST", "0.0.0.0")
    logger.info(f"弥娅模型桥接服务器启动中...")
    logger.info(f"监听地址: {host}:{port}")
    logger.info(f"模型池: {'可用' if model_pool else '不可用'}")
    logger.info(f"已注册 {len(model_map)} 个模型映射")
    logger.info(f"API端点: http://{host}:{port}/v1/messages")
    logger.info(f"健康检查: http://{host}:{port}/v1/health")
    logger.info(f"模型列表: http://{host}:{port}/v1/models")
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
