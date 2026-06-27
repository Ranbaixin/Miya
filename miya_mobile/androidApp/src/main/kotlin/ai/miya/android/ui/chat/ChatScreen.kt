package ai.miya.android.ui.chat

import ai.miya.shared.ServiceLocator
import ai.miya.shared.api.WsEvent
import ai.miya.shared.model.ContentType
import ai.miya.shared.model.MiyaEmotion
import ai.miya.shared.model.SessionInfo
import androidx.compose.animation.animateColorAsState
import androidx.compose.animation.core.*
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.gestures.detectTapGestures
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
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.draw.drawWithContent
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Rect
import androidx.compose.ui.geometry.RoundRect
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.*
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.drawscope.clipRect
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.layout.onSizeChanged
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.IntSize
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import ai.miya.android.ui.theme.*
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.collectLatest
import kotlinx.coroutines.launch
import kotlin.random.Random
import coil.compose.AsyncImage
import coil.request.ImageRequest
import androidx.compose.ui.platform.LocalContext

// ═══════════════════════════════════════════════
// 消息气泡数据模型
// ═══════════════════════════════════════════════

data class ChatBubble(
    val id: String = java.util.UUID.randomUUID().toString(),
    val contentType: ContentType = ContentType.TEXT,
    val content: String = "",
    val isMiya: Boolean = false,
    val isStreaming: Boolean = false,
    val emotion: String? = null,
    val imageUrl: String? = null,
    val thumbnailUrl: String? = null,
    val imageWidth: Int = 0,
    val imageHeight: Int = 0,
    val stickerId: String? = null,
    val stickerUrl: String? = null,
    val voiceUrl: String? = null,
    val voiceDuration: Int = 0,
    val quoteContent: String? = null,
    val quoteSender: String? = null,
    val timestamp: Long = System.currentTimeMillis(),
)

// ═══════════════════════════════════════════════
// PGR 风格形状与动画工具
// ═══════════════════════════════════════════════

val PGR_CLIP_DP = 8f

fun PGRClipPath(size: Size, clipDp: Float = PGR_CLIP_DP): Path {
    val w = size.width
    val h = size.height
    return Path().apply {
        moveTo(0f, clipDp)
        lineTo(clipDp, 0f)
        lineTo(w, 0f)
        lineTo(w, h - clipDp)
        lineTo(w - clipDp, h)
        lineTo(clipDp, h)
        lineTo(0f, h - clipDp)
        close()
    }
}

fun Modifier.pgrClipBackground(color: Color): Modifier = this.drawBehind {
    drawPath(
        path = PGRClipPath(size),
        color = color,
    )
}

fun Modifier.pgrBracket(size: Size, color: Color, strokeWidth: Float = 1.5f): Modifier =
    this.drawWithContent {
        drawContent()
        val c = color
        val sw = strokeWidth * density
        val clip = PGR_CLIP_DP * density
        val w = size.width
        val h = size.height
        val cornerLen = 12f * density

        // 左上 bracket
        drawLine(c, Offset(0f, clip + cornerLen), Offset(0f, clip), sw)
        drawLine(c, Offset(0f, clip), Offset(cornerLen, clip), sw)
        // 左下 bracket
        drawLine(c, Offset(0f, h - clip - cornerLen), Offset(0f, h - clip), sw)
        drawLine(c, Offset(0f, h - clip), Offset(cornerLen, h - clip), sw)
        // 右上 bracket (细)
        val sw2 = sw * 0.5f
        drawLine(c, Offset(w, clip + cornerLen), Offset(w, clip), sw2)
        drawLine(c, Offset(w, clip), Offset(w - cornerLen, clip), sw2)
        // 右下 bracket
        drawLine(c, Offset(w, h - clip - cornerLen), Offset(w, h - clip), sw2)
        drawLine(c, Offset(w, h - clip), Offset(w - cornerLen, h - clip), sw2)
    }

