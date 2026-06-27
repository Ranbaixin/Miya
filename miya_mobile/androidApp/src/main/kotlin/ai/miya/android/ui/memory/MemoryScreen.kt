package ai.miya.android.ui.memory

import ai.miya.shared.ServiceLocator
import ai.miya.shared.model.MemoryItem
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import ai.miya.android.ui.theme.*
import kotlinx.coroutines.launch

@Composable
fun MemoryScreen() {
    val scope = rememberCoroutineScope()
    val repo = remember { ServiceLocator.memoryRepo }

    var memories by remember { mutableStateOf<List<MemoryItem>>(emptyList()) }
    var searchQuery by remember { mutableStateOf("") }
    var isLoading by remember { mutableStateOf(true) }

    LaunchedEffect(Unit) {
        scope.launch {
            try {
                memories = repo.getList()
                isLoading = false
            } catch (_: Exception) {
                isLoading = false
            }
        }
    }

    fun search() {
        isLoading = true
        scope.launch {
            try {
                memories = if (searchQuery.isBlank()) {
                    repo.getList()
                } else {
                    repo.search(searchQuery)
                }
                isLoading = false
            } catch (_: Exception) {
                isLoading = false
            }
        }
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(MiyaBackground)
            .padding(16.dp)
    ) {
        Text(
            text = "记忆",
            color = MiyaTextPrimary,
            fontSize = 24.sp,
            fontWeight = FontWeight.Bold,
        )

        Spacer(modifier = Modifier.height(12.dp))

        // 搜索栏
        OutlinedTextField(
            value = searchQuery,
            onValueChange = { searchQuery = it },
            modifier = Modifier.fillMaxWidth(),
            placeholder = { Text("搜索记忆...", color = MiyaTextSecondary) },
            leadingIcon = {
                Icon(Icons.Filled.Search, contentDescription = null, tint = MiyaTextSecondary)
            },
            trailingIcon = {
                IconButton(onClick = { search() }) {
                    Icon(Icons.Filled.ArrowForward, contentDescription = "搜索", tint = MiyaPrimary)
                }
            },
            colors = OutlinedTextFieldDefaults.colors(
                focusedContainerColor = MiyaSurface,
                unfocusedContainerColor = MiyaSurface,
                focusedBorderColor = MiyaPrimary,
                unfocusedBorderColor = MiyaBorder,
                focusedTextColor = MiyaTextPrimary,
                unfocusedTextColor = MiyaTextPrimary,
            ),
            shape = RoundedCornerShape(16.dp),
            singleLine = true,
        )

        Spacer(modifier = Modifier.height(12.dp))

        if (isLoading) {
            Box(modifier = Modifier.fillMaxWidth().weight(1f), contentAlignment = androidx.compose.ui.Alignment.Center) {
                CircularProgressIndicator(color = MiyaPrimary)
            }
        } else {
            LazyColumn(
                modifier = Modifier.weight(1f),
                verticalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                if (memories.isEmpty()) {
                    item {
                        Text(
                            text = "没有找到记忆",
                            color = MiyaTextSecondary,
                            modifier = Modifier.padding(vertical = 40.dp),
                        )
                    }
                }
                items(memories) { memory ->
                    MemoryCard(memory)
                }
            }
        }
    }
}

@Composable
private fun MemoryCard(memory: MemoryItem) {
    Card(
        colors = CardDefaults.cardColors(containerColor = MiyaSurface),
        shape = RoundedCornerShape(12.dp),
    ) {
        Column(modifier = Modifier.padding(14.dp)) {
            Row(verticalAlignment = androidx.compose.ui.Alignment.CenterVertically) {
                Icon(
                    imageVector = Icons.Filled.Memory,
                    contentDescription = null,
                    tint = MiyaPrimary,
                    modifier = Modifier.size(20.dp),
                )
                Spacer(modifier = Modifier.width(8.dp))
                Surface(
                    shape = RoundedCornerShape(6.dp),
                    color = MiyaSurfaceVariant,
                ) {
                    Text(
                        text = memory.level,
                        color = MiyaAccent,
                        fontSize = 11.sp,
                        modifier = Modifier.padding(horizontal = 8.dp, vertical = 2.dp),
                    )
                }
            }
            Spacer(modifier = Modifier.height(8.dp))
            Text(
                text = memory.content,
                color = MiyaTextPrimary,
                fontSize = 14.sp,
            )
            if (memory.tags.isNotEmpty()) {
                Spacer(modifier = Modifier.height(8.dp))
                Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                    memory.tags.forEach { tag ->
                        Surface(
                            shape = RoundedCornerShape(4.dp),
                            color = MiyaPrimary.copy(alpha = 0.15f),
                        ) {
                            Text(
                                text = "#$tag",
                                color = MiyaPrimary,
                                fontSize = 11.sp,
                                modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp),
                            )
                        }
                    }
                }
            }
        }
    }
}
