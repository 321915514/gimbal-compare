#!/usr/bin/env python3
"""直接 curl 下载 run 的 APK artifact（后台跑，避免前台超时）"""
import json, os, subprocess, sys, zipfile

REPO = "321915514/gimbal-compare"
RUN = sys.argv[1]
OUT = os.path.join(os.environ["LOCALAPPDATA"], "Temp", "apk_run_%s" % RUN)
os.makedirs(OUT, exist_ok=True)


def tok():
    o = subprocess.run(["git", "credential", "fill"], input=b"protocol=https\nhost=github.com\n\n",
                       capture_output=True, env=dict(os.environ, GIT_TERMINAL_PROMPT="0"))
    for line in o.stdout.decode().splitlines():
        if line.startswith("password="):
            return line[9:]
    raise SystemExit("no token")


T = tok()
A = ["-H", "Authorization: Bearer " + T, "-H", "Accept: application/vnd.github+json",
     "-H", "User-Agent: hermes"]
r = subprocess.run(["curl", "-sS", "-m", "90"] + A +
                   ["https://api.github.com/repos/%s/actions/runs/%s/artifacts" % (REPO, RUN)],
                   capture_output=True, check=True)
arts = json.loads(r.stdout.decode())["artifacts"]
for a in arts:
    print("artifact:", a["name"], a["size_in_bytes"], "bytes", "expired" if a["expired"] else "ok")
a = arts[0]
z = os.path.join(OUT, "apk.zip")
print("download ->", z)
subprocess.run(["curl", "-sSL", "--retry", "5", "--retry-delay", "3", "-m", "1200", "-o", z] + A +
               [a["archive_download_url"]], check=True)
print("bytes:", os.path.getsize(z))
with zipfile.ZipFile(z) as zf:
    print("entries:", zf.namelist())
    zf.extractall(OUT)
for f in os.listdir(OUT):
    print("file:", f, os.path.getsize(os.path.join(OUT, f)))
