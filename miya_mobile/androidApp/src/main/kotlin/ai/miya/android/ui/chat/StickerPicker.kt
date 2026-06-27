package ai.miya.android.ui.chat

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Search
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import ai.miya.android.ui.theme.*

// ═══════════════════════════════════════════════
// 内置弥娅主题表情数据
// ═══════════════════════════════════════════════

data class StickerItem(
    val id: String,
    val emoji: String,
    val name: String,
    val category: String,
)

val miyaStickers = listOf(
    // 基础表情
    StickerItem("miya_smile", "😊", "开心", "基础"),
    StickerItem("miya_laugh", "😄", "大笑", "基础"),
    StickerItem("miya_love", "😍", "喜欢", "基础"),
    StickerItem("miya_wink", "😉", "眨眼", "基础"),
    StickerItem("miya_kiss", "😘", "亲亲", "基础"),
    StickerItem("miya_shy", "😳", "害羞", "基础"),
    StickerItem("miya_cry", "😢", "哭泣", "基础"),
    StickerItem("miya_angry", "😠", "生气", "基础"),
    StickerItem("miya_surprise", "😲", "惊讶", "基础"),
    StickerItem("miya_cool", "😎", "酷", "基础"),
    StickerItem("miya_sleep", "😴", "困了", "基础"),
    StickerItem("miya_sick", "🤒", "难受", "基础"),
    StickerItem("miya_think", "🤔", "思考", "基础"),
    StickerItem("miya_clap", "👏", "鼓掌", "基础"),
    StickerItem("miya_ok", "👌", "OK", "基础"),
    StickerItem("miya_hug", "🫂", "抱抱", "基础"),

    // 弥娅专属
    StickerItem("miya_heart", "💙", "爱心", "弥娅"),
    StickerItem("miya_sparkle", "✨", "闪耀", "弥娅"),
    StickerItem("miya_hello", "👋", "你好", "弥娅"),
    StickerItem("miya_night", "🌙", "晚安", "弥娅"),
    StickerItem("miya_morning", "🌅", "早安", "弥娅"),
    StickerItem("miya_coffee", "☕", "咖啡", "弥娅"),
    StickerItem("miya_star", "⭐", "星星", "弥娅"),
    StickerItem("miya_pray", "🙏", "拜托", "弥娅"),

    // 动作表情
    StickerItem("miya_facepalm", "🤦", "捂脸", "动作"),
    StickerItem("miya_roll", "🙄", "白眼", "动作"),
    StickerItem("miya_sweat", "😅", "尴尬", "动作"),
    StickerItem("miya_party", "🎉", "庆祝", "动作"),
    StickerItem("miya_flex", "💪", "加油", "动作"),
    StickerItem("miya_please", "🥺", "求求", "动作"),
)

// ═══════════════════════════════════════════════
// 表情选择面板
// ═══════════════════════════════════════════════

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun StickerPickerPanel(
    onStickerSelected: (stickerId: String, stickerUrl: String) -> Unit,
    onDismiss: () -> Unit,
    modifier: Modifier = Modifier,
) {
    var selectedTab by remember { mutableIntStateOf(0) }
    val tabs = listOf("弥娅表情", "搜索表情")
    var searchQuery by remember { mutableStateOf("") }

    Surface(
        modifier = modifier
            .fillMaxWidth()
            .heightIn(max = 320.dp),
        color = MiyaSurfaceDeep.copy(alpha = 0.95f),
        shape = RoundedCornerShape(topStart = 20.dp, topEnd = 20.dp),
        tonalElevation = 8.dp,
    ) {
        Column {
            // 顶部操作栏
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 12.dp, vertical = 8.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                tabs.forEachIndexed { index, title ->
                    val isSelected = selectedTab == index
                    TextButton(
                        onClick = { selectedTab = index },
                        modifier = Modifier.weight(1f),
                        colors = ButtonDefaults.textButtonColors(
                            contentColor = if (isSelected) MiyaAccent else MiyaTextSecondary,
                        ),
                    ) {
                        Text(
                            title,
                            fontWeight = if (isSelected) FontWeight.Bold else FontWeight.Normal,
                            fontSize = 13.sp,
                        )
                    }
                }
                IconButton(onClick = onDismiss, modifier = Modifier.size(32.dp)) {
                    Icon(Icons.Filled.Close, "关闭", tint = MiyaTextSecondary, modifier = Modifier.size(18.dp))
                }
            }

            // 内容区
            when (selectedTab) {
                0 -> BuiltInStickersGrid(onStickerSelected)
                1 -> StickerSearchPanel(searchQuery, onSearchQueryChange = { searchQuery = it }, onStickerSelected)
            }
        }
    }
}

