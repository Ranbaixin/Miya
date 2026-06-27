package ai.miya.shared.model

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class SystemStatus(
    val status: String? = null,
    val version: String? = null,
    val uptime: String? = null,
    val running: Boolean = false,
    val personality: String? = null,
    val name: String? = null,
    val platforms: Int = 0,
    @SerialName("platforms_active")
    val platformsActive: Int = 0,
    @SerialName("providers_loaded")
    val providersLoaded: Int? = null,
    val emotion: EmotionState? = null,
    val memory: MemoryStats? = null,
)

@Serializable
data class HealthResponse(
    val status: String = "unknown",
)

@Serializable
data class ApiError(
    val error: ErrorDetail? = null,
)

@Serializable
data class ErrorDetail(
    val code: String? = null,
    val message: String? = null,
    val detail: String? = null,
)
