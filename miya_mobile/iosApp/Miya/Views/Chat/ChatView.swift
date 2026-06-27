import SwiftUI
import PhotosUI

// MARK: - 聊天主视图 (全屏角色 + 浮层聊天, PGR 风格)

struct ChatView: View {
    @EnvironmentObject var appState: AppState

    @State private var messages: [ChatMessage] = []
    @State private var inputText = ""
    @State private var isStreaming = false
    @State private var currentSessionId: String?
    @State private var sessions: [MiyaSession] = []
    @State private var showStickerPicker = false
    @State private var showImagePicker = false
    @State private var selectedPhotoItem: PhotosPickerItem?
    @State private var quotedMessage: ChatMessage?

    // 相机/相册
    @State private var showCamera = false
    @State private var cameraImage: UIImage?

    var body: some View {
        // 聊天全屏
        VStack(spacing: 0) {
                // 顶部状态栏 (QQ 风格)
                chatTopBar

                // 消息列表 (占满剩余空间)
                ScrollViewReader { scrollProxy in
                    ScrollView {
                        LazyVStack(spacing: 0) {
                            ForEach(Array(groupedMessages.enumerated()), id: \.element.id) { _, group in
                                if group.isTimeDivider {
                                    timeDivider(group.timestamp)
                                } else {
                                    ForEach(group.messages) { msg in
                                        messageBubble(msg)
                                            .id(msg.id)
                                    }
                                }
                            }
                        }
                        .padding(.horizontal, 10)
                        .padding(.vertical, 8)
                    }
                    .onChange(of: messages.count) { _, _ in
                        if let last = messages.last {
                            withAnimation { scrollProxy.scrollTo(last.id, anchor: .bottom) }
                        }
                    }
                }

                // 引用预览
                if let quoted = quotedMessage {
                    quotePreview(quoted)
                }

                // 输入栏
                InputBarView(
                    text: $inputText,
                    isStreaming: $isStreaming,
                    onSend: { sendMessage() },
                    onStop: { stopChat() },
                    onSticker: { showStickerPicker.toggle() },
                    onImage: { showImagePicker = true }
                )
                .background(MiyaColors.background.opacity(0.95))
        }
        .ignoresSafeArea(.keyboard)
        .onAppear {
            Task { sessions = (try? await appState.apiService.getSessions()) ?? [] }
        }
        .sheet(isPresented: $showStickerPicker) {
            StickerPickerView { stickerId, stickerUrl in
                sendSticker(stickerId: stickerId, stickerUrl: stickerUrl)
                showStickerPicker = false
            }
            .presentationDetents([.medium, .large])
        }
        .confirmationDialog("发送图片", isPresented: $showImagePicker) {
            Button("拍照") { showCamera = true }
            PhotosPicker(selection: $selectedPhotoItem, matching: .images) {
                Text("从相册选择")
            }
            Button("取消", role: .cancel) {}
        }
        .fullScreenCover(isPresented: $showCamera) {
            ImagePicker(sourceType: .camera) { image in
                cameraImage = image
                if let img = image, let data = img.jpegData(compressionQuality: 0.8) {
                    let url = saveImageToTemp(data: data)
                    sendImageMessage(url: url)
                }
                showCamera = false
            }
        }
        .onChange(of: selectedPhotoItem) { _, newItem in
            guard let item = newItem else { return }
            Task {
                if let data = try? await item.loadTransferable(type: Data.self) {
                    let url = saveImageToTemp(data: data)
                    sendImageMessage(url: url)
                }
            }
        }
    }

    // MARK: - 消息发送

