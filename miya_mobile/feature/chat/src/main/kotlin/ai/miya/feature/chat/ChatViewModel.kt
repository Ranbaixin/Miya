package ai.miya.feature.chat

import ai.miya.database.MessageEntity
import ai.miya.database.MiyaDatabase
import ai.miya.domain.ServiceRegistry
import ai.miya.domain.ChatProvider
import ai.miya.domain.SessionProvider
import ai.miya.model.*
import ai.miya.network.MiyaApiClient
import android.app.Application
import android.content.Context
import android.graphics.BitmapFactory
import android.net.Uri
import android.provider.OpenableColumns
import android.util.Base64
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.*
import kotlinx.coroutines.flow.*
import java.io.ByteArrayOutputStream

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
    val showStickerPicker: Boolean = false,
    val imageCaption: String = "",
    val pendingImageUri: Uri? = null,
    val pendingFileUri: Uri? = null,
    val fileCaption: String = "",
    val quotedMessage: ChatMessage? = null,
    val poked: Boolean = false,
)

data class ChatMessage(
    val id: String,
    val content: String,
    val role: String,
    val timestamp: Long,
    val imageBase64: String? = null,
    val imageUrl: String? = null,
    val fileName: String? = null,
    val fileSize: Long? = null,
    val fileMimeType: String? = null,
    val quotedId: String? = null,
    val quotedContent: String? = null,
) {
    val isUser: Boolean get() = role == "user"
    val hasImage: Boolean get() = imageBase64 != null || imageUrl != null
    val imageSrc: String? get() = imageBase64 ?: imageUrl
    val hasFile: Boolean get() = fileName != null && imageBase64 == null && imageUrl == null
    val hasQuote: Boolean get() = quotedContent != null
    fun contentPreview(maxLen: Int = 50): String =
        if (content.length <= maxLen) content else content.take(maxLen) + "…"
}

val COMMON_STICKERS = listOf(
    "😀" to "笑脸", "😂" to "笑哭", "😍" to "喜欢", "😭" to "大哭",
    "😡" to "生气", "😱" to "震惊", "😴" to "睡觉", "🤔" to "思考",
    "👍" to "赞", "❤️" to "爱心", "🎉" to "庆祝", "🔥" to "火",
    "🥺" to "委屈", "🙏" to "祈祷", "💪" to "加油", "✨" to "闪亮",
    "🐱" to "猫猫", "🐶" to "狗狗", "🌸" to "花花", "⭐" to "星星",
    "🍰" to "蛋糕", "☕" to "咖啡", "📱" to "手机", "💻" to "电脑",
)

class ChatViewModel(application: Application) : AndroidViewModel(application) {

    private val _state = MutableStateFlow(ChatUiState())
    val state: StateFlow<ChatUiState> = _state.asStateFlow()

    private val db by lazy { MiyaDatabase.getInstance(getApplication()) }
    private val messageDao by lazy { db.messageDao() }

    fun init() { loadSessions(); startProactivePolling() }

    private fun startProactivePolling() {
        viewModelScope.launch {
            while (isActive) {
                delay(15_000)
                try {
                    val api = ServiceRegistry.get(MiyaApiClient::class.java) ?: continue
                    val msgs = api.getPendingMessages("default")
                    for (msg in msgs) {
                        val text = msg["message"] ?: continue
                        val aiMsg = ChatMessage("p_${System.currentTimeMillis()}", text, "assistant", System.currentTimeMillis())
                        _state.update { it.copy(messages = it.messages + aiMsg) }
                        saveToDb(aiMsg)
                    }
                } catch (_: Exception) {}
            }
        }
    }

    fun loadSessions() {
        viewModelScope.launch {
            try { _state.update { it.copy(sessions = ServiceRegistry.getOrThrow(SessionProvider::class.java).getSessions()) } } catch (_: Exception) {}
        }
    }

    fun selectSession(id: String) {
        _state.update { it.copy(currentSessionId = id, messages = emptyList(), showSessionPicker = false, quotedMessage = null) }
        loadMessages(id)
    }