@Composable
fun BuiltInStickersGrid(onStickerSelected: (stickerId: String, stickerUrl: String) -> Unit) {
    LazyVerticalGrid(
        columns = GridCells.Fixed(6),
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 8.dp, vertical = 4.dp),
        horizontalArrangement = Arrangement.spacedBy(4.dp),
        verticalArrangement = Arrangement.spacedBy(4.dp),
    ) {
        items(miyaStickers) { sticker ->
            StickerCell(
                emoji = sticker.emoji,
                label = sticker.name,
                onClick = {
                    onStickerSelected(sticker.id, sticker.id)
                },
            )
        }
    }
}

@Composable
fun StickerCell(emoji: String, label: String, onClick: () -> Unit) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(8.dp))
            .clickable(onClick = onClick)
            .padding(4.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Surface(
            color = MiyaSurface,
            shape = RoundedCornerShape(8.dp),
            modifier = Modifier.size(44.dp),
        ) {
            Box(contentAlignment = Alignment.Center, modifier = Modifier.fillMaxSize()) {
                Text(
                    text = emoji,
                    fontSize = 22.sp,
                    textAlign = TextAlign.Center,
                )
            }
        }
        Text(
            text = label,
            color = MiyaTextSecondary,
            fontSize = 9.sp,
            maxLines = 1,
        )
    }
}

@Composable
fun StickerSearchPanel(
    query: String,
    onSearchQueryChange: (String) -> Unit,
    onStickerSelected: (stickerId: String, stickerUrl: String) -> Unit,
) {
    Column(modifier = Modifier.padding(horizontal = 12.dp, vertical = 8.dp)) {
        OutlinedTextField(
            value = query,
            onValueChange = onSearchQueryChange,
            modifier = Modifier.fillMaxWidth(),
            placeholder = { Text("搜索表情...", color = MiyaTextSecondary, fontSize = 13.sp) },
            leadingIcon = {
                Icon(Icons.Filled.Search, null, tint = MiyaTextSecondary, modifier = Modifier.size(18.dp))
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
            shape = RoundedCornerShape(12.dp),
            singleLine = true,
            textStyle = androidx.compose.ui.text.TextStyle(fontSize = 13.sp),
        )

        Spacer(Modifier.height(12.dp))

        if (query.isBlank()) {
            Box(
                modifier = Modifier.fillMaxWidth().height(120.dp),
                contentAlignment = Alignment.Center,
            ) {
                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    Text("🔍", fontSize = 32.sp)
                    Spacer(Modifier.height(8.dp))
                    Text(
                        "输入关键词搜索表情",
                        color = MiyaTextSecondary,
                        fontSize = 13.sp,
                    )
                    Spacer(Modifier.height(4.dp))
                    Text(
                        "支持 GIPHY 表情搜索",
                        color = MiyaTextDim,
                        fontSize = 11.sp,
                    )
                }
            }
        } else {
            Box(
                modifier = Modifier.fillMaxWidth().height(120.dp),
                contentAlignment = Alignment.Center,
            ) {
                Text(
                    "搜索 \"${query}\" 中...",
                    color = MiyaTextSecondary,
                    fontSize = 13.sp,
                )
            }
        }
    }
}
