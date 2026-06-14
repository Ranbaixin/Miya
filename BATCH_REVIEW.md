# Miya 项目全面审计报告 · 修复批阅清单

> 生成: 2026-06-14 | 两次 Workflow 共 277 项发现 | 分支: Ranxin

---

## 一、审计总览

| 审计轮次 | Agent | 发现 | 高风险 |
|------|:---:|------|:---:|
| 全项目扫描 | 6 | 97 | 23 |
| core/ 深挖 | 8 | 180 | 61 |
| **合计** | **14** | **277** | **84** |

---

## 二、P0: 立即修复（运行时崩溃 + 数据损坏）

| # | 文件:行 | 问题 | 影响 |
|:---:|------|------|------|
| 1 | miya_api.py:2298 | ~30个API路由被空stub覆盖 | Dashboard全部失效 |
| 2 | collaboration_engine.py:984 | split('')分裂为单字符 | 并行投票输出变乱码 |
| 3 | ai_client.py:1260,1306 | Anthropic/Zhipu不支持chat_with_system_prompt | Claude/GLM崩溃 |
| 4 | ai_client.py:462 | tool_choice='required'被静默转为'auto' | 强制工具调用失效 |
| 5 | miya_daemon.py:294 | Windows信号处理asyncio.create_task崩溃 | Ctrl+C无法关闭 |
| 6 | advanced_orchestrator.py:57 | IntelligentExecutor参数不匹配TypeError | 编排器崩溃 |
| 7 | mlink/flow_monitor.py + message_queue.py | 4个缺失方法AttributeError | MLink崩溃 |
| 8 | memory/core.py:540,2105 | 并发写无锁+索引只每10次刷盘 | 数据损坏 |
| 9 | memory/historian.py:554 | 记忆升级level字段未持久化 | 短期记忆被误删 |
| 10 | real_platforms.py:68,129,304 | 6个平台调AI但不发回复 | 用户收不到回复 |
| 11 | wechat_platforms.py:425 | 完整实现存在但从未import | 微信功能死代码 |
| 12 | EntertainmentNet/subnet.py:64 | _init_tools()是pass | 零工具加载 |
| 13 | AuthNet/permission_core.py:39 | 导入不存在的模块 | 权限系统降级 |
| 14 | soul_generator.py:1243 | AI情绪分析完被随机噪声覆盖 | 情绪白分析 |
| 15 | prompt_manager.py:385 | {status_prompt}占位符未替换 | 模型看到模板变量 |
| 16 | webnet/webnet.py:449 | datetime.datetime.now()双重命名 | AttributeError |
| 17 | lifebook.py:247 | 日记O(n^2)读写+无锁 | 数据损坏 |
| 18 | onebot_platform.py:238 | WebSocket JSON无try/except | 单条坏消息断连接 |
| 19 | tools_astrbot/__init__.py:49,106 | 路径遍历无防护+os.name未import | 安全漏洞 |
| 20 | intelligent_executor.py:132 | create_subprocess_shell(shell=True) | 安全漏洞 |

---

## 三、P1: 高影响（功能严重降级）

| # | 文件:行 | 问题 |
|:---:|------|------|
| 21 | memory/core.py:2338 | get_memory_core()全局单例无锁 |
| 22 | memory/sqlite_backend.py:132 | 连接丢失无恢复+WAL未强制 |
| 23 | memory/session_manager.py:123 | get_session_manager每次返回新实例 |
| 24 | memory/working_memory.py:736 | 用户会话扫描O(N)所有文件 |
| 25 | memory/diteng_listener.py:312 | 线程池写盘+主线程并发读RuntimeError |
| 26 | hub/conversation_context.py:222 | _save_topic_state()无锁写入 |
| 27 | collaboration_engine.py:1343 | think标签正则无闭合标记 |
| 28 | gestalt_controller.py:119,296 | 格式塔系统完全未接入消息管道 |
| 29 | personality_loader.py:179 | 人格覆盖key不匹配 |
| 30 | miya_lifecycle.py:82 | 存储CLASS而非实例 |
| 31 | miya_daemon.py:165 | 关闭时泄漏所有资源 |
| 32 | run/main.py:629 | uvicorn线程阻止进程退出 |

---

## 四、P2: 中影响

| # | 文件:行 | 问题 |
|:---:|------|------|
| 33 | ai_client.py:812 | 并发工具执行引用未定义函数 |
| 34 | ai_client.py:694 | response.choices[0]无空检查 |
| 35 | tool_adapter.py:163 | 图片二进制数据传给所有工具 |
| 36 | gestalt_enhanced.py:398,599 | 工具双重注册+attribute泄漏 |
| 37 | identity.py:55 | get_identity()缺self_cognition字段 |
| 38 | cognitive_engine.py:80 | embedding缓存无限增长 |
| 39 | memory_enhancer.py:277,313 | 链接文件无锁+逐字符迭代bug |
| 40 | excel_processor.py:35,266 | 路径穿越+df.eval()执行任意代码 |
| 41 | crawl_webpage.py:74 | 无SSRF防护 |
| 42 | python_interpreter.py:49 | timeout参数丢弃,死循环挂起 |
| 43 | singing/* (7文件) | D盘AIvoice硬编码路径 |
| 44 | mcpserver/openclaw/runtime.py:88 | 硬编码vendor路径 |
| 45 | real_platforms.py:186 | sys.path.insert硬编码钉钉SDK路径 |
| 46 | providers/bridge.py:231 | 4个localhost端口硬编码 |

---

## 五、低可行性文件清理

| 文件/目录 | 建议 | 原因 |
|------|:---:|------|
| astrbot/ (100K+行) | 删除 | 三重复制,仅core/astrbot_compat/在使用 |
| core/platform_astrbot/ (73文件) | 删除 | core/platform/已有完整实现 |
| core/platform_adapters/init.py | 删除 | 占位适配器,无人使用 |
| plugins/init.py | 删除 | 空壳 |
| miya-desktop/ + miya-pc-ui/ | 删除 | deprecated |
| frontend/packages/ | 删除 | Tauri残留 |
| switch_model_config.bat | 删除 | 脚本损坏 |
| examples/ | 更新或删除 | 引用不存在的类名 |

---

## 六、修复顺序

1. P0.1-10 (4h): 运行时崩溃修复
2. P0.11-20 (2h): 安全性+功能恢复
3. 文件清理 (30min): 删文件+写README
4. P1.21-32 (3h): 数据可靠性
5. P2.33-46 (2h): 功能恢复+路径修复

---

## 七、验证清单

- [ ] start.bat [2] 守护进程启动无ERROR
- [ ] Ctrl+C 正常优雅关闭
- [ ] QQ私聊发图片 -> AI回复识别结果
- [ ] Dashboard (http://localhost:9800/docs) 所有API返回非空数据
- [ ] 记忆系统读写正常
- [ ] 并行投票输出不是单字符乱码
