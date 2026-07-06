package ai.miya.android.ui.discover

import ai.miya.shared.ServiceLocator
import ai.miya.shared.model.EmotionState
import ai.miya.shared.model.MemoryStats
import ai.miya.shared.model.SystemStatus
import ai.miya.android.ui.theme.LocalMiyaColors
import ai.miya.android.ui.theme.emotionColor
import androidx.compose.animation.*
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
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.coroutines.launch

@Composable
fun DiscoverScreen() {
    val colors = LocalMiyaColors.current
    val scope = rememberCoroutineScope()
    val api = remember { ServiceLocator.apiClient }
    val ws = remember { ServiceLocator.webSocket }

    var systemStatus by remember { mutableStateOf<SystemStatus?>(null) }
    var memoryStats by remember { mutableStateOf<MemoryStats?>(null) }
    var isLoading by remember { mutableStateOf(true) }
    var error by remember { mutableStateOf<String?>(null) }

    LaunchedEffect(Unit) {
        try {
            systemStatus = api.systemStatus()
            memoryStats = api.getMemoryStats()
            isLoading = false
        } catch (e: Exception) {
            error = "连接失败: ${e.message}"
            isLoading = false
        }
    }

    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .background(colors.background)
            .statusBarsPadding(),
    ) {
        item {
            Text(
                text = "发现",
                color = colors.textPrimary,
                fontSize = 28.sp,
                fontWeight = FontWeight.Bold,
                modifier = Modifier.padding(horizontal = 20.dp, vertical = 14.dp),
            )
        }

        if (isLoading) {
            item {
                Box(
                    modifier = Modifier.fillMaxWidth().height(200.dp),
                    contentAlignment = Alignment.Center,
                ) {
                    CircularProgressIndicator(color = colors.primary)
                }
            }
            return@LazyColumn
        }

        error?.let { err ->
            item {
                Surface(
                    color = colors.danger.copy(alpha = 0.1f),
                    shape = RoundedCornerShape(12.dp),
                    modifier = Modifier.padding(horizontal = 16.dp, vertical = 8.dp),
                ) {
                    Row(
                        modifier = Modifier.padding(16.dp),
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Icon(Icons.Default.Warning, "错误", tint = colors.danger, modifier = Modifier.size(20.dp))
                        Spacer(Modifier.width(8.dp))
                        Text(err, color = colors.danger, fontSize = 13.sp)
                    }
                }
            }
            return@LazyColumn
        }

        // ═══ 实时情感面板 ═══
        systemStatus?.emotion?.let { emotion ->
            item {
                SectionTitle("灵魂共鸣", "SOUL RESONANCE")
            }
            item {
                EmotionPanel(emotion)
            }
        }

        // ═══ 认知引擎状态 ═══
        systemStatus?.let { status ->
            item { Spacer(Modifier.height(8.dp)) }
            item {
                SectionTitle("认知引擎", "COGNITION ENGINE")
            }
            item {
                CognitionPanel(status, memoryStats)
            }
        }

        // ═══ 记忆搜索入口 ═══
        item { Spacer(Modifier.height(8.dp)) }
        item {
            SectionTitle("记忆搜索", "MEMORY SEARCH")
        }
        item {
            MemorySearchEntry()
        }

        // ═══ 每日数据卡片 ═══
        item { Spacer(Modifier.height(8.dp)) }
        item {
            SectionTitle("今日数据", "DAILY STATS")
        }
        item {
            DailyStatsCard()
        }

        item { Spacer(Modifier.height(24.dp)) }
    }
}

@Composable
private fun SectionTitle(title: String, subtitle: String) {
    val colors = LocalMiyaColors.current
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 20.dp, vertical = 4.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Text(title, color = colors.textPrimary, fontSize = 17.sp, fontWeight = FontWeight.SemiBold)
        Spacer(Modifier.width(8.dp))
        Text(
            subtitle,
            color = colors.textDim,
            fontSize = 10.sp,
            fontFamily = FontFamily.Monospace,
            letterSpacing = 1.sp,
        )
    }
}

