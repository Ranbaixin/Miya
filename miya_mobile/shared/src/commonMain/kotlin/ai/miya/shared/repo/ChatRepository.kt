package ai.miya.shared.repo

import ai.miya.shared.api.MiyaApiClient
import ai.miya.shared.model.*
import kotlinx.coroutines.flow.Flow

class ChatRepository(
    private val api: MiyaApiClient,
) {
    suspend fun sendMessage(message: String, sessionId: String = "default"): ChatResponse {
        return api.sendMessage(
            ChatSendRequest(message = message, sessionId = sessionId)
        )
    }

    fun streamChat(message: String, sessionId: String = "default"): Flow<String> {
        return api.chatStream(
            ChatSendRequest(message = message, sessionId = sessionId)
        )
    }

    suspend fun stopChat(): Boolean = api.stopChat()

    suspend fun getSessions(): List<SessionInfo> = api.listSessions()

    suspend fun newSession(): String {
        return api.newSession().id
    }

    suspend fun deleteSession(sessionId: String) {
        api.deleteSession(sessionId)
    }

    suspend fun renameSession(sessionId: String, name: String) {
        api.updateSessionName(sessionId, name)
    }
}
