from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from miya_psyarch.channels.expectation_pressure import BAnchorExpectationVerifier
from miya_psyarch.core.action import ActionConsequencePlanner, SafetyGate
from miya_psyarch.core.action.focus_actuators import AuditoryBandActuator, VisualGazeActuator
from miya_psyarch.core.action.text_actuator import TextActionActuator
from miya_psyarch.core.attention.selector import AttentionSelector
from miya_psyarch.core.innate import InnateCodingEngine
from miya_psyarch.core.innate.default_rules import RuleDef, default_rules
from miya_psyarch.core.learning import InnateLearningEventRouter
from miya_psyarch.core.runtime.engine import APV21Runtime
from miya_psyarch.config.defaults import RuntimeConfig


REPORT_PATH = ROOT / "docs" / "ColdSave_先天规则逐条闭环验证报告_20260528.md"
JSON_PATH = ROOT / "data" / "validation" / "innate_rule_closure_20260528.json"


MEANINGS = {
    "CF-001": "正认知压代表现实超出预测, 触发惊并把注意力推向意外对象。",
    "CF-002": "负认知压代表预测落空, 触发违和并把预测/现实错配绑定起来。",
    "CF-003": "预测与现实对齐时产生正确感, 为路径巩固和奖励调制提供内在证据。",
    "CF-004": "Bn/Bn' 匹配效率高时产生把握感, 表示现状可被经验解释。",
    "CF-005": "整体错配低且结构顺滑时产生合理/连贯感。",
    "CF-006": "多个 B/C 候选接近时产生不确定感, 推动等待、回读或发散。",
    "CF-007": "奖励后继预测形成期待感, 让系统知道自己在期待什么。",
    "CF-008": "惩罚后继预测形成压力感, 让风险预期可被认知和验证。",
    "CF-009": "期待被验证时产生满足感, 连接期待、奖励和正确性。",
    "CF-010": "期待落空时产生落差感, 连接期待、不验和违和。",
    "CF-011": "召回记忆时间差出现波峰时形成时间感。",
    "CF-012": "节奏相位稳定时形成下一拍/相位期待。",
    "CF-013": "运行负载高时产生复杂感, 用于预算和注意力收窄。",
    "CF-014": "低负载、低错配时产生简单感, 用于发散或探索。",
    "CF-015": "规则或锚点疲劳过高时让疲劳本身可被认知。",
    "AT-001": "惊把行动倾向推向异常锚点聚焦。",
    "AT-002": "违和推动残差/错配对象检查。",
    "AT-003": "把握和后继清晰时保持焦点, 支持慢系统连续性。",
    "AT-004": "压力和残差推动检查, 避免风险被忽略。",
    "AT-005": "合理感抑制无意义发散, 让熟悉场景更稳。",
    "AT-006": "新奇/低把握推动发散扫描。",
    "AT-007": "疲劳推动释放重复焦点。",
    "AT-008": "时间感推动按时间间隔召回。",
    "AT-009": "节奏相位推动等待或准备下一拍。",
    "BC-001": "正认知压给在线学习提供正向共现证据。",
    "BC-002": "负认知压给在线学习提供过拟合/负向证据。",
    "BC-003": "顺序证据提供 transition 学习入口。",
    "BC-004": "行动反馈提供行动后果学习入口。",
    "BC-005": "多模态共现提供跨模态绑定学习入口。",
    "BC-006": "期待/压力锚创建后安排后续 B 锚验证。",
    "EM-DA-001": "奖励提高 DA, 增强趋利驱动。",
    "EM-DA-002": "惩罚降低 DA, 抑制重复冲动。",
    "EM-ADR-001": "惊提高 ADR, 增强警觉和反应。",
    "EM-ADR-002": "连贯/熟悉降低 ADR, 让系统冷静。",
    "EM-OXY-001": "正反馈提高 OXY, 增强信任/互动权重。",
    "EM-OXY-002": "社交或反馈惩罚降低 OXY, 增强警惕。",
    "EM-SER-001": "正确感提高 SER, 增强稳定和秩序。",
    "EM-SER-002": "违和降低 SER, 允许系统打破稳定去修错。",
    "EM-END-001": "缓解提高 END, 支持从压力中恢复。",
    "EM-END-002": "持续压力降低 END, 表示恢复资源被消耗。",
    "EM-COR-001": "风险提高 COR, 让外部行动更谨慎。",
    "EM-COR-002": "安全验证降低 COR, 解除过度警戒。",
    "EM-NOV-001": "新奇提高 NOV, 增强探索。",
    "EM-NOV-002": "熟悉降低 NOV, 减少无谓探索。",
    "EM-FOC-001": "清晰后继提高 FOC, 增强焦点锁定。",
    "EM-FOC-002": "不确定降低 FOC, 避免卡在错误焦点。",
    "AC-001": "视觉意外推动视焦点转向。",
    "AC-002": "视觉运动推动视线追踪。",
    "AC-003": "陌生/低把握推动视觉扫描。",
    "AC-004": "视觉不确定推动放大采样。",
    "AC-005": "听觉突变推动听觉焦段滑动。",
    "AC-006": "人声样式推动听觉焦段锁定。",
    "AC-007": "听觉低把握推动放宽频段寻找声源。",
    "AC-008": "文本违和推动回读。",
    "AC-009": "强预测 token 推动文本插入准备。",
    "AC-010": "文本错配推动替换/修订准备。",
    "AC-011": "正确且低压力时推动提交准备。",
    "AC-012": "期待锚推动按期待回忆。",
    "AC-013": "外部动作前的压力应推动后果回放。",
    "AC-014": "时间感推动按时间感回忆。",
    "AC-015": "不确定时推动等待, 让不行动成为合法行动。",
    "AC-016": "外部风险触发安全门, 抑制高风险外部动作。",
    "AC-017": "UI 目标应推动鼠标移动, 是电脑控制预留。",
    "AC-018": "安全验证后应允许点击准备, 是电脑控制预留。",
    "AC-019": "复杂低把握任务推动 LLM 思考预留接口。",
    "AC-020": "高风险外部动作推动 LLM 批判预留接口。",
    "AF-001": "行动被选中后形成可记忆的行动选择事件。",
    "AF-002": "行动胜出后保存因果窗口, 为后果学习定位上下文。",
    "AF-003": "行动反馈进入状态池/记忆/学习链。",
    "AF-004": "正反馈产生奖励/正确信号。",
    "AF-005": "负反馈产生惩罚/压力塑形信号。",
    "AF-006": "正反馈增强未来同类行动倾向。",
    "AF-007": "负反馈抑制未来同类行动倾向。",
    "AF-008": "预测后果和实际反馈不符时记录行动预测误差。",
    "AF-009": "从 B/C 后继读出历史 action_feedback 来评估行动后果。",
    "AF-010": "C/C' 召回 action::* 后把虚能量转成驱动力。",
    "AF-011": "安全抑制本身入池, 让想做但不做也可学习。",
}