    private func sendMessage() {
        let text = inputText.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !text.isEmpty, !isStreaming else { return }

        var msg = ChatMessage(content: text, isMiya: false, timestamp: Date())
        if let quoted = quotedMessage {
            msg.quoteContent = String(quoted.content.prefix(50))
            msg.quoteSender = quoted.isMiya ? "弥娅" : "你"
        }

        messages.append(msg)
        inputText = ""
        quotedMessage = nil
        isStreaming = true

        let miyaMsg = ChatMessage(content: "", isMiya: true, isStreaming: true, timestamp: Date())
        messages.append(miyaMsg)

        Task {
            var fullResponse = ""
            let stream = appState.apiService.streamChat(text, sessionId: currentSessionId)
            do {
                for try await chunk in stream {
                    fullResponse += chunk
                    if let index = messages.lastIndex(where: { $0.isMiya }) {
                        messages[index].content = fullResponse
                        messages[index].isStreaming = true
                    }
                }
            } catch {
                if let index = messages.lastIndex(where: { $0.isMiya }) {
                    messages[index].content = fullResponse.isEmpty ? "连接失败..." : fullResponse
                }
            }

            if let index = messages.lastIndex(where: { $0.isMiya }) {
                messages[index].isStreaming = false
                messages[index].emotion = appState.currentEmotion.rawValue
            }
            isStreaming = false
            sessions = (try? await appState.apiService.getSessions()) ?? []
        }
    }

    private func sendSticker(stickerId: String, stickerUrl: String) {
        messages.append(ChatMessage(
            contentType: .sticker,
            stickerId: stickerId,
            stickerUrl: stickerUrl,
            isMiya: false,
            timestamp: Date()
        ))

        Task {
            let stream = appState.apiService.streamChat("[表情:\(stickerId)]", sessionId: currentSessionId)
            var fullResponse = ""
            do {
                for try await _ in stream { }
            } catch {}
        }
    }

    private func sendImageMessage(url: String) {
        messages.append(ChatMessage(
            contentType: .image,
            content: "[图片]",
            imageUrl: url,
            isMiya: false,
            timestamp: Date()
        ))

        Task {
            let stream = appState.apiService.streamChat("[用户发送了一张图片]", sessionId: currentSessionId)
            var fullResponse = ""
            do {
                for try await _ in stream { }
            } catch {}
        }
    }

    private func stopChat() {
        Task {
            await appState.apiService.stopChat()
            isStreaming = false
        }
    }

    private func saveImageToTemp(data: Data) -> String {
        let dir = FileManager.default.temporaryDirectory
        let fileURL = dir.appendingPathComponent("miya_img_\(Date().timeIntervalSince1970).jpg")
        try? data.write(to: fileURL)
        return fileURL.absoluteString
    }

    // MARK: - 消息分组

    struct MessageGroup: Identifiable {
        let id = UUID()
        let messages: [ChatMessage]
        let timestamp: Date
        let isTimeDivider: Bool
    }

    private var groupedMessages: [MessageGroup] {
        guard !messages.isEmpty else { return [] }
        var result: [MessageGroup] = []
        var lastTime: Date?
        var current: [ChatMessage] = []

        for msg in messages {
            if let last = lastTime, msg.timestamp.timeIntervalSince(last) > 300 {
                if !current.isEmpty {
                    result.append(MessageGroup(messages: current, timestamp: current.first!.timestamp, isTimeDivider: false))
                    current = []
                }
                result.append(MessageGroup(messages: [], timestamp: msg.timestamp, isTimeDivider: true))
            }
            current.append(msg)
            lastTime = msg.timestamp
        }
        if !current.isEmpty {
            result.append(MessageGroup(messages: current, timestamp: current.first!.timestamp, isTimeDivider: false))
        }
        return result
    }

    // MARK: - UI 组件

    private var chatTopBar: some View {
        HStack(spacing: 8) {
            Text(sessions.first { $0.id == currentSessionId }?.name ?? "弥娅")
                .font(.system(size: 18, weight: .semibold))
                .foregroundColor(MiyaColors.textPrimary)
            Text(isStreaming ? "正在输入..." : appState.currentEmotion.rawValue)
                .font(.system(size: 12))
                .foregroundColor(isStreaming
                    ? MiyaColors.accent
                    : MiyaColors.emotionColor(for: appState.currentEmotion.rawValue).opacity(0.7))
            if isStreaming {
                Circle()
                    .fill(MiyaColors.accent)
                    .frame(width: 6, height: 6)
            }
            Spacer()
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 12)
        .background(.ultraThinMaterial)
    }

    private func timeDivider(_ timestamp: Date) -> some View {
        let formatter = DateFormatter()
        formatter.dateFormat = Calendar.current.isDateInToday(timestamp) ? "HH:mm" : "MM-dd HH:mm"

        return HStack {
            Spacer()
            Text(formatter.string(from: timestamp))
                .font(.system(size: 11, design: .monospaced))
                .foregroundColor(MiyaColors.textSecondary)
                .padding(.horizontal, 10)
                .padding(.vertical, 3)
                .background(MiyaColors.surfaceDeep)
                .clipShape(RoundedRectangle(cornerRadius: 8))
            Spacer()
        }
        .padding(.vertical, 6)
    }

