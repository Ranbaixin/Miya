import SwiftUI

struct SettingsView: View {
    @EnvironmentObject var appState: AppState

    @State private var personas: [MiyaPersona] = []
    @State private var currentPersonaId: String?
    @State private var hostInput = "localhost"
    @State private var portInput = "9800"

    var body: some View {
        NavigationStack {
            List {
                // ── 连接设置 ──
                Section {
                    HStack {
                        Text("主机")
                            .foregroundColor(.white.opacity(0.7))
                        TextField("localhost", text: $hostInput)
                            .multilineTextAlignment(.trailing)
                            .foregroundColor(.white)
                            .keyboardType(.URL)
                    }
                    HStack {
                        Text("端口")
                            .foregroundColor(.white.opacity(0.7))
                        TextField("9800", text: $portInput)
                            .multilineTextAlignment(.trailing)
                            .foregroundColor(.white)
                            .keyboardType(.numberPad)
                    }
                    Button(action: reconnect) {
                        HStack {
                            Spacer()
                            Label("重新连接", systemImage: "wifi")
                            Spacer()
                        }
                    }
                    .tint(Color("MiyaPrimary"))
                } header: {
                    Text("连接设置")
                }

                // ── 连接状态 ──
                Section {
                    HStack {
                        Circle()
                            .fill(appState.isConnected ? Color.green : Color.red)
                            .frame(width: 10, height: 10)
                        Text(appState.isConnected ? "已连接 \(appState.baseURL)" : "未连接")
                            .font(.subheadline)
                            .foregroundColor(.white.opacity(0.7))
                    }
                } header: {
                    Text("连接状态")
                }

                // ── 人格切换 ──
                Section {
                    if personas.isEmpty {
                        HStack {
                            ProgressView()
                                .tint(Color("MiyaPrimary"))
                            Text("加载中...")
                                .foregroundColor(.white.opacity(0.5))
                                .padding(.leading, 8)
                        }
                    } else {
                        ForEach(personas) { persona in
                            Button(action: { switchPersona(persona) }) {
                                HStack {
                                    Image(systemName: currentPersonaId == persona.id
                                          ? "checkmark.circle.fill"
                                          : "circle")
                                        .foregroundColor(currentPersonaId == persona.id
                                            ? Color("MiyaPrimary")
                                            : .white.opacity(0.3))
                                    VStack(alignment: .leading) {
                                        Text(persona.displayName ?? persona.name)
                                            .foregroundColor(.white)
                                        Text(persona.id)
                                            .font(.caption)
                                            .foregroundColor(.white.opacity(0.5))
                                    }
                                }
                            }
                        }
                    }
                } header: {
                    Text("切换人格")
                }

                // ── 关于 ──
                Section {
                    HStack {
                        Text("弥娅版本")
                        Spacer()
                        Text("v8.0")
                            .foregroundColor(.white.opacity(0.5))
                    }
                    HStack {
                        Text("客户端版本")
                        Spacer()
                        Text("v1.0.0")
                            .foregroundColor(.white.opacity(0.5))
                    }
                    HStack {
                        Text("类型")
                        Spacer()
                        Text("AI 虚拟化身")
                            .foregroundColor(.white.opacity(0.5))
                    }
                } header: {
                    Text("关于")
                }
            }
            .scrollContentBackground(.hidden)
            .background(Color("MiyaBackground"))
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
