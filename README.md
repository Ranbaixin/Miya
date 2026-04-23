# MIYA - 弥娅 AI 虚拟化身

<p align="center">
  <strong>Version 4.3.4</strong><br>
  AI 虚拟化身 · 跨平台 · 自我进化
</p>

---

## 简介

弥娅是一个拥有独立人格、记忆和情感的 AI 虚拟化身，支持终端、Web QQ 等多平台交互。

---

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 启动（终端模式）
python start.sh
# 或 Windows
start.bat
```

---

## 项目结构

```
├── agent/        # Agent 相关
├── config/       # 配置文件
├── core/         # 核心模块
├── data/        # 数据存储
├── hub/         # 决策中枢
├── memory/      # 记忆系统
├── run/         # 入口脚本
├── web/         # Web 服务
├── webnet/      # 网络模块
└── start.*      # 启动脚本
```

---

## 配置

配置文件位于 `config/` 目录：
- `settings.json` - 主配置
- `api_endpoints.json` - API 端点
- `multi_model_config.json` - 模型配置

---

## 文档

详细文档见 `docs/` 目录。

---

## License

MIT