import SwiftUI

// ═══════════════════════════════════════════════
// 记忆视图 (PGR 风格)
// ═══════════════════════════════════════════════

struct MemoryView: View {
    @EnvironmentObject var appState: AppState

    @State private var memories: [MemoryItem] = []
    @State private var searchQuery = ""
    @State private var isLoading = true

    var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                HStack {
                    Image(systemName: "magnifyingglass")
                        .foregroundColor(MiyaColors.textSecondary)
                    TextField("搜索记忆...", text: $searchQuery)
                        .foregroundColor(MiyaColors.textPrimary)
                        .onSubmit { performSearch() }
                    if !searchQuery.isEmpty {
                        Button(action: {
                            searchQuery = ""
                            performSearch()
                        }) {
                            Image(systemName: "xmark.circle.fill")
                                .foregroundColor(MiyaColors.textSecondary)
                        }
                    }
                }
                .padding(12)
                .background(RoundedRectangle(cornerRadius: 14).fill(MiyaColors.surface))
                .padding(.horizontal, 16)
                .padding(.top, 8)

                if isLoading {
                    Spacer()
                    ProgressView().tint(MiyaColors.primary)
                    Spacer()
                } else if memories.isEmpty {
                    Spacer()
                    VStack(spacing: 8) {
                        Image(systemName: "brain.head.profile")
                            .font(.system(size: 48))
                            .foregroundColor(MiyaColors.textDim)
                        Text("没有找到记忆")
                            .foregroundColor(MiyaColors.textSecondary)
                    }
                    Spacer()
                } else {
                    List(memories) { memory in
                        MemoryCardView(memory: memory)
                            .listRowBackground(Color.clear)
                            .listRowSeparator(.hidden)
                    }
                    .listStyle(.plain)
                    .scrollContentBackground(.hidden)
                }
            }
            .background(MiyaColors.background)
            .navigationTitle("记忆")
            .navigationBarTitleDisplayMode(.large)
        }
        .task { await loadMemories() }
    }

    private func loadMemories() async {
        isLoading = true
        do {
            memories = try await appState.apiService.getMemoryList()
        } catch {
            memories = []
        }
        isLoading = false
    }

    private func performSearch() {
        Task {
            isLoading = true
            do {
                memories = searchQuery.isEmpty
                    ? try await appState.apiService.getMemoryList()
                    : try await appState.apiService.searchMemory(searchQuery)
            } catch {
                memories = []
            }
            isLoading = false
        }
    }
}

struct MemoryCardView: View {
    let memory: MemoryItem

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Image(systemName: "memorychip")
                    .font(.caption)
                    .foregroundColor(MiyaColors.primary)
                Text(memory.level)
                    .font(.caption)
                    .foregroundColor(MiyaColors.accent)
                    .padding(.horizontal, 8)
                    .padding(.vertical, 2)
                    .background(Capsule().fill(MiyaColors.accent.opacity(0.15)))
                if let priority = memory.priority {
                    Spacer()
                    HStack(spacing: 2) {
                        Image(systemName: "star.fill").font(.system(size: 8))
                        Text(String(format: "%.1f", priority))
                    }
                    .font(.caption2)
                    .foregroundColor(MiyaColors.textDim)
                }
            }

            Text(memory.content)
                .font(.subheadline)
                .foregroundColor(MiyaColors.textPrimary)
                .lineLimit(3)

            if let tags = memory.tags, !tags.isEmpty {
                ScrollView(.horizontal, showsIndicators: false) {
                    HStack(spacing: 6) {
                        ForEach(tags, id: \.self) { tag in
                            Text("#\(tag)")
                                .font(.caption2)
                                .foregroundColor(MiyaColors.primary)
                                .padding(.horizontal, 6)
                                .padding(.vertical, 2)
                                .background(RoundedRectangle(cornerRadius: 4).fill(MiyaColors.primary.opacity(0.12)))
                        }
                    }
                }
            }

            if let date = memory.createdAt {
                Text(date)
                    .font(.caption2)
                    .foregroundColor(MiyaColors.textDim)
            }
        }
        .padding(14)
        .background(RoundedRectangle(cornerRadius: 12).fill(MiyaColors.surface))
    }
}

#Preview {
    MemoryView()
        .environmentObject(AppState())
}
