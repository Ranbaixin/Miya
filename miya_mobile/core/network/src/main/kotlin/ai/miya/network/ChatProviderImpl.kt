package ai.miya.network

import ai.miya.domain.ChatProvider
import ai.miya.model.ChatRequest
import ai.miya.model.ChatResponse
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flow

class ChatProviderImpl(
    private val apiClient: MiyaApiClient,
) : ChatProvider {

    override suspend fun sendMessage(request: ChatRequest): ChatResponse {
        return apiClient.sendMessage(request)
    }

    override fun streamChat(request: ChatRequest): Flow<String> = flow {
        val response = apiClient.sendMessage(request)
        emit(response.response)
    }

    override suspend fun stopChat(): Boolean {
        return apiClient.stopChat()
    }
}
