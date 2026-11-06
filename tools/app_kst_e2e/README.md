# app_kst_e2e — 吊舱↔双目 1:1 换算回归（真跑 App 的 JS，不是纸面推导）

`app_kst_e2e.js` 从 `app/src/main/assets/gimbal_compare.html` 抽出主 `<script>`，在 Node 的
`vm` context 里用 DOM 打桩**真实执行**：按标定 manifest 里的真实孔位坐标派发
`pointerdown` 点四个圆 → 走 App 自己的 `toImg / fitCircle / recompute` → 读回面板文本，
再与另一条独立实现算出的期望值逐条对比。图片尺寸不写死，从归档图真实字节解出
（PNG IHDR / JPEG SOF）。MQTT 发布靠替换 global 上的 `mqttPublish` 捕获，未改 App 源码。

## 跑法

```bash
"C:/Users/QI/AppData/Local/hermes/node/node" app_kst_e2e.js   # 同时写 _node_result.json
```
文件开头两个路径：`DIR`（assets 目录）、`D`（标定归档数据目录，需含 `manifest.json`
和 `pod_*.jpg` / `_st.jpg` / `_st02.jpg`）。换机器改这两行即可。

## 本次结果（2026-11-06，5 组全部对上）

| 用例 | App 面板 | 独立算出的期望 |
|---|---|---|
| 吊舱组04 点四圆 (642.8,361.4) | `dx -0mm` `dy 0mm` | `0.00 / -0.06` mm |
| ↳ 双目换算 + 板心预测 | `0.0mm` `-0.1mm` @ `(784.4, 559.2)` | `0.00 / -0.07` @ `(784.44, 559.15)` |
| 双目组04 点四圆 (785.5,559.7) | `-1mm` `-1mm` / `-1.0mm` `-0.5mm` | `-0.95 / -0.52` mm |
| 吊舱组02 | `1mm` `0mm` → 双目 `1.1mm` `0.5mm` | `1.07 / 0.54` mm |
| 双目组02 | `-0mm` `0mm` | `-0.08 / 0.50` mm |
| 合成偏移 吊舱 (+40,-25px) | `-48mm` `30mm` → 双目 `-47.6mm` `29.7mm` @ `(841.8, 523.3)` | `-47.63 / 29.66` @ `(841.85, 523.26)` |
| 双目帧点「校准」 | 只改 `ST_REF→(785.55,559.72)`，吊舱 ref 不动，`aruco/stop` 发布 **0 条** | 与四孔均值一致；本地量不该通知板端 |
| 吊舱帧点「校准」 | `REF→(642.83,361.45)`，发 `aruco/stop{cmd:"calibrate"}` + `gimbal/result{dx:0,dy:0}` | payload 只 `dx/dy`，`dz/msgid/rotation/valid` 是板端契约，App 侧未动 |
| 存盘/恢复/复位 | 写 `stereo_ref`+`gimbal_ref` 两个 key；`applyConfig` 分别恢复；复位回到 config.js | 两套常量互不污染 |
| App 自测新增两项 | `双相机常量 齐备`、`换算·100mm→双目像素 ±100mm ↔ ±120px` 通过 | k_st=0.83 → 100/0.83=120.5px |

## 覆盖与不覆盖

- 真跑：孔位拟合、两套常量切换、1:1 换算、板心预测、校准分流、持久化、复位、自测。
- 不覆盖：真实取帧（libVLC / 板端 HTTP）、WebView 内核渲染、真 MQTT 链路、像素吸附
  `snapImageData`（桩里 `getImageData` 只给 4 字节，走的是手动点路线）。
