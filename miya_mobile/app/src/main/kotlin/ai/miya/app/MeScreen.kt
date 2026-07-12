package ai.miya.app

import ai.miya.domain.ServiceRegistry
import ai.miya.domain.ConnectionProvider
import ai.miya.domain.ConnectionStatus
import ai.miya.uicommon.component.ConnectionDot
import ai.miya.uicommon.component.ConnectionDotState
import ai.miya.uicommon.theme.MiyaColors
import androidx.compose.animation.*
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.KeyboardArrowRight
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
import androidx.lifecycle.compose.collectAsStateWithLifecycle

@Composable
fun MeScreen(
    onSettingsClick: () -> Unit,
) {
    val cp = remember { ServiceRegistry.get(ConnectionProvider::class.java) }
    val connectionState by cp?.state?.collectAsStateWithLifecycle()
        ?: remember { mutableStateOf(null) }
    val isConnected = connectionState?.status == ConnectionStatus.CONNECTED
    val host = connectionState?.baseUrl?.removePrefix("http://")?.split(":")?.getOrNull(0) ?: ""
    val port = connectionState?.baseUrl?.removePrefix("http://")?.split(":")?.getOrNull(1) ?: ""

    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp),
    ) {
        // Profile header
        AnimatedItem(0) {
            Card(
                shape = RoundedCornerShape(16.dp),
                colors = CardDefaults.cardColors(containerColor = Color(0xFF2D2228)),
            ) {
                Row(
                    modifier = Modifier.padding(20.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Box(
                        modifier = Modifier
                            .size(56.dp)
                            .clip(CircleShape)
                            .background(MiyaColors.Primary.copy(alpha = 0.15f)),
                        contentAlignment = Alignment.Center,
                    ) {
                        Text("弥", color = MiyaColors.Primary, style = MaterialTheme.typography.headlineMedium)
                    }
                    Spacer(Modifier.width(16.dp))
                    Column {
                        Text("弥娅 (MIYA)", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            ConnectionDot(
                                state = if (isConnected) ConnectionDotState.CONNECTED else ConnectionDotState.DISCONNECTED,
                            )
                            Spacer(Modifier.width(6.dp))
                            Text(
                                if (isConnected) "$host:$port · 已连接" else "未连接",
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.onSurfaceVariant,
                            )
                        }
                    }
                }
            }
        }

        // Menu
        AnimatedItem(1) {
            Card(
                shape = RoundedCornerShape(14.dp),
                colors = CardDefaults.cardColors(containerColor = Color(0xFF2D2228)),
            ) {
                MeMenuItem(
                    icon = Icons.Default.Settings,
                    title = "连接设置",
                    subtitle = "服务器地址与端口配置",
                    onClick = onSettingsClick,
                )
            }
        }

        // About
        AnimatedItem(2) {
            Card(
                shape = RoundedCornerShape(14.dp),
                colors = CardDefaults.cardColors(containerColor = Color(0xFF2D2228)),
            ) {
                Column(modifier = Modifier.padding(20.dp)) {
                    Text("关于", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
                    Spacer(Modifier.height(12.dp))
                    AboutRow("版本", "1.0.0")
                    AboutRow("构建", "Android Native · Compose M3")
                    AboutRow("通信", "REST + SSE + WebSocket")
                    AboutRow("后端", "http://$host:$port")
                }
            }
        }

        // Footer
        Spacer(Modifier.height(16.dp))
        Text(
            "弥娅 AI 虚拟化身 · 移动客户端",
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.5f),
            modifier = Modifier.align(Alignment.CenterHorizontally),
        )

        Spacer(Modifier.height(32.dp))
    }
}

@Composable
private fun MeMenuItem(
    icon: ImageVector,
    title: String,
    subtitle: String,
    onClick: () -> Unit,
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick)
            .padding(horizontal = 16.dp, vertical = 14.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Box(
            modifier = Modifier
                .size(40.dp)
                .clip(RoundedCornerShape(12.dp))
                .background(MiyaColors.Primary.copy(alpha = 0.1f)),
            contentAlignment = Alignment.Center,
        ) {
            Icon(icon, null, tint = MiyaColors.Primary, modifier = Modifier.size(22.dp))
        }
        Spacer(Modifier.width(14.dp))
        Column(modifier = Modifier.weight(1f)) {
            Text(title, style = MaterialTheme.typography.bodyLarge)
            Text(subtitle, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
        Icon(Icons.AutoMirrored.Filled.KeyboardArrowRight, null, tint = MaterialTheme.colorScheme.onSurfaceVariant, modifier = Modifier.size(20.dp))
    }
}

@Composable
private fun AboutRow(label: String, value: String) {
    Row(
        modifier = Modifier.fillMaxWidth().padding(vertical = 2.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
    ) {
        Text(label, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
        Text(value, style = MaterialTheme.typography.bodyMedium)
    }
}

@Composable
private fun AnimatedItem(index: Int, content: @Composable () -> Unit) {
    AnimatedVisibility(
        visible = true,
        enter = fadeIn(tween(400, delayMillis = index * 80)) +
                slideInVertically(tween(400, delayMillis = index * 80)) { it / 4 },
    ) {
        content()
    }
}
