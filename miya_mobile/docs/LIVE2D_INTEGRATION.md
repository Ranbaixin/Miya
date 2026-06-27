# Live2D Cubism SDK 集成指南

## 概述

弥娅手机APP 当前使用占位渲染（彩色光晕 + SF Symbol / Vector Drawable）。
接入 Live2D Cubism SDK 后，将渲染真正的弥娅 Live2D 角色。

## 模型资源

```
miya_frontend/public/models/弥娅/Miya/
├── 01.model3.json      ← 模型描述文件 (入口)
├── 01.moc3             ← 模型二进制数据
├── 01.physics3.json    ← 物理模拟
├── 01.cdi3.json        ← 碰撞检测
├── 01.vtube.json       ← VTube Studio 配置
├── 11.exp3.json        ← 表情 1
├── 22.exp3.json        ← 表情 2
└── 01.8192/            ← 纹理贴图目录
    └── ...
```

## 步骤

### 1. 获取 Cubism SDK

从 Live2D 官网下载 SDK（需注册并同意许可协议）：

- **Cubism SDK for Java** (Android)
  - https://www.live2d.com/download/cubism-sdk/download-native/
  - 选择 "Cubism SDK for Java"
  
- **Cubism SDK for Native** (iOS)
  - https://www.live2d.com/download/cubism-sdk/download-native/
  - 选择 "Cubism SDK for Native"

### 2. Android 集成

#### 2.1 导入 SDK

```bash
# 解压下载的 SDK
# 将 Live2D_SDK_Java_xxx/ 目录下的 .aar 放入:
miya_mobile/androidApp/libs/Live2D_SDK_Java.aar
```

#### 2.2 修改 build.gradle.kts

```kotlin
// androidApp/build.gradle.kts
dependencies {
    implementation(files("libs/Live2D_SDK_Java.aar"))
    // ...
}
```

#### 2.3 部署模型资源

```bash
# 模型文件已自动部署到:
androidApp/src/main/assets/models/miya-model/
# 入口文件: 01.model3.json
```

#### 2.4 启用 Cubism 渲染

在 `MiyaLive2DRenderer.kt` 中取消注释 Cubism SDK 相关代码块，
替换 `drawPlaceholderGlow()` 为 Cubism 渲染管线。

关键 API：

```kotlin
// 初始化
CubismFramework.initialize()

// 加载模型
val model = CubismNativeModel("models/弥娅/Miya")
model.loadModel()       // 读取 .model3.json
model.createRenderer()  // 创建 GL 渲染器

// 每帧渲染
model.update(deltaTime)
model.draw(cubismMatrix)

// 表情控制
model.setExpression("happy")  // 加载 .exp3.json
model.setParameterValue("ParamMouthOpenY", 0.6f)
model.setParameterValue("ParamEyeBallX", 0.2f)
model.setParameterValue("ParamEyeBallY", 0.1f)

// 动作
motionManager.startMotion("idle_01", priority = 2)
```

### 3. iOS 集成

#### 3.1 导入 SDK

将 SDK 中的 `Cubism.xcframework` 拖入 Xcode 项目：

```
iosApp/
├── Frameworks/
│   └── Cubism.xcframework/
```

在 Xcode → Target → General → Frameworks, Libraries, and Embedded Content 中
添加 `Cubism.xcframework`，设为 "Embed & Sign"。

#### 3.2 配置 Bridging Header

创建 `iosApp/Miya/Miya-Bridging-Header.h`：

```objc
#import <CubismFramework/CubismFramework.hpp>
```

在 Xcode → Build Settings → Swift Compiler - General → Objective-C Bridging Header 中设置路径为 `Miya/Miya-Bridging-Header.h`。

#### 3.3 部署模型资源

将 `miya_frontend/public/models/弥娅/Miya/` 文件夹拖入 Xcode 项目，
确保在 Build Phases → Copy Bundle Resources 中。

#### 3.4 启用 Cubism 渲染

在 `Live2D/Live2DView.swift` 中取消注释 `CubismLive2DView` 代码，
实现 `CubismMetalView` 使用 Metal + Cubism SDK 渲染管线。

### 4. 表情映射

弥娅模型的表情 (.exp3.json) 与情感状态的对应关系：

| 情感 | 表情文件 | Live2D Key |
|------|---------|------------|
| 开心 | 11.exp3.json (推测) | happy |
| 喜悦 | 11.exp3.json | happy |
| 悲伤 | 22.exp3.json (推测) | sad |
| 愤怒 | 自定义参数 | angry |
| 惊讶 | 自定义参数 | surprise |
| 平静 | 默认 | neutral |

> **注意**：实际表情文件名称可能不同，需要检查 `.exp3.json` 文件内容确认。
> 可以通过 `CubismViewer` 或 Live2D Cubism Editor 查看模型结构。

### 5. 眼球追踪

手机端支持触摸点追踪（手指触摸屏幕位置映射到眼球方向）：

- Android: 监听 `onTouchEvent` → 转换为模型坐标 → `ParamEyeBallX/Y`
- iOS: 监听手势 → `DragGesture` → 转换坐标 → 更新模型参数

当前代码中 `setEyeTracking(x, y)` 已预留接口。

### 6. 口型同步

TTS 输出时驱动口型动画：
- 从音频流获取音量包络
- 映射到 `ParamMouthOpenY` (0.0 - 1.0)
- 已在 `MiyaLive2DRenderer.setMouthOpen()` 预留接口

## 注意事项

1. **许可协议**：Cubism SDK 有特定的许可条款，发布应用前请确认合规。
2. **模型版权**：确保拥有弥娅 Live2D 模型的使用权。
3. **性能**：手机端渲染 Live2D 对 GPU 有一定要求，建议在低端机型上降低纹理分辨率。
4. **内存**：模型文件约 2-5MB，加载后在内存中占用 10-30MB。