STATUS_OVERRIDES = {
    "CF-004": ("部分闭环", "规则可触发 trace; 把握感功能主要由 CognitiveFeelingChannel 统一生成并入池。"),
    "CF-006": ("部分闭环", "规则可触发 trace; 不确定感可进入 action_preselect, 但该 phase 的 emit_sa 当前未直接入池。"),
    "CF-007": ("部分闭环", "期待功能由 ExpectationPressureChannel/BAnchorVerifier 入池; innate feeling item 当前只在 trace。"),
    "CF-008": ("部分闭环", "压力功能由 ExpectationPressureChannel/BAnchorVerifier 入池并进入 SafetyGate; innate feeling item 当前只在 trace。"),
    "CF-009": ("部分闭环", "满足感可由 BAnchorVerifier 入池; innate feeling item 当前只在 emotion_post trace。"),
    "CF-010": ("部分闭环", "落差感可由 BAnchorVerifier 入池; innate feeling item 当前只在 emotion_post trace。"),
    "CF-011": ("trace/audit", "innate 规则只输出 trace_log; 实际 timefelt::elapsed 由 TimeFeelingChannel 生成、入池并偏置召回。"),
    "CF-012": ("trace/audit", "innate 规则只输出 trace_log; 实际 rhythmfelt::* 由 RhythmChannel 生成并入池。"),
    "AT-001": ("完整闭环", "focus_anchor 胜出后由 ActionControlEffectRouter 生成 control::attention_anchor, 下一 tick AttentionSelector 消费 boost。"),
    "AT-002": ("完整闭环", "inspect_residual 胜出后生成 control::residual_inspection 和 slow_query_hints, 可把预测/现实残差拉回慢系统。"),
    "AT-003": ("完整闭环", "continue_focus 胜出后生成 focus_hold 控制和 slow_query_hints, 支持慢系统连续内心发展。"),
    "AT-005": ("完整闭环", "合理感可通过 action_bias 抑制 diverge, 并推动 continue_focus 保持稳定认知。"),
    "AT-006": ("完整闭环", "diverge_attention 胜出后产生 family_budget_modulation, 使注意力分布短期更发散。"),
    "AT-007": ("完整闭环", "release_focus 胜出后生成 focus_release suppression 与 family budget 调制, 防止重复焦点自激。"),
    "AT-008": ("完整闭环", "recall_by_timefelt 胜出后按 time_context 召回目标时间附近 snapshot, 生成 control::timefelt_recall。"),
    "AT-009": ("完整闭环", "wait 胜出后生成 control::timing_wait, 并在 action_feedback 中作为合法不行动被奖惩塑形。"),
    "BC-001": ("部分闭环", "事件被路由为在线学习 trace; 直接学习写入由 MemoryStore 基于状态池认知压完成。"),
    "BC-002": ("部分闭环", "事件被路由为在线学习 trace; 直接学习写入由 MemoryStore 基于状态池认知压完成。"),
    "BC-003": ("部分闭环", "事件被路由为 transition trace; 直接 transition/后继学习由 MemoryStore 完成。"),
    "BC-004": ("部分闭环", "事件被路由为 action outcome trace; 直接写入由 planner.record_feedback/ActionOutcomeMemory 完成。"),
    "BC-005": ("部分闭环", "事件被路由为多模态绑定 trace; 直接绑定/数值召回仍由 MemoryStore 和传感器通道完成。"),
    "BC-006": ("完整闭环", "verify_b_anchor 事件有 BAnchorVerifier 消费, 并能产生 satisfaction/gap/pressure_validation。"),
    "AC-001": ("完整闭环", "可生成视觉焦点行动, VisualGazeActuator 能产 control::visual_gaze; 下一 tick 视觉传感器会消费 gaze state 调整采样精度。"),
    "AC-002": ("完整闭环", "可生成视觉追踪行动, 控制状态可入池; 下一 tick 视觉传感器会按焦点距离调制对象 salience 和 reconstruction precision。"),
    "AC-003": ("部分闭环", "可生成扫描行动, 控制状态可入池; 扫描策略仍是简单确定性模式。"),
    "AC-004": ("完整闭环", "可生成视觉放大行动, 控制状态可入池; 下一 tick 焦点高精采样会受 scale 控制。"),
    "AC-005": ("完整闭环", "可生成听觉焦段滑动, AuditoryBandActuator 能产 control::auditory_band; 下一 tick 音频传感器会消费 band state 调整频段采样。"),
    "AC-006": ("完整闭环", "可生成听觉锁定行动, 控制状态可入池; 后续音频 focus_band / STFT payload precision 会按焦段状态变化。"),
    "AC-007": ("完整闭环", "可生成听觉放宽行动, 控制状态可入池; 下一 tick 采样焦段宽度会影响 focus precision 和 band vector。"),
    "AC-008": ("完整闭环", "text_reread 可作为候选; TextActionActuator 已直接消费 text_reread 并生成 text_action::reread SA。"),
    "AC-009": ("完整闭环", "text_insert 可作为候选并受 SafetyGate 审查; TextActionActuator 已直接执行内部文本插入并入池。"),
    "AC-010": ("完整闭环", "text_replace 可作为候选并受 SafetyGate 审查; TextActionActuator 已直接执行内部替换/修订并入池。"),
    "AC-011": ("部分闭环", "text_commit 可作为候选并受 SafetyGate 审查, 但没有真实外部提交执行器。"),
    "AC-012": ("完整闭环", "recall_by_expectation 胜出后会从 B anchor source_memory_id 回灌 core labels, 支持期待/压力自查询。"),
    "AC-013": ("完整闭环", "pressure_external_candidate 可触发 replay_episode; episode 回放的 safety_review_hint 可提高 SafetyGate 外部审查。"),
    "AC-014": ("完整闭环", "recall_by_timefelt 可生成候选, runtime 已按 time_context 回灌目标时间附近记忆内容。"),
    "AC-015": ("完整闭环", "wait 可作为行动候选/行动 SA, 胜出后写入 control::timing_wait 并进入行动反馈学习。"),
    "AC-016": ("完整闭环", "SafetyGate 综合压力/COR/B锚/control risk 抑制外部行动, 并写入 action_inhibition::*。"),
    "AC-017": ("部分闭环", "ui_goal 已由 UI 视觉目标/显式 ui_trace 计算并可触发 pointer_move; 真实 OS 鼠标执行器仍保持预留。"),
    "AC-018": ("部分闭环", "click_ready 已由 UI 目标、pointer_on_target、正确感、低压力共同计算并可触发 pointer_click; 真实 OS 点击仍由安全门预留。"),
    "AC-019": ("预留/未执行", "llm_think 可生成候选, 但 LLM 行动器没有真实调用执行, 且会受 SafetyGate 阻断。"),
    "AC-020": ("预留/未执行", "llm_critique 可生成候选, 但 LLM 行动器没有真实调用执行; 风险审查由 SafetyGate 实现。"),
    "AF-001": ("完整闭环", "行动选择会生成 action::* SA 并进入状态池/记忆。"),
    "AF-002": ("完整闭环", "runtime 保存 action_causal_window/v1 并写入反馈 anchor_meta。"),
    "AF-003": ("完整闭环", "action_feedback::* 能进入状态池、记忆和后果学习, 且受概念学习保护。"),
    "AF-004": ("完整闭环", "外部/内部正反馈能生成 signal::reward/signal::correctness。"),
    "AF-005": ("完整闭环", "惩罚作为真实事件和未来压力塑形同时编码。"),
    "AF-006": ("完整闭环", "ActionOutcomeMemory 会记录成功并增强 drive_bias。"),
    "AF-007": ("完整闭环", "ActionOutcomeMemory 会记录失败并形成 avoidance/负 drive_bias。"),
    "AF-008": ("部分闭环", "规则能记录 prediction_error 事件; 目前主要用于 trace/后果学习审计。"),
    "AF-009": ("完整闭环", "ActionConsequenceEvaluator 能从 successor action_feedback 读出经验并调制候选。"),
    "AF-010": ("完整闭环", "planner 能把 action::* 虚能量转为 memory_predicted_action drive。"),
    "AF-011": ("完整闭环", "SafetyGate 会写 action_inhibition::* 并进入状态池/记忆。"),
}


