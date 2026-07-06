import SwiftUI

struct ProfileView: View {
    @Environment(\.colorScheme) var colorScheme
    @EnvironmentObject var appState: AppState
    @AppStorage("isDarkTheme") private var isDarkTheme = true
    @State private var personas: [MiyaPersona] = []
    @State private var currentPersonaId: String?
    @State private var showPersonaSheet = false
    @State private var showConnectionEdit = false
    @State private var editHost = ""
    @State private var editPort = ""

    var isDark: Bool { colorScheme == .dark }

    var body: some View {
        ScrollView {
            VStack(spacing: 0) {
                // 用户头部
                HStack(spacing: 16) {
                    ZStack {
                        Circle()
                            .fill((isDark ? MiyaColors.primary : MiyaLightColors.primary).opacity(0.15))
                            .frame(width: 72, height: 72)
                        Text("弥")
                            .font(.system(size: 30, weight: .bold))
                            .foregroundColor(isDark ? MiyaColors.primary : MiyaLightColors.primary)
                    }
                    VStack(alignment: .leading, spacing: 4) {
                        Text("弥娅")
                            .font(.system(size: 22, weight: .bold))
                            .foregroundColor(isDark ? MiyaColors.textPrimary : MiyaLightColors.textPrimary)
                        Text("AI 虚拟化身 · v8.0")
                            .font(.system(size: 13))
                            .foregroundColor(isDark ? MiyaColors.textSecondary : MiyaLightColors.textSecondary)
                        Text("MIYA-CORE")
                            .font(.system(size: 10, design: .monospaced))
                            .foregroundColor(isDark ? MiyaColors.primary : MiyaLightColors.primary)
                            .padding(.horizontal, 6)
                            .padding(.vertical, 2)
                            .background((isDark ? MiyaColors.primary : MiyaLightColors.primary).opacity(0.1))
                            .cornerRadius(4)
                    }
                    Spacer()
                    Image(systemName: "chevron.right")
                        .foregroundColor(isDark ? MiyaColors.textDim : MiyaLightColors.textDim)
                }
                .padding(20)

                // 连接状态
                HStack(spacing: 12) {
                    Circle()
                        .fill(appState.isConnected ? Color.green : Color.red)
                        .frame(width: 10, height: 10)
                    VStack(alignment: .leading, spacing: 2) {
                        Text(appState.isConnected ? "已连接" : "未连接")
                            .font(.system(size: 15, weight: .medium))
                            .foregroundColor(isDark ? MiyaColors.textPrimary : MiyaLightColors.textPrimary)
                        Text(appState.baseURL)
                            .font(.system(size: 12))
                            .foregroundColor(isDark ? MiyaColors.textDim : MiyaLightColors.textDim)
                    }
                    Spacer()
                }
                .padding(16)
                .background(isDark ? MiyaColors.surface : MiyaLightColors.surface)
                .cornerRadius(12)
                .padding(.horizontal, 16)
                .padding(.bottom, 16)

                // 设置组 1
                settingsGroup {
                    settingsRow(
                        icon: "wifi",
                        label: "连接配置",
                        subtitle: "\(UserDefaults.standard.string(forKey: "server_host") ?? "localhost"):\(UserDefaults.standard.integer(forKey: "server_port"))",
                        action: {
                            editHost = UserDefaults.standard.string(forKey: "server_host") ?? "localhost"
                            editPort = "\(UserDefaults.standard.integer(forKey: "server_port"))"
                            showConnectionEdit = true
                        }
                    )
                    settingsRow(
                        icon: "face.smiling",
                        label: "当前人格",
                        subtitle: personas.first(where: { $0.id == currentPersonaId })?.displayName
                            ?? personas.first(where: { $0.id == currentPersonaId })?.name ?? "default",
                        action: { showPersonaSheet = true }
                    )
                }

                Spacer().frame(height: 16)

                // 设置组 2
                settingsGroup {
                    HStack {
                        Image(systemName: isDarkTheme ? "moon.fill" : "sun.max.fill")
                            .foregroundColor(isDark ? MiyaColors.primary : MiyaLightColors.primary)
                            .frame(width: 22)
                        Text("深色主题")
                            .foregroundColor(isDark ? MiyaColors.textPrimary : MiyaLightColors.textPrimary)
                        Spacer()
                        Toggle("", isOn: $isDarkTheme)
                            .tint(isDark ? MiyaColors.primary : MiyaLightColors.primary)
                    }
                    .padding(.horizontal, 16)
                    .padding(.vertical, 14)

                    settingsRow(
                        icon: "info.circle",
                        label: "关于弥娅",
                        subtitle: "手机客户端 v2.0 · 弥娅 v8.0"
                    )
                }

                Spacer().frame(height: 32)

                Text("弥娅 (MIYA) AI 虚拟化身\n所有服务运行在你的电脑上")
                    .font(.system(size: 11))
                    .multilineTextAlignment(.center)
                    .foregroundColor(isDark ? MiyaColors.textDim : MiyaLightColors.textDim)
            }
        }
        .background(isDark ? MiyaColors.background : MiyaLightColors.background)
        .task { await loadPersonas() }
        .sheet(isPresented: $showConnectionEdit) {
            connectionEditSheet
                .presentationDetents([.medium])
        }
        .sheet(isPresented: $showPersonaSheet) {
            personaSheet
                .presentationDetents([.medium])
        }
    }

