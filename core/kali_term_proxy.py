"""Kali 终端 WebSocket 代理

独立运行在 8008 端口，绕过弥娅 Web API 的安全中间件。
前端 xterm.js 直连 ws://localhost:8008 即可操作 Kali 容器终端。

启动: python kali_term_proxy.py
"""

import asyncio
import base64
import hashlib
import json
import logging
import os
import queue
import re
import secrets
import struct
import subprocess
import threading

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("kali-term")

KALI_CONTAINER = os.environ.get("MIYA_KALI_CONTAINER", "miya-kali")
ACCESS_TOKEN = os.environ.get("MIYA_KALI_TERMINAL_TOKEN", "")

if not ACCESS_TOKEN:
    _generated = secrets.token_urlsafe(32)
    ACCESS_TOKEN = os.environ.setdefault("MIYA_KALI_TERMINAL_TOKEN", _generated)
    logger.info(f"Kali 终端 Token 已生成: miya_kali_{_generated}")


def _find_script_pty() -> str | None:
    try:
        result = subprocess.run(
            [
                "docker",
                "exec",
                KALI_CONTAINER,
                "bash",
                "-c",
                "ps -o tty= -p $(pgrep -f 'script -q' | head -1)",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
        tty = result.stdout.strip()
        if tty and tty != "?":
            return f"/dev/{tty}"
    except Exception:
        pass
    return None


def _resize_pty(pty_path: str | None, cols: int, rows: int):
    if pty_path:
        try:
            subprocess.run(
                ["docker", "exec", KALI_CONTAINER, "bash", "-c", f"stty cols {cols} rows {rows} < {pty_path}"],
                capture_output=True,
                timeout=3,
            )
            return True
        except Exception:
            pass
    return False


async def check_container() -> bool:
    try:
        proc = await asyncio.create_subprocess_exec(
            "docker",
            "inspect",
            "-f",
            "{{.State.Running}}",
            KALI_CONTAINER,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        return stdout.decode().strip() == "true"
    except Exception as e:
        logger.warning(f"[kali-term] 容器状态检查失败: {e}")
        return False


def _relay_thread(proc: subprocess.Popen, q_out: queue.Queue, q_in: queue.Queue):
    def reader():
        try:
            while True:
                data = proc.stdout.read(4096)
                if not data:
                    q_out.put(None)
                    return
                q_out.put(data)
        except Exception:
            q_out.put(None)

    def writer():
        try:
            while True:
                data = q_in.get()
                if data is None:
                    return
                proc.stdin.write(data)
                proc.stdin.flush()
        except Exception:
            pass

    t_reader = threading.Thread(target=reader, daemon=True)
    t_reader.start()
    writer()
    t_reader.join(timeout=1)


def _send_frame(writer, data: bytes):
    plen = len(data)
    if plen < 126:
        header = bytes([0x82, plen])
    elif plen <= 65535:
        header = bytes([0x82, 0x7E]) + struct.pack(">H", plen)
    else:
        header = bytes([0x82, 0x7F]) + struct.pack(">Q", plen)
    writer.write(header + data)


async def websocket_handler(reader, writer):
    try:
        raw = await asyncio.wait_for(reader.readuntil(b"\r\n\r\n"), timeout=10)
    except asyncio.TimeoutError:
        logger.warning("[kali-term] WebSocket 握手超时")
        writer.close()
        return

    headers_text = raw.decode(errors="replace")
    peername = writer.get_extra_info("peername")
    client_ip = peername[0] if peername else "unknown"

    if client_ip not in ("127.0.0.1", "::1"):
        token_match = re.search(r"Authorization:\s*Bearer\s+(\S+)", headers_text)
        expected = f"miya_kali_{ACCESS_TOKEN}"
        if not token_match or not secrets.compare_digest(token_match.group(1), expected):
            logger.warning(f"[kali-term] Token 验证失败，来自: {peername}")
            writer.write(
                b"HTTP/1.1 403 Forbidden\r\n"
                b"Access-Control-Allow-Origin: http://localhost:9800\r\n"
                b"Content-Type: text/plain\r\n"
                b"\r\n"
            )
            await writer.drain()
            writer.close()
            return

    key_match = re.search(r"Sec-WebSocket-Key:\s*(\S+)", headers_text)
    if not key_match:
        writer.close()
        return

    key = key_match.group(1)
    accept = base64.b64encode(hashlib.sha1((key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode()).digest()).decode()

    writer.write(
        f"HTTP/1.1 101 Switching Protocols\r\n"
        f"Upgrade: websocket\r\n"
        f"Connection: Upgrade\r\n"
        f"Sec-WebSocket-Accept: {accept}\r\n"
        f"Access-Control-Allow-Origin: http://localhost:9800\r\n"
        f"\r\n".encode()
    )
    await writer.drain()

    if not await check_container():
        msg = (
            "\x1b[31mKali 容器未运行 (miya-kali)\x1b[0m\r\n\r\n"
            "\x1b[33m启动容器:\x1b[0m  docker start miya-kali\r\n"
            "\x1b[33m构建镜像:\x1b[0m  docker build -f Dockerfile.kali -t miya-kali .\r\n"
        )
        _send_frame(writer, msg.encode())
        await writer.drain()
        writer.close()
        return

    peername = writer.get_extra_info("peername")
    logger.info(f"[kali-term] Kali 终端连接: {peername}")

    tips = (
        b"\x1b[1;35m  \xe2\x96\xb8 Kali Terminal \xe2\x80\x94 miya-kali \xe2\x80\x94 bash\x1b[0m\r\n"
        b"\x1b[2m  Ctrl+C \xe4\xb8\xad\xe6\x96\xad  "
        b"Ctrl+D \xe9\x80\x80\xe5\x87\xba  "
        b"Ctrl+Shift+C \xe5\xa4\x8d\xe5\x88\xb6  "
        b"Ctrl+Shift+V \xe7\xb2\x98\xe8\xb4\xb4\x1b[0m\r\n\r\n"
    )
    _send_frame(writer, tips)
    await writer.drain()

    q_out = queue.Queue()
    q_in = queue.Queue()
    proc = subprocess.Popen(
        ["docker", "exec", "-i", KALI_CONTAINER, "script", "-q", "-c", "bash -i", "/dev/null"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        bufsize=0,
    )
    relay = threading.Thread(target=_relay_thread, args=(proc, q_out, q_in), daemon=True)
    relay.start()
    loop = asyncio.get_event_loop()

    # 发现 script 分配的 PTY 设备路径（用于无闪现 resize）
    pty_path = await loop.run_in_executor(None, _find_script_pty)
    if pty_path:
        logger.info(f"[kali-term] PTY 设备: {pty_path}")
    else:
        logger.info("[kali-term] PTY 未检测到，resize 将回退到 stdin 模式")

    async def docker_to_ws():
        try:
            while True:
                data = await loop.run_in_executor(None, q_out.get)
                if data is None:
                    logger.info("[kali-term] docker 进程输出结束")
                    break
                _send_frame(writer, data)
                await writer.drain()
        except (ConnectionError, BrokenPipeError):
            logger.info("[kali-term] docker→ws 连接已关闭")
        except Exception as e:
            logger.info(f"[kali-term] docker→ws 错误: {e}")

    async def ws_to_docker():
        try:
            while True:
                frame = await reader.readexactly(1)
                opcode = frame[0] & 0x0F
                if opcode == 0x8:
                    frame2 = await reader.readexactly(1)
                    clen = frame2[0] & 0x7F
                    if clen >= 2:
                        close_body = await reader.readexactly(clen)
                        mask_key = close_body[:4]
                        masked = close_body[4:]
                        c = bytes(masked[i] ^ mask_key[i % 4] for i in range(len(masked)))
                        code = struct.unpack(">H", c[:2])[0]
                        logger.info(f"[kali-term] 客户端发送了 close 帧 (code={code})")
                    else:
                        logger.info("[kali-term] 客户端发送了 close 帧")
                    break
                if opcode == 0x9:
                    frame2 = await reader.readexactly(1)
                    plen = frame2[0] & 0x7F
                    if plen > 0:
                        await reader.readexactly(plen)
                    writer.write(bytes([0x8A, 0]))
                    await writer.drain()
                    continue
                frame += await reader.readexactly(1)
                length = frame[1] & 0x7F
                if length == 126:
                    length = struct.unpack(">H", await reader.readexactly(2))[0]
                elif length == 127:
                    length = struct.unpack(">Q", await reader.readexactly(8))[0]
                mask_key = await reader.readexactly(4)
                payload = bytearray(await reader.readexactly(length))
                for i in range(len(payload)):
                    payload[i] ^= mask_key[i % 4]
                data = bytes(payload)
                if data.startswith(b"\x00\x00\x01"):
                    try:
                        ctrl = json.loads(data[3:].decode())
                        if ctrl.get("type") == "resize":
                            cols, rows = ctrl["cols"], ctrl["rows"]
                            logger.info(f"[kali-term] 终端尺寸变更: {cols}x{rows}")
                            if not _resize_pty(pty_path, cols, rows):
                                q_in.put(f"stty cols {cols} rows {rows}\n".encode())
                        continue
                    except Exception:
                        pass
                q_in.put(data)
        except (ConnectionError, BrokenPipeError, asyncio.IncompleteReadError):
            logger.info("[kali-term] ws→docker WebSocket 断开")
        except Exception as e:
            logger.info(f"[kali-term] ws→docker 错误: {e}")

    docker_task = asyncio.create_task(docker_to_ws())
    try:
        await ws_to_docker()
    except Exception as e:
        logger.info(f"[kali-term] 主循环退出: {e}")
    finally:
        docker_task.cancel()
        q_in.put(None)
        try:
            proc.terminate()
        except Exception:
            pass
        relay.join(timeout=2)
        try:
            writer.close()
        except Exception:
            pass
        logger.info("[kali-term] Kali 终端断开")


async def main():
    server = await asyncio.start_server(websocket_handler, "127.0.0.1", 8008)
    logger.info(f"[kali-term] Kali 终端代理启动: ws://127.0.0.1:8008")
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
