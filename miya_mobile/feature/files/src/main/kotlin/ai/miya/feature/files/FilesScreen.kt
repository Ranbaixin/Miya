package ai.miya.feature.files

import ai.miya.uicommon.theme.MiyaColors
import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.animation.*
import androidx.compose.animation.core.*
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import coil.compose.AsyncImage
import coil.request.ImageRequest

@Composable
fun FilesScreen(viewModel: FilesViewModel = viewModel()) {
    val context = LocalContext.current
    LaunchedEffect(Unit) { viewModel.loadFiles(context) }
    FilesContent(viewModel)
}

@Composable
private fun FilesContent(viewModel: FilesViewModel) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val context = LocalContext.current

    val filePicker = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) { uri: Uri? ->
        uri?.let {
            val name = getFileName(context, it) ?: "文件"
            val mine = context.contentResolver.getType(it) ?: "application/octet-stream"
            val item = LocalFileItem(it, name, 0, mine, System.currentTimeMillis(), mine.startsWith("image/"))
            viewModel.selectFile(item)
        }
    }

    Box(modifier = Modifier.fillMaxSize()) {

        Column(modifier = Modifier.fillMaxSize().statusBarsPadding().padding(top = 8.dp)) {
            // Header
            Row(
                Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 4.dp),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Text("文件", style = MaterialTheme.typography.titleLarge, color = MaterialTheme.colorScheme.onSurface)
                FilledTonalButton(
                    onClick = { filePicker.launch(arrayOf("*/*")) },
                    colors = ButtonDefaults.filledTonalButtonColors(containerColor = MiyaColors.Primary.copy(alpha = 0.15f)),
                ) {
                    Icon(Icons.Default.Add, null, modifier = Modifier.size(18.dp))
                    Spacer(Modifier.width(6.dp))
                    Text("发送文件给弥娅", color = MiyaColors.Primary)
                }
            }

            Spacer(Modifier.height(4.dp))

            // Filter chips
            Row(
                Modifier.fillMaxWidth().padding(horizontal = 12.dp),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                FileFilterType.entries.forEach { filter ->
                    val selected = state.filterType == filter
                    FilterChip(
                        selected = selected,
                        onClick = { viewModel.setFilter(filter) },
                        label = { Text(filter.label, fontSize = 12.sp) },
                        colors = FilterChipDefaults.filterChipColors(
                            selectedContainerColor = MiyaColors.Primary.copy(alpha = 0.2f),
                            selectedLabelColor = MiyaColors.Primary,
                        ),
                        border = null,
                    )
                }
            }

            Spacer(Modifier.height(8.dp))

            // Selected file preview + analysis
            AnimatedVisibility(
                visible = state.selectedFile != null,
                enter = fadeIn(tween(200)) + expandVertically(tween(250)),
                exit = fadeOut(tween(150)) + shrinkVertically(tween(200)),
            ) {
                state.selectedFile?.let { file ->
                    Surface(
                        color = Color(0xFF2D2228).copy(alpha = 0.92f),
                        shape = RoundedCornerShape(14.dp),
                        modifier = Modifier.fillMaxWidth().padding(horizontal = 14.dp),
                    ) {
                        Column(Modifier.padding(12.dp)) {
                            Row(verticalAlignment = Alignment.CenterVertically) {
                                Box(
                                    Modifier.size(44.dp).clip(RoundedCornerShape(10.dp))
                                        .background(if (file.isImage) MiyaColors.Primary.copy(alpha = 0.12f) else MiyaColors.Secondary.copy(alpha = 0.12f)),
                                    contentAlignment = Alignment.Center,
                                ) {
                                    if (file.isImage) {
                                        AsyncImage(
                                            model = ImageRequest.Builder(context).data(file.uri).size(88).crossfade(true).build(),
                                            contentDescription = null,
                                            modifier = Modifier.fillMaxSize().clip(RoundedCornerShape(10.dp)),
                                            contentScale = ContentScale.Crop,
                                        )
                                    } else {
                                        Icon(Icons.Default.Description, null, tint = MiyaColors.Secondary, modifier = Modifier.size(22.dp))
                                    }
                                }
                                Spacer(Modifier.width(10.dp))
                                Column(Modifier.weight(1f)) {
                                    Text(file.name, style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.Medium, maxLines = 1, overflow = TextOverflow.Ellipsis)
                                    Text("${file.formattedSize} · ${file.formattedDate}", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                                }
                                IconButton(onClick = { viewModel.clearSelection() }, modifier = Modifier.size(28.dp)) {
                                    Icon(Icons.Default.Close, "取消", modifier = Modifier.size(16.dp))
                                }
                            }

                            Spacer(Modifier.height(8.dp))

                            // Analysis result
                            AnimatedVisibility(visible = state.currentAnalysis.isNotEmpty() || state.isAnalyzing) {
                                Surface(
                                    color = Color.White.copy(alpha = 0.04f),
                                    shape = RoundedCornerShape(10.dp),
                                    modifier = Modifier.fillMaxWidth(),
                                ) {
                                    Column(Modifier.padding(10.dp)) {
                                        Text("弥娅分析", style = MaterialTheme.typography.labelMedium, color = MiyaColors.Primary)
                                        Spacer(Modifier.height(4.dp))
                                        if (state.isAnalyzing) {
                                            Row(verticalAlignment = Alignment.CenterVertically) {
                                                CircularProgressIndicator(modifier = Modifier.size(14.dp), strokeWidth = 2.dp, color = MiyaColors.Primary)
                                                Spacer(Modifier.width(8.dp))
                                                Text("正在分析...", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                                            }
                                            if (state.currentAnalysis.isNotEmpty()) {
                                                Spacer(Modifier.height(6.dp))
                                                Text(state.currentAnalysis, style = MaterialTheme.typography.bodySmall, lineHeight = 18.sp, maxLines = 8, overflow = TextOverflow.Ellipsis)
                                            }
                                        } else if (state.currentAnalysis.isNotEmpty()) {
                                            Text(state.currentAnalysis, style = MaterialTheme.typography.bodySmall, lineHeight = 18.sp, maxLines = 10, overflow = TextOverflow.Ellipsis)
                                        }
                                    }
                                }
                            }

                            Spacer(Modifier.height(8.dp))

                            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.End) {
                                if (state.isAnalyzing) {
                                    OutlinedButton(
                                        onClick = { viewModel.stopAnalysis() },
                                        colors = ButtonDefaults.outlinedButtonColors(contentColor = MiyaColors.Error),
                                    ) {
                                        Text("停止", fontSize = 12.sp)
                                    }
                                } else {
                                    Button(
                                        onClick = { viewModel.sendToMiya(context) },
                                        colors = ButtonDefaults.buttonColors(containerColor = MiyaColors.Primary),
                                    ) {
                                        Text("发送给弥娅分析", fontSize = 12.sp)
                                    }
                                }
                            }
                        }
                    }
                    Spacer(Modifier.height(8.dp))
                }
            }

            // File list
            val filteredFiles = when (state.filterType) {
                FileFilterType.IMAGES -> state.deviceFiles.filter { it.isImage }
                FileFilterType.DOCUMENTS -> state.deviceFiles.filter { !it.isImage }
                FileFilterType.RESULTS -> emptyList()
                FileFilterType.ALL -> state.deviceFiles
            }

            if (state.filterType == FileFilterType.RESULTS && state.analysisResults.isNotEmpty()) {
                LazyColumn(
                    modifier = Modifier.fillMaxSize().padding(horizontal = 14.dp),
                    verticalArrangement = Arrangement.spacedBy(8.dp),
                    contentPadding = PaddingValues(bottom = 80.dp),
                ) {
                    items(state.analysisResults) { result ->
                        AnalysisResultCard(result)
                    }
                }
            } else if (state.filterType == FileFilterType.RESULTS) {
                Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                    Text("暂无分析结果", style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
            } else if (filteredFiles.isEmpty()) {
                Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                    Column(horizontalAlignment = Alignment.CenterHorizontally) {
                        Text("没有找到文件", style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
                        Spacer(Modifier.height(8.dp))
                        Text("点击上方按钮选择文件发送给弥娅", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.6f))
                    }
                }
            } else if (state.filterType == FileFilterType.IMAGES || state.filterType == FileFilterType.ALL) {
                LazyVerticalGrid(
                    columns = GridCells.Fixed(3),
                    modifier = Modifier.fillMaxSize().padding(horizontal = 14.dp),
                    horizontalArrangement = Arrangement.spacedBy(6.dp),
                    verticalArrangement = Arrangement.spacedBy(6.dp),
                    contentPadding = PaddingValues(bottom = 80.dp),
                ) {
                    items(filteredFiles) { file ->
                        FileGridItem(file, onClick = { viewModel.selectFile(file) })
                    }
                }
            } else {
                LazyColumn(
                    modifier = Modifier.fillMaxSize().padding(horizontal = 14.dp),
                    verticalArrangement = Arrangement.spacedBy(2.dp),
                    contentPadding = PaddingValues(bottom = 80.dp),
                ) {
                    items(filteredFiles) { file ->
                        FileListItem(file, onClick = { viewModel.selectFile(file) })
                    }
                }
            }
        }

        // Error snackbar
        AnimatedVisibility(
            visible = state.error != null,
            enter = slideInVertically { it } + fadeIn(),
            exit = slideOutVertically { it } + fadeOut(),
            modifier = Modifier.align(Alignment.BottomCenter).padding(bottom = 80.dp),
        ) {
            Surface(color = MiyaColors.Error.copy(alpha = 0.15f), shape = RoundedCornerShape(10.dp)) {
                Row(Modifier.padding(horizontal = 16.dp, vertical = 8.dp), verticalAlignment = Alignment.CenterVertically) {
                    Icon(Icons.Default.Error, null, tint = MiyaColors.Error, modifier = Modifier.size(16.dp))
                    Spacer(Modifier.width(8.dp))
                    Text(state.error ?: "", style = MaterialTheme.typography.bodySmall, color = MiyaColors.Error)
                    Spacer(Modifier.width(8.dp))
                    IconButton(onClick = { viewModel.clearError() }, modifier = Modifier.size(24.dp)) {
                        Icon(Icons.Default.Close, null, tint = MiyaColors.Error, modifier = Modifier.size(14.dp))
                    }
                }
            }
        }
    }
}

