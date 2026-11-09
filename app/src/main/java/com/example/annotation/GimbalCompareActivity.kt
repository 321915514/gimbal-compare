// GimbalCompareActivity.kt —— G20 全屏显示页面 + libVLC 抓 RTSP 帧
// 现场只改 rtspUrl（config.js / gimbal_config.json），页面点「获取帧」→ 本类连 RTSP 抓一帧回传。
package com.example.annotation

import android.annotation.SuppressLint
import android.app.Activity
import android.content.Context
import android.content.Intent
import android.graphics.Bitmap
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.util.Base64
import android.view.Gravity
import android.view.TextureView
import android.webkit.JavascriptInterface
import android.webkit.WebChromeClient
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.FrameLayout
import org.videolan.libvlc.LibVLC
import org.videolan.libvlc.Media
import org.videolan.libvlc.MediaPlayer
import java.io.ByteArrayOutputStream
import com.example.annotation.mqttbridge.IMqttBridge
import com.example.annotation.mqttbridge.IMqttListener
import org.json.JSONObject

class GimbalCompareActivity : Activity() {

    private lateinit var webView: WebView
    private lateinit var rtspView: TextureView   // 隐藏的 RTSP 渲染目标（在 WebView 后面）
    private var libVLC: LibVLC? = null
    private var mediaPlayer: MediaPlayer? = null
    private var mqttBridge: IMqttBridge? = null
    @Volatile private var pendingManualPayload: String? = null   // 冷启动/热拉起时服务传来的 manual/request

    // 抓帧分辨率：与 H 标定时吊舱帧分辨率一致（改这里）
    private val GRAB_W = 1280
    private val GRAB_H = 720

