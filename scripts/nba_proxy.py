#!/usr/bin/env python3
"""讓 App 打得到 NBA 官方即時資料的中繼站。

為什麼需要它：`cdn.nba.com` 有兩道牆，各自擋住一種客戶端。

| 牆 | 誰中 | 能不能自己解 |
|---|---|---|
| CORS 白名單 | 瀏覽器 / 網頁 App | **不能**。實測只有 `Origin: https://www.nba.com` 拿得到
|            |                   | `access-control-allow-origin`，而瀏覽器不准偽造 Origin |
| TLS 指紋     | 原生 App、Node、Python、curl | 要能偽裝瀏覽器指紋的客戶端（curl_cffi） |

這支同時拆掉兩道：它用 curl_cffi 偽裝 Chrome 去抓（過 TLS 指紋），
再加上 `Access-Control-Allow-Origin: *` 回給你的 App（過 CORS）。

    你的 App  ──►  這支 proxy  ──►  cdn.nba.com
              8~20 秒的官方完整資料（33 欄 box score、精確投籃座標）

要跑在哪：**必須是能裝 curl_cffi 的環境** —— 一台 VPS、Fly.io / Railway / Render /
Cloud Run 的容器、或你家裡的機器。**不能是 Cloudflare Workers、Vercel Edge Function
或 Deno Deploy**：它們用自己的 TLS stack，裝不了原生函式庫，一樣會吃 403。
資料中心 IP 對 `cdn.nba.com` 是可以的（本 repo 已在 GitHub Actions 的 Azure IP 上驗證過），
但 `stats.nba.com` 不行 —— 所以這支只代理 cdn。

本機試跑：
    pip install curl_cffi
    python scripts/nba_proxy.py --port 8080
    curl -s localhost:8080/scoreboard | head -c 300
    curl -s localhost:8080/boxscore/0022600249 | head -c 300

部署到 Cloud Run：見 deploy/cloudrun/README.md。
聽哪個 port 由環境變數 PORT 決定（Cloud Run 會設它），--port 只是本機用的預設。

端點（都只是把官方的 JSON 原樣轉出來）：
    GET /scoreboard              今日所有比賽與即時比分
    GET /boxscore/<gameId>       單場 box score（33 欄）
    GET /playbyplay/<gameId>     單場逐球紀錄（含投籃座標）
    GET /schedule                整季賽程（檔案大，快取久一點）
    GET /healthz                 存活檢查

⚠️ 這支刻意**只允許上面那幾條路徑**，不是通用轉發器 —— 不然它會變成一台開放代理，
   任何人都能拿你的主機去打別的網站。要公開部署的話，至少再加一層 token 或限流。
"""

import argparse, hmac, json, os, re, sys, threading, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

try:
    from curl_cffi import requests as cffi
except ImportError:
    sys.exit("需要 curl_cffi：pip install curl_cffi")

CDN = "https://cdn.nba.com/static/json"
H = {"Referer": "https://www.nba.com/", "Origin": "https://www.nba.com",
     "Accept": "application/json, text/plain, */*"}
GAME_ID = re.compile(r"^\d{10}$")

# 設了 PROXY_TOKEN 就要求每個請求帶上它（header X-Proxy-Token 或 ?token=）。
# 這擋的是「陌生人拿你的網址當免費 NBA API 用」。注意它擋不掉「請求打進你的容器」——
# 要在 Google 那層就擋掉得用 IAM（--no-allow-unauthenticated），但那會讓 App 端複雜很多。
# 真正把費用封頂的是 --max-instances=1，見 deploy/cloudrun/README.md。
TOKEN = os.environ.get("PROXY_TOKEN", "")

