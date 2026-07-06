package ai.miya.shared

import ai.miya.shared.api.MiyaApiClient
import ai.miya.shared.api.MiyaWebSocket
import ai.miya.shared.connection.ConnectionManager
import ai.miya.shared.repo.ChatRepository
import ai.miya.shared.repo.MemoryRepository
import ai.miya.shared.repo.PersonaRepository
import com.russhwolf.settings.Settings

class PlatformContext(
    val settingsFactory: () -> Settings,
)

object ServiceLocator {
    var platformContext: PlatformContext? = null

    private var _appConfig: AppConfig? = null
    private var _apiClient: MiyaApiClient? = null
    private var _webSocket: MiyaWebSocket? = null
    private var _connectionManager: ConnectionManager? = null
    private var _chatRepo: ChatRepository? = null
    private var _memoryRepo: MemoryRepository? = null
    private var _personaRepo: PersonaRepository? = null

    fun init(context: PlatformContext) {
        platformContext = context
        val settings = context.settingsFactory()
        _appConfig = AppConfig(settings)
        val baseUrl = _appConfig!!.serverBaseUrl
        _connectionManager = ConnectionManager()
        _apiClient = MiyaApiClient(baseUrl)
        _webSocket = MiyaWebSocket(baseUrl.replace("http", "ws"))
        _chatRepo = ChatRepository(apiClient)
        _memoryRepo = MemoryRepository(apiClient)
        _personaRepo = PersonaRepository(apiClient)
    }

    fun reconnect(host: String, port: Int) {
        _appConfig?.saveHost(host)
        _appConfig?.savePort(port)
        val baseUrl = "http://$host:$port"
        _apiClient = MiyaApiClient(baseUrl)
        _webSocket = MiyaWebSocket(baseUrl.replace("http", "ws"))
        _chatRepo = ChatRepository(apiClient)
        _memoryRepo = MemoryRepository(apiClient)
        _personaRepo = PersonaRepository(apiClient)
    }

    val appConfig: AppConfig
        get() = _appConfig ?: error("ServiceLocator not initialized")

    val apiClient: MiyaApiClient
        get() = _apiClient ?: error("ServiceLocator not initialized")

    val webSocket: MiyaWebSocket
        get() = _webSocket ?: error("ServiceLocator not initialized")

    val connectionManager: ConnectionManager
        get() = _connectionManager ?: error("ServiceLocator not initialized")

    val chatRepo: ChatRepository
        get() = _chatRepo ?: error("ServiceLocator not initialized")

    val memoryRepo: MemoryRepository
        get() = _memoryRepo ?: error("ServiceLocator not initialized")

    val personaRepo: PersonaRepository
        get() = _personaRepo ?: error("ServiceLocator not initialized")
}
