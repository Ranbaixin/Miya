package ai.miya.app

sealed class MainRoute(val route: String) {
    object Home : MainRoute("home")
    object Me : MainRoute("me")
    object Memory : MainRoute("memory")
    object Hub : MainRoute("hub")
    object Settings : MainRoute("settings")
}
