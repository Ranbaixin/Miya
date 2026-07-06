import SwiftUI

struct ConnectionSetupView: View {
    @Environment(\.colorScheme) var colorScheme
    @State private var host = ""
    @State private var port = "8000"
    @State private var isLoading = false
    @State private var errorMsg: String?

    var isDark: Bool { colorScheme == .dark }
    var onConnected: (String, Int) -> Void

    var body: some View {
        VStack(spacing: 0) {
            Spacer()

            ZStack {
                Circle()
                    .fill((isDark ? MiyaColors.primary : MiyaLightColors.primary).opacity(0.12))
                    .frame(width: 80, height: 80)
                Text("弥")
                    .font(.system(size: 36, weight: .bold))
                    .foregroundColor(isDark ? MiyaColors.primary : MiyaLightColors.primary)
            }

            Spacer().frame(height: 20)

            Text("弥娅")
                .font(.system(size: 26, weight: .bold))
                .foregroundColor(isDark ? MiyaColors.textPrimary : MiyaLightColors.textPrimary)

            Text("MIYA AI Companion")
                .font(.system(size: 13, design: .monospaced))
                .kerning(2)
                .foregroundColor(isDark ? MiyaColors.textSecondary : MiyaLightColors.textSecondary)

            Text("连接到运行在电脑上的弥娅服务")
                .font(.system(size: 13))
                .foregroundColor(isDark ? MiyaColors.textDim : MiyaLightColors.textDim)
                .padding(.top, 4)

            Spacer().frame(height: 40)

            VStack(spacing: 12) {
                TextField("服务器地址 (如 192.168.1.100)", text: $host)
                    .textFieldStyle(.plain)
                    .padding(12)
                    .background(isDark ? MiyaColors.surface : MiyaLightColors.surface)
                    .cornerRadius(12)
                    .overlay(
                        RoundedRectangle(cornerRadius: 12)
                            .stroke(isDark ? MiyaColors.borderDim : MiyaLightColors.borderDim, lineWidth: 1)
                    )
                    .foregroundColor(isDark ? MiyaColors.textPrimary : MiyaLightColors.textPrimary)
                    .keyboardType(.URL)
                    .autocapitalization(.none)

                TextField("端口", text: $port)
                    .textFieldStyle(.plain)
                    .padding(12)
                    .background(isDark ? MiyaColors.surface : MiyaLightColors.surface)
                    .cornerRadius(12)
                    .overlay(
                        RoundedRectangle(cornerRadius: 12)
                            .stroke(isDark ? MiyaColors.borderDim : MiyaLightColors.borderDim, lineWidth: 1)
                    )
                    .foregroundColor(isDark ? MiyaColors.textPrimary : MiyaLightColors.textPrimary)
                    .keyboardType(.numberPad)
            }
            .padding(.horizontal, 32)

            if let error = errorMsg {
                Text(error)
                    .font(.system(size: 12))
                    .foregroundColor(.red)
                    .padding(.top, 8)
            }

            Spacer().frame(height: 24)

            Button(action: connect) {
                if isLoading {
                    ProgressView()
                        .progressViewStyle(CircularProgressViewStyle(tint: .white))
                } else {
                    Text("连接弥娅")
                        .font(.system(size: 16, weight: .medium))
                        .foregroundColor(.white)
                }
            }
            .frame(maxWidth: .infinity)
            .frame(height: 48)
            .background(isDark ? MiyaColors.primary : MiyaLightColors.primary)
            .cornerRadius(12)
            .disabled(isLoading)
            .padding(.horizontal, 32)

            Spacer().frame(height: 12)

            Text("手机和电脑需在同一局域网\n或通过 frp/ngrok 远程访问")
                .font(.system(size: 11))
                .multilineTextAlignment(.center)
                .foregroundColor(isDark ? MiyaColors.textDim : MiyaLightColors.textDim)

            Spacer()
        }
        .background(isDark ? MiyaColors.background : MiyaLightColors.background)
        .ignoresSafeArea(.keyboard)
    }

    private func connect() {
        let trimmedHost = host.trimmingCharacters(in: .whitespaces)
        guard !trimmedHost.isEmpty else {
            errorMsg = "请输入服务器地址"; return
        }
        guard let portNum = Int(port.trimmingCharacters(in: .whitespaces)), (1...65535).contains(portNum) else {
            errorMsg = "请输入有效端口 (1-65535)"; return
        }
        isLoading = true
        UserDefaults.standard.set(trimmedHost, forKey: "server_host")
        UserDefaults.standard.set(portNum, forKey: "server_port")
        onConnected(trimmedHost, portNum)
    }
}
