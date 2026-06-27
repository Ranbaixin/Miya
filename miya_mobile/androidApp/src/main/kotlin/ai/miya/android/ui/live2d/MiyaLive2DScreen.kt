package ai.miya.android.ui.live2d

import ai.miya.shared.ServiceLocator
import ai.miya.shared.api.WsEvent
import ai.miya.shared.model.MiyaEmotion
import androidx.compose.animation.core.*
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import ai.miya.android.ui.theme.*
import kotlinx.coroutines.flow.collectLatest

@Composable
fun MiyaLive2DScreen() {
    val ws = remember { ServiceLocator.webSocket }
    var currentEmotion by remember { mutableStateOf(MiyaEmotion.NEUTRAL) }
    var emotionIntensity by remember { mutableIntStateOf(50) }

    LaunchedEffect(Unit) {
        ws.events.collectLatest { event ->
            when (event) {
                is WsEvent.EmotionChanged -> {
                    currentEmotion = MiyaEmotion.fromDominant(event.dominant)
                    emotionIntensity = event.intensity
                }
                else -> {}
            }
        }
    }

    val emotionCol = emotionColor(currentEmotion.name)
    val infiniteTransition = rememberInfiniteTransition(label = "glow")
    val glowAlpha by infiniteTransition.animateFloat(
        0.06f, 0.18f,
        infiniteRepeatable(tween(2000, easing = EaseInOutCubic), RepeatMode.Reverse),
        label = "glow",
    )

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(MiyaBackground),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Spacer(Modifier.weight(0.15f))

        // Live2D 角色区域
        MiyaLive2DComposeView(
            emotion = currentEmotion,
            state = MiyaLive2DGLView.Live2DState.IDLE,
            modifier = Modifier
                .fillMaxWidth()
                .weight(0.5f),
        )

        // 情感信息面板
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 24.dp, vertical = 16.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            Spacer(Modifier.height(12.dp))

            Text(
                text = "弥娅",
                color = MiyaTextPrimary,
                fontSize = 24.sp,
                fontWeight = FontWeight.Bold,
            )

            Spacer(Modifier.height(6.dp))

            Surface(
                color = emotionCol.copy(alpha = 0.15f),
                shape = RoundedCornerShape(20.dp),
            ) {
                Text(
                    text = currentEmotion.displayName,
                    color = emotionCol,
                    fontSize = 16.sp,
                    modifier = Modifier.padding(horizontal = 20.dp, vertical = 6.dp),
                )
            }

            Spacer(Modifier.height(16.dp))

            // 情感强度条
            Text(
                text = "${emotionCol.copy(alpha = 0.5f)} 情感强度 $emotionIntensity%",
                color = emotionCol.copy(alpha = 0.5f),
                fontSize = 11.sp,
                fontFamily = FontFamily.Monospace,
            )
            Spacer(Modifier.height(6.dp))
            LinearProgressIndicator(
                progress = { emotionIntensity / 100f },
                modifier = Modifier
                    .fillMaxWidth(0.6f)
                    .height(4.dp)
                    .clip(RoundedCornerShape(2.dp)),
                color = emotionCol,
                trackColor = MiyaSurfaceVariant,
            )
        }

        Spacer(Modifier.weight(0.15f))
    }
}
