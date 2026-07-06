package ai.miya.android.ui.profile

import ai.miya.shared.ServiceLocator
import ai.miya.shared.connection.ConnectionStatus
import ai.miya.shared.model.Persona
import ai.miya.android.ui.theme.LocalMiyaColors
import androidx.compose.animation.*
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.coroutines.launch

@Composable
fun ProfileScreen() {
    val colors = LocalMiyaColors.current
    val scope = rememberCoroutineScope()
    val appConfig = remember { ServiceLocator.appConfig }
    val personaRepo = remember { ServiceLocator.personaRepo }
    val connMgr = remember { ServiceLocator.connectionManager }
    val connState by connMgr.state.collectAsState()

    var personas by remember { mutableStateOf<List<Persona>>(emptyList()) }
    var currentPersonaId by remember { mutableStateOf<String?>(null) }
    var isDarkTheme by remember { mutableStateOf(appConfig.isDarkTheme) }
    var showPersonaSheet by remember { mutableStateOf(false) }
    var showConnectionEdit by remember { mutableStateOf(false) }
    var editHost by remember { mutableStateOf(appConfig.load().serverHost) }
    var editPort by remember { mutableStateOf(appConfig.load().serverPort.toString()) }

    LaunchedEffect(Unit) {
        try {
            personas = personaRepo.getList()
            val current = personaRepo.getCurrent()
            currentPersonaId = current.id ?: current.current
        } catch (_: Exception) { }
    }

    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .background(colors.background)
            .statusBarsPadding(),
    ) {
        // 头像 + 用户信息
        item {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 20.dp, vertical = 20.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Box(
                    modifier = Modifier
                        .size(72.dp)
                        .clip(CircleShape)
                        .background(colors.primary.copy(alpha = 0.15f)),
                    contentAlignment = Alignment.Center,
                ) {
                    Text("弥", color = colors.primary, fontSize = 30.sp, fontWeight = FontWeight.Bold)
                }
                Spacer(Modifier.width(16.dp))
                Column {
                    Text("弥娅", color = colors.textPrimary, fontSize = 22.sp, fontWeight = FontWeight.Bold)
                    Spacer(Modifier.height(4.dp))
                    Text(
                        text = "AI 虚拟化身 · v8.0",
                        color = colors.textSecondary,
                        fontSize = 13.sp,
                    )
                    Spacer(Modifier.height(4.dp))
                    Surface(
                        color = colors.primary.copy(alpha = 0.1f),
                        shape = RoundedCornerShape(4.dp),
                    ) {
                        Text(
                            text = "MIYA-CORE",
                            color = colors.primary,
                            fontSize = 10.sp,
                            fontFamily = androidx.compose.ui.text.font.FontFamily.Monospace,
                            modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp),
                        )
                    }
                }
                Spacer(Modifier.weight(1f))
                Icon(Icons.Default.ChevronRight, null, tint = colors.textDim)
            }
        }

        // 连接状态卡片
        item {
            Surface(
                color = colors.surface,
                shape = RoundedCornerShape(12.dp),
                modifier = Modifier.padding(horizontal = 16.dp, vertical = 4.dp),
            ) {
                Row(
                    modifier = Modifier.fillMaxWidth().padding(16.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Box(
                        modifier = Modifier
                            .size(10.dp)
                            .clip(CircleShape)
                            .background(
                                when (connState.status) {
                                    ConnectionStatus.CONNECTED -> colors.success
                                    ConnectionStatus.CONNECTING -> colors.warning
                                    else -> colors.danger
                                }
                            ),
                    )
                    Spacer(Modifier.width(12.dp))
                    Column(modifier = Modifier.weight(1f)) {
                        Text(
                            text = when (connState.status) {
                                ConnectionStatus.CONNECTED -> "已连接"
                                ConnectionStatus.CONNECTING -> "连接中..."
                                ConnectionStatus.ERROR -> "连接失败"
                                ConnectionStatus.DISCONNECTED -> "未连接"
                            },
                            color = colors.textPrimary,
                            fontSize = 15.sp,
                            fontWeight = FontWeight.Medium,
                        )
                        Text(
                            text = connState.baseUrl,
                            color = colors.textDim,
                            fontSize = 12.sp,
                        )
                    }
                }
            }
        }

        item { Spacer(Modifier.height(16.dp)) }

        // 设置项组 1 - 连接与人格
        item {
            SettingsGroup {
                SettingsItem(
                    icon = Icons.Default.Wifi,
                    label = "连接配置",
                    subtitle = "${appConfig.load().serverHost}:${appConfig.load().serverPort}",
                    onClick = { showConnectionEdit = true },
                )
                SettingsItem(
                    icon = Icons.Default.Face,
                    label = "当前人格",
                    subtitle = personas.find { it.id == currentPersonaId }?.displayName
                        ?: personas.find { it.id == currentPersonaId }?.name
                        ?: "default",
                    onClick = { showPersonaSheet = true },
                )
            }
        }

        item { Spacer(Modifier.height(16.dp)) }

        // 设置项组 2 - 外观 + 关于
        item {
            SettingsGroup {
                SettingsItem(
                    icon = if (isDarkTheme) Icons.Default.DarkMode else Icons.Default.LightMode,
                    label = "深色主题",
                    subtitle = if (isDarkTheme) "已开启" else "已关闭",
                    trailing = {
                        Switch(
                            checked = isDarkTheme,
                            onCheckedChange = {
                                isDarkTheme = it
                                appConfig.saveTheme(it)
                            },
                            colors = SwitchDefaults.colors(
                                checkedThumbColor = colors.surface,
                                checkedTrackColor = colors.primary,
                            ),
                        )
                    },
                )
                SettingsItem(
                    icon = Icons.Default.Info,
                    label = "关于弥娅",
                    subtitle = "手机客户端 v2.0 · 弥娅 v8.0",
                )
            }
        }

        item { Spacer(Modifier.height(32.dp)) }

        // 底部文字
        item {
            Text(
                text = "弥娅 (MIYA) AI 虚拟化身\n所有服务运行在你的电脑上",
                color = colors.textDim,
                fontSize = 11.sp,
                textAlign = androidx.compose.ui.text.style.TextAlign.Center,
                modifier = Modifier.fillMaxWidth().padding(bottom = 20.dp),
                lineHeight = 18.sp,
            )
        }
    }

    // ═══ 连接配置弹窗 ═══
    if (showConnectionEdit) {
        AlertDialog(
            onDismissRequest = { showConnectionEdit = false },
            title = { Text("连接配置", color = colors.textPrimary) },
            text = {
                Column {
                    OutlinedTextField(
                        value = editHost,
                        onValueChange = { editHost = it },
                        label = { Text("服务器地址") },
                        singleLine = true,
                        modifier = Modifier.fillMaxWidth(),
                    )
                    Spacer(Modifier.height(8.dp))
                    OutlinedTextField(
                        value = editPort,
                        onValueChange = { editPort = it },
                        label = { Text("端口") },
                        singleLine = true,
                        modifier = Modifier.fillMaxWidth(),
                    )
                }
            },
            confirmButton = {
                TextButton(onClick = {
                    val port = editPort.toIntOrNull() ?: 9800
                    appConfig.saveHost(editHost)
                    appConfig.savePort(port)
                    ServiceLocator.reconnect(editHost, port)
                    connMgr.setLanMode(editHost, port)
                    scope.launch {
                        try {
                            ServiceLocator.apiClient.health()
                            connMgr.markConnected()
                        } catch (_: Exception) {
                            connMgr.markError("连接失败")
                        }
                    }
                    showConnectionEdit = false
                }) {
                    Text("保存并重连", color = colors.primary)
                }
            },
            dismissButton = {
                TextButton(onClick = { showConnectionEdit = false }) {
                    Text("取消", color = colors.textSecondary)
                }
            },
            containerColor = colors.surface,
        )
    }

    // ═══ 人格选择弹窗 ═══
    if (showPersonaSheet) {
        AlertDialog(
            onDismissRequest = { showPersonaSheet = false },
            title = { Text("切换人格", color = colors.textPrimary) },
            text = {
                Column {
                    personas.forEach { persona ->
                        Surface(
                            color = if (currentPersonaId == persona.id) colors.primary.copy(alpha = 0.1f)
                            else Color.Transparent,
                            shape = RoundedCornerShape(8.dp),
                            onClick = {
                                scope.launch {
                                    try {
                                        val result = personaRepo.switch(persona.id)
                                        if (result.success) {
                                            currentPersonaId = result.current
                                            appConfig.load().copy(lastPersonaId = result.current)
                                                .let { appConfig.save(it) }
                                        }
                                    } catch (_: Exception) { }
                                }
                            },
                        ) {
                            Row(
                                modifier = Modifier.fillMaxWidth().padding(12.dp),
                                verticalAlignment = Alignment.CenterVertically,
                            ) {
                                RadioButton(
                                    selected = currentPersonaId == persona.id,
                                    onClick = null,
                                    colors = RadioButtonDefaults.colors(selectedColor = colors.primary),
                                )
                                Spacer(Modifier.width(8.dp))
                                Column {
                                    Text(
                                        persona.displayName ?: persona.name,
                                        color = colors.textPrimary,
                                        fontWeight = if (currentPersonaId == persona.id) FontWeight.Bold else FontWeight.Normal,
                                    )
                                    Text(
                                        persona.id,
                                        color = colors.textDim,
                                        fontSize = 11.sp,
                                    )
                                }
                            }
                        }
                    }
                }
            },
            confirmButton = {
                TextButton(onClick = { showPersonaSheet = false }) {
                    Text("完成", color = colors.primary)
                }
            },
            containerColor = colors.surface,
        )
    }
}

