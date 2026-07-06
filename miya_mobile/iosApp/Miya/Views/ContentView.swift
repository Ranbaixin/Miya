import SwiftUI

enum MainTab: String, CaseIterable {
    case messages = "消息"
    case discover = "发现"
    case me = "我的"

    var icon: String {
        switch self {
        case .messages: return "message.fill"
        case .discover: return "safari.fill"
        case .me: return "person.fill"
        }
    }
}

struct ContentView: View {
    @EnvironmentObject var appState: AppState
    @State private var selectedTab: MainTab = .messages
    @AppStorage("isDarkTheme") private var isDarkTheme = true
    @State private var showSetup = false
    @State private var chatSession: (id: String, name: String)? = nil

    var body: some View {
        Group {
            if showSetup {
                ConnectionSetupView(onConnected: { host, port in
                    appState.updateConnection(host: host, port: port)
                    showSetup = false
                })
                .preferredColorScheme(isDarkTheme ? .dark : .light)
            } else if let session = chatSession {
                NavigationStack {
                    ChatDetailView(
                        sessionId: session.id,
                        sessionName: session.name,
                        onBack: { chatSession = nil }
                    )
                }
                .preferredColorScheme(isDarkTheme ? .dark : .light)
            } else {
                TabView(selection: $selectedTab) {
                    ConversationListView(onConversationClick: { id, name in
                        chatSession = (id, name)
                    })
                    .tabItem {
                        Label(MainTab.messages.rawValue, systemImage: MainTab.messages.icon)
                    }
                    .tag(MainTab.messages)

                    DiscoverView()
                        .tabItem {
                            Label(MainTab.discover.rawValue, systemImage: MainTab.discover.icon)
                        }
                        .tag(MainTab.discover)

                    ProfileView()
                        .tabItem {
                            Label(MainTab.me.rawValue, systemImage: MainTab.me.icon)
                        }
                        .tag(MainTab.me)
                }
                .tint(isDarkTheme ? MiyaColors.primary : MiyaLightColors.primary)
                .preferredColorScheme(isDarkTheme ? .dark : .light)
            }
        }
        .onAppear {
            checkInitialConnection()
        }
    }

    private func checkInitialConnection() {
        let savedHost = UserDefaults.standard.string(forKey: "server_host") ?? "localhost"
        let savedPort = UserDefaults.standard.integer(forKey: "server_port")
        let port = savedPort > 0 ? savedPort : 9800

        if savedHost != "localhost" {
            appState.updateConnection(host: savedHost, port: port)
        }

        Task {
            let healthy = await appState.apiService.healthCheck()
            if !healthy { showSetup = true }
        }
    }
}

#Preview {
    ContentView()
        .environmentObject(AppState())
}