# 路徑白名單：(正則, 轉去哪, 快取秒數)
# 快取是為了保護 NBA 也保護你 —— App 每 5 秒輪詢時不會每次都真的打出去。
ROUTES = [
    (re.compile(r"^/scoreboard$"),
     lambda m: f"{CDN}/liveData/scoreboard/todaysScoreboard_00.json", 5),
    (re.compile(r"^/boxscore/(\d{10})$"),
     lambda m: f"{CDN}/liveData/boxscore/boxscore_{m.group(1)}.json", 5),
    (re.compile(r"^/playbyplay/(\d{10})$"),
     lambda m: f"{CDN}/liveData/playbyplay/playbyplay_{m.group(1)}.json", 5),
    (re.compile(r"^/schedule$"),
     lambda m: f"{CDN}/staticData/scheduleLeagueV2_32.json", 3600),
]

_cache = {}
_lock = threading.Lock()
_session = cffi.Session(impersonate="chrome")


def fetch(url, ttl):
    """抓一次，TTL 內重複請求直接給快取。回傳 (status, body_bytes)。"""
    now = time.time()
    with _lock:
        hit = _cache.get(url)
        if hit and now - hit[0] < ttl:
            return 200, hit[1]
    try:
        r = _session.get(url, headers=H, timeout=25)
    except Exception as e:
        return 502, json.dumps(
            {"error": "upstream_unreachable", "detail": f"{type(e).__name__}: {e}"[:200]}
        ).encode()
    if r.status_code != 200:
        return r.status_code, json.dumps(
            {"error": "upstream_status", "status": r.status_code}).encode()
    with _lock:
        _cache[url] = (now, r.content)
    return 200, r.content


class Handler(BaseHTTPRequestHandler):
    server_version = "nba-proxy"

    def _send(self, status, body, ctype="application/json", ttl=5):
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        # 這兩行就是拆掉 CORS 那道牆的地方
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", f"public, max-age={ttl}")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, HEAD, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Access-Control-Max-Age", "86400")
        self.end_headers()

    def do_HEAD(self):
        self.do_GET()

    def _authorized(self):
        if not TOKEN:
            return True
        got = (self.headers.get("X-Proxy-Token")
               or parse_qs(urlparse(self.path).query).get("token", [""])[0])
        # 用 compare_digest，不要用 ==，避免逐字元比較洩漏 token 長度與內容
        return hmac.compare_digest(got, TOKEN)

    def do_GET(self):
        path = urlparse(self.path).path.rstrip("/") or "/"
        if path == "/healthz":
            return self._send(200, b'{"ok":true}', ttl=0)
        if not self._authorized():
            return self._send(401, json.dumps(
                {"error": "unauthorized", "detail": "缺少或錯誤的 X-Proxy-Token"}).encode(), ttl=0)
        if path == "/":
            return self._send(200, json.dumps({
                "endpoints": ["/scoreboard", "/boxscore/<gameId>",
                              "/playbyplay/<gameId>", "/schedule", "/healthz"]}).encode(), ttl=60)
        for pat, build, ttl in ROUTES:
            m = pat.match(path)
            if m:
                status, body = fetch(build(m), ttl)
                return self._send(status, body, ttl=ttl)
        self._send(404, json.dumps(
            {"error": "not_allowed", "detail": "只開放 / 列出的那幾條路徑"}).encode(), ttl=0)

    def log_message(self, fmt, *a):
        sys.stderr.write(f"{self.address_string()} {fmt % a}\n")


def main():
    ap = argparse.ArgumentParser()
    # Cloud Run 透過 PORT 環境變數告訴你要聽哪個 port，必須照辦。
    ap.add_argument("--port", type=int, default=int(os.environ.get("PORT", 8080)))
    ap.add_argument("--host", default="0.0.0.0")
    a = ap.parse_args()
    print(f"nba-proxy 聽在 http://{a.host}:{a.port}  （Ctrl-C 停止）", flush=True)
    print("  /scoreboard  /boxscore/<gameId>  /playbyplay/<gameId>  /schedule  /healthz",
          flush=True)
    print(f"  token 檢查：{'開啟' if TOKEN else '關閉（沒設 PROXY_TOKEN）'}", flush=True)
    ThreadingHTTPServer((a.host, a.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
