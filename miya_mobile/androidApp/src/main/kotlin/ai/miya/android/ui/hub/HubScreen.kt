package ai.miya.android.ui.hub

import ai.miya.shared.ServiceLocator
import ai.miya.shared.model.MemoryStats
import ai.miya.shared.model.SystemStatus
import androidx.compose.foundation.background
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
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import ai.miya.android.ui.theme.*
import kotlinx.coroutines.launch

@Composable
fun HubScreen() {
    val scope = rememberCoroutineScope()
    val api = remember { ServiceLocator.apiClient }

    var systemStatus by remember { mutableStateOf<SystemStatus?>(null) }
    var memoryStats by remember { mutableStateOf<MemoryStats?>(null) }
    var isLoading by remember { mutableStateOf(true) }
    var error by remember { mutableStateOf<String?>(null) }

    LaunchedEffect(Unit) {
        scope.launch {
            try {
                systemStatus = api.systemStatus()
                memoryStats = api.getMemoryStats()
                isLoading = false
            } catch (e: Exception) {
                error = e.message
                isLoading = false
            }
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
                text = "中枢",
                color = MiyaTextPrimary,
                fontSize = 24.sp,
                fontWeight = FontWeight.Bold,
            )
        }

        if (isLoading) {
            item {
                Box(
                    modifier = Modifier.fillMaxWidth().height(200.dp),
                    contentAlignment = Alignment.Center,
                ) {
                    CircularProgressIndicator(color = MiyaPrimary)
                }
            }
            return@LazyColumn
        }

        error?.let { err ->
            item {
                Card(
                    colors = CardDefaults.cardColors(containerColor = MiyaEmotionAngry.copy(alpha = 0.2f)),
                    shape = RoundedCornerShape(16.dp),
                ) {
                    Text(
                        text = "连接失败: $err",
                        color = MiyaEmotionAngry,
                        modifier = Modifier.padding(16.dp),
                    )
                }
            }
            return@LazyColumn
        }

        systemStatus?.let { status ->
            // 状态卡片
            item {
                Card(
                    colors = CardDefaults.cardColors(containerColor = MiyaSurface),
                    shape = RoundedCornerShape(16.dp),
                ) {
                    Column(modifier = Modifier.padding(16.dp)) {
                        Text("系统状态", color = MiyaTextPrimary, fontWeight = FontWeight.Bold)
                        Spacer(modifier = Modifier.height(8.dp))
                        StatusRow("运行状态", if (status.running) "在线" else "离线", if (status.running) MiyaEmotionHappy else MiyaEmotionAngry)
                        status.version?.let { StatusRow("版本", it, MiyaAccent) }
                        status.uptime?.let { StatusRow("运行时间", it, MiyaTextSecondary) }
                        StatusRow("连接平台", "${status.platformsActive}/${status.platforms}", MiyaAccent)
                        status.providersLoaded?.let { StatusRow("AI 提供者", "$it 个", MiyaPrimary) }
                    }
                }
            }

            // 人格卡片
            item {
                Card(
                    colors = CardDefaults.cardColors(containerColor = MiyaSurface),
                    shape = RoundedCornerShape(16.dp),
                ) {
                    Column(modifier = Modifier.padding(16.dp)) {
                        Text("当前人格", color = MiyaTextPrimary, fontWeight = FontWeight.Bold)
                        Spacer(modifier = Modifier.height(8.dp))
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Icon(
                                Icons.Filled.Face,
                                contentDescription = null,
                                tint = MiyaPrimary,
                                modifier = Modifier.size(32.dp),
                            )
                            Spacer(modifier = Modifier.width(12.dp))
                            Text(
                                text = status.personality ?: "default",
                                color = MiyaTextPrimary,
                                fontSize = 18.sp,
                                fontWeight = FontWeight.Medium,
                            )
                        }
                    }
                }
            }

            // 情感卡片
            status.emotion?.let { emotion ->
                item {
                    Card(
                        colors = CardDefaults.cardColors(containerColor = MiyaSurface),
                        shape = RoundedCornerShape(16.dp),
                    ) {
                        Column(modifier = Modifier.padding(16.dp)) {
                            Text("当前情感", color = MiyaTextPrimary, fontWeight = FontWeight.Bold)
                            Spacer(modifier = Modifier.height(8.dp))
                            Row(verticalAlignment = Alignment.CenterVertically) {
                                Text(
                                    text = emotion.dominant,
                                    color = MiyaEmotionHappy,
                                    fontSize = 28.sp,
                                )
                                Spacer(modifier = Modifier.width(8.dp))
                                Text(
                                    text = "强度 ${emotion.intensity}%",
                                    color = MiyaTextSecondary,
                                    fontSize = 14.sp,
                                )
                            }
                            if (emotion.emotions.isNotEmpty()) {
                                Spacer(modifier = Modifier.height(8.dp))
                                emotion.emotions.forEach { e ->
                                    Row(
                                        modifier = Modifier.fillMaxWidth().padding(vertical = 2.dp),
                                        verticalAlignment = Alignment.CenterVertically,
                                    ) {
                                        Text(
                                            text = e.name,
                                            color = MiyaTextSecondary,
                                            fontSize = 13.sp,
                                            modifier = Modifier.width(60.dp),
                                        )
                                        LinearProgressIndicator(
                                            progress = { e.intensity / 100f },
                                            modifier = Modifier
                                                .weight(1f)
                                                .height(6.dp)
                                                .clip(RoundedCornerShape(3.dp)),
                                            color = MiyaPrimary,
                                            trackColor = MiyaSurfaceVariant,
                                        )
                                        Spacer(modifier = Modifier.width(8.dp))
                                        Text(
                                            text = "${e.intensity}%",
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
        }

        // 记忆统计卡片
        memoryStats?.let { mem ->
            item {
                Card(
                    colors = CardDefaults.cardColors(containerColor = MiyaSurface),
                    shape = RoundedCornerShape(16.dp),
                ) {
                    Column(modifier = Modifier.padding(16.dp)) {
                        Text("记忆统计", color = MiyaTextPrimary, fontWeight = FontWeight.Bold)
                        Spacer(modifier = Modifier.height(12.dp))
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceEvenly,
                        ) {
                            MemoryStatItem("总计", mem.total)
                            MemoryStatItem("对话", mem.dialogue)
                            MemoryStatItem("长期", mem.longTerm)
                            MemoryStatItem("语义", mem.semantic)
                        }
                        Spacer(modifier = Modifier.height(8.dp))
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceEvenly,
                        ) {
                            MemoryStatItem("短期", mem.shortTerm)
                            MemoryStatItem("知识", mem.knowledge)
                            MemoryStatItem("固定", mem.pinned)
                            MemoryStatItem("节点", mem.nodeCount)
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun StatusRow(label: String, value: String, color: androidx.compose.ui.graphics.Color) {
    Row(
        modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
    ) {
        Text(text = label, color = MiyaTextSecondary, fontSize = 14.sp)
        Text(text = value, color = color, fontSize = 14.sp, fontWeight = FontWeight.Medium)
    }
}

@Composable
private fun MemoryStatItem(label: String, count: Int) {
    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        Text(
            text = "$count",
            color = MiyaPrimary,
            fontSize = 20.sp,
            fontWeight = FontWeight.Bold,
        )
        Text(
            text = label,
            color = MiyaTextSecondary,
            fontSize = 12.sp,
        )
    }
}
