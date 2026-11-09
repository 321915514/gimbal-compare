// MqttForegroundService.kt —— 冷启动常驻服务：订阅 aruco/manual/request，收到就拉起标注 App
// Paho/MqttManager 在条件源码集 src/main/mqtt，不能直接 import，故反射加载（同 Activity 的做法）；
// ENABLE_MQTT=false 时反射失败，服务空转不订阅，不崩溃。
package com.example.annotation

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.os.Build
import android.os.IBinder
import com.example.annotation.mqttbridge.IMqttBridge
import com.example.annotation.mqttbridge.IMqttListener

class MqttForegroundService : Service() {

    private var bridge: IMqttBridge? = null
    private var worker: Thread? = null
    @Volatile private var running = false
    private val topic = "aruco/manual/request"

    override fun onCreate() {
        super.onCreate()
        startAsForeground()
        running = true
        worker = Thread { connectLoop() }.also { it.isDaemon = true; it.start() }
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int = START_STICKY
    override fun onBind(i: Intent?): IBinder? = null

    private fun startAsForeground() {
        val ch = "gimbal_manual_wake"
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val nc = NotificationChannel(ch, "标注待办常驻", NotificationManager.IMPORTANCE_LOW)
            getSystemService(NotificationManager::class.java)?.createNotificationChannel(nc)
        }
        @Suppress("DEPRECATION")
        val b = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O)
            Notification.Builder(this, ch) else Notification.Builder(this)
        val notif = b.setContentTitle("吊舱标注待办常驻")
            .setContentText("自动校准失败时会自动打开标注")
            .setSmallIcon(android.R.drawable.stat_notify_sync)
            .build()
        try {
            if (Build.VERSION.SDK_INT >= 34)
                startForeground(2, notif, ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC)
            else startForeground(2, notif)
        } catch (_: Exception) {}
    }

    private fun connectLoop() {
        while (running) {
            val prefs = getSharedPreferences("gimbal_cfg", Context.MODE_PRIVATE)
            val broker = prefs.getString("broker", "") ?: ""
            val clientId = (prefs.getString("clientId", "g20") ?: "g20") + "_svc"
            if (broker.isNotEmpty() && connectOnce(broker, clientId)) {
                // 已连上，交给 MqttManager 自动重连；轮询等断连或 broker 变更
                while (running) {
                    val nowBroker = getSharedPreferences("gimbal_cfg", Context.MODE_PRIVATE).getString("broker", "") ?: ""
                    if (bridge?.isConnected() == false || nowBroker != broker) break
                    sleepQuiet(5000)
                }
                try { bridge?.stop() } catch (_: Exception) {}
                bridge = null
                continue
            }
            sleepQuiet(6000)
        }
    }

    private fun connectOnce(brokerCsv: String, clientId: String): Boolean {
        val b = try {
            Class.forName("com.example.annotation.mqtt.MqttManager")
                .getDeclaredConstructor().newInstance() as IMqttBridge
        } catch (_: Exception) { return false }
        bridge = b
        b.start(brokerCsv, clientId, topic, object : IMqttListener {
            override fun onMessage(t: String, payload: String) {
                if (t == topic) wakeApp(payload)
            }
        })
        sleepQuiet(3500)
        if (b.isConnected()) return true
        try { b.stop() } catch (_: Exception) {}
        bridge = null
        return false
    }

    private fun wakeApp(payload: String) {
        val i = Intent(this, GimbalCompareActivity::class.java).apply {
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_SINGLE_TOP or
                    Intent.FLAG_ACTIVITY_CLEAR_TOP)
            putExtra("manual_request", payload)
        }
        // 前台时直接拉起（快）；后台/未开时靠 full-screen intent 通知绕过 Android 12+ 后台启动限制
        try { startActivity(i) } catch (_: Exception) {}
        val pi = PendingIntent.getActivity(this, 1, i,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)
        val ch = "gimbal_wake_alert"
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val nc = NotificationChannel(ch, "标注提醒", NotificationManager.IMPORTANCE_HIGH)
            getSystemService(NotificationManager::class.java)?.createNotificationChannel(nc)
        }
        @Suppress("DEPRECATION")
        val b = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O)
            Notification.Builder(this, ch) else Notification.Builder(this)
        val notif = b.setContentTitle("需要人工标注")
            .setContentText("自动校准失败，请在画面标 4 个孔")
            .setSmallIcon(android.R.drawable.stat_notify_sync)
            .setFullScreenIntent(pi, true)
            .setAutoCancel(true)
            .build()
        try { getSystemService(NotificationManager::class.java)?.notify(100, notif) } catch (_: Exception) {}
    }

    private fun sleepQuiet(ms: Long) { try { Thread.sleep(ms) } catch (_: InterruptedException) {} }

    override fun onDestroy() {
        running = false
        try { bridge?.stop() } catch (_: Exception) {}
        worker?.interrupt()
        super.onDestroy()
    }
}