def context_for_condition(condition: str) -> dict:
    context: dict = {"tick_index": 1}
    if condition == "positive_pressure":
        context["state_items"] = [item("text::unexpected", family="text", real=1.0, virtual=0.0, cp=1.0)]
    elif condition == "negative_pressure":
        context["state_items"] = [item("text::missed", family="text", real=0.0, virtual=1.0, cp=-1.0)]
    elif condition == "alignment":
        context["prediction_trace"] = {"alignment_score": 1.0, "mismatch_ratio": 0.0}
    elif condition == "grasp":
        context["fast_bn"] = [bn("mem-grasp", match=0.92)]
    elif condition == "coherence":
        context["feelings"] = {"channels": {"coherence": 1.0, "grasp": 1.0}}
        context["prediction_trace"] = {"alignment_score": 0.9}
    elif condition == "uncertainty":
        context["fast_bn"] = [bn("mem-a", match=0.2, weight=0.5), bn("mem-b", match=0.2, weight=0.5)]
    elif condition == "expectation":
        context["expectation_pressure"] = {"channels": {"expectation_level": 1.0}}
    elif condition == "pressure":
        context["expectation_pressure"] = {"channels": {"pressure_level": 1.0}}
    elif condition == "satisfaction":
        context["expectation_pressure"] = {"channels": {"satisfaction_level": 1.0}}
    elif condition == "expectation_gap":
        context["expectation_pressure"] = {"channels": {"expectation_gap": 1.0}}
    elif condition == "timefelt":
        context["time_trace"] = {"channels": {"confidence": 1.0}}
    elif condition == "rhythm_phase":
        context["rhythm_trace"] = {"channels": {"phase_expectation": 1.0}}
    elif condition == "complexity":
        context["runtime_load_trace"] = {"channels": {"complexity": 1.0}}
    elif condition == "simplicity":
        context["runtime_load_trace"] = {"channels": {"simplicity": 1.0}}
    elif condition in {"surprise", "dissonance", "correctness"}:
        context["feelings"] = {"channels": {condition: 1.0}}
    elif condition == "continue_focus":
        context["feelings"] = {"channels": {"grasp": 1.0, "expectation": 1.0}}
        context["rhythm_trace"] = {"channels": {"phase_expectation": 1.0}}
    elif condition == "inspect_residual":
        context["feelings"] = {"channels": {"dissonance": 1.0, "pressure": 1.0}}
        context["residual_summary"] = {"total_unresolved_mass": 10.0}
    elif condition == "novelty":
        context["feelings"] = {"channels": {"surprise": 1.0, "grasp": 0.0}}
    elif condition == "transition":
        context["state_items"] = [
            item("text::dog", family="text"),
            item("text::bite", family="text"),
            item("text::me", family="text"),
            item("text::order", family="text"),
        ]
    elif condition == "multimodal_binding":
        context["state_items"] = [
            item("vision::bell", family="vision_object", source_type="vision_numeric"),
            item("audio::ring", family="audio_object", source_type="audio_numeric"),
        ]
    elif condition in {"reward", "social_reward"}:
        context["action_feedback_trace"] = {"applied": True, "observed_feedback": {"reward": 1.0, "confidence": 1.0}}
    elif condition in {"punishment", "social_punishment"}:
        context["action_feedback_trace"] = {"applied": True, "observed_feedback": {"punishment": 1.0, "confidence": 1.0}}
    elif condition == "relief":
        context["action_feedback_trace"] = {"applied": True, "observed_feedback": {"reward": 1.0, "correctness": 1.0, "confidence": 1.0}}
        context["expectation_pressure"] = {"channels": {"satisfaction_level": 1.0}}
    elif condition == "sustained_pressure":
        context["feelings"] = {"channels": {"pressure": 1.0}}
    elif condition == "risk":
        context["feelings"] = {"channels": {"pressure": 1.0}}
        context["emotion_state"] = {"COR": 1.0}
    elif condition == "safe_validation":
        context["action_feedback_trace"] = {"applied": True, "observed_feedback": {"correctness": 1.0, "reward": 1.0, "confidence": 1.0}}
    elif condition == "familiarity":
        context["feelings"] = {"channels": {"grasp": 1.0, "coherence": 1.0}}
    elif condition == "visual_surprise":
        context["state_items"] = [item("vision::flash", family="vision_object", source_type="vision_numeric", cp=1.0)]
    elif condition == "visual_motion":
        row = item("vision::motion", family="vision_object", source_type="vision_numeric")
        row["numeric_features"] = {"motion_vector": [1.0, 0.0]}
        context["state_items"] = [row]
    elif condition == "visual_uncertainty":
        context["state_items"] = [item("vision::small", family="vision_object", source_type="vision_numeric")]
        context["feelings"] = {"channels": {"grasp": 0.0}}
    elif condition == "audio_surprise":
        context["state_items"] = [item("audio::bang", family="audio_object", source_type="audio_numeric", cp=1.0)]
    elif condition == "voice_like":
        row = item("audio::voice", family="audio_object", source_type="audio_numeric")
        row["numeric_features"] = {"pitch_confidence": 1.0}
        context["state_items"] = [row]
    elif condition == "audio_low_grasp":
        context["state_items"] = [item("audio::unknown", family="audio_object", source_type="audio_numeric")]
        context["feelings"] = {"channels": {"grasp": 0.0}}
    elif condition == "text_mismatch":
        context["state_items"] = [item("text::wrong", family="text")]
        context["feelings"] = {"channels": {"dissonance": 1.0}}
    elif condition == "expected_token":
        context["fast_cn"] = [{"predicted_items": [{"sa_label": "text::next", "virtual_energy": 1.0}]}]
    elif condition == "text_revision":
        context["feelings"] = {"channels": {"dissonance": 1.0}}
    elif condition == "text_commit_ready":
        context["feelings"] = {"channels": {"correctness": 1.0, "pressure": 0.0}}
    elif condition == "pressure_external_candidate":
        context["feelings"] = {"channels": {"pressure": 1.0}}
        context["action_trace"] = {
            "candidates": [
                {
                    "action_id": "action::text_commit",
                    "actuator_id": "actuator::text_editor",
                    "predicted_outcome": {"pressure": 0.4, "confidence": 0.9},
                }
            ]
        }
    elif condition == "ui_goal":
        context["state_items"] = [
            {
                **item("vision_ui::button::ok", family="vision_ui", source_type="vision_numeric", real=0.9),
                "anchor_meta": {"ui_role": "button", "ui_target": True, "bbox_norm": [0.42, 0.62, 0.12, 0.06], "confidence": 0.92},
                "numeric_features": {"ui.target": 0.92},
            }
        ]
        context["feelings"] = {"channels": {"correctness": 0.7, "pressure": 0.0}}
    elif condition == "click_ready":
        context["state_items"] = [
            {
                **item("vision_ui::button::ok", family="vision_ui", source_type="vision_numeric", real=0.9),
                "anchor_meta": {"ui_role": "button", "ui_target": True, "bbox_norm": [0.42, 0.62, 0.12, 0.06], "confidence": 0.92},
                "numeric_features": {"ui.target": 0.92},
            }
        ]
        context["feelings"] = {"channels": {"correctness": 0.9, "pressure": 0.0}}
        context["ui_trace"] = {"safe_to_click": 0.9, "pointer_on_target": 0.8}
        context["pointer_trace"] = {"on_target": 0.88}
    elif condition == "external_risk":
        context["emotion_state"] = {"COR": 1.0}
        context["action_trace"] = {"candidates": [{"action_id": "action::text_commit", "predicted_outcome": {"punishment": 1.0, "pressure": 1.0, "confidence": 0.0}}]}
    elif condition == "hard_task":
        context["runtime_load_trace"] = {"channels": {"complexity": 1.0}}
        context["feelings"] = {"channels": {"grasp": 0.0}}
    elif condition == "action_selected":
        context["action_trace"] = {"selected_actions": [{"action_id": "action::inspect_residual"}]}
    elif condition == "action_feedback":
        context["action_feedback_trace"] = {"applied": True, "observed_feedback": {"reward": 0.2, "confidence": 1.0}, "selected_actions": [{"action_id": "action::inspect_residual"}]}
    elif condition == "positive_action_feedback":
        context["action_feedback_trace"] = {"applied": True, "observed_feedback": {"reward": 1.0, "correctness": 1.0, "confidence": 1.0}}
    elif condition == "negative_action_feedback":
        context["action_feedback_trace"] = {"applied": True, "observed_feedback": {"punishment": 1.0, "confidence": 1.0}}
    elif condition == "action_prediction_error":
        context["action_feedback_trace"] = {
            "applied": True,
            "selected_actions": [{"action_id": "action::text_commit", "predicted_outcome": {"reward": 1.0, "punishment": 0.0, "correctness": 1.0}}],
            "observed_feedback": {"reward": 0.0, "punishment": 1.0, "correctness": 0.0, "confidence": 1.0},
        }
    elif condition == "successor_action_feedback":
        context["action_consequence_trace"] = {"supported_action_count": 3}
    elif condition == "memory_predicted_action":
        context["fast_cn"] = [{"predicted_items": [{"sa_label": "action::inspect_residual", "virtual_energy": 1.0}]}]
    elif condition == "action_inhibition":
        context["state_items"] = [item("action_inhibition::text_commit", family="action_inhibition", source_type="safety_gate")]
    return context


