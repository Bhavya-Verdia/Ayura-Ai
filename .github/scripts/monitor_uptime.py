"""Uptime check for ayuraai.in, run by .github/workflows/monitor-uptime.yml.

Standard library only. Each check retries before it counts as down, because a
deploy restarts the API for about a minute and that is not an outage. Writes a
markdown report to $REPORT and exits 1 if anything is down.
"""
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

SITE = os.environ.get("SITE", "https://ayuraai.in")
SLOW_S = 10.0
ATTEMPTS, PAUSE_S = 3, 40


def fetch(path, method="GET", body=None):
    req = urllib.request.Request(SITE + path, method=method, data=body,
                                 headers={"Content-Type": "application/json", "User-Agent": "ayura-uptime-monitor",
                                          "Origin": SITE})
    t = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status, r.read(), r.headers.get("Content-Type", ""), time.monotonic() - t
    except urllib.error.HTTPError as e:
        return e.code, e.read(), e.headers.get("Content-Type", ""), time.monotonic() - t


def check_health():
    code, raw, _, secs = fetch("/api/health")
    if code != 200:
        return f"/api/health returned HTTP {code}"
    h = json.loads(raw)
    bad = [f"{k}={h.get(k)}" for k, want in (("status", "healthy"), ("mongodb", "connected"), ("chromadb", "connected"))
           if h.get(k) != want]
    if bad:
        return "/api/health reports " + ", ".join(bad)
    if secs > SLOW_S:
        return f"/api/health took {secs:.1f}s"
    return None


def check_frontend():
    for path in ("/", "/app.html"):
        code, _, _, secs = fetch(path)
        if code != 200:
            return f"{path} returned HTTP {code}"
    code, raw, _, _ = fetch("/app.html")
    m = re.search(rb'/assets/index-[\w-]+\.js', raw)
    if not m:
        return "/app.html has no entry script: the deployed frontend is broken"
    code, _, ctype, _ = fetch(m.group(0).decode())
    if code != 200 or "javascript" not in ctype:
        return f"entry script {m.group(0).decode()} returned HTTP {code} ({ctype})"
    return None


def check_auth_path():
    # A wrong password must be refused by the app, which proves the API, its
    # database and the login route all answer. The address cannot exist.
    body = json.dumps({"email": "uptime-monitor@example.com", "password": "not-a-real-password"}).encode()
    code, raw, _, _ = fetch("/api/auth/login", "POST", body)
    if code not in (401, 429):
        return f"login with a wrong password returned HTTP {code}, not 401: {raw[:160]!r}"
    code, _, _, _ = fetch("/api/profile/me", "PUT", b"{}")
    if code != 401:
        return f"an unauthenticated profile save returned HTTP {code}, not 401"
    return None


CHECKS = {"API health": check_health, "Frontend": check_frontend, "Login and profile routes": check_auth_path}


def main():
    lines, down = [], []
    for name, fn in CHECKS.items():
        problem = None
        for attempt in range(1, ATTEMPTS + 1):
            try:
                problem = fn()
            except Exception as e:
                problem = f"{type(e).__name__}: {e}"
            if not problem:
                break
            if attempt < ATTEMPTS:
                time.sleep(PAUSE_S)
        lines.append(f"- {'✅' if not problem else '🔴'} **{name}**" + (f": {problem}" if problem else ""))
        if problem:
            down.append(name)
    report = f"### {'All checks passing' if not down else 'DOWN: ' + ', '.join(down)}\n\n" + "\n".join(lines)
    print(report)
    if os.environ.get("REPORT"):
        open(os.environ["REPORT"], "w").write(report)
    return 1 if down else 0


if __name__ == "__main__":
    sys.exit(main())
