"""
天气查询工具
"""

import logging
from typing import Any, Dict

import httpx

from webnet.ToolNet.base import BaseTool, ToolContext

logger = logging.getLogger(__name__)


class WeatherQueryTool(BaseTool):
    """天气查询工具"""

    @property
    def config(self) -> Dict[str, Any]:
        return {
            "name": "weather_query",
            "description": "查询指定城市的天气情况，包括温度、天气状况、湿度、风力等。当用户问'天气'、'气温'、'下雨'等相关问题时使用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "要查询的城市名称，如'北京'、'上海'、'杭州'",
                    }
                },
                "required": ["city"],
            },
        }

    async def execute(self, context: ToolContext, **kwargs) -> str:
        args = kwargs.get("args", {}) if kwargs else {}
        city = args.get("city", "")

        if not city:
            return "请提供要查询的城市名称"

        return await self._query_weather(city)

    async def _query_weather(self, city: str) -> str:
        """查询天气"""
        try:
            # 使用免费天气API
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    "https://api.seniverse.com/v3/weather/now.json",
                    params={
                        "key": "your_key_here",  # 需要配置API key
                        "location": city,
                        "language": "zh-Hans",
                        "unit": "c",
                    },
                )

                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("results"):
                        result = data["results"][0]
                        now = result.get("now", {})
                        location = result.get("location", {})

                        return (
                            f"【{location.get('name', city)}天气】\n"
                            f"温度: {now.get('temperature', '未知')}°C\n"
                            f"天气: {now.get('text', '未知')}\n"
                            f"湿度: {now.get('humidity', '未知')}%\n"
                            f"风力: {now.get('wind_direction', '')} {now.get('wind_scale', '')}级"
                        )

            # 备用：简单返回
            return f"【{city}】天气查询服务暂时不可用，请稍后再试"

        except Exception as e:
            logger.error(f"天气查询失败: {e}")
            return f"查询天气失败: {str(e)[:50]}"


def get_weather_query_tool():
    return WeatherQueryTool()