@Composable
private fun SettingsGroup(content: @Composable ColumnScope.() -> Unit) {
    val colors = LocalMiyaColors.current
    Surface(
        color = colors.surface,
        shape = RoundedCornerShape(12.dp),
        modifier = Modifier.padding(horizontal = 16.dp),
    ) {
        Column(modifier = Modifier.padding(vertical = 4.dp)) {
            content()
        }
    }
}

@Composable
private fun SettingsItem(
    icon: ImageVector,
    label: String,
    subtitle: String,
    onClick: (() -> Unit)? = null,
    trailing: (@Composable () -> Unit)? = null,
) {
    val colors = LocalMiyaColors.current
    Surface(
        color = Color.Transparent,
        onClick = { onClick?.invoke() },
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 16.dp, vertical = 14.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Icon(icon, label, tint = colors.primary, modifier = Modifier.size(22.dp))
            Spacer(Modifier.width(14.dp))
            Column(modifier = Modifier.weight(1f)) {
                Text(label, color = colors.textPrimary, fontSize = 15.sp)
                Text(subtitle, color = colors.textDim, fontSize = 12.sp)
            }
            if (trailing != null) {
                trailing()
            } else {
                Icon(Icons.Default.ChevronRight, null, tint = colors.textDim, modifier = Modifier.size(20.dp))
            }
        }
    }
}

@Composable
private fun SettingsItem(
    icon: ImageVector,
    label: String,
    subtitle: String,
) {
    SettingsItem(icon = icon, label = label, subtitle = subtitle, onClick = null, trailing = null)
}
