// GimbalCompareActivity.kt —— G20 全屏显示页面 + libVLC 抓 RTSP 帧
// 现场只改 rtspUrl（config.js / gimbal_config.json），页面点「获取帧」→ 本类连 RTSP 抓一帧回传。
package com.example.annotation

import android.annotation.SuppressLint
import android.app.Activity
import android.graphics.Bitmap
import android.net.Uri
import android.os.Bundle
import android.util.Base64
import android.view.Gravity
import android.view.TextureView
import android.view.View
import android.webkit.JavascriptInterface
import android.webkit.WebChromeClient
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.FrameLayout
import org.videolan.libvlc.LibVLC
import org.videolan.libvlc.Media
import org.videolan.libvlc.MediaPlayer
import java.io.ByteArrayOutputStream

class GimbalCompareActivity : Activity() {

    private lateinit var webView: WebView
    private lateinit var rtspView: TextureView   // 隐藏的 RTSP 渲染目标（在 WebView 后面）
    private var libVLC: LibVLC? = null
    private var mediaPlayer: MediaPlayer? = null

    // 抓帧分辨率：与 H 标定时吊舱帧分辨率一致（改这里）
    private val GRAB_W = 1280
    private val GRAB_H = 720

    inner class Bridge {
        @JavascriptInterface
        fun grabFrame(rtspUrl: String) = runOnUiThread { grabRtspFrame(rtspUrl) }
    }

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        immersive()

        // TextureView（渲染 RTSP，抓帧用）在 WebView 后面
        rtspView = TextureView(this)
        rtspView.layoutParams = FrameLayout.LayoutParams(GRAB_W, GRAB_H, Gravity.CENTER)
        webView = WebView(this)
        webView.layoutParams = FrameLayout.LayoutParams(
            FrameLayout.LayoutParams.MATCH_PARENT, FrameLayout.LayoutParams.MATCH_PARENT)
        val root = FrameLayout(this)
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
    }

    /** 连 RTSP → play → 等第一帧 → TextureView 抓 Bitmap → JPEG base64 → 推回页面 */
    private fun grabRtspFrame(rtspUrl: String) {
        releasePlayer()
        try {
            val lv = LibVLC(this, arrayListOf(
                "--network-caching=1000", "--live-caching=500",
                "--drop-late-frames", "--skip-frames"))
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
                        rtspView.postDelayed({ grabAndPush(); releasePlayer() }, 700)
                    MediaPlayer.Event.EncounteredError -> { pushFail(); releasePlayer() }
                }
            }
            mp.play()
        } catch (e: Exception) {
            pushFail(); releasePlayer()
        }
    }

    private fun grabAndPush() {
        try {
            val bmp = rtspView.bitmap ?: run { pushFail(); return }
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

    private fun immersive() {
        window.decorView.systemUiVisibility = (View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY
                or View.SYSTEM_UI_FLAG_FULLSCREEN
                or View.SYSTEM_UI_FLAG_HIDE_NAVIGATION
                or View.SYSTEM_UI_FLAG_LAYOUT_STABLE
                or View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN
                or View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION)
    }

    override fun onResume() { super.onResume(); immersive() }
    override fun onDestroy() { releasePlayer(); super.onDestroy() }
}
