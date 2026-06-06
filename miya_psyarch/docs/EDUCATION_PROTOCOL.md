# APV2.1 Education Protocol

This document explains how APV2.1 teaches skills without turning the AP core into a hard-coded rule engine.

## Core Boundary

The education system is outside AP core.

The teacher may provide:

- ordinary state-field materials,
- soft action drive bias,
- reward / punishment / correctness feedback,
- and optional parameterized action hints during scaffold phases.

The teacher must not:

- directly execute AP actions,
- directly rewrite AP memory as a hidden answer table,
- inject final answers during teacher-off tests,
- bypass AP state-field competition,
- or hide domain-specific solvers inside the runtime.

The AP runtime remains responsible for cognition, action competition, action execution, feedback digestion, and memory formation.

## Packet Shape

The generic packet is `education_intervention/v1`:

```json
{
  "schema_id": "education_intervention/v1",
  "source": "external_teacher",
  "teacher_kind": "human_or_llm_or_fake_teacher",
  "goal": "teach a reusable skill brick",
  "tick_index": 12,
  "state_items": [],
  "action_biases": [],
  "feedback": {},
  "notes": ["external_education_intervention"]
}
```

### State Items

A state item is not an order. It is material added to the same state field as perception, action feedback, cognitive feeling, and memory evidence.

```json
{
  "sa_label": "education_hint::reread_before_commit",
  "display_text": "reread before commit",
  "family": "education_intervention",
  "source_type": "external_teacher",
  "real_energy": 0.18,
  "cognitive_pressure": 0.06,
  "anchor_meta": {
    "schema_id": "education_state_item/v1",
    "meaning": "external_teacher_hint_first_class_state_item"
  }
}
```

### Action Biases

An action bias is a soft drive delta. AP may accept it, ignore it, or let another action outcompete it.

```json
{
  "schema_id": "education_action_bias/v1",
  "action_id": "text_editor::reread_current_draft",
  "drive_delta": 0.22,
  "params": {
    "focus": "current_text_box"
  },
  "notes": [
    "education_intervention_bias",
    "soft_drive_bias_only"
  ]
}
```

Parameterized actions are first-class. The parameter is not an invisible argument; it becomes part of the action trace and can later participate in recall and consequence evaluation.

### Feedback

Feedback is post-action evidence. It can reward or punish an outcome, but it should not carry the final answer in teacher-off or feedback-only tests.

```json
{
  "schema_id": "education_feedback/v1",
  "reward": 0.8,
  "punishment": 0.0,
  "correctness": 1.0,
  "confidence": 0.95,
  "source": "education::teacher",
  "notes": ["correct process, good reread before commit"]
}
```

For an incorrect math answer, APV2.1 feedback can punish the submitted outcome without passing the answer:

```json
{
  "schema_id": "education_feedback/v1",
  "reward": 0.0,
  "punishment": 0.7,
  "correctness": 0.0,
  "confidence": 1.0,
  "source": "education::math_judge",
  "notes": ["submitted result failed reverse check"],
  "answer_payload": null
}
```

## Scaffold Phases

The standard fade schedule is:

```text
demonstrate
-> strong_scaffold
-> weak_scaffold
-> feedback_only
-> teacher_off
-> cold_retest
```

`education/skill_protocol_v2.py` normalizes this schedule.

### Demonstrate

The teacher may provide state items, soft action bias, and feedback. This is like showing a child how a skill looks.

Example:

```json
{
  "phase_id": "demonstrate",
  "teacher_signal": {
    "state_items": true,
    "action_biases": true,
    "feedback": true
  },
  "strength": 1.0
}
```

### Strong Scaffold

The teacher still helps, but AP action competition matters.

### Weak Scaffold

Teacher hints fade. AP's learned process traces, cognitive feelings, and action consequences matter more.

### Feedback Only

The teacher gives no state hints and no action hints. It only rewards or punishes outcomes.

### Teacher Off

The teacher emits nothing:

```json
{
  "state_items": [],
  "action_biases": [],
  "feedback": {}
}
```

AP must rely on its own state field, short-term memory, learned feedback, and action consequence traces.

### Cold Retest

Teacher remains off under a fresh or partially reset context. This tests retention rather than one-episode echo.

## Building Blocks

The teacher should teach enough reusable bricks before testing unseen combinations.

For multimodal language:

- color visual state: red, yellow;
- object visual state: apple, banana;
- text/audio association: "red", "yellow", "apple", "banana";
- sentence order: color before object in the target language;
- commit/revision behavior: draft, reread, fix, submit.

Then an unseen prompt such as a yellow apple should not be solved by an answer table. It should be assembled from learned color, object, text, order, and revision bricks.

For arithmetic:

- digit and quantity,
- sequence,
- addition/subtraction within ten,
- carry and borrow,
- place value,
- vertical layout,
- partial products,
- multiplication table bricks,
- quotient trial,
- multiply-back,
- subtract,
- remainder boundary,
- reverse check,
- reread and revise before commit.

Then larger vertical arithmetic can be tested by combining learned bricks.

## LLM Teacher Role

An LLM teacher can be used later as a flexible external teacher. It should output protocol packets and feedback, not modify AP internals.

The teacher prompt should explain:

- AP begins like a child with limited learned bricks;
- the teacher must teach reusable bricks, not magic final answers;
- scaffolding should fade;
- feedback-only and teacher-off phases must not pass hidden answers;
- all action parameters must be explicit and auditable;
- uncertainty should be rewarded when evidence is insufficient.

## Why This Supports Generalization

Generalization does not come from one special hidden module. It comes from many reusable state-field materials interacting:

- current sensory evidence,
- remembered examples,
- action traces,
- cognitive feelings such as mismatch, evidence gap, closure, calculation pressure, and visual confirmation,
- reward/punishment history,
- temporal applicability weighting,
- and short-term task recovery.

When AP sees a new case, it can recall similar process traces through these shared hidden variables. A new yellow apple is not exactly the same as red apple or yellow banana, but it shares color/object/text/order materials. A new division problem is not in an answer table, but it shares bring-down, trial, multiply-back, subtract, boundary, reverse-check, and revision materials.

That is the APV2.1 teaching philosophy: teach enough bricks, then let the AP runtime compete, assemble, revise, and retain.

