package ai.miya.uicommon.theme

import android.net.Uri
import androidx.compose.runtime.*
import androidx.compose.ui.graphics.Color
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

data class MiyaThemeConfig(
    val primary: Color = WarmAnime.Primary,
    val primaryLight: Color = WarmAnime.PrimaryLight,
    val secondary: Color = WarmAnime.Secondary,
    val secondaryLight: Color = WarmAnime.SecondaryLight,
    val glassBg: Color = WarmAnime.GlassBg,
    val glassBgStrong: Color = WarmAnime.GlassBgStrong,
    val glassBorder: Color = WarmAnime.GlassBorder,
    val background: Color = WarmAnime.Background,
    val onSurface: Color = WarmAnime.OnSurface,
    val onSurfaceVariant: Color = WarmAnime.OnSurfaceVariant,
)

object WarmAnime {
    val Primary = Color(0xFFFF8BA7)
    val PrimaryLight = Color(0xFFFFB3C6)
    val Secondary = Color(0xFFD4A5FF)
    val SecondaryLight = Color(0xFFE8D0FF)
    val Background = Color(0xFF1A111A)
    val GlassBg = Color(0x4D2D222D)
    val GlassBgStrong = Color(0x80332233)
    val GlassBorder = Color(0x26FF8BA7)
    val OnSurface = Color(0xFFF0E6EE)
    val OnSurfaceVariant = Color(0xCCD4C5D2)
}

val LocalMiyaTheme = staticCompositionLocalOf { MiyaThemeConfig() }

private val _activeTheme = MutableStateFlow(MiyaThemeConfig())
val activeTheme: StateFlow<MiyaThemeConfig> = _activeTheme.asStateFlow()

fun updateTheme(config: MiyaThemeConfig) {
    _activeTheme.value = config
}

fun updatePrimaryColor(color: Color) {
    _activeTheme.value = _activeTheme.value.copy(
        primary = color,
        primaryLight = color.copy(alpha = 0.7f),
        glassBorder = color.copy(alpha = 0.15f),
    )
}

private val _backgroundUri = MutableStateFlow<Uri?>(null)
val backgroundUri: StateFlow<Uri?> = _backgroundUri.asStateFlow()

fun updateBackgroundUri(uri: Uri?) {
    _backgroundUri.value = uri
}

// Legacy static references (for non-Compose code or quick access)
object MiyaColors {
    val Primary get() = _activeTheme.value.primary
    val PrimaryLight get() = _activeTheme.value.primaryLight
    val Secondary get() = _activeTheme.value.secondary
    val SecondaryLight get() = _activeTheme.value.secondaryLight
    val Background get() = _activeTheme.value.background
    val SurfaceGlass get() = _activeTheme.value.glassBg
    val SurfaceGlassStrong get() = _activeTheme.value.glassBgStrong
    val GlassBorder get() = _activeTheme.value.glassBorder
    val OnSurface get() = _activeTheme.value.onSurface
    val OnSurfaceVariant get() = _activeTheme.value.onSurfaceVariant

    val Online = Color(0xFF81C784)
    val Offline = Color(0xFF666666)
    val Error = Color(0xFFFF6B6B)
    val Warning = Color(0xFFFFB74D)
    val Happy = Color(0xFFFFD54F)
    val Sad = Color(0xFF90CAF9)
    val Angry = Color(0xFFEF5350)
    val Calm = Color(0xFFA5D6A7)
    val Surprise = Color(0xFFFFAB91)
    val Trust = Color(0xFFCE93D8)
    val Anticipation = Color(0xFFFFCC80)
}
