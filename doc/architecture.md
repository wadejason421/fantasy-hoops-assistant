# 系統架構與 API 規格（最終版）

> 這份是**技術參考**：零件、介面、資料結構、部署步驟。
> 不重複論證過程 —— 「為什麼要這樣做」看 [conclusion.md](conclusion.md)，
> 實測數據看 [app-live-data.md](app-live-data.md)，中繼站部署細節看
> [../proxy/README.md](../proxy/README.md)。
>
> 更新於 2026-11-18。

## 一、全貌

```
┌─────────────┐   ①即時 (8~20秒)   ┌──────────┐            ┌──────────────┐
│  web/       │ ───────fetch──────► │ 中繼站    │ ──fetch──► │ cdn.nba.com  │
│  瀏覽器網頁  │ ◄──加 CORS header── │ (你部署)  │            │  liveData    │
└─────────────┘                     └──────────┘            └──────────────┘
       │                                                            ▲
       │ ②歷史 (隔天)                                                │ 每天 / 比賽時段
       ▼                                                            │
┌─────────────────────┐                              ┌──────────────────────┐
│ raw.githubusercontent│ ◄──────commit CSV────────────│  GitHub Actions      │
│  repo 的 data/       │                              │  fetch-nba/live-nba  │
└─────────────────────┘                              └──────────────────────┘
```

**兩條資料流互不相干**，共用同一個上游：

| | ① 即時 | ② 歷史 |
|---|---|---|
| 給誰用 | 網頁的「現在幾分」 | 賽後分析、整季趨勢、投籃圖 |
| 路徑 | 網頁 → 中繼站 → NBA | Actions → NBA → commit 成 CSV |
| 延遲 | **8~20 秒** | 隔天（實測排程會跳輪，見下） |
| 格式 | 官方原始 JSON | CSV（33 欄 box score、逐球含座標） |
| 要錢嗎 | 免費 | 免費 |

## 二、四個零件

| 零件 | 檔案 | 跑在哪 | 狀態 |
|---|---|---|---|
| **網頁** | [`web/index.html`](../web/index.html) | GitHub Pages / 任何靜態主機 | ✅ 做好了，本機實測過 |
| **中繼站（Node）** | [`proxy/`](../proxy/) | Vercel / Cloudflare Workers | ✅ 寫好了，**還沒部署** |
| **中繼站（Python）** | [`scripts/nba_proxy.py`](../scripts/nba_proxy.py) | Cloud Run / VPS / 家裡電腦 | ✅ 寫好了，備案 |
| **歷史倉庫** | [`.github/workflows/`](../.github/workflows/) + [`data/`](../data/) | GitHub Actions | ✅ **已經在跑** |

兩種中繼站**介面完全相同**，網頁指到哪一個都能跑，不用改程式。

## 三、中繼站 API 規格

這是整個系統唯一的介面。網頁只認得這四條路徑。

### 端點

| 路徑 | 回什麼 | 快取 |
|---|---|---|
| `GET /static/json/liveData/scoreboard/todaysScoreboard_00.json` | 今日所有比賽 + 即時比分 | 10 秒 |
| `GET /static/json/liveData/boxscore/boxscore_<gameId>.json` | 單場 box score，33 欄 | 10 秒 |
| `GET /static/json/liveData/playbyplay/playbyplay_<gameId>.json` | 單場逐球，含投籃座標 | 10 秒 |
| `GET /static/json/staticData/scheduleLeagueV2_32.json` | 整季賽程 | 3600 秒 |

`<gameId>` 必須是 10 位數字（例 `0022600245`），從 scoreboard 拿。
**路徑是白名單比對，不是轉發任意網址** —— 否則它會變成開放代理。

Python 版另外接受簡寫 `/scoreboard`、`/boxscore/<id>`、`/playbyplay/<id>`、`/schedule`、
`/healthz`，內容相同。網頁用上面的原樣路徑，因為兩邊都支援。

### 請求標頭

| 標頭 | 何時要帶 |
|---|---|
| `X-Proxy-Token: <token>` | 中繼站有設 `PROXY_TOKEN` 時。也可以用 `?token=` |
| `If-Modified-Since: <上次的 Last-Modified>` | 建議。沒變動時回 304、0 bytes |

