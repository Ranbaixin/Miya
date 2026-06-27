package ai.miya.android.ui.live2d

import android.content.Context
import android.graphics.Color
import android.opengl.GLSurfaceView
import android.util.AttributeSet
import android.util.Log

/**
 * Live2D 渲染视图 — 先试 Cubism, 失败则降级到占位渲染
 */
class MiyaLive2DGLView @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
) : GLSurfaceView(context, attrs) {

    companion object {
        private const val TAG = "MiyaLive2DGL"
    }

    private var placeholderRenderer: MiyaLive2DRenderer? = null
    private var cubismRenderer: MiyaCubismRenderer? = null
    private var cubismAvailable: Boolean = false
    private var cubismTried: Boolean = false

    init {
        setEGLContextClientVersion(2)
        setBackgroundColor(Color.TRANSPARENT)
        holder.setFormat(android.graphics.PixelFormat.TRANSLUCENT)

        cubismAvailable = tryLoadCubism()
        Log.i(TAG, "Cubism SDK: $cubismAvailable")
    }

    private fun tryLoadCubism(): Boolean {
        return try {
            Class.forName("com.live2d.sdk.cubism.framework.CubismFramework")
            true
        } catch (_: ClassNotFoundException) {
            false
        }
    }

    fun loadModel() {
        // TODO: 启用 Cubism 后改为 loadCubismModel()
        // 当前使用占位渲染确保可见，Cubism SDK 需 adb logcat 调试
        loadPlaceholder()
    }

    private fun loadCubismModel() {
        try {
            val r = MiyaCubismRenderer(context.assets)
            cubismRenderer = r
            setRenderer(r)
            renderMode = RENDERMODE_CONTINUOUSLY
            Log.i(TAG, "Cubism renderer active")
        } catch (e: Exception) {
            Log.e(TAG, "Cubism failed, fallback: ${e.message}", e)
            cubismAvailable = false
            loadPlaceholder()
        }
    }

    private fun loadPlaceholder() {
        val r = MiyaLive2DRenderer(context, "models/miya-model/01.model3.json")
        placeholderRenderer = r
        setRenderer(r)
        renderMode = RENDERMODE_CONTINUOUSLY
        Log.i(TAG, "Placeholder active")
    }

    fun setEmotion(emotionKey: String) {
        cubismRenderer?.setEmotion(emotionKey)
        placeholderRenderer?.setEmotion(emotionKey)
    }

    fun setState(state: Live2DState) {
        cubismRenderer?.setState(state)
        placeholderRenderer?.setState(state)
    }

    fun setMouthOpen(ratio: Float) {
        cubismRenderer?.setMouthOpen(ratio)
        placeholderRenderer?.setMouthOpen(ratio)
    }

    fun setEyeTracking(targetX: Float, targetY: Float) {
        cubismRenderer?.setEyeTracking(targetX, targetY)
        placeholderRenderer?.setEyeTracking(targetX, targetY)
    }

    enum class Live2DState {
        IDLE, THINKING, TALKING
    }
}
