package ai.miya.app

import android.app.*
import android.content.Context
import android.content.Intent
import android.os.Build
import android.os.IBinder
import androidx.core.app.NotificationCompat
import ai.miya.domain.ServiceRegistry
import ai.miya.network.MiyaApiClient
import kotlinx.coroutines.*

class ChatNotificationService : Service() {

    private val scope = CoroutineScope(Dispatchers.IO + SupervisorJob())
    private var lastMessageId: String = ""

    companion object {
        const val CHANNEL_ID = "miya_chat_notifications"
        const val CHANNEL_NAME = "弥娅消息"
        const val NOTIFICATION_ID = 1001

        fun start(context: Context) {
            val intent = Intent(context, ChatNotificationService::class.java)
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                context.startForegroundService(intent)
            } else {
                context.startService(intent)
            }
        }

        fun stop(context: Context) {
            context.stopService(Intent(context, ChatNotificationService::class.java))
        }
    }

    override fun onCreate() {
        super.onCreate()
        createNotificationChannel()
        startPolling()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        val notification = createNotification("正在等待弥娅的消息…")
        startForeground(NOTIFICATION_ID, notification)
        return START_STICKY
    }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onDestroy() {
        scope.cancel()
        super.onDestroy()
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID, CHANNEL_NAME, NotificationManager.IMPORTANCE_HIGH
            ).apply {
                description = "弥娅的新消息提醒"
                enableLights(true)
                enableVibration(true)
                setBypassDnd(true)
            }
            val manager = getSystemService(NotificationManager::class.java)
            manager.createNotificationChannel(channel)
        }
    }

    private fun createNotification(text: String): Notification {
        val intent = packageManager.getLaunchIntentForPackage(packageName)
        val pendingIntent = PendingIntent.getActivity(
            this, 0, intent, PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )
        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setSmallIcon(android.R.drawable.ic_dialog_info)
            .setContentTitle("弥娅")
            .setContentText(text)
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .setCategory(NotificationCompat.CATEGORY_MESSAGE)
            .setContentIntent(pendingIntent)
            .setOngoing(true)
            .build()
    }

    private fun showMessageNotification(message: String) {
        val intent = packageManager.getLaunchIntentForPackage(packageName)
        val pendingIntent = PendingIntent.getActivity(
            this, 1, intent, PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )
        val notification = NotificationCompat.Builder(this, CHANNEL_ID)
            .setSmallIcon(android.R.drawable.ic_dialog_info)
            .setContentTitle("弥娅")
            .setContentText(message.take(100))
            .setStyle(NotificationCompat.BigTextStyle().bigText(message))
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .setCategory(NotificationCompat.CATEGORY_MESSAGE)
            .setContentIntent(pendingIntent)
            .setAutoCancel(true)
            .build()
        val manager = getSystemService(NotificationManager::class.java)
        manager.notify(NOTIFICATION_ID + 1, notification)
    }

    private fun startPolling() {
        scope.launch {
            while (isActive) {
                delay(15_000)
                try {
                    val api = ServiceRegistry.getOrThrow(MiyaApiClient::class.java)
                    val msgs = api.getPendingMessages("default")
                    for (msg in msgs) {
                        val text = msg["message"] ?: continue
                        if (text != lastMessageId) {
                            lastMessageId = text
                            showMessageNotification(text)
                        }
                    }
                } catch (_: Exception) {}
            }
        }
    }
}
