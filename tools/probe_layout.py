import json, os, subprocess, sys, time, urllib.request
import websocket

URL = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8123/gimbal_compare.html"
EXPR = sys.argv[2] if len(sys.argv) > 2 else "1"
W = int(os.environ.get("VW", "753"))
H = int(os.environ.get("VH", "399"))
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
PORT = 9223

proc = subprocess.Popen([EDGE, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                         f"--remote-debugging-port={PORT}", "--user-data-dir=" + os.path.join(os.environ["TEMP"], "edge_probe"),
                         "--no-first-run", "about:blank"],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
try:
    tg = None
    for _ in range(40):
        time.sleep(0.5)
        try:
            tg = json.load(urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json"))
            if tg:
                break
        except Exception:
            pass
    ws = websocket.create_connection([t for t in tg if t["type"] == "page"][0]["webSocketDebuggerUrl"], timeout=60)
    mid = [0]

    def call(method, **params):
        mid[0] += 1
        ws.send(json.dumps({"id": mid[0], "method": method, "params": params}))
        while True:
            m = json.loads(ws.recv())
            if m.get("id") == mid[0]:
                return m.get("result", {})

    call("Emulation.setDeviceMetricsOverride", width=W, height=H, deviceScaleFactor=2.55, mobile=True)
    call("Page.enable")
    call("Page.navigate", url=URL)
    time.sleep(3)
    r = call("Runtime.evaluate", expression=EXPR, returnByValue=True, awaitPromise=True)
    print(json.dumps(r.get("result", {}).get("value", r), ensure_ascii=False, indent=1))
    if os.environ.get("SHOT"):
        d = call("Page.captureScreenshot", format="png")
        import base64
        open(os.environ["SHOT"], "wb").write(base64.b64decode(d["data"]))
        print("shot ->", os.environ["SHOT"])
finally:
    proc.terminate()