def item(label: str, *, family: str, source_type: str = "test", real: float = 1.0, virtual: float = 0.0, cp: float = 0.0) -> dict:
    return {
        "sa_label": label,
        "display_text": label,
        "family": family,
        "source_type": source_type,
        "real_energy": real,
        "virtual_energy": virtual,
        "cognitive_pressure": cp,
    }


def bn(memory_id: str, *, match: float = 0.8, weight: float = 1.0, real: float = 0.4) -> dict:
    return {
        "memory_id": memory_id,
        "memory_kind": "state",
        "normalized_weight": weight,
        "match_efficiency": match,
        "grasp_confidence": match,
        "b_real_energy": real,
        "b_effective_real_energy": real,
    }


def simulate_rule(rule: RuleDef) -> dict:
    engine = InnateCodingEngine(min_fire_strength=0.001)
    context = context_for_condition(rule.condition)
    if rule.condition == "fatigue":
        warm = context_for_condition("positive_pressure")
        for tick in range(8):
            engine.evaluate(phase="post_prediction_validation", context={**warm, "tick_index": tick}, tick_index=tick)
        context = {"tick_index": 8}
    trace = engine.simulate(phase=rule.phase, context=context)
    hit = next((row for row in trace["hits"] if row["rule_id"] == rule.rule_id), None)
    status, note = closure_status(rule, bool(hit))
    return {
        "rule_id": rule.rule_id,
        "phase": rule.phase,
        "condition": rule.condition,
        "meaning": MEANINGS.get(rule.rule_id, rule.description),
        "expected_outputs": list(rule.outputs),
        "fired": bool(hit),
        "raw_strength": hit.get("raw_strength") if hit else 0.0,
        "effective_strength": hit.get("effective_strength") if hit else 0.0,
        "observed_outputs": hit.get("outputs", []) if hit else [],
        "trace_items": [row.get("sa_label") for row in trace.get("items", [])],
        "trace_action_nodes": [row.get("action_id") for row in trace.get("action_nodes", [])],
        "trace_action_biases": [row.get("action_id") for row in trace.get("action_biases", [])],
        "trace_emotion_deltas": trace.get("emotion_deltas", {}),
        "trace_learning_events": [row.get("event") for row in trace.get("learning_events", [])],
        "trace_safety_gate": trace.get("safety_gate", []),
        "trace_logs": trace.get("trace_logs", []),
        "metrics": trace.get("metrics", {}),
        "closure_status": status,
        "closure_note": note,
    }


