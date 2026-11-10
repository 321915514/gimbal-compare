#!/usr/bin/env python3
"""下载指定 run 的 APK artifact（token 从 git credential fill 读，传输走 curl，不打印 token）"""
import json, os, subprocess, sys, zipfile

RUN = sys.argv[1] if len(sys.argv) > 1 else "42175121816"
REPO = "321915514/gimbal-compare"
OUT = os.path.join(os.environ["LOCALAPPDATA"], "Temp", "apk_run_%s" % RUN)
os.makedirs(OUT, exist_ok=True)


def tok():
    o = subprocess.run(["git", "credential", "fill"], input=b"protocol=https\nhost=github.com\n\n",
                       capture_output=True, env=dict(os.environ, GIT_TERMINAL_PROMPT="0"))
    for line in o.stdout.decode().splitlines():
        if line.startswith("password="):
            return line[9:]
    raise SystemExit("no token in credential store")


T = tok()
A = ["-H", "Authorization: Bearer " + T, "-H", "Accept: application/vnd.github+json",
     "-H", "User-Agent: hermes"]


def api(path, out=None):
    cmd = ["curl", "-sS", "-m", "90"] + A + ["https://api.github.com" + path]
    if out:
        subprocess.run(cmd + ["-o", out], check=True)
        return json.load(open(out, encoding="utf-8"))
    r = subprocess.run(cmd, capture_output=True, check=True)
    return json.loads(r.stdout.decode())


arts = api("/repos/%s/actions/runs/%s/artifacts" % (REPO, RUN))
name = None
for a in arts["artifacts"]:
    print("artifact:", a["name"], a["size_in_bytes"], "bytes", "expired" if a["expired"] else "ok")
    name = a["name"]

url = arts["artifacts"][0]["archive_download_url"]
z = os.path.join(OUT, name + ".zip")
print("下载 ->", z)
for i in range(1, 6):
    rc = subprocess.run(["curl", "-sSL", "-m", "600", "-o", z] + A + [url]).returncode
    if rc == 0 and os.path.exists(z) and os.path.getsize(z) > 1_000_000:
        break
    print("  第 %d 次失败(rc=%s, %s B)，重试" % (i, rc, os.path.getsize(z) if os.path.exists(z) else 0))
print("zip 大小", os.path.getsize(z))

with zipfile.ZipFile(z) as zf:
    zf.extractall(OUT)
apk = os.path.join(OUT, "app-debug.apk")
print("APK", apk, os.path.getsize(apk), "字节")
import hashlib
print("md5", hashlib.md5(open(apk, "rb").read()).hexdigest())
