package ai.miya.app

import android.app.Application
import ai.miya.domain.*
import ai.miya.network.*

class MiyaApplication : Application() {

    companion object {
        lateinit var instance: MiyaApplication
            private set
    }

    override fun onCreate() {
        super.onCreate()
        instance = this
        registerServices()
    }

    private fun registerServices() {
        val connectionManager = MiyaConnectionManager()
        val apiClient = MiyaApiClient()

        ServiceRegistry.registerSingleton(ConnectionProvider::class.java) {
            ConnectionProviderImpl(connectionManager, apiClient)
        }

        ServiceRegistry.registerSingleton(ChatProvider::class.java) {
            ChatProviderImpl(apiClient)
        }

        ServiceRegistry.registerSingleton(SessionProvider::class.java) {
            SessionProviderImpl(apiClient)
        }

        ServiceRegistry.registerSingleton(MemoryProvider::class.java) {
            MemoryProviderImpl(apiClient)
        }

        ServiceRegistry.registerSingleton(PersonaProvider::class.java) {
            PersonaProviderImpl(apiClient)
        }

        ServiceRegistry.markInitialized()
    }
}