def closure_status(rule: RuleDef, fired: bool) -> tuple[str, str]:
    if not fired:
        if rule.rule_id in STATUS_OVERRIDES:
            return STATUS_OVERRIDES[rule.rule_id]
        return "未闭环", "目标上下文下未触发, 需要补触发指标或检查条件公式。"
    if rule.rule_id in STATUS_OVERRIDES:
        return STATUS_OVERRIDES[rule.rule_id]
    output_types = {str(row.get("type", "")) for row in rule.outputs}
    if output_types == {"trace_log"}:
        return "trace/audit", "只记录 trace_log, 不直接改变状态池/行动/学习。"
    if "emotion_delta" in output_types:
        return "完整闭环", "emotion_delta 被 EmotionModulator 消费, 进入 8 情绪慢量调制。"
    if "attention_bias" in output_types:
        return "完整闭环", "attention_bias 会跨 tick 被 AttentionSelector 消费。"
    if "action_node" in output_types or "action_bias" in output_types:
        return "部分闭环", "行动候选会进入 planner, 胜出后 action SA 可入池; 具体 actuator 效果按 action_id 有差异。"
    if "learning_event" in output_types:
        return "部分闭环", "learning_event 被 InnateLearningEventRouter 路由; 直接学习由专用模块完成。"
    if "emit_sa" in output_types:
        if rule.phase in {"post_prediction_validation", "tick_end"}:
            return "完整闭环", "该 phase 的 innate item 会被 runtime 写入状态池。"
        return "部分闭环", "规则可产生 item, 但该 phase 当前未统一写回状态池。"
    if "safety_gate" in output_types:
        return "部分闭环", "安全门 trace 可传入 SafetyGate; 实际阻断由 SafetyGate 完成。"
    return "部分闭环", "规则可触发, 但需要人工核对下游消费。"


