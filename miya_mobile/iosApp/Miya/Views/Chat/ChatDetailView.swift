import SwiftUI

struct ChatDetailView: View {
    @Environment(\.colorScheme) var colorScheme
    @EnvironmentObject var appState: AppState
    @State private var messages: [ChatMessage] = [
        ChatMessage(isMiya: true, content: "你好，我是弥娅 ❤️ 有什么可以帮你的？", timestamp: Date().addingTimeInterval(-60))
    ]
    @State private var inputText = ""
    @State private var isStreaming = false
    @State private var currentEmotion = "neutral"

    let sessionId: String
    let sessionName: String
    var onBack: () -> Void
    var isDark: Bool { colorScheme == .dark }

    var body: some View {
        VStack(spacing: 0) {
            // 顶部栏
            HStack(spacing: 10) {
                Button(action: onBack) {
                    Image(systemName: "chevron.left")
                        .font(.system(size: 18, weight: .semibold))
                        .foregroundColor(isDark ? MiyaColors.textPrimary : MiyaLightColors.textPrimary)
                }
                ZStack {
                    Circle()
                        .fill((isDark ? MiyaColors.primary : MiyaLightColors.primary).opacity(0.15))
                        .frame(width: 38, height: 38)
                    Text("弥")
                        .font(.system(size: 16, weight: .bold))
                        .foregroundColor(isDark ? MiyaColors.primary : MiyaLightColors.primary)
                }
                VStack(alignment: .leading, spacing: 2) {
                    Text(sessionName)
                        .font(.system(size: 17, weight: .semibold))
                        .foregroundColor(isDark ? MiyaColors.textPrimary : MiyaLightColors.textPrimary)
                    Text(isStreaming ? "正在输入..." : currentEmotion)
                        .font(.system(size: 11))
                        .foregroundColor(isDark ? MiyaColors.accent : MiyaLightColors.accent)
                }
                Spacer()
                Button(action: {}) {
                    Image(systemName: "ellipsis")
                        .foregroundColor(isDark ? MiyaColors.textPrimary : MiyaLightColors.textPrimary)
                }
            }
            .padding(.horizontal, 8)
            .padding(.vertical, 10)
            .background(isDark ? MiyaColors.background : MiyaLightColors.background)

            Divider()
                .background(isDark ? MiyaColors.borderDim : MiyaLightColors.borderDim)

            // 消息列表
            ScrollViewReader { proxy in
                ScrollView {
                    LazyVStack(spacing: 4) {
                        ForEach(messages) { msg in
                            ChatBubbleView(msg: msg, isDark: isDark)
                                .id(msg.id)
                                .padding(.horizontal, 12)
                                .padding(.vertical, 2)
                        }
                    }
                    .padding(.vertical, 8)
                }
                .background(isDark ? MiyaColors.background : MiyaLightColors.background)
                .onChange(of: messages.count) { _, _ in
                    if let last = messages.last {
                        withAnimation { proxy.scrollTo(last.id, anchor: .bottom) }
                    }
                }
            }

            // 底部输入栏
            HStack(spacing: 6) {
                Button(action: {}) {
                    Image(systemName: "mic.fill")
                        .font(.system(size: 20))
                        .foregroundColor(isDark ? MiyaColors.textSecondary : MiyaLightColors.textSecondary)
                }
                .frame(width: 36, height: 36)

                TextField("和弥娅说点什么...", text: $inputText, axis: .vertical)
                    .padding(.horizontal, 14)
                    .padding(.vertical, 10)
                    .background(isDark ? MiyaColors.surface : MiyaLightColors.surface)
                    .cornerRadius(20)
                    .foregroundColor(isDark ? MiyaColors.textPrimary : MiyaLightColors.textPrimary)
                    .lineLimit(4)

                Button(action: {}) {
                    Image(systemName: "face.smiling")
                        .font(.system(size: 20))
                        .foregroundColor(isDark ? MiyaColors.textSecondary : MiyaLightColors.textSecondary)
                }
                .frame(width: 36, height: 36)

                Button(action: sendMessage) {
                    Image(systemName: inputText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty ? "plus" : "paperplane.fill")
                        .font(.system(size: 20))
                        .foregroundColor(inputText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
                            ? (isDark ? MiyaColors.textSecondary : MiyaLightColors.textSecondary)
                            : (isDark ? MiyaColors.primary : MiyaLightColors.primary))
                }
                .frame(width: 36, height: 36)
                .disabled(inputText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty && !isStreaming)
            }
            .padding(.horizontal, 10)
            .padding(.vertical, 8)
            .background(isDark ? MiyaColors.background : MiyaLightColors.background)
        }
    }

