# 最終結論：怎麼做出即時看 box score 與 play-by-play

> 兩輪獨立調查（2026-11-16、11-17）合併後的定論。所有數字都是實測。
> 細節見 [app-live-data.md](app-live-data.md)、[app-design.md](app-design.md)、[research.md](research.md)。

## 一句話

**可行。延遲 8~20 秒，跟 NBA 官方 App 同級，免費。**
唯一必須做的事：**部署一台中繼站。**

## 為什麼一定要中繼站

你的網頁不能直接打 NBA，有兩道牆：

| 牆 | 擋誰 | 瀏覽器能自己繞嗎 |
|---|---|---|
| **CORS 白名單** | 所有網頁 | ❌ **不可能**。實測只有 `Origin: https://www.nba.com` 拿得到許可，其他一律沒有，而瀏覽器不准 JS 偽造 Origin |
| **傳輸層指紋** | `curl`、Python urllib | 瀏覽器本身沒問題 |

中繼站在伺服器上跑，**伺服器沒有 CORS 這回事**，所以它抓得到；它再蓋章把資料轉給你的網頁。

```
你的網頁 ──fetch──► 中繼站 ──fetch──► cdn.nba.com
         ◄── 加上 Access-Control-Allow-Origin ──
```

## 架構：三個零件

| 零件 | 做什麼 | 狀態 |
|---|---|---|
| **① 中繼站** | 比賽中幫網頁去抓官方資料 | 程式寫好了，**還沒部署** |
| **② 網頁** | 顯示比分 / box score / 逐球 | ❌ 還沒做 |
| ③ GitHub Actions | 每天抓完整歷史存成 CSV | ✅ **已經在跑** |

③ 跟即時無關，它是資料倉庫。**GitHub 不能當中繼站** —— Actions 沒有對外網址、
Pages 只能放靜態檔，而且經過 git 傳遞最快也要 1~7 分鐘。

## 中繼站：兩種實作，挑一個

兩種都寫好也都實測過，程式完全等價（白名單、token、5~10 秒快取、304 省流量）。

| | **Node 版** | **Python 版** |
|---|---|---|
| 檔案 | [`proxy/`](../proxy/) | [`scripts/nba_proxy.py`](../scripts/nba_proxy.py) |
| 相依套件 | **零** | `curl_cffi` |
| 要包 Docker | ❌ 不用 | ✅ 要（[`deploy/cloudrun/`](../deploy/cloudrun/)） |
| 部署難度 | 一行指令 | build image → push → Cloud Run |
| 可跑在 | Vercel、Netlify、Cloud Run、VPS、家裡電腦 | Cloud Run、VPS、Fly.io、Railway、家裡電腦 |

**先試 Node 版**，它簡單得多。不通再換 Python 版 —— 那套已經完整，不會白做。

### 為什麼 Node 版可行（這是這輪最關鍵的發現）

原本以為只有 `curl_cffi` 偽裝得了指紋。實測推翻：

```
Node 原生 fetch，只給 Referer     HTTP 200   40,524B   內容完整
curl  完全相同的 header            HTTP 403
```

把 Node 送出的每一個標頭複製到 curl 上，**還是 403** —— 差異在傳輸層，不是標頭。
Azure 資料中心 IP 上也成立（GitHub Actions，四個端點全過，沒裝任何套件）。

## 延遲：實測 8~20 秒

在真實進行中的比賽量的（量法：現在時間 − 最後一個動作的發生時間，取最小值）：

| 比賽 | `cdn.nba.com` | ESPN |
|---|---|---|
| HOU@MIA Q4 | 17.8 秒 | 14.7 秒 |
| POR@MIN Q4 | 7.1 秒 | 44.5 秒 |
| POR@MIN Q4（16 輪） | 15.9 秒 | 9.5 秒 |
| ORL@BOS Q2 | 7.5 秒 | — |

**這是 NBA 自己的生產延遲**（記錄員輸入 → CDN），官方 App 讀的也是同一個端點，
所以誰都追不過它。差別在穩定度：官方平穩推進，ESPN 是突發式的（會卡住十幾秒再跳好幾筆）。

**所以用官方資料，不用 ESPN** —— 一樣快、欄位多（33 欄 vs 14 欄）、有精確投籃座標。

## 流量：一定要用條件式請求

每 10 秒抓一次 play-by-play，一場 3 小時 = 1,080 次 × 400 KB ≈ **200 MB**。手機不能這樣。

`cdn.nba.com` 支援 `If-Modified-Since`，沒變動就回 **304、0 bytes**。
兩個中繼站實作都已內建。前端這樣用：

```js
let lastMod = null;
async function poll(url) {
  const r = await fetch(url, lastMod ? { headers: { "If-Modified-Since": lastMod } } : {});
  if (r.status === 304) return null;            // 沒變，不用重畫
  lastMod = r.headers.get("Last-Modified");
  return r.json();
}
```

一場從 200 MB 降到幾 MB。

## 你現在要做的

```bash
cd /Users/wubinghan/Documents/NBA_Fantasy/proxy && npm i -g vercel && vercel --prod
```

部署完開 `https://你的網址/__selftest`：

| 回應 | 意思 | 下一步 |
|---|---|---|
| `upstreamStatus: 200` | ✅ 通了 | 把網址給我，我做網頁 |
| `403` | 那個平台的 IP 被擋 | 換 Cloudflare Workers，再不行用 Python 版 + Cloud Run |

**不用猜，三分鐘就知道。**

## 還沒驗證的

| 項目 | 風險 |
|---|---|
| Google Cloud / Vercel 的 IP 會不會被擋 | 🟡 目前證據顯示 `cdn.nba.com` **不擋**資料中心 IP（Azure 實測通過），只有 `stats.nba.com` 擋 —— 而中繼站用不到它 |
| Cloudflare Workers / Deno 的指紋 | 🟡 它們的 TLS stack 既不是 undici 也不是 libcurl，`/__selftest` 會告訴你 |
| 原生 App（iOS `URLSession` / Android `OkHttp`） | 🔴 沒驗證過，指紋類別跟 curl 接近，風險高。**做網頁比做原生 App 保險** |

## 長期風險

這是**未公開端點**，沒有文件、沒有 SLA、NBA 隨時可以改或擋
（有紀錄顯示 2026-06-16 就加過一次檢查，一批專案當時集體掛掉）。

沒有人拿爬來的端點上正式產品。自己看球沒問題；哪天要給別人用就換付費 API
（BallDontLie 約 $10~40/月、API-NBA 約 $15/月）。
