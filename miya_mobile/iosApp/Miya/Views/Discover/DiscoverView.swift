import SwiftUI

struct DiscoverView: View {
    @Environment(\.colorScheme) var colorScheme
    @EnvironmentObject var appState: AppState
    @State private var systemStatus: SystemStatusInfo?
    @State private var memoryStats: MemoryStatsInfo?
    @State private var isLoading = true
    @State private var error: String?
    @State private var searchQuery = ""
    @State private var searchResult = ""

    var isDark: Bool { colorScheme == .dark }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 0) {
                Text("发现")
                    .font(.system(size: 28, weight: .bold))
                    .foregroundColor(isDark ? MiyaColors.textPrimary : MiyaLightColors.textPrimary)
                    .padding(.horizontal, 20)
                    .padding(.vertical, 14)

                if isLoading {
                    ProgressView()
                        .frame(maxWidth: .infinity)
                        .padding(.top, 80)
                } else if let error {
                    HStack {
                        Image(systemName: "exclamationmark.triangle")
                        Text(error)
                    }
                    .font(.system(size: 13))
                    .foregroundColor(.red)
                    .padding(16)
                    .background(Color.red.opacity(0.1))
                    .cornerRadius(12)
                    .padding(.horizontal, 16)
                } else {
                    // 情感面板
                    if let emotion = systemStatus?.emotion ?? nil {
                        sectionHeader("灵魂共鸣", "SOUL RESONANCE")
                        EmotionCard(emotion: emotion)
                    }

                    // 认知引擎
                    if let status = systemStatus {
                        Spacer().frame(height: 16)
                        sectionHeader("认知引擎", "COGNITION ENGINE")
                        CognitionCard(status: status, memory: memoryStats)
                    }

                    // 记忆搜索
                    Spacer().frame(height: 16)
                    sectionHeader("记忆搜索", "MEMORY SEARCH")
                    MemorySearchCard(query: $searchQuery, result: $searchResult)

                    // 每日数据
                    Spacer().frame(height: 16)
                    sectionHeader("今日数据", "DAILY STATS")
                    DailyStatsCard()
                }
            }
        }
        .background(isDark ? MiyaColors.background : MiyaLightColors.background)
        .task { await loadData() }
    }

    private func sectionHeader(_ title: String, _ sub: String) -> some View {
        HStack {
            Text(title)
                .font(.system(size: 17, weight: .semibold))
                .foregroundColor(isDark ? MiyaColors.textPrimary : MiyaLightColors.textPrimary)
            Text(sub)
                .font(.system(size: 10, design: .monospaced))
                .kerning(1)
                .foregroundColor(isDark ? MiyaColors.textDim : MiyaLightColors.textDim)
        }
        .padding(.horizontal, 20)
        .padding(.vertical, 4)
    }

    private func loadData() async {
        isLoading = true
        do {
            systemStatus = try await appState.apiService.getSystemStatus()
            memoryStats = try await appState.apiService.getMemoryStats()
        } catch {
            error = "连接失败: \(error.localizedDescription)"
        }
        isLoading = false
    }
}

struct EmotionCard: View {
    @Environment(\.colorScheme) var colorScheme
    var emotion: EmotionData
    var isDark: Bool { colorScheme == .dark }

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Circle()
                    .fill(MiyaColors.emotionColor(for: emotion.dominant))
                    .frame(width: 10, height: 10)
                Text(emotion.dominant)
                    .font(.system(size: 22, weight: .bold))
                    .foregroundColor(MiyaColors.emotionColor(for: emotion.dominant))
                Spacer()
                Text("强度 \(emotion.intensity)%")
                    .font(.system(size: 12))
                    .foregroundColor(isDark ? MiyaColors.textSecondary : MiyaLightColors.textSecondary)
            }

            if let emotions = emotion.emotions, !emotions.isEmpty {
                ForEach(emotions.prefix(6), id: \.name) { e in
                    HStack(spacing: 8) {
                        Text(e.name)
                            .font(.system(size: 12))
                            .foregroundColor(isDark ? MiyaColors.textSecondary : MiyaLightColors.textSecondary)
                            .frame(width: 50, alignment: .leading)
                        GeometryReader { geo in
                            ZStack(alignment: .leading) {
                                RoundedRectangle(cornerRadius: 3)
                                    .fill(isDark ? MiyaColors.surfaceVariant : MiyaLightColors.surfaceVariant)
                                    .frame(height: 6)
                                RoundedRectangle(cornerRadius: 3)
                                    .fill(MiyaColors.emotionColor(for: e.name))
                                    .frame(width: geo.size.width * CGFloat(e.intensity) / 100, height: 6)
                            }
                        }
                        .frame(height: 6)
                        Text("\(e.intensity)%")
                            .font(.system(size: 10, design: .monospaced))
                            .foregroundColor(isDark ? MiyaColors.textDim : MiyaLightColors.textDim)
                    }
                }
            }

            if let thought = emotion.innerThought {
                Text("\u201C\(thought)\u201D")
                    .font(.system(size: 13))
                    .foregroundColor(isDark ? MiyaColors.textSecondary : MiyaLightColors.textSecondary)
                    .padding(12)
                    .background((isDark ? MiyaColors.primary : MiyaLightColors.primary).opacity(0.06))
                    .cornerRadius(8)
            }
        }
        .padding(16)
        .background(isDark ? MiyaColors.surface : MiyaLightColors.surface)
        .cornerRadius(16)
        .padding(.horizontal, 16)
    }
}

