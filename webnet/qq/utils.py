"""
QQ工具实用函数
"""

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


class OneBotAPICompatibility:
    """OneBot API兼容性检查器"""
    
    # 标准OneBot API列表及其支持状态
    STANDARD_APIS = {
        "send_private_msg": {"description": "发送私聊消息", "required": True},
        "send_group_msg": {"description": "发送群消息", "required": True},
        "send_like": {"description": "发送好友点赞", "required": False},
        "send_poke": {"description": "发送戳一戳", "required": False},
        "get_friend_list": {"description": "获取好友列表", "required": False},
        "get_group_list": {"description": "获取群列表", "required": False},
        "get_group_member_list": {"description": "获取群成员列表", "required": False},
        "get_msg": {"description": "获取消息", "required": False},
        "delete_msg": {"description": "撤回消息", "required": False},
        "set_group_kick": {"description": "群组踢人", "required": False},
        "set_group_ban": {"description": "群组禁言", "required": False},
    }
    
    @classmethod
    async def check_api_support(cls, client, api_name: str) -> Dict[str, Any]:
        """检查API是否支持"""
        try:
            # 尝试调用API的简单版本
            if api_name == "send_like":
                # 发送测试点赞（给自己）
                await client.send_like(int(client.bot_qq), 1)
                return {"supported": True, "message": "API支持点赞功能"}
            elif api_name == "send_poke":
                await client.send_poke(int(client.bot_qq))
                return {"supported": True, "message": "API支持戳一戳功能"}
            else:
                return {"supported": False, "message": f"未知API: {api_name}"}
        except Exception as e:
            error_msg = str(e)
            if "retcode=1200" in error_msg or "网络连接异常" in error_msg:
                return {
                    "supported": False,
                    "message": f"API不支持或网络异常: {api_name}",
                    "error": error_msg
                }
            elif "不支持" in error_msg or "未实现" in error_msg:
                return {
                    "supported": False,
                    "message": f"OneBot实现不支持此API: {api_name}",
                    "error": error_msg
                }
            else:
                return {
                    "supported": True,
                    "message": f"API调用异常但可能支持: {api_name}",
                    "error": error_msg,
                    "warning": True
                }
    
    @classmethod
    async def get_supported_apis(cls, client) -> Dict[str, Dict[str, Any]]:
        """获取支持的API列表"""
        supported_apis = {}
        
        for api_name, api_info in cls.STANDARD_APIS.items():
            try:
                result = await cls.check_api_support(client, api_name)
                supported_apis[api_name] = {
                    **api_info,
                    **result
                }
            except Exception as e:
                supported_apis[api_name] = {
                    **api_info,
                    "supported": False,
                    "message": f"检查失败: {str(e)}",
                    "error": str(e)
                }
        
        return supported_apis


def format_qq_message(user_id: int, message: str) -> str:
    """格式化QQ消息"""
    return f"[QQ{user_id}] {message}"


def extract_qq_numbers(text: str) -> list:
    """从文本中提取QQ号"""
    import re
    
    # 匹配QQ号（5-12位数字）
    qq_pattern = r'(?<!\d)\d{5,12}(?!\d)'
    matches = re.findall(qq_pattern, text)
    
    # 过滤掉明显不是QQ号的数字（如年份、时间等）
    valid_qqs = []
    for match in matches:
        # QQ号通常不以0开头（除了某些特殊号段）
        if not match.startswith('0'):
            valid_qqs.append(int(match))
    
    return valid_qqs


def is_qq_admin(user_id: int, super_admins: list) -> bool:
    """检查用户是否为管理员"""
    return str(user_id) in [str(admin) for admin in super_admins]


def create_at_message(user_id: int) -> str:
    """创建@消息"""
    return f"[CQ:at,qq={user_id}]"


def create_image_message(image_url: str) -> str:
    """创建图片消息"""
    return f"[CQ:image,file={image_url}]"


def create_voice_message(voice_url: str) -> str:
    """创建语音消息"""
    return f"[CQ:record,file={voice_url}]"


def create_file_message(file_url: str) -> str:
    """创建文件消息"""
    return f"[CQ:file,file={file_url}]"


def create_face_message(face_id: int) -> str:
    """创建表情消息"""
    return f"[CQ:face,id={face_id}]"


def parse_cq_code(message: str) -> list:
    """解析CQ码"""
    import re
    
    cq_pattern = r'\[CQ:([^,\]]+)(?:,([^\]]+))?\]'
    matches = re.findall(cq_pattern, message)
    
    parsed = []
    for match in matches:
        cq_type = match[0]
        params_str = match[1] if len(match) > 1 else ""
        
        params = {}
        if params_str:
            param_pairs = params_str.split(',')
            for pair in param_pairs:
                if '=' in pair:
                    key, value = pair.split('=', 1)
                    params[key] = value
        
        parsed.append({
            "type": cq_type,
            "params": params
        })
    
    return parsed


def escape_cq_code(text: str) -> str:
    """转义CQ码特殊字符"""
    # 需要转义的字符
    escape_chars = ['[', ']', ',', '&']
    
    for char in escape_chars:
        text = text.replace(char, f'&#{ord(char)};')
    
    return text


