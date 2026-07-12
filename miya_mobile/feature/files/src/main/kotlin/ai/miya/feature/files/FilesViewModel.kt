package ai.miya.feature.files

import ai.miya.domain.ServiceRegistry
import ai.miya.domain.ChatProvider
import ai.miya.model.ChatRequest
import android.content.Context
import android.net.Uri
import android.provider.OpenableColumns
import android.util.Base64
import android.os.Environment
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.io.File
import java.text.SimpleDateFormat
import java.util.Locale

data class FilesUiState(
    val deviceFiles: List<LocalFileItem> = emptyList(),
    val analysisResults: List<AnalysisResult> = emptyList(),
    val isLoading: Boolean = false,
    val selectedFile: LocalFileItem? = null,
    val currentAnalysis: String = "",
    val isAnalyzing: Boolean = false,
    val error: String? = null,
    val filterType: FileFilterType = FileFilterType.ALL,
)

data class LocalFileItem(
    val uri: Uri,
    val name: String,
    val size: Long,
    val mimeType: String,
    val lastModified: Long,
    val isImage: Boolean,
) {
    val formattedSize: String get() = when {
        size < 1024 -> "${size}B"
        size < 1024 * 1024 -> "${size / 1024}KB"
        size < 1024 * 1024 * 1024 -> "${"%.1f".format(size.toFloat() / (1024 * 1024))}MB"
        else -> "${"%.2f".format(size.toFloat() / (1024 * 1024 * 1024))}GB"
    }
    val formattedDate: String get() {
        val sdf = SimpleDateFormat("MM-dd HH:mm", Locale.getDefault())
        return sdf.format(java.util.Date(lastModified))
    }
}

data class AnalysisResult(
    val id: String,
    val fileName: String,
    val mimeType: String,
    val timestamp: Long,
    val response: String,
    val isImage: Boolean,
)

enum class FileFilterType(val label: String) {
    ALL("全部"),
    IMAGES("图片"),
    DOCUMENTS("文档"),
    RESULTS("分析结果"),
}

class FilesViewModel : ViewModel() {

    private val _state = MutableStateFlow(FilesUiState())
    val state: StateFlow<FilesUiState> = _state.asStateFlow()

    fun loadFiles(context: Context) {
        viewModelScope.launch {
            _state.update { it.copy(isLoading = true) }
            val files = withContext(Dispatchers.IO) {
                scanDeviceFiles(context)
            }
            _state.update { it.copy(deviceFiles = files, isLoading = false) }
        }
    }

    fun setFilter(filter: FileFilterType) {
        _state.update { it.copy(filterType = filter) }
    }

    fun selectFile(file: LocalFileItem) {
        _state.update { it.copy(selectedFile = file, currentAnalysis = "") }
    }

    fun clearSelection() {
        _state.update { it.copy(selectedFile = null, currentAnalysis = "") }
    }

    fun sendToMiya(context: Context) {
        val file = _state.value.selectedFile ?: return
        if (_state.value.isAnalyzing) return

        viewModelScope.launch {
            _state.update { it.copy(isAnalyzing = true, error = null, currentAnalysis = "") }
            try {
                if (file.isImage) {
                    sendImageToMiya(context, file)
                } else {
                    sendFileToMiya(context, file)
                }
            } catch (e: Exception) {
                _state.update { it.copy(error = "发送失败: ${e.message}", isAnalyzing = false) }
            }
        }
    }

    private suspend fun sendImageToMiya(context: Context, file: LocalFileItem) {
        val bytes = readBytes(context, file.uri)
        val mine = file.mimeType.ifEmpty { "image/jpeg" }
        val base64 = "data:$mine;base64,${Base64.encodeToString(bytes, Base64.NO_WRAP)}"

        val cp = ServiceRegistry.getOrThrow(ChatProvider::class.java)
        val request = ChatRequest(
            message = "请分析这张图片",
            sessionId = "files",
            platform = "mobile",
            imageData = base64,
        )

        val sb = StringBuilder()
        cp.streamChat(request).collect { chunk -> sb.append(chunk); _state.update { it.copy(currentAnalysis = sb.toString()) } }

        val result = AnalysisResult(
            id = "r_${System.currentTimeMillis()}",
            fileName = file.name,
            mimeType = file.mimeType,
            timestamp = System.currentTimeMillis(),
            response = sb.toString(),
            isImage = true,
        )
        _state.update { it.copy(analysisResults = listOf(result) + it.analysisResults, isAnalyzing = false) }
    }

