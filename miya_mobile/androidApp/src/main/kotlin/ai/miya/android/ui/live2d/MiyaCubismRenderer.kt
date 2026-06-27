package ai.miya.android.ui.live2d

import android.content.res.AssetManager
import android.graphics.BitmapFactory
import android.opengl.GLES20
import android.opengl.GLSurfaceView
import android.opengl.GLUtils
import android.util.Log
import com.live2d.sdk.cubism.framework.CubismFramework
import com.live2d.sdk.cubism.framework.CubismModelSettingJson
import com.live2d.sdk.cubism.framework.effect.CubismBreath
import com.live2d.sdk.cubism.framework.effect.CubismEyeBlink
import com.live2d.sdk.cubism.framework.math.CubismMatrix44
import com.live2d.sdk.cubism.framework.math.CubismModelMatrix
import com.live2d.sdk.cubism.framework.math.CubismViewMatrix
import com.live2d.sdk.cubism.framework.model.CubismMoc
import com.live2d.sdk.cubism.framework.model.CubismModel
import com.live2d.sdk.cubism.framework.model.CubismUserModel
import com.live2d.sdk.cubism.framework.motion.CubismExpressionMotion
import com.live2d.sdk.cubism.framework.motion.CubismExpressionMotionManager
import com.live2d.sdk.cubism.framework.motion.CubismMotion
import com.live2d.sdk.cubism.framework.motion.CubismMotionManager
import com.live2d.sdk.cubism.framework.rendering.android.CubismRendererAndroid
import javax.microedition.khronos.egl.EGLConfig
import javax.microedition.khronos.opengles.GL10

