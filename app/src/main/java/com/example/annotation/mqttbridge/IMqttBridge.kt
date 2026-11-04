package com.example.annotation.mqttbridge

/** MQTT 消息回调（App 侧实现） */
interface IMqttListener {
    fun onMessage(topic: String, payload: String)
}

/** MQTT 桥接口：实现类只在 ENABLE_MQTT=true 时编译进 APK，App 侧只依赖此接口 */
interface IMqttBridge {
    fun start(broker: String, clientId: String, subscribe: String, listener: IMqttListener)
    fun publish(topic: String, payload: String)
    fun stop()
    /** 当前是否已连上 broker（供设置页自测/状态显示用） */
    fun isConnected(): Boolean
    /** 用给定 broker 候选串做一次真实连接探测，返回 "OK:<url>" 或 "FAIL:<原因>"（不改变已生效连接） */
    fun probe(brokerCsv: String): String
}
