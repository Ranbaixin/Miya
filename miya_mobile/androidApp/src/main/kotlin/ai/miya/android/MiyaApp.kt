package ai.miya.android

import android.app.Application
import ai.miya.shared.ServiceLocator
import ai.miya.shared.PlatformContext
import com.russhwolf.settings.Settings

class MiyaApp : Application() {
    override fun onCreate() {
        super.onCreate()
        try {
            ServiceLocator.init(
                context = PlatformContext(
                    settingsFactory = { Settings() }
                ),
                baseUrl = "http://192.168.10.122:8000"
            )
        } catch (e: Exception) {
            e.printStackTrace()
        }
    }
}
