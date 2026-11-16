# NBA API 使用指南

## 這份文件能讓你做到什麼

照這份文件做，你可以在**比賽進行中**，用 Python 從 NBA 官方介面取得：

- **Box score** — 每個球員 33 個統計欄位、球隊 61 個欄位、單節比分、場館／觀眾數／裁判
- **Play-by-play** — 每個動作一筆，含**投籃座標**、投籃距離、助攻者、當下比分
- **進階數據** — ORtg／DRtg／TS%／USG%／PACE
- **Hustle stats** — 封阻投籃、撥球、掩護助攻、卡位、救球

資料格式是 JSON，免 API key、免註冊、免費。`nba_api` 這個 Python 套件可以直接用。

## 這是什麼來源

**NBA 官方營運、但未公開也不受支援的內部介面。** 網域是 `cdn.nba.com` / `stats.nba.com`，
就是 NBA.com 網站自己的後端 —— 你拿到的跟網頁上顯示的是同一份資料（連裁判名字、觀眾數都有）。
不是第三方轉手的，也不是誰逆向工程出來的資料集；`nba_api` 只是把這些 URL 包成 Python 函式。

代價是**沒有文件、沒有使用條款、沒有 SLA**，NBA 沒有義務維持相容性。
所以風險在「沒有保證」，不在「資料來源可疑」。

## 目前不確定的

1. **CDN 快取延遲**。所有實測都在比賽結束後做的（2026-11-16 當下沒有進行中的比賽）。
   資料結構確定支援即時（見「即時性」一節的證據），但**比賽進行中連續輪詢時，
   Akamai 的快取會不會讓你拿到幾秒前的舊資料，還沒親眼確認**。
   驗證方式：比賽中跑 `scripts/live_watch.py`，看 `actions=` 的數字是否持續變大。
2. **這是未公開介面**。沒有官方文件、沒有 SLA、NBA 沒有義務維持相容性，欄位和路徑可能隨時改。
   所以務必存原始 JSON（見「存檔格式」），並做 schema 檢查。

---

## 一、環境設定

### 為什麼不能用普通的 requests

NBA 的 Akamai 會擋掉非瀏覽器的 TLS 指紋。解法是 `curl_cffi`，它用 Chrome 的指紋發請求：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install curl_cffi nba_api
```

### 直接打 HTTP

```python
from curl_cffi import requests as cffi

HEADERS = {
    "Referer": "https://www.nba.com/",      # cdn.nba.com 必須有，否則 403
    "Origin":  "https://www.nba.com",
    "Accept":  "application/json, text/plain, */*",
}
S = cffi.Session(impersonate="chrome")      # ← 關鍵就是這個參數

r = S.get("https://cdn.nba.com/static/json/liveData/boxscore/boxscore_0022600244.json",
          headers=HEADERS, timeout=25)
data = r.json()
```

`impersonate` 用 `"chrome"` 或 `"safari"` 都可以，實測兩者皆通。

### 透過 nba_api（回傳 pandas DataFrame）

`nba_api` 有官方掛鉤 `set_session()`，把 curl_cffi 的 session 塞進去即可：

```python
from curl_cffi import requests as cffi
from nba_api.library.http import NBAHTTP
from nba_api.stats.library.http import NBAStatsHTTP
from nba_api.live.nba.library.http import NBALiveHTTP

session = cffi.Session(impersonate="chrome")
for cls in (NBAHTTP, NBAStatsHTTP, NBALiveHTTP):
    cls.set_session(session)

# 必要：NBALiveHTTP 預設 header 沒有 Referer，而 cdn.nba.com 需要它。
# 它寫死的 UA 也還是 Chrome/87（2020 年），跟 impersonate 的指紋不一致，一起換掉。
NBALiveHTTP.headers = {
    **NBALiveHTTP.headers,
    "Referer": "https://www.nba.com/",
    "Origin":  "https://www.nba.com",
    "User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"),
}

