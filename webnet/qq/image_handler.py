"""
统一版QQ图片处理器
所有模型从 multi_model_config.json 模型池加载
"""

import hashlib
import logging
import os
import warnings
from datetime import datetime
from typing import Any, Dict, Optional

# 禁SSL警告
warnings.filterwarnings("ignore", message="Unverified HTTPS request")

import contextlib

import httpx

from .models import QQMessage

logger = logging.getLogger(__name__)


class QQImageHandler:
    """统一版QQ图片处理器 - 使用 MultiVisionAnalyzer"""

    def __init__(self, qq_net, personality=None):
        self.qq_net = qq_net
        self.personality = personality
        self.http_client = httpx.AsyncClient(
            timeout=60.0, verify=False, headers={"User-Agent": "Miya/1.0"}
        )
        self._analyzer = None
        self.image_cache: Dict[str, Dict] = {}
        self.cache_expire_seconds = 24 * 3600
        logger.info("[QQImageHandler] 初始化完成 - 使用多模型视觉分析系统")

    async def _get_analyzer(self):
        """获取或初始化视觉分析器"""
        if self._analyzer is None:
            from core.multi_vision_analyzer import get_vision_analyzer

            self._analyzer = await get_vision_analyzer()
        return self._analyzer

    def configure(self, enable_ocr: bool = False, enable_ai_analysis: bool = True):
        """配置处理器"""
        pass

    async def handle_image_message(self, event: Dict) -> Optional[QQMessage]:
        """处理图片消息"""
        try:
            image_info = self._extract_image_info(event)
            if not image_info:
                logger.warning("[QQImageHandler] 无法提取图片信息")
                return None

            image_data = await self._download_image(image_info)
            if not image_data:
                logger.warning("[QQImageHandler] 图片下载失败")
                return None

            image_id = hashlib.md5(image_data).hexdigest()

            # 分析图片
            analysis_result = await self._analyze_image(image_data)

            # 缓存分析结果
            self._cache_image(image_id, analysis_result)

            # 自动保存表情包
            await self._auto_save_emoji(event, image_data, image_info)

            # 构建消息对象（附加 image_analysis）
            message = QQMessage.from_dict(event)

            # 从消息段中提取文本内容（混合消息：文字+图片）
            raw_message = event.get("message", [])
            text_content = self._extract_text_from_segments(raw_message)
            if text_content:
                message.message = text_content

            # 检测是否@了机器人
            message.is_at_bot = self._is_at_bot(raw_message)
            message.at_list = self._extract_at_list(raw_message)

            message.image_data = image_data
            message.image_info = image_info
            message.image_analysis = analysis_result
            message.has_image = True

            logger.info(
                f"[QQImageHandler] 图片消息处理完成, 文本: {text_content[:50] if text_content else '无'}, at_bot: {message.is_at_bot}"
            )
            return message

        except Exception as e:
            logger.error(f"[QQImageHandler] 处理图片消息失败: {e}", exc_info=True)
            return None

    def _extract_text_from_segments(self, segments) -> str:
        """从消息段中提取文本内容"""
        if not segments:
            return ""
        text_parts = []
        for seg in segments:
            if isinstance(seg, dict):
                seg_type = seg.get("type", "")
                if seg_type == "text":
                    text_parts.append(seg.get("data", {}).get("text", ""))
        return " ".join(text_parts).strip()

    def _is_at_bot(self, segments) -> bool:
        """检测是否@了机器人"""
        if not self.qq_net or not self.qq_net.bot_qq:
            return False
        bot_qq_str = str(self.qq_net.bot_qq)
        for seg in segments:
            if isinstance(seg, dict) and seg.get("type") == "at":
                at_qq = str(seg.get("data", {}).get("qq", ""))
                if at_qq == bot_qq_str:
                    return True
        return False

    def _extract_at_list(self, segments) -> list:
        """提取@列表"""
        at_list = []
        for seg in segments:
            if isinstance(seg, dict) and seg.get("type") == "at":
                at_qq = seg.get("data", {}).get("qq", "")
                if at_qq and at_qq != "all":
                    with contextlib.suppress(ValueError, TypeError):
                        at_list.append(int(at_qq))
        return at_list

    async def _auto_save_emoji(self, event: Dict, image_data: bytes, image_info: Dict):
        """自动保存用户发送的表情包"""
        try:
            user_id = event.get("user_id") or event.get("sender_id")
            if not user_id:
                return

            try:
                from utils.auto_emoji_saver import get_auto_emoji_saver

                auto_saver = get_auto_emoji_saver()
                if not auto_saver or not auto_saver.is_enabled():
                    return

                save_result = await auto_saver.auto_save_emoji(
                    user_id=user_id, image_data=image_data, image_info=image_info
                )
                if save_result.get("success"):
                    logger.info("[QQImageHandler] 表情包已自动保存")
            except ImportError:
                pass
        except Exception as e:
            logger.debug(f"[QQImageHandler] 自动保存表情包失败: {e}")

    def _extract_image_info(self, event: Dict) -> Optional[Dict[str, Any]]:
        """从事件中提取图片信息"""
        message = event.get("message", [])
        for segment in message:
            if isinstance(segment, dict) and segment.get("type") == "image":
                data = segment.get("data", {})
                return {
                    "url": data.get("url", ""),
                    "file": data.get("file", ""),
                    "type": "image",
                    "size": data.get("size", 0),
                }
        return None

    async def _download_image(self, image_info: Dict) -> Optional[bytes]:
        """下载图片"""
        url = image_info.get("url")
        file_path = image_info.get("file")

        if not url and not file_path:
            return None

        try:
            if file_path and os.path.exists(file_path):
                with open(file_path, "rb") as f:
                    return f.read()

            if url:
                # 检查缓存
                cache_key = hashlib.md5(url.encode()).hexdigest()
                if cache_key in self.image_cache:
                    cached = self.image_cache[cache_key]
                    if (
                        datetime.now() - cached["timestamp"]
                    ).total_seconds() < self.cache_expire_seconds:
                        return cached["data"]

                response = await self.http_client.get(url)
                if response.status_code == 200:
                    image_data = response.content
                    self.image_cache[cache_key] = {
                        "data": image_data,
                        "timestamp": datetime.now(),
                    }
                    self._cleanup_cache()
                    return image_data
                else:
                    logger.error(
                        f"[QQImageHandler] 下载图片失败: HTTP {response.status_code}"
                    )
                    return None

            return None
        except Exception as e:
            logger.error(f"[QQImageHandler] 下载图片失败: {e}")
            return None

    async def _analyze_image(self, image_data: bytes) -> Dict[str, Any]:
        """使用 MultiVisionAnalyzer 分析图片"""
        try:
            analyzer = await self._get_analyzer()
            from core.multi_vision_analyzer import ImageAnalysisResult

            result: ImageAnalysisResult = await analyzer.analyze_image(
                image_data, max_retries=3
            )

            if result.success:
                return {
                    "success": True,
                    "has_text": result.has_text,
                    "text": result.text or "",
                    "text_confidence": result.text_confidence,
                    "description": result.description or "",
                    "labels": result.labels or [],
                    "nsfw_score": result.nsfw_score,
                    "size_kb": result.size_kb,
                    "format": result.format,
                    "model": result.model_used,
                    "provider": result.provider,
                    "confidence": result.confidence,
                    "processing_time_ms": result.processing_time_ms,
                    "api_call": result.model_used != "简单分析",
                }
            else:
                return self._create_fallback_result(image_data)

        except Exception as e:
            logger.error(f"[QQImageHandler] 视觉模型分析失败: {e}")
            return self._create_fallback_result(image_data)

    def _create_fallback_result(self, image_data: bytes) -> Dict[str, Any]:
        """创建 fallback 结果（本地简单分析）"""
        try:
            import io

            from PIL import Image

            image_format = self._detect_image_format(image_data)
            size_kb = len(image_data) / 1024

            image = Image.open(io.BytesIO(image_data))
            width, height = image.size

            description = (
                f"这是一张{image_format.upper()}格式的图片，"
                f"尺寸为{width}×{height}像素，大小约{size_kb:.1f}KB。"
            )

            labels = [image_format.upper(), "图片"]
            if width <= 200 and height <= 200:
                labels.append("小图")
            elif width >= 800 or height >= 800:
                labels.append("大图")

            return {
                "success": True,
                "has_text": False,
                "text": "",
                "text_confidence": 0.0,
                "description": description,
                "labels": labels,
                "nsfw_score": 0.0,
                "size_kb": size_kb,
                "format": image_format,
                "model": "本地分析",
                "provider": "local",
                "confidence": 0.3,
                "api_call": False,
            }
        except Exception as e:
            logger.debug(f"[QQImageHandler] Fallback 分析也失败: {e}")
            return {
                "success": False,
                "has_text": False,
                "text": "",
                "text_confidence": 0.0,
                "description": "暂时无法分析这张图片，请稍后再试~",
                "labels": ["分析失败"],
                "nsfw_score": 0.0,
                "size_kb": len(image_data) / 1024,
                "format": "unknown",
                "model": "none",
                "provider": "none",
                "confidence": 0.0,
                "api_call": False,
            }

    def _detect_image_format(self, image_data: bytes) -> str:
        """检测图片格式"""
        if len(image_data) < 8:
            return "unknown"
        if image_data.startswith(b"\xff\xd8\xff"):
            return "jpeg"
        elif image_data.startswith(b"\x89PNG\r\n\x1a\n"):
            return "png"
        elif image_data.startswith(b"GIF87a") or image_data.startswith(b"GIF89a"):
            return "gif"
        elif image_data.startswith(b"BM"):
            return "bmp"
        elif image_data.startswith(b"RIFF") and image_data[8:12] == b"WEBP":
            return "webp"
        return "unknown"

    def _cache_image(self, image_id: str, image_analysis: Dict[str, Any]):
        """缓存图片分析结果"""
        try:
            if (
                hasattr(self, "qq_net")
                and self.qq_net
                and hasattr(self.qq_net, "cache_manager")
            ):
                self.qq_net.cache_manager.set_image_analysis(image_id, image_analysis)
        except Exception as e:
            logger.debug(f"[QQImageHandler] 缓存分析结果失败: {e}")

    def _cleanup_cache(self):
        """清理过期缓存"""
        now = datetime.now()
        expired = [
            k
            for k, v in self.image_cache.items()
            if (now - v["timestamp"]).total_seconds() > self.cache_expire_seconds
        ]
        for k in expired:
            del self.image_cache[k]

    async def cleanup(self):
        """清理资源"""
        with contextlib.suppress(Exception):
            await self.http_client.aclose()
