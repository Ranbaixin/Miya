import SwiftUI

struct ConversationListView: View {
    @Environment(\.colorScheme) var colorScheme
    @EnvironmentObject var appState: AppState
    @State private var sessions: [MiyaSession] = []
    @State private var isLoading = true

    var isDark: Bool { colorScheme == .dark }
    var onConversationClick: (String, String) -> Void

    var body: some View {
        VStack(spacing: 0) {
            // 标题栏
            HStack {
                Text("消息")
                    .font(.system(size: 28, weight: .bold))
                    .foregroundColor(isDark ? MiyaColors.textPrimary : MiyaLightColors.textPrimary)
                Spacer()
                Button(action: createNewSession) {
                    Image(systemName: "plus")
                        .font(.system(size: 18))
                        .foregroundColor(isDark ? MiyaColors.primary : MiyaLightColors.primary)
                }
            }
            .padding(.horizontal, 20)
            .padding(.vertical, 14)

            // 搜索栏
            HStack {
                Image(systemName: "magnifyingglass")
                    .foregroundColor(isDark ? MiyaColors.textDim : MiyaLightColors.textDim)
                Text("搜索对话...")
                    .foregroundColor(isDark ? MiyaColors.textDim : MiyaLightColors.textDim)
                    .font(.system(size: 14))
                Spacer()
            }
            .padding(10)
            .background(isDark ? MiyaColors.surface : MiyaLightColors.surface)
            .cornerRadius(10)
            .padding(.horizontal, 16)

            if isLoading {
                Spacer()
                ProgressView()
                    .tint(isDark ? MiyaColors.primary : MiyaLightColors.primary)
                Spacer()
            } else {
                List {
                    // 置顶：弥娅
                    Button(action: { onConversationClick("default", "弥娅") }) {
                        HStack(spacing: 14) {
                            ZStack {
                                Circle()
                                    .fill((isDark ? MiyaColors.primary : MiyaLightColors.primary).opacity(0.15))
                                    .frame(width: 52, height: 52)
                                Text("弥")
                                    .font(.system(size: 22, weight: .bold))
                                    .foregroundColor(isDark ? MiyaColors.primary : MiyaLightColors.primary)
                            }
                            VStack(alignment: .leading, spacing: 4) {
                                HStack {
                                    Text("弥娅")
                                        .font(.system(size: 16, weight: .semibold))
                                        .foregroundColor(isDark ? MiyaColors.textPrimary : MiyaLightColors.textPrimary)
                                    Spacer()
                                    Text("现在")
                                        .font(.system(size: 11))
                                        .foregroundColor(isDark ? MiyaColors.textDim : MiyaLightColors.textDim)
                                }
                                Text("你好，我是弥娅，有什么可以帮你的？")
                                    .font(.system(size: 13))
                                    .foregroundColor(isDark ? MiyaColors.textDim : MiyaLightColors.textDim)
                                    .lineLimit(1)
                            }
                        }
                        .padding(.vertical, 4)
                    }
                    .listRowBackground(Color.clear)
                    .listRowSeparator(.hidden)

                    // 会话列表
                    ForEach(sessions) { session in
                        Button(action: {
                            onConversationClick(session.id, session.name ?? "对话")
                        }) {
                            HStack(spacing: 14) {
                                ZStack {
                                    Circle()
                                        .fill(isDark ? MiyaColors.surfaceVariant : MiyaLightColors.surfaceVariant)
                                        .frame(width: 52, height: 52)
                                    Text(String(session.name?.prefix(1) ?? "M"))
                                        .font(.system(size: 20, weight: .medium))
                                        .foregroundColor(isDark ? MiyaColors.textSecondary : MiyaLightColors.textSecondary)
                                }
                                VStack(alignment: .leading, spacing: 4) {
                                    HStack {
                                        Text(session.name ?? "对话")
                                            .font(.system(size: 16))
                                            .foregroundColor(isDark ? MiyaColors.textPrimary : MiyaLightColors.textPrimary)
                                        Spacer()
                                        Text(formatTime(session.updatedAt))
                                            .font(.system(size: 11))
                                            .foregroundColor(isDark ? MiyaColors.textDim : MiyaLightColors.textDim)
                                    }
                                    Text("\(session.messageCount ?? 0) 条消息")
                                        .font(.system(size: 13))
                                        .foregroundColor(isDark ? MiyaColors.textDim : MiyaLightColors.textDim)
                                }
                            }
                            .padding(.vertical, 4)
                        }
                        .listRowBackground(Color.clear)
                        .listRowSeparator(.hidden)
                    }
                }
                .listStyle(.plain)
                .scrollContentBackground(.hidden)
            }
        }
        .background(isDark ? MiyaColors.background : MiyaLightColors.background)
        .task { await loadSessions() }
    }

    private func loadSessions() async {
        isLoading = true
        do {
            sessions = try await appState.apiService.getSessions()
        } catch { }
        isLoading = false
    }

    private func createNewSession() {
        Task {
            do {
                let id = try await appState.apiService.newSession()
                onConversationClick(id, "新对话")
            } catch { }
        }
    }

    private func formatTime(_ iso: String?) -> String {
        guard let iso else { return "" }
        let fmt = ISO8601DateFormatter()
        fmt.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        if let date = fmt.date(from: iso) {
            let now = Date()
            let diff = Calendar.current.dateComponents([.day], from: date, to: now).day ?? 999
            let tf = DateFormatter()
            tf.locale = Locale(identifier: "zh_CN")
            switch diff {
            case 0: tf.dateFormat = "HH:mm"
            case 1: return "昨天"
            case ..<7: tf.dateFormat = "EEEE"
            default: tf.dateFormat = "MM/dd"
            }
            return tf.string(from: date)
        }
        return ""
    }
}
