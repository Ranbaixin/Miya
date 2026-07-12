package ai.miya.feature.chat

import ai.miya.uicommon.component.MiyaChatAvatar
import ai.miya.uicommon.component.pulseGlow
import ai.miya.uicommon.theme.LocalMiyaTheme
import ai.miya.uicommon.theme.MiyaColors
import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.animation.*
import androidx.compose.animation.core.*
import androidx.compose.foundation.ExperimentalFoundationApi
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.combinedClickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.automirrored.filled.Send
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalClipboardManager
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalFocusManager
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.text.SpanStyle
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.buildAnnotatedString
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.text.withStyle
import androidx.compose.ui.unit.DpOffset
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import coil.compose.AsyncImage
import coil.request.ImageRequest

@Composable
fun ChatScreen(
    sessionId: String = "default",
    onBack: (() -> Unit)? = null,
) {
    val viewModel = androidx.lifecycle.viewmodel.compose.viewModel<ChatViewModel>()
    LaunchedEffect(sessionId) { viewModel.selectSession(sessionId); viewModel.init() }
    ChatContent(viewModel, onBack)
}

@OptIn(ExperimentalFoundationApi::class)
@Composable
private fun ChatContent(viewModel: ChatViewModel, onBack: (() -> Unit)?) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val listState = rememberLazyListState()
    val focusManager = LocalFocusManager.current
    val context = LocalContext.current
    val clipboard = LocalClipboardManager.current

    val atBottom by remember {
        derivedStateOf {
            val last = listState.layoutInfo.visibleItemsInfo.lastOrNull()?.index ?: 0
            last >= listState.layoutInfo.totalItemsCount - 2
        }
    }

    LaunchedEffect(state.messages.size) { listState.animateScrollToItem(listState.layoutInfo.totalItemsCount) }
    LaunchedEffect(state.streamedText) { if (atBottom) listState.animateScrollToItem(listState.layoutInfo.totalItemsCount) }

    val imagePicker = rememberLauncherForActivityResult(ActivityResultContracts.GetContent()) { uri: Uri? ->
        uri?.let { viewModel.sendWithImage(context, it) }
    }
    val filePicker = rememberLauncherForActivityResult(ActivityResultContracts.GetContent()) { uri: Uri? ->
        uri?.let { viewModel.sendWithTextFile(context, it) }
    }

    // Context menu state
    var contextMenuMessage by remember { mutableStateOf<ChatMessage?>(null) }

    Box(modifier = Modifier.fillMaxSize()) {

        // Top bar with back button
        if (onBack != null) {
            Row(
                Modifier.fillMaxWidth().statusBarsPadding().padding(horizontal = 4.dp, vertical = 2.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                IconButton(onClick = onBack, modifier = Modifier.size(36.dp)) {
                    Icon(Icons.AutoMirrored.Filled.ArrowBack, "返回", tint = MaterialTheme.colorScheme.onSurface)
                }
                Spacer(Modifier.width(4.dp))
                Text(
                    state.sessions.find { it.id == state.currentSessionId }?.displayName ?: "聊天",
                    style = MaterialTheme.typography.titleSmall,
                    fontWeight = FontWeight.Medium,
                    color = MaterialTheme.colorScheme.onSurface,
                )
            }
        }

        // Session pill (only when no back button)
        if (onBack == null && state.sessions.size > 1) {
            val name = state.sessions.find { it.id == state.currentSessionId }?.displayName ?: "聊天"
            Surface(
                color = Color(0xFF2D2228).copy(alpha = 0.85f),
                shape = RoundedCornerShape(12.dp),
                modifier = Modifier.align(Alignment.TopCenter).statusBarsPadding().padding(top = 8.dp),
            ) {
                Row(
                    Modifier.clickable { viewModel.toggleSessionPicker() }.padding(horizontal = 14.dp, vertical = 6.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Text(name, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    Spacer(Modifier.width(4.dp))
                    Icon(Icons.Default.ExpandMore, null, tint = MaterialTheme.colorScheme.onSurfaceVariant, modifier = Modifier.size(14.dp))
                }
            }
        }

        // Session picker dropdown
        AnimatedVisibility(
            visible = state.showSessionPicker,
            enter = fadeIn(tween(200)) + scaleIn(tween(200)),
            exit = fadeOut(tween(150)) + scaleOut(tween(150)),
            modifier = Modifier.align(Alignment.TopCenter).statusBarsPadding().padding(top = 50.dp),
        ) {
            Surface(color = Color(0xFF2D2228), shape = RoundedCornerShape(14.dp), tonalElevation = 8.dp, modifier = Modifier.widthIn(max = 280.dp)) {
                Column(Modifier.padding(12.dp)) {
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                        Text("会话", style = MaterialTheme.typography.titleSmall)
                        IconButton(onClick = { viewModel.newSession() }, modifier = Modifier.size(28.dp)) {
                            Icon(Icons.Default.Add, "新建", tint = MiyaColors.Primary, modifier = Modifier.size(16.dp))
                        }
                    }
                    Spacer(Modifier.height(4.dp))
                    state.sessions.take(5).forEach { s ->
                        Row(
                            Modifier.fillMaxWidth().clip(RoundedCornerShape(8.dp)).clickable { viewModel.selectSession(s.id) }
                                .background(if (s.id == state.currentSessionId) MiyaColors.Primary.copy(alpha = 0.1f) else Color.Transparent)
                                .padding(horizontal = 10.dp, vertical = 8.dp),
                            verticalAlignment = Alignment.CenterVertically,
                        ) {
                            Column(Modifier.weight(1f)) {
                                Text(s.displayName ?: s.name ?: s.id, style = MaterialTheme.typography.bodyMedium, maxLines = 1)
                                if (s.messageCount != null) Text("${s.messageCount}条", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                            }
                            if (s.id == state.currentSessionId) Icon(Icons.Default.Check, null, tint = MiyaColors.Primary, modifier = Modifier.size(14.dp))
                            if (s.id != "default") {
                                IconButton(onClick = { viewModel.deleteSession(s.id) }, modifier = Modifier.size(24.dp)) {
                                    Icon(Icons.Default.Close, "删除", modifier = Modifier.size(12.dp), tint = MaterialTheme.colorScheme.onSurfaceVariant)
                                }
                            }
                        }
                    }
                }
            }
        }

        Column(modifier = Modifier.fillMaxSize().statusBarsPadding().padding(top = if (onBack != null) 44.dp else 36.dp)) {
            LazyColumn(
                state = listState,
                modifier = Modifier.weight(1f).padding(horizontal = 8.dp),
                verticalArrangement = Arrangement.spacedBy(2.dp),
                contentPadding = PaddingValues(top = 8.dp, bottom = 8.dp),
            ) {
                itemsIndexed(state.messages, key = { _, m -> m.id }) { _, message ->
                    ChatBubble(
                        message = message,
                        onLongPress = { contextMenuMessage = message },
                    )
                }
                if (state.isStreaming && state.streamedText.isNotEmpty()) {
                    item(key = "streaming") { StreamingBubble(text = state.streamedText) }
                } else if (state.isStreaming) {
                    item(key = "typing") { TypingBubble() }
                }
            }

            AnimatedVisibility(visible = state.error != null, enter = slideInVertically { it } + fadeIn(), exit = slideOutVertically { it } + fadeOut()) {
                Surface(color = MiyaColors.Error.copy(alpha = 0.1f), modifier = Modifier.fillMaxWidth()) {
                    Row(Modifier.padding(horizontal = 16.dp, vertical = 8.dp), verticalAlignment = Alignment.CenterVertically) {
                        Icon(Icons.Default.Error, null, tint = MiyaColors.Error, modifier = Modifier.size(16.dp))
                        Spacer(Modifier.width(8.dp))
                        Text(state.error ?: "", style = MaterialTheme.typography.bodySmall, color = MiyaColors.Error, modifier = Modifier.weight(1f))
                        IconButton(onClick = { viewModel.clearError() }, modifier = Modifier.size(24.dp)) {
                            Icon(Icons.Default.Close, null, tint = MiyaColors.Error, modifier = Modifier.size(16.dp))
                        }
                    }
                }
            }

            AnimatedVisibility(visible = state.showAttachmentPicker, enter = fadeIn(tween(200)) + slideInVertically(tween(250)) { it }, exit = fadeOut(tween(150)) + slideOutVertically(tween(200)) { it }) {
                Surface(color = Color(0xFF2D2228), tonalElevation = 4.dp, modifier = Modifier.fillMaxWidth()) {
                    Row(Modifier.padding(horizontal = 16.dp, vertical = 12.dp), horizontalArrangement = Arrangement.spacedBy(24.dp)) {
                        Column(horizontalAlignment = Alignment.CenterHorizontally, modifier = Modifier.clickable { imagePicker.launch("image/*"); viewModel.toggleAttachmentPicker() }) {
                            Box(Modifier.size(52.dp).clip(RoundedCornerShape(14.dp)).background(MiyaColors.Primary.copy(alpha = 0.12f)), contentAlignment = Alignment.Center) {
                                Icon(Icons.Default.Image, null, tint = MiyaColors.Primary, modifier = Modifier.size(26.dp))
                            }
                            Spacer(Modifier.height(4.dp))
                            Text("图片", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                        }
                        Column(horizontalAlignment = Alignment.CenterHorizontally, modifier = Modifier.clickable { filePicker.launch("*/*"); viewModel.toggleAttachmentPicker() }) {
                            Box(Modifier.size(52.dp).clip(RoundedCornerShape(14.dp)).background(MiyaColors.Secondary.copy(alpha = 0.12f)), contentAlignment = Alignment.Center) {
                                Icon(Icons.Default.Description, null, tint = MiyaColors.Secondary, modifier = Modifier.size(26.dp))
                            }
                            Spacer(Modifier.height(4.dp))
                            Text("文件", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                        }
                    }
                }
            }

            ChatInputBar(
                text = state.inputText,
                onTextChange = { viewModel.onInputChange(it) },
                onSend = { focusManager.clearFocus(); viewModel.sendMessage() },
                onStop = { viewModel.stopStreaming() },
                isStreaming = state.isStreaming,
                onAttachment = { viewModel.toggleAttachmentPicker() },
            )
        }
    }

    // Context menu dropdown
    contextMenuMessage?.let { message ->
        AlertDialog(
            onDismissRequest = { contextMenuMessage = null },
            title = null,
            text = {
                Column {
                    if (!message.hasImage && !message.hasFile) {
                        TextButton(onClick = {
                            clipboard.setText(AnnotatedString(message.content))
                            contextMenuMessage = null
                        }, modifier = Modifier.fillMaxWidth()) {
                            Icon(Icons.Default.ContentCopy, null, modifier = Modifier.size(18.dp))
                            Spacer(Modifier.width(12.dp))
                            Text("复制文本")
                            Spacer(Modifier.weight(1f))
                        }
                    }
                    TextButton(onClick = {
                        viewModel.deleteMessage(message.id)
                        contextMenuMessage = null
                    }, modifier = Modifier.fillMaxWidth()) {
                        Icon(Icons.Default.Delete, null, modifier = Modifier.size(18.dp), tint = MiyaColors.Error)
                        Spacer(Modifier.width(12.dp))
                        Text("删除消息", color = MiyaColors.Error)
                        Spacer(Modifier.weight(1f))
                    }
                }
            },
            confirmButton = {},
            dismissButton = {},
            containerColor = Color(0xFF2D2228),
            shape = RoundedCornerShape(16.dp),
        )
    }
}

@OptIn(ExperimentalFoundationApi::class)
@Composable
private fun ChatBubble(message: ChatMessage, onLongPress: () -> Unit) {
    val isUser = message.isUser
    val isMiya = !isUser

    Row(
        Modifier.fillMaxWidth().combinedClickable(
            onClick = {},
            onLongClick = onLongPress,
        ),
        horizontalArrangement = if (isUser) Arrangement.End else Arrangement.Start,
    ) {
        if (isMiya) {
            MiyaChatAvatar(modifier = Modifier.padding(top = 4.dp, end = 8.dp), size = 32.dp)
        }

        Surface(
            shape = RoundedCornerShape(
                topStart = 18.dp, topEnd = 18.dp,
                bottomStart = if (isUser) 18.dp else 6.dp,
                bottomEnd = if (isUser) 6.dp else 18.dp,
            ),
            color = if (isUser) MiyaColors.Primary.copy(alpha = 0.85f) else Color(0xFF2D2228).copy(alpha = 0.92f),
            tonalElevation = 0.dp,
            shadowElevation = 0.dp,
            modifier = Modifier.widthIn(max = 280.dp),
        ) {
            Column(Modifier.padding(horizontal = 14.dp, vertical = 10.dp)) {
                if (message.hasImage) {
                    ImageAttachmentCard(message.imageBase64)
                    Spacer(Modifier.height(4.dp))
                }
                if (message.hasFile) {
                    FileAttachmentCard(message.fileName, message.fileSize, message.fileMimeType)
                    Spacer(Modifier.height(4.dp))
                }
                if (message.content.isNotEmpty()) {
                    if (isMiya) {
                        MarkdownText(message.content, isUser)
                    } else {
                        Text(
                            message.content,
                            style = MaterialTheme.typography.bodyLarge.copy(lineHeight = 22.sp, letterSpacing = 0.2.sp),
                            color = Color.White,
                        )
                    }
                }
                Spacer(Modifier.height(2.dp))
            }
        }
    }
}

@Composable
private fun ImageAttachmentCard(base64: String?) {
    if (base64 == null) return
    Surface(
        shape = RoundedCornerShape(10.dp),
        color = Color.White.copy(alpha = 0.08f),
        modifier = Modifier.fillMaxWidth(),
    ) {
        Box(Modifier.fillMaxWidth().aspectRatio(16f / 10f)) {
            AsyncImage(
                model = ImageRequest.Builder(LocalContext.current).data(base64).crossfade(true).build(),
                contentDescription = "图片",
                modifier = Modifier.fillMaxSize().clip(RoundedCornerShape(10.dp)),
                contentScale = ContentScale.Crop,
            )
            Box(
                Modifier.align(Alignment.BottomStart).fillMaxWidth()
                    .background(Color.Black.copy(alpha = 0.35f))
                    .padding(horizontal = 8.dp, vertical = 3.dp),
            ) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Icon(Icons.Default.Image, null, tint = Color.White, modifier = Modifier.size(12.dp))
                    Spacer(Modifier.width(4.dp))
                    Text("图片", style = MaterialTheme.typography.labelSmall, color = Color.White)
                }
            }
        }
    }
}

@Composable
private fun FileAttachmentCard(name: String?, size: Long?, mimeType: String?) {
    Surface(
        shape = RoundedCornerShape(10.dp),
        color = Color.White.copy(alpha = 0.06f),
        modifier = Modifier.fillMaxWidth(),
    ) {
        Row(
            Modifier.padding(horizontal = 10.dp, vertical = 10.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Box(
                Modifier.size(38.dp).clip(RoundedCornerShape(8.dp)).background(MiyaColors.Secondary.copy(alpha = 0.15f)),
                contentAlignment = Alignment.Center,
            ) {
                Icon(
                    when {
                        mimeType?.startsWith("image/") == true -> Icons.Default.Image
                        mimeType?.startsWith("audio/") == true -> Icons.Default.Audiotrack
                        mimeType?.startsWith("video/") == true -> Icons.Default.Videocam
                        else -> Icons.Default.Description
                    },
                    null,
                    tint = MiyaColors.Secondary,
                    modifier = Modifier.size(20.dp),
                )
            }
            Spacer(Modifier.width(10.dp))
            Column(Modifier.weight(1f)) {
                Text(name ?: "文件", style = MaterialTheme.typography.bodySmall, fontWeight = FontWeight.Medium, maxLines = 1, overflow = TextOverflow.Ellipsis)
                if (size != null && size > 0) {
                    Text(formatFileSize(size), style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
            }
        }
    }
}

@Composable
private fun StreamingBubble(text: String) {
    val cursor by rememberInfiniteTransition().animateFloat(0f, 1f, infiniteRepeatable(tween(500), RepeatMode.Reverse))

    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.Start) {
        MiyaChatAvatar(
            modifier = Modifier
                .padding(top = 4.dp, end = 8.dp)
                .pulseGlow(MiyaColors.Primary.copy(alpha = 0.5f), radius = 30.dp, durationMs = 1800),
            size = 32.dp,
        )

        Surface(
            shape = RoundedCornerShape(18.dp, 18.dp, 18.dp, 6.dp),
            color = Color(0xFF2D2228).copy(alpha = 0.92f),
            modifier = Modifier.widthIn(max = 280.dp),
        ) {
            Box(Modifier.padding(horizontal = 14.dp, vertical = 10.dp)) {
                Text(
                    buildAnnotatedString {
                        MarkdownParser.parseToAnnotated(text, this)
                        withStyle(SpanStyle(color = MiyaColors.Primary.copy(alpha = cursor))) { append("▌") }
                    },
                    style = MaterialTheme.typography.bodyLarge.copy(lineHeight = 22.sp),
                    color = MaterialTheme.colorScheme.onSurface,
                )
            }
        }
    }
}

@Composable
private fun TypingBubble() {
    val alphas = listOf(0, 120, 240).map { delay ->
        rememberInfiniteTransition().animateFloat(0.4f, 1f, infiniteRepeatable(tween(400, delayMillis = delay), RepeatMode.Reverse)).value
    }
    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.Start) {
        MiyaChatAvatar(
            modifier = Modifier
                .padding(top = 4.dp, end = 8.dp)
                .pulseGlow(MiyaColors.Primary.copy(alpha = 0.4f), radius = 28.dp, durationMs = 1500),
            size = 32.dp,
        )
        Surface(shape = RoundedCornerShape(18.dp, 18.dp, 18.dp, 6.dp), color = Color(0xFF2D2228).copy(alpha = 0.92f)) {
            Row(Modifier.padding(horizontal = 14.dp, vertical = 12.dp), horizontalArrangement = Arrangement.spacedBy(5.dp)) {
                alphas.forEach { alpha ->
                    Box(Modifier.size(7.dp).clip(CircleShape).background(MiyaColors.Primary.copy(alpha = alpha)))
                }
            }
        }
    }
}

@Composable
private fun ChatInputBar(
    text: String,
    onTextChange: (String) -> Unit,
    onSend: () -> Unit,
    onStop: () -> Unit,
    isStreaming: Boolean,
    onAttachment: () -> Unit,
) {
    val hasContent = text.isNotBlank()
    Surface(color = Color(0xFF1A1218).copy(alpha = 0.95f), tonalElevation = 0.dp) {
        Row(Modifier.fillMaxWidth().navigationBarsPadding().padding(horizontal = 10.dp, vertical = 8.dp), verticalAlignment = Alignment.CenterVertically) {
            IconButton(onClick = onAttachment, modifier = Modifier.size(36.dp)) {
                Icon(Icons.Default.Add, "附件", tint = MaterialTheme.colorScheme.onSurfaceVariant, modifier = Modifier.size(22.dp))
            }
            Box(Modifier.weight(1f).clip(RoundedCornerShape(21.dp)).background(Color.White.copy(alpha = 0.06f)).padding(horizontal = 14.dp, vertical = 10.dp)) {
                BasicTextField(
                    value = text, onValueChange = onTextChange, maxLines = 4,
                    textStyle = TextStyle(color = MaterialTheme.colorScheme.onSurface, fontSize = 15.sp, lineHeight = 20.sp),
                    cursorBrush = SolidColor(MiyaColors.Primary),
                    modifier = Modifier.fillMaxWidth(),
                    decorationBox = { inner ->
                        if (text.isEmpty()) Text("和弥娅说些什么...", style = TextStyle(color = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.5f), fontSize = 15.sp))
                        inner()
                    },
                )
            }
            Spacer(Modifier.width(8.dp))
            if (isStreaming) {
                IconButton(onClick = onStop, modifier = Modifier.size(40.dp).clip(CircleShape).background(MiyaColors.Error)) {
                    Icon(Icons.Default.Stop, "停止", tint = Color.White, modifier = Modifier.size(20.dp))
                }
            } else {
                IconButton(onClick = onSend, enabled = hasContent, modifier = Modifier.size(40.dp).clip(CircleShape).background(if (hasContent) MiyaColors.Primary else Color.White.copy(alpha = 0.06f))) {
                    Icon(Icons.AutoMirrored.Filled.Send, "发送", tint = if (hasContent) Color.White else MaterialTheme.colorScheme.onSurface.copy(alpha = 0.3f), modifier = Modifier.size(18.dp))
                }
            }
        }
    }
}

// ── Markdown Text ──

@Composable
private fun MarkdownText(text: String, isUser: Boolean) {
    val annotated = remember(text) {
        buildAnnotatedString {
            MarkdownParser.parseToAnnotated(text, this)
        }
    }
    Text(
        annotated,
        style = MaterialTheme.typography.bodyLarge.copy(lineHeight = 22.sp, letterSpacing = 0.2.sp),
        color = if (isUser) Color.White else MaterialTheme.colorScheme.onSurface,
    )
}

// ── Markdown Parser ──

object MarkdownParser {
    fun parseToAnnotated(text: String, builder: androidx.compose.ui.text.AnnotatedString.Builder) {
        val codeBlockPattern = Regex("```(?:\\w+\\n)?([\\s\\S]*?)```")
        val boldPattern = Regex("\\*\\*(.+?)\\*\\*")
        val italicPattern = Regex("\\*(.+?)\\*")
        val inlineCodePattern = Regex("`(.+?)`")

        var remaining = text

        while (remaining.isNotEmpty()) {
            val codeBlock = codeBlockPattern.find(remaining)
            val bold = boldPattern.find(remaining)
            val italic = italicPattern.find(remaining)
            val inlineCode = inlineCodePattern.find(remaining)

            val matches = listOfNotNull(
                codeBlock?.let { "code" to it },
                bold?.let { "bold" to it },
                italic?.let { "italic" to it },
                inlineCode?.let { "icode" to it },
            ).sortedBy { it.second.range.first }

            if (matches.isEmpty()) {
                builder.append(remaining)
                break
            }

            val (type, match) = matches.first()
            if (match.range.first > 0) {
                builder.append(remaining.substring(0, match.range.first))
            }

            when (type) {
                "code" -> {
                    val code = match.groupValues[1].trim()
                    builder.withStyle(SpanStyle(
                        fontFamily = FontFamily.Monospace,
                        fontSize = 13.sp,
                        background = Color.White.copy(alpha = 0.06f),
                    )) { append("\n$code\n") }
                }
                "icode" -> {
                    val code = match.groupValues[1]
                    builder.withStyle(SpanStyle(
                        fontFamily = FontFamily.Monospace,
                        fontSize = 13.sp,
                        background = Color.White.copy(alpha = 0.08f),
                    )) { append(code) }
                }
                "bold" -> {
                    builder.withStyle(SpanStyle(fontWeight = FontWeight.Bold)) {
                        append(match.groupValues[1])
                    }
                }
                "italic" -> {
                    builder.withStyle(SpanStyle(fontStyle = FontStyle.Italic)) {
                        append(match.groupValues[1])
                    }
                }
            }

            remaining = remaining.substring(match.range.last + 1)
        }
    }
}

// ── Utilities ──

private fun formatTimestamp(ts: Long): String {
    if (ts == 0L) return ""
    val cal = java.util.Calendar.getInstance().apply { timeInMillis = ts }
    return String.format("%02d:%02d", cal.get(java.util.Calendar.HOUR_OF_DAY), cal.get(java.util.Calendar.MINUTE))
}

private fun formatFileSize(size: Long): String = when {
    size < 1024 -> "${size}B"
    size < 1024 * 1024 -> "${size / 1024}KB"
    size < 1024 * 1024 * 1024 -> "${"%.1f".format(size.toFloat() / (1024 * 1024))}MB"
    else -> "${"%.2f".format(size.toFloat() / (1024 * 1024 * 1024))}GB"
}
