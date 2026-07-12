package ai.miya.feature.chat

import ai.miya.domain.ServiceRegistry
import ai.miya.domain.ChatProvider
import ai.miya.domain.SessionProvider
import ai.miya.model.*
import android.content.Context
import android.net.Uri
import android.provider.OpenableColumns
import android.util.Base64
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.*
import kotlinx.coroutines.flow.*

data class ChatUiState(
    val messages: List<ChatMessage> = emptyList(),
    val inputText: String = "",
    val isStreaming: Boolean = false,
    val streamedText: String = "",
    val sessions: List<SessionInfo> = emptyList(),
    val currentSessionId: String = "default",
    val error: String? = null,
    val showSessionPicker: Boolean = false,
    val showAttachmentPicker: Boolean = false,
)

data class ChatMessage(
    val id: String,
    val content: String,
    val role: String,
    val timestamp: Long,
    val imageBase64: String? = null,
    val fileName: String? = null,
    val fileSize: Long? = null,
    val fileMimeType: String? = null,
) {
    val isUser: Boolean get() = role == "user"
    val hasImage: Boolean get() = imageBase64 != null
    val hasFile: Boolean get() = fileName != null && imageBase64 == null
}

class ChatViewModel : androidx.lifecycle.ViewModel() {

    private val _state = MutableStateFlow(ChatUiState())
    val state: StateFlow<ChatUiState> = _state.asStateFlow()

    fun init() { loadSessions() }

    fun loadSessions() {
        viewModelScope.launch {
            try { _state.update { it.copy(sessions = ServiceRegistry.getOrThrow(SessionProvider::class.java).getSessions()) } } catch (_: Exception) {}
        }
    }

    fun selectSession(id: String) { _state.update { it.copy(currentSessionId = id, messages = emptyList(), showSessionPicker = false) } }

    fun newSession() {
        viewModelScope.launch {
            try {
                val id = ServiceRegistry.getOrThrow(SessionProvider::class.java).newSession()
                _state.update { it.copy(currentSessionId = id, messages = emptyList(), streamedText = "", showSessionPicker = false) }
                loadSessions()
            } catch (e: Exception) { _state.update { it.copy(error = "创建失败: ${e.message}") } }
        }
    }

    fun deleteSession(id: String) {
        viewModelScope.launch {
            try {
                ServiceRegistry.getOrThrow(SessionProvider::class.java).deleteSession(id)
                loadSessions()
                if (_state.value.currentSessionId == id) _state.update { it.copy(currentSessionId = "default", messages = emptyList()) }
            } catch (_: Exception) {}
        }
    }

    fun deleteMessage(id: String) {
        _state.update { it.copy(messages = it.messages.filter { m -> m.id != id }) }
    }

    fun onInputChange(text: String) { _state.update { it.copy(inputText = text, error = null) } }
    fun toggleSessionPicker() { _state.update { it.copy(showSessionPicker = !it.showSessionPicker) } }
    fun toggleAttachmentPicker() { _state.update { it.copy(showAttachmentPicker = !it.showAttachmentPicker) } }
    fun clearError() { _state.update { it.copy(error = null) } }

    fun sendMessage() {
        val text = _state.value.inputText.trim()
        if (text.isEmpty() || _state.value.isStreaming) return
        val msg = ChatMessage("u_${System.currentTimeMillis()}", text, "user", System.currentTimeMillis())
        _state.update { it.copy(messages = it.messages + msg, inputText = "", isStreaming = true, streamedText = "", error = null) }
        doStream(ChatRequest(message = text, sessionId = _state.value.currentSessionId, platform = "mobile"))
    }