def unescape_cq_code(text: str) -> str:
    """反转义CQ码特殊字符"""
    import html
    
    # 先使用HTML实体解码
    text = html.unescape(text)
    
    return text


class QQMessageBuilder:
    """QQ消息构建器"""
    
    def __init__(self):
        self.parts = []
    
    def add_text(self, text: str) -> 'QQMessageBuilder':
        """添加文本"""
        self.parts.append(text)
        return self
    
    def add_at(self, user_id: int) -> 'QQMessageBuilder':
        """添加@"""
        self.parts.append(create_at_message(user_id))
        return self
    
    def add_image(self, image_url: str) -> 'QQMessageBuilder':
        """添加图片"""
        self.parts.append(create_image_message(image_url))
        return self
    
    def add_voice(self, voice_url: str) -> 'QQMessageBuilder':
        """添加语音"""
        self.parts.append(create_voice_message(voice_url))
        return self
    
    def add_file(self, file_url: str) -> 'QQMessageBuilder':
        """添加文件"""
        self.parts.append(create_file_message(file_url))
        return self
    
    def add_face(self, face_id: int) -> 'QQMessageBuilder':
        """添加表情"""
        self.parts.append(create_face_message(face_id))
        return self
    
    def add_line_break(self) -> 'QQMessageBuilder':
        """添加换行"""
        self.parts.append('\n')
        return self
    
    def build(self) -> str:
        """构建消息"""
        return ''.join(self.parts)
    
    def build_list(self) -> list:
        """构建消息列表（兼容数组格式）"""
        messages = []
        
        for part in self.parts:
            if part.startswith('[CQ:'):
                # 解析CQ码为对象
                messages.append(self._parse_cq_code(part))
            else:
                # 文本作为字符串
                messages.append(part)
        
        return messages
    
    def _parse_cq_code(self, cq_code: str) -> dict:
        """解析CQ码为OneBot消息段对象"""
        # 移除[CQ:和末尾的]
        content = cq_code[4:-1]
        
        # 分割类型和参数
        if ',' in content:
            cq_type, params_str = content.split(',', 1)
            cq_type = cq_type.strip()
            
            # 解析参数
            data = {}
            for param in params_str.split(','):
                if '=' in param:
                    key, value = param.split('=', 1)
                    data[key.strip()] = value.strip()
            
            return {"type": cq_type, "data": data}
        else:
            # 没有参数的CQ码
            return {"type": content.strip(), "data": {}}


# 点赞功能备选方案
class LikeFallback:
    """点赞功能备选方案"""
    
    @staticmethod
    async def send_like_fallback(client, user_id: int, times: int = 1) -> Dict[str, Any]:
        """点赞功能备选方案"""
        try:
            # 尝试使用标准API
            return await client.send_like(user_id, times)
        except Exception as e:
            error_msg = str(e)
            
            if "retcode=1200" in error_msg or "网络连接异常" in error_msg:
                logger.warning(f"点赞API失败，使用备选方案: {error_msg}")
                
                # 备选方案1：发送表情消息代替点赞
                try:
                    # 发送表情消息
                    emoji_message = "👍" * min(times, 10)
                    result = await client.send_private_msg(
                        user_id=user_id,
                        message=f"（点赞备选）{emoji_message}"
                    )
                    
                    return {
                        "status": "fallback",
                        "message": f"已发送表情代替点赞: {emoji_message}",
                        "original_error": error_msg,
                        "data": result
                    }
                except Exception as fallback_error:
                    # 备选方案2：记录日志，返回友好提示
                    logger.error(f"点赞备选方案也失败: {fallback_error}")
                    
                    return {
                        "status": "error",
                        "message": "点赞功能暂时不可用",
                        "original_error": error_msg,
                        "fallback_error": str(fallback_error),
                        "suggestion": "请检查OneBot服务是否支持点赞API，或稍后重试"
                    }
            else:
                # 其他错误直接抛出
                raise


# 工具函数：检查OneBot连接状态
async def check_onebot_connection(client) -> Dict[str, Any]:
    """检查OneBot连接状态"""
    try:
        # 尝试获取机器人自身信息
        from webnet.qq.client import QQOneBotClient
        
        if not isinstance(client, QQOneBotClient):
            return {"connected": False, "message": "客户端类型错误"}
        
        # 检查WebSocket连接
        if not client.ws or client.ws.closed:
            return {"connected": False, "message": "WebSocket连接已关闭"}
        
        # 尝试简单API调用
        try:
            # 获取机器人QQ号
            bot_qq = getattr(client, 'bot_qq', None)
            
            return {
                "connected": True,
                "message": "OneBot连接正常",
                "bot_qq": bot_qq,
                "ws_url": getattr(client, 'ws_url', 'unknown'),
                "ws_open": not client.ws.closed
            }
        except Exception as api_error:
            return {
                "connected": False,
                "message": f"API调用失败: {str(api_error)}",
                "ws_open": not client.ws.closed
            }
            
    except Exception as e:
        return {
            "connected": False,
            "message": f"连接检查失败: {str(e)}"
        }
