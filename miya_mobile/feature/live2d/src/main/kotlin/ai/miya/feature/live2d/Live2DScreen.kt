package ai.miya.feature.live2d

import ai.miya.domain.ServiceRegistry
import ai.miya.domain.WebSocketProvider
import ai.miya.domain.WsEvent
import ai.miya.model.MiyaEmotion
import ai.miya.uicommon.theme.MiyaColors
import androidx.lifecycle.viewModelScope
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.compose.animation.animateColorAsState
import androidx.compose.animation.core.*
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch
import kotlin.math.cos
import kotlin.math.sin

data class Live2DState(
    val emotion: MiyaEmotion = MiyaEmotion.NEUTRAL,
    val intensity: Int = 50,
    val innerThought: String? = null,
    val isConnected: Boolean = false,
    val showEmotionPicker: Boolean = false,
    val availableEmotions: List<MiyaEmotion> = MiyaEmotion.entries,
)

class Live2DViewModel : androidx.lifecycle.ViewModel() {

    private val _state = MutableStateFlow(Live2DState())
    val state: StateFlow<Live2DState> = _state.asStateFlow()

    init {
        observeEmotionUpdates()
    }

    private fun observeEmotionUpdates() {
        viewModelScope.launch {
            val wsProvider = ServiceRegistry.get(WebSocketProvider::class.java)
            wsProvider?.events?.collectLatest { event ->
                when (event) {
                    is WsEvent.EmotionChanged -> {
                        _state.update { it.copy(
                            emotion = MiyaEmotion.fromDominant(event.dominant),
                            intensity = event.intensity,
                            isConnected = true,
                        ) }
                    }
                    is WsEvent.Connected -> {
                        _state.update { it.copy(isConnected = true) }
                    }
                    is WsEvent.Disconnected -> {
                        _state.update { it.copy(isConnected = false) }
                    }
                    else -> {}
                }
            }
        }
    }

    fun onSelectEmotion(emotion: MiyaEmotion) {
        _state.update { it.copy(emotion = emotion, showEmotionPicker = false) }
    }
}

@Composable
fun Live2DScreen(
    viewModel: Live2DViewModel = androidx.lifecycle.viewmodel.compose.viewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()

    Box(
        modifier = Modifier.fillMaxSize(),
        contentAlignment = Alignment.Center,
    ) {
        // Placeholder for actual Live2D rendering
        Live2DPlaceholder(
            emotion = state.emotion,
            intensity = state.intensity,
            isConnected = state.isConnected,
            innerThought = state.innerThought,
            modifier = Modifier.fillMaxSize(),
        )

        // Emotion label
        Column(
            modifier = Modifier
                .align(Alignment.BottomCenter)
                .padding(bottom = 32.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            Text(
                text = state.emotion.displayName,
                style = MaterialTheme.typography.headlineMedium,
                color = MaterialTheme.colorScheme.onSurface,
            )
            Spacer(Modifier.height(4.dp))
            Text(
                text = "强度: ${state.intensity}%",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }

        // Connection indicator
        Row(
            modifier = Modifier
                .align(Alignment.TopEnd)
                .padding(16.dp)
                .clip(RoundedCornerShape(8.dp))
                .background(MaterialTheme.colorScheme.surface.copy(alpha = 0.8f))
                .padding(horizontal = 12.dp, vertical = 6.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Box(
                modifier = Modifier
                    .size(8.dp)
                    .clip(CircleShape)
                    .background(if (state.isConnected) MiyaColors.Online else MiyaColors.Offline),
            )
            Spacer(Modifier.width(6.dp))
            Text(
                text = if (state.isConnected) "已连接" else "断开",
                style = MaterialTheme.typography.bodySmall,
            )
        }
    }
}

@Composable
private fun Live2DPlaceholder(
    emotion: MiyaEmotion,
    intensity: Int,
    isConnected: Boolean,
    innerThought: String?,
    modifier: Modifier = Modifier,
) {
    val emotionColor by animateColorAsState(
        when (emotion) {
            MiyaEmotion.HAPPY, MiyaEmotion.JOY -> MiyaColors.Happy
            MiyaEmotion.SAD -> MiyaColors.Sad
            MiyaEmotion.ANGRY -> MiyaColors.Angry
            MiyaEmotion.SURPRISE, MiyaEmotion.ANTICIPATION -> Color(0xFFFFAB91)
            else -> MiyaColors.Primary
        },
    )

    val infiniteTransition = rememberInfiniteTransition()
    val breatheScale by infiniteTransition.animateFloat(
        initialValue = 0.95f,
        targetValue = 1.05f,
        animationSpec = infiniteRepeatable(
            animation = tween(2000, easing = EaseInOutCubic),
            repeatMode = RepeatMode.Reverse,
        ),
    )
    val glowAlpha by infiniteTransition.animateFloat(
        initialValue = 0.1f,
        targetValue = 0.3f,
        animationSpec = infiniteRepeatable(
            animation = tween(1500, easing = EaseInOutCubic),
            repeatMode = RepeatMode.Reverse,
        ),
    )

    Box(
        modifier = modifier,
        contentAlignment = Alignment.Center,
    ) {
        // Glow ring
        val intensityFactor = intensity / 100f
        Canvas(modifier = Modifier.size(220.dp)) {
            val center = Offset(size.width / 2f, size.height / 2f)
            val radius = size.width / 2f - 8f
            drawCircle(
                color = emotionColor.copy(alpha = glowAlpha * intensityFactor),
                radius = radius * breatheScale,
                center = center,
            )
            drawCircle(
                color = emotionColor.copy(alpha = 0.15f * intensityFactor),
                radius = radius * 1.15f * breatheScale,
                center = center,
                style = Stroke(width = 2f),
            )
        }

        // Avatar circle
        Box(
            modifier = Modifier
                .size(160.dp)
                .clip(CircleShape)
                .background(emotionColor.copy(alpha = 0.2f)),
            contentAlignment = Alignment.Center,
        ) {
            Text(
                "弥",
                style = MaterialTheme.typography.displayLarge,
                color = emotionColor,
            )
        }

        // Inner thought bubble
        if (!innerThought.isNullOrEmpty()) {
            Text(
                text = "「$innerThought」",
                modifier = Modifier
                    .align(Alignment.TopCenter)
                    .offset(y = 32.dp)
                    .clip(RoundedCornerShape(12.dp))
                    .background(MaterialTheme.colorScheme.surface.copy(alpha = 0.9f))
                    .padding(horizontal = 16.dp, vertical = 8.dp),
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
}
