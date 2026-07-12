package ai.miya.network

import ai.miya.model.*
import io.ktor.client.*
import io.ktor.client.call.*
import io.ktor.client.plugins.*
import io.ktor.client.plugins.contentnegotiation.*
import io.ktor.client.plugins.logging.*
import io.ktor.client.request.*
import io.ktor.client.statement.*
import io.ktor.http.*
import io.ktor.serialization.kotlinx.json.*
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flow
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.jsonPrimitive

class MiyaApiClient(
    baseUrl: String = "http://localhost:8000",
) {
    var baseUrl: String = baseUrl
        private set

    fun updateBaseUrl(newBaseUrl: String) {
        baseUrl = newBaseUrl
    }

    private val json = Json {
        ignoreUnknownKeys = true
        isLenient = true
        encodeDefaults = true
    }

    private val client = HttpClient {
        install(ContentNegotiation) {
            json(this@MiyaApiClient.json)
        }
        install(Logging) {
            level = LogLevel.HEADERS
        }
        install(HttpTimeout) {
            requestTimeoutMillis = 120_000
            connectTimeoutMillis = 10_000
        }
        defaultRequest {
            contentType(ContentType.Application.Json)
        }
    }

    private fun apiUrl(path: String): String = "$baseUrl$path"

    // ── 健康检查 ──

    suspend fun health(): Boolean {
        return try {
            client.get(apiUrl("/health")).status == HttpStatusCode.OK
        } catch (_: Exception) {
            false
        }
    }

    // ── 系统状态 ──

    suspend fun systemStatus(): SystemStatus {
        return client.get(apiUrl("/api/status")).body()
    }

    // ── 情感 ──

    suspend fun getEmotion(): EmotionResponse {
        return client.get(apiUrl("/api/emotion")).body()
    }

    // ── 聊天 (非流式) ──

    suspend fun sendMessage(request: ChatRequest): ChatResponse {
        val response = client.post(apiUrl("/api/chat")) {
            setBody(request)
        }
        return response.body()
    }

    // ── 聊天 (SSE 流式) ──
    // 后端发送 SSE 格式: data: {"type":"plain","data":"..."}\n\n
    // 使用 bodyAsText() 全量读取，彻底避免 Ktor CIO 流式 read 兼容性问题

    fun chatStream(request: ChatRequest): Flow<String> = flow {
        val rawBody: String = client.post(apiUrl("/api/chat/send")) {
            setBody(request)
            headers { append(HttpHeaders.Accept, "text/event-stream") }
        }.bodyAsText()

        val events = rawBody.split("\n\n")
        for (rawEvent in events) {
            val trimmed = rawEvent.trim()
            if (trimmed.isEmpty() || !trimmed.startsWith("data:")) continue

            val rawData = trimmed.removePrefix("data:").trimStart()
            if (rawData.isEmpty()) continue

            try {
                val obj = json.decodeFromString<JsonObject>(rawData)
                when (obj["type"]?.jsonPrimitive?.content) {
                    "plain" -> obj["data"]?.jsonPrimitive?.content?.let { emit(it) }
                    "error" -> {
                        val msg = obj["message"]?.jsonPrimitive?.content ?: "未知错误"
                        emit("[错误] $msg")
                    }
                }
            } catch (_: Exception) {
                if (rawData.isNotEmpty() && !rawData.startsWith("{")) {
                    emit(rawData)
                }
            }
        }
    }

    suspend fun stopChat(): Boolean {
        return try {
            client.post(apiUrl("/api/chat/stop"))
            true
        } catch (_: Exception) {
            false
        }
    }

    // ── 会话管理 ──

    suspend fun listSessions(): List<SessionInfo> {
        return try {
            client.get(apiUrl("/api/chat/sessions")).body()
        } catch (_: Exception) {
            emptyList()
        }
    }

    suspend fun newSession(): NewSessionResponse {
        return client.get(apiUrl("/api/chat/new_session")).body()
    }

    suspend fun deleteSession(sessionId: String) {
        client.get(apiUrl("/api/chat/delete_session?session_id=$sessionId"))
    }

    suspend fun updateSessionName(sessionId: String, name: String) {
        client.post(apiUrl("/api/chat/update_session_display_name")) {
            setBody(RenameSessionRequest(sessionId, name))
        }
    }

    // ── 记忆 ──

    suspend fun getMemoryStats(): MemoryStats {
        return client.get(apiUrl("/api/memory/stats")).body()
    }

    suspend fun searchMemory(query: String, limit: Int = 20): List<MemoryItem> {
        return try {
            val response: MemoryListResponse = client.get(
                apiUrl("/api/memory/search?query=$query&limit=$limit")
            ).body()
            response.results
        } catch (_: Exception) {
            emptyList()
        }
    }

    suspend fun getMemoryList(limit: Int = 50): List<MemoryItem> {
        return try {
            val response: MemoryListResponse = client.get(
                apiUrl("/api/memory/list?limit=$limit")
            ).body()
            response.results
        } catch (_: Exception) {
            emptyList()
        }
    }

    // ── 人格 ──

    suspend fun getPersonaList(): List<Persona> {
        return try {
            val response: PersonaListResponse = client.get(
                apiUrl("/api/persona/list")
            ).body()
            response.personalities
        } catch (_: Exception) {
            emptyList()
        }
    }

    suspend fun getCurrentPersona(): PersonaCurrentResponse {
        return client.get(apiUrl("/api/persona/current")).body()
    }

    suspend fun switchPersona(personalityId: String): SwitchPersonaResponse {
        return client.post(apiUrl("/api/persona/switch")) {
            setBody(SwitchPersonaRequest(personalityId))
        }.body()
    }

    // ── TTS ──

    suspend fun textToSpeech(
        text: String,
        voice: String? = null,
        speed: Float = 1.0f,
        engine: String = "edge_tts",
    ): ByteArray? {
        return try {
            val response = client.post(apiUrl("/tts/speech")) {
                setBody(mapOf(
                    "input" to text,
                    "voice" to voice,
                    "speed" to speed,
                    "engine" to engine,
                    "response_format" to "mp3",
                ))
            }
            response.body<ByteArray>()
        } catch (_: Exception) {
            null
        }
    }

    // ── 模型 ──

    suspend fun getModelList(): List<Map<String, String>> {
        return try {
            client.get(apiUrl("/api/models/list")).body()
        } catch (_: Exception) {
            emptyList()
        }
    }

    fun close() {
        client.close()
    }
}
