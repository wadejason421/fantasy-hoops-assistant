# Research — NBA 官方即時數據 API 實測記錄

> 這是**完整的調查過程記錄**：測了什麼、怎麼失敗、為什麼失敗、怎麼解決。
> 只想知道怎麼用，看 [nba-api-usage.md](nba-api-usage.md)。

實測日期 **2026-11-16**，標的 **2026-11-15 雷霆 @ 國王**（OKC 125 - SAC 103，Final）。
所有結果都是從這台 Mac 實際發請求測出來的。

舊的 Yahoo Fantasy 設計研究已移到 [archive/doc/](../archive/doc/)。其中
[03-data-sources.md](../archive/doc/03-data-sources.md) 的結論是「NBA 官方 403，改用 ESPN」
—— 那個結論在 Fantasy 主線上仍然成立，但這次找到了官方那條路的關鍵原因和繞過方式。

---

## 一、先講結論

| 問題 | 答案 |
|---|---|
| 官方有 API 嗎？ | **有**。`nba_api` 包的就是官方介面，沒有公開文件但真實存在 |
| 資料完整嗎？ | **非常完整**。傳統 box score、進階 box score、play-by-play（含投籃座標）、hustle stats 全都有 |
| 從這台機器打得通嗎？ | **原生 curl / Python 打不通**（cdn 403、stats.nba.com TLS 握手逾時）→ 直接用 `nba_api` 會失敗 |
| 有解嗎？ | **有，已實測成功**。`curl_cffi` + `impersonate="chrome"` 全部 200，`nba_api` 也能原封不動用（見第五節） |
| 那剛才的數據怎麼抓到的？ | **用真實瀏覽器**（Chrome）從 `nba.com` 頁面裡 `fetch()`。同一台機器、同一個 IP，瀏覽器通、curl 不通 |
| 所以是什麼在擋？ | **不是 IP 封鎖，是 client 指紋**（TLS/JA3 + header 組合）。Akamai 認得出 curl 和 Python urllib |

---

## 二、怎麼找 game id

官方 game id 不是 ESPN 的 id。11/15 雷霆 @ 國王：

| 來源 | ID |
|---|---|
| NBA 官方 | `0022600244` |
| ESPN | `401909993` |

格式 `00` + `2`(regular season) + `26`(season 2026-27) + `00244`(第幾場)。

查法 — 整季賽程（3.2 MB，一次抓完離線查）：

```
https://cdn.nba.com/static/json/staticData/scheduleLeagueV2_32.json
```

結構：`leagueSchedule.gameDates[].games[]`，每場有 `gameId`、`gameDateTimeEst`、
`homeTeam/awayTeam.teamTricode`、`score`、`gameStatusText`。

當天比賽（含即時比分，比賽中會動）：

```
https://cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_00.json
```

---

## 三、端點實測總表（GameID=0022600244）

### A. liveData — 比賽中即時更新，約 5~15 秒延遲，**這是即時數據要用的**

| 端點 | 結果 | 內容 |
|---|---|---|
| `cdn.nba.com/static/json/liveData/boxscore/boxscore_0022600244.json` | ✅ 200，40 KB | 完整 box score + 單節比分 + 場館/觀眾數/裁判 |
| `cdn.nba.com/static/json/liveData/playbyplay/playbyplay_0022600244.json` | ✅ 200，418 KB | **590 筆** play-by-play，含投籃 x/y 座標 |

### B. stats.nba.com — 賽後統計，功能最多但比賽中更新較慢

| 端點 | 結果 | 內容 |
|---|---|---|
| `boxscoretraditionalv3` | ✅ 200，16.8 KB | 傳統 box score（JSON 物件格式，好解） |
| `boxscoreadvancedv3` | ✅ 200，19.3 KB | 進階：ORtg/DRtg/TS%/USG%/PACE/EFG% |
| `boxscoretraditionalv2` | ✅ 200，5.3 KB | 舊版 `resultSets` 格式，24 名球員 + 2 隊 + 先發/替補分組 |
| `playbyplayv3` | ✅ 200，227 KB | **509 筆**（比 liveData 少 81 筆，少的是換人/暫停等非比賽動作） |
| `hustlestatsboxscore` | ✅ 200，4.6 KB | 22 名球員：封阻投籃、撥球、掩護助攻、卡位、救球 |
| `playbyplayv2` | ❌ 回 `{}` | **已失效**，改用 v3 |
| `winprobabilitypbp` | ❌ 500 | 壞了 |

### C. ESPN — 免認證、curl 直接可用，備援首選

| 端點 | 結果 | 內容 |
|---|---|---|
| `site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates=20261115` | ✅ 200 | 當日所有比賽 + event id |
| `site.api.espn.com/.../summary?event=401909993` | ✅ 200，440 KB | box score + 488 筆 plays + 傷病 + 賠率 + 勝率曲線 |
| `sports.core.api.espn.com/v2/sports/basketball/leagues/nba/events/{id}/competitions/{id}/plays?limit=1000` | ✅ 200，904 KB | 488 筆 play-by-play，含 `probability`（即時勝率） |

---

## 四、官方 liveData 的欄位有多完整

### 球員 box score — 每人 33 個欄位

```
minutes  points  assists  steals  blocks  blocksReceived  turnovers
fieldGoalsMade/Attempted/Percentage
threePointersMade/Attempted/Percentage
twoPointersMade/Attempted/Percentage
freeThrowsMade/Attempted/Percentage
reboundsOffensive/Defensive/Total
foulsPersonal/Offensive/Technical/Drawn
plus  minus  plusMinusPoints
pointsFastBreak  pointsInThePaint  pointsSecondChance  pointsFromTurnovers
```