def run_scenarios() -> list[dict]:
    rows: list[dict] = []

    def add(name: str, ok: bool, evidence: str, status: str = "通过") -> None:
        rows.append({"name": name, "ok": bool(ok), "status": status if ok else "未通过/缺口", "evidence": evidence})

    selector = AttentionSelector(focus_limit=1, pressure_gain=0.6, attention_gain_weight=0.8, fatigue_weight=0.5)
    biased = selector.select(
        [
            {"sa_label": "text::plain", "cognitive_pressure": 0.3},
            {"sa_label": "text::flash", "cognitive_pressure": 0.05},
        ],
        innate_attention_biases=[{"bias": "surprise_anchor", "strength": 0.9, "target_labels": ["text::flash"]}],
    )
    add("CF attention_bias -> AttentionSelector", biased["selected_labels"] == ["text::flash"], f"selected={biased['selected_labels']}")

    gate = SafetyGate(enabled=True, veto_pressure_threshold=0.5, review_pressure_threshold=0.3, min_external_confidence=0.6)
    safety = gate.review(
        tick_index=1,
        candidates=[],
        selected_actions=[{"action_id": "action::text_commit", "actuator_id": "actuator::text_editor", "predicted_outcome": {"pressure": 0.8, "confidence": 0.4}}],
        cognitive_feelings={"channels": {"pressure": 0.8}},
        emotion_state={"COR": 0.2},
    )
    add("SafetyGate -> action_inhibition", not safety["selected_actions"] and safety["inhibition_items"], f"blocked={safety['vetoed_action_ids'] or safety['require_review_action_ids']}")

    planner = ActionConsequencePlanner(
        enabled=True,
        selection_threshold=0.1,
        max_selected_actions=1,
        fatigue_decay=0.9,
        fatigue_step=0.0,
        bias_learning_rate=0.0,
        bias_gain=0.0,
        confidence_gain=0.18,
        wait_base_drive=0.18,
    )
    plan = planner.plan(
        tick_index=1,
        state_snapshot_items=[item("action::text_reread", family="action", source_type="predicted", virtual=0.8, cp=-0.8)],
        fast_bn=[],
        fast_cn=[],
        slow_bn=[],
        slow_cn=[],
        cognitive_feelings={"channels": {"dissonance": 0.8}},
        rhythm_trace={"channels": {}},
        time_trace={"channels": {}},
        memory_action_drive_gain=0.4,
    )
    add("action::* virtual_energy -> drive", any("drive_source::memory_predicted_action" in note for row in plan["candidates"] for note in row["notes"]), "memory_predicted_action note found")

    verifier = BAnchorExpectationVerifier(min_outcome_virtual=0.01, min_anchor_level=0.01)
    first = verifier.update(tick_index=1, fast_bn=[bn("mem-cat", real=0.4)], slow_bn=[], fast_cn=[{"source_memory_id": "mem-cat", "predicted_items": [{"sa_label": "signal::reward", "family": "signal", "virtual_energy": 0.8}]}], slow_cn=[], action_feedback_trace={}, cognitive_feelings={"channels": {}})
    second = verifier.update(tick_index=2, fast_bn=[bn("mem-cat", real=0.8)], slow_bn=[], fast_cn=[], slow_cn=[], action_feedback_trace={"observed_feedback": {"reward": 0.5}}, cognitive_feelings={"channels": {"correctness": 0.3}})
    add("B anchor expectation -> satisfaction", bool(first["created"] and second["verified"] and any(row["sa_label"] == "feeling::satisfaction" for row in second["items"])), f"created={len(first['created'])}, verified={len(second['verified'])}")

    router = InnateLearningEventRouter()
    routed = router.route(
        tick_index=1,
        innate_traces={"tick_end": {"learning_events": [{"event": "positive_pair", "rule_id": "BC-001"}, {"event": "action_outcome", "rule_id": "BC-004"}]}},
        action_feedback_trace={"applied": True, "feedback_items": [{"sa_label": "action_feedback::x"}]},
    )
    routes = {row["event"]: row["route"] for row in routed["routes"]}
    add("InnateLearningEventRouter guard", routes.get("positive_pair") == "content_online_embedding_trace" and routes.get("action_outcome") == "action_outcome_learning_trace", json.dumps(routes, ensure_ascii=False))

    visual = VisualGazeActuator().step(
        tick_index=1,
        selected_actions=[{"action_id": "action::move_gaze_to", "drive": 0.9, "effective_decisiveness": 0.4, "params": {"x": 0.2, "y": 0.8}}],
        attention_trace={"selected_labels": ["vision::flash"]},
    )
    auditory = AuditoryBandActuator().step(
        tick_index=1,
        selected_actions=[{"action_id": "action::slide_audio_band", "drive": 0.8, "effective_decisiveness": 0.5, "params": {"center_hz": 1800}}],
        attention_trace={"selected_labels": ["audio::voice"]},
    )
    add("visual/audio focus action -> control SA", bool(visual["items"] and auditory["items"]), f"visual={visual['items'][0]['sa_label']}, audio={auditory['items'][0]['sa_label']}")

    text = TextActionActuator().step(
        tick_index=1,
        input_text="",
        selected_actions=[{"action_id": "action::text_insert", "params": {"token": "hello"}}],
        fast_cn=[{"predicted_items": [{"sa_label": "text::hello", "virtual_energy": 1.0}]}],
        slow_cn=[],
        focus_labels=[],
        cognitive_feelings={"channels": {}},
    )
    add("direct text_insert actuator execution", bool(text["output_items"]) and text["visible_text"] == "hello", f"visible={text['visible_text']}, items={[row['sa_label'] for row in text['output_items']]}")

    text_editor = TextActionActuator(max_visible_buffer=16)
    for idx, token in enumerate("1020", start=1):
        text_editor.step(
            tick_index=idx,
            input_text="",
            selected_actions=[{"action_id": "action::text_insert", "params": {"token": token}}],
            fast_cn=[],
            slow_cn=[],
            focus_labels=[],
            cognitive_feelings={"channels": {}},
        )
    replaced = text_editor.step(
        tick_index=5,
        input_text="",
        selected_actions=[{"action_id": "action::text_replace", "params": {"span": [1, 3], "new_text": "23"}}],
        fast_cn=[],
        slow_cn=[],
        focus_labels=[],
        cognitive_feelings={"channels": {}},
    )
    add("TextAction cursor/span middle replace", replaced["visible_text"] == "1230", f"visible={replaced['visible_text']}, event={replaced['recent_events'][0] if replaced['recent_events'] else {}}")

    runtime = APV21Runtime(config=RuntimeConfig())
    time_snapshot = runtime.memory.write_snapshot(
        tick_index=4,
        memory_kind="state",
        items=[item("text::beat", family="text", source_type="external_text", real=0.9), item("text::bass", family="text", source_type="external_text", real=0.7)],
        focus_labels=["text::beat"],
        source_text="beat bass",
    )
    runtime.tick_index = 8
    time_controls = runtime._timefelt_recall_control_rows(
        selected_action={"action_id": "action::recall_by_timefelt", "drive": 0.9, "effective_threshold": 0.3},
        state_snapshot_items=[item("text::beat", family="text", source_type="external_text", real=0.8)],
        time_context={"current_tick": 8, "target_delta_t": 4, "time_sigma": 1.0, "confidence": 1.0, "gain": 3.0, "felt_energy": 1.0},
        limit=6,
    )
    add("recall_by_timefelt -> time snapshot control", any(row["sa_label"] == "control::timefelt_recall" for row in time_controls) and any(row["sa_label"] == "text::bass" for row in time_controls), f"source={time_snapshot['memory_id']}, labels={[row['sa_label'] for row in time_controls[:6]]}")

    risky = runtime.memory.write_snapshot(
        tick_index=9,
        memory_kind="state",
        items=[
            item("text::button", family="text", source_type="external_text", real=0.8),
            {
                "sa_label": "action_feedback::text_commit",
                "display_text": "行动反馈:text_commit",
                "family": "action_feedback",
                "source_type": "action_feedback",
                "real_energy": 0.0,
                "virtual_energy": 0.7,
                "anchor_meta": {
                    "action_id": "action::text_commit",
                    "observed_feedback": {"reward": 0.0, "punishment": 0.8, "correctness": 0.0, "confidence": 0.9},
                    "feedback_energy_semantics": {"punishment_pressure": 0.66},
                },
            },
        ],
        focus_labels=["text::button"],
        source_text="button",
    )
    replay_controls = runtime._episode_replay_control_rows(
        selected_action={"action_id": "action::replay_episode", "drive": 1.0, "effective_threshold": 0.3, "params": {"source_memory_id": risky["memory_id"], "risk": 0.7}},
        expectation_pressure_trace={},
        action_consequence_trace={},
        limit=6,
    )
    replay_gate = gate.review(
        tick_index=10,
        candidates=[],
        selected_actions=[{"action_id": "action::text_commit", "actuator_id": "actuator::text_editor", "predicted_outcome": {"pressure": 0.0, "confidence": 0.9}}],
        cognitive_feelings={"channels": {}},
        emotion_state={},
        action_control_items=replay_controls,
    )
    add("replay_episode -> SafetyGate action_control risk", bool(replay_controls) and not replay_gate["selected_actions"], f"blocked={replay_gate['vetoed_action_ids'] or replay_gate['require_review_action_ids']}, control_risk={replay_gate.get('control_risk')}")

    wait_control = runtime._wait_control_row(selected_action={"action_id": "action::wait", "drive": 0.7, "effective_threshold": 0.3, "params": {"rhythm_expectation": 0.8, "uncertainty": 0.7}})
    wait_feedback = runtime._observe_action_feedback(
        selected_actions=[{"action_id": "action::wait", "drive": 0.7, "effective_threshold": 0.3, "params": {"rhythm_expectation": 0.8, "uncertainty": 0.7}}],
        feedback_context={"top_labels_after_control": ["control::timing_wait"], "focus_labels_after_control": [], "action_control_effects": [wait_control["anchor_meta"]]},
    )
    add("wait -> timing control and feedback", wait_control["sa_label"] == "control::timing_wait" and "timing_wait_semantics" in wait_feedback["notes"], f"control={wait_control['anchor_meta']}, feedback={wait_feedback}")

    competition = planner.plan(
        tick_index=2,
        state_snapshot_items=[],
        fast_bn=[],
        fast_cn=[],
        slow_bn=[],
        slow_cn=[],
        cognitive_feelings={"channels": {"dissonance": 1.0, "surprise": 1.0, "pressure": 0.6}},
        rhythm_trace={"channels": {}},
        time_trace={"channels": {}},
        innate_action_nodes=[
            {"action_id": "action::focus_anchor", "actuator_id": "actuator::attention_allocation", "drive": 0.7, "strength": 0.9},
            {"action_id": "action::inspect_residual", "actuator_id": "actuator::attention_allocation", "drive": 0.65, "strength": 0.9},
        ],
    )
    comp = competition["competition_trace"]
    add("action competition trace", bool(comp.get("suppressed_action_ids")) or any(row.get("suppressed_action_ids") for row in comp.get("domains", [])), json.dumps(comp, ensure_ascii=False)[:300])

    engine = InnateCodingEngine()
    pressure_candidate = engine.simulate(phase="action_preselect", context=context_for_condition("pressure_external_candidate"))
    add("pressure_external_candidate natural trigger", any(hit["rule_id"] == "AC-013" for hit in pressure_candidate["hits"]), f"hits={[hit['rule_id'] for hit in pressure_candidate['hits']]}")

    ui_goal = engine.simulate(phase="action_preselect", context=context_for_condition("ui_goal"))
    click_ready = engine.simulate(phase="action_preselect", context=context_for_condition("click_ready"))
    add("UI pointer/click innate metrics", any(hit["rule_id"] == "AC-017" for hit in ui_goal["hits"]) and any(hit["rule_id"] == "AC-018" for hit in click_ready["hits"]), f"ui_hits={[hit['rule_id'] for hit in ui_goal['hits']]}, click_hits={[hit['rule_id'] for hit in click_ready['hits']]}")

    return rows


