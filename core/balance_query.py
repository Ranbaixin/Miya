"""
DeepSeek 账户余额查询 — QQ「余额」指令后端

接口：GET https://api.deepseek.com/user/balance（Bearer 鉴权，官方文档
api-docs.deepseek.com/zh-cn/api/get-user-balance）。当前 chat/vision/embedding
均走 DeepSeek，余额直接关系服务可用性。
"""

import logging
import os

import httpx

logger = logging.getLogger(__name__)

BALANCE_URL = "https://api.deepseek.com/user/balance"


def format_balance(data: dict) -> str:
    """格式化余额响应（纯函数，单测友好）"""
    is_available = bool(data.get("is_available", False))
    infos = data.get("balance_infos") or []
    if not infos:
        return "余额查询成功，但账户无余额信息"
    lines = ["【DeepSeek 账户余额】"]
    for info in infos:
        currency = info.get("currency", "CNY")
        symbol = "¥" if currency == "CNY" else f"{currency} "
        lines.append(f"总余额: {symbol}{info.get('total_balance', '?')}")
        lines.append(f"├ 赠送: {symbol}{info.get('granted_balance', '0.00')}")
        lines.append(f"└ 充值: {symbol}{info.get('topped_up_balance', '0.00')}")
    lines.append("状态: ✅ 可用" if is_available else "状态: ⚠️ 账户不可用")
    return "\n".join(lines)


async def fetch_balance(api_key: str = None, timeout: float = 10.0) -> tuple:
    """查询余额。返回 (ok: bool, text: str)，text 为已格式化的中文回复，不抛异常。"""
    key = api_key or os.getenv("DEEPSEEK_API_KEY", "")
    if not key:
        return False, "未配置 DEEPSEEK_API_KEY，无法查询余额"
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(BALANCE_URL, headers={"Authorization": f"Bearer {key}"})
    except (httpx.TimeoutException, httpx.HTTPError, OSError) as e:
        logger.warning(f"[余额查询] 网络异常: {e}")
        return False, "余额查询失败（网络异常），稍后再试"
    if resp.status_code == 401:
        return False, "API Key 无效（401），请检查 DEEPSEEK_API_KEY"
    if resp.status_code != 200:
        return False, f"查询失败（HTTP {resp.status_code}）"
    try:
        return True, format_balance(resp.json())
    except ValueError:
        logger.warning("[余额查询] 响应非 JSON")
        return False, "余额查询失败（响应格式异常）"