注意：`blocksReceived`（被封阻）、`foulsDrawn`（製造犯規）、`plus`/`minus` 分開給，
這些是 ESPN **沒有**的。球隊層級有 61 個欄位。

`minutes` 是 ISO 8601 duration（`PT27M21.00S`），要自己轉換。

### play-by-play — 每筆 34 個欄位

```
actionNumber  orderNumber  clock  timeActual  period  periodType
teamId  teamTricode  personId  playerName  playerNameI
actionType  subType  descriptor  qualifiers
x  y  xLegacy  yLegacy  shotDistance  side        ← 投籃座標
isFieldGoal  shotResult  pointsTotal
scoreHome  scoreAway  possession
assistPersonId  assistPlayerNameInitial  assistTotal
description  personIdsFilter  edited  isTargetScoreLastPeriod
```

實際一筆：

```json
{
  "actionNumber": 29, "actionType": "3pt", "subType": "Jump Shot",
  "descriptor": "step back", "clock": "PT09M12.00S", "period": 1,
  "teamTricode": "OKC", "playerNameI": "K. Williams",
  "shotDistance": 26.84, "shotResult": "Made", "side": "left",
  "x": 33.39, "y": 62.18, "xLegacy": -61, "yLegacy": 261,
  "assistPlayerNameInitial": "I. Hartenstein", "assistTotal": 1,
  "scoreAway": "11", "scoreHome": "4",
  "description": "K. Williams 26' 3PT step back (3 PTS) (I. Hartenstein 1 AST)"
}
```

有 `x/y` 座標就能自己畫投籃分佈圖，不需要另外打 `shotchartdetail`。

### 抓到的完整 box score（驗證用）

Golden 1 Center, Sacramento ｜ 觀眾 13,021 ｜ 132 分鐘
裁判：Justin Van Duyne, Tre Maddox, Dannica Baroody
單節（SAC）：24 / 26 / 30 / 23

| 隊 | 球員 | MIN | PTS | FG | 3P | FT | REB | AST | STL | BLK | TO | PF | +/- |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| OKC | Shai Gilgeous-Alexander | 29:33 | 37 | 13-20 | 4-5 | 7-7 | 2 | 2 | 0 | 0 | 0 | 1 | +21 |
| OKC | Aday Mara | 25:32 | 16 | 8-11 | 0-0 | 0-0 | 13 | 3 | 0 | 0 | 4 | 4 | +8 |
| OKC | Ajay Mitchell | 27:21 | 14 | 6-14 | 1-4 | 1-1 | 3 | 5 | 2 | 0 | 1 | 3 | +16 |
| OKC | Jared McCain | 30:05 | 12 | 3-12 | 1-8 | 5-6 | 1 | 1 | 2 | 0 | 1 | 0 | +9 |
| OKC | Alex Caruso | 18:28 | 11 | 3-6 | 1-3 | 4-4 | 2 | 3 | 4 | 1 | 3 | 1 | +21 |
| OKC | Kenrich Williams | 18:48 | 10 | 4-5 | 2-3 | 0-0 | 1 | 2 | 2 | 0 | 0 | 1 | +19 |
| OKC | Nique Clifford | 23:51 | 9 | 3-4 | 0-1 | 3-4 | 3 | 0 | 1 | 0 | 0 | 3 | +4 |
| OKC | Nikola Topić | 13:28 | 8 | 4-6 | 0-1 | 0-0 | 0 | 0 | 0 | 0 | 2 | 3 | -12 |
| OKC | Micah Peavy | 13:21 | 5 | 1-6 | 1-4 | 2-4 | 3 | 1 | 1 | 1 | 0 | 1 | -1 |
| OKC | Isaiah Hartenstein | 18:11 | 3 | 1-1 | 0-0 | 1-2 | 11 | 2 | 0 | 0 | 1 | 1 | +12 |
| OKC | Bennett Stirtz | 17:28 | 0 | 0-3 | 0-2 | 0-0 | 1 | 2 | 2 | 0 | 0 | 2 | +12 |
| OKC | Brooks Barnhizer | 3:53 | 0 | 0-0 | 0-0 | 0-0 | 0 | 0 | 1 | 0 | 0 | 0 | +1 |
| SAC | Darius Acuff Jr. | 32:39 | 26 | 10-25 | 3-10 | 3-4 | 0 | 6 | 0 | 0 | 9 | 1 | -24 |
| SAC | Malik Monk | 28:46 | 14 | 6-13 | 1-7 | 1-1 | 1 | 10 | 1 | 0 | 2 | 0 | -15 |
| SAC | Daeqwon Plowden | 23:59 | 13 | 4-6 | 3-5 | 2-2 | 2 | 1 | 1 | 0 | 2 | 2 | -9 |
| SAC | Leaky Black | 29:09 | 12 | 4-5 | 4-5 | 0-0 | 9 | 2 | 4 | 1 | 2 | 6 | -7 |
| SAC | Domantas Sabonis | 29:29 | 11 | 3-6 | 0-2 | 5-6 | 13 | 3 | 0 | 0 | 1 | 4 | -10 |
| SAC | Dylan Cardwell | 19:04 | 10 | 5-6 | 0-1 | 0-3 | 6 | 2 | 0 | 0 | 0 | 3 | -22 |
| SAC | Emanuel Sharp | 21:04 | 9 | 3-9 | 1-5 | 2-2 | 0 | 2 | 2 | 0 | 2 | 5 | -6 |
| SAC | Keegan Murray | 21:06 | 6 | 2-9 | 2-5 | 0-0 | 1 | 0 | 0 | 1 | 1 | 0 | -22 |
| SAC | Mason Plumlee | 5:22 | 2 | 0-0 | 0-0 | 2-2 | 0 | 0 | 0 | 1 | 2 | 1 | 0 |
| SAC | Alex Karaban | 29:22 | 0 | 0-3 | 0-3 | 0-0 | 5 | 1 | 1 | 0 | 0 | 2 | +5 |

