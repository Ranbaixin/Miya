package ai.miya.shared.connection

import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow

enum class ConnectionMode {
    LAN,     // 局域网直连
    REMOTE,  // frp/nps 远程中转
}

enum class ConnectionStatus {
    DISCONNECTED,
    CONNECTING,
    CONNECTED,
    ERROR,
}

data class ConnectionState(
    val mode: ConnectionMode = ConnectionMode.LAN,
    val status: ConnectionStatus = ConnectionStatus.DISCONNECTED,
    val baseUrl: String = "http://localhost:9800",
    val wsUrl: String = "ws://localhost:9800",
    val error: String? = null,
)

class ConnectionManager {
    private val _state = MutableStateFlow(ConnectionState())
    val state: StateFlow<ConnectionState> = _state

    private val localPorts = listOf(9800, 8000)

    fun setLanMode(host: String = "localhost", port: Int = 9800) {
        _state.value = ConnectionState(
            mode = ConnectionMode.LAN,
            status = ConnectionStatus.CONNECTING,
            baseUrl = "http://$host:$port",
            wsUrl = "ws://$host:$port",
        )
    }

    fun setRemoteMode(host: String, port: Int = 9800) {
        _state.value = ConnectionState(
            mode = ConnectionMode.REMOTE,
            status = ConnectionStatus.CONNECTING,
            baseUrl = "http://$host:$port",
            wsUrl = "ws://$host:$port",
        )
    }

    fun markConnected() {
        _state.value = _state.value.copy(status = ConnectionStatus.CONNECTED, error = null)
    }

    fun markDisconnected() {
        _state.value = _state.value.copy(status = ConnectionStatus.DISCONNECTED)
    }

    fun markError(error: String) {
        _state.value = _state.value.copy(status = ConnectionStatus.ERROR, error = error)
    }

    val isConnected: Boolean
        get() = _state.value.status == ConnectionStatus.CONNECTED
}
