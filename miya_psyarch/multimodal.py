from __future__ import annotations

_MM_CFG = {}
try:
    import yaml
    from pathlib import Path
    p = Path(__file__).resolve().parent / 'config' / 'miya_config.yaml'
    with open(p, 'r', encoding='utf-8') as f_cfg:
        raw = yaml.safe_load(f_cfg) or {}
    _MM_CFG = raw.get('multimodal', {})
except Exception:
    pass

_MM_LABELS = _MM_CFG.get('labels', {})
"""
弥娅多模态感知系统

支持弥娅「看」图片、「听」音频——所有感知结果进入 AP 状态池，参与认知闭环。

图片：PIL 分析（颜色、亮度、复杂度）+ LLM 描述
音频：wave 分析（振幅、频谱、时长）+ LLM 转写
"""



import io
import logging
import math
import struct
import wave
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("miya_psyarch.multimodal")


# ── 视觉感知 ──


@dataclass
class VisualPerception:
    """图片分析结果"""

    width: int = 0
    height: int = 0
    aspect_ratio: float = 1.0
    dominant_colors: list[tuple[int, int, int]] = field(default_factory=list)
    avg_brightness: float = 0.5
    contrast: float = 0.0
    complexity: float = 0.0
    has_text: bool = False
    llm_description: str = ""
    raw_bytes: bytes | None = None


