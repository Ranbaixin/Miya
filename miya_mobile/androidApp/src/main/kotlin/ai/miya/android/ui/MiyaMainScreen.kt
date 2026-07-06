package ai.miya.android.ui

import ai.miya.shared.ServiceLocator
import ai.miya.shared.connection.ConnectionStatus
import ai.miya.android.ui.chat.ChatDetailScreen
import ai.miya.android.ui.conversation.ConversationListScreen
import ai.miya.android.ui.discover.DiscoverScreen
import ai.miya.android.ui.profile.ProfileScreen
import ai.miya.android.ui.setup.ConnectionSetupScreen
import ai.miya.android.ui.theme.LocalMiyaColors
import androidx.compose.animation.*
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.coroutines.launch

enum class MainTab(val label: String) {
    MESSAGES("消息"),
    DISCOVER("发现"),
    ME("我的"),
}

sealed class AppScreen {
    data object Main : AppScreen()
    data class ChatDetail(val sessionId: String = "default", val sessionName: String = "弥娅") : AppScreen()
}

@Composable
fun MiyaMainScreen() {
    val colors = LocalMiyaColors.current
    val appConfig = remember { ServiceLocator.appConfig }
    val connMgr = remember { ServiceLocator.connectionManager }
    val connState by connMgr.state.collectAsState()
    val scope = rememberCoroutineScope()

    var currentTab by remember { mutableStateOf(MainTab.MESSAGES) }
    var currentScreen by remember { mutableStateOf<AppScreen>(AppScreen.Main) }
    var showSetup by remember { mutableStateOf(false) }

    LaunchedEffect(Unit) {
        val saved = appConfig.load()
        if (saved.serverHost != "localhost" || saved.serverPort != 9800) {
            connMgr.setLanMode(saved.serverHost, saved.serverPort)
        }
        try {
            val health = ServiceLocator.apiClient.health()
            if (health.status != "ok") {
                showSetup = true
            } else {
                connMgr.markConnected()
            }
        } catch (_: Exception) {
            showSetup = true
        }
    }

    if (showSetup) {
        ConnectionSetupScreen(
            onConnected = { host, port ->
                scope.launch {
                    appConfig.saveHost(host)
                    appConfig.savePort(port)
                    ServiceLocator.reconnect(host, port)
                    connMgr.setLanMode(host, port)
                    try {
                        ServiceLocator.apiClient.health()
                        connMgr.markConnected()
                    } catch (_: Exception) {
                        connMgr.markError("连接失败")
                    }
                    showSetup = false
                }
            }
        )
        return
    }

    when (val screen = currentScreen) {
        is AppScreen.Main -> {
            Scaffold(
                modifier = Modifier.fillMaxSize().background(colors.background),
                containerColor = colors.background,
                bottomBar = {
                    HorizontalDivider(thickness = 0.5.dp, color = colors.divider)
                    NavigationBar(
                        containerColor = colors.surface,
                        contentColor = colors.textPrimary,
                        tonalElevation = 0.dp,
                    ) {
                        NavigationBarItem(
                            selected = currentTab == MainTab.MESSAGES,
                            onClick = { currentTab = MainTab.MESSAGES },
                            icon = {
                                Text(
                                    text = "\uD83D\uDCAC",
                                    fontSize = 18.sp,
                                    modifier = Modifier.offset(y = (-2).dp),
                                )
                            },
                            label = {
                                Text(
                                    "消息",
                                    fontSize = 10.sp,
                                    fontWeight = if (currentTab == MainTab.MESSAGES) FontWeight.Bold else FontWeight.Normal,
                                )
                            },
                            colors = NavigationBarItemDefaults.colors(
                                selectedIconColor = colors.primary,
                                selectedTextColor = colors.primary,
                                unselectedIconColor = colors.textSecondary,
                                unselectedTextColor = colors.textSecondary,
                                indicatorColor = colors.primary.copy(alpha = 0.12f),
                            ),
                        )
                        NavigationBarItem(
                            selected = currentTab == MainTab.DISCOVER,
                            onClick = { currentTab = MainTab.DISCOVER },
                            icon = {
                                Text(
                                    text = "\u25C7",
                                    fontSize = 20.sp,
                                    modifier = Modifier.offset(y = (-2).dp),
                                )
                            },
                            label = {
                                Text(
                                    "发现",
                                    fontSize = 10.sp,
                                    fontWeight = if (currentTab == MainTab.DISCOVER) FontWeight.Bold else FontWeight.Normal,
                                )
                            },
                            colors = NavigationBarItemDefaults.colors(
                                selectedIconColor = colors.primary,
                                selectedTextColor = colors.primary,
                                unselectedIconColor = colors.textSecondary,
                                unselectedTextColor = colors.textSecondary,
                                indicatorColor = colors.primary.copy(alpha = 0.12f),
                            ),
                        )
                        NavigationBarItem(
                            selected = currentTab == MainTab.ME,
                            onClick = { currentTab = MainTab.ME },
                            icon = {
                                Text(
                                    text = "\u25CB",
                                    fontSize = 20.sp,
                                    modifier = Modifier.offset(y = (-2).dp),
                                )
                            },
                            label = {
                                Text(
                                    "我的",
                                    fontSize = 10.sp,
                                    fontWeight = if (currentTab == MainTab.ME) FontWeight.Bold else FontWeight.Normal,
                                )
                            },
                            colors = NavigationBarItemDefaults.colors(
                                selectedIconColor = colors.primary,
                                selectedTextColor = colors.primary,
                                unselectedIconColor = colors.textSecondary,
                                unselectedTextColor = colors.textSecondary,
                                indicatorColor = colors.primary.copy(alpha = 0.12f),
                            ),
                        )
                    }
                },
            ) { padding ->
                Box(
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(padding)
                        .background(colors.background)
                ) {
                    when (currentTab) {
                        MainTab.MESSAGES -> ConversationListScreen(
                            onConversationClick = { id, name ->
                                currentScreen = AppScreen.ChatDetail(id, name)
                            }
                        )
                        MainTab.DISCOVER -> DiscoverScreen()
                        MainTab.ME -> ProfileScreen()
                    }
                }
            }
        }
        is AppScreen.ChatDetail -> {
            ChatDetailScreen(
                sessionId = screen.sessionId,
                sessionName = screen.sessionName,
                onBack = { currentScreen = AppScreen.Main },
            )
        }
    }
}
