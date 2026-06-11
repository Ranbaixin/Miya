"""
QQ图片发送工具

支持发送图片到QQ群或私聊，支持多种图片来源
"""

import base64
import builtins
import contextlib
import logging
import os
from typing import Any, Dict, Optional

import aiofiles
import asyncio
import httpx

from webnet.ToolNet.base import BaseTool, ToolContext

logger = logging.getLogger(__name__)


class QQImageTool(BaseTool):
    """QQ图片发送工具"""

    @property
    def config(self) -> Dict[str, Any]:
        return {
            "name": "qq_image",
            "description": "发送图片到QQ群或私聊。支持本地文件路径、网络图片URL、Base64编码图片。用户说'发图片'、'发送图片'、'分享图片'时，必须调用此工具。",
            "parameters": {
                "type": "object",
                "properties": {
                    "target_type": {
                        "type": "string",
                        "description": "目标类型：group(群聊)或private(私聊)，默认为当前会话类型",
                        "enum": ["group", "private"],
                        "default": "group",
                    },
                    "target_id": {"type": "integer", "description": "目标ID（群号或用户QQ号），默认为当前用户ID或群ID"},
                    "image_source": {
                        "type": "string",
                        "description": "图片来源：local(本地文件)、url(网络地址)、base64(Base64编码)，默认为local",
                        "enum": ["local", "url", "base64"],
                        "default": "local",
                    },
                    "image_path": {
                        "type": "string",
                        "description": "图片路径或URL或Base64数据（当image_source为base64时，必须是有效的Base64图片数据）",
                    },
                    "caption": {"type": "string", "description": "图片说明文字，可选"},
                    "resize": {
                        "type": "boolean",
                        "description": "是否调整图片大小以适应QQ限制，默认为True",
                        "default": True,
                    },
                    "max_width": {"type": "integer", "description": "最大宽度（像素），默认为1920", "default": 1920},
                    "max_height": {"type": "integer", "description": "最大高度（像素），默认为1080", "default": 1080},
                },
                "required": ["image_path"],
            },
        }

    async def execute(self, args: Dict[str, Any], context: ToolContext) -> str:
        """执行图片发送"""
        try:
            # 获取参数
            target_type = args.get("target_type", "")
            if not target_type:
                target_type = self._detect_message_type(context)
            target_id = args.get("target_id", self._get_default_target_id(context))
            image_source = args.get("image_source", "local")
            image_path = args.get("image_path", "")
            caption = args.get("caption", "")
            resize = args.get("resize", True)
            max_width = args.get("max_width", 1920)
            max_height = args.get("max_height", 1080)

            if not image_path:
                return "❌ 请提供图片路径或数据"

            # 获取QQ客户端
            qq_client = getattr(context, "onebot_client", None)
            if not qq_client:
                return "❌ QQ客户端不可用"

            # 处理图片数据
            temp_file_path = await self._process_image(image_source, image_path, resize, max_width, max_height)

            if not temp_file_path:
                return "❌ 图片处理失败"

            try:
                # 发送图片
                if target_type == "group":
                    result = await qq_client.send_group_image(
                        group_id=target_id, image_path=temp_file_path, caption=caption
                    )
                    target_desc = f"群 {target_id}"
                else:
                    result = await qq_client.send_private_image(
                        user_id=target_id, image_path=temp_file_path, caption=caption
                    )
                    target_desc = f"用户 {target_id}"

                # 清理临时文件
                with contextlib.suppress(builtins.BaseException):
                    os.unlink(temp_file_path)

                if result and result.get("status") == "ok":
                    # 延迟清理临时文件，给 NapCat 时间读取
                    asyncio.ensure_future(self._delayed_cleanup(temp_file_path))
                    return f"✅ 图片已发送到 {target_desc}"
                else:
                    with contextlib.suppress(builtins.BaseException):
                        os.unlink(temp_file_path)
                    return f"❌ 图片发送失败: {result}"

            except Exception as e:
                with contextlib.suppress(builtins.BaseException):
                    os.unlink(temp_file_path)
                raise e

        except Exception as e:
            logger.error(f"图片发送失败: {e}", exc_info=True)
            return f"❌ 图片发送失败: {str(e)}"

    def _get_default_target_id(self, context: ToolContext) -> int:
        """获取默认目标ID"""
        if context.group_id:
            return context.group_id
        elif context.user_id:
            return context.user_id
        else:
            return 0

    def _detect_message_type(self, context: ToolContext) -> str:
        """自动检测当前聊天类型"""
        msg_type = getattr(context, "message_type", "") or ""
        if msg_type == "group" or (context.group_id and not context.user_id):
            return "group"
        return "private"

    async def _process_image(
        self, image_source: str, image_path: str, resize: bool, max_width: int, max_height: int
    ) -> Optional[str]:
        """处理图片数据，返回临时文件路径"""
        import tempfile

        temp_file = None
        temp_file_path = None

        try:
            # 根据来源处理图片
            if image_source == "local":
                # 本地文件
                if not os.path.exists(image_path):
                    raise FileNotFoundError(f"图片文件不存在: {image_path}")

                temp_file_path = image_path

            elif image_source == "url":
                # 网络图片
                temp_file = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
                temp_file_path = temp_file.name

                async with httpx.AsyncClient() as client:
                    response = await client.get(image_path, timeout=30.0)
                    if response.status_code != 200:
                        raise Exception(f"下载图片失败: HTTP {response.status_code}")

                    async with aiofiles.open(temp_file_path, "wb") as f:
                        await f.write(response.content)

                temp_file.close()

            elif image_source == "base64":
                # Base64数据
                temp_file = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
                temp_file_path = temp_file.name

                # 移除可能的Base64头部
                if "," in image_path:
                    image_path = image_path.split(",", 1)[1]

                image_data = base64.b64decode(image_path)
                async with aiofiles.open(temp_file_path, "wb") as f:
                    await f.write(image_data)

                temp_file.close()

            else:
                raise ValueError(f"不支持的图片来源: {image_source}")

            # 图片大小调整（可选）
            if resize and temp_file_path:
                await self._resize_image_if_needed(temp_file_path, max_width, max_height)

            return temp_file_path

        except Exception as e:
            logger.error(f"图片处理失败: {e}")

            # 清理临时文件
            if temp_file:
                try:
                    temp_file.close()
                    os.unlink(temp_file.name)
                except:
                    pass

            return None

    async def _resize_image_if_needed(self, image_path: str, max_width: int, max_height: int) -> None:
        """如果需要，调整图片大小"""
        try:
            from PIL import Image

            # 打开图片
            with Image.open(image_path) as img:
                width, height = img.size

                # 检查是否需要调整大小
                if width <= max_width and height <= max_height:
                    return

                # 计算新的尺寸
                if width > max_width or height > max_height:
                    # 保持宽高比
                    ratio = min(max_width / width, max_height / height)
                    new_width = int(width * ratio)
                    new_height = int(height * ratio)

                    # 调整大小
                    resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

                    # 保存回原文件
                    if image_path.lower().endswith(".png"):
                        resized_img.save(image_path, "PNG")
                    else:
                        resized_img.save(image_path, "JPEG", quality=85)

                    logger.info(f"图片已调整大小: {width}x{height} -> {new_width}x{new_height}")

        except ImportError:
            logger.warning("PIL库未安装，跳过图片大小调整")
        except Exception as e:
            logger.warning(f"图片大小调整失败: {e}")

    async def _delayed_cleanup(self, file_path: str):
        """延迟清理临时文件，给 OneBot 时间读取并上传"""
        await asyncio.sleep(30)
        with contextlib.suppress(Exception):
            if os.path.exists(file_path):
                os.unlink(file_path)
