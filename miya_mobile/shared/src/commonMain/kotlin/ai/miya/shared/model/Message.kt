package ai.miya.shared.model

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class Message(
    val role: String,
    val content: String,
    val sender: String? = null,
    val timestamp: Long = 0L,
)

@Serializable
data class ChatSendRequest(
    val message: String,
    @SerialName("session_id")
    val sessionId: String = "default",
    val platform: String = "mobile",
    @SerialName("user_id")
    val userId: String? = null,
)

@Serializable
data class ChatResponse(
    val reply: String? = null,
    val emotion: String? = null,
    @SerialName("session_id")
    val sessionId: String? = null,
    val error: String? = null,
)

@Serializable
data class SessionInfo(
    val id: String,
    val name: String? = null,
    @SerialName("created_at")
    val createdAt: String? = null,
    @SerialName("updated_at")
    val updatedAt: String? = null,
    @SerialName("message_count")
    val messageCount: Int? = null,
)

@Serializable
data class NewSessionResponse(
    val id: String,
)
