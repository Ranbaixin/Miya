# Legacy 代码快照

> 创建日期: 2026-07-26
> 源分支: fix/v8-hardening (1c432923)
> 快照分支: legacy/pre-cleanup-snapshot

## 归档内容

此分支保留了 P3 死代码清理前 Miya 仓库的**完整快照**，包括以下即将从主干删除的代码：

| 对象 | 行数 | 说明 |
|---|---|---|
| `astrbot/` | 40,578 | AstrBot 框架三重复制之一 (顶层副本) |
| `core/*_astrbot/` (20 个目录) | ~3.3MB | AstrBot 三重复制 (迁移后残留) |
| `core/platform/` | 26,181 | 与 core/platform_astrbot/ 近乎全等的副本 |
| `core/platform_astrbot/` | 25,617 | AstrBot 平台层 |
| `core/miya_core.py` 等替代核心簇 | ~6,700 | 一套从未被 run/daemon.py 触达的替代架构 |
| `core/unified_platform.py` | 282 | 被同名包遮蔽的死模块 |
| `core/platforms_config.py` 等配置双轨 | ~1,852 | 与 config/ 同名但不同实现的死配置 |
| `core/unified_knowledge.py` 等 4 文件 | ~973 | 把 astrbot import 藏在函数体内的隐蔽消费者 |

## 重要参考

如需将来重新接入以下平台，它们的**正确发送实现**在这个分支里（主干版本是坏的）：
- `core/unified_platform_impl/wechat_platforms.py` — 企微/微信公众号/微信开放平台完整实现
- `core/unified_platform_impl/webhook_platforms.py` — LINE/Lark 等 webhook 实现

## 恢复方法

```bash
# 查看某文件的历史版本
git show legacy/pre-cleanup-snapshot:path/to/file.py

# 从快照恢复单个文件
git restore -s legacy/pre-cleanup-snapshot -- path/to/file.py

# 切换回快照分支 (只读)
git checkout legacy/pre-cleanup-snapshot
```
