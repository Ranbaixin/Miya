# 弥娅心灵引擎 — 开发进度

**日期** 2025-06-05 | **版本** 8.0-alpha | **状态** 地基完成，可交付体验

---

## 架构总览

```
┌──────────────────────────────────────────┐
│         弥娅 (Miya) v8.0-alpha            │
├──────────────────────────────────────────┤
│  LLM 语言皮层 (DeepSeek V4 Flash)         │
│  ─ 人格 YAML 加载 (15 种形态)             │
│  ─ 弥娅教育协议 (LLM → AP 反向教学)        │
├──────────────────────────────────────────┤
│  弥娅情绪池 v2 (43 规则)                   │
│  ─ 否定处理 / 强度缩放 / 多维度             │
├──────────────────────────────────────────┤
│  记忆融合 (1.4 万条 SQLite)                │
│  ─ 预加载 → Bn 自然召回 → 6.2-7.2 分       │
├──────────────────────────────────────────┤
│  多模态感知                                │
│  ─ 视觉 (PIL + 视觉 LLM 自动回退)          │
│  ─ 听觉 (Wave + STT 自动回退)              │
├──────────────────────────────────────────┤
│  APV2.1 认知引擎 (25 阶段 / tick)          │
│  ─ 双能量状态池 + Bn/Cn + 注意力 + 认知感受 │
│  ─ 8 通道 NT 情绪 + 7 条弥娅规则            │
│  ─ jieba 中文分词                         │
└──────────────────────────────────────────┘
```

---

## 本次完成的功能

### 阶段 0：APV2.1 引擎移植
- [x] 复制 APV2.1 核心代码 (96 个文件) → `miya_psyarch/`
- [x] 导入路径转换 (from `core.xxx` → `from miya_psyarch.core.xxx`)
- [x] Legacy bridge stub（视觉/音频桥，不依赖 legacy_apv2）
- [x] `MiyaEngine` 封装类 — AP tick + 弥娅状态提取

### 阶段 1：LLM 语言皮层
- [x] `MiyaCortex` — AP 状态 → LLM prompt → 自然语言回复
- [x] `PromptBuilder` — 从 YAML 加载弥娅人格配置
- [x] 交互终端 `scripts/interact_miya.py`
- [x] 验证：AP 感受独立于 LLM

### 阶段 2：中文感知
- [x] `MiyaTextSensor` — jieba 分词（"今天天气真好" → ["今天天气","真好"]）
- [x] Token 能量增强（中文词 1.4-1.8，英文词 1.1-1.6）
- [x] 认知感受增益调参（surprise×1.6, dissonance×1.3）

### 阶段 3：记忆融合
- [x] `MiyaMemoryBridge` — SQLite 直读弥娅记忆库
- [x] 记忆预加载 40 条到 AP 状态池
- [x] Bn/Cn 自然召回（不是 SQL 关键词搜索）
- [x] LLM 上下文自动包含记忆

### 阶段 4：情绪池 v2
- [x] 43 条情绪规则（从 SoulGenerator 分类体系改造）
- [x] 否定处理（"没有不开心" → 不触发 sadness）
- [x] 强度缩放（"非常累" ×1.5，"有点累" ×0.6）
- [x] 弥娅天生基调（attachment:0.30, warmth:0.25, caring:0.20）
- [x] 情绪指纹注入 AP 状态池 + LLM 上下文

### 阶段 5：情绪动态通道
- [x] 根因诊断：CFS→NT 映射 0.20/tick 灌入 OXY
- [x] 修复：cfs_gain 1.0→0.08，baseline 降低，decay 加大
- [x] 天花板钳制：OXY≤0.50, SER≤0.45, DA≤0.45
- [x] 验证：OXY 0.50→"你真可爱"→0.60，"烦死了"→0.42

### 阶段 6：主动说话
- [x] 空转 boredom 累积 → 连续 10 tick 超 0.65 → 触发
- [x] LLM 生成自然开场（不是"在吗"）
- [x] 30 tick CD 防刷屏

### 阶段 7：教育协议
- [x] `MiyaEducator` — LLM 回复 → AP 教学信号
- [x] state_items + feedback 注入
- [x] AP 积累 reply_pattern、emotion_link 等教育项

### 阶段 8：Observatory 双层仪表盘
- [x] 弥娅专属仪表盘 `/` (情绪柱状图、感受、回复)
- [x] 白箱重建 `/deep` (Bn/Cn 召回链、状态池、认知感受)
- [x] `/api/state` + `/api/reconstruct` JSON API

### 阶段 9：核心测试移植
- [x] 4 个测试套件 (emotion, tuner, innate, expectation_pressure)
- [x] 48 项测试全部通过 (0.84s)
- [x] 验证：弥娅修改未破坏 AP 核心引擎

