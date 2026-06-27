import SwiftUI

enum MiyaTab: String, CaseIterable {
    case chat = "聊天"
    case hub = "中枢"
    case memory = "记忆"
    case settings = "设置"

    var icon: String {
        switch self {
        case .chat: return "message.fill"
        case .hub: return "circle.hexagongrid.fill"
        case .memory: return "brain.head.profile"
        case .settings: return "gearshape.fill"
        }
    }
}

struct ContentView: View {
    @State private var selectedTab: MiyaTab = .chat

    var body: some View {
        TabView(selection: $selectedTab) {
            ChatView()
                .tabItem {
                    Label(MiyaTab.chat.rawValue, systemImage: MiyaTab.chat.icon)
                }
                .tag(MiyaTab.chat)

            HubView()
                .tabItem {
                    Label(MiyaTab.hub.rawValue, systemImage: MiyaTab.hub.icon)
                }
                .tag(MiyaTab.hub)

            MemoryView()
                .tabItem {
                    Label(MiyaTab.memory.rawValue, systemImage: MiyaTab.memory.icon)
                }
                .tag(MiyaTab.memory)

            SettingsView()
                .tabItem {
                    Label(MiyaTab.settings.rawValue, systemImage: MiyaTab.settings.icon)
                }
                .tag(MiyaTab.settings)
        }
        .tint(Color("MiyaPrimary"))
        .preferredColorScheme(.dark)
    }
}

#Preview {
    ContentView()
        .environmentObject(AppState())
}