# 之後正常使用
from nba_api.stats.endpoints import boxscoretraditionalv3
df = boxscoretraditionalv3.BoxScoreTraditionalV3(game_id="0022600244").get_data_frames()[0]
```

> 這段設定只要漏掉 `Referer`，live 系列的三個端點會回
> `JSONDecodeError: Expecting value: line 1 column 1` —— 那是 403 的 HTML 被當 JSON 解，
> 訊息完全看不出是權限問題。把這段抽成一個模組，所有呼叫都 import 它。

---

## 二、先拿到 game id

官方 game id 是 **10 位數字**，例如 `0022600244`：

```
00  22600244
    └ 2  = 球季類型（1 季前賽 / 2 例行賽 / 4 季後賽）
      26 = 球季（2026-27）
      00244 = 當季第幾場
```

ESPN 的 event id（`401909993`）**不通用**，兩套系統各自編號。

### 查今天的比賽（含即時比分與狀態）

```python
sb = S.get("https://cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_00.json",
           headers=HEADERS, timeout=25).json()["scoreboard"]

for g in sb["games"]:
    print(g["gameId"], g["awayTeam"]["teamTricode"], g["awayTeam"]["score"],
          "@", g["homeTeam"]["teamTricode"], g["homeTeam"]["score"],
          g["gameStatus"], g["gameStatusText"], g["gameClock"], g["period"])
```

`gameStatus`：**1 = 未開始，2 = 進行中，3 = 已結束**。這是判斷「現在能不能抓即時資料」的依據。

> 注意 `sb["gameDate"]` 不是依本地午夜換日。美東 2026-11-16 08:20 時它還回 `2026-11-15`
> （前一晚的比賽）。要指定日期請用下面的整季賽程。

### 查任意日期 / 整季賽程

```python
sch = S.get("https://cdn.nba.com/static/json/staticData/scheduleLeagueV2_32.json",
            headers=HEADERS, timeout=30).json()
for d in sch["leagueSchedule"]["gameDates"]:       # d["gameDate"] = "11/15/2026 00:00:00"
    for g in d["games"]:
        g["gameId"], g["gameDateTimeEst"], g["awayTeam"]["teamTricode"], g["homeTeam"]["teamTricode"]