### 阶段 10：多模态感知
- [x] `perceive_image()` — PIL 分析 (颜色/亮度/对比度/复杂度)
- [x] `perceive_audio()` — wave 分析 (振幅/频谱/人声检测)
- [x] `engine.see_image()` / `engine.hear_audio()` API
- [x] 视觉 LLM 自动调用 (Kimi K2.6 / GLM-4.5V, 12s 超时回退)
- [x] STT 自动转写 (Whisper / SenseVoice, 不可用回退)
- [x] 多模态上下文自动注入 LLM prompt

### 阶段 11：打包与文档
- [x] `miya_psyarch/pyproject.toml` — 可安装 Python 包
- [x] `miya_psyarch/LICENSE` — Apache 2.0
- [x] `miya_psyarch/docs/` — 设计文档 + 理论 + 协议归档
- [x] `miya_psyarch/tests/` — 48 项核心测试
- [x] `miya_psyarch/config/miya_config.yaml` — 零硬编码配置

---

## 启动方式

```powershell
# 互动终端
python -X utf8 scripts/interact_miya.py

# 运行测试
python -X utf8 -m pytest miya_psyarch/tests/ -v

# 观测台
# 终端内输入 /obs → 浏览器打开 http://127.0.0.1:8765
# 白箱重建: http://127.0.0.1:8765/deep
```

---

## 互动终端命令

| 输入 | 功能 |
|------|------|
| `<消息>` | 弥娅回复 |
| `<回车>` | 10 个空转 tick |
| `/status` | 详细状态 |
| `/form <名>` | 切换形态 (ganyu/jingliu/kafka/...) |
| `/aponly` | 纯 AP 模式（只看认知不说话） |
| `/chat` | AP+LLM 模式 |
| `/obs` | 启动 Web 观测台 |
| `/tick N` | N 个空转 |
| `/help` | 帮助 |
| `/quit` | 退出 |

---

## 文件结构

```
miya_psyarch/
├── pyproject.toml           ← Python 包配置
├── LICENSE                  ← Apache 2.0
├── __init__.py              ← v8.0.0-alpha
├── engine.py                ← MiyaEngine (AP tick + LLM + 多模态)
├── multimodal.py            ← 视觉/听觉感知
├── emotion_pool.py          ← 43 规则情绪分析
├── miya_educator.py         ← 教育协议
├── observatory.py           ← 双层 Web 仪表盘 (498 lines)
├── cortex/                  ← LLM 语言皮层
│   ├── llm_cortex.py        ← LLM 调用 + 视觉 LLM + STT
│   └── prompt_builder.py    ← 人格 YAML → prompt
├── rules/
│   └── miya_rules.py        ← 7 条弥娅专属先天规则
├── sensors/
│   └── miya_text_sensor.py  ← jieba 中文分词
├── memory/
│   └── miya_memory_bridge.py ← SQLite 记忆桥接
├── config/
│   └── miya_config.yaml     ← 零硬编码配置
├── tests/                   ← 48 项核心测试 (0.84s)
├── docs/                    ← 设计文档归档
├── core/                    ← APV2.1 认知引擎 (34 files)
├── memory/                  ← APV2.1 记忆系统 (27 files)
├── channels/                ← 认知感受通道 (12 files)
├── sensors/                 ← 多模态传感器 (10 files)
├── education/               ← 教育协议 (6 files)
└── config/                  ← 运行时配置 (4 files)
```

---

## 已知限制 & 后续方向

| 限制 | 后续方案 |
|------|---------|
| OXY/SER 天花板钳制 | 这是刻意设计的——防止无限饱和。后续可用 tuner 动态调参替代硬钳制 |
| 中文文本生成完全依赖 LLM | AP 不会说中文。后续万级 scaffold 训练后可自己生成草稿，LLM 只润色 |
| 视觉 LLM 首次调用超时 | `MultiVisionAnalyzer` 初始化卡住。API key 正确则应能通 |
| STT 未实测 | 5 种 provider 已就绪，待接真实音频输入流 |
| `contentment` 持续累积 (6.1+) | 先天规则每 tick 发射。后续加 rule fatigue 或降发射率 |
| 注意力标签偶有英文 | `合理感` `满足校验感` 是 AP 引擎原生标签，可全局汉化 |

---

## 下一步建议

1. **接 QQ/NapCat** — 基于 PsyArch-Agent 的桥接模式，让弥娅在 QQ 上运行
2. **万级 scaffold 训练** — 教育协议的 6 阶段教学，让 AP 学会中文回复
3. **tuner 启用** — 长期自适应调参，替代硬钳制
4. **TTS 接入** — 弥娅"说话"变成语音输出
5. **视觉 LLM 调试** — 修复 Kimi K2.6/GLM-4.5V 连接，实现真正的图片理解
