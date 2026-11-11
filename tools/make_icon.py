# -*- coding: utf-8 -*-
"""由 icon_1_192.png 生成 adaptive icon：绿底满铺 + 前景 S 标(透明)
   输出:
     res/values/colors.xml              ic_launcher_bg 颜色
     res/mipmap-anydpi-v26/ic_launcher.xml   adaptive-icon
     res/mipmap-<d>/ic_launcher_foreground.png  108dp 画布，标记约 56%（安全区）
     res/mipmap-<d>/ic_launcher.png     旧系统/通知用满铺方图（标记约 74%）
"""
import os
from PIL import Image

SRC = r"C:\Users\Qi\Downloads\icon_1105\icon_1105\icon_1_192.png"
ROOT = r"C:\Users\Qi\gimbal-compare\app\src\main\res"
DENS = [("ldpi", 0.75), ("mdpi", 1.0), ("hdpi", 1.5), ("xhdpi", 2.0), ("xxhdpi", 3.0), ("xxxhdpi", 4.0)]

im = Image.open(SRC).convert("RGB")
W, H = im.size
px = im.load()
bg = px[2, 2]
print("源图 %dx%d 角点底色 RGB=%s" % (W, H, bg))

# 1) 抠背景 -> 前景 RGBA（按与底色的最大通道差做软边）
rgba = Image.new("RGBA", (W, H))
out = rgba.load()
tol_hard, tol_soft = 26, 60
for y in range(H):
    for x in range(W):
        r, g, b = px[x, y]
        d = max(abs(r - bg[0]), abs(g - bg[1]), abs(b - bg[2]))
        if d <= tol_hard:
            a = 0
        elif d >= tol_soft:
            a = 255
        else:
            a = int(255 * (d - tol_hard) / (tol_soft - tol_hard))
        out[x, y] = (r, g, b, a)

bbox = rgba.split()[3].point(lambda v: 255 if v > 128 else 0).getbbox()
print("标记外接框 bbox=%s  尺寸=%dx%d" % (bbox, bbox[2] - bbox[0], bbox[3] - bbox[1]))
mark = rgba.crop(bbox)

def place(canvas_px, ratio, bgless=True):
    """把标记等比缩放到 canvas*ratio，居中放回 canvas"""
    side = int(round(canvas_px * ratio))
    mw, mh = mark.size
    s = side / max(mw, mh)
    nm = mark.resize((max(1, int(mw * s)), max(1, int(mh * s))), Image.LANCZOS)
    if bgless:
        cv = Image.new("RGBA", (canvas_px, canvas_px), (0, 0, 0, 0))
    else:
        cv = Image.new("RGBA", (canvas_px, canvas_px), bg + (255,))
    cv.paste(nm, ((canvas_px - nm.width) // 2, (canvas_px - nm.height) // 2), nm)
    return cv

def mkdir(p):
    os.makedirs(p, exist_ok=True)

for name, k in DENS:
    d = os.path.join(ROOT, "mipmap-" + name)
    mkdir(d)
    # 108dp 前景：标记占 56%（落在 66dp 圆形安全区内，圆/方遮罩都不切角）
    fg = place(int(round(108 * k)), 0.56)
    fg.save(os.path.join(d, "ic_launcher_foreground.png"))
    # 旧系统满铺方图（36/48/72/96/144/192 同档）：标记占 74%
    lg = place(int(round(48 * k)), 0.74, bgless=False).convert("RGB")
    lg.save(os.path.join(d, "ic_launcher.png"))
    print("  %-8s 前景 %dpx  方图 %dpx" % (name, fg.width, lg.width))

md = os.path.join(ROOT, "mipmap-anydpi-v26")
mkdir(md)
with open(os.path.join(md, "ic_launcher.xml"), "w", encoding="utf-8", newline="\n") as f:
    f.write('<?xml version="1.0" encoding="utf-8"?>\n'
            '<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">\n'
            '    <background android:drawable="@color/ic_launcher_bg"/>\n'
            '    <foreground android:drawable="@mipmap/ic_launcher_foreground"/>\n'
            '</adaptive-icon>\n')

vd = os.path.join(ROOT, "values")
mkdir(vd)
hexc = "#FF%02X%02X%02X" % bg
with open(os.path.join(vd, "colors.xml"), "w", encoding="utf-8", newline="\n") as f:
    f.write('<?xml version="1.0" encoding="utf-8"?>\n<resources>\n'
            '    <color name="ic_launcher_bg">%s</color>\n</resources>\n' % hexc)

print("adaptive xml + colors.xml 写好，底色 %s" % hexc)
