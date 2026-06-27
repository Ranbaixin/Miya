package ai.miya.android.ui

import androidx.compose.animation.*
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material.icons.outlined.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.unit.dp
import ai.miya.android.ui.chat.ChatScreen
import ai.miya.android.ui.hub.HubScreen
import ai.miya.android.ui.memory.MemoryScreen
import ai.miya.android.ui.settings.SettingsScreen
import ai.miya.android.ui.theme.*
import ai.miya.shared.ServiceLocator

enum class MiyaTab(
    val label: String,
    val selectedIcon: ImageVector,
    val unselectedIcon: ImageVector,
) {
    CHAT("聊天", Icons.Filled.Chat, Icons.Outlined.Chat),
    HUB("中枢", Icons.Filled.Hub, Icons.Outlined.Hub),
    MEMORY("记忆", Icons.Filled.Memory, Icons.Outlined.Memory),
    SETTINGS("设置", Icons.Filled.Settings, Icons.Outlined.Settings),
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MiyaMainScreen() {
    var selectedTab by remember { mutableStateOf(MiyaTab.CHAT) }

    MaterialTheme(
        colorScheme = darkColorScheme(
            primary = MiyaPrimary,
            secondary = MiyaSecondary,
            background = MiyaBackground,
            surface = MiyaSurface,
            surfaceVariant = MiyaSurfaceVariant,
            onPrimary = MiyaTextPrimary,
            onSecondary = MiyaTextPrimary,
            onBackground = MiyaTextPrimary,
            onSurface = MiyaTextPrimary,
            onSurfaceVariant = MiyaTextSecondary,
        )
    ) {
        Scaffold(
            modifier = Modifier.fillMaxSize(),
            bottomBar = {
                MiyaBottomBar(
                    selectedTab = selectedTab,
                    onTabSelected = { selectedTab = it }
                )
            },
            containerColor = MiyaBackground,
        ) { padding ->
            Box(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(padding)
            ) {
                when (selectedTab) {
                    MiyaTab.CHAT -> ChatScreen()
                    MiyaTab.HUB -> HubScreen()
                    MiyaTab.MEMORY -> MemoryScreen()
                    MiyaTab.SETTINGS -> SettingsScreen()
                }
            }
        }
    }
}

@Composable
private fun MiyaBottomBar(
    selectedTab: MiyaTab,
    onTabSelected: (MiyaTab) -> Unit,
) {
    NavigationBar(
        containerColor = MiyaSurface,
        contentColor = MiyaTextPrimary,
        tonalElevation = 0.dp,
    ) {
        MiyaTab.entries.forEach { tab ->
            NavigationBarItem(
                selected = selectedTab == tab,
                onClick = { onTabSelected(tab) },
                icon = {
                    Icon(
                        imageVector = if (selectedTab == tab) tab.selectedIcon else tab.unselectedIcon,
                        contentDescription = tab.label
                    )
                },
                label = { Text(tab.label) },
                colors = NavigationBarItemDefaults.colors(
                    selectedIconColor = MiyaPrimary,
                    selectedTextColor = MiyaPrimary,
                    unselectedIconColor = MiyaTextSecondary,
                    unselectedTextColor = MiyaTextSecondary,
                    indicatorColor = MiyaSurfaceVariant,
                )
            )
        }
    }
}
