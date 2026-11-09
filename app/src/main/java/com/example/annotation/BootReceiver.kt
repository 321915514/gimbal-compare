// BootReceiver.kt —— 开机自启常驻服务（配过 broker 才起，供冷启动拉起标注 App）
package com.example.annotation

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.os.Build

class BootReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action != Intent.ACTION_BOOT_COMPLETED) return
        val prefs = context.getSharedPreferences("gimbal_cfg", Context.MODE_PRIVATE)
        if ((prefs.getString("broker", "") ?: "").isEmpty()) return  // 从没配过地址，不起服务
        try {
            val i = Intent(context, MqttForegroundService::class.java)
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) context.startForegroundService(i)
            else context.startService(i)
        } catch (_: Exception) {}
    }
}
