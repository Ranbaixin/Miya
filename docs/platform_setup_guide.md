# 弥娅多平台配置指南

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install botpy  # QQ官方机器人SDK
pip install python-telegram-bot  # Telegram
pip install discord.py  # Discord
```

### 2. 配置平台

编辑 `config/platforms_config.py`，填入你的平台凭证。

### 3. 启动服务

```bash
python start_platforms.py
```

---

## 📱 各平台配置详解

### QQ 官方机器人（最优先）

**申请步骤：**

1. 访问 [QQ开放平台](https://q.qq.com/)
2. 注册并登录
3. 点击「创建应用」
4. 选择「机器人」类型
5. 填写应用信息，提交审核
6. 审核通过后，在「开发设置」中获取：
   - `App ID`
   - `App Secret`

**配置示例：**

```python
QQ_OFFICIAL_CONFIG = {
    "enabled": True,
    "app_id": "123456789",
    "app_secret": "your_app_secret_here",
    "sandbox": False,  # 测试时设为 True
}
```

**注意事项：**
- 需要完成实名认证
- 机器人需要加入频道或群组才能接收消息
- 沙箱环境用于测试，不会影响正式环境

---

### Telegram

**申请步骤：**

1. 打开 Telegram，搜索 `@BotFather`
2. 发送 `/newbot`
3. 按提示输入机器人名称和用户名
4. 获取 `Bot Token`

**配置示例：**

```python
TELEGRAM_CONFIG = {
    "enabled": True,
    "bot_token": "123456789:ABCdefGHIjklMNOpqrsTUVwxyz",
}
```

**注意事项：**
- 机器人用户名必须以 `bot` 结尾
- 可以通过 `/setcommands` 设置命令菜单

---

### Discord

**申请步骤：**

1. 访问 [Discord开发者门户](https://discord.com/developers/applications)
2. 点击「New Application」
3. 输入应用名称
4. 在左侧菜单选择「Bot」
5. 点击「Reset Token」获取 Token
6. 开启「Message Content Intent」

**配置示例：**

```python
DISCORD_CONFIG = {
    "enabled": True,
    "bot_token": "your_bot_token_here",
}
```

**邀请机器人：**
1. 在「OAuth2」->「URL Generator」中选择 `bot` scope
2. 选择需要的权限
3. 复制生成的链接，在浏览器中打开邀请机器人

---

### 飞书

**申请步骤：**

1. 访问 [飞书开放平台](https://open.feishu.cn/)
2. 创建企业自建应用
3. 在「凭证与基础信息」中获取：
   - `App ID`
   - `App Secret`
4. 在「事件订阅」中配置回调地址
5. 添加「接收消息」事件

**配置示例：**

```python
FEISHU_CONFIG = {
    "enabled": True,
    "app_id": "cli_xxxxxxxxxxxxxxxx",
    "app_secret": "your_app_secret_here",
}
```

---

### 钉钉

**申请步骤：**

1. 访问 [钉钉开放平台](https://open.dingtalk.com/)
2. 创建应用
3. 在「凭证与基础信息」中获取：
   - `AppKey`
   - `AppSecret`
4. 在「消息推送」中开启机器人功能

**配置示例：**

```python
DINGDING_CONFIG = {
    "enabled": True,
    "app_key": "dingxxxxxxxxxxxxxxxx",
    "app_secret": "your_app_secret_here",
}
```

---

### 企业微信

**申请步骤：**

1. 访问 [企业微信管理后台](https://work.weixin.qq.com/)
2. 在「应用管理」中创建应用
3. 获取：
   - `CorpID`（在「我的企业」中）
   - `Secret`（在应用详情中）

**配置示例：**

```python
WECOM_CONFIG = {
    "enabled": True,
    "corpid": "wwxxxxxxxxxxxxxxxx",
    "corpsecret": "your_corpsecret_here",
}
```

---

### Slack

**申请步骤：**

1. 访问 [Slack API](https://api.slack.com/apps)
2. 点击「Create New App」
3. 选择「From scratch」
4. 在「OAuth & Permissions」中获取 `Bot Token`
5. 添加需要的权限 scopes

**配置示例：**

```python
SLACK_CONFIG = {
    "enabled": True,
    "bot_token": "xoxb-your-bot-token",
}
```

---

### 网页聊天

无需申请，直接使用。

**配置示例：**

```python
WEBCHAT_CONFIG = {
    "enabled": True,
    "port": 8080,
}
```

访问 `http://localhost:8080` 即可使用。

---

## 🔧 常见问题

### Q: 如何测试机器人？

A: 使用沙箱环境（QQ）或测试频道（Discord）进行测试。

### Q: 机器人收不到消息怎么办？

A: 
1. 检查凭证是否正确
2. 检查机器人是否已加入群组/频道
3. 检查网络连接
4. 查看日志文件 `miya_platforms.log`

### Q: 可以同时运行多个平台吗？

A: 可以！只需在配置文件中启用多个平台即可。

### Q: 如何自定义消息处理？

A: 编辑 `start_platforms.py` 中的 `_create_message_handler` 方法。

---

## 📞 获取帮助

- 查看日志: `miya_platforms.log`
- 检查配置: `config/platforms_config.py`
- 启动脚本: `start_platforms.py`

---

## 💡 提示

- 建议先配置一个平台测试成功后，再添加其他平台
- 所有平台的凭证都应该保密，不要提交到版本控制
- 可以使用环境变量存储敏感信息