---

## 五、封鎖的真相：兩個主機兩種防護

同一台 Mac、同一個網路、同一個 URL：

| 客戶端 | header | 結果 |
|---|---|---|
| Chrome（nba.com 頁面裡 `fetch()`） | 瀏覽器自帶 | ✅ **200** |
| `curl` + 完整瀏覽器 UA | UA / Referer / Origin 都給 | ❌ **403** Akamai Access Denied |
| Python `urllib` + `nba_api` 的完整 header 組 | UA / Referer / Origin / `x-nba-stats-origin` / `x-nba-stats-token` / Sec-Fetch-* 全給 | ❌ **403**；`stats.nba.com` 連 **TLS 握手就逾時** |

03 的推測是「IP 被列入黑名單」。從住宅 IP 測出來不是 —— **瀏覽器從同一個 IP 打得通**。
真正擋的是 TLS 指紋（JA3/JA4），Akamai Bot Manager 認得出 curl 和 Python 的 OpenSSL 握手。
補 header 沒用，因為問題不在 header。

> **後續修正（見六之五）**：這個結論對 `cdn.nba.com` 完全成立，但對 `stats.nba.com` 只對一半。
> 雲端實測顯示 `stats.nba.com` 在指紋檢查之外，**還會丟棄資料中心 IP 的封包**。
> 住宅 IP 測不出這一層，因為住宅 IP 本來就不在它的丟棄名單上。

`stats.nba.com` 在 Python 連 TLS 握手都逾時，比 403 更徹底 —— 那層直接丟包。

### 所以 `nba_api` 在這台機器上裝了也沒用

`pip install nba_api` 之後直接 call 一定吃 403 / timeout，因為它底層是 `requests`。
這跟 `nba_api` 的已知 issue 一致，但原因比「雲端 IP 被封」更普遍：**任何非瀏覽器客戶端都會中**。

### 三條可行的繞過路線

| 方案 | 做法 | 評價 |
|---|---|---|
| **`curl_cffi`** | `pip install curl_cffi`，用 `impersonate="chrome"` 偽裝 Chrome 的 TLS 指紋 | ✅ **已實測成功，全部 200**。無頭、改動小。詳見下方 |
| Playwright / headless Chrome | 開真瀏覽器，導到 `nba.com` 後在頁面裡 `fetch()` | 能通，但重、慢、要裝 browser binary。有 `curl_cffi` 就不需要 |
| 美國住宅代理 / VPN | 換出口 IP | **解不到問題**。擋的是指紋不是 IP |

---

## 六、`curl_cffi` 實測：成功

環境：macOS arm64，系統 Python 3.9.6，`python3 -m venv .venv`，`curl_cffi 0.13.0`。

```bash
cd /Users/wubinghan/Documents/NBA_Fantasy
python3 -m venv .venv
.venv/bin/python -m pip install curl_cffi nba_api
.venv/bin/python scripts/probe_curlcffi.py 0022600244
```

### 結果（`scripts/probe_curlcffi.py`）

| 端點 | `impersonate="chrome"` | `impersonate="safari"` | 對照組（不偽裝） |
|---|---|---|---|
| cdn todaysScoreboard | ✅ 200 ／ 28 KB ／ 343ms | ✅ 200 ／ 284ms | ❌ 403 |
| cdn liveData boxscore | ✅ 200 ／ 40 KB ／ 508ms | ✅ 200 ／ 230ms | ❌ 403 |
| cdn liveData playbyplay | ✅ 200 ／ 418 KB ／ 836ms | ✅ 200 ／ 360ms | ❌ 403 |
| cdn scheduleLeagueV2 | ✅ 200 ／ 3.37 MB ／ 768ms | ✅ 200 ／ 632ms | ❌ 403 |
| stats boxscoretraditionalv3 | ✅ 200 ／ 492ms | ✅ 200 ／ 480ms | ❌ 逾時 25s |
| stats boxscoreadvancedv3 | ✅ 200 ／ 472ms | ✅ 200 ／ 502ms | ❌ 逾時 25s |
| stats playbyplayv3 | ✅ 200 ／ 551ms | ✅ 200 ／ 682ms | ❌ 逾時 25s |
| stats hustlestatsboxscore | ✅ 200 ／ 598ms | ✅ 200 ／ 453ms | ❌ 逾時 25s |

**同一支程式、同一組 header、同一個 IP，差別只有 TLS 指紋** —— 偽裝就 200，不偽裝就 403。
這直接證明了第五節的結論。`chrome` 和 `safari` 兩種指紋都通，延遲都在 200~850ms。

### `nba_api` 可以直接沿用，不用改它的程式碼

`nba_api` 的 `NBAHTTP` 有官方掛鉤 `set_session()`，塞一個 `curl_cffi` 的 Session 就好：

