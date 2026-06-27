package ai.miya.android.ui.chat

import ai.miya.shared.ServiceLocator
import ai.miya.shared.api.WsEvent
import ai.miya.shared.model.MiyaEmotion
import ai.miya.shared.model.SessionInfo
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import ai.miya.android.ui.live2d.MiyaLive2DGLView
import ai.miya.android.ui.live2d.MiyaLive2DComposeView
import ai.miya.android.ui.theme.*
import kotlinx.coroutines.flow.collectLatest
import kotlinx.coroutines.launch

data class ChatBubble(
    val content: String,
    val isMiya: Boolean,
    val isStreaming: Boolean = false,
)

@Composable
fun ChatScreen() {
    val scope = rememberCoroutineScope()
    val chatRepo = remember { ServiceLocator.chatRepo }
    val ws = remember { ServiceLocator.webSocket }

    var messages by remember { mutableStateOf(listOf<ChatBubble>()) }
    var inputText by remember { mutableStateOf("") }
    var isStreaming by remember { mutableStateOf(false) }
    var sessions by remember { mutableStateOf<List<SessionInfo>>(emptyList()) }
    var currentSessionId by remember { mutableStateOf<String?>(null) }
    var currentEmotion by remember { mutableStateOf(MiyaEmotion.NEUTRAL) }
    val listState = rememberLazyListState()

    // Live2D 状态：根据 streaming 推断
    val live2dState = when {
        isStreaming && messages.lastOrNull()?.isMiya == true -> MiyaLive2DGLView.Live2DState.TALKING
        isStreaming -> MiyaLive2DGLView.Live2DState.THINKING
        else -> MiyaLive2DGLView.Live2DState.IDLE
    }

    LaunchedEffect(Unit) {
        try {
            sessions = chatRepo.getSessions()
        } catch (_: Exception) { }
    }

    LaunchedEffect(Unit) {
        ws.events.collectLatest { event ->
            when (event) {
                is WsEvent.EmotionChanged -> {
                    currentEmotion = MiyaEmotion.fromDominant(event.dominant)
                }
                else -> {}
            }
        }
    }

    fun sendMessage() {
        val text = inputText.trim()
        if (text.isEmpty() || isStreaming) return

        messages = messages + ChatBubble(content = text, isMiya = false)
        inputText = ""
        isStreaming = true

        val miyaIndex = messages.size
        messages = messages + ChatBubble(content = "", isMiya = true, isStreaming = true)

        scope.launch {
            try {
                val fullResponse = StringBuilder()
                chatRepo.streamChat(text, currentSessionId ?: "default").collect { chunk ->
                    fullResponse.append(chunk)
                    messages = messages.toMutableList().also {
                        if (miyaIndex < it.size) {
                            it[miyaIndex] = it[miyaIndex].copy(
                                content = fullResponse.toString(),
                                isStreaming = true
                            )
                        }
                    }
                }
                messages = messages.toMutableList().also {
                    if (miyaIndex < it.size) {
                        it[miyaIndex] = it[miyaIndex].copy(isStreaming = false)
                    }
                }
                sessions = chatRepo.getSessions()
            } catch (_: Exception) {
                messages = messages.toMutableList().also {
                    if (miyaIndex < it.size && it[miyaIndex].content.isEmpty()) {
                        it[miyaIndex] = it[miyaIndex].copy(
                            content = "连接失败，请检查网络和设置中的主机地址",
                            isStreaming = false
                        )
                    }
                }
            } finally {
                isStreaming = false
            }
        }
    }

    Box(modifier = Modifier.fillMaxSize()) {
        // Layer 1: Live2D 全屏角色
        MiyaLive2DComposeView(
            emotion = currentEmotion,
            state = live2dState,
            modifier = Modifier.fillMaxSize(),
        )

        // Layer 2: 聊天浮层
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(horizontal = 12.dp)
        ) {
            Spacer(modifier = Modifier.weight(0.55f))

            // 消息列表
            LazyColumn(
                modifier = Modifier
                    .weight(0.35f)
                    .fillMaxWidth()
                    .background(
                        MiyaChatBubble,
                        RoundedCornerShape(topStart = 20.dp, topEnd = 20.dp)
                    )
                    .padding(horizontal = 12.dp, vertical = 8.dp),
                state = listState,
            ) {
                items(messages) { msg ->
                    ChatBubbleItem(msg)
                }
            }

            // 输入栏
            InputBar(
                value = inputText,
                onValueChange = { inputText = it },
                onSend = { sendMessage() },
                isStreaming = isStreaming,
                onStop = {
                    scope.launch {
                        chatRepo.stopChat()
                        isStreaming = false
                    }
                },
            )
        }
    }
}

