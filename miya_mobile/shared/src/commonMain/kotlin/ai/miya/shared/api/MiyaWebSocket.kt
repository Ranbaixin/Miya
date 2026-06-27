package ai.miya.shared.api

import ai.miya.shared.model.EmotionUpdate
import io.ktor.client.*
import io.ktor.client.plugins.websocket.*
import io.ktor.websocket.*
import kotlinx.coroutines.*
import kotlinx.coroutines.flow.*
import kotlinx.serialization.json.Json

sealed class WsEvent {
    data class EmotionChanged(val dominant: String, val intensity: Int) : WsEvent()
    data class MemoryStored(val memoryId: String, val preview: String) : WsEvent()
    data class PlatformMessage(val platform: String, val userId: String, val content: String) : WsEvent()
    data class PlatformStatusChanged(val platform: String, val status: String) : WsEvent()
    data class Error(val message: String) : WsEvent()
    data object Connected : WsEvent()
    data object Disconnected : WsEvent()
}

class MiyaWebSocket(
    private val baseUrl: String = "ws://localhost:9800",
) {
    private val json = Json { ignoreUnknownKeys = true; isLenient = true }
    private var session: WebSocketSession? = null
    private var job: Job? = null

    private val _events = MutableSharedFlow<WsEvent>(extraBufferCapacity = 64)
    val events: SharedFlow<WsEvent> = _events.asSharedFlow()

    fun connect(scope: CoroutineScope) {
        job?.cancel()
        job = scope.launch {
            try {
                val client = HttpClient {
                    install(WebSockets)
                }
                client.webSocket("$baseUrl/api/v1/ws") {
                    session = this
                    _events.emit(WsEvent.Connected)

                    for (frame in incoming) {
                        when (frame) {
                            is Frame.Text -> {
                                val text = frame.readText()
                                processMessage(text)
                            }
                            else -> {}
                        }
                    }
                }
            } catch (e: Exception) {
                _events.emit(WsEvent.Error(e.message ?: "WebSocket error"))
            } finally {
                session = null
                _events.emit(WsEvent.Disconnected)
            }
        }
    }

    fun disconnect() {
        job?.cancel()
        job = null
        session = null
    }

    private suspend fun processMessage(text: String) {
        try {
            val data = json.decodeFromString<kotlinx.serialization.json.JsonObject>(text)
            when (data["type"]?.toString()?.trim('"')) {
                "miya_emotion" -> {
                    val payload = data["data"]
                    val dominant = payload?.let {
                        (it as? kotlinx.serialization.json.JsonObject)?.get("dominant")?.toString()?.trim('"')
                    } ?: "neutral"
                    val intensity = payload?.let {
                        (it as? kotlinx.serialization.json.JsonObject)?.get("intensity")?.toString()?.toIntOrNull()
                    } ?: 50
                    _events.emit(WsEvent.EmotionChanged(dominant, intensity))
                }
                "memory_stored" -> {
                    val payload = data["data"]
                    val memId = payload?.let {
                        (it as? kotlinx.serialization.json.JsonObject)?.get("memory_id")?.toString()?.trim('"')
                    } ?: ""
                    val preview = payload?.let {
                        (it as? kotlinx.serialization.json.JsonObject)?.get("content_preview")?.toString()?.trim('"')
                    } ?: ""
                    _events.emit(WsEvent.MemoryStored(memId, preview))
                }
                "platform_message" -> {
                    val payload = data["data"]
                    // 解析 payload 中的字段
                    val platform = payload?.let { p ->
                        (p as? kotlinx.serialization.json.JsonObject)?.get("platform")?.toString()?.trim('"')
                    } ?: "unknown"
                    val userId = payload?.let { p ->
                        (p as? kotlinx.serialization.json.JsonObject)?.get("user_id")?.toString()?.trim('"')
                    } ?: ""
                    val content = payload?.let { p ->
                        (p as? kotlinx.serialization.json.JsonObject)?.get("content")?.toString()?.trim('"')
                    } ?: ""
                    _events.emit(WsEvent.PlatformMessage(platform, userId, content))
                }
                "platform_status" -> {
                    val payload = data["data"]
                    val platform = payload?.let { p ->
                        (p as? kotlinx.serialization.json.JsonObject)?.get("platform")?.toString()?.trim('"')
                    } ?: "unknown"
                    val status = payload?.let { p ->
                        (p as? kotlinx.serialization.json.JsonObject)?.get("status")?.toString()?.trim('"')
                    } ?: "offline"
                    _events.emit(WsEvent.PlatformStatusChanged(platform, status))
                }
            }
        } catch (_: Exception) {
            // skip malformed messages
        }
    }

    val isConnected: Boolean get() = session != null && job?.isActive == true
}
