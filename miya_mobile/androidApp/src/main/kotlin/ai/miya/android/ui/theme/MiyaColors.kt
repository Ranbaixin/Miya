package ai.miya.android.ui.theme

import androidx.compose.runtime.staticCompositionLocalOf
import androidx.compose.ui.graphics.Color

data class MiyaColorScheme(
    val background: Color,
    val surface: Color,
    val surfaceVariant: Color,
    val surfaceDeep: Color,
    val primary: Color,
    val primaryDim: Color,
    val accent: Color,
    val accentGlow: Color,
    val textPrimary: Color,
    val textSecondary: Color,
    val textDim: Color,
    val border: Color,
    val borderDim: Color,
    val divider: Color,
    val bubbleMe: Color,
    val bubbleMiya: Color,
    val danger: Color,
    val success: Color,
    val warning: Color,
)

val DarkMiyaColors = MiyaColorScheme(
    background = Color(0xFF1A1D23),
    surface = Color(0xFF252830),
    surfaceVariant = Color(0xFF2E323A),
    surfaceDeep = Color(0xFF15171D),
    primary = Color(0xFF00ADB5),
    primaryDim = Color(0xFF007B82),
    accent = Color(0xFF00FFF5),
    accentGlow = Color(0x3300FFF5),
    textPrimary = Color(0xFFE4ECF0),
    textSecondary = Color(0xFF8899A6),
    textDim = Color(0xFF555D68),
    border = Color(0xFF2E323A),
    borderDim = Color(0xFF22262D),
    divider = Color(0xFF1E2228),
    bubbleMe = Color(0xFF00ADB5),
    bubbleMiya = Color(0xFF252830),
    danger = Color(0xFFEF4444),
    success = Color(0xFF22C55E),
    warning = Color(0xFFF59E0B),
)

val LightMiyaColors = MiyaColorScheme(
    background = Color(0xFFF0F2F5),
    surface = Color(0xFFFFFFFF),
    surfaceVariant = Color(0xFFF7F8FA),
    surfaceDeep = Color(0xFFEBEDF0),
    primary = Color(0xFF00838F),
    primaryDim = Color(0xFF006064),
    accent = Color(0xFF00ACC1),
    accentGlow = Color(0x1A00ACC1),
    textPrimary = Color(0xFF1A1D23),
    textSecondary = Color(0xFF6B7280),
    textDim = Color(0xFF9CA3AF),
    border = Color(0xFFE5E7EB),
    borderDim = Color(0xFFD1D5DB),
    divider = Color(0xFFE5E7EB),
    bubbleMe = Color(0xFF00838F),
    bubbleMiya = Color(0xFFFFFFFF),
    danger = Color(0xFFDC2626),
    success = Color(0xFF16A34A),
    warning = Color(0xFFD97706),
)

val LocalMiyaColors = staticCompositionLocalOf { DarkMiyaColors }
