"""
弥娅前端兼容配置层 - 直接使用弥娅系统的配置
"""

import json
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

# 获取配置目录
_CONFIG_DIR = Path(__file__).parent.parent.parent / "config"

# 加载所有弥娅配置
_ALL_CONFIGS = {}


def _load_config(name):
    """加载配置文件"""
    if name in _ALL_CONFIGS:
        return _ALL_CONFIGS[name]

    config_path = _CONFIG_DIR / f"{name}.json"
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                _ALL_CONFIGS[name] = json.load(f)
                logger.info(f"加载配置 {name} 成功")
        except Exception as e:
            logger.warning(f"加载配置 {name} 失败: {e}")
            _ALL_CONFIGS[name] = {}
    else:
        _ALL_CONFIGS[name] = {}
    return _ALL_CONFIGS[name]


# 预加载关键配置
_TTS_CONFIG = _load_config("tts_config")
_SYSTEM_CONSTANTS = _load_config("system_constants")
_API_ENDPOINTS = _load_config("api_endpoints")
_MULTI_MODEL_CONFIG = _load_config("multi_model_config")
_TEXT_CONFIG = _load_config("text_config")
_PERSONALITY_CONFIG = _load_config("personality_config")
_MEMORY_CONFIG = _load_config("memory_config")
_SOUL_GENERATOR_CONFIG = _load_config("soul_generator_config")
_WEB_SEARCH_CONFIG = _load_config("web_search_config")
_AGENT_ROUTING_CONFIG = _load_config("agent_routing_config")


def _get_miya_config(category, key, default=None):
    """从弥娅配置获取值"""
    sys_const = _SYSTEM_CONSTANTS.get(category, {})
    return sys_const.get(key, default)


# ==================== 配置类定义 ====================


class DynamicMiyaConfig:
    """动态弥娅配置 - 自动返回正确类型"""

    # 需要返回 bool 的属性
    BOOL_ATTRS = {
        "enabled",
        "gpt_sovits_enabled",
        "vits_enabled",
        "gpt_sovits_ref_free",
        "gpt_sovits_filter_brackets",
        "gpt_sovits_filter_special_chars",
        "auto_play",
        "interrupt_playback",
        "local_playback_enabled",
        "streaming_enabled",
        "smart_tts_enabled",
        "qq_message_split",
        "voiceprint_enabled",
        "active_communication",
        "diary_enabled",
        "stream_mode",
        "voice_enabled",
        "debug",
        "version",
        "log_level",
        "diary_auto_save",
        "live2d_enabled",
        "voice_input_enabled",
        "gpt_sovits_enabled",
        "vits_enabled",
        "gpt_sovits_ref_free",
        "gpt_sovits_filter_brackets",
        "gpt_sovits_filter_special_chars",
        "auto_play",
        "interrupt_playback",
        "model",
        "provider",
        "engine",
    }

    # 需要返回 int 的属性
    INT_ATTRS = {
        "port",
        "asr_port",
        "tts_port",
        "record_duration",
        "vits_voice_id",
        "max_tokens",
        "temperature",
        "top_k",
        "top_p",
        "max_history_rounds",
        "max_message_length",
        "qq_max_message_length",
        "timeout",
    }

    # 需要返回 string 的属性
    STRING_ATTRS = {
        "model",
        "provider",
        "engine",
        "language",
        "log_level",
        "version",
        "default_engine",
        "default_voice",
        "gpt_sovits_url",
        "gpt_sovits_ref_text",
        "gpt_sovits_ref_audio_path",
        "vits_url",
    }

    # 需要返回 int 的属性
    INT_ATTRS = {
        "window_bg_alpha",
    }

    # 需要返回 float 的属性
    FLOAT_ATTRS = {
        "gpt_sovits_speed",
        "gpt_sovits_pitch",
        "vad_threshold",
        "frequency_penalty",
        "presence_penalty",
        "similarity_threshold",
        "local_playback_volume",
    }

    def __init__(self, defaults=None):
        self._defaults = defaults or {}
        self._data = {}

    def __getattr__(self, attr):
        # 先检查 _data
        if attr in self._data:
            return self._data[attr]

        # 检查默认值
        if attr in self._defaults:
            value = self._defaults[attr]
            self._data[attr] = value
            return value

        # 根据属性名返回正确类型的默认值
        if attr in self.BOOL_ATTRS:
            return False
        elif attr in self.INT_ATTRS:
            return 0
        elif attr in self.FLOAT_ATTRS:
            return 0.0
        elif attr in self.STRING_ATTRS:
            return ""
        return ""