@Composable
fun ChatBubbleItem(msg: ChatBubble) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 4.dp),
        horizontalArrangement = if (msg.isMiya) Arrangement.Start else Arrangement.End
    ) {
        if (msg.isMiya) {
            Icon(
                imageVector = Icons.Filled.Face,
                contentDescription = null,
                modifier = Modifier
                    .size(28.dp)
                    .clip(CircleShape)
                    .background(MiyaSurfaceVariant)
                    .padding(4.dp),
                tint = MiyaPrimary,
            )
            Spacer(modifier = Modifier.width(8.dp))
        }
        Surface(
            shape = RoundedCornerShape(
                topStart = if (msg.isMiya) 4.dp else 16.dp,
                topEnd = if (msg.isMiya) 16.dp else 4.dp,
                bottomStart = 16.dp,
                bottomEnd = 16.dp,
            ),
            color = if (msg.isMiya) MiyaSurfaceVariant else MiyaPrimary.copy(alpha = 0.3f),
            modifier = Modifier.widthIn(max = 280.dp),
        ) {
            Text(
                text = msg.content + if (msg.isStreaming) " ▌" else "",
                color = MiyaTextPrimary,
                fontSize = 15.sp,
                modifier = Modifier.padding(10.dp),
            )
        }
        if (!msg.isMiya) {
            Spacer(modifier = Modifier.width(8.dp))
            Icon(
                imageVector = Icons.Filled.Person,
                contentDescription = null,
                modifier = Modifier
                    .size(28.dp)
                    .clip(CircleShape)
                    .background(MiyaPrimary.copy(alpha = 0.3f))
                    .padding(4.dp),
                tint = MiyaTextPrimary,
            )
        }
    }
}

@Composable
fun InputBar(
    value: String,
    onValueChange: (String) -> Unit,
    onSend: () -> Unit,
    isStreaming: Boolean,
    onStop: () -> Unit,
) {
    Surface(
        modifier = Modifier.fillMaxWidth(),
        color = MiyaChatBubble,
        shape = RoundedCornerShape(bottomStart = 20.dp, bottomEnd = 20.dp),
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 12.dp, vertical = 8.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            IconButton(onClick = { /* 语音输入 */ }) {
                Icon(
                    imageVector = Icons.Filled.Mic,
                    contentDescription = "语音",
                    tint = MiyaTextSecondary,
                )
            }

            OutlinedTextField(
                value = value,
                onValueChange = onValueChange,
                modifier = Modifier.weight(1f),
                placeholder = { Text("和弥娅说点什么...", color = MiyaTextSecondary) },
                colors = OutlinedTextFieldDefaults.colors(
                    focusedContainerColor = MiyaSurface,
                    unfocusedContainerColor = MiyaSurface,
                    focusedBorderColor = MiyaPrimary,
                    unfocusedBorderColor = MiyaBorder,
                    focusedTextColor = MiyaTextPrimary,
                    unfocusedTextColor = MiyaTextPrimary,
                ),
                shape = RoundedCornerShape(24.dp),
                maxLines = 4,
            )

            Spacer(modifier = Modifier.width(8.dp))

            if (isStreaming) {
                IconButton(onClick = onStop) {
                    Icon(
                        imageVector = Icons.Filled.Stop,
                        contentDescription = "停止",
                        tint = MiyaEmotionAngry,
                    )
                }
            } else {
                IconButton(
                    onClick = onSend,
                    enabled = value.isNotBlank()
                ) {
                    Icon(
                        imageVector = Icons.Filled.Send,
                        contentDescription = "发送",
                        tint = if (value.isNotBlank()) MiyaPrimary else MiyaTextSecondary,
                    )
                }
            }
        }
    }
}