struct CognitionCard: View {
    @Environment(\.colorScheme) var colorScheme
    var status: SystemStatusInfo
    var memory: MemoryStatsInfo?
    var isDark: Bool { colorScheme == .dark }

    var body: some View {
        VStack(spacing: 12) {
            HStack {
                statBadge("服务", status.running ? "在线" : "离线", status.running ? .green : .red)
                statBadge("版本", status.version ?? "--", isDark ? MiyaColors.accent : MiyaLightColors.accent)
                statBadge("人格", status.personality ?? "default", isDark ? MiyaColors.primary : MiyaLightColors.primary)
            }
            Divider()
            HStack {
                infoItem("连接平台", "\(status.platformsActive ?? 0)/\(status.platforms ?? 0)")
                infoItem("AI 引擎", "\(status.providersLoaded ?? 0) 个")
            }
            if let uptime = status.uptime { infoItem("运行时间", uptime) }
            if let mem = memory {
                HStack {
                    memDot("总计", mem.total)
                    memDot("对话", mem.dialogue)
                    memDot("长期", mem.longTerm)
                    memDot("语义", mem.semantic)
                    memDot("节点", mem.nodeCount)
                }
            }
        }
        .padding(16)
        .background(isDark ? MiyaColors.surface : MiyaLightColors.surface)
        .cornerRadius(16)
        .padding(.horizontal, 16)
    }

    func statBadge(_ label: String, _ value: String, _ color: Color) -> some View {
        VStack {
            Text(value)
                .font(.system(size: 15, weight: .bold))
                .foregroundColor(color)
            Text(label)
                .font(.system(size: 10))
                .foregroundColor(isDark ? MiyaColors.textDim : MiyaLightColors.textDim)
        }
        .frame(maxWidth: .infinity)
    }

    func infoItem(_ label: String, _ value: String) -> some View {
        HStack(spacing: 4) {
            Text(label)
                .font(.system(size: 13))
                .foregroundColor(isDark ? MiyaColors.textSecondary : MiyaLightColors.textSecondary)
            Text(value)
                .font(.system(size: 13, weight: .medium))
                .foregroundColor(isDark ? MiyaColors.textPrimary : MiyaLightColors.textPrimary)
        }
    }

    func memDot(_ label: String, _ count: Int) -> some View {
        VStack {
            Text("\(count)")
                .font(.system(size: 18, weight: .bold))
                .foregroundColor(isDark ? MiyaColors.primary : MiyaLightColors.primary)
            Text(label)
                .font(.system(size: 10))
                .foregroundColor(isDark ? MiyaColors.textDim : MiyaLightColors.textDim)
        }
        .frame(maxWidth: .infinity)
    }
}

struct MemorySearchCard: View {
    @Binding var query: String
    @Binding var result: String
    @EnvironmentObject var appState: AppState
    @Environment(\.colorScheme) var colorScheme
    var isDark: Bool { colorScheme == .dark }

    var body: some View {
        VStack(spacing: 8) {
            HStack {
                Image(systemName: "magnifyingglass")
                    .foregroundColor(isDark ? MiyaColors.textDim : MiyaLightColors.textDim)
                TextField("搜索弥娅的记忆...", text: $query)
                    .foregroundColor(isDark ? MiyaColors.textPrimary : MiyaLightColors.textPrimary)
                Button("搜索") {
                    Task {
                        do {
                            let items = try await appState.apiService.searchMemory(query: query, limit: 5)
                            result = items.map { String($0.content.prefix(80)) + "..." }.joined(separator: "\n")
                        } catch { result = "搜索失败" }
                    }
                }
                .font(.system(size: 13))
                .foregroundColor(isDark ? MiyaColors.primary : MiyaLightColors.primary)
            }
            if !result.isEmpty {
                Text(result)
                    .font(.system(size: 13))
                    .foregroundColor(isDark ? MiyaColors.textSecondary : MiyaLightColors.textSecondary)
            }
        }
        .padding(16)
        .background(isDark ? MiyaColors.surface : MiyaLightColors.surface)
        .cornerRadius(16)
        .padding(.horizontal, 16)
    }
}

struct DailyStatsCard: View {
    @Environment(\.colorScheme) var colorScheme
    var isDark: Bool { colorScheme == .dark }

    var body: some View {
        HStack {
            DailyStatItem("💬", "12", "对话轮数")
            DailyStatItem("❤️", "joy", "主情绪")
            DailyStatItem("⏱", "5min", "响应速度")
            DailyStatItem("🌟", "8.0", "版本号")
        }
        .padding(20)
        .background(isDark ? MiyaColors.surface : MiyaLightColors.surface)
        .cornerRadius(16)
        .padding(.horizontal, 16)
    }
}

struct DailyStatItem: View {
    @Environment(\.colorScheme) var colorScheme
    var icon: String
    var value: String
    var label: String
    var isDark: Bool { colorScheme == .dark }

    init(_ icon: String, _ value: String, _ label: String) {
        self.icon = icon; self.value = value; self.label = label
    }

    var body: some View {
        VStack(spacing: 4) {
            Text(icon).font(.system(size: 24))
            Text(value)
                .font(.system(size: 18, weight: .bold))
                .foregroundColor(isDark ? MiyaColors.textPrimary : MiyaLightColors.textPrimary)
            Text(label)
                .font(.system(size: 10))
                .foregroundColor(isDark ? MiyaColors.textDim : MiyaLightColors.textDim)
        }
        .frame(maxWidth: .infinity)
    }
}