class TtsConfig(DynamicMiyaConfig):
    """TTS配置 - 直接使用tts_config.json"""

    def __init__(self):
        super().__init__()
        engines = _TTS_CONFIG.get("engines", {})
        gpt = engines.get("gpt_sovits", {})

        # 从配置加载
        self._data = {
            "enabled": _TTS_CONFIG.get("enabled", True),
            "gpt_sovits_enabled": gpt.get("enabled", False),
            "vits_enabled": gpt.get("enabled", False),
            "gpt_sovits_speed": gpt.get("speed", 1.0),
            "gpt_sovits_pitch": 0,
            "gpt_sovits_ref_free": gpt.get("ref_free", False),
            "gpt_sovits_filter_brackets": gpt.get("filter_brackets", True),
            "gpt_sovits_filter_special_chars": gpt.get("filter_special_chars", True),
            "port": self._parse_port(gpt.get("api_url", "http://127.0.0.1:9880")),
            "local_playback_enabled": _TTS_CONFIG.get("local_playback_enabled", True),
            "local_playback_volume": _TTS_CONFIG.get("local_playback_volume", 1.0),
            "engine": "gpt_sovits",
            "default_engine": "edge_tts",
            "default_voice": "zh-CN-XiaoyiNeural",
            "gpt_sovits_url": "http://127.0.0.1:9880",
            "gpt_sovits_ref_text": "",
            "gpt_sovits_ref_audio_path": "",
            "vits_url": "http://127.0.0.1:7860",
        }

    def _parse_port(self, url):
        if ":" in str(url):
            try:
                return int(url.split(":")[-1])
            except:
                pass
        return 9880

    def __getattr__(self, attr):
        if attr in self._data:
            return self._data[attr]
        # 动态属性处理
        if attr == "port":
            return self._data.get("port", 9880)
        if attr in self.BOOL_ATTRS:
            return self._data.get(attr, False)
        return self._data.get(attr, 0)


class VoiceRealtimeConfig(DynamicMiyaConfig):
    """实时语音配置"""

    def __init__(self):
        super().__init__(
            {
                "enabled": False,
                "auto_play": True,
                "interrupt_playback": True,
                "asr_port": 5000,
                "tts_port": 5001,
                "record_duration": 10,
                "vad_threshold": 0.5,
                "provider": "openai",
                "language": "zh",
                "model": "whisper-1",
                "engine": "openai",
            }
        )


class SystemConfig(DynamicMiyaConfig):
    """系统配置"""

    def __init__(self):
        super().__init__(
            {
                "version": "1.0.0",
                "debug": False,
                "log_level": "INFO",
                "stream_mode": False,
                "window": True,
                "active_communication": False,
                "voiceprint_enabled": False,
            }
        )


class ApiConfig(DynamicMiyaConfig):
    """API配置 - 自动检测弥娅API端口"""

    def __init__(self):
        api_const = _SYSTEM_CONSTANTS.get("api", {})
        msg_const = _SYSTEM_CONSTANTS.get("message", {})

        # 自动检测可用端口
        detected_port = self._detect_api_port()

        super().__init__(
            {
                "max_tokens": api_const.get("max_tokens_default", 4096),
                "max_history_rounds": msg_const.get("max_history_length", 10),
                "context_load_days": 7,
                "temperature": api_const.get("temperature_default", 0.7),
                "model": "gpt-4",
                "base_url": f"http://localhost:{detected_port}",
                "host": "127.0.0.1",
                "port": detected_port,
            }
        )

    def _detect_api_port(self) -> int:
        """检测弥娅API实际使用的端口"""
        import socket
        import httpx

        # 检查常见端口 (按可能性排序)
        for port in [8003, 8000, 8001, 8002, 8004, 8005]:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(0.5)
                    if s.connect_ex(("127.0.0.1", port)) == 0:
                        # 端口开放，进一步确认是弥娅API
                        try:
                            resp = httpx.get(
                                f"http://127.0.0.1:{port}/api/health", timeout=1
                            )
                            if resp.status_code == 200:
                                logger.info(f"[API配置] 检测到弥娅API端口: {port}")
                                return port
                        except:
                            pass
            except:
                pass

        # 默认返回8000
        logger.warning("[API配置] 未检测到弥娅API，使用默认端口8000")
        return 8000


class UiConfig(DynamicMiyaConfig):
    """UI配置 - 从弥娅配置读取"""

    def __init__(self):
        sys_const = _SYSTEM_CONSTANTS.get("system", {})
        ui_const = _SYSTEM_CONSTANTS.get("ui", {})
        super().__init__(
            {
                "theme": ui_const.get("theme", "dark"),
                "font_size": ui_const.get("font_size", 14),
                "font_family": ui_const.get("font_family", "微软雅黑"),
                "bg_alpha": 0.5,  # 0-1 范围，0.5 表示50%透明
                "sidebar_width": ui_const.get("sidebar_width", 280),
                "input_height": ui_const.get("input_height", 120),
                "max_input_length": 2000,
                "max_history": 100,
                "message_animation": True,
                "auto_scroll": True,
                "show_timestamp": True,
                "enter_to_send": True,
                "sound_enabled": False,
                "notification_enabled": True,
                "window_bg_alpha": 180,  # 0-255 范围，180 ≈ 70% 不透明
                "title_bar_height": 40,
                "title_bar_color": "#2D2D2D",
                "input_bg_color": "#3D3D3D",
                "send_button_color": "#4A90D9",
                "user_bubble_color": "#4A90D9",
                "ai_bubble_color": "#3D3D3D",
                "user_name": "user",
                "default_model": "gpt-4",
                "mac_btn_size": 12,
                "mac_btn_margin": 10,
                "mac_btn_gap": 8,
                "animation_duration": 200,
            }
        )