@Composable
private fun FileGridItem(file: LocalFileItem, onClick: () -> Unit) {
    Card(
        modifier = Modifier.fillMaxWidth().aspectRatio(1f).clickable(onClick = onClick),
        shape = RoundedCornerShape(12.dp),
        colors = CardDefaults.cardColors(containerColor = Color(0xFF2D2228)),
    ) {
        Box(Modifier.fillMaxSize()) {
            if (file.isImage) {
                AsyncImage(
                    model = ImageRequest.Builder(LocalContext.current).data(file.uri).size(256).crossfade(true).build(),
                    contentDescription = file.name,
                    modifier = Modifier.fillMaxSize(),
                    contentScale = ContentScale.Crop,
                )
            } else {
                Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                    Column(horizontalAlignment = Alignment.CenterHorizontally) {
                        Icon(Icons.Default.Description, null, tint = MiyaColors.Secondary, modifier = Modifier.size(32.dp))
                        Spacer(Modifier.height(4.dp))
                        Text(file.name, maxLines = 1, overflow = TextOverflow.Ellipsis, style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant, modifier = Modifier.padding(horizontal = 4.dp))
                    }
                }
            }
            Box(Modifier.align(Alignment.BottomStart).fillMaxWidth().background(Color.Black.copy(alpha = 0.45f)).padding(horizontal = 4.dp, vertical = 2.dp)) {
                Text(file.formattedDate, style = MaterialTheme.typography.labelSmall, color = Color.White, maxLines = 1)
            }
        }
    }
}

