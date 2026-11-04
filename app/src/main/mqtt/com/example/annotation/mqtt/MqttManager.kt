package com.example.annotation.mqtt

import com.example.annotation.mqttbridge.IMqttBridge
import com.example.annotation.mqttbridge.IMqttListener
import org.eclipse.paho.client.mqttv3.IMqttDeliveryToken
import org.eclipse.paho.client.mqttv3.MqttCallbackExtended
import org.eclipse.paho.client.mqttv3.MqttClient
import org.eclipse.paho.client.mqttv3.MqttConnectOptions
import org.eclipse.paho.client.mqttv3.MqttMessage
import java.util.concurrent.atomic.AtomicBoolean
import java.util.concurrent.atomic.AtomicInteger

/**
 * 基于 Paho 的 MQTT 客户端。仅在 ENABLE_MQTT=true 时编译进 APK。
 *
 * broker 支持逗号分隔的多个候选地址，例如：
 *   "tcp://192.168.3.78:1883,tcp://192.168.2.82:1883"
 * 依次尝试，连上哪个就用哪个；全部失败则每 3 秒重试一轮。
 * 连上后开启 Paho 自动重连，断线不需要重启 App。
 */
class MqttManager : IMqttBridge {

    @Volatile private var client: MqttClient? = null
    @Volatile private var brokers: List<String> = emptyList()
    @Volatile private var clientIdPrefix: String = "g20"
    @Volatile private var subscribeTopics: String = ""
    @Volatile private var listener: IMqttListener? = null
    private val running = AtomicBoolean(false)
    private val gen = AtomicInteger(0)

    override fun start(broker: String, clientId: String, subscribe: String, listener: IMqttListener) {
        brokers = broker.split(',').map { it.trim() }.filter { it.isNotEmpty() }
        clientIdPrefix = clientId
        subscribeTopics = subscribe
        this.listener = listener
        if (brokers.isEmpty()) return
        val myGen = gen.incrementAndGet()          // 递增代数，使旧连接线程自行退出
        try { client?.disconnect() } catch (_: Exception) {}
        try { client?.close() } catch (_: Exception) {}
        client = null
        running.set(true)
        Thread { connectLoop(myGen) }.start()
    }

    override fun isConnected(): Boolean = client?.isConnected == true

    override fun probe(brokerCsv: String): String {
        val urls = brokerCsv.split(',').map { it.trim() }.filter { it.isNotEmpty() }
        if (urls.isEmpty()) return "FAIL:未填写 broker"
        var lastErr = ""
        for (u in urls) {
            try {
                val c = MqttClient(u, "probe_" + System.nanoTime(), null)
                c.connect(MqttConnectOptions().apply {
                    isCleanSession = true
                    connectionTimeout = 2
                })
                c.disconnect(); c.close()
                return "OK:$u"
            } catch (e: Exception) {
                lastErr = e.message ?: e.toString()
            }
        }
        return "FAIL:$lastErr"
    }

    private fun connectLoop(myGen: Int) {
        while (running.get() && gen.get() == myGen) {
            for (b in brokers) {
                if (!running.get()) return
                try {
                    val c = MqttClient(b, clientIdPrefix + "_" + System.currentTimeMillis(), null)
                    val opts = MqttConnectOptions().apply {
                        isCleanSession = true
                        connectionTimeout = 4
                        keepAliveInterval = 20
                        isAutomaticReconnect = true
                    }
                    c.connect(opts)
                    client = c

                    val topics = subscribeTopics.split(',').map { it.trim() }.filter { it.isNotEmpty() }
                    if (topics.isNotEmpty()) {
                        c.setCallback(object : MqttCallbackExtended {
                            override fun connectComplete(reconnect: Boolean, serverURI: String?) {
                                android.util.Log.d("MqttManager", "已连接(${if (reconnect) "重连" else "首次"}): $serverURI")
                            }
                            override fun connectionLost(cause: Throwable?) {
                                android.util.Log.d("MqttManager", "连接断开(自动重连中): ${cause?.message}")
                            }
                            override fun messageArrived(topic: String, msg: MqttMessage) {
                                try {
                                    listener?.onMessage(topic, String(msg.payload, Charsets.UTF_8))
                                } catch (_: Exception) {}
                            }
                            override fun deliveryComplete(token: IMqttDeliveryToken?) {}
                        })
                        c.subscribe(topics.toTypedArray())
                    }
                    android.util.Log.d("MqttManager", "已连接 broker: $b")
                    return   // 连上即退出循环，后续交给 Paho 自动重连
                } catch (e: Exception) {
                    android.util.Log.d("MqttManager", "连接失败 $b: ${e.message}")
                }
            }
            try { Thread.sleep(3000) } catch (_: InterruptedException) { return }
        }
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
        gen.incrementAndGet()
        running.set(false)
        try { client?.disconnect() } catch (_: Exception) {}
        try { client?.close() } catch (_: Exception) {}
        client = null
    }
}