@Composable
fun Modifier.pgrGlossSweep(
    color: Color = Color.White,
    durationMs: Int = 4500,
    randomDelay: Boolean = true,
): Modifier {
    val delayFraction = remember { if (randomDelay) Random.nextFloat() else 0.5f }
    val infiniteTransition = rememberInfiniteTransition(label = "gloss")
    val progress by infiniteTransition.animateFloat(
        initialValue = 0f,
        targetValue = 2.5f,
        animationSpec = infiniteRepeatable(
            animation = tween(durationMs, easing = LinearEasing),
            repeatMode = RepeatMode.Restart,
        ),
        label = "glossProgress",
    )

    return this.drawWithContent {
        drawContent()

        val sweepX = (progress - delayFraction) * size.width * 2f
        val glossWidth = 80f * density

        clipRect(left = maxOf(0f, sweepX - glossWidth), right = minOf(size.width, sweepX)) {
            drawRect(
                brush = Brush.linearGradient(
                    colors = listOf(
                        color.copy(alpha = 0f),
                        color.copy(alpha = 0.12f),
                        color.copy(alpha = 0.06f),
                        color.copy(alpha = 0f),
                    ),
                    start = Offset(sweepX - glossWidth, 0f),
                    end = Offset(sweepX, 0f),
                ),
                size = size,
            )
        }
    }
}

@Composable
fun PGRBubbleSurface(
    modifier: Modifier = Modifier,
    color: Color = MiyaSurfaceVariant,
    borderColor: Color = MiyaBorder.copy(alpha = 0.3f),
    content: @Composable () -> Unit,
) {
    Box(
        modifier = modifier
            .drawBehind {
                val path = PGRClipPath(size)
                drawPath(path, color)
                drawPath(path, borderColor, style = Stroke(1f * density))
            }
            .padding(1.dp),
        contentAlignment = Alignment.Center,
    ) {
        content()
    }
}

@Composable
fun SciFiHUDOverlay(modifier: Modifier = Modifier) {
    val hexChars = remember { (1..60).map { Random.nextInt(0, 16).toString(16).uppercase() } }
    val blinkingDots = remember { (1..10).map { Random.nextFloat() } }
    val infiniteTransition = rememberInfiniteTransition(label = "hud")
    val scanProgress by infiniteTransition.animateFloat(
        0f, 1f, infiniteRepeatable(tween(3000, easing = LinearEasing)), label = "scan",
    )

    Box(modifier = modifier.fillMaxSize()) {
        androidx.compose.foundation.Canvas(Modifier.fillMaxSize()) {
            val alpha = 0.12f
            hexChars.forEachIndexed { i, ch ->
                val x = (0.05f + (i * 0.016f % 0.9f)) * size.width
                val y = (0.02f + i * 0.028f % 0.95f) * size.height
                drawContext.canvas.nativeCanvas.drawText(
                    ch, x, y,
                    android.graphics.Paint().apply {
                        color = android.graphics.Color.argb((alpha * 255).toInt(), 0, 255, 245)
                        textSize = 10f * density
                        typeface = android.graphics.Typeface.MONOSPACE
                    }
                )
            }
        }
    }
}

