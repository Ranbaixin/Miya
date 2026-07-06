package ai.miya.android.ui.theme

import ai.miya.shared.ServiceLocator
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.graphics.Color

private val DarkColorScheme = darkColorScheme(
    primary = DarkMiyaColors.primary,
    secondary = DarkMiyaColors.accent,
    background = DarkMiyaColors.background,
    surface = DarkMiyaColors.surface,
    surfaceVariant = DarkMiyaColors.surfaceVariant,
    onPrimary = Color.White,
    onSecondary = Color.Black,
    onBackground = DarkMiyaColors.textPrimary,
    onSurface = DarkMiyaColors.textPrimary,
    onSurfaceVariant = DarkMiyaColors.textSecondary,
    outline = DarkMiyaColors.border,
    error = DarkMiyaColors.danger,
)

private val LightColorScheme = lightColorScheme(
    primary = LightMiyaColors.primary,
    secondary = LightMiyaColors.accent,
    background = LightMiyaColors.background,
    surface = LightMiyaColors.surface,
    surfaceVariant = LightMiyaColors.surfaceVariant,
    onPrimary = Color.White,
    onSecondary = Color.Black,
    onBackground = LightMiyaColors.textPrimary,
    onSurface = LightMiyaColors.textPrimary,
    onSurfaceVariant = LightMiyaColors.textSecondary,
    outline = LightMiyaColors.border,
    error = LightMiyaColors.danger,
)

@Composable
fun MiyaTheme(
    content: @Composable () -> Unit,
) {
    val appConfig = remember { ServiceLocator.appConfig }
    var isDark by remember { mutableStateOf(appConfig.isDarkTheme) }
    val systemDark = isSystemInDarkTheme()

    val actualDark = isDark

    val colorScheme = if (actualDark) DarkColorScheme else LightColorScheme
    val miyaColors = if (actualDark) DarkMiyaColors else LightMiyaColors

    CompositionLocalProvider(
        LocalMiyaColors provides miyaColors,
    ) {
        MaterialTheme(
            colorScheme = colorScheme,
            typography = Typography(),
            content = content,
        )
    }
}