### 回應標頭

| 標頭 | 意思 |
|---|---|
| `Access-Control-Allow-Origin: *` | 拆掉 CORS 那道牆的就是這一行 |
| `Access-Control-Expose-Headers: Last-Modified, X-Upstream-Status` | 不 expose 的話前端讀不到下面兩個 |
| `Last-Modified` | 下次請求原樣放進 `If-Modified-Since` |
| `X-Upstream-Status` | `cdn.nba.com` 回的狀態。**診斷關鍵** |

### 狀態碼對照

| 看到 | 意思 | 怎麼辦 |
|---|---|---|
| `200` | 正常 | — |
| `304` | 資料沒變，body 是空的 | 沿用上次的資料 |
| `401` | token 不對或沒帶 | 檢查前端設定 |
| `403` | 路徑不在白名單 | 用上表那四條 |
| `502` + `X-Upstream-Status: 403` | **中繼站好的，但 NBA 擋了它的 IP** | 換個地方跑中繼站，程式不用改 |
| `502` 其他 | 中繼站連不到 NBA | 看中繼站的 log |

最後兩列是最容易搞混的：**兩種 403 完全不同**。網頁會分開顯示。

## 四、資料結構（網頁實際用到的欄位）

回來的就是 `cdn.nba.com` 的原始 JSON，中繼站不改內容。完整欄位見
[nba-api-usage.md](nba-api-usage.md)。

### scoreboard

```jsonc
{ "scoreboard": {
    "gameDate": "2026-11-17",
    "games": [{
      "gameId": "0022600245",
      "gameStatus": 1,              // 1=未開始 2=進行中 3=已結束
      "gameStatusText": "Final",    // 進行中會是 "2nd Qtr" 之類
      "period": 4,
      "gameClock": "PT05M12.00S",   // ISO 8601 duration，要自己轉 5:12
      "awayTeam": { "teamTricode": "NYK", "score": 111 },
      "homeTeam": { "teamTricode": "TOR", "score": 102 }
    }]
} }
```

### boxscore

```jsonc
{ "game": {
    "gameStatusText": "Final",
    "arena": { "arenaName": "Scotiabank Arena" },
    "awayTeam": {
      "teamTricode": "NYK", "score": 111,
      "periods": [{ "score": 23 }, { "score": 31 }],     // 單節比分
      "players": [{
        "name": "Jalen Brunson",
        "starter": "1",            // 字串 "1"/"0"，不是布林
        "played":  "1",            // ⚠️ 整張名單都是 "1"，不能用它判斷有沒有上場
        "statistics": {
          "minutes": "PT34M26.00S", // 0 分鐘＝沒上場，用這個判斷
          "points": 31, "reboundsTotal": 5, "assists": 5,
          "steals": 0, "blocks": 1, "turnovers": 2,
          "fieldGoalsMade": 11, "fieldGoalsAttempted": 22,
          "threePointersMade": 3, "threePointersAttempted": 9,
          "freeThrowsMade": 6, "freeThrowsAttempted": 6,
          "plusMinusPoints": 7
          // …共 33 項，另有禁區得分、快攻得分、被封阻、製造犯規等
        }
      }]
    },
    "homeTeam": { /* 同上 */ }
} }
```

> ⚠️ 踩過的坑：`played` 對整張名單都是 `"1"`，用它過濾會把 DNP 的球員也列出來
> （全 0、0:00）。要用 `minutes` 判斷。

### playbyplay

```jsonc
{ "game": { "actions": [{
    "actionNumber": 320,
    "period": 4,
    "clock": "PT00M36.30S",
    "teamTricode": "NYK",
    "description": "M. Bridges 25' 3PT (17 PTS) (L. Shamet 1 AST)",
    "scoreAway": "111", "scoreHome": "102",
    "isFieldGoal": 1,
    "shotResult": "Made",          // "Made" / "Missed"
    "shotDistance": 25.7,
    "x": 4.22, "y": 95.96,         // 精確投籃座標（ESPN 沒有）
    "descriptor": "pullup"         // step back / driving / fadeaway…
}] } }
```

`actions` 是**附加式**的：每次輪詢只會在尾端長出新的。網頁就靠這點只插新項目，
不整塊重畫，捲動位置才不會跳掉。