def perceive_image(image_bytes: bytes, *, thumbnail_size: int = 128) -> VisualPerception:
    """用 PIL 分析图片"""
    try:
        from PIL import Image, ImageStat
    except ImportError:
        return VisualPerception(llm_description="[PIL not available]")

    result = VisualPerception()
    result.raw_bytes = image_bytes

    try:
        img = Image.open(io.BytesIO(image_bytes))
        result.width, result.height = img.size
        result.aspect_ratio = result.width / max(result.height, 1)

        # 缩略图用于快速分析
        thumb = img.convert("RGB").resize((thumbnail_size, thumbnail_size), Image.LANCZOS)
        pixels = list(thumb.getdata())

        # 亮度
        result.avg_brightness = sum(r + g + b for r, g, b in pixels) / (len(pixels) * 3 * 255)

        # 主导颜色（简单像素聚类）
        color_counts: dict[tuple[int, int, int], int] = {}
        for r, g, b in pixels:
            key = (r // 32 * 32, g // 32 * 32, b // 32 * 32)
            color_counts[key] = color_counts.get(key, 0) + 1
        result.dominant_colors = sorted(color_counts, key=color_counts.get, reverse=True)[:5]

        # 对比度（相邻像素亮度差）
        diffs = []
        for i in range(len(pixels) - 1):
            b1 = sum(pixels[i]) / 3
            b2 = sum(pixels[i + 1]) / 3
            diffs.append(abs(b1 - b2) / 255)
        result.contrast = sum(diffs) / max(len(diffs), 1)

        # 复杂度（色彩熵）
        probs = [c / len(pixels) for c in color_counts.values()]
        entropy = -sum(p * math.log2(max(p, 1e-9)) for p in probs)
        result.complexity = min(1.0, entropy / 8.0)

        img.close()
    except Exception as e:
        logger.warning(f"Image analysis failed: {e}")

    return result


def describe_image_with_llm(perception: VisualPerception, llm_render) -> str:
    """用 LLM 生成图片描述（需要 cortex）"""
    features = []
    if perception.avg_brightness < 0.3:
        features.append("画面偏暗")
    elif perception.avg_brightness > 0.7:
        features.append("画面明亮")
    features.append(f"尺寸 {perception.width}x{perception.height}")
    if perception.contrast > 0.3:
        features.append("高对比度")
    features.append(f"色彩复杂度: {'高' if perception.complexity > 0.4 else '低'}")
    if perception.dominant_colors:
        color_desc = ", ".join(f"rgb({r},{g},{b})" for r, g, b in perception.dominant_colors[:3])
        features.append(f"主要颜色: {color_desc}")

    return ", ".join(features)


def image_to_state_items(perception: VisualPerception, base_energy: float = 1.2) -> list[dict]:
    """将视觉感知转换为 AP 状态池项"""
    items = []
    # 基本属性
    items.append(
        {
            "sa_label": "vision::image_present",
            "display_text": _MM_LABELS.get("image_present", "图片 {w}x{h}").replace("{w}", str(perception.width)).replace("{h}", str(perception.height)),
            "family": "vision",
            "source_type": "multimodal_vision",
            "real_energy": base_energy,
            "anchor_meta": {
                "channel": "vision",
                "width": perception.width,
                "height": perception.height,
            },
        }
    )
    # 亮度
    if perception.avg_brightness < 0.3:
        items.append(
            {
                "sa_label": "vision::dark",
                "display_text": _MM_LABELS.get("dark", "暗色调"),
                "family": "vision",
                "source_type": "multimodal_vision",
                "real_energy": 0.8,
            }
        )
    elif perception.avg_brightness > 0.7:
        items.append(
            {
                "sa_label": "vision::bright",
                "display_text": _MM_LABELS.get("bright", "明亮"),
                "family": "vision",
                "source_type": "multimodal_vision",
                "real_energy": 0.8,
            }
        )
    # 对比度
    if perception.contrast > 0.3:
        items.append(
            {
                "sa_label": "vision::high_contrast",
                "display_text": _MM_LABELS.get("high_contrast", "高对比"),
                "family": "vision",
                "source_type": "multimodal_vision",
                "real_energy": 0.7,
            }
        )
    return items


# ── 听觉感知 ──


@dataclass
class AudioPerception:
    """音频分析结果"""

    duration_ms: float = 0.0
    sample_rate: int = 0
    channels: int = 1
    max_amplitude: float = 0.0
    avg_amplitude: float = 0.0
    dominant_freq: float = 0.0
    has_voice: bool = False
    llm_transcript: str = ""
    waveform_preview: list[float] = field(default_factory=list)


def perceive_audio(audio_bytes: bytes) -> AudioPerception:
    """分析 WAV 音频"""
    result = AudioPerception()

    try:
        with wave.open(io.BytesIO(audio_bytes), "rb") as wf:
            result.sample_rate = wf.getframerate()
            result.channels = wf.getnchannels()
            n_frames = wf.getnframes()
            n_channels = result.channels
            result.duration_ms = (n_frames / max(result.sample_rate, 1)) * 1000

            frames = wf.readframes(min(n_frames, result.sample_rate * 30))
    except Exception as e:
        logger.warning(f"Audio decode failed: {e}")
        return result

    if not frames:
        return result

    # 解码
    try:
        fmt = f"<{len(frames) // 2}h"
        raw = list(struct.unpack(fmt, frames[: len(frames) // 2 * 2]))
        samples = raw if n_channels == 1 else [raw[i] for i in range(0, len(raw), n_channels)]
    except Exception as e:
        logger.warning(f"Audio sample decode failed: {e}")
        return result

    if not samples:
        return result

    # 振幅
    abs_samples = [abs(s) for s in samples]
    result.max_amplitude = max(abs_samples) / 32768.0
    result.avg_amplitude = sum(abs_samples) / (len(abs_samples) * 32768.0)

    # 粗略频谱（简单自相关估算主导频率）
    if len(samples) > 1000:
        chunk = samples[:1000]
        result.dominant_freq = _rough_dominant_freq(chunk, result.sample_rate)

    # 波形预览
    step = max(1, len(samples) // 64)
    preview = []
    for i in range(0, min(len(samples), step * 64), step):
        chunk = samples[i : min(i + step, len(samples))]
        if chunk:
            preview.append(round(max(abs(s) for s in chunk) / 32768.0, 3))
    result.waveform_preview = preview[:64]

    # 简单判断是否有人声（频谱集中在人声范围内）
    result.has_voice = (
        result.avg_amplitude > 0.01
        and result.dominant_freq > 80
        and result.dominant_freq < 3000
        and result.duration_ms > 500
    )

    return result


def _rough_dominant_freq(samples: list[int], sample_rate: int) -> float:
    """简单自相关法估算主导频率"""
    n = len(samples)
    if n < 100:
        return 0.0
    # 检测过零点
    zero_crossings = 0
    for i in range(1, n):
        if (samples[i] >= 0) != (samples[i - 1] >= 0):
            zero_crossings += 1
    return (zero_crossings * sample_rate) / (2 * max(n, 1))


def audio_to_state_items(perception: AudioPerception, base_energy: float = 1.0) -> list[dict]:
    """将听觉感知转换为 AP 状态池项"""
    items = []
    items.append(
        {
            "sa_label": "audio::audio_present",
            "display_text": f"音频 {perception.duration_ms:.0f}ms",
            "family": "audio",
            "source_type": "multimodal_audio",
            "real_energy": base_energy,
            "anchor_meta": {
                "channel": "audio",
                "duration_ms": perception.duration_ms,
                "sample_rate": perception.sample_rate,
            },
        }
    )
    if perception.has_voice:
        items.append(
            {
                "sa_label": "audio::voice_detected",
                "display_text": _MM_LABELS.get("voice", "语音"),
                "family": "audio",
                "source_type": "multimodal_audio",
                "real_energy": 1.2,
            }
        )
    if perception.max_amplitude > 0.5:
        items.append(
            {
                "sa_label": "audio::loud",
                "display_text": _MM_LABELS.get("loud", "大声"),
                "family": "audio",
                "source_type": "multimodal_audio",
                "real_energy": 0.8,
            }
        )
    return items


# ── 多模态上下文 ──


@dataclass
class MultiModalContext:
    """当前 tick 的多模态上下文——同时传给 AP 和 LLM"""

    image: VisualPerception | None = None
    audio: AudioPerception | None = None
    image_description: str = ""
    audio_description: str = ""

    def to_llm_context(self) -> str:
        parts = []
        if self.image and self.image.llm_description:
            parts.append(f"[图片描述] {self.image.llm_description}")
        elif self.image:
            parts.append(
                f"[图片] {self.image.width}x{self.image.height}, "
                f"亮度{'高' if self.image.avg_brightness > 0.6 else '低'}, "
                f"复杂度{'高' if self.image.complexity > 0.4 else '低'}"
            )
        if self.audio:
            if self.audio.llm_transcript:
                parts.append(f"[语音转写] {self.audio.llm_transcript}")
            if self.audio.has_voice:
                parts.append(f"[语音] 时长{self.audio.duration_ms:.0f}ms, 检测到人声")
            elif self.audio.duration_ms > 0:
                parts.append(f"[声音] 时长{self.audio.duration_ms:.0f}ms")
        return "\n".join(parts)

    def has_multimodal(self) -> bool:
        return self.image is not None or self.audio is not None

    def to_state_items(self) -> list[dict]:
        items = []
        if self.image:
            items.extend(image_to_state_items(self.image))
        if self.audio:
            items.extend(audio_to_state_items(self.audio))
        return items
