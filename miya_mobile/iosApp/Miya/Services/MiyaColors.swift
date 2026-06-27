import SwiftUI

// ═══════════════════════════════════════════════
// 弥娅 PGR 战双帕米什风格配色 (与 Android/前端统一)
// ═══════════════════════════════════════════════

struct MiyaColors {
    // 核心
    static let background = Color(hex: "222831")
    static let surface = Color(hex: "393E46").opacity(0.85)
    static let surfaceVariant = Color(hex: "393E46")
    static let surfaceDeep = Color(hex: "08101C").opacity(0.92)

    // 主色
    static let primary = Color(hex: "00ADB5")
    static let accent = Color(hex: "00FFF5")
    static let glow = Color(hex: "00ADB5").opacity(0.30)
    static let gold = Color(hex: "00FFF5").opacity(0.35)

    // 文本
    static let textPrimary = Color(hex: "E4ECF0")
    static let textSecondary = Color(hex: "E4ECF0").opacity(0.45)
    static let textDim = Color(hex: "E4ECF0").opacity(0.30)

    // 边框
    static let border = Color(hex: "00ADB5")
    static let borderDim = Color(hex: "00ADB5").opacity(0.20)

    // 气泡
    static let chatAI = Color(hex: "00FFF5")
    static let chatUser = Color(hex: "00ADB5")
    static let chatBg = Color(hex: "222831")

    // 情绪色 (17 种)
    static let emotionJoy = Color(hex: "FFD700")
    static let emotionSadness = Color(hex: "7DD3FC")
    static let emotionAnger = Color(hex: "EF4444")
    static let emotionFear = Color(hex: "B44DFF")
    static let emotionLove = Color(hex: "FF6B9D")
    static let emotionSurprise = Color(hex: "FBBF24")
    static let emotionNeutral = Color(hex: "94A3B8")
    static let emotionWarm = Color(hex: "FF8C69")
    static let emotionCalm = Color(hex: "67E8F9")
    static let emotionSweet = Color(hex: "F472B6")
    static let emotionNostalgic = Color(hex: "D8B4FE")
    static let emotionShy = Color(hex: "FBCFE8")
    static let emotionAnticipation = Color(hex: "FACC15")
    static let emotionAttachment = Color(hex: "C084FC")
    static let emotionMoved = Color(hex: "C4B5FD")
    static let emotionTender = Color(hex: "A5B4FC")
    static let emotionCurious = Color(hex: "67E8F9")

    static func emotionColor(for name: String) -> Color {
        switch name.lowercased() {
        case "joy", "happy": return emotionJoy
        case "sadness", "sad": return emotionSadness
        case "anger", "angry": return emotionAnger
        case "fear": return emotionFear
        case "love": return emotionLove
        case "surprise": return emotionSurprise
        case "neutral": return emotionNeutral
        case "warm": return emotionWarm
        case "calm": return emotionCalm
        case "sweet": return emotionSweet
        case "nostalgic": return emotionNostalgic
        case "shy": return emotionShy
        case "anticipation": return emotionAnticipation
        case "attachment": return emotionAttachment
        case "moved": return emotionMoved
        case "tender": return emotionTender
        case "curious": return emotionCurious
        default: return primary
        }
    }
}

extension Color {
    init(hex: String) {
        let hex = hex.trimmingCharacters(in: CharacterSet.alphanumerics.inverted)
        var int: UInt64 = 0
        Scanner(string: hex).scanHexInt64(&int)
        let a, r, g, b: UInt64
        switch hex.count {
        case 6:
            (a, r, g, b) = (255, (int >> 16) & 0xFF, (int >> 8) & 0xFF, int & 0xFF)
        case 8:
            (a, r, g, b) = ((int >> 24) & 0xFF, (int >> 16) & 0xFF, (int >> 8) & 0xFF, int & 0xFF)
        default:
            (a, r, g, b) = (255, 0, 0, 0)
        }
        self.init(
            .sRGB,
            red: Double(r) / 255,
            green: Double(g) / 255,
            blue: Double(b) / 255,
            opacity: Double(a) / 255
        )
    }
}

// ═══════════════════════════════════════════════
// PGR 风格形状
// ═══════════════════════════════════════════════

struct PGRClipShape: Shape {
    let clip: CGFloat

    init(clip: CGFloat = 8) { self.clip = clip }

    func path(in rect: CGRect) -> Path {
        var path = Path()
        let w = rect.width
        let h = rect.height
        path.move(to: CGPoint(x: 0, y: clip))
        path.addLine(to: CGPoint(x: clip, y: 0))
        path.addLine(to: CGPoint(x: w, y: 0))
        path.addLine(to: CGPoint(x: w, y: h - clip))
        path.addLine(to: CGPoint(x: w - clip, y: h))
        path.addLine(to: CGPoint(x: clip, y: h))
        path.addLine(to: CGPoint(x: 0, y: h - clip))
        path.closeSubpath()
        return path
    }
}
