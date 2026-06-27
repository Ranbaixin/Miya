package ai.miya.shared.model

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

enum class ContentType {
    @SerialName("text") TEXT,
    @SerialName("image") IMAGE,
    @SerialName("sticker") STICKER,
    @SerialName("voice") VOICE,
    @SerialName("file") FILE,
    @SerialName("system") SYSTEM,
}

@Serializable
data class ImagePayload(
    val url: String,
    @SerialName("thumbnail_url")
    val thumbnailUrl: String? = null,
    val width: Int = 0,
    val height: Int = 0,
    @SerialName("file_size")
    val fileSize: Long = 0,
)

@Serializable
data class StickerPayload(
    @SerialName("sticker_id")
    val stickerId: String,
    val url: String,
    val category: String? = null,
    @SerialName("is_external")
    val isExternal: Boolean = false,
)

@Serializable
data class VoicePayload(
    val url: String,
    val duration: Int = 0,
    @SerialName("file_size")
    val fileSize: Long = 0,
)

@Serializable
data class QuotePayload(
    @SerialName("message_id")
    val messageId: String? = null,
    val content: String = "",
    val sender: String? = null,
)

@Serializable
data class Message(
    val id: String? = null,
    @SerialName("content_type")
    val contentType: ContentType = ContentType.TEXT,
    val content: String = "",
    val role: String = "user",
    val sender: String? = null,
    val timestamp: Long = 0L,
    val image: ImagePayload? = null,
    val sticker: StickerPayload? = null,
    val voice: VoicePayload? = null,
    val quote: QuotePayload? = null,
)

@Serializable
data class ChatSendRequest(
    val message: String? = null,
    @SerialName("content_type")
    val contentType: ContentType = ContentType.TEXT,
    @SerialName("image_url")
    val imageUrl: String? = null,
    @SerialName("sticker_id")
    val stickerId: String? = null,
    @SerialName("voice_url")
    val voiceUrl: String? = null,
    @SerialName("quoted_message_id")
    val quotedMessageId: String? = null,
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
    @SerialName("content_type")
    val contentType: ContentType = ContentType.TEXT,
    val image: ImagePayload? = null,
    val sticker: StickerPayload? = null,
    val voice: VoicePayload? = null,
    val quote: QuotePayload? = null,
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