// ═══════════════════════════════════════════════
// 主聊天屏幕
// ═══════════════════════════════════════════════

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
    var showStickerPicker by remember { mutableStateOf(false) }
    var showImagePicker by remember { mutableStateOf(false) }
    var quotedBubble by remember { mutableStateOf<ChatBubble?>(null) }
    val listState = rememberLazyListState()
    val imagePicker = rememberImagePicker()

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

    LaunchedEffect(messages.size) {
        delay(100)
        if (messages.isNotEmpty()) {
            listState.animateScrollToItem(messages.size - 1)
        }
    }

    LaunchedEffect(imagePicker.selectedImageUri) {
        val uri = imagePicker.selectedImageUri ?: return@LaunchedEffect
        val imageMsg = ChatBubble(
            contentType = ContentType.IMAGE,
            content = "[图片]",
            imageUrl = uri.toString(),
            isMiya = false,
            timestamp = System.currentTimeMillis(),
        )
        messages = messages + imageMsg
        imagePicker.onClearSelected()
        showImagePicker = false

        scope.launch {
            try {
                val fullResponse = StringBuilder()
                chatRepo.streamChat("[用户发送了一张图片]", currentSessionId ?: "default").collect { chunk ->
                    fullResponse.append(chunk)
                }
            } catch (_: Exception) { }
        }
    }

    fun sendMessage() {
        if (isStreaming) return

        val hasContent = when {
            inputText.trim().isNotEmpty() -> true
            else -> false
        }
        if (!hasContent) return

        val msg = ChatBubble(
            content = inputText.trim(),
            isMiya = false,
            timestamp = System.currentTimeMillis(),
            quoteContent = quotedBubble?.content?.take(50),
            quoteSender = if (quotedBubble?.isMiya == true) "弥娅" else "你",
        )
        messages = messages + msg
        val userText = inputText.trim()
        inputText = ""
        quotedBubble = null
        isStreaming = true

        val miyaId = java.util.UUID.randomUUID().toString()
        messages = messages + ChatBubble(
            id = miyaId,
            content = "",
            isMiya = true,
            isStreaming = true,
            timestamp = System.currentTimeMillis(),
        )

        scope.launch {
            try {
                val fullResponse = StringBuilder()
                chatRepo.streamChat(userText, currentSessionId ?: "default").collect { chunk ->
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
                sessions = chatRepo.getSessions()
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

    fun sendSticker(stickerId: String, stickerUrl: String) {
        messages = messages + ChatBubble(
            contentType = ContentType.STICKER,
            stickerId = stickerId,
            stickerUrl = stickerUrl,
            isMiya = false,
            timestamp = System.currentTimeMillis(),
        )
        showStickerPicker = false
        scope.launch {
            try {
                val fullResponse = StringBuilder()
                chatRepo.streamChat("[表情:$stickerId]", currentSessionId ?: "default").collect { chunk ->
                    fullResponse.append(chunk)
                }
            } catch (_: Exception) { }
        }
    }

    Box(modifier = Modifier.fillMaxSize().background(MiyaBackground)) {
        // 聊天全屏
        Column(
            modifier = Modifier
                .fillMaxSize()
                .systemBarsPadding()
                .navigationBarsPadding()
        ) {
            // 顶部状态栏
            ChatTopBar(
                currentEmotion = currentEmotion,
                sessionName = sessions.find { it.id == currentSessionId }?.name ?: "弥娅",
                isStreaming = isStreaming,
            )

            // 消息列表 (占满剩余空间)
            LazyColumn(
                modifier = Modifier
                    .weight(1f)
                    .fillMaxWidth(),
                state = listState,
                reverseLayout = false,
            ) {
                item { Spacer(Modifier.height(8.dp)) }
                val groupedMsgs = groupMessagesByTime(messages)
                groupedMsgs.forEach { entry ->
                    if (entry.isTimeDivider) {
                        item {
                            TimeDivider(
                                text = formatTimeLabel(entry.timestamp),
                                modifier = Modifier.fillMaxWidth().padding(vertical = 8.dp),
                            )
                        }
                    } else {
                        items(entry.messages) { msg ->
                            when (msg.contentType) {
                                ContentType.STICKER -> StickerBubbleItem(msg)
                                ContentType.IMAGE -> ImageBubbleItem(msg)
                                else -> ChatBubbleItem(msg, onLongPress = { quotedBubble = msg })
                            }
                            Spacer(Modifier.height(4.dp))
                        }
                    }
                }
                item { Spacer(Modifier.height(4.dp)) }
            }

            // 引用预览条
            quotedBubble?.let { quoted ->
                QuotePreviewBar(
                    quoteSender = if (quoted.isMiya) "弥娅" else "你",
                    quoteContent = quoted.content.ifEmpty { "[表情]" },
                    onDismiss = { quotedBubble = null },
                )
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
                onStickerClick = { showStickerPicker = !showStickerPicker },
                onImageClick = { showImagePicker = true },
            )
        }

        // 表情包面板
        if (showStickerPicker) {
            StickerPickerPanel(
                onStickerSelected = { id, url -> sendSticker(id, url) },
                onDismiss = { showStickerPicker = false },
                modifier = Modifier.align(Alignment.BottomCenter),
            )
        }

        // 图片选择面板
        if (showImagePicker) {
            ImageSourceSheet(
                onDismiss = { showImagePicker = false },
                onCamera = { imagePicker.onLaunchCamera() },
                onGallery = { imagePicker.onLaunchGallery() },
            )
        }
    }
}

// ═══════════════════════════════════════════════
// 消息分组 (按时间)
// ═══════════════════════════════════════════════

data class MessageGroup(
    val messages: List<ChatBubble>,
    val timestamp: Long,
    val isTimeDivider: Boolean,
)

fun groupMessagesByTime(messages: List<ChatBubble>): List<MessageGroup> {
    if (messages.isEmpty()) return emptyList()
    val result = mutableListOf<MessageGroup>()
    var lastTime = 0L
    val currentGroup = mutableListOf<ChatBubble>()

    for (msg in messages) {
        val gap = msg.timestamp - lastTime
        if (lastTime > 0 && gap > 5 * 60 * 1000) {
            if (currentGroup.isNotEmpty()) {
                result.add(MessageGroup(currentGroup.toList(), currentGroup.first().timestamp, false))
                currentGroup.clear()
            }
            result.add(MessageGroup(emptyList(), msg.timestamp, true))
        }
        currentGroup.add(msg)
        lastTime = msg.timestamp
    }
    if (currentGroup.isNotEmpty()) {
        result.add(MessageGroup(currentGroup.toList(), currentGroup.first().timestamp, false))
    }
    return result
}

fun formatTimeLabel(timestamp: Long): String {
    val sdf = java.text.SimpleDateFormat("HH:mm", java.util.Locale.getDefault())
    val now = java.util.Calendar.getInstance()
    val cal = java.util.Calendar.getInstance().apply { timeInMillis = timestamp }
    return if (now.get(java.util.Calendar.DAY_OF_YEAR) == cal.get(java.util.Calendar.DAY_OF_YEAR)) {
        sdf.format(java.util.Date(timestamp))
    } else {
        java.text.SimpleDateFormat("MM-dd HH:mm", java.util.Locale.getDefault()).format(java.util.Date(timestamp))
    }
}

@Composable
fun TimeDivider(text: String, modifier: Modifier = Modifier) {
    Box(modifier = modifier, contentAlignment = Alignment.Center) {
        Text(
            text = text,
            color = MiyaTextSecondary,
            fontSize = 11.sp,
            fontFamily = FontFamily.Monospace,
            modifier = Modifier
                .background(MiyaSurfaceDeep, RoundedCornerShape(8.dp))
                .padding(horizontal = 10.dp, vertical = 3.dp),
        )
    }
}

// ═══════════════════════════════════════════════
// 聊天气泡组件
// ═══════════════════════════════════════════════

@Composable
fun ChatBubbleItem(msg: ChatBubble, onLongPress: () -> Unit = {}) {
    val isMiya = msg.isMiya
    val emotionKey = msg.emotion ?: "neutral"
    val bubbleColor = if (isMiya) MiyaSurfaceDeep else MiyaPrimary.copy(alpha = 0.18f)
    val borderColor = if (isMiya) MiyaBorder.copy(alpha = 0.25f) else MiyaPrimary.copy(alpha = 0.4f)
    val textColor = if (isMiya) MiyaAccent.copy(alpha = 0.85f) else MiyaTextPrimary
    val emotionCol = emotionColor(emotionKey)

    Column(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 3.dp),
        horizontalAlignment = if (isMiya) Alignment.Start else Alignment.End,
    ) {
        // 发送者标签
        Row(verticalAlignment = Alignment.CenterVertically) {
            if (isMiya) {
                Spacer(Modifier.width(4.dp))
                // 情绪光带 (仅 AI 消息显示)
                Box(
                    modifier = Modifier
                        .width(24.dp)
                        .height(3.dp)
                        .background(emotionCol, RoundedCornerShape(2.dp))
                )
                Spacer(Modifier.width(6.dp))
                Text(
                    text = "MIYA",
                    color = MiyaAccent.copy(alpha = 0.6f),
                    fontSize = 9.sp,
                    fontFamily = FontFamily.Monospace,
                    letterSpacing = 1.sp,
                )
                Spacer(Modifier.width(6.dp))
                Text(
                    text = emotionKey.uppercase(),
                    color = emotionCol.copy(alpha = 0.7f),
                    fontSize = 8.sp,
                    fontFamily = FontFamily.Monospace,
                )
            } else {
                Text(
                    text = "YOU",
                    color = MiyaPrimary.copy(alpha = 0.6f),
                    fontSize = 9.sp,
                    fontFamily = FontFamily.Monospace,
                    letterSpacing = 1.sp,
                )
                Spacer(Modifier.width(4.dp))
            }
        }

        Spacer(Modifier.height(3.dp))

        // 气泡主体
        Box(
            modifier = Modifier
                .widthIn(max = 300.dp)
                .pointerInput(Unit) { detectTapGestures(onLongPress = { onLongPress() }) }
                .drawBehind {
                    val path = PGRClipPath(size)
                    drawPath(path, bubbleColor)
                    drawPath(path, borderColor, style = Stroke(1f * density))
                }
                .pgrGlossSweep(color = if (isMiya) MiyaAccent else Color.White, durationMs = 5500)
                .padding(horizontal = 12.dp, vertical = 8.dp),
        ) {
            Column {
                // 引用块
                if (msg.quoteContent != null) {
                    QuoteInline(
                        content = msg.quoteContent,
                        sender = msg.quoteSender ?: "",
                        modifier = Modifier.padding(bottom = 6.dp),
                    )
                }
                // 文本内容
                Text(
                    text = msg.content + if (msg.isStreaming) " \u258C" else "",
                    color = textColor,
                    fontSize = 14.sp,
                    lineHeight = 20.sp,
                )
            }
        }
    }
}

@Composable
fun QuoteInline(content: String, sender: String, modifier: Modifier = Modifier) {
    Column(
        modifier = modifier
            .fillMaxWidth()
            .drawBehind {
                drawRect(MiyaBorder.copy(alpha = 0.4f), topLeft = Offset(0f, 0f), size = Size(3f * density, size.height))
            }
            .padding(start = 8.dp),
    ) {
        Text(
            text = sender,
            color = MiyaAccent.copy(alpha = 0.7f),
            fontSize = 10.sp,
            fontFamily = FontFamily.Monospace,
        )
        Text(
            text = content,
            color = MiyaTextSecondary,
            fontSize = 12.sp,
            maxLines = 2,
            overflow = TextOverflow.Ellipsis,
        )
    }
}

@Composable
fun QuotePreviewBar(
    quoteSender: String,
    quoteContent: String,
    onDismiss: () -> Unit,
) {
    Surface(
        modifier = Modifier.fillMaxWidth(),
        color = MiyaSurfaceDeep,
        shape = RoundedCornerShape(topStart = 12.dp, topEnd = 12.dp),
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 12.dp, vertical = 6.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Box(
                modifier = Modifier
                    .width(3.dp)
                    .height(28.dp)
                    .background(MiyaAccent, RoundedCornerShape(2.dp))
            )
            Spacer(Modifier.width(8.dp))
            Column(modifier = Modifier.weight(1f)) {
                Text(quoteSender, color = MiyaAccent, fontSize = 11.sp, fontWeight = FontWeight.Bold)
                Text(quoteContent, color = MiyaTextSecondary, fontSize = 12.sp, maxLines = 1, overflow = TextOverflow.Ellipsis)
            }
            IconButton(onClick = onDismiss, modifier = Modifier.size(28.dp)) {
                Icon(Icons.Filled.Close, "取消引用", tint = MiyaTextSecondary, modifier = Modifier.size(16.dp))
            }
        }
    }
}

// ═══════════════════════════════════════════════
// 表情包气泡
// ═══════════════════════════════════════════════

@Composable
fun StickerBubbleItem(msg: ChatBubble) {
    val isMiya = msg.isMiya
    val align = if (isMiya) Alignment.CenterStart else Alignment.CenterEnd
    val stickerEmoji = remember(msg.stickerId) {
        miyaStickers.find { it.id == msg.stickerId }?.emoji ?: "😊"
    }

    Box(
        modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp),
        contentAlignment = align,
    ) {
        if (msg.stickerUrl != null && (msg.stickerUrl.startsWith("http://") || msg.stickerUrl.startsWith("https://"))) {
            AsyncImage(
                model = msg.stickerUrl,
                contentDescription = "表情",
                modifier = Modifier
                    .size(100.dp)
                    .clip(RoundedCornerShape(12.dp)),
            )
        } else {
            Box(
                modifier = Modifier
                    .size(72.dp)
                    .background(MiyaSurface, RoundedCornerShape(12.dp)),
                contentAlignment = Alignment.Center,
            ) {
                Text(text = stickerEmoji, fontSize = 40.sp)
            }
        }
    }
}