@Composable
private fun EmotionPanel(emotion: EmotionState) {
    val colors = LocalMiyaColors.current
    val emoCol = emotionColor(emotion.dominant)

    Surface(
        color = colors.surface,
        shape = RoundedCornerShape(16.dp),
        modifier = Modifier.padding(horizontal = 16.dp),
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            // 主导情绪
            Row(verticalAlignment = Alignment.CenterVertically) {
                Box(
                    modifier = Modifier
                        .size(10.dp)
                        .clip(CircleShape)
                        .background(emoCol),
                )
                Spacer(Modifier.width(8.dp))
                Text(
                    text = emotion.dominant,
                    color = emoCol,
                    fontSize = 22.sp,
                    fontWeight = FontWeight.Bold,
                )
                Spacer(Modifier.weight(1f))
                Text(
                    text = "强度 ${emotion.intensity}%",
                    color = colors.textSecondary,
                    fontSize = 12.sp,
                )
            }

            // 情绪条
            if (emotion.emotions.isNotEmpty()) {
                Spacer(Modifier.height(12.dp))
                emotion.emotions.take(6).forEach { e ->
                    Row(
                        modifier = Modifier.fillMaxWidth().padding(vertical = 3.dp),
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Text(
                            text = e.name,
                            color = colors.textSecondary,
                            fontSize = 12.sp,
                            modifier = Modifier.width(50.dp),
                        )
                        LinearProgressIndicator(
                            progress = { e.intensity / 100f },
                            modifier = Modifier
                                .weight(1f)
                                .height(6.dp)
                                .clip(RoundedCornerShape(3.dp)),
                            color = emotionColor(e.name),
                            trackColor = colors.surfaceVariant,
                        )
                        Spacer(Modifier.width(6.dp))
                        Text(
                            text = "${e.intensity}%",
                            color = colors.textDim,
                            fontSize = 10.sp,
                            fontFamily = FontFamily.Monospace,
                        )
                    }
                }
            }

            // 内心独白
            emotion.innerThought?.let { thought ->
                Spacer(Modifier.height(12.dp))
                Surface(
                    color = colors.primary.copy(alpha = 0.06f),
                    shape = RoundedCornerShape(8.dp),
                ) {
                    Text(
                        text = "\u201C${thought}\u201D",
                        color = colors.textSecondary,
                        fontSize = 13.sp,
                        lineHeight = 20.sp,
                        modifier = Modifier.padding(12.dp),
                    )
                }
            }
        }
    }
}

@Composable
private fun CognitionPanel(status: SystemStatus, memoryStats: MemoryStats?) {
    val colors = LocalMiyaColors.current

    Surface(
        color = colors.surface,
        shape = RoundedCornerShape(16.dp),
        modifier = Modifier.padding(horizontal = 16.dp),
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            // 状态指示器
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
            ) {
                StatusBadge(
                    label = "服务",
                    value = if (status.running) "在线" else "离线",
                    color = if (status.running) colors.success else colors.danger,
                )
                StatusBadge(
                    label = "版本",
                    value = status.version ?: "--",
                    color = colors.accent,
                )
                StatusBadge(
                    label = "人格",
                    value = status.personality ?: "default",
                    color = colors.primary,
                )
            }

            Spacer(Modifier.height(12.dp))
            HorizontalDivider(color = colors.divider)
            Spacer(Modifier.height(12.dp))

            // 平台 + AI Provider
            Row(modifier = Modifier.fillMaxWidth()) {
                InfoItem("连接平台", "${status.platformsActive}/${status.platforms}")
                Spacer(Modifier.width(16.dp))
                InfoItem("AI 引擎", "${status.providersLoaded ?: 0} 个")
            }

            // 运行时间
            status.uptime?.let {
                Spacer(Modifier.height(8.dp))
                InfoItem("运行时间", it)
            }

            // 记忆统计
            memoryStats?.let { mem ->
                Spacer(Modifier.height(12.dp))
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceEvenly,
                ) {
                    MemoryDot("总计", mem.total)
                    MemoryDot("对话", mem.dialogue)
                    MemoryDot("长期", mem.longTerm)
                    MemoryDot("语义", mem.semantic)
                    MemoryDot("节点", mem.nodeCount)
                }
            }
        }
    }
}

@Composable
private fun StatusBadge(label: String, value: String, color: androidx.compose.ui.graphics.Color) {
    val colors = LocalMiyaColors.current
    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        Text(value, color = color, fontSize = 15.sp, fontWeight = FontWeight.Bold)
        Text(label, color = colors.textDim, fontSize = 10.sp)
    }
}

