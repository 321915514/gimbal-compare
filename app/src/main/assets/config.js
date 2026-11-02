// ============================================================
//  现场部署配置 —— 现场只改这一个文件即可
// ============================================================
window.GIMBAL_CONFIG = {

  // RTSP 地址：吊舱视频流（App 内原生抓帧用，现场只改这个）
  rtspUrl: "rtsp://192.168.1.103:8554/test",

  // HTTP 抓帧地址（浏览器调试回退用，App 里不用）
  frameUrl: "http://127.0.0.1:8899/frame.jpg",

  // 单应矩阵 H（行优先 9 个数）
  H: "0.960786 0.113722 221.225764 0.041811 1.750072 55.030138 0.000008 0.00017 1.0",

  // 双目内参 + 工作距离
  Z: 731, fx: 1081.7555, fy: 1081.9276,

  // 基准点
  baseX: 787, baseY: 535,

  // 偏差阈值 mm（预留）
    threshold: 2,

  // MQTT 通信（需 APK 用 ENABLE_MQTT=true 编译才生效；enabled=false 不连接）
  mqtt: {
    enabled: true,
    broker: "tcp://192.168.1.103:1883",   // 板端 EMQX broker
    clientId: "g20",
    subscribe: "gimbal/real_dxdy",         // 订阅双目/云台真值
    publish: "gimbal/result"               // 发布本机计算结果
  }
};
