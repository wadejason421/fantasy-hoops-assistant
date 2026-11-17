# proxy/ — 讓瀏覽器拿得到 NBA 官方即時資料

瀏覽器不能直接打 `cdn.nba.com`：CORS 會擋（實測從第三方網域 `fetch` 直接 `Failed to fetch`）。
這個代理在伺服器端抓（伺服器端沒有 CORS 這回事），再補上 `Access-Control-Allow-Origin` 轉回前端。

```
瀏覽器 ──fetch──► 你的代理 ──fetch──► cdn.nba.com
        ◄── 加上 CORS header ──
```

**零相依套件。** NBA 擋的是傳輸層指紋，而 JS runtime 的指紋被接受 ——
實測 Node 原生 `fetch` 只要帶 `Referer: https://www.nba.com/` 就 200，
住宅 IP 與 Azure 資料中心 IP 都成立。所以不需要 `curl_cffi`，也不需要能編譯原生套件的環境。

## 部署：挑一個

### Vercel（推薦 — 跑真正的 Node，指紋已實測可用）

```bash
npm i -g vercel
cd proxy && vercel --prod
```

得到 `https://<專案名>.vercel.app`。Hobby 方案免費。

### Cloudflare Workers（免費額度最大，但指紋未驗證）

```bash
npm i -g wrangler && wrangler login
cd proxy && wrangler deploy
```

得到 `https://nba-proxy.<你的名字>.workers.dev`。每天 10 萬次請求免費。

Workers 用的是 `workerd` 不是 Node，傳輸層指紋沒測過。部署後先打自我檢測：

```
https://你的網址/__selftest
```

`upstreamStatus: 200` 就是可用；`403` 代表 workerd 被擋，改用 Vercel。

## 怎麼用

部署完把 `https://cdn.nba.com` 換成你的代理網址，路徑原封不動：

```js
const BASE = "https://你的代理網址";

// 今日比賽 + 即時比分
const sb = await (await fetch(`${BASE}/static/json/liveData/scoreboard/todaysScoreboard_00.json`)).json();

// 單場即時 box score
const box = await (await fetch(`${BASE}/static/json/liveData/boxscore/boxscore_0022600244.json`)).json();

// 單場即時 play-by-play（含投籃 x/y 座標）
const pbp = await (await fetch(`${BASE}/static/json/liveData/playbyplay/playbyplay_0022600244.json`)).json();
```

回傳格式跟官方完全一樣，欄位說明見 [`doc/nba-api-usage.md`](../doc/nba-api-usage.md)。

## 省流量：條件式請求

比賽中每 10 秒抓一次 play-by-play，一場 3 小時就是 1,080 次 × 400 KB ≈ **200 MB**。
用手機看球這個量不能接受。

所以代理會轉送 `If-Modified-Since`：資料沒變就回 **304、0 bytes**。
實測 `cdn.nba.com` 支援這個（`If-None-Match` 無效，所以只轉 `If-Modified-Since`）。

前端這樣用：

```js
let lastMod = null;

async function poll(url) {
  const headers = lastMod ? { "If-Modified-Since": lastMod } : {};
  const r = await fetch(url, { headers });
  if (r.status === 304) return null;           // 沒變，不用重畫
  lastMod = r.headers.get("Last-Modified");    // 代理有 expose 這個 header
  return r.json();
}
```

這樣只有真正有新事件時才會傳資料，一場比賽的流量從 200 MB 降到幾 MB。

## 額度夠不夠

一場 3 小時的比賽、每 10 秒輪詢一次：

| | 一場 | 一個月（15 個比賽夜） |
|---|---|---|
| 請求數 | 約 3,200 | 約 48,000 |
| Vercel Hobby 額度 | 100 萬次/月 | **用掉 5%** |
| Cloudflare Workers 額度 | 10 萬次/**天** | **用掉 3%** |

兩邊都綽綽有餘。流量因為有 304，實際只有幾 MB。

> **Vercel Hobby 是「個人非商業用途」授權。** 自己看球、自己玩 fantasy 沒問題；
> 哪天要放廣告或收費就得升級 Pro（$20/月）。Cloudflare Workers 免費方案沒有這條限制。

## 白名單

**只開放四條路徑**，其餘一律 403：

| 路徑 | 快取 |
|---|---|
| `/static/json/liveData/scoreboard/todaysScoreboard_00.json` | 10 秒 |
| `/static/json/liveData/boxscore/boxscore_<10位數字>.json` | 10 秒 |
| `/static/json/liveData/playbyplay/playbyplay_<10位數字>.json` | 10 秒 |
| `/static/json/staticData/scheduleLeagueV2_32.json` | 1 小時 |

**不要拿掉白名單。** 沒有白名單它就是一個開放代理，會被別人拿去當跳板，
然後你的免費額度被吃光、網址被列入黑名單。

## 檔案

| 檔案 | 用途 |
|---|---|
| `_shared.js` | 白名單、轉發、CORS、快取。兩個平台共用 |
| `worker.js` + `wrangler.toml` | Cloudflare Workers 版本 |
| `api/nba.js` + `vercel.json` | Vercel 版本 |

## 注意

- `stats.nba.com`（進階數據 / hustle stats）**不在白名單**，因為資料中心 IP 會被丟包，
  放進去也抓不到。那些數據走 `scripts/advanced_stats.py` 自己算。
- 快取設 10 秒是刻意的：比賽中資料約 10~20 秒更新一次，再短只是浪費額度並且對 NBA 不禮貌。
