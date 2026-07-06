import SwiftUI

// 弥娅亮色配色
struct MiyaLightColors {
    static let background = Color(hex: "F0F2F5")
    static let surface = Color(hex: "FFFFFF")
    static let surfaceVariant = Color(hex: "F7F8FA")
    static let textPrimary = Color(hex: "1A1D23")
    static let textSecondary = Color(hex: "6B7280")
    static let textDim = Color(hex: "9CA3AF")
    static let border = Color(hex: "E5E7EB")
    static let borderDim = Color(hex: "D1D5DB")
    static let primary = Color(hex: "00838F")
    static let accent = Color(hex: "00ACC1")
    static let bubbleMe = Color(hex: "00838F")
    static let bubbleMiya = Color.white
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