    private func quotePreview(_ quoted: ChatMessage) -> some View {
        HStack(spacing: 8) {
            Rectangle()
                .fill(MiyaColors.accent)
                .frame(width: 3, height: 28)
                .clipShape(RoundedRectangle(cornerRadius: 2))

            VStack(alignment: .leading, spacing: 1) {
                Text(quoted.isMiya ? "弥娅" : "你")
                    .font(.caption)
                    .foregroundColor(MiyaColors.accent)
                Text(quoted.content.isEmpty ? "[表情]" : quoted.content)
                    .font(.caption2)
                    .foregroundColor(MiyaColors.textSecondary)
                    .lineLimit(1)
            }
            Spacer()
            Button(action: { quotedMessage = nil }) {
                Image(systemName: "xmark")
                    .font(.caption)
                    .foregroundColor(MiyaColors.textSecondary)
            }
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 6)
        .background(MiyaColors.surfaceDeep)
    }
}

// MARK: - 消息气泡 (PGR 风格)

func messageBubble(_ msg: ChatMessage) -> some View {
    let isMiya = msg.isMiya
    let emotionKey = msg.emotion ?? "neutral"
    let emotionCol = MiyaColors.emotionColor(for: emotionKey)

    return VStack(alignment: isMiya ? .leading : .trailing, spacing: 2) {
        // 发送者标签 + 情绪光带
        HStack(spacing: 4) {
            if isMiya {
                Capsule()
                    .fill(emotionCol)
                    .frame(width: 24, height: 3)
                Text("MIYA")
                    .font(.system(size: 9, design: .monospaced))
                    .foregroundColor(MiyaColors.accent.opacity(0.6))
                Text(emotionKey.uppercased())
                    .font(.system(size: 8, design: .monospaced))
                    .foregroundColor(emotionCol.opacity(0.7))
            } else {
                Text("YOU")
                    .font(.system(size: 9, design: .monospaced))
                    .foregroundColor(MiyaColors.primary.opacity(0.6))
            }
        }
        .padding(.horizontal, 6)

        // 气泡内容
        Group {
            switch msg.contentType {
            case .sticker:
                if let url = msg.stickerUrl, let nsUrl = URL(string: url),
                   url.hasPrefix("http") {
                    AsyncImage(url: nsUrl) { phase in
                        switch phase {
                        case .success(let image):
                            image.resizable().scaledToFit().frame(width: 80, height: 80)
                                .clipShape(RoundedRectangle(cornerRadius: 12))
                        case .failure, .empty:
                            stickerFallback(msg)
                        @unknown default:
                            stickerFallback(msg)
                        }
                    }
                } else {
                    stickerFallback(msg)
                }

            case .image:
                if let url = msg.imageUrl, let nsUrl = URL(string: url) {
                    if url.hasPrefix("http") {
                        AsyncImage(url: nsUrl) { phase in
                            switch phase {
                            case .success(let image):
                                image.resizable().scaledToFit()
                                    .frame(maxWidth: 200, maxHeight: 200)
                                    .clipShape(RoundedRectangle(cornerRadius: 10))
                                    .overlay(PGRClipShape(clip: 8).stroke(
                                        MiyaColors.border.opacity(0.3), lineWidth: 1
                                    ))
                            case .failure, .empty:
                                imageFallback
                            @unknown default:
                                imageFallback
                            }
                        }
                    } else if let data = try? Data(contentsOf: nsUrl),
                              let uiImage = UIImage(data: data) {
                        Image(uiImage: uiImage)
                            .resizable().scaledToFit()
                            .frame(maxWidth: 200, maxHeight: 200)
                            .clipShape(RoundedRectangle(cornerRadius: 10))
                    } else {
                        imageFallback
                    }
                } else {
                    imageFallback
                }

            default:
                VStack(alignment: .leading, spacing: 0) {
                    // 引用块
                    if let quoteContent = msg.quoteContent {
                        HStack(spacing: 0) {
                            Rectangle()
                                .fill(MiyaColors.border.opacity(0.4))
                                .frame(width: 3)
                            VStack(alignment: .leading, spacing: 1) {
                                Text(msg.quoteSender ?? "")
                                    .font(.system(size: 10, design: .monospaced))
                                    .foregroundColor(MiyaColors.accent.opacity(0.7))
                                Text(quoteContent)
                                    .font(.system(size: 11))
                                    .foregroundColor(MiyaColors.textSecondary)
                                    .lineLimit(2)
                            }
                            .padding(.leading, 6)
                        }
                        .padding(.bottom, 6)
                    }

                    Text(msg.content + (msg.isStreaming ? " ▌" : ""))
                        .font(.system(size: 14))
                        .foregroundColor(isMiya ? MiyaColors.accent.opacity(0.85) : MiyaColors.textPrimary)
                }
            }
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 8)
        .frame(maxWidth: 280, alignment: isMiya ? .leading : .trailing)
        .background(
            PGRClipShape(clip: 8)
                .fill(isMiya ? MiyaColors.surfaceDeep : MiyaColors.primary.opacity(0.18))
                .overlay(PGRClipShape(clip: 8).stroke(
                    isMiya ? MiyaColors.border.opacity(0.25) : MiyaColors.primary.opacity(0.4),
                    lineWidth: 1
                ))
        )
        .contextMenu {
            Button(action: { UIPasteboard.general.string = msg.content }) {
                Label("复制", systemImage: "doc.on.doc")
            }
            Button(action: {
                // 引用回复 - 通过通知传递
            }) {
                Label("引用", systemImage: "arrowshape.turn.up.left")
            }
        }
        .onLongPressGesture {
            // 设置引用消息
        }
    }
    .frame(maxWidth: .infinity, alignment: isMiya ? .leading : .trailing)
}

