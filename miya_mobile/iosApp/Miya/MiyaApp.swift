import SwiftUI

@main
struct MiyaApp: App {
    @StateObject private var appState = AppState()
    @AppStorage("isDarkTheme") private var isDarkTheme = true

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(appState)
                .preferredColorScheme(isDarkTheme ? .dark : .light)
        }
    }
}
