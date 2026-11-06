#!/usr/bin/env python3
"""API 推送后的独立回读校验：ref、提交链、tree 一致性、逐文件 blob sha、CI 状态。走 curl。"""
import json, os, subprocess, sys, urllib.parse

REPO = os.environ.get("GH_REPO", "321915514/gimbal-compare")
TOK = [l[9:] for l in subprocess.run(["git", "credential", "fill"],
        input=b"protocol=https\nhost=github.com\n\n", capture_output=True,
        env=dict(os.environ, GIT_TERMINAL_PROMPT="0")).stdout.decode().splitlines()
       if l.startswith("password=")]
if not TOK:
    sys.exit("凭据库里没有 github.com 的 token")


def get(path):
    r = subprocess.run(["curl", "-sS", "-m", "90", "-H", "Authorization: Bearer " + TOK[0],
                        "-H", "Accept: application/vnd.github+json", "-H", "User-Agent: hermes-verify",
                        "https://api.github.com" + path], capture_output=True)
    if r.returncode != 0:
        raise RuntimeError("curl: " + r.stderr.decode("utf-8", "replace")[:200])
    return json.loads(r.stdout.decode("utf-8", "replace"))


def local(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True).stdout.decode().strip()


ref = get("/repos/%s/git/ref/heads/main" % REPO)["object"]["sha"]
print("远端 main =", ref)
print("本地 HEAD  =", local("git rev-parse HEAD"))
print("本地 tree  =", local("git rev-parse HEAD^{tree}"))
print("远端 tree  =", get("/repos/%s/git/commits/%s" % (REPO, ref))["tree"]["sha"])

print("\n远端提交链（新→旧）:")
c, n = ref, 0
while n < 6:
    d = get("/repos/%s/git/commits/%s" % (REPO, c))
    print("  %s  %s  %s" % (d["sha"][:9], d["author"]["date"], d["message"].splitlines()[0][:52]))
    n += 1
    if not d["parents"]:
        break
    c = d["parents"][0]["sha"]

print("\n本地 vs 远端 逐文件 blob sha:")
files = local("git ls-tree -r --name-only HEAD").split("\n")
bad = 0
for f in files:
    lo = local('git rev-parse HEAD:"%s"' % f.replace('"', '\\"'))
    try:
        ro = get("/repos/%s/contents/%s" % (REPO, urllib.parse.quote(f)))["sha"]
    except Exception:
        ro = "缺失"
    if lo != ro:
        bad += 1
        print("  不一致: %-46s 本地 %s 远端 %s" % (f[:46], lo[:9], ro[:9] if ro != "缺失" else ro))
print("  共 %d 个文件，不一致 %d 个" % (len(files), bad))

print("\nCI / Actions:")
rs = get("/repos/%s/actions/runs?per_page=3" % REPO)["workflow_runs"]
for r in rs:
    print("  run #%-3s %-14s head=%s %s/%s  制品=%d  %s"
          % (r["run_number"], r["name"], r["head_sha"][:9], r["status"], r["conclusion"],
             r["artifacts_count"], r["html_url"]))