    private fun loadMessages(sessionId: String) {
        viewModelScope.launch {
            try {
                val entities = messageDao.getMessages(sessionId)
                val messages = entities.map { e ->
                    ChatMessage(e.id, e.content, e.role, e.timestamp, e.imageBase64, null, e.fileName, e.fileSize, e.fileMimeType)
                }
                _state.update { it.copy(messages = messages) }
            } catch (_: Exception) {}
        }
    }

    fun newSession() {
        viewModelScope.launch {
            try {
                val id = ServiceRegistry.getOrThrow(SessionProvider::class.java).newSession()
                _state.update { it.copy(currentSessionId = id, messages = emptyList(), streamedText = "", showSessionPicker = false, quotedMessage = null) }
                loadSessions()
            } catch (e: Exception) { _state.update { it.copy(error = "创建失败: ${e.message}") } }
        }
    }

    fun deleteSession(id: String) {
        viewModelScope.launch {
            try {
                ServiceRegistry.getOrThrow(SessionProvider::class.java).deleteSession(id)
                messageDao.deleteBySession(id)
                loadSessions()
                if (_state.value.currentSessionId == id) _state.update { it.copy(currentSessionId = "default", messages = emptyList()) }
            } catch (_: Exception) {}
        }
    }

    fun deleteMessage(id: String) {
        _state.update { it.copy(messages = it.messages.filter { m -> m.id != id }) }
        viewModelScope.launch { try { messageDao.deleteById(id) } catch (_: Exception) {} }
    }

    fun onInputChange(text: String) { _state.update { it.copy(inputText = text, error = null) } }
    fun toggleSessionPicker() { _state.update { it.copy(showSessionPicker = !it.showSessionPicker) } }
    fun toggleAttachmentPicker() { _state.update { it.copy(showAttachmentPicker = !it.showAttachmentPicker, showStickerPicker = false) } }
    fun toggleStickerPicker() { _state.update { it.copy(showStickerPicker = !it.showStickerPicker, showAttachmentPicker = false) } }
    fun clearError() { _state.update { it.copy(error = null) } }

    // ── Quote ──
    fun setQuotedMessage(msg: ChatMessage?) { _state.update { it.copy(quotedMessage = msg) } }
    fun clearQuote() { _state.update { it.copy(quotedMessage = null) } }

    // ── Image caption ──
    fun setPendingImage(uri: Uri) { _state.update { it.copy(pendingImageUri = uri, imageCaption = "", showAttachmentPicker = false) } }
    fun onImageCaptionChange(text: String) { _state.update { it.copy(imageCaption = text) } }
    fun cancelImageCaption() { _state.update { it.copy(pendingImageUri = null, imageCaption = "") } }
    fun confirmImageSend(context: Context) {
        val uri = _state.value.pendingImageUri ?: return
        sendWithImage(context, uri, _state.value.imageCaption.ifEmpty { null })
    }

    // ── File caption ──
    fun setPendingFile(uri: Uri) { _state.update { it.copy(pendingFileUri = uri, fileCaption = _state.value.inputText, showAttachmentPicker = false) } }
    fun onFileCaptionChange(text: String) { _state.update { it.copy(fileCaption = text) } }
    fun cancelFileCaption() { _state.update { it.copy(pendingFileUri = null, fileCaption = "") } }
    fun confirmFileSend(context: Context) {
        val uri = _state.value.pendingFileUri ?: return
        sendWithTextFile(context, uri, _state.value.fileCaption.ifEmpty { null })
    }

    // ── Poke ──
    fun sendPoke() {
        if (_state.value.isStreaming) return
        val msg = ChatMessage("u_${System.currentTimeMillis()}", "拍了拍弥娅", "user", System.currentTimeMillis())
        _state.update { it.copy(messages = it.messages + msg, poked = true) }
        saveToDb(msg)
        doStream(ChatRequest(message = "/poke", sessionId = _state.value.currentSessionId, platform = "mobile"))
    }