```

3.4 MB，整季一次抓完存起來離線查就好，不用每次打。

---

## 三、Box score

```
https://cdn.nba.com/static/json/liveData/boxscore/boxscore_{GAME_ID}.json
```

回傳 JSON，約 40 KB。結構：

```
game
├─ gameId, gameStatus, gameStatusText, period, gameClock, duration, attendance
├─ arena      { arenaName, arenaCity, arenaState }
├─ officials  [ { name, nameI, firstName, familyName, personId, jerseyNum,
│                 assignment } ]            ← assignment = "OFFICIAL1".."OFFICIAL3"
├─ homeTeam / awayTeam
│  ├─ teamId, teamName, teamCity, teamTricode, score
│  ├─ inBonus, timeoutsRemaining
│  ├─ periods    [ { period, periodType, score } ]      ← 單節比分
│  ├─ statistics { ...61 個球隊欄位... }
│  └─ players    [ { personId, name, nameI, firstName, familyName,
│                    position, jerseyNum, order, starter, oncourt, played,
│                    status, statistics {...33 個...} } ]
```

### 球員 statistics 的 33 個欄位

| 類別 | 欄位 |
|---|---|
| 時間 | `minutes` |
| 得分 | `points` `pointsFastBreak` `pointsInThePaint` `pointsSecondChance` `pointsFromTurnovers` |
| 投籃 | `fieldGoalsMade` `fieldGoalsAttempted` `fieldGoalsPercentage` |
| 三分 | `threePointersMade` `threePointersAttempted` `threePointersPercentage` |
| 兩分 | `twoPointersMade` `twoPointersAttempted` `twoPointersPercentage` |
| 罰球 | `freeThrowsMade` `freeThrowsAttempted` `freeThrowsPercentage` |
| 籃板 | `reboundsOffensive` `reboundsDefensive` `reboundsTotal` |
| 其他 | `assists` `steals` `blocks` `blocksReceived` `turnovers` |
| 犯規 | `foulsPersonal` `foulsOffensive` `foulsTechnical` `foulsDrawn` |
| 正負值 | `plus` `minus` `plusMinusPoints` |

兩個格式陷阱：

- **`minutes` 是 ISO 8601 duration**：`"PT27M21.00S"`。要自己轉成秒或 mm:ss。
- **百分比是 0~1 的浮點數**，不是 0~100：`0.42857142857142855`。

### 進階數據與 hustle stats

```
https://stats.nba.com/stats/boxscoreadvancedv3?GameID={GAME_ID}&StartPeriod=0&EndPeriod=14&StartRange=0&EndRange=28800&RangeType=0
https://stats.nba.com/stats/hustlestatsboxscore?GameID={GAME_ID}
```

`stats.nba.com` 這組需要**額外兩個 header**：

```python
STATS_HEADERS = {**HEADERS, "x-nba-stats-origin": "stats", "x-nba-stats-token": "true"}
```

進階數據每位球員 23 個統計欄位：`offensiveRating` `defensiveRating` `netRating`
`trueShootingPercentage` `effectiveFieldGoalPercentage` `usagePercentage`
`assistPercentage` `assistRatio` `assistToTurnover` `turnoverRatio`
`offensiveReboundPercentage` `defensiveReboundPercentage` `reboundPercentage`
`pace` `pacePer40` `possessions` `PIE`，另有四個 `estimated*` 版本與 `minutes`。
Hustle 回 25 欄（含 `CONTESTED_SHOTS` `DEFLECTIONS` `SCREEN_ASSISTS` `BOX_OUTS`
`LOOSE_BALLS_RECOVERED` `CHARGES_DRAWN`）。

---

## 四、Play-by-play

```
https://cdn.nba.com/static/json/liveData/playbyplay/playbyplay_{GAME_ID}.json
```

回傳 `game.actions`，一場完整比賽約 **590 筆、418 KB**。

每筆有 34 個共通欄位，但**不同動作類型會多帶自己的欄位**（例如 `rebound` 多
`reboundTotal` / `reboundDefensiveTotal` / `shotActionNumber`），所以用
`pd.json_normalize()` 攤平整場會得到 **54 欄**。共通的 34 個：

| 類別 | 欄位 |
|---|---|
| 識別排序 | `actionNumber` `orderNumber` `actionId` |
| 時間 | `clock`（比賽時鐘，`PT09M12.00S`）`timeActual`（真實世界時間，UTC）`period` `periodType` |
| 人／隊 | `teamId` `teamTricode` `personId` `playerName` `playerNameI` `personIdsFilter` |
| 動作分類 | `actionType` `subType` `descriptor` `qualifiers` |
| **投籃座標** | `x` `y`（百分比座標）`xLegacy` `yLegacy`（傳統英尺座標）`shotDistance` `side` |
| 投籃結果 | `isFieldGoal` `shotResult` `pointsTotal` |
| 比分 | `scoreHome` `scoreAway` `possession` |
| 助攻 | `assistPersonId` `assistPlayerNameInitial` `assistTotal` |
| 文字 | `description` |
| 其他 | `edited`（該筆最後寫入時間）`isTargetScoreLastPeriod` |

實際一筆：

```json
{
  "actionNumber": 29, "actionType": "3pt", "subType": "Jump Shot",
  "descriptor": "step back", "clock": "PT09M12.00S", "period": 1,
  "teamTricode": "OKC", "playerNameI": "K. Williams", "personId": 1629026,
  "shotDistance": 26.84, "shotResult": "Made", "side": "left",
  "x": 33.39, "y": 62.18, "xLegacy": -61, "yLegacy": 261,
  "assistPlayerNameInitial": "I. Hartenstein", "assistTotal": 1,
  "scoreAway": "11", "scoreHome": "4",
  "description": "K. Williams 26' 3PT step back (3 PTS) (I. Hartenstein 1 AST)"
}
```

有 `x`/`y` 就能自己畫投籃分佈圖，不用另外打 `shotchartdetail`。
`actionType` 實測出現的全部 15 種值：`2pt` `3pt` `heave` `freethrow` `rebound`
`block` `steal` `turnover` `foul` `violation` `substitution` `timeout` `jumpball`
`period` `game`。

> `stats.nba.com/stats/playbyplayv3` 是同一場比賽的另一個版本，509 筆、24 欄
> —— 少的是換人／暫停等非比賽動作，也沒有 `x`/`y` 百分比座標。
> **要做分析就用上面 cdn 的 liveData 版本**，欄位最完整。

---

## 五、即時性

### 更新頻率

`liveData` 的兩個端點在比賽進行中會持續更新。從完整比賽的時間戳推算：

```
play-by-play 相鄰動作間隔：中位數 0s、平均 13.5s
```

**比賽中每 10~20 秒輪詢一次就足夠**，不要每秒打。

### 支援即時的證據

每筆 action 都帶 `timeActual`（該動作發生的真實世界時間）。分析一場完整比賽：

```
timeActual 跨幅         : 132 分鐘
boxscore 回報 duration  : 132 分鐘      ← 完全吻合

