package ai.miya.android.ui.live2d

import android.content.Context
import android.graphics.Color
import android.opengl.GLSurfaceView
import android.util.AttributeSet

/**
 * Live2D 渲染视图 (OpenGL ES Surface)
 *
 * 依赖: Cubism SDK for Java
 * 1. 从 Live2D 官网下载 SDK: https://www.live2d.com/download/cubism-sdk/
 * 2. 将 Live2D_SDK_Java/ 下的 .aar 放到 androidApp/libs/
 * 3. 在 build.gradle.kts 添加: implementation(files("libs/Live2D_SDK_Java_xxx.aar"))
 */
class MiyaLive2DGLView @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
) : GLSurfaceView(context, attrs) {

    private var renderer: MiyaLive2DRenderer? = null
    private var currentModelPath: String = ""

    init {
        setEGLContextClientVersion(3)
        setBackgroundColor(Color.TRANSPARENT)
        holder.setFormat(android.graphics.PixelFormat.TRANSLUCENT)
    }

    fun loadModel(modelPath: String) {
        currentModelPath = modelPath
        val r = MiyaLive2DRenderer(context, modelPath)
        renderer = r
        setRenderer(r)
        renderMode = RENDERMODE_CONTINUOUSLY
    }

    fun setEmotion(emotionKey: String) {
        renderer?.setEmotion(emotionKey)
    }

    fun setState(state: Live2DState) {
        renderer?.setState(state)
    }

    fun setMouthOpen(ratio: Float) {
        renderer?.setMouthOpen(ratio)
    }

    fun setEyeTracking(targetX: Float, targetY: Float) {
        renderer?.setEyeTracking(targetX, targetY)
    }

    fun startRandomMotion() {
        renderer?.startRandomMotion()
    }

    enum class Live2DState {
        IDLE, THINKING, TALKING
    }
}