    // ── Sticker ──
    fun sendSticker(emoji: String) {
        if (_state.value.isStreaming) return
        val msg = ChatMessage("u_${System.currentTimeMillis()}", emoji, "user", System.currentTimeMillis())
        _state.update { it.copy(messages = it.messages + msg, inputText = "", showStickerPicker = false) }
        saveToDb(msg)
        doStream(ChatRequest(message = emoji, sessionId = _state.value.currentSessionId, platform = "mobile"))
    }

    // ── Draw ──
    fun sendDrawCommand() {
        val text = _state.value.inputText.trim()
        if (text.isEmpty() || _state.value.isStreaming) return
        val drawText = if (text.startsWith("/draw")) text else "/draw $text"
        val msg = ChatMessage("u_${System.currentTimeMillis()}", text, "user", System.currentTimeMillis())
        _state.update { it.copy(messages = it.messages + msg, inputText = "", isStreaming = true, streamedText = "", error = null) }
        saveToDb(msg)
        doStream(ChatRequest(message = drawText, sessionId = _state.value.currentSessionId, platform = "mobile"))
    }

    fun sendMessage() {
        val text = _state.value.inputText.trim()
        if (text.isEmpty() || _state.value.isStreaming) return
        if (text.startsWith("/draw") || text.startsWith("/画")) { sendDrawCommand(); return }
        val quoted = _state.value.quotedMessage
        val quotedText = if (quoted != null) "「引用: ${quoted.contentPreview(80)}」\n" else ""
        val fullText = quotedText + text
        val msg = ChatMessage("u_${System.currentTimeMillis()}", text, "user", System.currentTimeMillis(),
            quotedId = quoted?.id, quotedContent = quoted?.contentPreview(80))
        _state.update { it.copy(messages = it.messages + msg, inputText = "", isStreaming = true, streamedText = "", error = null, quotedMessage = null) }
        saveToDb(msg)
        doStream(ChatRequest(message = fullText, sessionId = _state.value.currentSessionId, platform = "mobile"))
    }

    fun sendWithImage(context: Context, uri: Uri, caption: String? = null) {
        if (_state.value.isStreaming) return
        viewModelScope.launch(Dispatchers.IO) {
            try {
                val rawBytes = readBytes(context, uri)
                val mime = context.contentResolver.getType(uri) ?: "image/jpeg"
                val name = getFileName(context, uri) ?: "图片"
                val originalSize = rawBytes.size.toLong()

                val compressed = compressImage(rawBytes, mime)
                val base64 = "data:${if (compressed.any { it < 0 }) "image/jpeg" else "image/jpeg"};base64,${Base64.encodeToString(compressed, Base64.NO_WRAP)}"
                val text = caption ?: _state.value.inputText.ifEmpty { "请查看图片" }
                val msg = ChatMessage("u_${System.currentTimeMillis()}", text, "user", System.currentTimeMillis(),
                    imageBase64 = base64, fileName = name, fileSize = originalSize, fileMimeType = mime)
                _state.update { it.copy(
                    messages = it.messages + msg, inputText = "", isStreaming = true, streamedText = "",
                    showAttachmentPicker = false, pendingImageUri = null, imageCaption = "",
                ) }
                saveToDb(msg)
                doStream(ChatRequest(message = text, sessionId = _state.value.currentSessionId, platform = "mobile", imageData = base64))
            } catch (e: Exception) { _state.update { it.copy(error = "图片发送失败: ${e.message}") } }
        }
    }

    private fun compressImage(bytes: ByteArray, mime: String): ByteArray {
        return try {
            val opts = BitmapFactory.Options()
            opts.inJustDecodeBounds = true
            BitmapFactory.decodeByteArray(bytes, 0, bytes.size, opts)
            opts.inJustDecodeBounds = false
            opts.inSampleSize = maxOf(1, maxOf(opts.outWidth, opts.outHeight) / 1024)
            val bmp = BitmapFactory.decodeByteArray(bytes, 0, bytes.size, opts) ?: return bytes
            val bos = ByteArrayOutputStream()
            bmp.compress(android.graphics.Bitmap.CompressFormat.JPEG, 70, bos)
            bmp.recycle()
            bos.toByteArray()
        } catch (_: Exception) { bytes }
    }

