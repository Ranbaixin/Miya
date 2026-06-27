package ai.miya.shared.api

import ai.miya.shared.model.*
import io.ktor.client.*
import io.ktor.client.call.*
import io.ktor.client.plugins.*
import io.ktor.client.plugins.contentnegotiation.*
import io.ktor.client.plugins.logging.*
import io.ktor.client.request.*
import io.ktor.client.statement.*
import io.ktor.http.*
import io.ktor.serialization.kotlinx.json.*
import io.ktor.utils.io.*
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flow
import kotlinx.serialization.json.Json

class MiyaApiClient(
    private val baseUrl: String = "http://localhost:9800",
) {
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
            level = LogLevel.BODY
        }
        install(HttpTimeout) {
            requestTimeoutMillis = 30_000
            connectTimeoutMillis = 10_000
        }
        defaultRequest {
            contentType(ContentType.Application.Json)
        }
    }

    private fun apiUrl(path: String): String = "$baseUrl$path"

    // ── 系统 ──

    suspend fun health(): HealthResponse {
        return client.get(apiUrl("/health")).body()
    }

    suspend fun systemStatus(): SystemStatus {
        return client.get(apiUrl("/api/status")).body()
    }

    // ── 聊天 ──

    suspend fun sendMessage(request: ChatSendRequest): ChatResponse {
        val response = client.post(apiUrl("/api/chat/send")) {
            setBody(request)
        }
        return response.body()
    }

    fun chatStream(request: ChatSendRequest): Flow<String> = flow {
        val httpResponse = client.post(apiUrl("/api/chat")) {
            setBody(request)
        }
        val body = httpResponse.bodyAsText()
        try {
            val jsonObj = json.decodeFromString<ChatJsonResponse>(body)
            val text = jsonObj.response
            if (!text.isNullOrEmpty()) {
                emit(text)
            }
        } catch (_: Exception) {
            emit("回复解析失败")
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
            setBody(mapOf("session_id" to sessionId, "display_name" to name))
        }
    }

    // ── 记忆 ──

    suspend fun getMemoryStats(): MemoryStats {
        return client.get(apiUrl("/api/memory/stats")).body()
    }

    suspend fun searchMemory(query: String, limit: Int = 20): List<MemoryItem> {
        return try {
            val response: MemoryListResponse = client.get(
                apiUrl("/api/memory/search?query=${query}&limit=$limit")
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

    // ── 语音 ──

    suspend fun transcribeAudio(audioData: ByteArray, language: String = "zh"): String? {
        return try {
            val response = client.post(apiUrl("/api/audio/transcribe")) {
                setBody(audioData)
                headers { append("X-Language", language) }
            }
            val result: Map<String, String> = response.body()
            result["text"]
        } catch (_: Exception) {
            null
        }
    }

    fun updateBaseUrl(newUrl: String): MiyaApiClient {
        return MiyaApiClient(newUrl)
    }
}

@kotlinx.serialization.Serializable
private data class ChatJsonResponse(
    val response: String? = null,
)
