#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MIYA API 服务器

使用方法:
    python miya_server.py              # 默认端口 8765
    python miya_server.py --port 8080 # 指定端口
    python miya_server.py --help     # 查看帮助
"""

import argparse
import asyncio
import json
import logging
import sys
import time
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

# 设置项目根目录
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("miya_server")


# ==================== 配置 ====================


@dataclass
class ServerConfig:
    """服务器配置"""

    host: str = "0.0.0.0"
    port: int = 8765
    cors: bool = True
    log_level: str = "info"


# ==================== 简单 HTTP 服务器 ====================


class MIYARequest:
    """简单的请求对象"""

    def __init__(self, path: str, method: str = "GET", body: bytes = None):
        self.path = path
        self.method = method
        self.body = body
        self._json = None

    async def json(self) -> Dict:
        """解析 JSON body"""
        if self._json is None:
            if self.body:
                try:
                    self._json = json.loads(self.body.decode("utf-8"))
                except:
                    self._json = {}
            else:
                self._json = {}
        return self._json


class SimpleHTTPHandler:
    """简单 HTTP 处理器"""

    def __init__(self):
        from core.dashboard_api import get_api_router, list_all_routes

        self.router = get_api_router()
        self.routes = list_all_routes()

    async def handle(
        self, path: str, method: str, body: bytes = None
    ) -> tuple[int, str]:
        """处理 HTTP 请求"""
        try:
            # 构造请求对象
            request = MIYARequest(path, method, body)

            # 处理 CORS 预检
            if method == "OPTIONS":
                return 200, ""

            # 查找路由 - 先尝试完整匹配
            route_key = f"{method} {path}"
            handler = self.router._routes.get(route_key)

            # 再尝试路径参数匹配
            if not handler:
                for r_key, r_handler in self.router._routes.items():
                    r_method, r_path = r_key.split(" ", 1)
                    if r_method == method and ":" in r_path:
                        # 转换路径参数格式
                        pattern = r_path.replace(":id", "([^/]+)")
                        import re

                        if re.match(f"^{pattern}$", path):
                            handler = r_handler
                            break

            # 执行处理器
            if handler:
                result = await handler(request)
                return 200, json.dumps(result, ensure_ascii=False)
            else:
                # 404
                return 404, json.dumps({"error": "Not Found", "path": path})

        except Exception as e:
            logger.error(f"处理请求失败: {e}")
            return 500, json.dumps({"error": str(e)})


class MIYAServer:
    """MIYA HTTP 服务器"""

    def __init__(self, config: ServerConfig):
        self.config = config
        self.handler = SimpleHTTPHandler()
        self.start_time = time.time()
        self._running = False

    async def handle_client(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ):
        """处理客户端连接"""
        try:
            # 读取请求
            data = await reader.read(4096)
            if not data:
                writer.close()
                await writer.wait_closed()
                return

            # 解析请求行
            request_line = data.decode("utf-8", errors="ignore").split("\r\n")[0]
            parts = request_line.split(" ")
            method = parts[0] if len(parts) > 0 else "GET"
            path = parts[1] if len(parts) > 1 else "/"

            # 获取 body
            body = None
            if "Content-Length:" in data.decode():
                for line in data.decode().split("\r\n"):
                    if line.startswith("Content-Length:"):
                        length = int(line.split(":")[1].strip())
                        body = data[-length:]
                        break

            # 处理请求
            status_code, response_body = await self.handler.handle(path, method, body)

            # 构建响应
            headers = [
                "HTTP/1.1",
                f" {status_code} {'OK' if status_code == 200 else 'Not Found' if status_code == 404 else 'Error'}",
                "Content-Type: application/json; charset=utf-8",
                "Access-Control-Allow-Origin: *",
                "Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS",
                "Access-Control-Allow-Headers: Content-Type",
            ]

            response = (
                "\r\n".join(headers)
                + f"\r\nContent-Length: {len(response_body)}\r\n\r\n"
                + response_body
            )

            # 发送响应
            writer.write(response.encode())
            await writer.drain()

        except Exception as e:
            logger.error(f"处理客户端失败: {e}")
        finally:
            writer.close()
            await writer.wait_closed()

    async def start(self):
        """启动服务器"""
        self._running = True

        server = await asyncio.start_server(
            self.handle_client,
            self.config.host,
            self.config.port,
        )

        addr = server.sockets[0].getsockname()
        logger.info(f"=" * 50)
        logger.info(f"🎭 MIYA API Server v6.0 已启动")
        logger.info(f"   地址: http://{addr[0]}:{addr[1]}")
        logger.info(f"   路由: {len(self.handler.routes)} 个")
        logger.info(f"   启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"=" * 50)

        # 输出路由列表
        logger.info("\n📋 可用路由:")
        for route in self.handler.routes[:10]:
            logger.info(f"   {route['method']:6} {route['path']}")
        if len(self.handler.routes) > 10:
            logger.info(f"   ... 还有 {len(self.handler.routes) - 10} 个路由")

        async with server:
            await server.serve_forever()


# ==================== 主函数 ====================


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="MIYA API Server")
    parser.add_argument("--host", default="0.0.0.0", help="监听地址")
    parser.add_argument("--port", type=int, default=8765, help="监听端口")
    args = parser.parse_args()

    config = ServerConfig(host=args.host, port=args.port)
    server = MIYAServer(config)

    try:
        asyncio.run(server.start())
    except KeyboardInterrupt:
        logger.info("\n👋 服务器已停止")


if __name__ == "__main__":
    main()
