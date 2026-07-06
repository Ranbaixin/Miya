package ai.miya.android.ui.conversation

import ai.miya.shared.ServiceLocator
import ai.miya.shared.model.SessionInfo
import ai.miya.android.ui.theme.LocalMiyaColors
import androidx.compose.animation.*
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.coroutines.launch
import java.text.SimpleDateFormat
import java.util.*

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ConversationListScreen(
    onConversationClick: (sessionId: String, sessionName: String) -> Unit,
) {
    val colors = LocalMiyaColors.current
    val scope = rememberCoroutineScope()
    val chatRepo = remember { ServiceLocator.chatRepo }
    var sessions by remember { mutableStateOf<List<SessionInfo>>(emptyList()) }
    var isLoading by remember { mutableStateOf(true) }

    LaunchedEffect(Unit) {
        try {
            sessions = chatRepo.getSessions()
        } catch (_: Exception) { }
        isLoading = false
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(colors.background)
            .statusBarsPadding()
    ) {
        // 顶部标题栏
        Surface(
            color = colors.background,
            shadowElevation = 0.dp,
        ) {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 20.dp, vertical = 14.dp),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Text(
                    text = "消息",
                    color = colors.textPrimary,
                    fontSize = 28.sp,
                    fontWeight = FontWeight.Bold,
                )
                IconButton(
                    onClick = {
                        scope.launch {
                            try {
                                val newId = chatRepo.newSession()
                                onConversationClick(newId, "新对话")
                            } catch (_: Exception) { }
                        }
                    }
                ) {
                    Icon(
                        Icons.Default.Add,
                        contentDescription = "新建对话",
                        tint = colors.primary,
                    )
                }
            }
        }

        // 搜索栏
        Surface(
            color = colors.background,
            shadowElevation = 0.dp,
        ) {
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 16.dp, vertical = 4.dp),
            ) {
                Surface(
                    color = colors.surface,
                    shape = RoundedCornerShape(10.dp),
                    modifier = Modifier.fillMaxWidth(),
                ) {
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(horizontal = 12.dp, vertical = 8.dp),
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Text(
                            text = "\uD83D\uDD0D",
                            fontSize = 14.sp,
                            color = colors.textDim,
                        )
                        Spacer(Modifier.width(8.dp))
                        Text(
                            text = "搜索对话...",
                            color = colors.textDim,
                            fontSize = 14.sp,
                        )
                    }
                }
            }
        }

        Spacer(Modifier.height(4.dp))

        if (isLoading) {
            Box(
                modifier = Modifier.fillMaxSize(),
                contentAlignment = Alignment.Center,
            ) {
                CircularProgressIndicator(color = colors.primary)
            }
        } else {
            LazyColumn(
                modifier = Modifier.fillMaxSize(),
            ) {
                // 置顶项：弥娅
                item(key = "miya_sticky") {
                    Surface(
                        color = colors.surface.copy(alpha = 0.5f),
                        onClick = { onConversationClick("default", "弥娅") },
                    ) {
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(horizontal = 16.dp, vertical = 12.dp),
                            verticalAlignment = Alignment.CenterVertically,
                        ) {
                            Box(
                                modifier = Modifier
                                    .size(52.dp)
                                    .clip(CircleShape)
                                    .background(colors.primary.copy(alpha = 0.15f)),
                                contentAlignment = Alignment.Center,
                            ) {
                                Text(
                                    text = "弥",
                                    color = colors.primary,
                                    fontSize = 22.sp,
                                    fontWeight = FontWeight.Bold,
                                )
                            }
                            Spacer(Modifier.width(14.dp))
                            Column(
                                modifier = Modifier.weight(1f),
                            ) {
                                Text(
                                    text = "弥娅",
                                    color = colors.textPrimary,
                                    fontSize = 16.sp,
                                    fontWeight = FontWeight.SemiBold,
                                )
                                Spacer(Modifier.height(4.dp))
                                Text(
                                    text = "你好，我是弥娅，有什么可以帮你的？",
                                    color = colors.textDim,
                                    fontSize = 13.sp,
                                    maxLines = 1,
                                    overflow = TextOverflow.Ellipsis,
                                )
                            }
                            Column(horizontalAlignment = Alignment.End) {
                                Text(
                                    text = "现在",
                                    color = colors.textDim,
                                    fontSize = 11.sp,
                                )
                                Spacer(Modifier.height(4.dp))
                                Box(
                                    modifier = Modifier
                                        .size(8.dp)
                                        .clip(CircleShape)
                                        .background(colors.success),
                                )
                            }
                        }
                    }
                    HorizontalDivider(thickness = 0.5.dp, color = colors.divider)
                }

                items(sessions, key = { it.id }) { session ->
                    Surface(
                        color = colors.background,
                        onClick = {
                            onConversationClick(session.id, session.name ?: "对话")
                        },
                    ) {
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(horizontal = 16.dp, vertical = 12.dp),
                            verticalAlignment = Alignment.CenterVertically,
                        ) {
                            Box(
                                modifier = Modifier
                                    .size(52.dp)
                                    .clip(CircleShape)
                                    .background(colors.surface),
                                contentAlignment = Alignment.Center,
                            ) {
                                Text(
                                    text = session.name?.firstOrNull()?.toString() ?: "M",
                                    color = colors.textSecondary,
                                    fontSize = 20.sp,
                                    fontWeight = FontWeight.Medium,
                                )
                            }
                            Spacer(Modifier.width(14.dp))
                            Column(
                                modifier = Modifier.weight(1f),
                            ) {
                                Row(
                                    modifier = Modifier.fillMaxWidth(),
                                    horizontalArrangement = Arrangement.SpaceBetween,
                                ) {
                                    Text(
                                        text = session.name ?: "对话",
                                        color = colors.textPrimary,
                                        fontSize = 16.sp,
                                        fontWeight = FontWeight.Normal,
                                    )
                                    Text(
                                        text = formatConversationTime(session.updatedAt),
                                        color = colors.textDim,
                                        fontSize = 11.sp,
                                    )
                                }
                                Spacer(Modifier.height(4.dp))
                                Text(
                                    text = "${session.messageCount ?: 0} 条消息",
                                    color = colors.textDim,
                                    fontSize = 13.sp,
                                    maxLines = 1,
                                    overflow = TextOverflow.Ellipsis,
                                )
                            }
                        }
                    }
                    HorizontalDivider(
                        modifier = Modifier.padding(start = 82.dp),
                        thickness = 0.5.dp,
                        color = colors.divider,
                    )
                }

                item { Spacer(Modifier.height(8.dp)) }
            }
        }
    }
}

private fun formatConversationTime(isoString: String?): String {
    if (isoString == null) return ""
    return try {
        val formats = listOf(
            "yyyy-MM-dd'T'HH:mm:ss",
            "yyyy-MM-dd HH:mm:ss",
            "yyyy-MM-dd'T'HH:mm:ss.SSS",
        )
        var date: Date? = null
        for (fmt in formats) {
            try {
                date = SimpleDateFormat(fmt, Locale.getDefault()).parse(isoString)
                if (date != null) break
            } catch (_: Exception) { }
        }
        if (date == null) return ""
        val now = Calendar.getInstance()
        val cal = Calendar.getInstance().apply { time = date }
        val diffDays = (now.timeInMillis - cal.timeInMillis) / (1000 * 60 * 60 * 24)
        when {
            diffDays == 0L -> SimpleDateFormat("HH:mm", Locale.getDefault()).format(date)
            diffDays == 1L -> "昨天"
            diffDays < 7L -> SimpleDateFormat("EEEE", Locale.CHINESE).format(date)
            else -> SimpleDateFormat("MM/dd", Locale.getDefault()).format(date)
        }
    } catch (_: Exception) {
        ""
    }
}