// ═══════════════════════════════════════════════
// 图片气泡
// ═══════════════════════════════════════════════

@Composable
fun ImageBubbleItem(msg: ChatBubble) {
    val isMiya = msg.isMiya
    val align = if (isMiya) Alignment.CenterStart else Alignment.CenterEnd
    val context = LocalContext.current
    val borderColor = if (isMiya) MiyaBorder.copy(alpha = 0.25f) else MiyaPrimary.copy(alpha = 0.4f)

    Box(
        modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp),
        contentAlignment = align,
    ) {
        Box(
            modifier = Modifier
                .widthIn(max = 240.dp)
                .heightIn(max = 280.dp)
                .drawBehind {
                    val path = PGRClipPath(size)
                    drawPath(path, borderColor, style = Stroke(1.5f * density))
                }
                .padding(1.5f.dp),
        ) {
            val imageModel = msg.imageUrl?.let { url ->
                if (url.startsWith("http://") || url.startsWith("https://")) {
                    url
                } else {
                    null
                }
            }
            if (imageModel != null) {
                AsyncImage(
                    model = ImageRequest.Builder(context)
                        .data(imageModel)
                        .crossfade(true)
                        .build(),
                    contentDescription = "图片",
                    modifier = Modifier.fillMaxWidth(),
                    contentScale = ContentScale.FillWidth,
                )
            } else if (msg.imageUrl != null) {
                AsyncImage(
                    model = msg.imageUrl,
                    contentDescription = "图片",
                    modifier = Modifier.fillMaxWidth(),
                    contentScale = ContentScale.FillWidth,
                )
            } else {
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(120.dp)
                        .background(MiyaSurface),
                    contentAlignment = Alignment.Center,
                ) {
                    Icon(
                        Icons.Filled.BrokenImage,
                        contentDescription = "图片加载失败",
                        tint = MiyaTextSecondary,
                        modifier = Modifier.size(32.dp),
                    )
                }
            }
        }
    }
}

