package ai.miya.feature.memory

import ai.miya.domain.ServiceRegistry
import ai.miya.domain.MemoryProvider
import ai.miya.model.MemoryItem
import ai.miya.model.MemoryStats
import ai.miya.uicommon.theme.MiyaColors
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch
import androidx.lifecycle.viewModelScope
import androidx.compose.animation.animateColorAsState
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Search
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import kotlinx.coroutines.launch

data class MemoryScreenState(
    val stats: MemoryStats? = null,
    val memoryItems: List<MemoryItem> = emptyList(),
    val searchQuery: String = "",
    val isLoading: Boolean = false,
    val isSearching: Boolean = false,
)

class MemoryViewModel : androidx.lifecycle.ViewModel() {

    private val _state = MutableStateFlow(MemoryScreenState())
    val state: StateFlow<MemoryScreenState> = _state.asStateFlow()

    fun loadMemory() {
        viewModelScope.launch {
            _state.update { it.copy(isLoading = true) }
            try {
                val memoryProvider = ServiceRegistry.getOrThrow(MemoryProvider::class.java)
                val stats = memoryProvider.getStats()
                val items = memoryProvider.getList(50)
                _state.update { it.copy(
                    stats = stats,
                    memoryItems = items,
                    isLoading = false,
                ) }
            } catch (e: Exception) {
                _state.update { it.copy(isLoading = false) }
            }
        }
    }

    fun search(query: String) {
        _state.update { it.copy(searchQuery = query) }
        if (query.length < 2) {
            if (query.isEmpty()) loadMemory()
            return
        }
        viewModelScope.launch {
            _state.update { it.copy(isSearching = true) }
            try {
                val memoryProvider = ServiceRegistry.getOrThrow(MemoryProvider::class.java)
                val results = memoryProvider.search(query)
                _state.update { it.copy(
                    memoryItems = results,
                    isSearching = false,
                ) }
            } catch (_: Exception) {
                _state.update { it.copy(isSearching = false) }
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MemoryScreen(
    viewModel: MemoryViewModel = androidx.lifecycle.viewmodel.compose.viewModel(),
    onBack: () -> Unit,
) {
    val state by viewModel.state.collectAsStateWithLifecycle()

    LaunchedEffect(Unit) {
        viewModel.loadMemory()
    }

    Column(modifier = Modifier.fillMaxSize()) {
        TopAppBar(
            title = { Text("记忆空间") },
            navigationIcon = {
                IconButton(onClick = onBack) {
                    Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "返回")
                }
            },
        )

        // Stats cards
        if (state.stats != null) {
            MemoryStatsRow(stats = state.stats!!)
        }

        // Search bar
        OutlinedTextField(
            value = state.searchQuery,
            onValueChange = { viewModel.search(it) },
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 16.dp, vertical = 8.dp),
            placeholder = { Text("搜索记忆...") },
            leadingIcon = {
                Icon(Icons.Default.Search, contentDescription = "搜索")
            },
            shape = RoundedCornerShape(12.dp),
            singleLine = true,
        )

        // Memory list
        if (state.isLoading || state.isSearching) {
            Box(
                modifier = Modifier.fillMaxSize(),
                contentAlignment = Alignment.Center,
            ) {
                CircularProgressIndicator(color = MaterialTheme.colorScheme.primary)
            }
        } else if (state.memoryItems.isEmpty()) {
            Box(
                modifier = Modifier.fillMaxSize(),
                contentAlignment = Alignment.Center,
            ) {
                Text(
                    "暂无记忆记录",
                    style = MaterialTheme.typography.bodyLarge,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
        } else {
            LazyColumn(
                modifier = Modifier.fillMaxSize(),
                contentPadding = PaddingValues(16.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                items(state.memoryItems, key = { it.id }) { item ->
                    MemoryCard(item = item)
                }
            }
        }
    }
}

@Composable
private fun MemoryStatsRow(stats: MemoryStats) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 16.dp, vertical = 8.dp),
        horizontalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        StatChip("总记忆", stats.total, MiyaColors.Primary)
        StatChip("短期", stats.shortTermCount, MiyaColors.Secondary)
        StatChip("长期", stats.longTermCount, MiyaColors.Happy)
        StatChip("对话", stats.dialogueCount, MiyaColors.Calm)
    }
}

@Composable
private fun StatChip(label: String, value: Int, color: androidx.compose.ui.graphics.Color) {
    Column(
        modifier = Modifier
            .clip(RoundedCornerShape(12.dp))
            .background(color.copy(alpha = 0.1f))
            .padding(12.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
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

@Composable
private fun MemoryCard(item: MemoryItem) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(12.dp),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.5f),
        ),
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Text(
                text = item.content,
                style = MaterialTheme.typography.bodyMedium,
                maxLines = 3,
                overflow = TextOverflow.Ellipsis,
            )
            if (item.tags.isNotEmpty()) {
                Spacer(Modifier.height(8.dp))
                Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                    item.tags.take(4).forEach { tag ->
                        Surface(
                            shape = RoundedCornerShape(4.dp),
                            color = MaterialTheme.colorScheme.primary.copy(alpha = 0.1f),
                        ) {
                            Text(
                                text = tag,
                                modifier = Modifier.padding(horizontal = 8.dp, vertical = 2.dp),
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.primary,
                            )
                        }
                    }
                }
            }
            if (!item.level.isNullOrEmpty()) {
                Spacer(Modifier.height(4.dp))
                Text(
                    text = "级别: ${item.level} · 优先级: ${"%.1f".format(item.priority)}",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
        }
    }
}
