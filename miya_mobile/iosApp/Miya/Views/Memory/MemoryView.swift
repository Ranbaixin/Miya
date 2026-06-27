import SwiftUI

struct MemoryView: View {
    @EnvironmentObject var appState: AppState

    @State private var memories: [MemoryItem] = []
    @State private var searchQuery = ""
    @State private var isLoading = true

    var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                // 搜索栏
                HStack {
                    Image(systemName: "magnifyingglass")
                        .foregroundColor(.white.opacity(0.5))
                    TextField("搜索记忆...", text: $searchQuery)
                        .foregroundColor(.white)
                        .onSubmit { performSearch() }
                    if !searchQuery.isEmpty {
                        Button(action: {
                            searchQuery = ""
                            performSearch()
                        }) {
                            Image(systemName: "xmark.circle.fill")
                                .foregroundColor(.white.opacity(0.5))
                        }
                    }
                }
                .padding(12)
                .background(RoundedRectangle(cornerRadius: 14).fill(Color("MiyaSurface")))
                .padding(.horizontal, 16)
                .padding(.top, 8)

                // 记忆列表
                if isLoading {
                    Spacer()
                    ProgressView()
                        .tint(Color("MiyaPrimary"))
                    Spacer()
                } else if memories.isEmpty {
                    Spacer()
                    VStack(spacing: 8) {
                        Image(systemName: "brain.head.profile")
                            .font(.system(size: 48))
                            .foregroundColor(.white.opacity(0.3))
                        Text("没有找到记忆")
                            .foregroundColor(.white.opacity(0.5))
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
            .background(Color("MiyaBackground"))
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
                if searchQuery.isEmpty {
                    memories = try await appState.apiService.getMemoryList()
                } else {
                    memories = try await appState.apiService.searchMemory(searchQuery)
                }
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
                    .foregroundColor(Color("MiyaPrimary"))
                Text(memory.level)
                    .font(.caption)
                    .foregroundColor(Color("MiyaAccent"))
                    .padding(.horizontal, 8)
                    .padding(.vertical, 2)
                    .background(Capsule().fill(Color("MiyaAccent").opacity(0.15)))
                if let priority = memory.priority {
                    Spacer()
                    HStack(spacing: 2) {
                        Image(systemName: "star.fill")
                            .font(.system(size: 8))
                        Text(String(format: "%.1f", priority))
                    }
                    .font(.caption2)
                    .foregroundColor(.white.opacity(0.4))
                }
            }

            Text(memory.content)
                .font(.subheadline)
                .foregroundColor(.white)
                .lineLimit(3)

            if let tags = memory.tags, !tags.isEmpty {
                ScrollView(.horizontal, showsIndicators: false) {
                    HStack(spacing: 6) {
                        ForEach(tags, id: \.self) { tag in
                            Text("#\(tag)")
                                .font(.caption2)
                                .foregroundColor(Color("MiyaPrimary"))
                                .padding(.horizontal, 6)
                                .padding(.vertical, 2)
                                .background(RoundedRectangle(cornerRadius: 4).fill(Color("MiyaPrimary").opacity(0.12)))
                        }
                    }
                }
            }

            if let date = memory.createdAt {
                Text(date)
                    .font(.caption2)
                    .foregroundColor(.white.opacity(0.3))
            }
        }
        .padding(14)
        .background(RoundedRectangle(cornerRadius: 12).fill(Color("MiyaSurface")))
    }
}

#Preview {
    MemoryView()
        .environmentObject(AppState())
}