private func stickerFallback(_ msg: ChatMessage) -> some View {
    let sticker = builtInStickers.first { $0.id == msg.stickerId }
    return Text(sticker?.emoji ?? "😊")
        .font(.system(size: 48))
}

private var imageFallback: some View {
    Image(systemName: "photo")
        .font(.title)
        .foregroundColor(MiyaColors.textSecondary)
        .frame(width: 80, height: 80)
}

// MARK: - 输入栏 (PGR 风格)

struct InputBarView: View {
    @Binding var text: String
    @Binding var isStreaming: Bool
    let onSend: () -> Void
    let onStop: () -> Void
    let onSticker: () -> Void
    let onImage: () -> Void

    @FocusState private var isFocused: Bool

    var body: some View {
        HStack(spacing: 8) {
            // 图片按钮
            Button(action: onImage) {
                Image(systemName: "photo")
                    .font(.system(size: 20))
                    .foregroundColor(MiyaColors.textSecondary)
            }

            // 表情按钮
            Button(action: onSticker) {
                Image(systemName: "face.smiling")
                    .font(.system(size: 20))
                    .foregroundColor(MiyaColors.textSecondary)
            }

            // 语音按钮
            Button(action: {}) {
                Image(systemName: "mic")
                    .font(.system(size: 20))
                    .foregroundColor(MiyaColors.textSecondary)
            }

            // 输入框
            TextField("和弥娅说点什么...", text: $text, axis: .vertical)
                .focused($isFocused)
                .padding(.horizontal, 14)
                .padding(.vertical, 10)
                .background(
                    RoundedRectangle(cornerRadius: 22)
                        .fill(MiyaColors.background)
                        .overlay(
                            RoundedRectangle(cornerRadius: 22)
                                .stroke(MiyaColors.borderDim, lineWidth: 1)
                        )
                )
                .foregroundColor(MiyaColors.textPrimary)
                .lineLimit(1...4)

            // 发送/停止
            if isStreaming {
                Button(action: onStop) {
                    Image(systemName: "stop.fill")
                        .font(.system(size: 22))
                        .foregroundColor(MiyaColors.emotionAnger)
                }
            } else {
                Button(action: onSend) {
                    Image(systemName: "arrow.up.circle.fill")
                        .font(.system(size: 32))
                        .foregroundColor(text.trimmingCharacters(in: .whitespaces).isEmpty
                            ? MiyaColors.textSecondary
                            : MiyaColors.primary
                        )
                }
                .disabled(text.trimmingCharacters(in: .whitespaces).isEmpty)
            }
        }
        .padding(.horizontal, 10)
        .padding(.vertical, 8)
    }
}

