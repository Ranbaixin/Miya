package ai.miya.shared

import ai.miya.shared.model.AppSettings
import com.russhwolf.settings.Settings

class AppConfig(private val settings: Settings) {
    companion object {
        private const val KEY_HOST = "server_host"
        private const val KEY_PORT = "server_port"
        private const val KEY_DARK_THEME = "dark_theme"
        private const val KEY_PERSONA = "last_persona"
    }

    fun load(): AppSettings = AppSettings(
        serverHost = settings.getString(KEY_HOST, "localhost"),
        serverPort = settings.getInt(KEY_PORT, 8000),
        isDarkTheme = settings.getBoolean(KEY_DARK_THEME, true),
        lastPersonaId = settings.getStringOrNull(KEY_PERSONA),
    )

    fun save(settings: AppSettings) {
        this.settings.putString(KEY_HOST, settings.serverHost)
        this.settings.putInt(KEY_PORT, settings.serverPort)
        this.settings.putBoolean(KEY_DARK_THEME, settings.isDarkTheme)
        settings.lastPersonaId?.let { this.settings.putString(KEY_PERSONA, it) }
    }

    fun saveHost(host: String) = settings.putString(KEY_HOST, host)
    fun savePort(port: Int) = settings.putInt(KEY_PORT, port)
    fun saveTheme(isDark: Boolean) = settings.putBoolean(KEY_DARK_THEME, isDark)

    val serverBaseUrl: String
        get() = "http://${settings.getString(KEY_HOST, "localhost")}:${settings.getInt(KEY_PORT, 8000)}"

    val serverWsUrl: String
        get() = "ws://${settings.getString(KEY_HOST, "localhost")}:${settings.getInt(KEY_PORT, 8000)}"

    val isDarkTheme: Boolean
        get() = settings.getBoolean(KEY_DARK_THEME, true)
}
