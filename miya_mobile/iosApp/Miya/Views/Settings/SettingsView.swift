import SwiftUI

// ═══════════════════════════════════════════════
// 设置视图 (PGR 风格)
// ═══════════════════════════════════════════════

struct SettingsView: View {
    @EnvironmentObject var appState: AppState

    @State private var personas: [MiyaPersona] = []
    @State private var currentPersonaId: String?
    @State private var hostInput = "localhost"
    @State private var portInput = "9800"

    var body: some View {
        NavigationStack {
            List {
                Section {
                    HStack {
                        Text("主机").foregroundColor(MiyaColors.textSecondary)
                        TextField("localhost", text: $hostInput)
                            .multilineTextAlignment(.trailing)
                            .foregroundColor(MiyaColors.textPrimary)
                            .keyboardType(.URL)
                    }
                    HStack {
                        Text("端口").foregroundColor(MiyaColors.textSecondary)
                        TextField("9800", text: $portInput)
                            .multilineTextAlignment(.trailing)
                            .foregroundColor(MiyaColors.textPrimary)
                            .keyboardType(.numberPad)
                    }
                    Button(action: reconnect) {
                        HStack {
                            Spacer()
                            Label("重新连接", systemImage: "wifi")
                                .foregroundColor(MiyaColors.primary)
                            Spacer()
                        }
                    }
                } header: {
                    Text("连接设置").foregroundColor(MiyaColors.accent)
                }

                Section {
                    HStack {
                        Circle()
                            .fill(appState.isConnected ? MiyaColors.emotionJoy : MiyaColors.emotionAnger)
                            .frame(width: 10, height: 10)
                        Text(appState.isConnected ? "已连接 \(appState.baseURL)" : "未连接")
                            .font(.subheadline)
                            .foregroundColor(MiyaColors.textSecondary)
                    }
                } header: {
                    Text("连接状态").foregroundColor(MiyaColors.accent)
                }

                Section {
                    if personas.isEmpty {
                        HStack {
                            ProgressView().tint(MiyaColors.primary)
                            Text("加载中...").foregroundColor(MiyaColors.textSecondary).padding(.leading, 8)
                        }
                    } else {
                        ForEach(personas) { persona in
                            Button(action: { switchPersona(persona) }) {
                                HStack {
                                    Image(systemName: currentPersonaId == persona.id
                                          ? "checkmark.circle.fill"
                                          : "circle")
                                        .foregroundColor(currentPersonaId == persona.id
                                            ? MiyaColors.primary
                                            : MiyaColors.textDim)
                                    VStack(alignment: .leading) {
                                        Text(persona.displayName ?? persona.name)
                                            .foregroundColor(MiyaColors.textPrimary)
                                        Text(persona.id)
                                            .font(.caption)
                                            .foregroundColor(MiyaColors.textSecondary)
                                    }
                                }
                            }
                        }
                    }
                } header: {
                    Text("切换人格").foregroundColor(MiyaColors.accent)
                }

                Section {
                    HStack {
                        Text("弥娅版本")
                        Spacer()
                        Text("v8.0").foregroundColor(MiyaColors.textSecondary)
                    }
                    HStack {
                        Text("客户端版本")
                        Spacer()
                        Text("v1.0.0").foregroundColor(MiyaColors.textSecondary)
                    }
                    HStack {
                        Text("类型")
                        Spacer()
                        Text("AI 虚拟化身").foregroundColor(MiyaColors.textSecondary)
                    }
                } header: {
                    Text("关于").foregroundColor(MiyaColors.accent)
                }
            }
            .scrollContentBackground(.hidden)
            .background(MiyaColors.background)
            .navigationTitle("设置")
            .navigationBarTitleDisplayMode(.large)
        }
        .task { await loadPersonas() }
    }

    private func reconnect() {
        let port = Int(portInput) ?? 9800
        appState.updateConnection(host: hostInput, port: port)
    }

    private func loadPersonas() async {
        do {
            personas = try await appState.apiService.getPersonaList()
            currentPersonaId = try await appState.apiService.getCurrentPersona()
        } catch {
            personas = []
        }
    }

    private func switchPersona(_ persona: MiyaPersona) {
        Task {
            let success = try await appState.apiService.switchPersona(persona.id)
            if success {
                currentPersonaId = persona.id
                appState.currentPersona = persona.displayName ?? persona.name
            }
        }
    }
}

#Preview {
    SettingsView()
        .environmentObject(AppState())
}