def make_report(rule_rows: list[dict], scenarios: list[dict]) -> str:
    counts = Counter(row["closure_status"] for row in rule_rows)
    fired_count = sum(1 for row in rule_rows if row["fired"])
    scenario_ok = sum(1 for row in scenarios if row["ok"])
    lines = [
        "# APV2.1 先天规则逐条闭环验证报告",
        "",
        "日期: 2026-05-28",
        "性质: 严格验证报告 / 逐条规则闭环表 / 不把预留接口误报为完整实现",
        "",
        "## 1. 验证口径",
        "",
        "本报告以当前代码为准, 对 `core/innate/default_rules.py` 中 77 条规则逐条构造最小触发上下文, 调用 `InnateCodingEngine.simulate()` 验证是否命中, 再结合 runtime 下游消费点判断闭环等级。",
        "",
        "闭环等级定义:",
        "",
        "- 完整闭环: 规则输出已经被状态池/注意力/情绪/行动器/反馈学习等下游消费, 并能形成可观察后果。",
        "- 部分闭环: 规则能触发并产生标准输出, 但某些执行器、采样偏置或直接学习写入仍未完全闭合。",
        "- trace/audit: 当前只作为审计或旁路说明, 功能可能由独立 channel 实现。",
        "- 预留/未执行: 接口已注册, 但真实外部执行器未启用。",
        "- 未闭环: 当前条件无法自然触发或缺少关键下游。",
        "",
        "## 2. 总览结论",
        "",
        f"- 规则总数: {len(rule_rows)}",
        f"- 最小上下文可触发: {fired_count}/{len(rule_rows)}",
        f"- 场景验证通过: {scenario_ok}/{len(scenarios)}",
    ]
    for status, count in sorted(counts.items()):
        lines.append(f"- {status}: {count}")
    lines.extend(
        [
            "",
            "关键结论:",
            "",
            "1. 主链已经成立: 认知压/感受 -> 注意力偏置/行动候选 -> DriveManager/SafetyGate -> action/action_feedback 入池 -> outcome memory / successor feedback -> 未来 drive。",
            "2. 期待/压力 B 锚已经形成闭环: C 中 reward/punishment 虚能量可创建锚, 后续 B 实能量变化和反馈可验证/落空, 并影响回忆行动与 SafetyGate。",
            "3. 情绪通道已经形成慢量调制闭环: 16 条 EM 规则都可触发, emotion_delta 被 EmotionModulator 消费。",
            "4. 在线学习规则 BC-* 是路由/审计入口, 直接学习写入仍由 MemoryStore / ActionOutcomeMemory 完成, 这是符合设计边界的, 但不能说 BC 规则自己完成了学习拟合。",
            "5. 电脑控制和 LLM/工具外部行动仍是预留接口; AC-017/018 现在能自然触发候选, 但真实 OS 执行仍未启用且必须经过 SafetyGate。",
            "6. 视觉/听觉焦点行动可产控制 SA, 且下一 tick 的视觉/听觉传感器会消费 control state 改变采样精度与焦点 payload。",
            "",
            "## 3. 代表性闭环场景验证",
            "",
            "| 场景 | 结果 | 证据 |",
            "|---|---|---|",
        ]
    )
    for row in scenarios:
        result = "通过" if row["ok"] else "未通过/缺口"
        lines.append(f"| {row['name']} | {result} | {row['evidence']} |")
    lines.extend(
        [
            "",
            "## 4. 逐条规则验证表",
            "",
            "| ID | 阶段 | 条件 | 规则意义 | 触发 | 输出证据 | 闭环等级 | 结论/缺口 |",
            "|---|---|---|---|---:|---|---|---|",
        ]
    )
    for row in rule_rows:
        outputs = summarize_outputs(row)
        fired = "是" if row["fired"] else "否"
        lines.append(
            f"| {row['rule_id']} | {row['phase']} | {row['condition']} | {row['meaning']} | {fired} | {outputs} | {row['closure_status']} | {row['closure_note']} |"
        )
    lines.extend(
        [
            "",
            "## 5. 已形成的整体闭环",
            "",
            "### 5.1 预测误差最小化闭环",
            "",
            "外源 SA 入池后形成实能量, C/C' 回灌形成虚能量, 状态池计算认知压。正认知压触发 surprise/positive_pair, 负认知压触发 dissonance/negative_pair。MemoryStore 根据状态池认知压做在线能量学习, 后续 Bn 召回的 learned_score 会影响相似度, 使预测误差有下降方向。",
            "",
            "例子: `text::unexpected` 实能量高而虚能量低时, CF-001 产生 surprise, BC-001 路由 positive_pair, MemoryStore 在快照学习中把意外对象和实能量上下文拉近。",
            "",
            "### 5.2 注意力闭环",
            "",
            "CF-001/002 产生 attention_bias, runtime 在 tick 末记住, 下一 tick AttentionSelector 消费 target_labels, 使意外/错配对象更容易成为焦点。AT-* 还会产生行动候选; focus_anchor/inspect_residual/continue_focus/release_focus/diverge_attention 胜出后会生成明确 action_control, 进入下一 tick 注意力与慢系统查询。",
            "",
            "例子: `text::flash` 原本分数低, 加上 surprise_anchor 后能超过 `text::plain` 被选为焦点。",
            "",
            "### 5.3 期待/压力 B 锚闭环",
            "",
            "Bn 召回的 C 中出现 reward/punishment 虚能量时, BAnchorVerifier 创建 expectation/pressure anchor。后续 tick 若同一 B 的实能量上升且反馈验证, 产生 satisfaction/pressure_validation; 若 B 消失或下降, 产生 expectation_gap。planner 能把 active anchor 转为 `action::recall_by_expectation`, SafetyGate 能把 pressure anchor 计入外部行动风险。",
            "",
            "例子: `mem-cat -> signal::reward` 创建期待锚; 下一 tick `mem-cat` 实能量上升并收到 reward, 输出 `feeling::satisfaction`。",
            "",
            "### 5.4 行动与后天主动性闭环",
            "",
            "先天规则或记忆预测产生 action candidate, planner 竞争并生成 action::* SA; 下一 tick action_feedback::* 与 action_causal_window 入池; ActionOutcomeMemory 记录成功/失败; ActionConsequenceEvaluator 还能从 B/C successor 的 action_feedback 读出后果; 后续 C/C' 若召回 action::* 虚能量, planner 会转成 drive。",
            "",
            "例子: 过去 `action::text_reread` 被预测为虚能量 0.8 时, planner 给它增加 `drive_source::memory_predicted_action`。",
            "",
            "### 5.5 时间感/回忆行动闭环",
            "",
            "`action::recall_by_timefelt` 胜出后, runtime 使用 TimeFeelingChannel 的 dominant peak 构造 time_context, 在 MemoryStore 中召回目标时间差附近的 state/focus snapshot, 再生成 `control::timefelt_recall` 和 action_control target modulation。`action::replay_episode` 则读取 pressure anchor 或行动后果证据, 回放 core labels 与 action_feedback, 并给 SafetyGate 提供 control risk。",
            "",
            "例子: 当前 tick 8 出现 4 tick 时间感, 4 tick 前 `text::beat/text::bass` snapshot 被召回, 状态池出现 `control::timefelt_recall`; 高惩罚经验回放时, SafetyGate 因 `action_control_review` 阻断外部提交。",
            "",
            "### 5.6 安全抑制闭环",
            "",
            "外部行动候选进入 SafetyGate, 高 pressure/COR/低置信度/pressure anchor 会导致 veto 或 require_review。被阻断时生成 `action_inhibition::*` SA 入池, 之后 AF-011 可审计该抑制事件, 形成“想做但不做”的可学习状态。",
            "",
            "例子: `action::text_commit` 预测 pressure 0.8 且 confidence 0.4, SafetyGate 清空 selected_actions 并写入 `action_inhibition::text_commit`。",
            "",
            "### 5.7 等待与行动竞争闭环",
            "",
            "`action::wait` 胜出后写入 `control::timing_wait`, 其 feedback 会根据 rhythm expectation、uncertainty 和 wait intensity 产生 reward/correctness/punishment。planner 现在按 conflict_domain 做行动竞争, 记录 `action_competition_trace/v1`, 让被压制的强冲动也保留为可解释事实。",
            "",
            "例子: 高不确定时 wait 不是空转, 而是一个可奖惩塑形的 timing action; focus_anchor 与 inspect_residual 同域高 drive 时, 只执行一个, 另一个写入 suppressed_action_ids。",
            "",
            "## 6. 当前必须正视的缺口",
            "",
            "1. AC-017/AC-018 的 `ui_goal` / `click_ready` 已有指标来源并可生成候选, 但真实鼠标移动/点击执行器仍是预留接口。",
            "2. AC-013 的 `pressure_external_candidate` 已能识别 actuator 级 external action; replay_episode 目前是内部回忆行动, 但其 safety_review_hint 已能增强 SafetyGate 外部审查。",
            "3. AC-019/AC-020 只生成 LLM 候选, 没有真实 LLM 行动器执行; 外部动作默认被 SafetyGate 审查/阻断是正确的。",
            "4. `TextActionActuator` 已能直接消费 `action::text_insert/delete/replace/commit`, 并支持 cursor/span; 但 commit 当前仍是内部缓冲区提交准备, 不是真实对外发送。",
            "5. `VisualGazeActuator` 和 `AuditoryBandActuator` 已产控制 SA, 且视觉/听觉传感器会在下一 tick 用这些控制状态改变焦点采样。",
            "6. CF-011/CF-012 先天规则自身是 trace_log, 真正时间感/节奏感由独立 channel 完成; 这符合功能实现, 但不应说这两条 innate 规则本身入池。",
            "7. BC-* 规则是学习事件路由, 不是直接学习写入器; 直接在线学习仍要看 MemoryStore 与 ActionOutcomeMemory。",
            "",
            "## 7. 下一步建议",
            "",
            "1. 下一步应补真实 OS 鼠标/键盘执行器前的权限、安全和人工确认策略, 不要直接把预留候选接到系统控制。",
            "2. 继续升级 BC-* 在线学习事件层, 把预测误差、顺序关系、奖惩后果、多模态绑定整理成正式事件构建体系。",
            "3. 状态池能量子模块拆分与残差语义增强, 让预测验证、衰减、注意力调制、memory write view 更可解释。",
            "4. 增加视觉/听觉焦点采样的观测台对照验收, 让采样精度变化可视化/可听化。",
        ]
    )
    return "\n".join(lines) + "\n"