// ═══════════════════════════════════════════════
// 顶部栏 (QQ 风格)
// ═══════════════════════════════════════════════

@Composable
fun ChatTopBar(
    currentEmotion: MiyaEmotion,
    sessionName: String,
    isStreaming: Boolean,
) {
    val emotionCol = emotionColor(currentEmotion.name)

    Surface(
        modifier = Modifier.fillMaxWidth(),
        color = MiyaBackground.copy(alpha = 0.85f),
        tonalElevation = 0.dp,
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 16.dp, vertical = 12.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Text(
                text = sessionName,
                color = MiyaTextPrimary,
                fontSize = 18.sp,
                fontWeight = FontWeight.SemiBold,
            )
            Spacer(Modifier.width(8.dp))
            Text(
                text = if (isStreaming) "正在输入..." else currentEmotion.displayName,
                color = if (isStreaming) MiyaAccent else emotionCol.copy(alpha = 0.7f),
                fontSize = 12.sp,
            )
            if (isStreaming) {
                Spacer(Modifier.width(6.dp))
                Box(
                    modifier = Modifier
                        .size(6.dp)
                        .background(MiyaAccent, CircleShape)
                )
            }
        }
    }
}

// ═══════════════════════════════════════════════
// 输入栏
// ═══════════════════════════════════════════════