class MiyaCubismRenderer(
    private val assetManager: AssetManager,
) : GLSurfaceView.Renderer {

    companion object {
        private const val TAG = "MiyaCubism"
        private const val MODEL_DIR = "models/miya-model/"
        private const val MODEL_JSON = "01.model3.json"
    }

    // ── Cubism 对象 ──
    private var model: MiyaCubismModel? = null
    private var modelSetting: CubismModelSettingJson? = null
    private var renderer: CubismRendererAndroid? = null
    private var eyeBlink: CubismEyeBlink? = null
    private var breath: CubismBreath? = null
    private val expressionManager = CubismExpressionMotionManager()
    private val motionManager = CubismMotionManager()

    // 矩阵
    private var modelMatrix: CubismModelMatrix? = null
    private val viewMatrix = CubismViewMatrix()
    private val deviceToScreen = CubismMatrix44.create()

    private var surfaceWidth: Int = 0
    private var surfaceHeight: Int = 0
    private var modelLoaded: Boolean = false

    // 纹理
    private val textureIds = mutableListOf<Int>()

    // 状态
    private var currentEmotion: String = "neutral"
    private var mouthOpenRatio: Float = 0f
    private var eyeTargetX: Float = 0f
    private var eyeTargetY: Float = 0f
    private var deltaTimeSeconds: Float = 0f
    private var lastFrameTime: Long = 0L

    enum class Live2DState { IDLE, THINKING, TALKING }

    // ─── 模型加载 ─────────────────────────────────────

    fun loadModel() {
        try {
            val assets = assetManager

            // 1. 读取 .model3.json
            val modelPath = MODEL_DIR + MODEL_JSON
            val jsonStr = assets.open(modelPath).bufferedReader().use { it.readText() }
            modelSetting = CubismModelSettingJson(jsonStr.toByteArray(Charsets.UTF_8))

            // 2. 读取 .moc3
            val mocFileName = modelSetting!!.getModelFileName()
            val mocBytes = assets.open(MODEL_DIR + mocFileName).readBytes()

            // 3. 创建模型
            model = MiyaCubismModel()
            model!!.loadModel(mocBytes)

            // 4. 加载纹理
            loadTextures(assets, modelSetting!!)

            // 5. 创建渲染器
            val r = CubismRendererAndroid.create(1, 1)
            renderer = r as CubismRendererAndroid
            model!!.setupRenderer(r)
            renderer!!.initialize(model!!.getModel())

            // 6. 加载物理
            tryLoadPhysics(assets)

            // 7. 加载表情
            tryLoadExpressions(assets)

            // 8. 自动效果
            eyeBlink = CubismEyeBlink.create()
            breath = CubismBreath.create()

            // 9. 模型矩阵
            modelMatrix = CubismModelMatrix.create(2.0f, 2.0f)

            modelLoaded = true
            Log.i(TAG, "弥娅 Live2D 模型加载完毕")
        } catch (e: Exception) {
            Log.e(TAG, "模型加载失败: ${e.message}", e)
            modelLoaded = false
        }
    }

    // ─── 纹理 ──────────────────────────────────────────

    private fun loadTextures(assets: AssetManager, setting: CubismModelSettingJson) {
        val count = setting.getTextureCount()
        for (i in 0 until count) {
            val texFile = setting.getTextureFileName(i)
            val stream = assets.open(MODEL_DIR + texFile)
            val bitmap = BitmapFactory.decodeStream(stream)
            stream.close()

            val id = createGLTexture(bitmap)
            textureIds.add(id)
            renderer?.bindTexture(i, id)
            bitmap.recycle()
        }
    }

    private fun createGLTexture(bitmap: android.graphics.Bitmap): Int {
        val ids = IntArray(1)
        GLES20.glGenTextures(1, ids, 0)
        GLES20.glBindTexture(GLES20.GL_TEXTURE_2D, ids[0])
        GLES20.glTexParameteri(GLES20.GL_TEXTURE_2D, GLES20.GL_TEXTURE_MIN_FILTER, GLES20.GL_LINEAR_MIPMAP_LINEAR)
        GLES20.glTexParameteri(GLES20.GL_TEXTURE_2D, GLES20.GL_TEXTURE_MAG_FILTER, GLES20.GL_LINEAR)
        GLES20.glTexParameteri(GLES20.GL_TEXTURE_2D, GLES20.GL_TEXTURE_WRAP_S, GLES20.GL_CLAMP_TO_EDGE)
        GLES20.glTexParameteri(GLES20.GL_TEXTURE_2D, GLES20.GL_TEXTURE_WRAP_T, GLES20.GL_CLAMP_TO_EDGE)
        GLUtils.texImage2D(GLES20.GL_TEXTURE_2D, 0, bitmap, 0)
        GLES20.glGenerateMipmap(GLES20.GL_TEXTURE_2D)
        return ids[0]
    }

    // ─── 物理 / 表情 ───────────────────────────────────

    private fun tryLoadPhysics(assets: AssetManager) {
        try {
            val path = MODEL_DIR + MODEL_JSON.replace(".model3.json", ".physics3.json")
            val bytes = assets.open(path).readBytes()
            model?.loadPhysics(bytes)
        } catch (_: Exception) { }
    }

    private fun tryLoadExpressions(assets: AssetManager) {
        val count = modelSetting?.getExpressionCount() ?: 0
        for (i in 0 until count) {
            try {
                val name = modelSetting!!.getExpressionName(i)
                val file = modelSetting!!.getExpressionFileName(i)
                val bytes = assets.open(MODEL_DIR + file).readBytes()
                val motion = model?.loadExpression(bytes) ?: continue
                expressionManager.startMotionPriority(motion, 0)
            } catch (_: Exception) { }
        }
    }

    // ─── OpenGL 生命周期 ─────────────────────────────

    override fun onSurfaceCreated(gl: GL10?, config: EGLConfig?) {
        GLES20.glEnable(GLES20.GL_BLEND)
        GLES20.glBlendFunc(GLES20.GL_SRC_ALPHA, GLES20.GL_ONE_MINUS_SRC_ALPHA)
        lastFrameTime = System.nanoTime()

        initCubism()
        loadModel()
    }

    private fun initCubism() {
        if (CubismFramework.isStarted()) return
        try {
            val option = CubismFramework.Option()
            CubismFramework.startUp(option)
            CubismFramework.initialize()
            Log.i(TAG, "CubismFramework initialized")
        } catch (e: Exception) {
            Log.e(TAG, "CubismFramework init failed: ${e.message}", e)
        }
    }

    override fun onSurfaceChanged(gl: GL10?, width: Int, height: Int) {
        surfaceWidth = width
        surfaceHeight = height
        GLES20.glViewport(0, 0, width, height)

        val ratio = width.toFloat() / height.toFloat()
        viewMatrix.setScreenRect(-ratio, ratio, -1f, 1f)
        viewMatrix.setMaxScale(2.0f)
        viewMatrix.setMinScale(0.5f)
        viewMatrix.setMaxScreenRect(-2f, 2f, -1f, 1f)

        model?.setRenderTargetSize(width, height)
    }

    override fun onDrawFrame(gl: GL10?) {
        val now = System.nanoTime()
        deltaTimeSeconds = (now - lastFrameTime) / 1_000_000_000f.coerceAtLeast(1f)
        lastFrameTime = now

        GLES20.glClear(GLES20.GL_COLOR_BUFFER_BIT or GLES20.GL_DEPTH_BUFFER_BIT)

        if (modelLoaded && model != null && renderer != null) {
            GLES20.glClearColor(0f, 0f, 0f, 0f)
            GLES20.glClear(GLES20.GL_COLOR_BUFFER_BIT)
            drawModel()
        } else {
            drawFallbackGlow()
        }
    }

    private val fallbackColors = mapOf(
        "happy" to floatArrayOf(0.98f, 0.75f, 0.14f),
        "sad" to floatArrayOf(0.39f, 0.28f, 0.28f),
        "angry" to floatArrayOf(0.94f, 0.27f, 0.27f),
        "surprise" to floatArrayOf(0.02f, 0.71f, 0.83f),
        "neutral" to floatArrayOf(0.65f, 0.55f, 0.98f),
    )
    private var fallbackTime = 0f

    private fun drawFallbackGlow() {
        fallbackTime += deltaTimeSeconds
        val c = fallbackColors[currentEmotion] ?: fallbackColors["neutral"]!!
        val pulse = 0.12f + kotlin.math.sin(fallbackTime * 1.5f) * 0.04f
        GLES20.glClearColor(c[0] * 0.1f, c[1] * 0.1f, c[2] * 0.1f, pulse)
        GLES20.glClear(GLES20.GL_COLOR_BUFFER_BIT)
    }

    // ─── 帧渲染 ────────────────────────────────────────

    private fun drawModel() {
        val m = model!!
        val r = renderer!!
        val cubismModel = m.getModel()

        // 1. 情感参数
        applyEmotion(cubismModel)

        // 2. 口型 + 眼球
        applyStateParams(cubismModel)

        // 3. 物理 + 眨眼 + 呼吸
        m.updatePhysics(deltaTimeSeconds)
        eyeBlink?.updateParameters(cubismModel, deltaTimeSeconds)
        breath?.updateParameters(cubismModel, deltaTimeSeconds)

        // 4. 触摸拖拽 (眼球追踪)
        m.setDragging(eyeTargetX, eyeTargetY)

        // 5. 更新模型顶点
        cubismModel.update()

        // 6. 投影矩阵
        val projection = CubismMatrix44.create()
        CubismMatrix44.multiply(modelMatrix!!.getArray(), projection.getArray(), projection.getArray())
        CubismMatrix44.multiply(viewMatrix.getArray(), projection.getArray(), projection.getArray())
        r.setMvpMatrix(projection)

        // 7. 渲染
        r.drawModel()
    }

    // ─── 情感映射 ─────────────────────────────────────

    private fun applyEmotion(model: CubismModel) {
        val idMgr = CubismFramework.getIdManager()
        fun set(id: String, v: Float) {
            model.setParameterValue(idMgr.getId(id), v.coerceIn(0f, 1f))
        }
        when (currentEmotion) {
            "happy", "joy" -> {
                set("ParamMouthForm", 0.5f); set("ParamEyeLOpen", 0.6f)
                set("ParamEyeROpen", 0.6f); set("ParamBrowLY", -0.2f)
                set("ParamBrowRY", -0.2f)
            }
            "sad" -> {
                set("ParamBrowLY", 0.4f); set("ParamBrowRY", 0.4f)
                set("ParamEyeLOpen", 0.3f); set("ParamEyeROpen", 0.3f)
                set("ParamMouthForm", -0.3f)
            }
            "angry" -> {
                set("ParamBrowLY", 0.6f); set("ParamBrowRY", 0.6f)
                set("ParamEyeLOpen", 0.9f); set("ParamEyeROpen", 0.9f)
            }
            "surprise" -> {
                set("ParamEyeLOpen", 1f); set("ParamEyeROpen", 1f)
                set("ParamMouthOpenY", 0.3f); set("ParamBrowLY", -0.5f)
                set("ParamBrowRY", -0.5f)
            }
            "neutral" -> {
                set("ParamMouthForm", 0f); set("ParamEyeLOpen", 1f)
                set("ParamEyeROpen", 1f); set("ParamBrowLY", 0f)
                set("ParamBrowRY", 0f)
            }
        }
    }

    private fun applyStateParams(model: CubismModel) {
        val idMgr = CubismFramework.getIdManager()
        model.setParameterValue(idMgr.getId("ParamMouthOpenY"), mouthOpenRatio)
        model.setParameterValue(idMgr.getId("ParamEyeBallX"), eyeTargetX)
        model.setParameterValue(idMgr.getId("ParamEyeBallY"), eyeTargetY)
    }

    // ─── 控制接口 ─────────────────────────────────────

    fun setEmotion(emotionKey: String) {
        currentEmotion = emotionKey
    }

    fun setState(state: MiyaLive2DGLView.Live2DState) {
    }

    fun setMouthOpen(ratio: Float) {
        mouthOpenRatio = ratio.coerceIn(0f, 1f)
    }

    fun setEyeTracking(x: Float, y: Float) {
        eyeTargetX = x.coerceIn(-1f, 1f)
        eyeTargetY = y.coerceIn(-1f, 1f)
    }
}

/**
 * CubismUserModel 的子类，用于弥娅 Live2D 模型
 */
class MiyaCubismModel : CubismUserModel() {
    public override fun loadModel(buffer: ByteArray) {
        super.loadModel(buffer)
    }

    public override fun loadPhysics(buffer: ByteArray) {
        super.loadPhysics(buffer)
    }

    public override fun loadExpression(buffer: ByteArray): CubismExpressionMotion {
        return super.loadExpression(buffer)
    }

    fun updatePhysics(deltaTime: Float) {
        // CubismUserModel has physics built-in, updated automatically through motion
    }
}
