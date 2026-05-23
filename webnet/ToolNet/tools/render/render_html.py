"""
HTML渲染工具
"""

import base64
import logging
from typing import Any, Dict

from webnet.ToolNet.base import BaseTool, ToolContext

logger = logging.getLogger(__name__)


class RenderHtmlTool(BaseTool):
    """HTML渲染工具"""

    @property
    def config(self) -> Dict[str, Any]:
        return {
            "name": "render_html",
            "description": "将HTML内容渲染为图片，方便在QQ中发送美观的排版内容。当需要发送格式化内容时使用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "html": {"type": "string", "description": "HTML内容"},
                    "width": {
                        "type": "integer",
                        "description": "图片宽度，默认800",
                        "default": 800,
                    },
                    "height": {
                        "type": "integer",
                        "description": "图片高度，默认自适应",
                        "default": 0,
                    },
                },
                "required": ["html"],
            },
        }

    async def execute(self, context: ToolContext, **kwargs) -> str:
        args = kwargs.get("args", {}) if kwargs else {}
        html_content = args.get("html", "")

        if not html_content:
            return "请提供HTML内容"

        width = args.get("width", 800)

        try:
            # 尝试使用playwright渲染
            try:
                from playwright.async_api import async_playwright

                async with async_playwright() as p:
                    browser = await p.chromium.launch()
                    page = await browser.new_page(
                        viewport={"width": width, "height": 800}
                    )

                    await page.set_content(html_content)
                    screenshot = await page.screenshot()
                    await browser.close()

                    # 返回base64图片
                    img_base64 = base64.b64encode(screenshot).decode()
                    return f"[CQ:image,file=base64://{img_base64}]"
            except ImportError:
                return "HTML渲染需要安装playwright: pip install playwright && playwright install chromium"

        except Exception as e:
            logger.error(f"HTML渲染失败: {e}")
            return f"渲染失败: {str(e)[:50]}"


def get_render_html_tool():
    return RenderHtmlTool()
