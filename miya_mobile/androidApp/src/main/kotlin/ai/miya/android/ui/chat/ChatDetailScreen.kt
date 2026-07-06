package ai.miya.android.ui.chat

import ai.miya.shared.ServiceLocator
import ai.miya.shared.api.WsEvent
import ai.miya.shared.model.ContentType
import ai.miya.shared.model.MiyaEmotion
import ai.miya.android.ui.theme.LocalMiyaColors
import androidx.compose.animation.animateColorAsState
import androidx.compose.animation.core.*
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.collectLatest
import kotlinx.coroutines.launch
import java.text.SimpleDateFormat
import java.util.*
import kotlin.random.Random

data class ChatMsg(
    val id: String = UUID.randomUUID().toString(),
    val content: String = "",
    val isMiya: Boolean = false,
    val isStreaming: Boolean = false,
    val emotion: String? = null,
    val timestamp: Long = System.currentTimeMillis(),
)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ChatDetailScreen(
    sessionId: String,
    sessionName: String,
    onBack: () -> Unit,
) {
    val colors = LocalMiyaColors.current
    val scope = rememberCoroutineScope()
    val chatRepo = remember { ServiceLocator.chatRepo }
    val ws = remember { ServiceLocator.webSocket }

    var messages by remember { mutableStateOf(
        listOf(
            ChatMsg(
                content = "你好，我是弥娅 \u2764\uFE0F 有什么可以帮你的？",
                isMiya = true,
                timestamp = System.currentTimeMillis() - 60000,
            )
        )
    ) }
    var inputText by remember { mutableStateOf("") }
    var isStreaming by remember { mutableStateOf(false) }
    var currentEmotion by remember { mutableStateOf(MiyaEmotion.NEUTRAL) }
    var isRecording by remember { mutableStateOf(false) }
    val listState = rememberLazyListState()

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

    LaunchedEffect(messages.size) {
        delay(100)
        if (messages.isNotEmpty()) {
            listState.animateScrollToItem(messages.size - 1)
        }
    }

    fun sendMessage() {
        val text = inputText.trim()
        if (text.isEmpty() || isStreaming) return

        messages = messages + ChatMsg(content = text, isMiya = false)
        inputText = ""
        isStreaming = true

        val miyaId = UUID.randomUUID().toString()
        messages = messages + ChatMsg(id = miyaId, content = "", isMiya = true, isStreaming = true)

        scope.launch {
            try {
                val fullResponse = StringBuilder()
                chatRepo.streamChat(text, sessionId).collect { chunk ->
                    fullResponse.append(chunk)
                    messages = messages.toMutableList().also { list ->
                        val idx = list.indexOfFirst { it.id == miyaId }
                        if (idx >= 0) {
                            list[idx] = list[idx].copy(content = fullResponse.toString(), isStreaming = true)
                        }
                    }
                }
                messages = messages.toMutableList().also { list ->
                    val idx = list.indexOfFirst { it.id == miyaId }
                    if (idx >= 0) {
                        list[idx] = list[idx].copy(isStreaming = false, emotion = currentEmotion.name)
                    }
                }
            } catch (_: Exception) {
                messages = messages.toMutableList().also { list ->
                    val idx = list.indexOfFirst { it.id == miyaId }
                    if (idx >= 0 && list[idx].content.isEmpty()) {
                        list[idx] = list[idx].copy(content = "连接失败，请检查网络", isStreaming = false)
                    }
                }
            } finally {
                isStreaming = false
            }
        }
    }

    Scaffold(
        modifier = Modifier.fillMaxSize(),
        containerColor = colors.background,
        contentWindowInsets = WindowInsets.ime,
        topBar = {
            Surface(
                color = colors.background,
                shadowElevation = 0.dp,
            ) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .statusBarsPadding()
                        .padding(horizontal = 4.dp, vertical = 8.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    IconButton(onClick = onBack) {
                        Icon(Icons.Default.ArrowBack, "返回", tint = colors.textPrimary)
                    }
                    Box(
                        modifier = Modifier
                            .size(38.dp)
                            .clip(CircleShape)
                            .background(colors.primary.copy(alpha = 0.15f)),
                        contentAlignment = Alignment.Center,
                    ) {
                        Text("弥", color = colors.primary, fontSize = 16.sp, fontWeight = FontWeight.Bold)
                    }
                    Spacer(Modifier.width(10.dp))
                    Column(modifier = Modifier.weight(1f)) {
                        Text(
                            text = sessionName,
                            color = colors.textPrimary,
                            fontSize = 17.sp,
                            fontWeight = FontWeight.SemiBold,
                        )
                        Text(
                            text = if (isStreaming) "正在输入..." else currentEmotion.displayName,
                            color = if (isStreaming) colors.accent else colors.textSecondary,
                            fontSize = 11.sp,
                        )
                    }
                    IconButton(onClick = { }) {
                        Icon(Icons.Default.MoreVert, "更多", tint = colors.textPrimary)
                    }
                }
            }
            HorizontalDivider(thickness = 0.5.dp, color = colors.divider)
        },
        bottomBar = {
            Surface(
                color = colors.background,
                shadowElevation = 0.dp,
            ) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .navigationBarsPadding()
                        .padding(horizontal = 10.dp, vertical = 8.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    // 语音按钮
                    IconButton(
                        onClick = { isRecording = !isRecording },
                        modifier = Modifier.size(36.dp),
                    ) {
                        Icon(
                            if (isRecording) Icons.Default.Stop else Icons.Default.Mic,
                            contentDescription = "语音",
                            tint = if (isRecording) colors.danger else colors.textSecondary,
                            modifier = Modifier.size(22.dp),
                        )
                    }
                    // 输入框
                    Surface(
                        modifier = Modifier.weight(1f),
                        color = colors.surface,
                        shape = RoundedCornerShape(20.dp),
                    ) {
                        BasicTextField(
                            value = inputText,
                            onValueChange = { inputText = it },
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(horizontal = 14.dp, vertical = 10.dp),
                            textStyle = TextStyle(
                                color = colors.textPrimary,
                                fontSize = 15.sp,
                            ),
                            singleLine = true,
                            decorationBox = { innerTextField ->
                                if (inputText.isEmpty()) {
                                    Text(
                                        "和弥娅说点什么...",
                                        color = colors.textDim,
                                        fontSize = 15.sp,
                                    )
                                }
                                innerTextField()
                            },
                        )
                    }
                    Spacer(Modifier.width(6.dp))
                    // 表情按钮
                    IconButton(onClick = { }, modifier = Modifier.size(36.dp)) {
                        Icon(
                            Icons.Default.EmojiEmotions,
                            contentDescription = "表情",
                            tint = colors.textSecondary,
                            modifier = Modifier.size(22.dp),
                        )
                    }
                    // 更多 / 发送
                    if (inputText.isNotBlank()) {
                        IconButton(
                            onClick = { sendMessage() },
                            modifier = Modifier.size(36.dp),
                        ) {
                            Icon(
                                Icons.Default.Send,
                                contentDescription = "发送",
                                tint = colors.primary,
                                modifier = Modifier.size(22.dp),
                            )
                        }
                    } else {
                        IconButton(
                            onClick = { },
                            modifier = Modifier.size(36.dp),
                        ) {
                            Icon(
                                Icons.Default.Add,
                                contentDescription = "更多",
                                tint = colors.textSecondary,
                                modifier = Modifier.size(22.dp),
                            )
                        }
                    }
                }
            }
        },
    ) { padding ->
        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .background(colors.background),
            state = listState,
        ) {
            item { Spacer(Modifier.height(8.dp)) }
            var lastTime = 0L
            messages.forEachIndexed { index, msg ->
                val gap = if (index > 0) msg.timestamp - lastTime else 0
                if (gap > 5 * 60 * 1000 && lastTime > 0) {
                    item(key = "time_${msg.timestamp}") {
                        TimeLabel(
                            time = formatChatTime(msg.timestamp),
                            modifier = Modifier.fillMaxWidth().padding(vertical = 10.dp),
                        )
                    }
                }
                item(key = msg.id) {
                    ChatBubble(
                        msg = msg,
                        modifier = Modifier.padding(vertical = 2.dp),
                    )
                }
                lastTime = msg.timestamp
            }
            item { Spacer(Modifier.height(8.dp)) }
        }
    }
}

