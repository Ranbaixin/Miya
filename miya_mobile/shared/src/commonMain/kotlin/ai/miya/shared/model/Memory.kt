package ai.miya.shared.model

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class MemoryStats(
    @SerialName("nodeCount")
    val nodeCount: Int = 0,
    @SerialName("edgeCount")
    val edgeCount: Int = 0,
    @SerialName("memorySize")
    val memorySize: String? = null,
    val dialogue: Int = 0,
    @SerialName("short_term")
    val shortTerm: Int = 0,
    @SerialName("long_term")
    val longTerm: Int = 0,
    val semantic: Int = 0,
    val knowledge: Int = 0,
    val pinned: Int = 0,
    val total: Int = 0,
)

@Serializable
data class MemoryItem(
    val id: String = "",
    val content: String = "",
    val level: String = "",
    val tags: List<String> = emptyList(),
    val priority: Double = 0.0,
    @SerialName("created_at")
    val createdAt: String? = null,
)

@Serializable
data class MemorySearchResult(
    val results: List<MemoryItem> = emptyList(),
    val total: Int = 0,
)

@Serializable
data class MemoryListResponse(
    val results: List<MemoryItem> = emptyList(),
)

@Serializable
data class AddMemoryRequest(
    val subject: String,
    val predicate: String,
    @SerialName("obj")
    val obj: String,
    val type: String = "memory",
)
