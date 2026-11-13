import json, sys, urllib.request
import websocket

targets = json.load(urllib.request.urlopen("http://127.0.0.1:9222/json"))
page = [t for t in targets if t["type"] == "page"][0]
ws = websocket.create_connection(page["webSocketDebuggerUrl"], timeout=20)
expr = sys.argv[1] if len(sys.argv) > 1 else "1"
ws.send(json.dumps({"id": 1, "method": "Runtime.evaluate",
                    "params": {"expression": expr, "returnByValue": True, "awaitPromise": True}}))
while True:
    msg = json.loads(ws.recv())
    if msg.get("id") == 1:
        r = msg.get("result", {}).get("result", {})
        print(json.dumps(r.get("value", r), ensure_ascii=False, indent=1))
        break
ws.close()