    private suspend fun sendFileToMiya(context: Context, file: LocalFileItem) {
        val content = readText(context, file.uri)
        val cp = ServiceRegistry.getOrThrow(ChatProvider::class.java)
        val request = ChatRequest(
            message = "请分析这个文件:\n\n--- ${file.name} ---\n$content",
            sessionId = "files",
            platform = "mobile",
        )

        val sb = StringBuilder()
        cp.streamChat(request).collect { chunk -> sb.append(chunk); _state.update { it.copy(currentAnalysis = sb.toString()) } }

        val result = AnalysisResult(
            id = "r_${System.currentTimeMillis()}",
            fileName = file.name,
            mimeType = file.mimeType,
            timestamp = System.currentTimeMillis(),
            response = sb.toString(),
            isImage = false,
        )
        _state.update { it.copy(analysisResults = listOf(result) + it.analysisResults, isAnalyzing = false) }
    }

    fun stopAnalysis() {
        viewModelScope.launch {
            try { ServiceRegistry.getOrThrow(ChatProvider::class.java).stopChat() } catch (_: Exception) {}
        }
        _state.update { it.copy(isAnalyzing = false) }
    }

    fun clearError() {
        _state.update { it.copy(error = null) }
    }

    private suspend fun scanDeviceFiles(context: Context): List<LocalFileItem> = withContext(Dispatchers.IO) {
        val files = mutableListOf<LocalFileItem>()

        val projection = arrayOf(
            android.provider.MediaStore.Files.FileColumns._ID,
            android.provider.MediaStore.Files.FileColumns.DATA,
            android.provider.MediaStore.Files.FileColumns.DISPLAY_NAME,
            android.provider.MediaStore.Files.FileColumns.SIZE,
            android.provider.MediaStore.Files.FileColumns.MIME_TYPE,
            android.provider.MediaStore.Files.FileColumns.DATE_MODIFIED,
        )

        val selection = "${android.provider.MediaStore.Files.FileColumns.MIME_TYPE} LIKE 'image/%' OR " +
            "${android.provider.MediaStore.Files.FileColumns.MIME_TYPE} LIKE 'application/pdf' OR " +
            "${android.provider.MediaStore.Files.FileColumns.MIME_TYPE} LIKE 'text/%' OR " +
            "${android.provider.MediaStore.Files.FileColumns.MIME_TYPE} LIKE 'application/msword' OR " +
            "${android.provider.MediaStore.Files.FileColumns.MIME_TYPE} LIKE 'application/vnd.openxmlformats%' OR " +
            "${android.provider.MediaStore.Files.FileColumns.MIME_TYPE} LIKE 'application/vnd.ms-%'"

        try {
            context.contentResolver.query(
                android.provider.MediaStore.Files.getContentUri("external"),
                projection,
                selection,
                null,
                "${android.provider.MediaStore.Files.FileColumns.DATE_MODIFIED} DESC"
            )?.use { cursor ->
                val nameIdx = cursor.getColumnIndexOrThrow(android.provider.MediaStore.Files.FileColumns.DISPLAY_NAME)
                val sizeIdx = cursor.getColumnIndexOrThrow(android.provider.MediaStore.Files.FileColumns.SIZE)
                val mimeIdx = cursor.getColumnIndexOrThrow(android.provider.MediaStore.Files.FileColumns.MIME_TYPE)
                val dateIdx = cursor.getColumnIndexOrThrow(android.provider.MediaStore.Files.FileColumns.DATE_MODIFIED)
                val idIdx = cursor.getColumnIndexOrThrow(android.provider.MediaStore.Files.FileColumns._ID)

                while (cursor.moveToNext() && files.size < 100) {
                    val id = cursor.getLong(idIdx)
                    val name = cursor.getString(nameIdx) ?: "unknown"
                    val size = cursor.getLong(sizeIdx)
                    val mine = cursor.getString(mimeIdx) ?: "application/octet-stream"
                    val date = cursor.getLong(dateIdx) * 1000L
                    val uri = Uri.withAppendedPath(
                        android.provider.MediaStore.Files.getContentUri("external"),
                        id.toString()
                    )
                    files.add(LocalFileItem(uri, name, size, mine, date, mine.startsWith("image/")))
                }
            }
        } catch (_: Exception) {
            // MediaStore may not be available
        }

        files
    }

    private fun readBytes(c: Context, u: Uri) =
        c.contentResolver.openInputStream(u)?.use { it.readBytes() } ?: ByteArray(0)

    private fun readText(c: Context, u: Uri) = try {
        c.contentResolver.openInputStream(u)?.bufferedReader()?.readText()?.take(8000) ?: ""
    } catch (_: Exception) {
        "[无法读取文件内容]"
    }
}