@Composable
fun InputBar(
    value: String,
    onValueChange: (String) -> Unit,
    onSend: () -> Unit,
    isStreaming: Boolean,
    onStop: () -> Unit,
    onStickerClick: () -> Unit,
    onImageClick: () -> Unit,
) {
    Surface(
        modifier = Modifier.fillMaxWidth(),
        color = MiyaSurfaceDeep,
        shape = RoundedCornerShape(bottomStart = 20.dp, bottomEnd = 20.dp),
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 10.dp, vertical = 7.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            // 图片按钮
            IconButton(onClick = onImageClick, modifier = Modifier.size(36.dp)) {
                Icon(Icons.Filled.Image, "图片", tint = MiyaTextSecondary, modifier = Modifier.size(20.dp))
            }

            // 表情按钮
            IconButton(onClick = onStickerClick, modifier = Modifier.size(36.dp)) {
                Icon(Icons.Filled.EmojiEmotions, "表情", tint = MiyaTextSecondary, modifier = Modifier.size(20.dp))
            }

            // 语音按钮
            IconButton(onClick = { /* 语音输入 */ }, modifier = Modifier.size(36.dp)) {
                Icon(Icons.Filled.Mic, "语音", tint = MiyaTextSecondary, modifier = Modifier.size(20.dp))
            }

            // 文本输入
            OutlinedTextField(
                value = value,
                onValueChange = onValueChange,
                modifier = Modifier.weight(1f).heightIn(max = 120.dp),
                placeholder = {
                    Text("和弥娅说点什么...", color = MiyaTextSecondary, fontSize = 13.sp)
                },
                colors = OutlinedTextFieldDefaults.colors(
                    focusedContainerColor = MiyaBackground,
                    unfocusedContainerColor = MiyaBackground,
                    focusedBorderColor = MiyaPrimary,
                    unfocusedBorderColor = MiyaBorderDim,
                    focusedTextColor = MiyaTextPrimary,
                    unfocusedTextColor = MiyaTextPrimary,
                    cursorColor = MiyaAccent,
                ),
                shape = RoundedCornerShape(22.dp),
                maxLines = 4,
                textStyle = androidx.compose.ui.text.TextStyle(fontSize = 14.sp),
            )

            Spacer(Modifier.width(6.dp))

            if (isStreaming) {
                IconButton(onClick = onStop) {
                    Icon(Icons.Filled.Stop, "停止", tint = MiyaEmotionColors.anger, modifier = Modifier.size(22.dp))
                }
            } else {
                IconButton(
                    onClick = onSend,
                    enabled = value.isNotBlank(),
                ) {
                    Icon(
                        Icons.Filled.Send,
                        "发送",
                        tint = if (value.isNotBlank()) MiyaPrimary else MiyaTextSecondary,
                        modifier = Modifier.size(22.dp),
                    )
                }
            }
        }
    }
}
