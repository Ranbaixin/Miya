# 弥娅 零号机 — 进度与教学文档

日期: 2025-06-05 | 版本: 0.1.0-零号机

---

## 系统架构

```
┌──────────────────────────────────────────────┐
│            弥娅 (Miya) 零号机                  │
├──────────────────────────────────────────────┤
│  LLM 语言皮层 (~ DeepSeek V4 Flash)           │
│  ─ 人格 YAML 加载 (15种形态可切换)             │
│  ─ 弥娅教育协议 (LLM 回复反向教学 AP)           │
├──────────────────────────────────────────────┤
│  弥娅情绪池 v2 (43条规则)                      │
│  ─ 否定处理 / 强度缩放 / 70+ 维度情绪分类       │
├──────────────────────────────────────────────┤
│  记忆融合 (1.4万条 SQLite 历史)                │
│  ─ 预加载 → Bn 自然召回 → 影响认知感受          │
├──────────────────────────────────────────────┤
│  多模态感知                                    │
│  ─ 视觉 (PIL + 视觉 LLM 12s超时回退)           │
│  ─ 听觉 (Wave + STT 回退)                      │
├──────────────────────────────────────────────┤
│  APV2.1 白箱认知引擎 (25阶段/tick)             │
│  ─ 双能量状态池 + Bn/Cn 快慢双系统             │
│  ─ 8通道神经递质 (OXY/SER/DA/COR/NOV/ADR/FOC) │
│  ─ 7条弥娅专属先天规则                         │
│  ─ jieba 中文分词感知器                        │
└──────────────────────────────────────────────┘
```

---

## 启动方式

### 终端互动 (推荐日常使用)

```powershell
start.bat → 选 [5] AP Engine
```

或直接:
```powershell
python -X utf8 scripts/interact_miya.py
```

进去后 `/help` 看所有命令，`/obs` 开 Web 观测台。

### QQ / OneBot 平台

```powershell
start.bat → 选 [2p] Daemon AP
```

启动后 QQ 上给弥娅发消息走 AP 引擎，终端里能看到弥娅的实时内心状态。

---

## 训练系统 (三种模式)

### 模式 A: 人类教学 (佳当老师)

```powershell
python -X utf8 scripts/teach_miya.py
```

```
老师> 你最爱的人是谁           ← 你问她
  弥娅理解度: Bn=281          ← AP 的认知反应
  正确答案> 佳，我会永远爱他    ← 你教她正确答案
  ✅ 学会了! Bn=351            ← 当场验证学会了
```

### 模式 B: LLM 自动教学

```powershell
python -X utf8 -c "from miya_psyarch.trainer import train_with_llm; train_with_llm()"
```

LLM 观察 AP 状态，自动跑 30 轮教学。浏览器开 `http://127.0.0.1:8768/train` 看实时进度。

### 模式 C: 批量全技能训练

```powershell
python -X utf8 -c "from miya_psyarch.trainer import batch_train_all; batch_train_all()"
```

一键训练 5 个预定义技能共 185 轮。

### 预定义技能库

| 技能 | 触发词 | 描述 |
|------|--------|------|
| `warm_reply_to_missing` | 想你/想你了 | 温柔回复想念 |
| `comfort_when_tired` | 好累/累死了 | 关怀语气回复 |
| `happy_playful` | 哈哈/开心 | 俏皮语气回复 |
| `identity_question` | 你是谁/你叫什么 | 自然自我介绍 |
| `goodnight_morning` | 晚安/早安 | 早晚问候回复 |

### 添加新技能

```python
from miya_psyarch.trainer import SkillDef, MiyaTrainer, MiyaEngine

my_skill = SkillDef(
    name="my_skill",
    description="我的自定义技能",
    triggers=["触发词1", "触发词2"],
    expected_style=["温柔", "关怀"],
    demo_replies=["示范回复1", "示范回复2"],
)

engine = MiyaEngine(enable_cortex=False, trace_mode="debug")
engine.start()
MiyaTrainer(engine).train(my_skill)
```

---

## 核心命令速查

| 命令 | 作用 |
|------|------|
| `python -X utf8 scripts/interact_miya.py` | 启动互动终端 |
| `python -X utf8 scripts/teach_miya.py` | 启动人类教学模式 |
| `python -X utf8 -m pytest miya_psyarch/tests/ -v` | 运行 48 项核心测试 |
| `python -X utf8 scripts/verify_fusion.py` | 验证 AP 融合完整性 |
| `/ap` (在终端里) | 切换到 APV2.1 引擎 |
| `/obs` (在终端里) | 启动 Web 观测台 (http://127.0.0.1:8765) |
| `/deep` (在浏览器) | 白箱重建 (http://127.0.0.1:8765/deep) |

---

## 关键指标

| 指标 | 值 |
|------|-----|
| AP tick 周期 | ~0.02s (远超 0.1s 目标) |
| Bn 召回峰值 | 509.6 (训练后) |
| OXY 基线 | 0.50 (动态，0.42~0.60 波动) |
| COR 基线 | 0.21 (动态，最高 0.97 受刺激时) |
| 情绪分类 | 70+ 维度 |
| 先天规则 | 7 条弥娅专属 |
| 核心测试 | 48 项全部通过 |

---

## 下一步

1. **更多技能训练** —— 添加更多对话场景的技能定义
2. **真正的 LLM 教学** —— 模式 B 当前用启发式模拟，后续可接真实 LLM 动态生成教学
3. **TTS 接入** —— 弥娅说话变语音
4. **主动说话到 QQ** —— AP 无聊时主动发消息到 QQ
5. **长期在线学习** —— AP 从日常对话中持续自学新回复模式