    private func sendMessage() {
        let text = inputText.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !text.isEmpty, !isStreaming else { return }
        messages.append(ChatMessage(isMiya: false, content: text))
        inputText = ""
        isStreaming = true

        let miyaMsg = ChatMessage(isMiya: true, content: "", isStreaming: true)
        messages.append(miyaMsg)

        Task {
            var fullResponse = ""
            do {
                let stream = try await appState.apiService.streamChat(message: text, sessionId: sessionId)
                for try await chunk in stream {
                    fullResponse += chunk
                    if let idx = messages.firstIndex(where: { $0.id == miyaMsg.id }) {
                        messages[idx].content = fullResponse
                    }
                }
                if let idx = messages.firstIndex(where: { $0.id == miyaMsg.id }) {
                    messages[idx].isStreaming = false
                }
            } catch {
                if let idx = messages.firstIndex(where: { $0.id == miyaMsg.id && $0.content.isEmpty }) {
                    messages[idx].content = "连接失败，请检查网络"
                    messages[idx].isStreaming = false
                }
            }
            isStreaming = false
        }
    }
}

struct ChatBubbleView: View {
    let msg: ChatMessage
    let isDark: Bool

    var body: some View {
        HStack(alignment: .top, spacing: 8) {
            if msg.isMiya {
                ZStack {
                    Circle()
                        .fill((isDark ? MiyaColors.primary : MiyaLightColors.primary).opacity(0.15))
                        .frame(width: 36, height: 36)
                    Text("弥")
                        .font(.system(size: 14, weight: .bold))
                        .foregroundColor(isDark ? MiyaColors.primary : MiyaLightColors.primary)
                }
                Text(msg.content + (msg.isStreaming ? "▌" : ""))
                    .font(.system(size: 15))
                    .foregroundColor(isDark ? MiyaColors.textPrimary : MiyaLightColors.textPrimary)
                    .padding(.horizontal, 12)
                    .padding(.vertical, 10)
                    .background(isDark ? MiyaColors.surfaceDeep : MiyaLightColors.bubbleMiya)
                    .cornerRadius(18, corners: [.topLeft, .topRight, .bottomRight])
                Spacer(minLength: 40)
            } else {
                Spacer(minLength: 40)
                Text(msg.content)
                    .font(.system(size: 15))
                    .foregroundColor(.white)
                    .padding(.horizontal, 12)
                    .padding(.vertical, 10)
                    .background(isDark ? MiyaColors.chatUser : MiyaLightColors.bubbleMe)
                    .cornerRadius(18, corners: [.topLeft, .topRight, .bottomLeft])
            }
        }
    }
}

extension View {
    func cornerRadius(_ radius: CGFloat, corners: UIRectCorner) -> some View {
        clipShape(RoundedCorner(radius: radius, corners: corners))
    }
}

struct RoundedCorner: Shape {
    var radius: CGFloat = .infinity
    var corners: UIRectCorner = .allCorners

    func path(in rect: CGRect) -> Path {
        let path = UIBezierPath(
            roundedRect: rect,
            byRoundingCorners: corners,
            cornerRadii: CGSize(width: radius, height: radius)
        )
        return Path(path.cgPath)
    }
}
