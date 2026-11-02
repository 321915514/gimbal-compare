package com.example.annotation.mqtt

import com.example.annotation.mqttbridge.IMqttBridge
import com.example.annotation.mqttbridge.IMqttListener
import org.eclipse.paho.client.mqttv3.IMqttDeliveryToken
import org.eclipse.paho.client.mqttv3.MqttCallback
import org.eclipse.paho.client.mqttv3.MqttClient
import org.eclipse.paho.client.mqttv3.MqttConnectOptions
import org.eclipse.paho.client.mqttv3.MqttMessage

/** 基于 Paho 的 MQTT 客户端。仅在 ENABLE_MQTT=true 时编译进 APK。 */
class MqttManager : IMqttBridge {

    @Volatile private var client: MqttClient? = null

    override fun start(broker: String, clientId: String, subscribe: String, listener: IMqttListener) {
        Thread {
            try {
                val c = MqttClient(broker, clientId + "_" + System.currentTimeMillis(), null)
                client = c
                val opts = MqttConnectOptions().apply {
                    isCleanSession = true
                    connectionTimeout = 5
                    keepAliveInterval = 30
                }
                c.connect(opts)
                val topics = subscribe.split(',').map { it.trim() }.filter { it.isNotEmpty() }
                if (topics.isNotEmpty()) {
                    c.setCallback(object : MqttCallback {
                        override fun connectionLost(cause: Throwable?) {}
                        override fun messageArrived(topic: String, msg: MqttMessage) {
                            try {
                                listener.onMessage(topic, String(msg.payload, Charsets.UTF_8))
                            } catch (_: Exception) {}
                        }
                        override fun deliveryComplete(token: IMqttDeliveryToken?) {}
                    })
                    c.subscribe(topics.toTypedArray())
                }
            } catch (_: Exception) {
                // 连不上不影响主功能，静默
            }
        }.start()
    }

    override fun publish(topic: String, payload: String) {
        Thread {
            try {
                val c = client
                if (c == null || !c.isConnected) {
                    android.util.Log.d("MqttManager", "publish 失败: 未连接")
                    return@Thread
                }
                c.publish(topic, MqttMessage(payload.toByteArray(Charsets.UTF_8)))
                android.util.Log.d("MqttManager", "publish 成功: $topic = $payload")
            } catch (e: Exception) {
                android.util.Log.d("MqttManager", "publish 异常: ${e.message}")
            }
        }.start()
    }

    override fun stop() {
        try { client?.disconnect() } catch (_: Exception) {}
        try { client?.close() } catch (_: Exception) {}
        client = null
    }
}
