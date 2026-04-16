"""
弥娅 Web 服务主程序
提供 React Web 界面与弥娅 API 交互
"""

import asyncio
import logging
import socket
import httpx
from pathlib import Path

try:
    from fastapi import FastAPI, Request
    from fastapi.responses import JSONResponse
    from fastapi.staticfiles import StaticFiles
    from fastapi.middleware.cors import CORSMiddleware
    import uvicorn

    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    logging.warning("FastAPI 未安装，Web 服务将不可用")

logger = logging.getLogger(__name__)


def is_port_available(port: int) -> bool:
    """检查端口是否可用"""
    try:
        # 尝试连接端口，如果能连接说明被占用
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.1)
            result = s.connect_ex(("127.0.0.1", port))
            # result == 0 表示连接成功，说明端口被占用
            return result != 0
    except:
        return False


def find_available_port(start_port: int = 8000, max_attempts: int = 100) -> int:
    """查找可用端口"""
    for offset in range(max_attempts):
        port = start_port + offset
        if is_port_available(port):
            return port
    raise RuntimeError(f"无法找到可用端口，已尝试 {max_attempts} 次")


async def main():
    """启动 Web 服务"""
    if not FASTAPI_AVAILABLE:
        print("错误: FastAPI 未安装，请运行: pip install fastapi uvicorn")
        return

    app = FastAPI(title="弥娅 Web 服务")

    # CORS 中间件
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 查找 API 端口
    api_port = 8001
    try:
        for p in range(8001, 8051):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.1)
                result = s.connect_ex(("127.0.0.1", p))
                if result == 0:
                    api_port = p
                    logger.info(f"检测到 API 服务运行在端口 {api_port}")
                    break
    except:
        pass

    # 检查 React 构建文件是否存在
    web_dist_path = (
        Path(__file__).parent.parent / "frontend" / "packages" / "web" / "dist"
    )
    react_built = web_dist_path.exists()

    if not react_built:
        logger.error("=" * 60)
        logger.error("未找到 React 构建文件！")
        logger.error("=" * 60)
        logger.error("")
        logger.error("请先构建 React Web 前端：")
        logger.error("")
        logger.error("  Windows:")
        logger.error("    start.bat")
        logger.error("    选择 [B] Build Web Frontend")
        logger.error("")
        logger.error("  或手动构建:")
        logger.error("    cd frontend/packages/web")
        logger.error("    npm install")
        logger.error("    npm run build")
        logger.error("")
        logger.error("  Linux/Mac:")
        logger.error("    bash scripts/build_web_frontend.sh")
        logger.error("")
        logger.error("=" * 60)
        return

    logger.info("检测到 React 构建文件，提供静态文件服务")

    # 健康检查端点（放在静态文件之前）
    @app.get("/health")
    async def health():
        """健康检查"""
        return {"status": "ok", "service": "miya-web", "react": react_built}

    @app.get("/api/health")
    async def api_health():
        """API 健康检查"""
        return {"status": "ok", "service": "miya-web", "react": react_built}

    @app.get("/api/status")
    async def get_status():
        """获取状态"""
        return {
            "status": "running",
            "service": "miya-web",
            "version": "2.0.0",
            "react_ui": react_built,
            "api_port": api_port,
        }

    # 移动端聊天页面（来自 miya_frontend/ui）
    @app.get("/chat")
    async def chat_page():
        """移动端聊天页面"""
        from fastapi.responses import FileResponse

        html_path = (
            Path(__file__).parent.parent / "miya_frontend" / "ui" / "mobile_chat.html"
        )
        if html_path.exists():
            return FileResponse(html_path)
        return {"error": "前端文件未找到"}

    # API 代理端点（必须在静态文件之前定义）
    @app.post("/api/terminal/chat")
    async def proxy_chat(request: Request):
        """代理聊天请求到真实的 API 服务"""
        try:
            body = await request.json()
            logger.info(f"[代理] 收到聊天请求: {body}")

            # 检查API服务是否可用
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(0.5)
                    result = s.connect_ex(("127.0.0.1", api_port))
                    if result != 0:
                        logger.warning(
                            f"[代理] API服务(端口{api_port})未运行,返回模拟响应"
                        )
                        message = body.get("message", "")
                        session_id = body.get("session_id", "")

                        # 简单的模拟响应
                        if not message or message.strip() == "":
                            response_text = "我收到了您的消息，但内容是空的。请告诉我您需要什么帮助。"
                        elif "在吗" in message or "你好" in message:
                            response_text = "我在呢！有什么可以帮助您的吗？"
                        elif "谢谢" in message:
                            response_text = "不客气！随时为您服务。"
                        else:
                            response_text = f"弥娅已收到消息: '{message}'\n\n(当前弥娅核心服务未运行,这是模拟响应。请启动弥娅核心服务以获得完整功能。)"

                        return {
                            "status": "success",
                            "response": response_text,
                            "session_id": session_id,
                            "timestamp": asyncio.get_event_loop().time(),
                        }
            except:
                pass

            async with httpx.AsyncClient() as client:
                api_url = f"http://localhost:{api_port}/api/terminal/chat"
                logger.info(f"[代理] 转发到: {api_url}")

                response = await client.post(api_url, json=body, timeout=30.0)

                logger.info(f"[代理] 响应状态: {response.status_code}")

                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(
                        f"[代理] API 返回错误: {response.status_code} - {response.text}"
                    )
                    return {
                        "status": "error",
                        "error": f"API 服务错误 (状态码: {response.status_code})",
                        "response": f"API 服务错误 (状态码: {response.status_code})",
                    }

        except httpx.ConnectError as e:
            logger.error(f"[代理] 无法连接到 API 服务: {e}")
            return {
                "status": "error",
                "error": f"无法连接到弥娅核心服务 (端口 {api_port})",
                "response": f"无法连接到弥娅核心服务 (端口 {api_port})",
            }
        except httpx.TimeoutException as e:
            logger.error(f"[代理] API 请求超时: {e}")
            return {
                "status": "error",
                "error": "请求超时，请稍后重试",
                "response": "请求超时，请稍后重试",
            }
        except Exception as e:
            logger.error(f"[代理] 未知错误: {e}", exc_info=True)
            return {
                "status": "error",
                "error": "抱歉，发生未知错误。",
                "response": "抱歉，发生未知错误。",
            }

    # 监控 API 端点（Mock 数据，实际应该从弥娅核心获取）
    @app.get("/api/tools/list")
    async def get_tools_list():
        """获取可用工具列表"""
        return {"tools": []}

    @app.get("/api/tools/history")
    async def get_tools_history():
        """获取工具使用历史"""
        return {"history": []}

    @app.get("/api/skills/list")
    async def get_skills_list():
        """获取可用技能列表"""
        return {"skills": []}

    @app.get("/api/skills/history")
    async def get_skills_history():
        """获取技能使用历史"""
        return {"history": []}

    @app.get("/api/mcp/servers")
    async def get_mcp_servers():
        """获取 MCP 服务器列表"""
        return {"servers": []}

    # 系统信息端点（用于桌面端）
    @app.get("/api/system/info")
    async def get_system_info():
        """获取系统信息"""
        import platform
        import psutil

        return {
            "platform": platform.system(),
            "platform_version": platform.version(),
            "architecture": platform.machine(),
            "hostname": platform.node(),
            "cpu": {
                "count": psutil.cpu_count(),
                "percent": psutil.cpu_percent(interval=0.1),
            },
            "memory": {
                "total": psutil.virtual_memory().total,
                "available": psutil.virtual_memory().available,
                "percent": psutil.virtual_memory().percent,
            },
            "disk": {
                "total": psutil.disk_usage("/").total
                if platform.system() == "Darwin" or platform.system() == "Linux"
                else psutil.disk_usage("C:\\").total,
                "free": psutil.disk_usage("/").free
                if platform.system() == "Darwin" or platform.system() == "Linux"
                else psutil.disk_usage("C:\\").free,
                "percent": psutil.disk_usage("/").percent
                if platform.system() == "Darwin" or platform.system() == "Linux"
                else psutil.disk_usage("C:\\").percent,
            },
        }

    # ========== 弥娅核心管理 API 代理 ==========

    @app.get("/api/miya/status")
    async def proxy_miya_status():
        """代理弥娅核心状态"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"http://localhost:{api_port}/api/miya/status", timeout=10.0
                )
                return response.json()
        except Exception as e:
            logger.error(f"代理弥娅状态失败: {e}")
            return {"status": "error", "error": str(e)}

    @app.get("/api/miya/memory")
    async def proxy_miya_memory():
        """代理记忆系统统计"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"http://localhost:{api_port}/api/miya/memory", timeout=10.0
                )
                return response.json()
        except Exception as e:
            logger.error(f"代理记忆统计失败: {e}")
            return {"status": "error", "error": str(e)}

    @app.get("/api/miya/tools")
    async def proxy_miya_tools():
        """代理工具列表"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"http://localhost:{api_port}/api/miya/tools", timeout=10.0
                )
                return response.json()
        except Exception as e:
            logger.error(f"代理工具列表失败: {e}")
            return {"status": "error", "error": str(e)}

    @app.get("/api/miya/personality")
    async def proxy_miya_personality():
        """代理人设配置"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"http://localhost:{api_port}/api/miya/personality", timeout=10.0
                )
                return response.json()
        except Exception as e:
            logger.error(f"代理人设配置失败: {e}")
            return {"status": "error", "error": str(e)}

    @app.get("/api/miya/models")
    async def proxy_miya_models():
        """代理AI模型信息"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"http://localhost:{api_port}/api/miya/models", timeout=10.0
                )
                return response.json()
        except Exception as e:
            logger.error(f"代理模型信息失败: {e}")
            return {"status": "error", "error": str(e)}

    @app.get("/api/miya/logs")
    async def proxy_miya_logs(limit: int = 100):
        """代理系统日志"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"http://localhost:{api_port}/api/miya/logs?limit={limit}",
                    timeout=10.0,
                )
                return response.json()
        except Exception as e:
            logger.error(f"代理系统日志失败: {e}")
            return {"status": "error", "error": str(e), "logs": [], "count": 0}

    # 查找可用端口
    default_port = 8000
    actual_port = find_available_port(default_port)

    if actual_port != default_port:
        logger.warning(f"默认端口 {default_port} 被占用，自动切换到端口 {actual_port}")

    # 启动服务器
    config = uvicorn.Config(app, host="0.0.0.0", port=actual_port, log_level="info")
    server = uvicorn.Server(config)

    logger.info("弥娅 Web 服务启动中...")
    logger.info(f"访问地址: http://localhost:{actual_port}")
    logger.info(f"API 地址: http://localhost:{api_port}")
    logger.info("✅ 使用 React 现代化界面")
    logger.info("按 Ctrl+C 停止服务")

    # 挂载静态文件（必须在所有API路由定义之后）
    app.mount("/", StaticFiles(directory=str(web_dist_path), html=True), name="static")

    # 启动服务器
    config = uvicorn.Config(app, host="0.0.0.0", port=actual_port, log_level="info")
    server = uvicorn.Server(config)

    logger.info("弥娅 Web 服务启动中...")
    logger.info(f"访问地址: http://localhost:{actual_port}")
    logger.info(f"API 地址: http://localhost:{api_port}")
    logger.info("✅ 使用 React 现代化界面")
    logger.info("按 Ctrl+C 停止服务")

    await server.serve()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    asyncio.run(main())