Q1: 02:10:09 → 02:34:10 UTC  (24.0 分, 121 筆)
Q2: 02:36:59 → 03:08:40 UTC  (31.7 分, 164 筆)
Q3: 03:24:08 → 03:48:37 UTC  (24.5 分, 139 筆)   ← Q2→Q3 中間 15.5 分 = 中場休息
Q4: 03:51:33 → 04:22:15 UTC  (30.7 分, 166 筆)
```

時間跨幅與官方回報的比賽時長完全一致、四節落在各自的真實時鐘區間、中場空檔清楚可見。
這證明這個 feed 是**比賽進行中逐筆累積寫入**的，不是賽後一次產生的靜態檔。

**尚未確認**：比賽中輪詢時 Akamai 的快取會不會回舊資料。見本文開頭「目前不確定的」。

### 必須等開賽

**未開賽的比賽，`boxscore_{id}.json` 和 `playbyplay_{id}.json` 還不存在，回 403。**
所以流程一定是：

```
輪詢 todaysScoreboard_00.json
  └─ 等到某場的 gameStatus 變成 2（進行中）
       └─ 才開始打 boxscore_{id} / playbyplay_{id}
```

不要在開賽前就去打那兩個 URL，拿到的 403 不是權限問題，是檔案還沒生出來。

---

## 六、限制

| 項目 | 實際情況 |
|---|---|
| API key | 不需要 |
| 費用 | 免費 |
| 速率限制 | 沒有公告的數字。實測連續請求（間隔 0.4s）8 個端點沒被擋。比賽中 10~20 秒一次很安全 |
| 延遲 | 單次請求 200~850ms（cdn 較快，stats 較慢） |
| 回應大小 | boxscore 40 KB／playbyplay 418 KB（整場累積，開賽時小得多）／整季賽程 3.4 MB |
| 穩定性 | **未公開介面，無文件無 SLA**。欄位與路徑可能隨時變動 |
| 涵蓋範圍 | 只有 NBA。`todaysScoreboard` 只有當天 |
| 歷史資料 | 用 game id 可以回溯抓已結束的比賽，不限當天 |

因為最後兩點，**一定要存原始 JSON 並做 schema 檢查**：抓完先驗必要欄位存在、
筆數在合理範圍，異常就告警，而不是靜默產出垃圾分析。

---

## 六之二、在雲端 / 排程環境跑

本機以外的環境要拿官方資料，條件只有一個：**那個環境能跑 `curl_cffi`**。
TLS 指紋偽裝必須在 TLS 交握層完成，所以只有能執行原生程式碼的環境可以
（容器、VM、GitHub Actions runner、Raspberry Pi）。

```yaml
# .github/workflows/ 範例：免費、不需要伺服器
- uses: actions/setup-python@v5
  with: { python-version: '3.12' }
