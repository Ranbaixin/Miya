import Foundation
import Combine

// MARK: - App 全局状态

class AppState: ObservableObject {
    @Published var isConnected = false
    @Published var currentEmotion: MiyaEmotion = .neutral
    @Published var currentPersona = "default"
    @Published var connectionMode: ConnectionMode = .lan
    @Published var baseURL = "http://localhost:9800"

    let apiService = MiyaAPIService()

    enum ConnectionMode {
        case lan, remote
    }

    func updateConnection(host: String, port: Int) {
        baseURL = "http://\(host):\(port)"
        apiService.updateBaseURL(baseURL)
        checkConnection()
    }

    func checkConnection() {
        Task {
            isConnected = await apiService.healthCheck()
        }
    }
}

// MARK: - 情感枚举

enum MiyaEmotion: String, CaseIterable {
    case happy = "开心"
    case sad = "悲伤"
    case angry = "愤怒"
    case surprise = "惊讶"
    case neutral = "平静"
    case joy = "喜悦"

    var live2DKey: String {
        switch self {
        case .happy, .joy: return "happy"
        case .sad: return "sad"
        case .angry: return "angry"
        case .surprise: return "surprise"
        case .neutral: return "neutral"
        }
    }

    var color: Color {
        switch self {
        case .happy, .joy: return MiyaColors.emotionJoy
        case .sad: return MiyaColors.emotionSadness
        case .angry: return MiyaColors.emotionAnger
        case .surprise: return MiyaColors.emotionSurprise
        case .neutral: return MiyaColors.primary
        }
    }

    init(from dominant: String) {
        let lower = dominant.lowercased()
        self = Self.allCases.first { $0.rawValue == dominant || $0.live2DKey == lower } ?? .neutral
    }
}

// MARK: - 消息内容类型

enum MessageContentType: String, Codable {
    case text = "text"
    case image = "image"
    case sticker = "sticker"
    case voice = "voice"
    case file = "file"
    case system = "system"
}

struct QuotePayload: Codable, Equatable {
    let messageId: String?
    let content: String
    let sender: String?

    enum CodingKeys: String, CodingKey {
        case messageId = "message_id"
        case content, sender
    }
}

struct ImagePayload: Codable, Equatable {
    let url: String
    let thumbnailUrl: String?
    let width: Int
    let height: Int
    let fileSize: Int64

    enum CodingKeys: String, CodingKey {
        case url
        case thumbnailUrl = "thumbnail_url"
        case width, height
        case fileSize = "file_size"
    }
}

struct StickerPayload: Codable, Equatable {
    let stickerId: String
    let url: String
    let category: String?
    let isExternal: Bool

    enum CodingKeys: String, CodingKey {
        case stickerId = "sticker_id"
        case url, category
        case isExternal = "is_external"
    }
}

struct VoicePayload: Codable, Equatable {
    let url: String
    let duration: Int
    let fileSize: Int64

    enum CodingKeys: String, CodingKey {
        case url, duration
        case fileSize = "file_size"
    }
}

// MARK: - 消息模型

struct ChatMessage: Identifiable, Equatable {
    let id = UUID()
    var contentType: MessageContentType = .text
    var content: String = ""
    var isMiya: Bool = false
    var isStreaming: Bool = false
    var emotion: String? = nil
    var imageUrl: String? = nil
    var thumbnailUrl: String? = nil
    var stickerId: String? = nil
    var stickerUrl: String? = nil
    var voiceUrl: String? = nil
    var voiceDuration: Int = 0
    var quoteContent: String? = nil
    var quoteSender: String? = nil
    var timestamp: Date = Date()

    static func == (lhs: ChatMessage, rhs: ChatMessage) -> Bool {
        lhs.id == rhs.id
    }
}

// MARK: - 表情贴纸数据

struct MiyaSticker: Identifiable {
    let id: String
    let emoji: String
    let name: String
    let category: String
}