```python
from curl_cffi import requests as cffi
from nba_api.library.http import NBAHTTP
from nba_api.stats.library.http import NBAStatsHTTP
from nba_api.live.nba.library.http import NBALiveHTTP

session = cffi.Session(impersonate="chrome")
for cls in (NBAHTTP, NBAStatsHTTP, NBALiveHTTP):
    cls.set_session(session)

# ⚠️ 必要：nba_api 的 NBALiveHTTP 預設 header 沒有 Referer/Origin，
#    但 cdn.nba.com 一定要，否則回 403（表現為 JSONDecodeError）。
#    它寫死的 UA 還是 Chrome/87（2020 年），跟 impersonate 的指紋不一致，一起換掉。
NBALiveHTTP.headers = {
    **NBALiveHTTP.headers,
    "Referer": "https://www.nba.com/",
    "Origin": "https://www.nba.com",
    "User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"),
}

# 之後正常用就好
from nba_api.stats.endpoints import boxscoretraditionalv3
df = boxscoretraditionalv3.BoxScoreTraditionalV3(game_id="0022600244").get_data_frames()[0]
```

實測結果（`scripts/probe_nbaapi.py`，7 項全過）：

```
boxscoretraditionalv3      -> 24 列 / 34 欄
                             OKC  Shai Gilgeous-Alexander  37 PTS   2 REB   2 AST
                             SAC  Darius Acuff Jr.         26 PTS   0 REB   6 AST
                             OKC  Aday Mara                16 PTS  13 REB   3 AST
boxscoreadvancedv3         -> 24 列 / 37 欄  有 offensiveRating / defensiveRating
                                                trueShootingPercentage / usagePercentage
playbyplayv3               -> 509 列 / 24 欄
hustlestatsboxscore        -> 22 列 / 25 欄
live boxscore              -> OKC 125 @ SAC 103  (Final)  18+17 人
live playbyplay            -> 590 actions / 34 欄
live scoreboard (今天)      -> 9 場
```

### 三個踩到的坑

1. **`NBALiveHTTP` 缺 Referer**。沒補的話 `live boxscore` / `live playbyplay` /
   `live scoreboard` 三個全部回 `JSONDecodeError: Expecting value: line 1 column 1`
   —— 那是 403 的 HTML 被當 JSON 解。錯誤訊息完全看不出是權限問題，很容易誤判成 nba_api 壞了。
2. **`stats.nba.com` 的失敗是逾時不是 403**。那層直接丟包，所以 `timeout` 一定要設，
   不然會卡住整個流程。
3. **`nba_api.stats.library.http` 沒有 `requests` 屬性**。想 monkeypatch 的話要改
   `nba_api.library.http`（上層），但既然有 `set_session()` 就別 monkeypatch。

---

## 六之二、「即時」到什麼程度：證據與未驗證的部分

### 已驗證

`liveData` 的 play-by-play 每筆都帶 `timeActual`（該動作發生的真實世界時間）和
`edited`（該筆最後被寫入的時間）。分析 0022600244 的 590 筆：

```
timeActual 第一筆   : 2026-11-16 02:10:09 UTC
timeActual 最後一筆 : 2026-11-16 04:22:15 UTC
實際跨幅            : 132 分鐘
boxscore 回報 duration: 132 分鐘      ← 完全吻合

Q1: 02:10:09 -> 02:34:10 UTC  (24.0 分, 121 筆)
Q2: 02:36:59 -> 03:08:40 UTC  (31.7 分, 164 筆)
Q3: 03:24:08 -> 03:48:37 UTC  (24.5 分, 139 筆)   ← Q2 結束到 Q3 開始中間 15.5 分 = 中場休息
Q4: 03:51:33 -> 04:22:15 UTC  (30.7 分, 166 筆)

相鄰 action 間隔：中位數 0s、平均 13.5s、最大 928s（= 中場）
```

時間跨幅和官方回報的比賽時長**完全一致**，四節落在各自的真實時鐘區間，中場休息的空檔
清楚可見。這證明這個 feed 是**比賽進行中逐筆累積寫入**的，不是賽後一次產生的靜態檔案。

另外 `todaysScoreboard_00.json` 每場都有 `gameStatus`（1=未開始 / 2=進行中 / 3=已結束）、
`gameClock`、`period` —— 這三個欄位只有在「要表達比賽當下狀態」時才有意義。

### 尚未驗證

**所有實測都是在比賽結束後做的。** 2026-11-16 當下台北 21:20 / 美東 08:20，
今天的比賽美東 19:00 才開打（台北 11-17 08:00），沒有進行中的比賽可測。

所以還沒有親眼確認的是：**比賽進行中，連續輪詢同一個 URL 時 `actions` 會不會真的變長、
比分會不會跳動、CDN 的快取會不會讓你拿到舊資料**。前兩項從上面的證據幾乎可以確定成立，
第三項（CDN cache TTL）只有在比賽中才測得出來 —— 這是唯一真正的未知數。

### 驗證方式

`scripts/live_watch.py` 每 N 秒抓一次 `boxscore_{id}` + `playbyplay_{id}`，只印出「比上次多了什麼」：

```bash
.venv/bin/python scripts/live_watch.py          # 自動挑今天進行中的比賽
.venv/bin/python scripts/live_watch.py 0022600244 10   # 指定 game id、每 10 秒
```

沒有進行中的比賽時，它會自動挑一場已結束的當**對照組** —— 第一輪印出完整現況，
之後每輪都是 `(no change)` 然後自動停止。已實測這個對照組行為正確。

比賽進行中跑同一支，如果 `actions=` 的數字持續變大、比分跟著跳，就完全確認了。

## 六之三、這是什麼性質的 API？Google Apps Script 可行嗎？