- run: pip install curl_cffi
- run: python scripts/fetch.py
```

照這個模式，任何支援 Python 的排程環境都能用，不限 GitHub Actions。

### 兩個主機在雲端的差別（2026-11-16 於 GitHub Actions 實測）

| 主機 | 資料中心 IP | 裡面有什麼 |
|---|---|---|
| **`cdn.nba.com`** | ✅ **可用**（需 `curl_cffi` 偽裝指紋） | box score、play-by-play 含投籃 x/y 座標、賽程、即時比分 |
| `stats.nba.com` | ❌ 逾時（封包在網路層被丟棄） | 進階數據（ORtg/TS%/USG%）、hustle stats |

**核心資料都在 `cdn.nba.com`，所以雲端排程完全可行。** 進階數據拿不到，
但那些可以自己從 play-by-play 算出來。

要在自己的環境複驗：`.github/workflows/probe-nba.yml` 推上 GitHub 手動 Run 一次。

**只用 Google Apps Script 的話**：`UrlFetchApp` 碰不到 TLS 層，所以走 ESPN 的介面。
`scripts/appscript_espn_to_sheets.gs` 是完整可用的版本（ESPN → Google Sheets、
每日觸發器、自動去重），先在裡面跑 `testConnectivity()` 確認環境。
ESPN 有 box score 14 項與完整 play-by-play，但沒有官方的精確投籃 x/y 座標。

各方案的成本與取捨比較見 [research.md](research.md) 六之四節。

## 七、存檔格式

分兩層存，不要混。

### 第一層：原始 JSON（存檔用，不要改）

```
data/raw/2026-11-15/boxscore_0022600244.json
data/raw/2026-11-15/playbyplay_0022600244.json
```

原封不動的 API 回應。這是你的真相來源 —— 介面改了、分析寫錯了，都能從這裡重跑。
可以 gzip，實測 418 KB 的 play-by-play 壓完 **33 KB**，40 KB 的 box score 壓完 **4.7 KB**。

### 第二層：分析用的表格

play-by-play 和 box score 都是**天然的表格**（一筆動作一列、一個球員一列），
所以攤平成 DataFrame 再存：

| 格式 | 什麼時候用 | 說明 |
|---|---|---|
| **Parquet** | **本機分析的預設選擇** | 保留欄位型別（數字還是數字、時間還是時間）、壓縮率高、pandas／DuckDB／Polars 都直讀。多場比賽疊起來查最快 |
| **CSV** | 要給別人、要放 Google Drive、要用 Excel 開 | 通用性最高，但型別全部變字串，`shotDistance` 26.84 讀回來可能變文字。重讀時要指定 dtype |
| **SQLite** | 要跨比賽查詢（例如「這季所有 step back 三分」） | 單一檔案、支援 SQL、不需要架服務。累積幾百場之後比一堆檔案好管 |
| **.md** | ❌ 不要用來存數據 | Markdown 是給人讀的。存數據會丟型別、難以程式化讀取、檔案肥大。只用來寫結論和報告 |

```python
import pandas as pd
df = pd.json_normalize(data["game"]["actions"])
df.to_parquet("data/pbp/0022600244.parquet")   # 分析用
df.to_csv("data/export/0022600244.csv", index=False)  # 要分享時再轉
```

### 關於 Google Drive

Drive 適合**放結果**，不適合當分析時的工作目錄 —— 它會同步、會鎖檔，
pandas 寫一半被同步走會壞檔。建議：

- 本機 `data/` 跑分析（Parquet／SQLite），這個目錄**不要**放進 Drive
- 要分享的成果（CSV 或整理好的報表）才另存一份到 Drive
- 要在 Google Sheets 裡直接看就存 CSV；要保留多個工作表和格式才用 `.xlsx`
  （`df.to_excel()`，需要 `openpyxl`）。但 Excel 單張表上限 1,048,576 列，
  一場比賽 590 列沒問題，累積上千場就會撞到 —— 那時候該用 Parquet 或 SQLite 了

---

## 八、速查

```python
CDN = "https://cdn.nba.com/static/json"
HEADERS = {"Referer": "https://www.nba.com/", "Origin": "https://www.nba.com",
           "Accept": "application/json, text/plain, */*"}
S = cffi.Session(impersonate="chrome")
```

| 要什麼 | URL |
|---|---|
| 今天的比賽 + 即時比分 + `gameStatus` | `{CDN}/liveData/scoreboard/todaysScoreboard_00.json` |
| 整季賽程（查 game id） | `{CDN}/staticData/scheduleLeagueV2_32.json` |
| 即時 box score | `{CDN}/liveData/boxscore/boxscore_{GAME_ID}.json` |
| 即時 play-by-play（含座標） | `{CDN}/liveData/playbyplay/playbyplay_{GAME_ID}.json` |
| 進階數據 | `https://stats.nba.com/stats/boxscoreadvancedv3?GameID={GAME_ID}&StartPeriod=0&EndPeriod=14&StartRange=0&EndRange=28800&RangeType=0` |
| Hustle stats | `https://stats.nba.com/stats/hustlestatsboxscore?GameID={GAME_ID}` |

驗證腳本：

```bash
.venv/bin/python scripts/probe_curlcffi.py 0022600244   # 連通性
.venv/bin/python scripts/probe_nbaapi.py  0022600244    # nba_api 整合
.venv/bin/python scripts/live_watch.py                  # 即時監看
```

完整調查過程見 [research.md](research.md)。
