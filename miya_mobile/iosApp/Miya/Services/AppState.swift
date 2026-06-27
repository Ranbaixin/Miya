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

    var color: String {
        switch self {
        case .happy, .joy: return "MiyaEmotionHappy"
        case .sad: return "MiyaEmotionSad"
        case .angry: return "MiyaEmotionAngry"
        case .surprise: return "MiyaEmotionSurprise"
        case .neutral: return "MiyaPrimary"
        }
    }

    init(from dominant: String) {
        let lower = dominant.lowercased()
        self = Self.allCases.first { $0.rawValue == dominant || $0.live2DKey == lower } ?? .neutral
    }
}

// MARK: - 数据模型

struct ChatMessage: Identifiable, Equatable {
    let id = UUID()
    let content: String
    let isMiya: Bool
    var isStreaming: Bool = false

    static func == (lhs: ChatMessage, rhs: ChatMessage) -> Bool {
        lhs.id == rhs.id
    }
}

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
