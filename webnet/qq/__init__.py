"""QQ 交互子网模块包（2026-08 精简）

仅保留运行期真正被引用的模块：
- config_loader: 被 config/settings.py 引用（QQ 配置加载）
- memory_commands: 被 hub/decision_hub.py 引用（记忆快捷命令）

历史遗留的 client/core/message_handler 等已删除（QQNet 从未实例化，
现行 QQ 通道为 core/unified_platform_impl/onebot_platform.py）。
"""
