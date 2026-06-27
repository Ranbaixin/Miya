import SwiftUI

// ═══════════════════════════════════════════════
// 弥娅角色展示页
// ═══════════════════════════════════════════════

struct MiyaCharacterView: View {
    @EnvironmentObject var appState: AppState
    @State private var glowAnim = false

    var emotionCol: Color {
        MiyaColors.emotionColor(for: appState.currentEmotion.rawValue)
    }

    var body: some View {
        VStack(spacing: 0) {
            Spacer()

            // Live2D 角色
            Live2DCharacterView(emotion: appState.currentEmotion, state: .idle)
                .frame(maxHeight: UIScreen.main.bounds.height * 0.5)

            // 信息面板
            VStack(spacing: 12) {
                Text("弥娅")
                    .font(.title)
                    .fontWeight(.bold)
                    .foregroundColor(MiyaColors.textPrimary)

                Text(appState.currentEmotion.rawValue)
                    .font(.subheadline)
                    .foregroundColor(emotionCol)
                    .padding(.horizontal, 20)
                    .padding(.vertical, 6)
                    .background(
                        Capsule()
                            .fill(emotionCol.opacity(0.15))
                    )

                Text(appState.isConnected ? "已连接" : "未连接")
                    .font(.caption)
                    .foregroundColor(appState.isConnected ? MiyaColors.emotionCalm : MiyaColors.emotionAnger)
            }

            Spacer()
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(MiyaColors.background)
        .onAppear {
            withAnimation(.easeInOut(duration: 2).repeatForever(autoreverses: true)) {
                glowAnim = true
            }
        }
    }
}

#Preview {
    MiyaCharacterView()
        .environmentObject(AppState())
        .preferredColorScheme(.dark)
}