@Composable
private fun InfoItem(label: String, value: String) {
    val colors = LocalMiyaColors.current
    Row(verticalAlignment = Alignment.CenterVertically) {
        Text(label, color = colors.textSecondary, fontSize = 13.sp)
        Spacer(Modifier.width(6.dp))
        Text(value, color = colors.textPrimary, fontSize = 13.sp, fontWeight = FontWeight.Medium)
    }
}

@Composable
private fun MemoryDot(label: String, count: Int) {
    val colors = LocalMiyaColors.current
    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        Text(
            "$count",
            color = colors.primary,
            fontSize = 18.sp,
            fontWeight = FontWeight.Bold,
        )
        Text(label, color = colors.textDim, fontSize = 10.sp)
    }
}

@Composable
private fun MemorySearchEntry() {
    val colors = LocalMiyaColors.current
    var query by remember { mutableStateOf("") }
    var searchResults by remember { mutableStateOf("") }
    val scope = rememberCoroutineScope()

    Surface(
        color = colors.surface,
        shape = RoundedCornerShape(16.dp),
        modifier = Modifier.padding(horizontal = 16.dp),
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(
                    Icons.Default.Search,
                    "搜索",
                    tint = colors.textDim,
                    modifier = Modifier.size(20.dp),
                )
                Spacer(Modifier.width(8.dp))
                OutlinedTextField(
                    value = query,
                    onValueChange = { query = it },
                    placeholder = { Text("搜索弥娅的记忆...", color = colors.textDim) },
                    modifier = Modifier.weight(1f),
                    singleLine = true,
                    colors = OutlinedTextFieldDefaults.colors(
                        focusedContainerColor = colors.background,
                        unfocusedContainerColor = colors.background,
                        focusedBorderColor = colors.primary,
                        unfocusedBorderColor = Color.Transparent,
                        focusedTextColor = colors.textPrimary,
                        unfocusedTextColor = colors.textPrimary,
                        cursorColor = colors.accent,
                    ),
                    shape = RoundedCornerShape(10.dp),
                )
                Spacer(Modifier.width(8.dp))
                Button(
                    onClick = {
                        scope.launch {
                            try {
                                val results = ServiceLocator.memoryRepo.search(query, 5)
                                searchResults = results.joinToString("\n") { it.content.take(80) + "..." }
                            } catch (_: Exception) {
                                searchResults = "搜索失败"
                            }
                        }
                    },
                    enabled = query.trim().isNotEmpty(),
                    colors = ButtonDefaults.buttonColors(containerColor = colors.primary),
                    shape = RoundedCornerShape(10.dp),
                ) {
                    Text("搜索", fontSize = 13.sp)
                }
            }
            if (searchResults.isNotEmpty()) {
                Spacer(Modifier.height(8.dp))
                Text(searchResults, color = colors.textSecondary, fontSize = 13.sp, lineHeight = 20.sp)
            }
        }
    }
}

@Composable
private fun DailyStatsCard() {
    val colors = LocalMiyaColors.current
    Surface(
        color = colors.surface,
        shape = RoundedCornerShape(16.dp),
        modifier = Modifier.padding(horizontal = 16.dp),
    ) {
        Row(
            modifier = Modifier.fillMaxWidth().padding(20.dp),
            horizontalArrangement = Arrangement.SpaceEvenly,
        ) {
            DailyStatItem("\uD83D\uDCAC", "12", "对话轮数")
            DailyStatItem("\u2764\uFE0F", "joy", "主情绪")
            DailyStatItem("\u23F1\uFE0F", "5min", "响应速度")
            DailyStatItem("\uD83C\uDF1F", "8.0", "版本号")
        }
    }
}

@Composable
private fun DailyStatItem(icon: String, value: String, label: String) {
    val colors = LocalMiyaColors.current
    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        Text(icon, fontSize = 24.sp)
        Spacer(Modifier.height(4.dp))
        Text(value, color = colors.textPrimary, fontSize = 18.sp, fontWeight = FontWeight.Bold)
        Text(label, color = colors.textDim, fontSize = 10.sp)
    }
}