    private func settingsGroup<Content: View>(@ViewBuilder content: () -> Content) -> some View {
        VStack(spacing: 0) { content() }
            .background(isDark ? MiyaColors.surface : MiyaLightColors.surface)
            .cornerRadius(12)
            .padding(.horizontal, 16)
    }

    private func settingsRow(icon: String, label: String, subtitle: String, action: (() -> Void)? = nil) -> some View {
        Button(action: { action?() }) {
            HStack(spacing: 14) {
                Image(systemName: icon)
                    .foregroundColor(isDark ? MiyaColors.primary : MiyaLightColors.primary)
                    .frame(width: 22)
                VStack(alignment: .leading, spacing: 2) {
                    Text(label)
                        .font(.system(size: 15))
                        .foregroundColor(isDark ? MiyaColors.textPrimary : MiyaLightColors.textPrimary)
                    Text(subtitle)
                        .font(.system(size: 12))
                        .foregroundColor(isDark ? MiyaColors.textDim : MiyaLightColors.textDim)
                }
                Spacer()
                Image(systemName: "chevron.right")
                    .font(.system(size: 14))
                    .foregroundColor(isDark ? MiyaColors.textDim : MiyaLightColors.textDim)
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 14)
        }
        Divider().padding(.leading, 52)
    }

    private var connectionEditSheet: some View {
        VStack(spacing: 16) {
            Text("连接配置")
                .font(.headline)
            TextField("服务器地址", text: $editHost)
                .textFieldStyle(.roundedBorder)
            TextField("端口", text: $editPort)
                .textFieldStyle(.roundedBorder)
                .keyboardType(.numberPad)
            Button("保存并重连") {
                if let port = Int(editPort) {
                    UserDefaults.standard.set(editHost, forKey: "server_host")
                    UserDefaults.standard.set(port, forKey: "server_port")
                    appState.updateConnection(host: editHost, port: port)
                }
                showConnectionEdit = false
            }
            .buttonStyle(.borderedProminent)
            Button("取消") { showConnectionEdit = false }
        }
        .padding()
        .background(isDark ? MiyaColors.background : MiyaLightColors.background)
    }

    private var personaSheet: some View {
        VStack(spacing: 12) {
            Text("切换人格").font(.headline)
            ForEach(personas) { p in
                HStack {
                    Image(systemName: currentPersonaId == p.id ? "circle.fill" : "circle")
                    VStack(alignment: .leading) {
                        Text(p.displayName ?? p.name)
                        Text(p.id).font(.system(size: 11)).foregroundColor(.gray)
                    }
                    Spacer()
                }
                .padding(.horizontal)
                .onTapGesture {
                    Task {
                        do {
                            let result = try await appState.apiService.switchPersona(personalityId: p.id)
                            if result { currentPersonaId = p.id }
                        } catch { }
                    }
                }
            }
            Button("完成") { showPersonaSheet = false }
                .buttonStyle(.bordered)
        }
        .padding()
        .background(isDark ? MiyaColors.background : MiyaLightColors.background)
    }

    private func loadPersonas() async {
        do {
            personas = try await appState.apiService.getPersonas()
            if let currentId = try? await appState.apiService.getCurrentPersonaId() {
                currentPersonaId = currentId
            }
        } catch { }
    }
}
