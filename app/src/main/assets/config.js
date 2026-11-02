// ============================================================
//  现场部署配置 —— 现场只改这一个文件即可
// ============================================================
window.GIMBAL_CONFIG = {

  // RTSP 地址：吊舱视频流（App 内原生抓帧用，现场只改这个）
  rtspUrl: "rtsp://192.168.1.100:8554/test",

  // HTTP 抓帧地址（浏览器调试回退用，App 里不用）
  frameUrl: "http://127.0.0.1:8899/frame.jpg",

  // 简化算法：参考点 + 比例（不用 H 矩阵）
  gimbalRefX: 640,   // 吊舱参考中心 X（现场校准后自动记，这里只是初值）
  gimbalRefY: 360,   // 吊舱参考中心 Y
  scale: 0.68,       // mm/px（现场标定：Z / f_吊舱）

  // MQTT 通信（需 APK 用 ENABLE_MQTT=true 编译才生效）
  mqtt: {
    enabled: true,
    broker: "tcp://192.168.1.100:1883",    // EMQX
    clientId: "g20",
    subscribe: "gimbal/real_dxdy",          // 真值（订阅=收）
    publish: "gimbal/result",               // dx/dy 结果（发布=发）
    calibCmd: "aruco/stop",                 // 校准命令（发布=发，点「校准」发 {"cmd":"calibrate"}）
    calibStatus: "aruco/calibrate/status",  // 校准状态（订阅=收，收 {"status":0/1/2} 显示）
    stereoGrab: "stereo/grab",              // 请求双目图（发布=发 {"cmd":"grab"}）
    stereoImage: "stereo/image"             // 双目图返回（订阅=收 {"img":"base64"}）
  }
};
