"""配置更新器

负责应用配置更新到各个组件
"""

import logging
from typing import Any, Dict, Optional

from core.config_event_system import ConfigEventPublisher

logger = logging.getLogger(__name__)


class ConfigUpdater:
    """配置更新器

    职责：
    - 更新各个系统的配置
    - 处理不同配置类型的更新逻辑
    - 验证配置值的有效性
    """

    # 需要重启才能生效的配置项
    RESTART_REQUIRED_KEYS = {
        "log_level",
        "log_file_path",
        "log_max_size",
        "log_backup_count",
        "mqtt_broker",
        "mqtt_port",
        "mqtt_username",
        "mqtt_password",
        "mcp_server_enabled",
        "mcp_server_host",
        "mcp_server_port",
        "api_enabled",
        "api_host",
        "api_port",
    }

    def __init__(self, event_publisher: ConfigEventPublisher):
        """
        初始化配置更新器

        Args:
            event_publisher: 事件发布器实例
        """
        self.event_publisher = event_publisher

    def apply_updates(self, new_config: Dict[str, Any], changes: Dict[str, Any], context: Any) -> None:
        """应用配置更新

        Args:
            new_config: 新配置
            changes: 配置变更
            context: 配置上下文（包含各系统实例）
        """
        changed_keys = set(changes.keys())

        # 更新队列管理器
        if hasattr(context, "queue_manager") and context.queue_manager and "queue_intervals" in changed_keys:
            intervals = new_config.get("queue_intervals", {})
            context.queue_manager.update_model_intervals(intervals)
            logger.info("[配置更新] 队列间隔已更新")

        # 更新人格系统
        if hasattr(context, "personality") and context.personality and "personality" in changed_keys:
            personality_config = new_config.get("personality", {})
            self._update_personality_config(context.personality, personality_config)
            logger.info("[配置更新] 人格配置已更新")

        # 更新情绪系统
        if hasattr(context, "emotion") and context.emotion and "emotion" in changed_keys:
            emotion_config = new_config.get("emotion", {})
            self._update_emotion_config(context.emotion, emotion_config)
            logger.info("[配置更新] 情绪配置已更新")

        # 更新记忆系统
        if hasattr(context, "memory") and context.memory and "memory" in changed_keys:
            memory_config = new_config.get("memory", {})
            self._update_memory_config(context.memory, memory_config)
            logger.info("[配置更新] 记忆配置已更新")

        # 更新TTS配置
        if "tts" in changed_keys:
            tts_config = new_config.get("tts", {})
            self._update_tts_config(tts_config, context)
            logger.info("[配置更新] TTS配置已更新")

        # 更新WebAPI配置
        if hasattr(context, "web_api") and context.web_api and "web_api" in changed_keys:
            webapi_config = new_config.get("web_api", {})
            self._update_webapi_config(context.web_api, webapi_config)
            logger.info("[配置更新] WebAPI配置已更新")

        # 更新终端管理器配置
        if hasattr(context, "terminal_manager") and context.terminal_manager and "terminal" in changed_keys:
            terminal_config = new_config.get("terminal", {})
            self._update_terminal_config(context.terminal_manager, terminal_config)
            logger.info("[配置更新] 终端管理器配置已更新")

        # 更新IoT管理器配置
        if hasattr(context, "iot_manager") and context.iot_manager and "iot" in changed_keys:
            iot_config = new_config.get("iot", {})
            self._update_iot_config(context.iot_manager, iot_config)
            logger.info("[配置更新] IoT管理器配置已更新")

    def _update_personality_config(self, personality, config: Dict[str, Any]) -> None:
        """更新人格配置"""
        try:
            # 更新人格向量
            vectors = config.get("vectors", {})
            for key, value in vectors.items():
                if hasattr(personality, "vectors") and key in personality.vectors:
                    personality.vectors[key] = value

            # 更新形态
            form = config.get("form")
            if form:
                personality.set_form(form)

        except Exception as e:
            logger.error(f"[配置更新] 更新人格配置失败: {e}", exc_info=True)

    def _update_emotion_config(self, emotion, config: Dict[str, Any]) -> None:
        """更新情绪配置"""
        try:
            # 更新情绪衰减率
            decay_rate = config.get("decay_rate")
            if decay_rate:
                if 0.0 <= decay_rate <= 1.0:
                    if hasattr(emotion, "decay_rate"):
                        emotion.decay_rate = decay_rate
                    elif hasattr(emotion, "set_decay_rate"):
                        emotion.set_decay_rate(decay_rate)
                else:
                    logger.warning(f"[配置更新] 情绪衰减率超出范围 (0.0-1.0): {decay_rate}")

            # 更新情绪影响因子
            influence_factor = config.get("influence_factor")
            if influence_factor:
                if 0.0 <= influence_factor <= 2.0:
                    if hasattr(emotion, "influence_factor"):
                        emotion.influence_factor = influence_factor
                    elif hasattr(emotion, "set_influence_factor"):
                        emotion.set_influence_factor(influence_factor)
                else:
                    logger.warning(f"[配置更新] 情绪影响因子超出范围 (0.0-2.0): {influence_factor}")

        except Exception as e:
            logger.error(f"[配置更新] 更新情绪配置失败: {e}", exc_info=True)

    def _update_memory_config(self, memory, config: Dict[str, Any]) -> None:
        """更新记忆配置"""
        try:
            # 更新记忆保留天数
            retention_days = config.get("retention_days")
            if retention_days and retention_days >= 1:
                if hasattr(memory, "retention_days"):
                    memory.retention_days = retention_days
                elif hasattr(memory, "set_retention_days"):
                    memory.set_retention_days(retention_days)

            # 更新记忆最大容量
            max_size = config.get("max_size")
            if max_size and max_size >= 100:
                if hasattr(memory, "max_size"):
                    memory.max_size = max_size
                elif hasattr(memory, "set_max_size"):
                    memory.set_max_size(max_size)

        except Exception as e:
            logger.error(f"[配置更新] 更新记忆配置失败: {e}", exc_info=True)

    def _update_tts_config(self, config: Dict[str, Any], context: Any) -> None:
        """更新TTS配置"""
        try:
            engine = config.get("engine")
            if engine:
                tts_instance = self._get_tts_instance(context)
                if tts_instance:
                    if hasattr(tts_instance, "engine_name"):
                        tts_instance.engine_name = engine
                    elif hasattr(tts_instance, "set_engine"):
                        tts_instance.set_engine(engine)
                    logger.info(f"[配置更新] TTS引擎已切换到: {engine}")

            voice = config.get("voice")
            if voice:
                tts_instance = self._get_tts_instance(context)
                if tts_instance:
                    if hasattr(tts_instance, "voice"):
                        tts_instance.voice = voice
                    elif hasattr(tts_instance, "set_voice"):
                        tts_instance.set_voice(voice)
                    logger.info(f"[配置更新] TTS音色已切换到: {voice}")

        except Exception as e:
            logger.error(f"[配置更新] 更新TTS配置失败: {e}", exc_info=True)

    def _get_tts_instance(self, context: Any) -> Optional[Any]:
        """获取TTS实例"""
        if hasattr(context, "agent_manager") and context.agent_manager and hasattr(context.agent_manager, "tts_engine"):
            return context.agent_manager.tts_engine
        elif (
            hasattr(context, "config_manager")
            and context.config_manager
            and hasattr(context.config_manager, "tts_engine")
        ):
            return context.config_manager.tts_engine
        return None

    def _update_webapi_config(self, web_api, config: Dict[str, Any]) -> None:
        """更新WebAPI配置"""
        try:
            # 更新API密钥
            api_key = config.get("api_key")
            if api_key:
                if hasattr(web_api, "api_key"):
                    web_api.api_key = api_key
                elif hasattr(web_api, "set_api_key"):
                    web_api.set_api_key(api_key)

            # 更新CORS配置
            cors_origins = config.get("cors_origins")
            if cors_origins:
                if isinstance(cors_origins, str):
                    origins_list = [origin.strip() for origin in cors_origins.split(",")]
                else:
                    origins_list = list(cors_origins)

                if hasattr(web_api, "cors_origins"):
                    web_api.cors_origins = origins_list
                elif hasattr(web_api, "update_cors"):
                    web_api.update_cors(origins_list)

            # 更新速率限制
            rate_limit = config.get("rate_limit")
            if rate_limit and isinstance(rate_limit, int) and rate_limit > 0:
                if hasattr(web_api, "rate_limit"):
                    web_api.rate_limit = rate_limit
                elif hasattr(web_api, "set_rate_limit"):
                    web_api.set_rate_limit(rate_limit)

        except Exception as e:
            logger.error(f"[配置更新] 更新WebAPI配置失败: {e}", exc_info=True)

    def _update_terminal_config(self, terminal_manager, config: Dict[str, Any]) -> None:
        """更新终端管理器配置"""
        try:
            timeout = config.get("timeout")
            if timeout and isinstance(timeout, (int, float)) and timeout > 0:
                if hasattr(terminal_manager, "timeout"):
                    terminal_manager.timeout = timeout
                elif hasattr(terminal_manager, "set_timeout"):
                    terminal_manager.set_timeout(timeout)

            buffer_size = config.get("buffer_size")
            if buffer_size and isinstance(buffer_size, int) and buffer_size > 0:
                if hasattr(terminal_manager, "buffer_size"):
                    terminal_manager.buffer_size = buffer_size
                elif hasattr(terminal_manager, "set_buffer_size"):
                    terminal_manager.set_buffer_size(buffer_size)

            default_shell = config.get("default_shell")
            if default_shell:
                from pathlib import Path

                shell_path = Path(default_shell)
                if shell_path.exists():
                    if hasattr(terminal_manager, "default_shell"):
                        terminal_manager.default_shell = default_shell
                    elif hasattr(terminal_manager, "set_default_shell"):
                        terminal_manager.set_default_shell(default_shell)

        except Exception as e:
            logger.error(f"[配置更新] 更新终端配置失败: {e}", exc_info=True)

    def _update_iot_config(self, iot_manager, config: Dict[str, Any]) -> None:
        """更新IoT管理器配置"""
        try:
            device_timeout = config.get("device_timeout")
            if device_timeout:
                iot_manager.device_timeout = device_timeout

            heartbeat_interval = config.get("heartbeat_interval")
            if heartbeat_interval and isinstance(heartbeat_interval, (int, float)) and heartbeat_interval > 0:
                if hasattr(iot_manager, "heartbeat_interval"):
                    iot_manager.heartbeat_interval = heartbeat_interval

                # 重启心跳定时器
                if hasattr(iot_manager, "heartbeat_task") and iot_manager.heartbeat_task:
                    iot_manager.heartbeat_task.cancel()
                    if hasattr(iot_manager, "start_heartbeat"):
                        iot_manager.start_heartbeat()

            automation_rules = config.get("automation_rules")
            if automation_rules:
                if isinstance(automation_rules, list):
                    rules_dict = {rule.get("id", f"rule_{i}"): rule for i, rule in enumerate(automation_rules)}
                else:
                    rules_dict = automation_rules

                if hasattr(iot_manager, "automation_rules"):
                    iot_manager.automation_rules = rules_dict

        except Exception as e:
            logger.error(f"[配置更新] 更新IoT配置失败: {e}", exc_info=True)
