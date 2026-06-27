package ai.miya.android.ui.theme

import androidx.compose.ui.graphics.Color

// ═══════════════════════════════════════════════
// 弥娅 PGR 战双帕米什风格配色 (与前端统一)
// 主调: 青蓝 Teal-Cyan / 暗海灰背景
// ═══════════════════════════════════════════════

// ── 核心背景与表面 ──
val MiyaBackground = Color(0xFF222831)
val MiyaSurface = Color(0xB8393E46)     // rgba(57,62,70,0.72)
val MiyaSurfaceVariant = Color(0xD9393E46) // rgba(57,62,70,0.85)
val MiyaSurfaceDeep = Color(0xEB08101C)   // rgba(8,16,28,0.92) .box

// ── 主色 / 强调色 ──
val MiyaPrimary = Color(0xFF00ADB5)       // Teal 青绿 (--miya-accent)
val MiyaAccent = Color(0xFF00FFF5)        // Cyan 亮青 (--miya-chat-ai)
val MiyaGlow = Color(0x4D00ADB5)          // 发光 (30% primary)
val MiyaGold = Color(0x5900FFF5)           // 高光 (35% accent)

// ── 文本 ──
val MiyaTextPrimary = Color(0xFFE4ECF0)
val MiyaTextSecondary = Color(0x73E4ECF0)  // rgba(228,236,240,0.45)
val MiyaTextDim = Color(0x66E4ECF0)        // 更暗淡

// ── 边框 ──
val MiyaBorder = Color(0xFF00ADB5)         // 发光边框色
val MiyaBorderDim = Color(0x3300ADB5)      // 暗淡边框 (20%)

// ── 聊天气泡 ──
val MiyaChatAI = Color(0xFF00FFF5)          // AI 消息色
val MiyaChatUser = Color(0xFF00ADB5)        // 用户消息色
val MiyaChatBg = Color(0xFF222831)         // 聊天区背景
val MiyaChatBubble = Color(0xCC1A202B)     // 半透明气泡底

// ── 覆盖层 ──
val MiyaOverlay = Color(0x80000000)

// ═══════════════════════════════════════════════
// 弥娅 17 情绪色彩 (与前端 emotionColors.ts 一致)
// ═══════════════════════════════════════════════

object MiyaEmotionColors {
    val joy = Color(0xFFFFD700)            // 喜悦 - 金色
    val sadness = Color(0xFF7DD3FC)        // 忧伤 - 浅天蓝
    val anger = Color(0xFFEF4444)          // 愤怒 - 红色
    val fear = Color(0xFFB44DFF)           // 恐惧 - 紫色
    val love = Color(0xFFFF6B9D)           // 爱 - 粉色
    val surprise = Color(0xFFFBBF24)       // 惊喜 - 琥珀
    val neutral = Color(0xFF94A3B8)        // 中性 - 石板灰
    val warm = Color(0xFFFF8C69)           // 温暖 - 三文鱼
    val calm = Color(0xFF67E8F9)           // 安心 - 淡青蓝
    val sweet = Color(0xFFF472B6)          // 甜蜜 - 玫瑰粉
    val nostalgic = Color(0xFFD8B4FE)      // 怀旧 - 淡紫
    val shy = Color(0xFFFBCFE8)            // 害羞 - 浅粉
    val anticipation = Color(0xFFFACC15)   // 期待 - 金丝雀黄
    val attachment = Color(0xFFC084FC)     // 依恋 - 紫萝兰
    val moved = Color(0xFFC4B5FD)          // 感动 - 薰衣草
    val tender = Color(0xFFA5B4FC)         // 温柔 - 柔和蓝紫
    val curious = Color(0xFF67E8F9)         // 好奇 - 淡青
}

// ── 向后兼容别名 ──
val MiyaSecondary = MiyaPrimary
val MiyaChatBubbleLegacy = MiyaChatBubble
val MiyaEmotionHappy = MiyaEmotionColors.joy
val MiyaEmotionSad = MiyaEmotionColors.sadness
val MiyaEmotionAngry = MiyaEmotionColors.anger
val MiyaEmotionSurprise = MiyaEmotionColors.surprise

fun emotionColor(name: String): Color = when (name.lowercase()) {
    "joy", "happy" -> MiyaEmotionColors.joy
    "sadness", "sad" -> MiyaEmotionColors.sadness
    "anger", "angry" -> MiyaEmotionColors.anger
    "fear" -> MiyaEmotionColors.fear
    "love" -> MiyaEmotionColors.love
    "surprise" -> MiyaEmotionColors.surprise
    "neutral" -> MiyaEmotionColors.neutral
    "warm" -> MiyaEmotionColors.warm
    "calm" -> MiyaEmotionColors.calm
    "sweet" -> MiyaEmotionColors.sweet
    "nostalgic" -> MiyaEmotionColors.nostalgic
    "shy" -> MiyaEmotionColors.shy
    "anticipation" -> MiyaEmotionColors.anticipation
    "attachment" -> MiyaEmotionColors.attachment
    "moved" -> MiyaEmotionColors.moved
    "tender" -> MiyaEmotionColors.tender
    "curious" -> MiyaEmotionColors.curious
    else -> MiyaPrimary
}
