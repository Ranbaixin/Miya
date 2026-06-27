package ai.miya.android.ui.settings

import ai.miya.shared.ServiceLocator
import ai.miya.shared.model.Persona
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import ai.miya.android.ui.theme.*
import kotlinx.coroutines.launch

@Composable
fun SettingsScreen() {
    val scope = rememberCoroutineScope()
    val repo = remember { ServiceLocator.personaRepo }
    val connMgr = remember { ServiceLocator.connectionManager }

    var personas by remember { mutableStateOf<List<Persona>>(emptyList()) }
    var currentPersonaId by remember { mutableStateOf<String?>(null) }
    var connectionHost by remember { mutableStateOf("localhost") }
    var connectionPort by remember { mutableStateOf("9800") }
    val connectionState by connMgr.state.collectAsState()

    LaunchedEffect(Unit) {
        scope.launch {
            try {
                personas = repo.getList()
                val current = repo.getCurrent()
                currentPersonaId = current.id ?: current.current
            } catch (_: Exception) { }
        }
    }

    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .background(MiyaBackground)
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        item {
            Text(
                text = "设置",
                color = MiyaTextPrimary,
                fontSize = 24.sp,
                fontWeight = FontWeight.Bold,
            )
        }

        // 连接设置
        item {
            Card(
                colors = CardDefaults.cardColors(containerColor = MiyaSurface),
                shape = RoundedCornerShape(16.dp),
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Text("连接设置", color = MiyaTextPrimary, fontWeight = FontWeight.Bold)
                    Spacer(modifier = Modifier.height(12.dp))

                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(8.dp),
                    ) {
                        OutlinedTextField(
                            value = connectionHost,
                            onValueChange = { connectionHost = it },
                            label = { Text("主机") },
                            modifier = Modifier.weight(0.6f),
                            colors = OutlinedTextFieldDefaults.colors(
                                focusedContainerColor = MiyaSurfaceVariant,
                                unfocusedContainerColor = MiyaSurfaceVariant,
                                focusedBorderColor = MiyaPrimary,
                                unfocusedBorderColor = MiyaBorder,
                                focusedTextColor = MiyaTextPrimary,
                                unfocusedTextColor = MiyaTextPrimary,
                            ),
                        )
                        OutlinedTextField(
                            value = connectionPort,
                            onValueChange = { connectionPort = it },
                            label = { Text("端口") },
                            modifier = Modifier.weight(0.4f),
                            colors = OutlinedTextFieldDefaults.colors(
                                focusedContainerColor = MiyaSurfaceVariant,
                                unfocusedContainerColor = MiyaSurfaceVariant,
                                focusedBorderColor = MiyaPrimary,
                                unfocusedBorderColor = MiyaBorder,
                                focusedTextColor = MiyaTextPrimary,
                                unfocusedTextColor = MiyaTextPrimary,
                            ),
                        )
                    }
                    Spacer(modifier = Modifier.height(8.dp))
                    Button(
                        onClick = {
                            val port = connectionPort.toIntOrNull() ?: 9800
                            connMgr.setLanMode(connectionHost, port)
                        },
                        colors = ButtonDefaults.buttonColors(containerColor = MiyaPrimary),
                        modifier = Modifier.fillMaxWidth(),
                    ) {
                        Icon(Icons.Filled.Wifi, contentDescription = null)
                        Spacer(modifier = Modifier.width(8.dp))
                        Text("重新连接")
                    }
                }
            }
        }

        // 连接状态
        item {
            Card(
                colors = CardDefaults.cardColors(containerColor = MiyaSurface),
                shape = RoundedCornerShape(16.dp),
            ) {
                Row(
                    modifier = Modifier.padding(16.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Icon(
                        Icons.Filled.Circle,
                        contentDescription = null,
                        tint = when (connectionState.status) {
                            ai.miya.shared.connection.ConnectionStatus.CONNECTED -> MiyaEmotionHappy
                            ai.miya.shared.connection.ConnectionStatus.CONNECTING -> MiyaEmotionSurprise
                            else -> MiyaEmotionAngry
                        },
                        modifier = Modifier.size(12.dp),
                    )
                    Spacer(modifier = Modifier.width(12.dp))
                    Text(
                        text = when (connectionState.status) {
                            ai.miya.shared.connection.ConnectionStatus.CONNECTED -> "已连接 ${connectionState.baseUrl}"
                            ai.miya.shared.connection.ConnectionStatus.CONNECTING -> "连接中..."
                            ai.miya.shared.connection.ConnectionStatus.ERROR -> "连接失败: ${connectionState.error ?: ""}"
                            ai.miya.shared.connection.ConnectionStatus.DISCONNECTED -> "未连接"
                        },
                        color = MiyaTextSecondary,
                        fontSize = 13.sp,
                    )
                }
            }
        }

        // 人格选择
        item {
            Card(
                colors = CardDefaults.cardColors(containerColor = MiyaSurface),
                shape = RoundedCornerShape(16.dp),
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Text("切换人格", color = MiyaTextPrimary, fontWeight = FontWeight.Bold)
                    Spacer(modifier = Modifier.height(12.dp))

                    if (personas.isEmpty()) {
                        Text("加载中...", color = MiyaTextSecondary)
                    } else {
                        personas.forEach { persona ->
                            Row(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .clickable {
                                        scope.launch {
                                            try {
                                                val result = repo.switch(persona.id)
                                                if (result.success) {
                                                    currentPersonaId = result.current
                                                }
                                            } catch (_: Exception) { }
                                        }
                                    }
                                    .padding(vertical = 10.dp),
                                verticalAlignment = Alignment.CenterVertically,
                            ) {
                                RadioButton(
                                    selected = currentPersonaId == persona.id,
                                    onClick = {
                                        scope.launch {
                                            try {
                                                val result = repo.switch(persona.id)
                                                if (result.success) {
                                                    currentPersonaId = result.current
                                                }
                                            } catch (_: Exception) { }
                                        }
                                    },
                                    colors = RadioButtonDefaults.colors(selectedColor = MiyaPrimary),
                                )
                                Spacer(modifier = Modifier.width(8.dp))
                                Column {
                                    Text(
                                        text = persona.displayName ?: persona.name,
                                        color = MiyaTextPrimary,
                                        fontWeight = if (currentPersonaId == persona.id) FontWeight.Bold else FontWeight.Normal,
                                    )
                                    Text(
                                        text = persona.id,
                                        color = MiyaTextSecondary,
                                        fontSize = 12.sp,
                                    )
                                }
                            }
                        }
                    }
                }
            }
        }

        // 关于
        item {
            Card(
                colors = CardDefaults.cardColors(containerColor = MiyaSurface),
                shape = RoundedCornerShape(16.dp),
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Text("关于", color = MiyaTextPrimary, fontWeight = FontWeight.Bold)
                    Spacer(modifier = Modifier.height(8.dp))
                    Text("弥娅 v8.0 - 手机客户端 v1.0", color = MiyaTextSecondary, fontSize = 13.sp)
                    Text("AI 虚拟化身 · 原生应用", color = MiyaTextSecondary, fontSize = 13.sp)
                }
            }
        }
    }
}
