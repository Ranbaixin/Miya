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
            )
        } catch (e: Exception) {
            e.printStackTrace()
        }
    }
}
