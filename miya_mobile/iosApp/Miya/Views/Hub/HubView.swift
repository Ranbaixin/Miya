import SwiftUI

// ═══════════════════════════════════════════════
// 中枢面板 (PGR 风格)
// ═══════════════════════════════════════════════

struct HubView: View {
    @EnvironmentObject var appState: AppState

    @State private var systemStatus: SystemStatusInfo?
    @State private var memoryStats: MemoryStatsInfo?
    @State private var isLoading = true
    @State private var errorMessage: String?

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 14) {
                    if isLoading {
                        ProgressView()
                            .padding(.top, 100)
                            .tint(MiyaColors.primary)
                    } else if let error = errorMessage {
                        ErrorCard(message: error) {
                            await loadData()
                        }
                    } else {
                        if let status = systemStatus {
                            statusSection(status)
                        }
                        if let stats = memoryStats {
                            memorySection(stats)
                        }
                    }
                }
                .padding(16)
            }
            .background(MiyaColors.background)
            .navigationTitle("中枢")
            .navigationBarTitleDisplayMode(.large)
            .refreshable { await loadData() }
        }
        .task { await loadData() }
    }

    private func loadData() async {
        isLoading = true
        errorMessage = nil
        do {
            systemStatus = try await appState.apiService.getSystemStatus()
            memoryStats = try await appState.apiService.getMemoryStats()
        } catch {
            errorMessage = error.localizedDescription
        }
        isLoading = false
    }

    @ViewBuilder
    private func statusSection(_ status: SystemStatusInfo) -> some View {
        HubCard(title: "系统状态") {
            HubRow(label: "运行状态", value: status.running ? "在线" : "离线",
                   color: status.running ? MiyaColors.emotionJoy : MiyaColors.emotionAnger)
            if let version = status.version {
                HubRow(label: "版本", value: version, color: MiyaColors.accent)
            }
            if let uptime = status.uptime {
                HubRow(label: "运行时间", value: uptime, color: nil)
            }
            HubRow(label: "连接平台",
                   value: "\(status.platformsActive ?? 0)/\(status.platforms ?? 0)",
                   color: MiyaColors.accent)
            if let providers = status.providersLoaded {
                HubRow(label: "AI 提供者", value: "\(providers) 个", color: MiyaColors.primary)
            }
        }

        HubCard(title: "当前人格") {
            HStack(spacing: 12) {
                Image(systemName: "face.smiling")
                    .font(.title)
                    .foregroundColor(MiyaColors.primary)
                Text(status.personality ?? "default")
                    .font(.title3)
                    .fontWeight(.medium)
                    .foregroundColor(MiyaColors.textPrimary)
                Spacer()
            }
            .padding(.vertical, 4)
        }

        HubCard(title: "连接") {
            HStack(spacing: 10) {
                Circle()
                    .fill(appState.isConnected ? MiyaColors.emotionJoy : MiyaColors.emotionAnger)
                    .frame(width: 10, height: 10)
                Text(appState.isConnected ? "已连接 \(appState.baseURL)" : "未连接")
                    .font(.caption)
                    .foregroundColor(MiyaColors.textSecondary)
            }
        }
    }

    @ViewBuilder
    private func memorySection(_ stats: MemoryStatsInfo) -> some View {
        HubCard(title: "记忆统计") {
            LazyVGrid(columns: Array(repeating: GridItem(.flexible()), count: 4), spacing: 16) {
                StatItem("总计", stats.total)
                StatItem("对话", stats.dialogue)
                StatItem("长期", stats.longTerm)
                StatItem("语义", stats.semantic)
                StatItem("短期", stats.shortTerm)
                StatItem("知识", stats.knowledge)
                StatItem("固定", stats.pinned)
                StatItem("节点", stats.nodeCount)
            }
            .padding(.top, 4)
        }
    }
}

struct HubCard<Content: View>: View {
    let title: String
    @ViewBuilder let content: () -> Content

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text(title)
                .font(.headline)
                .foregroundColor(MiyaColors.textPrimary)
            content()
        }
        .padding(16)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(RoundedRectangle(cornerRadius: 16).fill(MiyaColors.surface))
    }
}

struct HubRow: View {
    let label: String
    let value: String
    let color: Color?

    init(label: String, value: String, color: Color?) {
        self.label = label
        self.value = value
        self.color = color
    }

    var body: some View {
        HStack {
            Text(label)
                .font(.subheadline)
                .foregroundColor(MiyaColors.textSecondary)
            Spacer()
            Text(value)
                .font(.subheadline)
                .fontWeight(.medium)
                .foregroundColor(color ?? MiyaColors.textPrimary)
        }
    }
}

struct StatItem: View {
    let label: String
    let value: Int

    var body: some View {
        VStack(spacing: 4) {
            Text("\(value)")
                .font(.title2)
                .fontWeight(.bold)
                .foregroundColor(MiyaColors.primary)
            Text(label)
                .font(.caption2)
                .foregroundColor(MiyaColors.textSecondary)
        }
    }
}

struct ErrorCard: View {
    let message: String
    let onRetry: () async -> Void

    var body: some View {
        VStack(spacing: 12) {
            Image(systemName: "wifi.slash")
                .font(.largeTitle)
                .foregroundColor(MiyaColors.emotionAnger)
            Text("连接失败")
                .font(.headline)
                .foregroundColor(MiyaColors.textPrimary)
            Text(message)
                .font(.caption)
                .foregroundColor(MiyaColors.textSecondary)
                .multilineTextAlignment(.center)
            Button(action: { Task { await onRetry() } }) {
                Label("重试", systemImage: "arrow.clockwise")
                    .font(.subheadline)
            }
            .buttonStyle(.bordered)
            .tint(MiyaColors.primary)
        }
        .padding(24)
        .frame(maxWidth: .infinity)
        .background(RoundedRectangle(cornerRadius: 16).fill(MiyaColors.surface))
        .padding(.top, 60)
    }
}

#Preview {
    HubView()
        .environmentObject(AppState())
}