### 它是不是 API

是。它是 HTTP + JSON 的介面，固定 URL、固定結構、可程式化呼叫 —— 定義上就是 API。

「官方」這個詞有兩種意思，這裡要分清楚：

| 問題 | 答案 |
|---|---|
| 是 NBA 自己營運的嗎？ | **是**。網域是 `cdn.nba.com` / `stats.nba.com`，是 NBA.com 網站自己的後端 |
| 資料是官方的嗎？ | **是**。跟 NBA.com 網頁上顯示的是同一份，裁判名字、觀眾數都有 |
| 有公開文件嗎？ | **沒有** |
| 有使用條款 / API key / SLA 嗎？ | **沒有** |
| NBA 有義務維持相容嗎？ | **沒有**。路徑和欄位可能隨時改 |

所以準確的說法是：**NBA 官方營運、但未公開也不受支援的內部介面**。
不是第三方提供的，也不是誰逆向工程出來的資料集 —— `nba_api` 這個套件只是把這些 URL 包成
Python 函式，資料本身一路都來自 NBA。

它的性質跟「官方公開 API」（例如有文件、有 key、有條款的那種）不同，風險在於**沒有保證**，
不在於資料來源可疑。

### Apps Script 能不能用這套方法

**curl_cffi 這套方法不能移植到 Apps Script。** 原因是機制層面的：

`curl_cffi` 是 libcurl-impersonate 的 Python 綁定 —— 一個重新實作了 Chrome TLS ClientHello
的編譯後 C 函式庫。它能通，是因為它在 **TLS 交握層**偽裝成 Chrome。

Apps Script 只有 `UrlFetchApp`，跑在 Google 的伺服器上、用 Google 自己的 HTTP stack。
你能設 header，但**碰不到 TLS 層**。而本次實測已經證明 NBA 擋的就是 TLS 指紋
（同一個 IP、同一組 header，偽裝 200、不偽裝 403）。所以 NBA 官方那條路在 Apps Script 上
幾乎確定不通。

### ESPN 那條路：實測有機會，但有兩個未知數

模擬 Apps Script 的請求（普通 HTTP client + 它的預設 UA
`Mozilla/5.0 (compatible; Google-Apps-Script; beanserver; ...)`）實測：

| UA | `site.api.espn.com` scoreboard / summary |
|---|---|
| 無 UA | ✅ 200 / 200 |
| **Apps Script 預設 UA** | ❌ **403 / 403** |
| 只有 `Google-Apps-Script` 字串 | ❌ 403 / 403 |
| 瀏覽器 UA | ✅ 200 / 200 |

**ESPN 擋的是 UA 字串本身，不是 TLS 指紋。** 所以只要在 `UrlFetchApp` 裡設瀏覽器 UA
就應該通 —— ESPN 不在意 TLS 指紋，這點跟 NBA 完全不同。
（`sports.core.api.espn.com` 的 play-by-play 連 Apps Script 預設 UA 都放行，實測 200。）

剩下兩個只有在 Apps Script 裡才測得出來的未知數：

1. **`UrlFetchApp` 到底能不能覆寫 `User-Agent`**。Google 文件只說了預設值是什麼，
   沒說能不能改。第三方指南說可以，但沒人驗證過；也有 App Engine 時代「設了無效」的舊報告。
2. **Google 的 IP 範圍會不會被擋**。這跟 UA 是兩回事，我在本機測不到。

### 驗證方式

`scripts/appscript_test.gs` 貼進 script.google.com 跑 `testAll()`，2 分鐘有答案。
它會先用 httpbin 回射確認你設的 UA 有沒有真的送出去（如果被 Google 覆寫，後面都不用看），
然後分別測 NBA 三個端點和 ESPN 三個端點。

### 有人做過嗎

搜不到「Apps Script + NBA 官方介面」的公開紀錄。
但「本機跑得動、部署到雲端就掛」的報告非常多（AWS、Azure、DigitalOcean、GitHub Actions
都有人回報），`nba_api` 的 issue 裡也有。所以雲端環境打 NBA 本來就是已知的痛點。

> 有一則 Hacker News 留言聲稱 `cdn.nba.com` 的 live 端點「沒有保護、任何地方都能打」。
> **本次實測與此不符** —— 從住宅 IP 用 curl 打 `cdn.nba.com` 一樣是 403。以實測為準。

### 務實的架構

既然要定時抓，而唯一確定能通的環境是這台 Mac：

```
Mac（launchd / cron）
  └─ curl_cffi 抓 NBA 官方 → 原始 JSON 存本機
       └─ 攤平成表格 → 用 Sheets API 寫進 Google Sheets
            └─ Apps Script / Looker Studio 在 Sheets 上做報表與通知
```

Apps Script 負責它擅長的（在 Sheets 裡排版、寄信、做介面），抓取交給 Mac。
這樣就不用賭 UrlFetchApp 的兩個未知數。

## 六之四、雲端方案：電腦不常開機怎麼辦

前提改變：抓取不能依賴這台 Mac。那要先釐清一件事。

### 「雲端 IP 被封」這件事其實還沒被驗證過

網路上的報告（AWS、Azure、DigitalOcean、GitHub Actions）都說「本機跑得動、部署就掛」。
但**那些報告全部都是用普通 `requests` 跑的** —— 而普通 `requests`
**從住宅 IP 也一樣失敗**（本次實測 403）。

所以那些報告無法區分兩件事：

