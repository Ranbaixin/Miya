package ai.miya.feature.hub

import ai.miya.domain.ServiceRegistry
import ai.miya.domain.SessionProvider
import ai.miya.model.MemoryStats
import ai.miya.model.MiyaEmotion
import ai.miya.model.SystemStatus
import ai.miya.uicommon.theme.MiyaColors
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch
import androidx.lifecycle.viewModelScope
import androidx.compose.animation.animateColorAsState
import androidx.compose.animation.core.*
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Favorite
import androidx.compose.material.icons.filled.Memory
import androidx.compose.material.icons.filled.Psychology
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle

data class HubState(
    val status: SystemStatus? = null,
    val isLoading: Boolean = true,
    val emotion: MiyaEmotion = MiyaEmotion.NEUTRAL,
    val emotionIntensity: Int = 50,
)

class HubViewModel : androidx.lifecycle.ViewModel() {

    private val _state = MutableStateFlow(HubState())
    val state: StateFlow<HubState> = _state.asStateFlow()

    fun refresh() {
        viewModelScope.launch {
            _state.update { it.copy(isLoading = true) }
            try {
                val sessionProvider = ServiceRegistry.getOrThrow(SessionProvider::class.java)
                val status = sessionProvider.getStatus()
                val emotion = status.emotion?.let {
                    MiyaEmotion.fromDominant(it.dominant)
                } ?: MiyaEmotion.NEUTRAL
                val intensity = status.emotion?.intensity ?: 50
                _state.update { it.copy(
                    status = status,
                    emotion = emotion,
                    emotionIntensity = intensity,
                    isLoading = false,
                ) }
            } catch (_: Exception) {
                _state.update { it.copy(isLoading = false) }
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun HubScreen(
    viewModel: HubViewModel = androidx.lifecycle.viewmodel.compose.viewModel(),
    onBack: () -> Unit,
) {
    val state by viewModel.state.collectAsStateWithLifecycle()

    LaunchedEffect(Unit) {
        viewModel.refresh()
    }

    Column(modifier = Modifier.fillMaxSize()) {
        TopAppBar(
            title = { Text("弥娅中枢") },
            navigationIcon = {
                IconButton(onClick = onBack) {
                    Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "返回")
                }
            },
        )

        if (state.isLoading) {
            Box(
                modifier = Modifier.fillMaxSize(),
                contentAlignment = Alignment.Center,
            ) {
                CircularProgressIndicator(color = MaterialTheme.colorScheme.primary)
            }
        } else if (state.status != null) {
            HubContent(
                status = state.status!!,
                emotion = state.emotion,
                intensity = state.emotionIntensity,
                onRefresh = { viewModel.refresh() },
            )
        }
    }
}

@Composable
private fun HubContent(
    status: SystemStatus,
    emotion: MiyaEmotion,
    intensity: Int,
    onRefresh: () -> Unit,
) {
    val statusColor by animateColorAsState(
        if (status.running) MiyaColors.Online else MiyaColors.Error,
    )

    LazyColumn(
        modifier = Modifier.fillMaxSize(),
        contentPadding = PaddingValues(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        // Emotion card
        item {
            EmotionCard(emotion = emotion, intensity = intensity)
        }

        // System info
        item {
            Card(shape = RoundedCornerShape(16.dp)) {
                Column(modifier = Modifier.padding(20.dp)) {
                    Text("系统状态", style = MaterialTheme.typography.titleMedium)
                    Spacer(Modifier.height(16.dp))
                    InfoRow("版本", status.version ?: "未知")
                    InfoRow("运行时间", status.uptime ?: "未知")
                    InfoRow("当前人格", status.personality ?: "未选择")
                    InfoRow("接入平台", "${status.platformsActive}/${status.platforms} 在线")

                    Spacer(Modifier.height(12.dp))
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Box(
                            modifier = Modifier
                                .size(10.dp)
                                .clip(CircleShape)
                                .background(statusColor),
                        )
                        Spacer(Modifier.width(8.dp))
                        Text(
                            text = if (status.running) "守护进程运行中" else "守护进程离线",
                            style = MaterialTheme.typography.bodyMedium,
                            color = statusColor,
                        )
                    }
                }
            }
        }

        // Memory stats
        if (status.memory != null) {
            item {
                Card(shape = RoundedCornerShape(16.dp)) {
                    Column(modifier = Modifier.padding(20.dp)) {
                        Text("记忆统计", style = MaterialTheme.typography.titleMedium)
                        Spacer(Modifier.height(16.dp))
                        Row(
                            horizontalArrangement = Arrangement.spacedBy(12.dp),
                        ) {
                            val mem = status.memory!!
                            HubStatItem("总计", mem.total, Icons.Default.Memory, MiyaColors.Primary)
                            HubStatItem("短期", mem.shortTermCount, Icons.Default.Psychology, MiyaColors.Secondary)
                            HubStatItem("长期", mem.longTermCount, Icons.Default.Favorite, MiyaColors.Calm)
                        }
                    }
                }
            }
        }

        // Refresh button
        item {
            TextButton(
                onClick = onRefresh,
                modifier = Modifier.fillMaxWidth(),
            ) {
                Text("刷新状态")
            }
        }
    }
}

@Composable
private fun EmotionCard(emotion: MiyaEmotion, intensity: Int) {
    val emotionColor by animateColorAsState(
        when (emotion) {
            MiyaEmotion.HAPPY, MiyaEmotion.JOY -> MiyaColors.Happy
            MiyaEmotion.SAD -> MiyaColors.Sad
            MiyaEmotion.ANGRY -> MiyaColors.Angry
            MiyaEmotion.SURPRISE -> MiyaColors.Warning
            else -> MiyaColors.Primary
        },
    )

    Card(
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(
            containerColor = emotionColor.copy(alpha = 0.1f),
        ),
    ) {
        Row(
            modifier = Modifier.padding(20.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Box(
                modifier = Modifier
                    .size(56.dp)
                    .clip(CircleShape)
                    .background(emotionColor.copy(alpha = 0.2f)),
                contentAlignment = Alignment.Center,
            ) {
                Text(
                    text = emotion.displayName.first().toString(),
                    style = MaterialTheme.typography.headlineMedium,
                    color = emotionColor,
                )
            }
            Spacer(Modifier.width(16.dp))
            Column {
                Text(
                    text = "当前情绪: ${emotion.displayName}",
                    style = MaterialTheme.typography.titleMedium,
                    color = MaterialTheme.colorScheme.onSurface,
                )
                Spacer(Modifier.height(4.dp))
                LinearProgressIndicator(
                    progress = { intensity / 100f },
                    modifier = Modifier.fillMaxWidth(0.6f),
                    color = emotionColor,
                    trackColor = emotionColor.copy(alpha = 0.1f),
                )
                Text(
                    text = "强度: $intensity%",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
        }
    }
}

@Composable
private fun InfoRow(label: String, value: String) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 4.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
    ) {
        Text(
            text = label,
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        Text(
            text = value,
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurface,
        )
    }
}

@Composable
private fun HubStatItem(label: String, value: Int, icon: ImageVector, color: Color) {
    Column(
        modifier = Modifier
            .clip(RoundedCornerShape(12.dp))
            .background(color.copy(alpha = 0.1f))
            .padding(12.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Icon(icon, contentDescription = null, tint = color)
        Spacer(Modifier.height(4.dp))
        Text(
            text = "$value",
            style = MaterialTheme.typography.titleLarge,
            color = color,
        )
        Text(
            text = label,
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
    }

}
