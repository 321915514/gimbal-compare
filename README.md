# G20 吊舱↔双目 对比验证（Android 原生版，含 RTSP 抓帧）

云端自动打包：**push 到 GitHub → Actions 自动编译 → 下载 APK**。

## 一、一次性设置（约 10 分钟）

1. 注册 GitHub 账号，新建空仓库（如 `gimbal-compare`，别勾 README）。
2. 本机装 git（没装去 https://git-scm.com 下）。
3. 命令行 cd 到本目录，推送：
   ```bash
   git init
   git add .
   git commit -m "init"
   git branch -M main
   git remote add origin https://github.com/<你的用户名>/gimbal-compare.git
   git push -u origin main
   ```

## 二、以后每次出 APK

1. 改代码 / 改 `app/src/main/assets/config.js`（改 rtspUrl 等）。
2. 提交推送：
   ```bash
   git add . && git commit -m "改配置" && git push
   ```
3. GitHub 仓库 → **Actions** 标签 → 等构建（约 3~5 分钟）。
4. 构建完，Actions 页面底部 **Artifacts** 下载 `gimbal-compare-apk`。
5. 装 G20：`adb install app-debug.apk`

## 三、现场改配置

App 优先读 `/sdcard/gimbal_compare.html` + `/sdcard/config.js`（存在就用，否则内置 assets）：

```bash
adb push config.js /sdcard/config.js
adb push gimbal_compare.html /sdcard/gimbal_compare.html   # HTML 没变可跳过
```

重启 App 生效。**现场只需改 config.js 里 `rtspUrl` 一个字段。**

## 四、关键配置

- `rtspUrl`：吊舱 RTSP 地址（唯一现场要改的）。
- `GRAB_W / GRAB_H`（GimbalCompareActivity.kt 里）：抓帧分辨率，**必须和 H 标定时吊舱帧分辨率一致**。

## 五、常见问题

- 构建失败「Could not resolve org.videolan.android:libvlc-all:3.6.0」→ 把 app/build.gradle 里版本改成 3.5.1 或 3.6.1 再推。
- 抓帧失败（页面提示）→ 检查 rtspUrl、G20 和吊舱同网段、RTSP 是否需要账号密码（rtsp://user:pass@ip/...）。
