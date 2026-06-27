package ai.miya.shared.repo

import ai.miya.shared.api.MiyaApiClient
import ai.miya.shared.model.*

class MemoryRepository(
    private val api: MiyaApiClient,
) {
    suspend fun getStats(): MemoryStats = api.getMemoryStats()

    suspend fun search(query: String, limit: Int = 20): List<MemoryItem> {
        return api.searchMemory(query, limit)
    }

    suspend fun getList(limit: Int = 50): List<MemoryItem> {
        return api.getMemoryList(limit)
    }
}