    inner class Bridge {
        @JavascriptInterface
        fun grabFrame(rtspUrl: String) = runOnUiThread { grabRtspFrame(rtspUrl) }

        @JavascriptInterface
        fun mqttStart(broker: String, clientId: String, subscribe: String) {
            runOnUiThread { startMqtt(broker, clientId, subscribe) }
        }

        @JavascriptInterface
        fun mqttPublish(topic: String, payload: String) {
            runOnUiThread { mqttBridge?.publish(topic, payload) }
        }

        @JavascriptInterface
        fun mqttIsConnected(): Boolean = mqttBridge?.isConnected() == true

        /** 冷启动/热拉起时取走待处理的人工标注请求(aruco/manual/request)，取一次即清空 */
        @JavascriptInterface
        fun takePendingManualRequest(): String {
            val p = pendingManualPayload ?: ""
            pendingManualPayload = null
            return p
        }

        /** 探测输入框里填的 broker（可逗号多个），不影响当前连接 */
        @JavascriptInterface
        fun mqttProbe(broker: String) {
            Thread {
                var ok = false
                var msg = ""
                try {
                    val b = mqttBridge ?: (
                        Class.forName("com.example.annotation.mqtt.MqttManager")
                            .getDeclaredConstructor().newInstance() as IMqttBridge)
                    val res = b.probe(broker)
                    ok = res.startsWith("OK:")
                    msg = if (ok) "已连上 " + res.removePrefix("OK:")
                          else "失败 " + res.removePrefix("FAIL:")
                } catch (e: Exception) {
                    msg = "MQTT 不可用：" + (e.message ?: "")
                }
                val f = ok
                val fm = msg
                webView.post {
                    webView.evaluateJavascript(
                        "window.onMqttProbeResult&&window.onMqttProbeResult($f,${jsStr(fm)})", null)
                }
            }.start()
        }

        /** 探测 RTSP 地址的 TCP 端口是否可连 */
        @JavascriptInterface
        fun rtspProbe(url: String) {
            Thread {
                var ok = false
                var err = ""
                try {
                    val u = java.net.URI(url)
                    val host = u.host ?: throw Exception("地址里没有主机名")
                    val port = if (u.port > 0) u.port else 554
                    java.net.Socket().use { s ->
                        s.connect(java.net.InetSocketAddress(host, port), 3000)
                        ok = true
                    }
                } catch (e: Exception) { err = e.message ?: "" }
                val f = ok
                val fe = err
                webView.post {
                    webView.evaluateJavascript(
                        "window.onRtspProbeResult&&window.onRtspProbeResult($f,${jsStr(fe)})", null)
                }
            }.start()
        }

        private fun jsStr(s: String): String =
            "\"" + s.replace("\\", "\\\\").replace("\"", "\\\"").replace("\n", " ").replace("\r", " ") + "\""
    }

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        WebView.setWebContentsDebuggingEnabled(true)   // 调试用：允许 chrome://inspect 查看 DOM
        // 内容适配系统栏：导航栏/状态栏不遮挡页面（显示底部导航按钮后，内容不被盖住）
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            window.setDecorFitsSystemWindows(true)
        }

        // TextureView（渲染 RTSP，抓帧用）在 WebView 后面
        rtspView = TextureView(this)
        rtspView.layoutParams = FrameLayout.LayoutParams(GRAB_W, GRAB_H, Gravity.CENTER)
        webView = WebView(this)
        webView.layoutParams = FrameLayout.LayoutParams(
            FrameLayout.LayoutParams.MATCH_PARENT, FrameLayout.LayoutParams.MATCH_PARENT)
        val root = FrameLayout(this)
        root.fitsSystemWindows = true   // 内容适配系统栏（老 Android 也生效），整体在导航栏/状态栏之内
        root.addView(rtspView)
        root.addView(webView)   // WebView 盖住 TextureView（不透明，用户看不到 RTSP 画面）
        setContentView(root)

        webView.settings.javaScriptEnabled = true
        webView.settings.domStorageEnabled = true
        webView.settings.allowFileAccess = true
        webView.webViewClient = WebViewClient()
        webView.webChromeClient = WebChromeClient()
        webView.addJavascriptInterface(Bridge(), "G20")

        // 现场 adb push html/config 到 /sdcard/ 覆盖；否则用内置 assets 版本
        val sdcardHtml = java.io.File("/sdcard/gimbal_compare.html")
        webView.loadUrl(if (sdcardHtml.exists()) "file:///sdcard/gimbal_compare.html"
                        else "file:///android_asset/gimbal_compare.html")

        // 冷启动/热拉起：服务经 intent extra 传来的标注请求先暂存，页面就绪后自取
        intent?.getStringExtra("manual_request")?.let { pendingManualPayload = it }
        ensureNotifPermission()
        ensureWakeService()
    }

    /** Android 13+ 通知权限（前台服务通知用，拒绝也不影响服务运行） */
    private fun ensureNotifPermission() {
        if (Build.VERSION.SDK_INT >= 33 &&
            checkSelfPermission(android.Manifest.permission.POST_NOTIFICATIONS) !=
                android.content.pm.PackageManager.PERMISSION_GRANTED) {
            try { requestPermissions(arrayOf(android.Manifest.permission.POST_NOTIFICATIONS), 1) } catch (_: Exception) {}
        }
    }

    /** 启动常驻唤醒服务（ENABLE_MQTT=false 时反射失败即空转，不崩） */
    private fun ensureWakeService() {
        try {
            val i = Intent(this, MqttForegroundService::class.java)
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) startForegroundService(i)
            else startService(i)
        } catch (_: Exception) {}
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        intent.getStringExtra("manual_request")?.let {
            pendingManualPayload = it
            webView.post {
                webView.evaluateJavascript("window.__takeManual&&window.__takeManual()", null)
            }
        }
    }

    /** 反射加载 MqttManager（仅 ENABLE_MQTT=true 编译时存在），App 侧不硬依赖 Paho */
    private fun startMqtt(broker: String, clientId: String, subscribe: String) {
        if (!BuildConfig.ENABLE_MQTT) return
        // 存 broker/clientId 供常驻唤醒服务读取（冷启动订阅用；服务用 clientId+"_svc" 避免 client id 冲突）
        try {
            getSharedPreferences("gimbal_cfg", Context.MODE_PRIVATE).edit()
                .putString("broker", broker).putString("clientId", clientId).apply()
        } catch (_: Exception) {}
        try {
            val cls = Class.forName("com.example.annotation.mqtt.MqttManager")
            val bridge = cls.getDeclaredConstructor().newInstance() as IMqttBridge
            mqttBridge = bridge
            bridge.start(broker, clientId, subscribe, object : IMqttListener {
                override fun onMessage(topic: String, payload: String) {
                    runOnUiThread {
                        val t = JSONObject.quote(topic)
                        val pl = JSONObject.quote(payload)
                        webView.evaluateJavascript("window.onMqttMessage && window.onMqttMessage($t,$pl)", null)
                    }
                }
            })
        } catch (_: Exception) {
            // MQTT 未编译进 APK 或加载失败，静默
        }
        ensureWakeService()   // 存好配置后再确保唤醒服务起来（服务会轮询 SharedPreferences 重连）
    }

    /** 连 RTSP → play → 等第一帧 → TextureView 抓 Bitmap → JPEG base64 → 推回页面 */
    private fun grabRtspFrame(rtspUrl: String) {
        releasePlayer()
        try {
            val lv = LibVLC(this, arrayListOf(
                "--network-caching=300", "--live-caching=200",
                "--drop-late-frames", "--skip-frames", "--rtsp-tcp"))
            libVLC = lv
            val mp = MediaPlayer(lv)
            mediaPlayer = mp
            mp.vlcVout.setVideoView(rtspView)
            mp.vlcVout.attachViews()
            val media = Media(lv, Uri.parse(rtspUrl))
            media.setHWDecoderEnabled(true, false)
            mp.media = media
            media.release()
            mp.setEventListener { event ->
                when (event.type) {
                    MediaPlayer.Event.Playing ->
                        rtspView.postDelayed({ tryGrab(0) }, 800)
                    MediaPlayer.Event.EncounteredError -> { pushFail(); releasePlayer() }
                }
            }
            mp.play()
        } catch (e: Exception) {
            pushFail(); releasePlayer()
        }
    }

    // 轮询抓帧直到非黑（RTSP 首帧要时间，黑帧=还没渲染出来）
    private fun tryGrab(attempt: Int) {
        if (attempt >= 12) { pushFail(); releasePlayer(); return }  // 约 6 秒超时
        val bmp = try { rtspView.bitmap } catch (e: Exception) { null }
        if (bmp != null && !isBlack(bmp)) {
            pushJpeg(bmp); releasePlayer()
        } else {
            rtspView.postDelayed({ tryGrab(attempt + 1) }, 500)
        }
    }

    private fun isBlack(bmp: Bitmap): Boolean {
        var nonBlack = 0
        val stepX = maxOf(1, bmp.width / 40)
        val stepY = maxOf(1, bmp.height / 40)
        var y = 0
        while (y < bmp.height) {
            var x = 0
            while (x < bmp.width) {
                val p = bmp.getPixel(x, y)
                if ((p and 0xFF) > 20 || ((p shr 8) and 0xFF) > 20 || ((p shr 16) and 0xFF) > 20) {
                    if (++nonBlack >= 8) return false
                }
                x += stepX
            }
            y += stepY
        }
        return true
    }

    private fun pushJpeg(bmp: Bitmap) {
        try {
            val bos = ByteArrayOutputStream()
            bmp.compress(Bitmap.CompressFormat.JPEG, 88, bos)
            val b64 = Base64.encodeToString(bos.toByteArray(), Base64.NO_WRAP)
            webView.evaluateJavascript("window.loadCompareFrame('data:image/jpeg;base64,$b64')", null)
        } catch (e: Exception) { pushFail() }
    }

    private fun pushFail() {
        runOnUiThread { webView.evaluateJavascript("window.loadCompareFrame('')", null) }
    }

    private fun releasePlayer() {
        try { mediaPlayer?.stop() } catch (_: Exception) {}
        try { mediaPlayer?.vlcVout?.detachViews() } catch (_: Exception) {}
        try { mediaPlayer?.release() } catch (_: Exception) {}
        mediaPlayer = null
        try { libVLC?.release() } catch (_: Exception) {}
        libVLC = null
    }

    override fun onDestroy() { mqttBridge?.stop(); releasePlayer(); super.onDestroy() }
}