    fun sendWithTextFile(context: Context, uri: Uri, caption: String? = null) {
        if (_state.value.isStreaming) return
        val text = caption ?: _state.value.inputText.ifEmpty { "请查看文件: ${getFileName(context, uri) ?: "文件"}" }
        viewModelScope.launch(Dispatchers.IO) {
            try {
                val name = getFileName(context, uri) ?: "文件"
                val mime = context.contentResolver.getType(uri) ?: "application/octet-stream"
                val size = getFileSize(context, uri)
                val bytes = readBytes(context, uri)

                val isTextFile = mime.startsWith("text/") ||
                    mime in listOf("application/json", "application/xml", "application/javascript", "application/x-yaml")
                val fileContent: String
                if (isTextFile) {
                    fileContent = "\n\n--- $name ---\n${String(bytes, Charsets.UTF_8).take(4000)}"
                } else {
                    val api = ServiceRegistry.get(MiyaApiClient::class.java)
                    val uploadResult = if (api != null) {
                        api.uploadFile(name, bytes, mime)
                    } else mapOf("success" to "false", "preview" to "上传失败")
                    val serverPath = uploadResult["path"] ?: name
                    fileContent = "\n[已上传: $name → $serverPath]\n[文件信息: $mime, ${formatFileSize(size ?: 0L)}]"
                }

                val fullText = "$text$fileContent"
                val msg = ChatMessage("u_${System.currentTimeMillis()}", text, "user", System.currentTimeMillis(),
                    fileName = name, fileSize = size, fileMimeType = mime)
                _state.update { it.copy(
                    messages = it.messages + msg, inputText = "", isStreaming = true, streamedText = "",
                    showAttachmentPicker = false, pendingFileUri = null, fileCaption = "",
                ) }
                saveToDb(msg)
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
                val rawText = sb.toString()
                val responseText = rawText.cleanAiContent()
                val imgUrl = extractImageUrl(rawText)
                val responseMsg = ChatMessage("a_${System.currentTimeMillis()}", responseText, "assistant", System.currentTimeMillis(),
                    imageUrl = imgUrl)
                _state.update { it.copy(messages = it.messages + responseMsg, isStreaming = false, streamedText = "") }
                saveToDb(responseMsg)
            } catch (_: CancellationException) { _state.update { it.copy(isStreaming = false, streamedText = "") } }
            catch (e: Exception) { _state.update { it.copy(isStreaming = false, streamedText = "", error = "发送失败: ${e.message}") } }
        }
    }

    private fun saveToDb(msg: ChatMessage) {
        viewModelScope.launch {
            try {
                messageDao.insert(MessageEntity(
                    id = msg.id, sessionId = _state.value.currentSessionId,
                    content = msg.content, role = msg.role, timestamp = msg.timestamp,
                    imageBase64 = msg.imageBase64, fileName = msg.fileName,
                    fileSize = msg.fileSize, fileMimeType = msg.fileMimeType,
                ))
            } catch (_: Exception) {}
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

    private fun formatFileSize(size: Long): String = when {
        size < 1024 -> "${size}B"
        size < 1024 * 1024 -> "${size / 1024}KB"
        size < 1024 * 1024 * 1024 -> "${"%.1f".format(size.toFloat() / (1024 * 1024))}MB"
        else -> "${"%.2f".format(size.toFloat() / (1024 * 1024 * 1024))}GB"
    }

    companion object {
        fun extractImageUrl(text: String): String? {
            val md = Regex("!\\[.*?\\]\\((https?://[^\\s)]+\\.(?:png|jpg|jpeg|gif|webp)(?:\\?[^\\s)]*)?)\\)")
                .find(text)?.groupValues?.getOrNull(1)
            if (md != null) return md
            val direct = Regex("(https?://[^\\s]+\\.(?:png|jpg|jpeg|gif|webp)(?:\\?[^\\s]*)?)")
                .find(text)?.groupValues?.getOrNull(1)
            return direct
        }
    }
}
