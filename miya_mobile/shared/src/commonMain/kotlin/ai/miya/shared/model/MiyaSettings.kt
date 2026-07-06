package ai.miya.shared.model

data class AppSettings(
    val serverHost: String = "localhost",
    val serverPort: Int = 8000,
    val isDarkTheme: Boolean = true,
    val lastPersonaId: String? = null,
)