## 五、網頁

[`web/index.html`](../web/index.html) —— 單一檔案、零相依、零建置，丟任何靜態主機就能跑。

| 功能 | 做法 |
|---|---|
| 設定中繼站網址與 token | 存在 `localStorage`，第一次開會提示 |
| 今日比賽列表 | 每 10 秒輪詢 scoreboard，進行中的顯示 `Q4 5:12` 並標紅 |
| Box Score 分頁 | 先發在上、替補灰字、沒上場的不列；單節比分在隊名旁 |
| 逐球分頁 | 最新在上；進球綠、沒進灰、附投籃距離；只插新項目 |
| 更新指示 | 右上角 `⟳ 10s` 倒數，更新瞬間閃一下 |
| 失敗處理 | 連續 3 次失敗顯示「連線中斷」並退避到 60 秒 |
| 深淺色 | 跟隨系統，可手動切換 |

輪詢間隔跟中繼站的快取都是 10 秒 —— 設更短只會打到快取，沒有意義。

## 六、從零到跑起來

| 步 | 做什麼 | 驗收 |
|---|---|---|
| 1 | 部署中繼站（[proxy/README.md](../proxy/README.md)，Vercel 一行指令） | 開 `https://你的網址/` 看到 JSON 的端點列表 |
| 2 | **立刻測上游** `.../liveData/scoreboard/todaysScoreboard_00.json` | 回 200。若 `X-Upstream-Status: 403` → 那個平台的 IP 被擋，換地方 |
| 3 | 把 `web/index.html` 丟 GitHub Pages（或本機 `python3 -m http.server`） | 頁面打得開 |
| 4 | 在頁面的「設定」填中繼站網址（有 token 就一起填），存檔 | 看到今日比賽列表 |
| 5 | `live-nba.yml` / `fetch-nba.yml` 已在 `main` 上跑 | repo 的 `data/` 每天長大 |

本機整條路一次跑起來：

```bash
PORT=8099 PROXY_TOKEN=test python3 scripts/nba_proxy.py
```

```bash
cd web && python3 -m http.server 8100
```

然後開 `http://127.0.0.1:8100/`，設定填 `http://127.0.0.1:8099` 和 `test`。

## 七、歷史資料那條

跟即時無關，是獨立的倉庫管線。

| workflow | 排程 | 做什麼 |
|---|---|---|
| [`live-nba.yml`](../.github/workflows/live-nba.yml) | 比賽時段每 15 分鐘 | 連進行中的比賽也抓 |
| [`fetch-nba.yml`](../.github/workflows/fetch-nba.yml) | 每天 08:23 UTC | 收尾，補齊原始 JSON 與壓縮檔 |

產出在 `data/`，格式見 [data/README.md](../data/README.md)。

> ⚠️ **實測：GitHub 的排程會大量跳輪。** 2026-11-17 夜間設定約 36 輪，實際只跑了 3 輪
> （23:42、04:02、05:32 UTC），間隔約 90 分鐘。所以這條路**不能當即時用**，
> 它的工作是「不要讓歷史消失」。即時一律走中繼站。

## 八、已驗證與未驗證

| 項目 | 狀態 |
|---|---|
| 網頁 → Python 中繼站 → NBA 全鏈路 | ✅ 本機實測：5 場比賽、21 列 box score、548 筆逐球、零 JS 錯誤 |
| 兩種中繼站介面一致 | ✅ Python 版已加上原樣路徑與 `X-Upstream-Status` |
| Node 原生 fetch 打得到 `cdn.nba.com` | ✅ 只帶 Referer 就 200 |
| 官方 feed 延遲 7~18 秒 | ✅ 四輪實測 |
| CORS 是 Origin 白名單 | ✅ 實測四種 origin |
| **網頁 → Node 中繼站** | ❌ Node 版還沒部署，沒測過 |
| **Vercel / Cloudflare 的 IP 會不會被擋** | ❌ 部署後第一件要測的事 |
| **Cloud Run 的 Docker 映像** | ❌ 沙箱憑證限制，沒建成功 |
| **進行中比賽的畫面** | ❌ 實測時比賽都結束了，只驗證過 Final 狀態的資料 |