| 可能原因 | 如果是這個 | 怎麼分辨 |
|---|---|---|
| TLS 指紋被擋 | 用 `curl_cffi` 在**任何**地方都能通，雲端完全可行 | 已證實指紋是**住宅 IP 失敗的唯一原因** |
| 資料中心 IP 另外被封 | 雲端就算用 `curl_cffi` 也不通，需要住宅代理 | **尚未驗證** |

本次的對照實驗（同一 IP、同一組 header，只換指紋 → 200 vs 403）已經證明
**指紋足以單獨解釋所有失敗**。所以「雲端 IP 被封」很可能只是 folklore，
是大家用錯工具得到的結論。

這個問題值得花五分鐘問清楚，因為答案決定了成本差一個量級。

### 決定性測試（免費，5 分鐘）

`.github/workflows/probe-nba.yml` —— 推上 GitHub，到 Actions 頁面手動 Run workflow。
GitHub 的 runner 跑在 Azure 上，是標準資料中心 IP。它會印出出口 IP / ASN，
然後用 `chrome` / `safari` / 不偽裝三組對照跑同一份 `probe_curlcffi.py`。

```
impersonate=chrome 全部 200   -> 雲端 IP 沒被封，指紋是唯一問題
                                 => 任何能跑 Python 的雲端環境都能抓官方資料（含投籃座標）
impersonate=chrome 也 403/逾時 -> 資料中心 IP 確實被封
                                 => 雲端只能走 ESPN，或需要住宅代理
```

### 方案比較

| 方案 | 成本 | 拿得到的資料 | 前置未知數 |
|---|---|---|---|
| **A. Apps Script → ESPN → Sheets** | 免費 | box score 14 項、play-by-play 488 筆、粗略座標 | UrlFetchApp 能否覆寫 UA；Google IP 是否被 ESPN 擋 |
| **B. GitHub Actions + curl_cffi → NBA 官方** | 免費（公開 repo 無限；私有 2000 分鐘/月） | **全部**，含 x/y 投籃座標、hustle stats | 資料中心 IP 是否被封 |
| **C. Cloud Run / Fly.io 跑 curl_cffi，Apps Script 呼叫它** | 免費額度內 | 全部 | 同 B，另加一層部署工 |
| **D. 住宅代理 + 上面任一個** | 約 $5~15/月起 | 全部 | 無。代理商的 IP 本來就是住宅 IP |
| **E. Raspberry Pi 放家裡** | 一次性 $50~80 | 全部 | 無。住宅 IP 已實證可通，但家裡網路要穩 |

### 建議的決策順序

1. **先跑 B 的 workflow**（5 分鐘，免費）。這是唯一真正的未知數。
2. **B 通了** → 就用 B。GitHub Actions 排程 + curl_cffi 抓官方資料，
   寫進 Google Sheets（服務帳號 + `gspread`）或直接 commit JSON 進 repo。
   Apps Script 留著做它擅長的：在 Sheets 上排版、寄通知、做介面。
3. **B 不通** → 跑 A 的 `testConnectivity()`（30 秒）。通了就用 A，完全免費零基礎建設，
   代價是沒有精確投籃座標。
4. **A 也不通** → D（住宅代理）或 E（Pi）。這兩個沒有未知數，只有成本。

### 為什麼 Apps Script 不能單獨完成 B

`UrlFetchApp` 碰不到 TLS 層，所以 Apps Script **永遠無法自己打通 NBA 官方介面**，
不管設什麼 header、換什麼 IP。要官方資料就必須有一個能跑 `curl_cffi` 的環境
（B 的 Actions runner、C 的容器、或 E 的 Pi），Apps Script 只能當它的消費端。

這不是調校問題，是機制問題 —— 所以別在 Apps Script 裡試 NBA 官方的 URL，省下時間。

### 已經寫好的東西

| 檔案 | 用途 |
|---|---|
| `.github/workflows/probe-nba.yml` + `scripts/cloud_probe.py` | 方案 B 的決定性測試。推上去手動 Run，結果寫在 Actions 的 Summary 頁 |
| `scripts/appscript_espn_to_sheets.gs` | 方案 A 的**完整生產版**：ESPN → 三個工作表、每日觸發器、去重、連通性自測 |
| `scripts/appscript_test.gs` | 純連通性探測（NBA 官方 + ESPN 都測） |

### 探針的成功判定條件

不是只看 HTTP 200 —— 那樣會被「200 但內容是錯誤頁」騙過。每個端點都驗內容：

| 端點 | 必須滿足 |
|---|---|
| cdn todaysScoreboard | 能解析出 `scoreboard.games` 陣列 |
| cdn boxscore | 兩隊各 ≥10 名球員、主隊比分 >0、每人 33 個統計欄位 |
| cdn playbyplay | `actions` ≥400 筆，且**至少有一筆帶 x/y 投籃座標** |
| cdn scheduleLeagueV2 | `gameDates` ≥100 個比賽日 |
| stats boxscoretraditionalv3 | 主隊 ≥10 名球員 |
| stats boxscoreadvancedv3 | 含 `offensiveRating` / `trueShootingPercentage` / `usagePercentage` |
| stats playbyplayv3 | `actions` ≥400 筆 |
| stats hustlestatsboxscore | `PlayerStats` ≥15 列 |

三組判定：

| 組 | 預期 | 為什麼要測 |
|---|---|---|
| **對照組**（不偽裝指紋） | **全部失敗** | 確認這次測的真的是指紋。如果對照組也通過，代表 NBA 當下沒在擋任何客戶端，成功就不能歸因於 `curl_cffi` |
| **偽裝組**（`impersonate="chrome"`） | 全部通過 | 這是真正想知道的答案 |
| **ESPN** | 全部通過 | 備援方案是否還在 |

