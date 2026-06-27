package ai.miya.android.ui.live2d

import android.content.Context
import android.opengl.GLES30
import android.opengl.GLSurfaceView
import java.io.File
import javax.microedition.khronos.egl.EGLConfig
import javax.microedition.khronos.opengles.GL10

/**
 * Live2D OpenGL 渲染器
 *
 * 在集成 Cubism SDK 之前，使用占位 OpenGL 渲染（彩色光晕动画）
 * 集成后替换为 Cubism 原生渲染管线。
 */
class MiyaLive2DRenderer(
    private val context: Context,
    private val modelPath: String,
) : GLSurfaceView.Renderer {

    private var currentEmotion: String = "neutral"
    private var currentState: MiyaLive2DGLView.Live2DState = MiyaLive2DGLView.Live2DState.IDLE
    private var mouthOpenRatio: Float = 0f
    private var eyeTargetX: Float = 0f
    private var eyeTargetY: Float = 0f
    private var animationTime: Float = 0f

    // ── Cubism SDK 占位 — 集成后启用 ──
    // private var cubismModel: CubismModel? = null
    // private var cubismMatrix: CubismMatrix44? = null
    // private var motionManager: CubismMotionManager? = null
    // private var expressionManager: CubismExpressionManager? = null

    private val emotionColors = mapOf(
        "happy" to floatArrayOf(0.98f, 0.75f, 0.14f, 1.0f),
        "sad" to floatArrayOf(0.39f, 0.28f, 0.28f, 1.0f),
        "angry" to floatArrayOf(0.94f, 0.27f, 0.27f, 1.0f),
        "surprise" to floatArrayOf(0.02f, 0.71f, 0.83f, 1.0f),
        "neutral" to floatArrayOf(0.65f, 0.55f, 0.98f, 1.0f),
    )

    override fun onSurfaceCreated(gl: GL10?, config: EGLConfig?) {
        GLES30.glClearColor(0f, 0f, 0f, 0f)
        GLES30.glEnable(GLES30.GL_BLEND)
        GLES30.glBlendFunc(GLES30.GL_SRC_ALPHA, GLES30.GL_ONE_MINUS_SRC_ALPHA)

        // Cubism SDK 初始化（集成后启用）
        // CubismFramework.initialize()
        // cubismModel = loadCubismModel(modelPath)
    }

    override fun onSurfaceChanged(gl: GL10?, width: Int, height: Int) {
        GLES30.glViewport(0, 0, width, height)
        // Cubism: 更新投影矩阵
        // cubismMatrix?.setSize(width.toFloat(), height.toFloat())
    }

    override fun onDrawFrame(gl: GL10?) {
        animationTime += 0.016f

        GLES30.glClear(GLES30.GL_COLOR_BUFFER_BIT or GLES30.GL_DEPTH_BUFFER_BIT)

        // ── 占位渲染：彩色光晕 ──
        // 集成 Cubism SDK 后替换为：cubismModel.draw(cubismMatrix)
        drawPlaceholderGlow()

        // Cubism 渲染管线（集成后启用）：
        // CubismFramework.update()
        // cubismModel?.update()
        // motionManager?.updateMotion(cubismModel, deltaTime)
        // expressionManager?.updateMotion(cubismModel, deltaTime)
        // cubismModel?.setParameterValue("ParamMouthOpenY", mouthOpenRatio)
        // cubismModel?.setParameterValue("ParamEyeBallX", eyeTargetX)
        // cubismModel?.setParameterValue("ParamEyeBallY", eyeTargetY)
        // cubismModel?.draw(cubismMatrix)
    }

    private fun drawPlaceholderGlow() {
        val color = emotionColors[currentEmotion] ?: emotionColors["neutral"]!!

        val pulse = when (currentState) {
            MiyaLive2DGLView.Live2DState.TALKING -> 1.2f + kotlin.math.sin(animationTime * 8f) * 0.3f
            MiyaLive2DGLView.Live2DState.THINKING -> 1.0f + kotlin.math.sin(animationTime * 3f) * 0.1f
            MiyaLive2DGLView.Live2DState.IDLE -> 1.0f + kotlin.math.sin(animationTime * 1.5f) * 0.05f
        }

        val alpha = when (currentState) {
            MiyaLive2DGLView.Live2DState.TALKING -> 0.25f
            MiyaLive2DGLView.Live2DState.THINKING -> 0.18f
            MiyaLive2DGLView.Live2DState.IDLE -> 0.12f
        }

        GLES30.glClearColor(
            color[0] * 0.1f,
            color[1] * 0.1f,
            color[2] * 0.1f,
            alpha * pulse
        )
    }

    fun setEmotion(emotionKey: String) {
        currentEmotion = emotionKey
    }

    fun setState(state: MiyaLive2DGLView.Live2DState) {
        currentState = state
    }

    fun setMouthOpen(ratio: Float) {
        mouthOpenRatio = ratio.coerceIn(0f, 1f)
    }

    fun setEyeTracking(targetX: Float, targetY: Float) {
        eyeTargetX = targetX.coerceIn(-1f, 1f)
        eyeTargetY = targetY.coerceIn(-1f, 1f)
    }

    fun startRandomMotion() {
        // Cubism SDK: 随机播放 idle motion
        // motionManager?.startRandomMotion("idle", Random.nextInt(3))
    }
}
