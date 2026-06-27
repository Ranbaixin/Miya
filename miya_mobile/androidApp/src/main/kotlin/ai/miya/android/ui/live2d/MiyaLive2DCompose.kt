package ai.miya.android.ui.live2d

import ai.miya.shared.model.MiyaEmotion
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.viewinterop.AndroidView
import ai.miya.android.ui.theme.*

/**
 * Live2D Compose 组件
 *
 * 将 MiyaLive2DGLView 包装为 Compose 可用的组件。
 * 全屏背景渲染，根据情感状态切换表情。
 */
@Composable
fun MiyaLive2DComposeView(
    emotion: MiyaEmotion,
    state: MiyaLive2DGLView.Live2DState,
    modifier: Modifier = Modifier,
) {
    val context = LocalContext.current
    val glView = remember { MiyaLive2DGLView(context) }

    // 情感变化 → 更新 Live2D 表情
    LaunchedEffect(emotion) {
        glView.setEmotion(emotion.live2dKey)
    }

    // 状态变化 → 更新动画状态
    LaunchedEffect(state) {
        glView.setState(state)
        when (state) {
            MiyaLive2DGLView.Live2DState.TALKING -> {
                glView.setMouthOpen(0.6f)
            }
            MiyaLive2DGLView.Live2DState.IDLE -> {
                glView.setMouthOpen(0f)
                glView.startRandomMotion()
            }
            MiyaLive2DGLView.Live2DState.THINKING -> {
                glView.setMouthOpen(0f)
            }
        }
    }

    AndroidView(
        factory = { glView },
        modifier = modifier.fillMaxSize(),
        update = { view ->
            // 模型路径：assets 或本地文件
            // 部署模型到 android assets: miya_frontend/public/models/弥娅/Miya/
            val modelPath = "models/miya-model/01.model3.json"
            if (view.tag != modelPath) {
                view.tag = modelPath
                view.loadModel(modelPath)
            }
        }
    )
}

/**
 * Live2D 角色 + 聊天浮层 完整布局
 *
 * 用于 ChatScreen 的根布局：Live2D 全屏 + 底部聊天浮层
 */
@Composable
fun Live2DChatLayout(
    emotion: MiyaEmotion,
    state: MiyaLive2DGLView.Live2DState,
    chatContent: @Composable (Modifier) -> Unit,
    modifier: Modifier = Modifier,
) {
    Box(modifier = modifier.fillMaxSize()) {
        // Layer 1: Live2D 全屏角色
        MiyaLive2DComposeView(
            emotion = emotion,
            state = state,
            modifier = Modifier.fillMaxSize(),
        )

        // Layer 2: 聊天浮层（底部区域）
        Box(
            modifier = Modifier
                .align(androidx.compose.ui.Alignment.BottomCenter)
                .fillMaxWidth()
        ) {
            chatContent(Modifier.fillMaxWidth())
        }
    }
}