結束碼決定 Actions 的綠勾紅叉：`0` = NBA 官方可用，`1` = 只剩 ESPN，`2` = 兩邊都不通。

> **踩過的坑**：三組一開始共用同一個 `curl_cffi.Session`，結果對照組假性通過 ——
> Akamai 會在成功的請求上發 bot-manager cookie（`_abck` / `bm_sz`），
> 偽裝組拿到的 cookie 被對照組沿用了。修法是**每組用全新的 Session**，
> 並把對照組排在最前面跑。

### 住宅 IP 的基準線（2026-11-16 實測）

同一支 `cloud_probe.py` 在這台 Mac 上跑的結果，拿來跟雲端對照：

```
出口 IP : 49.216.174.168 · Taipei, TW · AS24158 Taiwan Mobile

對照組（不偽裝）  cdn 四個端點全部 HTTP 403
偽裝組（chrome）  NBA 官方八個端點全部 PASS
ESPN             三個端點全部 PASS
exit 0
```

## 六之五、雲端實測結果（2026-11-16，GitHub Actions）

### 結論：核心資料在雲端可用，進階數據不可用

GitHub Actions runner，出口 IP `20.12.246.122`（Des Moines, US, AS8075 Microsoft）：

| 組 | 結果 |
|---|---|
| 對照組（不偽裝指紋） | cdn 四個端點全部 **403** —— 與住宅 IP 一致 |
| **`cdn.nba.com`**（`impersonate="chrome"`） | **四個端點全部 PASS** ✅ |
| `stats.nba.com`（`impersonate="chrome"`） | 四個端點全部 **逾時 30 秒** ❌ |
| ESPN | 三個端點全部 PASS ✅ |

所以答案不是非黑即白 —— **兩個主機的防護機制不一樣**：

| 主機 | 防護 | 資料中心 IP 能用嗎 | 裡面有什麼 |
|---|---|---|---|
| `cdn.nba.com` | 只檢查 TLS 指紋 | **可以**（要 `curl_cffi`） | box score、play-by-play（含投籃 x/y 座標）、賽程、今日即時比分 |
| `stats.nba.com` | 指紋檢查 **+ 丟棄資料中心 IP** | **不行** | 進階數據（ORtg/DRtg/TS%/USG%/PACE）、hustle stats |

`stats.nba.com` 的失敗是**逾時**不是 403 —— 封包在網路層就被丟掉，連 TLS 交握都沒完成。
這跟住宅 IP 上「不偽裝指紋時 `stats.nba.com` 也逾時」是同一種現象，
代表它的過濾比 `cdn.nba.com` 更早、更粗暴。

### 對日常使用的意義

**需要的東西都拿得到。** box score 和 play-by-play（含投籃座標）都在 `cdn.nba.com`，
雲端排程完全可行。拿不到的是進階數據和 hustle stats —— 而那些**可以自己從
play-by-play 算**（ORtg、TS%、USG% 都是從基礎數據推導的）。

### 我先前的一個誤判

六之三提到有一則 Hacker News 留言聲稱「`stats.nba.com` 用 TLS 指紋並丟棄資料中心 IP，
而 `cdn.nba.com` 的 live 端點不受保護、任何地方都能打」，我當時以住宅 IP 的實測
（cdn 也 403）判定它不符。

**那則留言對了一半，而且對的那一半是我當時測不到的那一半**：
`stats.nba.com` 確實會丟棄資料中心 IP。它錯的是「`cdn.nba.com` 不受保護」——
cdn 確實有指紋檢查（不偽裝就 403）。

教訓：住宅 IP 的實測無法否證「資料中心 IP 被封」這類命題，因為那個變數根本沒被測到。
我當時說「以實測為準」，但實測的範圍不涵蓋那個主張。

### 探針的判定已改成分層

`cloud_probe.py` 原本要求八個端點全過才給 exit 0，會把「核心可用、進階不可用」
誤報成失敗。現在改成以 `cdn.nba.com` 那組為準：

```
cdn 通 + stats 通  -> exit 0「NBA 官方全部可用」
cdn 通 + stats 不通 -> exit 0「核心資料可用，進階數據不可用」  ← 雲端的實際情況
cdn 不通 + ESPN 通  -> exit 1
兩邊都不通          -> exit 2
```

## 六之六、雲端拿不到的那些，到底有沒有救

六之五確認 `stats.nba.com` 在雲端不可用。那進階數據和 hustle stats 怎麼辦？
實測了三條可能的路：

| 可能的來源 | 結果 |
|---|---|
| `cdn.nba.com` 有沒有 hustle / advanced 端點 | ❌ 猜了 6 條路徑（`liveData/hustle/`、`liveData/boxscoreadvanced/` 等）全部 403 = 不存在 |
| `cdn.nba.com` box score 的球隊 statistics | ⚠️ **61 個欄位裡已經有** `trueShootingPercentage`、`trueShootingAttempts`、`fieldGoalsEffectiveAdjusted`、`assistsTurnoverRatio`（只有球隊層級，沒有球員層級） |
| ESPN core API 的 statistics | ❌ 有 `VORP`、`NBARating` 但實測 `VORP=0.0`、`avgMinutes=0.0`，沒有 ORtg/DRtg/PACE/TS%/USG% |

（順帶測到一個之前沒注意的：`liveData/odds/odds_todaysGames.json` 可用，115 KB，是賠率資料。）

### 自己算：誤差實測

