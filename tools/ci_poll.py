#!/usr/bin/env python3
"""轮询 GitHub Actions：按 SHA 找最新 run，输出状态；完了取 artifact"""
import json, subprocess, sys, time, os

REPO = "321915514/gimbal-compare"
SHA = sys.argv[1] if len(sys.argv) > 1 else ""


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


def api(path):
    r = subprocess.run(["curl", "-sS", "-m", "90"] + A + ["https://api.github.com" + path],
                       capture_output=True, check=True)
    return json.loads(r.stdout.decode())


runs = api("/repos/%s/actions/runs?per_page=10" % REPO)["workflow_runs"]
hit = [r for r in runs if r["head_sha"].startswith(SHA[:7])] if SHA else runs[:1]
if not hit:
    print("no run for", SHA, "| latest:", runs[0]["head_sha"][:7], runs[0]["status"], runs[0]["conclusion"])
    sys.exit(0)
r = hit[0]
print("run=%s sha=%s status=%s conclusion=%s workflow=%s" % (r["id"], r["head_sha"][:7], r["status"], r["conclusion"], r["name"]))
print("url=%s" % r["html_url"])