    fun sendWithImage(context: Context, uri: Uri) {
        if (_state.value.isStreaming) return
        viewModelScope.launch {
            try {
                val bytes = readBytes(context, uri)
                val mime = context.contentResolver.getType(uri) ?: "image/jpeg"
                val name = getFileName(context, uri) ?: "图片"
                val size = bytes.size.toLong()
                val base64 = "data:$mime;base64,${Base64.encodeToString(bytes, Base64.NO_WRAP)}"
                val text = _state.value.inputText.ifEmpty { "请查看图片" }
                _state.update { it.copy(
                    messages = it.messages + ChatMessage("u_${System.currentTimeMillis()}", text, "user", System.currentTimeMillis(), imageBase64 = base64, fileName = name, fileSize = size, fileMimeType = mime),
                    inputText = "", isStreaming = true, streamedText = "", showAttachmentPicker = false,
                ) }
                doStream(ChatRequest(message = text, sessionId = _state.value.currentSessionId, platform = "mobile", imageData = base64))
            } catch (e: Exception) { _state.update { it.copy(error = "图片发送失败: ${e.message}") } }
        }
    }

    fun sendWithTextFile(context: Context, uri: Uri) {
        if (_state.value.isStreaming) return
        viewModelScope.launch {
            try {
                val name = getFileName(context, uri) ?: "文件"
                val mime = context.contentResolver.getType(uri) ?: "application/octet-stream"
                val size = getFileSize(context, uri)
                val content = readText(context, uri)
                val fullText = "${_state.value.inputText}\n\n--- $name ---\n$content"
                val displayText = _state.value.inputText.ifEmpty { "请查看附件: $name" }
                _state.update { it.copy(
                    messages = it.messages + ChatMessage("u_${System.currentTimeMillis()}", displayText, "user", System.currentTimeMillis(), fileName = name, fileSize = size, fileMimeType = mime),
                    inputText = "", isStreaming = true, streamedText = "", showAttachmentPicker = false,
                ) }
                doStream(ChatRequest(message = fullText, sessionId = _state.value.currentSessionId, platform = "mobile"))
            } catch (e: Exception) { _state.update { it.copy(error = "文件发送失败: ${e.message}") } }
        }
    }

    private fun doStream(request: ChatRequest) {
        viewModelScope.launch {
            try {
                val cp = ServiceRegistry.getOrThrow(ChatProvider::class.java)
                val sb = StringBuilder()
                cp.streamChat(request).collect { chunk -> sb.append(chunk); _state.update { it.copy(streamedText = sb.toString()) } }
                _state.update { it.copy(messages = it.messages + ChatMessage("a_${System.currentTimeMillis()}", sb.toString().cleanAiContent(), "assistant", System.currentTimeMillis()), isStreaming = false, streamedText = "") }
            } catch (_: CancellationException) { _state.update { it.copy(isStreaming = false, streamedText = "") } }
            catch (e: Exception) { _state.update { it.copy(isStreaming = false, streamedText = "", error = "发送失败: ${e.message}") } }
        }
    }

    fun stopStreaming() {
        viewModelScope.launch { try { ServiceRegistry.getOrThrow(ChatProvider::class.java).stopChat() } catch (_: Exception) {} }
        _state.update { it.copy(isStreaming = false) }
    }

    private fun getFileName(c: Context, u: Uri) = try { c.contentResolver.query(u, null, null, null, null)?.use { cur -> val i = cur.getColumnIndex(OpenableColumns.DISPLAY_NAME); if (cur.moveToFirst() && i >= 0) cur.getString(i) else null } } catch (_: Exception) { null }
    private fun getFileSize(c: Context, u: Uri) = try { c.contentResolver.query(u, null, null, null, null)?.use { cur -> val i = cur.getColumnIndex(OpenableColumns.SIZE); if (cur.moveToFirst() && i >= 0) cur.getLong(i) else 0L } } catch (_: Exception) { 0L }
    private fun readBytes(c: Context, u: Uri) = c.contentResolver.openInputStream(u)?.use { it.readBytes() } ?: ByteArray(0)
    private fun readText(c: Context, u: Uri) = try { c.contentResolver.openInputStream(u)?.bufferedReader()?.readText() ?: "" } catch (_: Exception) { "[无法读取]" }

    private fun String.cleanAiContent() = this
        .replace(Regex("<think>.*?</think>", RegexOption.DOT_MATCHES_ALL), "")
        .replace(Regex("\n{3,}"), "\n\n").trim()
}
