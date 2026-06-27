import SwiftUI

// MARK: - 聊天主视图 (全屏角色 + 浮层聊天)

struct ChatView: View {
    @EnvironmentObject var appState: AppState

    @State private var messages: [ChatMessage] = []
    @State private var inputText = ""
    @State private var isStreaming = false
    @State private var currentSessionId: String?
    @State private var showSessionList = false
    @State private var sessions: [MiyaSession] = []

    /// Live2D 状态推断
    private var live2dState: Live2DCharacterView.Live2DState {
        if isStreaming {
            return messages.last?.isMiya == true ? .talking : .thinking
        }
        return .idle
    }

    var body: some View {
        ZStack {
            // ── Live2D 角色全屏背景 ──
            Live2DCharacterView(emotion: appState.currentEmotion, state: live2dState)
                .ignoresSafeArea()

            // ── 聊天浮层 (底部区域) ──
            VStack(spacing: 0) {
                Spacer(minLength: 0)

                // 消息列表 (半透明)
                ScrollViewReader { scrollProxy in
                    ScrollView {
                        LazyVStack(spacing: 6) {
                            ForEach(messages) { msg in
                                ChatBubbleView(message: msg)
                                    .id(msg.id)
                            }
                        }
                        .padding(.horizontal, 12)
                        .padding(.top, 12)
                    }
                    .background(
                        .ultraThinMaterial
                            .opacity(0.85)
                            .clipShape(UnevenRoundedRectangle(
                                topLeadingRadius: 20,
                                topTrailingRadius: 20
                            ))
                    )
                    .frame(maxHeight: UIScreen.main.bounds.height * 0.38)
                    .onChange(of: messages.count) { _, _ in
                        if let last = messages.last {
                            withAnimation { scrollProxy.scrollTo(last.id, anchor: .bottom) }
                        }
                    }
                }

                // 输入栏
                InputBarView(
                    text: $inputText,
                    isStreaming: $isStreaming,
                    onSend: { sendMessage() },
                    onStop: { stopChat() }
                )
                .background(.ultraThinMaterial.opacity(0.9))
            }
        }
        .onAppear {
            Task {
                sessions = (try? await appState.apiService.getSessions()) ?? []
            }
        }
    }

    private func sendMessage() {
        let text = inputText.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !text.isEmpty, !isStreaming else { return }

        messages.append(ChatMessage(content: text, isMiya: false))
        inputText = ""
        isStreaming = true

        let miyaMessage = ChatMessage(content: "", isMiya: true, isStreaming: true)
        messages.append(miyaMessage)

        Task {
            var fullResponse = ""
            let stream = appState.apiService.streamChat(text, sessionId: currentSessionId)

            do {
                for try await chunk in stream {
                    fullResponse += chunk
                    if let index = messages.lastIndex(where: { $0.isMiya }) {
                        messages[index] = ChatMessage(content: fullResponse, isMiya: true, isStreaming: true)
                    }
                }
            } catch {
                if let index = messages.lastIndex(where: { $0.isMiya }) {
                    messages[index] = ChatMessage(content: fullResponse.isEmpty ? "连接失败..." : fullResponse, isMiya: true)
                }
            }

            if let index = messages.lastIndex(where: { $0.isMiya }) {
                messages[index] = ChatMessage(content: fullResponse, isMiya: true, isStreaming: false)
            }
            isStreaming = false

            sessions = (try? await appState.apiService.getSessions()) ?? []
        }
    }

    private func stopChat() {
        Task {
            await appState.apiService.stopChat()
            isStreaming = false
        }
    }
}

// MARK: - 聊天气泡

struct ChatBubbleView: View {
    let message: ChatMessage

    var body: some View {
        HStack(alignment: .top, spacing: 8) {
            if message.isMiya {
                // 弥娅头像
                Image(systemName: "face.smiling")
                    .font(.title3)
                    .foregroundColor(Color("MiyaPrimary"))
                    .frame(width: 30, height: 30)
                    .background(Circle().fill(.white.opacity(0.1)))
            } else {
                Spacer(minLength: 50)
            }

            Text(message.content + (message.isStreaming ? " ▌" : ""))
                .font(.system(size: 15))
                .foregroundColor(.white)
                .padding(.horizontal, 12)
                .padding(.vertical, 8)
                .background(
                    message.isMiya
                        ? Color.white.opacity(0.1)
                        : Color("MiyaPrimary").opacity(0.3)
                )
                .clipShape(
                    RoundedRectangle(cornerRadius: 16)
                )
                .contextMenu {
                    Button(action: { UIPasteboard.general.string = message.content }) {
                        Label("复制", systemImage: "doc.on.doc")
                    }
                }

            if !message.isMiya {
                Image(systemName: "person.circle.fill")
                    .font(.title3)
                    .foregroundColor(Color("MiyaPrimary").opacity(0.6))
                    .frame(width: 30, height: 30)
                Spacer(minLength: 50)
            }
        }
    }
}

// MARK: - 输入栏

struct InputBarView: View {
    @Binding var text: String
    @Binding var isStreaming: Bool
    let onSend: () -> Void
    let onStop: () -> Void

    @FocusState private var isFocused: Bool

    var body: some View {
        HStack(spacing: 10) {
            // 语音按钮
            Button(action: {}) {
                Image(systemName: "mic.fill")
                    .font(.title3)
                    .foregroundColor(.white.opacity(0.6))
            }

            // 输入框
            TextField("和弥娅说点什么...", text: $text, axis: .vertical)
                .focused($isFocused)
                .padding(.horizontal, 14)
                .padding(.vertical, 10)
                .background(
                    RoundedRectangle(cornerRadius: 22)
                        .fill(.white.opacity(0.08))
                )
                .foregroundColor(.white)
                .lineLimit(1...4)

            // 发送/停止按钮
            if isStreaming {
                Button(action: onStop) {
                    Image(systemName: "stop.fill")
                        .font(.title3)
                        .foregroundColor(.red)
                }
            } else {
                Button(action: onSend) {
                    Image(systemName: "arrow.up.circle.fill")
                        .font(.system(size: 32))
                        .foregroundColor(text.trimmingCharacters(in: .whitespaces).isEmpty
                            ? .white.opacity(0.3)
                            : Color("MiyaPrimary")
                        )
                }
                .disabled(text.trimmingCharacters(in: .whitespaces).isEmpty)
            }
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 8)
    }
}

#Preview {
    ChatView()
        .environmentObject(AppState())
}