class Live2DConfig(DynamicMiyaConfig):
    """Live2D配置"""

    def __init__(self):
        super().__init__(
            {"enable": False, "enabled": False, "model_path": "", "motion_priority": 0}
        )


class VoiceConfig(DynamicMiyaConfig):
    """语音配置"""

    def __init__(self):
        super().__init__({"enable": False, "voice_engine": ""})


class ComputerControlConfig(DynamicMiyaConfig):
    """电脑控制配置"""

    def __init__(self):
        super().__init__(
            {
                "model": "gpt-4",
                "enabled": False,
                "grounding_model": "",
                "grounding_api_key": "",
                "grounding_url": "",
                "vision_model": "",
            }
        )


class GragConfig(DynamicMiyaConfig):
    """Grag配置"""

    def __init__(self):
        super().__init__(
            {
                "neo4j_uri": "bolt://localhost:7687",
                "neo4j_user": "neo4j",
                "neo4j_password": "",
                "similarity_threshold": 0.7,
            }
        )


class MqttConfig(DynamicMiyaConfig):
    """MQTT配置"""

    def __init__(self):
        super().__init__({"port": 1883, "enabled": False})


class NetworkConfig(DynamicMiyaConfig):
    """网络配置"""

    def __init__(self):
        net = _SYSTEM_CONSTANTS.get("network", {})
        super().__init__({"timeout": net.get("connection_timeout", 30), "proxy": ""})


class MiyaPortalConfig(DynamicMiyaConfig):
    """弥娅门户配置 - 预留扩展接口"""

    def __init__(self):
        super().__init__({"enabled": False})


# ==================== 主配置对象 ====================


class MiyaConfig:
    """弥娅配置主对象 - 为前端提供兼容"""

    def __init__(self):
        self.constants = _SYSTEM_CONSTANTS
        self._ai_name = "弥娅"
        self._server_port = 8001

    @property
    def AI_NAME(self):
        return self._ai_name

    @property
    def ui(self):
        return UiConfig()

    @property
    def live2d(self):
        return Live2DConfig()

    @property
    def voice(self):
        return VoiceConfig()

    @property
    def system(self):
        return SystemConfig()

    @property
    def api(self):
        return ApiConfig()

    @property
    def api_server(self):
        """api_server 是 api 的别名，保持与原代码兼容"""
        return self.api

    @property
    def miya_portal(self):
        return MiyaPortalConfig()

    @property
    def network(self):
        return NetworkConfig()

    @property
    def grag(self):
        return GragConfig()

    @property
    def computer_control(self):
        return ComputerControlConfig()

    @property
    def voice_realtime(self):
        return VoiceRealtimeConfig()

    @property
    def tts(self):
        return TtsConfig()

    @property
    def mqtt(self):
        return MqttConfig()

    def get(self, key, default=None):
        return _SYSTEM_CONSTANTS.get("system", {}).get(key, default)

    def get_prompt(self, key):
        prompts = _TEXT_CONFIG.get("prompts", {})
        return prompts.get(key, "")

    def save_prompt(self, key, value):
        pass

    def get_server_port(self):
        return self._server_port


# 导出配置对象
config = MiyaConfig()
logger = logging.getLogger(__name__)

AI_NAME = "弥娅"
UIConfig = UiConfig
Live2DConfig = Live2DConfig
VoiceConfig = VoiceConfig


def add_config_listener(callback):
    """添加配置监听器（空实现）"""
    pass


def get_prompt(key):
    """获取提示词"""
    return config.get_prompt(key)


def save_prompt(key, value):
    """保存提示词"""
    config.save_prompt(key, value)


def get_server_port():
    """获取服务器端口"""
    return config.get_server_port()


# ============ 弥娅配置访问接口 ============


def get_tts_config():
    """获取TTS配置"""
    return _TTS_CONFIG


def get_system_constants():
    """获取系统常量"""
    return _SYSTEM_CONSTANTS


def get_api_endpoints():
    """获取API端点"""
    return _API_ENDPOINTS


def get_multi_model_config():
    """获取多模型配置"""
    return _MULTI_MODEL_CONFIG


def get_text_config():
    """获取文本配置"""
    return _TEXT_CONFIG


def get_personality_config():
    """获取人格配置"""
    return _PERSONALITY_CONFIG


def get_memory_config():
    """获取记忆配置"""
    return _MEMORY_CONFIG


def get_soul_generator_config():
    """获取灵魂生成器配置"""
    return _SOUL_GENERATOR_CONFIG


def get_web_search_config():
    """获取网页搜索配置"""
    return _WEB_SEARCH_CONFIG


def get_agent_routing_config():
    """获取Agent路由配置"""
    return _AGENT_ROUTING_CONFIG