@Composable
private fun FileListItem(file: LocalFileItem, onClick: () -> Unit) {
    Row(
        Modifier.fillMaxWidth().clip(RoundedCornerShape(10.dp)).clickable(onClick = onClick).padding(horizontal = 4.dp, vertical = 8.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Box(
            Modifier.size(40.dp).clip(RoundedCornerShape(8.dp))
                .background(if (file.isImage) MiyaColors.Primary.copy(alpha = 0.1f) else MiyaColors.Secondary.copy(alpha = 0.1f)),
            contentAlignment = Alignment.Center,
        ) {
            if (file.isImage) {
                AsyncImage(
                    model = ImageRequest.Builder(LocalContext.current).data(file.uri).size(80).crossfade(true).build(),
                    contentDescription = null,
                    modifier = Modifier.fillMaxSize().clip(RoundedCornerShape(8.dp)),
                    contentScale = ContentScale.Crop,
                )
            } else {
                Icon(Icons.Default.Description, null, tint = MiyaColors.Secondary, modifier = Modifier.size(20.dp))
            }
        }
        Spacer(Modifier.width(10.dp))
        Column(Modifier.weight(1f)) {
            Text(file.name, style = MaterialTheme.typography.bodyMedium, maxLines = 1, overflow = TextOverflow.Ellipsis)
            Text("${file.formattedSize} · ${file.formattedDate}", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
    }
}

@Composable
private fun AnalysisResultCard(result: AnalysisResult) {
    Surface(
        color = Color(0xFF2D2228).copy(alpha = 0.92f),
        shape = RoundedCornerShape(12.dp),
    ) {
        Column(Modifier.padding(12.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(
                    if (result.isImage) Icons.Default.Image else Icons.Default.Description,
                    null,
                    tint = if (result.isImage) MiyaColors.Primary else MiyaColors.Secondary,
                    modifier = Modifier.size(18.dp),
                )
                Spacer(Modifier.width(8.dp))
                Text(result.fileName, style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.Medium, maxLines = 1, overflow = TextOverflow.Ellipsis)
                Spacer(Modifier.weight(1f))
                Text(formatTimestamp(result.timestamp), style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
            Spacer(Modifier.height(6.dp))
            Text(result.response, style = MaterialTheme.typography.bodySmall, lineHeight = 18.sp, maxLines = 6, overflow = TextOverflow.Ellipsis, color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.85f))
        }
    }
}

private fun getFileName(context: android.content.Context, uri: Uri): String? {
    return try {
        context.contentResolver.query(uri, null, null, null, null)?.use { cursor ->
            val idx = cursor.getColumnIndex(android.provider.OpenableColumns.DISPLAY_NAME)
            if (cursor.moveToFirst() && idx >= 0) cursor.getString(idx) else null
        }
    } catch (_: Exception) {
        uri.lastPathSegment
    }
}

private fun formatTimestamp(ts: Long): String {
    if (ts == 0L) return ""
    val cal = java.util.Calendar.getInstance().apply { timeInMillis = ts }
    return String.format("%02d:%02d", cal.get(java.util.Calendar.HOUR_OF_DAY), cal.get(java.util.Calendar.MINUTE))
}
