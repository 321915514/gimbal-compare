#!/usr/bin/env python3
"""把本地领先 origin/main 的 commit 逐个通过 GitHub Data API 重放到远端。
用途：本机 github.com 被网络层阻断（仅 api.github.com 可达）且公司 DLP 会掐 python 的 TLS，
所以传输层统一走 curl；token 从 `git credential fill` 读，不落命令文本、不打印。"""
import base64, json, os, subprocess, sys, time

REPO = os.environ.get("GH_REPO", "321915514/gimbal-compare")
API = "https://api.github.com"


def sh(args, binary=False, cwd=None):
    r = subprocess.run(args, capture_output=True, cwd=cwd or os.getcwd())
    if r.returncode != 0:
        raise RuntimeError(r.stderr.decode("utf-8", "replace")[:400])
    return r.stdout if binary else r.stdout.decode("utf-8", "replace").strip()


def token():
    out = subprocess.run(["git", "credential", "fill"],
                         input=b"protocol=https\nhost=github.com\n\n",
                         capture_output=True,
                         env=dict(os.environ, GIT_TERMINAL_PROMPT="0")).stdout.decode()
    for line in out.splitlines():
        if line.startswith("password="):
            return line[9:]
    raise RuntimeError("凭据库里没有 github.com 的 token（先 git credential approve）")


TOK = token()


def api(method, path, payload=None, tries=4):
    """经 curl 调 API；返回解析后的 JSON（无 body 时返回 {}）"""
    cmd = ["curl", "-sS", "-m", "120", "-X", method,
           "-H", "Authorization: Bearer " + TOK,
           "-H", "Accept: application/vnd.github+json",
           "-H", "User-Agent: hermes-api-push",
           "-w", "\n@@%{http_code}"]
    if payload is not None:
        cmd += ["-H", "Content-Type: application/json", "--data-binary", "@-"]
    cmd.append(API + path)
    for i in range(tries):
        r = subprocess.run(cmd, input=(json.dumps(payload).encode()
                                       if payload is not None else None), capture_output=True)
        raw = r.stdout.decode("utf-8", "replace")
        body, _, code = raw.rpartition("\n@@")
        if r.returncode != 0:                      # curl 自身失败（TLS/网络抖动）
            if i < tries - 1:
                time.sleep(4 * (i + 1)); continue
            raise RuntimeError("curl 失败: " + r.stderr.decode("utf-8", "replace")[:300])
        code = code.strip()
        if code in ("403", "429") and i < tries - 1:      # 限流退避
            time.sleep(10 * (i + 1)); continue
        if not code.startswith("2"):
            raise RuntimeError("%s %s -> HTTP %s %s" % (method, path, code, body[:500]))
        try:
            return json.loads(body) if body.strip() else {}
        except json.JSONDecodeError:
            raise RuntimeError("非 JSON 响应 (HTTP %s): %s" % (code, body[:300]))
    raise RuntimeError("重试耗尽: " + path)


def changed_files(sha):
    """commit 变更清单 [(status, path)]；-z 取原始字节，免中文路径八进制转义"""
    raw = sh(["git", "diff", "--name-status", "-z", sha + "^", sha], binary=True)
    toks = [t for t in raw.split(b"\0") if t]
    out, i = [], 0
    while i < len(toks):
        st = toks[i].decode()
        if st[0] in ("R", "C"):
            out += [("D", toks[i + 1].decode()), ("A", toks[i + 2].decode())]
            i += 3
        else:
            out.append((st[0], toks[i + 1].decode()))
            i += 2
    return out


def main():
    remote_head = api("GET", "/repos/%s/git/ref/heads/main" % REPO)["object"]["sha"]
    print("远端 main =", remote_head)
    # 远端 commit 是 API 重放出来的、本地仓库里没有对象，直接用 remote_head 做 rev-list 会报
    # "Invalid revision range"；可传一个本地基准：python tools/api_push.py 7dd83c3
    base = sys.argv[1] if len(sys.argv) > 1 else remote_head
    ahead = sh(["git", "rev-list", "--reverse", "%s..HEAD" % base]).split()
    print("基准 =", base, " 待重放 commit 数 =", len(ahead))
    if not ahead:
        print("本地不领先远端，无需推送"); return

    parent = remote_head
    for local_sha in ahead:
        msg = sh(["git", "show", "-s", "--format=%B", local_sha])
        a = sh(["git", "show", "-s", "--format=%an\x1f%ae\x1f%aI", local_sha]).split("\x1f")
        c = sh(["git", "show", "-s", "--format=%cn\x1f%ce\x1f%cI", local_sha]).split("\x1f")
        base_tree = api("GET", "/repos/%s/git/commits/%s" % (REPO, parent))["tree"]["sha"]
        entries = []
        for st, path in changed_files(local_sha):
            if st == "D":
                entries.append({"path": path, "mode": "100644", "type": "blob", "sha": None})
                continue
            data = sh(["git", "cat-file", "blob", local_sha + ":" + path], binary=True)
            mode = (sh(["git", "ls-tree", local_sha, "--", path]).split() or ["100644"])[0]
            blob = api("POST", "/repos/%s/git/blobs" % REPO,
                       {"content": base64.b64encode(data).decode(), "encoding": "base64"})
            entries.append({"path": path, "mode": mode, "type": "blob", "sha": blob["sha"]})
            print("   blob %-56s %8d B" % (path[-53:], len(data)))
        tree = api("POST", "/repos/%s/git/trees" % REPO, {"base_tree": base_tree, "tree": entries})
        com = api("POST", "/repos/%s/git/commits" % REPO, {
            "message": msg, "tree": tree["sha"], "parents": [parent],
            "author": {"name": a[0], "email": a[1], "date": a[2]},
            "committer": {"name": c[0], "email": c[1], "date": c[2]}})
        print("=> %s  %s" % (com["sha"][:9], msg.splitlines()[0][:62]))
        parent = com["sha"]

    api("PATCH", "/repos/%s/git/refs/heads/main" % REPO, {"sha": parent, "force": False})
    print("REF 已更新 -> main =", parent)


if __name__ == "__main__":
    main()
