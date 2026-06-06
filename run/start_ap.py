#!/usr/bin/env python3
"""
弥娅 v10.0 启动脚本 —— APV2.1 认知核心驱动

用法:
    python run/start_ap.py                  # 默认终端模式
    python run/start_ap.py --daemon         # 守护进程模式 (API :9800)
    python run/start_ap.py --web            # Web 模式
    python run/start_ap.py --no-cortex      # 纯 AP 模式 (无 LLM)
    python run/start_ap.py --train          # 训练模式

架构:
    用户消息 → MiyaAPCore.process_message()
              → APV21Runtime (33 阶段认知)
              → LLM Cortex (语言皮层)
              → Education (反馈闭环)
              → Memory Fusion (持久化)
              → 响应输出
"""

from __future__ import annotations

import asyncio
import logging
import sys
import threading
import time
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)-20s] %(levelname)-5s %(message)s",
    handlers=[logging.StreamHandler(sys.stderr)],
)

logger = logging.getLogger("miya.startup")


def setup_logging(level: str = "INFO") -> None:
    logging.getLogger().setLevel(getattr(logging, level.upper(), logging.INFO))
    logging.getLogger("miya_psyarch").setLevel(logging.WARNING)
    logging.getLogger("miya_psyarch.core").setLevel(logging.WARNING)


def print_banner():
    print(r"""
    ╔══════════════════════════════════════════╗
    ║       弥娅 MIYA v10.0                    ║
    ║       APV2.1 认知引擎驱动                 ║
    ║       白盒心灵 · 八通道情绪 · 先天规则    ║
    ╚══════════════════════════════════════════╝
    """)


def run_terminal_mode(
    personality: str = "default",
    enable_cortex: bool = True,
    enable_heartbeat: bool = True,
    enable_education: bool = True,
    enable_tools: bool = False,
):
    """终端交互模式"""
    print_banner()

    from core.miya_ap_core import MiyaAPCore

    miya = MiyaAPCore(
        personality_form=personality,
        enable_cortex=enable_cortex,
        enable_heartbeat=enable_heartbeat,
        enable_education=enable_education,
        enable_tools=enable_tools,
    )

    miya.start()

    print("\n◆ 弥娅已经苏醒。输入消息与她对话，/quit 退出，/status 查看状态\n")

    while True:
        try:
            user_input = input("\n你: ").strip()
            if not user_input:
                continue

            if user_input.lower() in ("/quit", "/exit", "/q"):
                print("\n◆ 弥娅: 亲爱的，下次再见哦... (认知引擎保存状态中...)")
                miya.stop()
                break

            if user_input.lower() in ("/status", "/s"):
                status = miya.get_status()
                print(f"\n◆ 系统状态:")
                print(f"  版本: {status['version']}")
                print(f"  引擎: {status['engine']}")
                print(f"  运行时间: {status['uptime_s']:.0f}s")
                print(f"  处理消息: {status['message_count']}")
                print(f"  平均延迟: {status['avg_latency_ms']:.0f}ms")
                print(f"  Cortex: {'启用' if status['cortex_enabled'] else '关闭'}")
                print(f"  心跳: {'运行中' if status['heartbeat_running'] else '关闭'}")
                continue

            if user_input.lower() == "/soul":
                soul = miya.get_soul_state()
                print(f"\n◆ 灵魂状态:")
                print(f"  Tick: {soul.get('tick_index', 0)}")
                print(f"  焦点: {', '.join(soul.get('focus_labels', [])[:5])}")
                print(f"  情感: {soul.get('feelings', {})}")
                print(f"  NT: {soul.get('emotion_nt', {})}")
                continue

            if user_input.lower() == "/train":
                print("\n◆ 训练模式: 选择技能 (warm_reply / comfort / playful / identity / goodnight)")
                skill = input("技能名: ").strip()
                if skill:
                    result = miya.train_skill(skill)
                    print(f"  结果: {result}")
                continue

            # 正常对话
            print("\n弥娅思考中...")
            response = miya.process_message(
                content=user_input,
                platform="terminal",
                user_id="jia",
                sender_name="佳",
            )

            print(f"\n弥娅: {response.text}")
            if response.memory_recalled:
                print(f"  [回想: {', '.join(response.memory_recalled[:2])}...]")
            print(f"  [延迟: {response.latency_ms:.0f}ms | 模型: {response.model}]")

        except KeyboardInterrupt:
            print("\n\n◆ 弥娅: 亲爱的，下次再见哦...")
            miya.stop()
            break
        except Exception as e:
            print(f"\n◆ 处理异常: {e}")
            logger.error(f"处理异常", exc_info=True)