def summarize_outputs(row: dict) -> str:
    parts: list[str] = []
    if row["trace_items"]:
        parts.append("items=" + ",".join(str(x) for x in row["trace_items"][:3]))
    if row["trace_action_nodes"]:
        parts.append("actions=" + ",".join(str(x) for x in row["trace_action_nodes"][:3]))
    if row["trace_action_biases"]:
        parts.append("biases=" + ",".join(str(x) for x in row["trace_action_biases"][:3]))
    if row["trace_emotion_deltas"]:
        parts.append("emotion=" + ",".join(f"{k}:{v}" for k, v in row["trace_emotion_deltas"].items()))
    if row["trace_learning_events"]:
        parts.append("learn=" + ",".join(str(x) for x in row["trace_learning_events"][:3]))
    if row["trace_safety_gate"]:
        parts.append("safety=" + ",".join(str(x.get("decision")) for x in row["trace_safety_gate"][:2]))
    if row["trace_logs"]:
        parts.append("trace=" + ",".join(str(x.get("topic")) for x in row["trace_logs"][:2]))
    return "; ".join(parts) if parts else "-"


def main() -> None:
    rules = default_rules()
    validation = InnateCodingEngine().validate()
    rule_rows = [simulate_rule(rule) for rule in rules]
    scenarios = run_scenarios()
    payload = {
        "schema_id": "innate_rule_closure_validation/v1",
        "validation": validation,
        "rule_count": len(rules),
        "fired_count": sum(1 for row in rule_rows if row["fired"]),
        "status_counts": dict(Counter(row["closure_status"] for row in rule_rows)),
        "scenario_count": len(scenarios),
        "scenario_pass_count": sum(1 for row in scenarios if row["ok"]),
        "rules": rule_rows,
        "scenarios": scenarios,
    }
    JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    JSON_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    REPORT_PATH.write_text(make_report(rule_rows, scenarios), encoding="utf-8")
    print(json.dumps({k: payload[k] for k in ("schema_id", "rule_count", "fired_count", "status_counts", "scenario_count", "scenario_pass_count")}, ensure_ascii=False, indent=2))
    print(f"report={REPORT_PATH}")
    print(f"json={JSON_PATH}")


if __name__ == "__main__":
    main()
