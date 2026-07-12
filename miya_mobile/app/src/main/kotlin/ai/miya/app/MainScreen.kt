package ai.miya.app

import ai.miya.feature.chat.ChatScreen
import ai.miya.feature.chat.SessionListScreen
import ai.miya.feature.files.FilesScreen
import ai.miya.feature.settings.SettingsScreen
import ai.miya.uicommon.component.MiyaBackground
import ai.miya.uicommon.theme.*
import androidx.compose.animation.*
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

@Composable
fun MainScreen() {
    var selectedTab by remember { mutableIntStateOf(0) }
    var showSettings by remember { mutableStateOf(false) }

    // Chat tab internal navigation
    var activeSessionId by remember { mutableStateOf<String?>(null) }

    val theme by collectAsState()
    val bgUri by backgroundUri.collectAsState()

    MiyaTheme {
        Box(modifier = Modifier.fillMaxSize()) {
            MiyaBackground(
                accentColor = theme.primary,
                backgroundUri = bgUri,
            )

            Scaffold(
                containerColor = Color.Transparent,
                contentColor = theme.onSurface,
                bottomBar = {
                    // 聊天详情页隐藏底部菜单
                    if (activeSessionId == null) {
                    Surface(
                        color = Color(0xFF1A111A).copy(alpha = 0.92f),
                        shadowElevation = 8.dp,
                    ) {
                        Row(
                            Modifier.fillMaxWidth().navigationBarsPadding().padding(vertical = 6.dp),
                            horizontalArrangement = Arrangement.SpaceEvenly,
                        ) {
                            TabItem(
                                selected = selectedTab == 0,
                                onClick = { selectedTab = 0; activeSessionId = null },
                                icon = { Icon(Icons.Default.QuestionAnswer, null, modifier = Modifier.size(24.dp)) },
                                label = "聊天",
                            )
                            TabItem(
                                selected = selectedTab == 1,
                                onClick = { selectedTab = 1 },
                                icon = { Icon(Icons.Default.Folder, null, modifier = Modifier.size(24.dp)) },
                                label = "文件",
                            )
                        }
                    }
                    } // end if activeSessionId == null
                },
            ) { innerPadding ->
                Box(Modifier.padding(innerPadding)) {
                    when (selectedTab) {
                        0 -> {
                            if (activeSessionId != null) {
                                ChatScreen(
                                    sessionId = activeSessionId!!,
                                    onBack = { activeSessionId = null },
                                )
                            } else {
                                SessionListScreen(
                                    onEnterSession = { sessionId -> activeSessionId = sessionId },
                                )
                            }
                        }
                        1 -> FilesScreen()
                    }
                }
            }

            // Settings gear
            if (!showSettings) {
                Box(
                    modifier = Modifier
                        .align(Alignment.TopEnd)
                        .statusBarsPadding()
                        .padding(top = 4.dp, end = 8.dp)
                        .size(36.dp)
                        .clip(CircleShape)
                        .background(Color.White.copy(alpha = 0.06f))
                        .clickable { showSettings = true },
                    contentAlignment = Alignment.Center,
                ) {
                    Icon(
                        Icons.Default.Settings,
                        contentDescription = "设置",
                        tint = Color.White.copy(alpha = 0.4f),
                        modifier = Modifier.size(18.dp),
                    )
                }
            }

            // Settings overlay
            AnimatedVisibility(
                visible = showSettings,
                enter = fadeIn(tween(200)) + slideInVertically(tween(250)) { it },
                exit = fadeOut(tween(150)) + slideOutVertically(tween(200)) { it },
            ) {
                Box(modifier = Modifier.fillMaxSize().background(Color(0xFF1A111A))) {
                    SettingsScreen(onBack = { showSettings = false })
                }
            }
        }
    }
}

@Composable
private fun TabItem(
    selected: Boolean,
    onClick: () -> Unit,
    icon: @Composable () -> Unit,
    label: String,
) {
    val color by animateColorAsState(
        if (selected) MiyaColors.Primary else Color.White.copy(alpha = 0.4f),
        tween(200),
    )

    Column(
        Modifier.clickable(onClick = onClick).padding(horizontal = 24.dp, vertical = 4.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        icon()
        Spacer(Modifier.height(2.dp))
        CompositionLocalProvider(LocalContentColor provides color) {
            Text(label, fontSize = 10.sp, fontWeight = if (selected) FontWeight.Bold else FontWeight.Normal)
        }
    }
}