把 `scripts/advanced_stats.py` 算出來的值跟 `stats.nba.com` 的官方值逐項對照
（game 0022600244）：

| 指標 | 誤差 |
|---|---|
| **TS%** | **±0.02 pp**（球員層級完全一致） |
| **eFG%** | **±0.05 pp** |
| DRtg | −0.33 |
| ORtg | −0.33 ～ −1.77 |
| PACE | +1.06 |
| USG% | +0.1 ～ +1.3 pp |

球員層級對照（TS% 我算 / 官方）：

```
SAC Darius Acuff Jr.    48.6 / 48.6      USG%  46.6 / 45.6
OKC Jared McCain        41.0 / 41.0      USG%  21.8 / 21.6
OKC Shai Gilgeous-Alex  80.2 / 80.2      USG%  32.8 / 31.5
SAC Domantas Sabonis    63.7 / 63.7      USG%  13.9 / 13.9
```

**TS% 和 eFG% 實質上完全一致。** ORtg / PACE / USG% 有小差異，
因為 NBA 用的回合數公式比標準估計式更細（處理球隊籃板、加罰、節末回合）。
對「比較兩個球員誰效率高」這種用途完全夠用；要跟官方數字逐位對齊就做不到。

### 最終結論

| 資料 | 雲端拿得到嗎 |
|---|---|
| box score（33 個球員欄位、61 個球隊欄位） | ✅ 直接拿 |
| play-by-play（含投籃 x/y 座標） | ✅ 直接拿 |
| 賽程、即時比分、賠率 | ✅ 直接拿 |
| TS% / eFG% | ✅ **自己算，誤差 ±0.05 pp** |
| ORtg / DRtg / PACE / USG% | ✅ 自己算，誤差 1~2% |
| **Hustle stats**（封阻投籃、撥球、掩護助攻、卡位、救球） | ❌ **真的拿不到**。那是獨立的人工記錄，不是從基礎數據推導的，三條路都沒有 |

唯一真正失去的是 hustle stats。

## 七、對這個專案的建議

分成兩種用途：

### 1. Fantasy 每日推薦（主線）→ 維持 03 的結論，用 ESPN

理由不變：免認證、純 GET、curl 直接通、沒有指紋問題，而且推薦引擎需要的是
「賽前的傷病 + 賽程 + 投影」，不是比賽中的即時 box score。
加一條 `nba_api` 不能用的紀錄就好。

### 2. 比賽中即時追蹤 / 投籃分佈 / play-by-play 分析（加分功能）→ 用官方

ESPN 的 play-by-play 只有文字 `text` 和粗略 `coordinate`，官方有 `x/y` + `shotDistance`
+ `assistPersonId` + `descriptor`（step back / driving / fadeaway），分析價值差很多。
球員 box score 也多了 `blocksReceived`、`foulsDrawn`、`pointsFastBreak` 等 ESPN 沒有的欄位。

落地步驟（第 1 步已完成）：

1. ~~測 `curl_cffi` 能不能通~~ → ✅ 已實測成功，`.venv` 已建好，`curl_cffi` + `nba_api` 已安裝
2. 包一層薄 client：把第六節那段 `set_session` + `NBALiveHTTP.headers` 的設定集中到一個模組，
   之後所有呼叫都 import 它，不要每個檔案各寫一次
3. 只打三個端點就夠即時追蹤：`todaysScoreboard_00` / `boxscore_{id}` / `playbyplay_{id}`
4. 降級鏈：官方（`curl_cffi`）→ ESPN `summary?event=` + `/plays`（座標較粗但 curl 直通）
5. 照 03 第五節的規則存 raw JSON 到 `data/cache/`，並做 schema 檢查

### 輪詢頻率

`liveData` 約 5~15 秒更新一次。比賽中每 **10~20 秒**抓一次就夠，
`boxscore` 40 KB、`playbyplay` 418 KB（整場累積，開賽時小得多）。
不要每秒打 —— 那是最快讓指紋被標記的方式。

---

## 八、速查

```bash
# 整季賽程（找 game id）
https://cdn.nba.com/static/json/staticData/scheduleLeagueV2_32.json

# 當日比賽 + 即時比分
https://cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_00.json

# 即時 box score
https://cdn.nba.com/static/json/liveData/boxscore/boxscore_{GAME_ID}.json

# 即時 play-by-play（含投籃座標）
https://cdn.nba.com/static/json/liveData/playbyplay/playbyplay_{GAME_ID}.json

# 進階數據
https://stats.nba.com/stats/boxscoreadvancedv3?GameID={GAME_ID}&StartPeriod=0&EndPeriod=14&StartRange=0&EndRange=28800&RangeType=0

# Hustle stats
https://stats.nba.com/stats/hustlestatsboxscore?GameID={GAME_ID}

# ESPN 備援
https://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary?event={ESPN_EVENT_ID}
```

必帶 header：

```
User-Agent: <完整的 Chrome UA>
Referer: https://www.nba.com/
Origin:  https://www.nba.com
x-nba-stats-origin: stats      # 只有 stats.nba.com 需要
x-nba-stats-token: true        # 只有 stats.nba.com 需要
```

但光給 header 不夠 —— **必須用 `curl_cffi` 的 `impersonate="chrome"`**，
原生 `requests` / `urllib` / `curl` 一律 403 或逾時。

驗證腳本：

```bash
.venv/bin/python scripts/probe_curlcffi.py 0022600244   # 三種指紋對照
.venv/bin/python scripts/probe_nbaapi.py  0022600244    # nba_api 整合
```
