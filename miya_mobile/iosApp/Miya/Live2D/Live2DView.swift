import SwiftUI
import Foundation

// MARK: - Live2D 角色视图 (SwiftUI)

/// Live2D 渲染占位视图
///
/// 集成 Cubism SDK for Native (iOS) 后，替换为原生 Metal/OpenGL 渲染管线。
/// SDK 下载: https://www.live2d.com/download/cubism-sdk/
///
/// 模型资源位置: miya_frontend/public/models/弥娅/Miya/
/// 部署: 将模型文件夹拖入 Xcode → Build Phases → Copy Bundle Resources
struct Live2DCharacterView: View {
    let emotion: MiyaEmotion
    let state: Live2DState

    @State private var isBreathing = false
    @State private var breathScale: CGFloat = 1.0

    enum Live2DState {
        case idle
        case thinking
        case talking

        var animationDuration: Double {
            switch self {
            case .idle: return 3.0
            case .thinking: return 1.5
            case .talking: return 0.6
            }
        }
    }

    var body: some View {
        ZStack {
            // ── 外圈光晕 ──
            Circle()
                .fill(Color(emotion.color).opacity(0.15))
                .frame(width: 180 * breathScale, height: 180 * breathScale)
                .blur(radius: 20)

            // ── 第二层光晕 ──
            Circle()
                .fill(Color(emotion.color).opacity(0.08))
                .frame(width: 240 * breathScale, height: 240 * breathScale)
                .blur(radius: 30)

            // ── 角色占位 (集成 Cubism SDK 后替换为 L2DView) ──
            ZStack {
                // 头部
                Circle()
                    .fill(Color.white.opacity(0.1))
                    .frame(width: 100, height: 110)

                // 眼睛
                HStack(spacing: 24) {
                    eyeView
                    eyeView
                }
                .offset(y: -12)

                // 嘴巴
                mouthView
                    .offset(y: 20)
            }
            .scaleEffect(breathScale)

            // ── 情感标签 ──
            VStack {
                Spacer()
                    .frame(height: 160)

                Text("弥娅")
                    .font(.title2)
                    .fontWeight(.medium)
                    .foregroundColor(.white)

                Text(emotion.rawValue)
                    .font(.caption)
                    .foregroundColor(Color(emotion.color))
                    .padding(.horizontal, 12)
                    .padding(.vertical, 4)
                    .background(
                        Capsule()
                            .fill(Color(emotion.color).opacity(0.15))
                    )
            }
        }
        .onAppear { isBreathing = true }
        .onChange(of: state) { _, newState in
            withAnimation(
                .easeInOut(duration: newState.animationDuration)
                .repeatForever(autoreverses: true)
            ) {
                isBreathing = true
                breathScale = newState == .talking ? 1.08 : 1.04
            }
        }
    }

    // MARK: - 眼睛组件

    private var eyeView: some View {
        ZStack {
            // 眼眶
            Ellipse()
                .fill(Color.white.opacity(0.25))
                .frame(width: 18, height: 12)

            // 瞳孔
            Circle()
                .fill(Color(emotion.color))
                .frame(width: 8, height: 8)
                .offset(x: state == .thinking ? 3 : 0) // 思考时眼球偏离
        }
    }

    // MARK: - 嘴巴组件

    private var mouthView: some View {
        Group {
            switch state {
            case .idle:
                // 微笑
                Path { path in
                    path.move(to: CGPoint(x: -10, y: 0))
                    path.addQuadCurve(
                        to: CGPoint(x: 10, y: 0),
                        control: CGPoint(x: 0, y: 5)
                    )
                }
                .stroke(Color.white.opacity(0.5), lineWidth: 2)

            case .talking:
                // 张开的椭圆
                Ellipse()
                    .fill(Color.white.opacity(0.4))
                    .frame(width: 16, height: 10)

            case .thinking:
                // 抿嘴
                Path { path in
                    path.move(to: CGPoint(x: -8, y: 2))
                    path.addLine(to: CGPoint(x: 8, y: 2))
                }
                .stroke(Color.white.opacity(0.3), lineWidth: 2)
            }
        }
    }
}

// MARK: - Live2D + 聊天浮层 完整布局

struct Live2DChatLayout<Content: View>: View {
    let emotion: MiyaEmotion
    let state: Live2DCharacterView.Live2DState
    @ViewBuilder let chatContent: () -> Content

    var body: some View {
        ZStack {
            // Layer 1: Live2D 全屏角色
            Live2DCharacterView(emotion: emotion, state: state)
                .ignoresSafeArea()

            // Layer 2: 聊天浮层 (底部)
            VStack {
                Spacer()
                chatContent()
            }
        }
    }
}

// MARK: - Cubism SDK 集成后替换方案

#if false
/// Cubism SDK Native 封装 (集成后启用)
/// 
/// 集成步骤:
/// 1. 下载 Cubism SDK for Native (iOS)
/// 2. 将 Cubism.xcframework 拖入 Xcode
/// 3. 创建 Bridging-Header.h:
///    #import <CubismFramework/CubismFramework.hpp>
/// 4. 使用 MetalKit 渲染 Live2D 模型
struct CubismLive2DView: UIViewRepresentable {
    let modelName: String
    @Binding var emotion: String
    @Binding var state: Live2DState

    func makeUIView(context: Context) -> CubismMetalView {
        let view = CubismMetalView()
        view.loadModel(named: modelName)
        return view
    }

    func updateUIView(_ uiView: CubismMetalView, context: Context) {
        uiView.setEmotion(emotion)
        uiView.setState(state)
    }
}

final class CubismMetalView: MTKView {
    // 使用 Metal + Cubism SDK 渲染 Live2D 模型
    // ...
}
#endif

// MARK: - 预览

#Preview("Idle") {
    Live2DCharacterView(emotion: .happy, state: .idle)
        .background(MiyaColors.background)
}

#Preview("Talking") {
    Live2DCharacterView(emotion: .surprise, state: .talking)
        .background(MiyaColors.background)
}