// MARK: - 表情包选择面板

struct StickerPickerView: View {
    let onSelect: (String, String) -> Void
    @State private var selectedTab = 0
    @State private var searchQuery = ""

    let tabs = ["弥娅表情", "搜索表情"]

    let columns = [GridItem(.adaptive(minimum: 50), spacing: 6)]

    var body: some View {
        VStack(spacing: 0) {
            // 标签栏
            Picker("标签", selection: $selectedTab) {
                ForEach(0..<tabs.count, id: \.self) { i in
                    Text(tabs[i]).tag(i)
                }
            }
            .pickerStyle(.segmented)
            .padding(.horizontal, 16)
            .padding(.top, 12)

            // 内容
            if selectedTab == 0 {
                ScrollView {
                    LazyVGrid(columns: columns, spacing: 6) {
                        ForEach(builtInStickers) { sticker in
                            Button(action: { onSelect(sticker.id, sticker.id) }) {
                                VStack(spacing: 2) {
                                    Text(sticker.emoji)
                                        .font(.system(size: 28))
                                        .frame(width: 48, height: 48)
                                        .background(MiyaColors.surface)
                                        .clipShape(RoundedRectangle(cornerRadius: 10))
                                    Text(sticker.name)
                                        .font(.system(size: 9))
                                        .foregroundColor(MiyaColors.textSecondary)
                                }
                            }
                        }
                    }
                    .padding(12)
                }
            } else {
                VStack(spacing: 12) {
                    HStack {
                        Image(systemName: "magnifyingglass")
                            .foregroundColor(MiyaColors.textSecondary)
                        TextField("搜索表情...", text: $searchQuery)
                            .foregroundColor(MiyaColors.textPrimary)
                    }
                    .padding(.horizontal, 14)
                    .padding(.vertical, 10)
                    .background(
                        RoundedRectangle(cornerRadius: 12)
                            .fill(MiyaColors.background)
                    )
                    .padding(.horizontal, 16)
                    .padding(.top, 12)

                    if searchQuery.isEmpty {
                        VStack(spacing: 8) {
                            Text("🔍")
                                .font(.title)
                            Text("输入关键词搜索表情")
                                .foregroundColor(MiyaColors.textSecondary)
                            Text("支持 GIPHY 表情搜索")
                                .font(.caption)
                                .foregroundColor(MiyaColors.textDim)
                        }
                        .frame(maxHeight: .infinity)
                    } else {
                        Text("搜索 \"\(searchQuery)\" 中...")
                            .foregroundColor(MiyaColors.textSecondary)
                            .frame(maxHeight: .infinity)
                    }
                }
            }
        }
        .background(MiyaColors.background)
    }
}

// MARK: - 图片选择器桥接

struct ImagePicker: UIViewControllerRepresentable {
    var sourceType: UIImagePickerController.SourceType
    var onImagePicked: (UIImage?) -> Void

    func makeUIViewController(context: Context) -> UIImagePickerController {
        let picker = UIImagePickerController()
        picker.sourceType = sourceType
        picker.delegate = context.coordinator
        return picker
    }

    func updateUIViewController(_ uiViewController: UIImagePickerController, context: Context) {}

    func makeCoordinator() -> Coordinator {
        Coordinator(onImagePicked: onImagePicked)
    }

    class Coordinator: NSObject, UIImagePickerControllerDelegate, UINavigationControllerDelegate {
        let onImagePicked: (UIImage?) -> Void
        init(onImagePicked: @escaping (UIImage?) -> Void) { self.onImagePicked = onImagePicked }

        func imagePickerController(_ picker: UIImagePickerController, didFinishPickingMediaWithInfo info: [UIImagePickerController.InfoKey: Any]) {
            let image = info[.originalImage] as? UIImage
            onImagePicked(image)
        }

        func imagePickerControllerDidCancel(_ picker: UIImagePickerController) {
            onImagePicked(nil)
        }
    }
}

// MARK: - 预览

#Preview {
    ChatView()
        .environmentObject(AppState())
        .preferredColorScheme(.dark)
}