let builtInStickers: [MiyaSticker] = [
    MiyaSticker(id: "miya_smile", emoji: "😊", name: "开心", category: "基础"),
    MiyaSticker(id: "miya_laugh", emoji: "😄", name: "大笑", category: "基础"),
    MiyaSticker(id: "miya_love", emoji: "😍", name: "喜欢", category: "基础"),
    MiyaSticker(id: "miya_wink", emoji: "😉", name: "眨眼", category: "基础"),
    MiyaSticker(id: "miya_kiss", emoji: "😘", name: "亲亲", category: "基础"),
    MiyaSticker(id: "miya_shy", emoji: "😳", name: "害羞", category: "基础"),
    MiyaSticker(id: "miya_cry", emoji: "😢", name: "哭泣", category: "基础"),
    MiyaSticker(id: "miya_angry", emoji: "😠", name: "生气", category: "基础"),
    MiyaSticker(id: "miya_surprise", emoji: "😲", name: "惊讶", category: "基础"),
    MiyaSticker(id: "miya_cool", emoji: "😎", name: "酷", category: "基础"),
    MiyaSticker(id: "miya_sleep", emoji: "😴", name: "困了", category: "基础"),
    MiyaSticker(id: "miya_think", emoji: "🤔", name: "思考", category: "基础"),
    MiyaSticker(id: "miya_clap", emoji: "👏", name: "鼓掌", category: "基础"),
    MiyaSticker(id: "miya_ok", emoji: "👌", name: "OK", category: "基础"),
    MiyaSticker(id: "miya_hug", emoji: "🫂", name: "抱抱", category: "基础"),
    MiyaSticker(id: "miya_heart", emoji: "💙", name: "爱心", category: "弥娅"),
    MiyaSticker(id: "miya_sparkle", emoji: "✨", name: "闪耀", category: "弥娅"),
    MiyaSticker(id: "miya_hello", emoji: "👋", name: "你好", category: "弥娅"),
    MiyaSticker(id: "miya_night", emoji: "🌙", name: "晚安", category: "弥娅"),
    MiyaSticker(id: "miya_morning", emoji: "🌅", name: "早安", category: "弥娅"),
    MiyaSticker(id: "miya_coffee", emoji: "☕", name: "咖啡", category: "弥娅"),
    MiyaSticker(id: "miya_star", emoji: "⭐", name: "星星", category: "弥娅"),
    MiyaSticker(id: "miya_pray", emoji: "🙏", name: "拜托", category: "弥娅"),
    MiyaSticker(id: "miya_facepalm", emoji: "🤦", name: "捂脸", category: "动作"),
    MiyaSticker(id: "miya_roll", emoji: "🙄", name: "白眼", category: "动作"),
    MiyaSticker(id: "miya_sweat", emoji: "😅", name: "尴尬", category: "动作"),
    MiyaSticker(id: "miya_party", emoji: "🎉", name: "庆祝", category: "动作"),
    MiyaSticker(id: "miya_flex", emoji: "💪", name: "加油", category: "动作"),
    MiyaSticker(id: "miya_please", emoji: "🥺", name: "求求", category: "动作"),
]

// MARK: - 连接数据模型

struct MiyaSession: Identifiable, Codable {
    let id: String
    var name: String?
    let createdAt: String?
    let updatedAt: String?
    let messageCount: Int?

    enum CodingKeys: String, CodingKey {
        case id
        case name
        case createdAt = "created_at"
        case updatedAt = "updated_at"
        case messageCount = "message_count"
    }
}

struct MiyaPersona: Identifiable, Codable {
    let id: String
    let name: String
    let active: Bool
    let displayName: String?

    enum CodingKeys: String, CodingKey {
        case id, name, active
        case displayName = "display_name"
    }
}

struct MemoryItem: Identifiable, Codable {
    let id: String
    let content: String
    let level: String
    let tags: [String]?
    let priority: Double?
    let createdAt: String?

    enum CodingKeys: String, CodingKey {
        case id, content, level, tags, priority
        case createdAt = "created_at"
    }
}

struct SystemStatusInfo: Codable {
    let status: String?
    let version: String?
    let uptime: String?
    let running: Bool
    let personality: String?
    let name: String?
    let platforms: Int?
    let platformsActive: Int?
    let providersLoaded: Int?

    enum CodingKeys: String, CodingKey {
        case status, version, uptime, running, personality, name, platforms
        case platformsActive = "platforms_active"
        case providersLoaded = "providers_loaded"
    }
}

struct MemoryStatsInfo: Codable {
    let nodeCount: Int
    let edgeCount: Int
    let dialogue: Int
    let shortTerm: Int
    let longTerm: Int
    let semantic: Int
    let knowledge: Int
    let pinned: Int
    let total: Int

    enum CodingKeys: String, CodingKey {
        case nodeCount, edgeCount, dialogue
        case shortTerm = "short_term"
        case longTerm = "long_term"
        case semantic, knowledge, pinned, total
    }
}

struct EmotionData: Codable {
    let dominant: String
    let intensity: Int
    let emotions: [EmotionItemData]?
    let innerThought: String?

    enum CodingKeys: String, CodingKey {
        case dominant, intensity, emotions
        case innerThought = "inner_thought"
    }
}

struct EmotionItemData: Codable {
    let name: String
    let intensity: Int
}