// ═══════════════════════════════════════════════
// 聊天气泡组件
// ═══════════════════════════════════════════════

@Composable
fun ChatBubble(
    msg: ChatMsg,
    modifier: Modifier = Modifier,
) {
    val colors = LocalMiyaColors.current
    val isMiya = msg.isMiya
    val align = if (isMiya) Alignment.Start else Alignment.End
    val bubbleBg = if (isMiya) colors.bubbleMiya else colors.bubbleMe
    val textColor = if (isMiya) colors.textPrimary else Color.White
    val bubbleShape = if (isMiya) {
        RoundedCornerShape(4.dp, 18.dp, 18.dp, 18.dp)
    } else {
        RoundedCornerShape(18.dp, 4.dp, 18.dp, 18.dp)
    }

    Column(
        modifier = modifier.fillMaxWidth().padding(horizontal = 12.dp),
        horizontalAlignment = align,
    ) {
        if (!isMiya) {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.End,
            ) {
                Spacer(Modifier.width(40.dp))
                Column(horizontalAlignment = Alignment.End) {
                    Surface(
                        color = bubbleBg,
                        shape = bubbleShape,
                        shadowElevation = 1.dp,
                    ) {
                        Text(
                            text = msg.content,
                            color = textColor,
                            fontSize = 15.sp,
                            lineHeight = 22.sp,
                            modifier = Modifier.padding(horizontal = 12.dp, vertical = 10.dp),
                        )
                    }
                }
            }
        } else {
            Row(
                verticalAlignment = Alignment.Top,
            ) {
                Box(
                    modifier = Modifier
                        .size(36.dp)
                        .clip(CircleShape)
                        .background(colors.primary.copy(alpha = 0.15f)),
                    contentAlignment = Alignment.Center,
                ) {
                    Text("弥", color = colors.primary, fontSize = 14.sp, fontWeight = FontWeight.Bold)
                }
                Spacer(Modifier.width(8.dp))
                Column {
                    Surface(
                        color = bubbleBg,
                        shape = bubbleShape,
                        shadowElevation = 1.dp,
                    ) {
                        Text(
                            text = msg.content + if (msg.isStreaming) "\u258C" else "",
                            color = textColor,
                            fontSize = 15.sp,
                            lineHeight = 22.sp,
                            modifier = Modifier.padding(horizontal = 12.dp, vertical = 10.dp),
                        )
                    }
                }
                Spacer(Modifier.width(40.dp))
            }
        }
    }
}

@Composable
fun TimeLabel(time: String, modifier: Modifier = Modifier) {
    val colors = LocalMiyaColors.current
    Box(modifier = modifier, contentAlignment = Alignment.Center) {
        Surface(
            color = colors.surface.copy(alpha = 0.6f),
            shape = RoundedCornerShape(4.dp),
        ) {
            Text(
                text = time,
                color = colors.textDim,
                fontSize = 11.sp,
                fontFamily = FontFamily.Monospace,
                modifier = Modifier.padding(horizontal = 10.dp, vertical = 3.dp),
            )
        }
    }
}

private fun formatChatTime(timestamp: Long): String {
    val now = Calendar.getInstance()
    val cal = Calendar.getInstance().apply { timeInMillis = timestamp }
    return if (now.get(Calendar.DAY_OF_YEAR) == cal.get(Calendar.DAY_OF_YEAR)) {
        SimpleDateFormat("HH:mm", Locale.getDefault()).format(Date(timestamp))
    } else {
        SimpleDateFormat("MM-dd HH:mm", Locale.getDefault()).format(Date(timestamp))
    }
}
