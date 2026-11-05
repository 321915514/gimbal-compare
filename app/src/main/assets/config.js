// ============================================================
//  现场部署配置 —— 现场只改这一个文件即可
// ============================================================
window.GIMBAL_CONFIG = {

  // RTSP 地址：吊舱视频流（App 内原生抓帧用，现场只改这个）
  rtspUrl: "rtsp://192.168.1.100:8554/test",

  // HTTP 抓帧地址（浏览器调试回退用，App 里不用）
  frameUrl: "http://127.0.0.1:8899/frame.jpg",

  // 简化算法：参考点 + 比例（不用 H 矩阵）
  // 参考点 = 吊舱相机向下对正时，画面里四圆孔中心（实测 653,358；帧中心是 640,360，差 +13/-2 px）
  gimbalRefX: 653,   // 吊舱参考中心 X
  gimbalRefY: 358,   // 吊舱参考中心 Y
  // scale 实测标定（720p 帧）：宽 250mm/209px=1.1962，长 440mm/370px=1.1892，两向差 0.58% -> 取 1.19
  // 视野覆盖 152.5cm x 85.8cm；平台走 100mm 图上应移 83.9px
  scale: 1.19,       // mm/px（现场标定：Z / f_吊舱）

  // MQTT 通信（需 APK 用 ENABLE_MQTT=true 编译才生效）
  mqtt: {
    enabled: true,
    broker: "tcp://192.168.3.78:1883,tcp://192.168.2.82:1883",  // 候选列表，连上哪个用哪个
    clientId: "g20",
    subscribe: "gimbal/real_dxdy,aruco/detection",   // 真值（订阅=收，两者都认）
    publish: "gimbal/result",               // dx/dy 结果（发布=发）
    calibCmd: "aruco/stop",                 // 校准命令（发布=发，点「校准」发 {"cmd":"calibrate"}）
    calibStatus: "aruco/calibrate/status",  // 校准状态（订阅=收，收 {"status":0/1/2} 显示）
    stereoGrab: "stereo/grab",              // 请求双目图（发布=发 {"cmd":"grab"}）
    stereoImage: "stereo/image"             // 双目图返回（订阅=收 {"img":"base64"}）
  }
};