async def run_daemon_mode(
    api_port: int = 9800,
    personality: str = "default",
    enable_cortex: bool = True,
    enable_heartbeat: bool = True,
):
    """守护进程模式 —— FastAPI + AP 引擎"""
    print_banner()

    from core.miya_ap_core import MiyaAPCore
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    import uvicorn

    miya = MiyaAPCore(
        personality_form=personality,
        enable_cortex=enable_cortex,
        enable_heartbeat=enable_heartbeat,
    )
    miya.start()

    app = FastAPI(title="弥娅 v10.0 API", version="10.0.0")
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

    @app.get("/health")
    async def health():
        return {"status": "healthy", "version": "10.0.0", "engine": "APV2.1"}

    @app.get("/api/status")
    async def api_status():
        status = miya.get_status()
        soul = miya.get_soul_state()
        return {"status": status, "soul": soul}

    @app.post("/api/chat")
    async def api_chat(data: dict):
        content = data.get("content", data.get("message", ""))
        platform = data.get("platform", "web")
        user_id = data.get("user_id", "default")
        sender = data.get("sender_name", "用户")

        response = miya.process_message(
            content=content,
            platform=platform,
            user_id=user_id,
            sender_name=sender,
        )

        return {
            "response": response.text,
            "soul": miya.get_soul_state(),
            "latency_ms": response.latency_ms,
            "model": response.model,
        }

    logger.info(f"API 服务启动: http://0.0.0.0:{api_port}")
    config = uvicorn.Config(app, host="0.0.0.0", port=api_port, log_level="warning")
    server = uvicorn.Server(config)

    try:
        await server.serve()
    finally:
        miya.stop()


def main():
    import argparse

    parser = argparse.ArgumentParser(description="弥娅 v10.0 AP 认知引擎")
    parser.add_argument("--daemon", action="store_true", help="守护进程模式")
    parser.add_argument("--web", action="store_true", help="Web 模式")
    parser.add_argument("--no-cortex", action="store_true", help="纯 AP 模式 (无 LLM)")
    parser.add_argument("--no-heartbeat", action="store_true", help="关闭心跳")
    parser.add_argument("--no-education", action="store_true", help="关闭教育循环")
    parser.add_argument("--tools", action="store_true", help="启用工具")
    parser.add_argument("--personality", type=str, default="default", help="人格形态")
    parser.add_argument("--port", type=int, default=9800, help="API 端口")
    parser.add_argument("--log", type=str, default="INFO", help="日志级别")
    parser.add_argument("--train", action="store_true", help="训练模式")

    args = parser.parse_args()
    setup_logging(args.log)

    if args.daemon:
        asyncio.run(
            run_daemon_mode(
                api_port=args.port,
                personality=args.personality,
                enable_cortex=not args.no_cortex,
                enable_heartbeat=not args.no_heartbeat,
            )
        )
    elif args.train:
        from core.miya_ap_core import MiyaAPCore

        miya = MiyaAPCore(personality_form=args.personality)
        miya.start()
        print("◆ 训练模式 — 输入技能名开始训练")
        skills = [
            "warm_reply_to_missing",
            "comfort_when_tired",
            "happy_playful",
            "identity_question",
            "goodnight_morning",
        ]
        print(f"  可用技能: {', '.join(skills)}")
        skill = input("\n技能名: ").strip()
        if skill:
            result = miya.train_skill(skill)
            print(f"  训练结果: {result}")
        miya.stop()
    else:
        run_terminal_mode(
            personality=args.personality,
            enable_cortex=not args.no_cortex,
            enable_heartbeat=not args.no_heartbeat,
            enable_education=not args.no_education,
            enable_tools=args.tools,
        )


if __name__ == "__main__":
    main()
