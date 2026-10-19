# 03 — 資料來源：實測結果

以下全部是 **2026-10-19 從這台機器實際發請求測出來的**，不是看文件抄的。這很重要，因為 NBA 官方的幾個常見來源現在是擋住的。

## 一、實測總表

| 來源 | 端點 | 結果 | 用途 | 需要 key |
|---|---|---|---|---|
| **ESPN 傷病** | `site.api.espn.com/apis/site/v2/sports/basketball/nba/injuries` | ✅ **200**，1.04 MB，28 隊 92 筆 | 傷病 + 新聞文字 | 否 |
| **ESPN 當日賽程** | `.../nba/scoreboard?dates=20261020` | ✅ **200**，3 場（BOS@DET, PHI@NY, OKC@SA） | 每日賽程 | 否 |
| **ESPN 球隊賽程** | `.../nba/teams/{id}/schedule?season=2027` | ✅ **200**，80 場 | 整季賽程（跑 30 隊） | 否 |
| **Sleeper 球員庫** | `api.sleeper.app/v1/players/nba` | ✅ **200**，2,176 人，含 `injury_status` | 傷病備援 + 球員 ID 對照表 | 否 |
| **Basketball Reference** | `basketball-reference.com/leagues/NBA_2027_per_game.html` | ✅ **200** | 季統計、進階數據 | 否 |
| Rotowire 傷病頁 | `rotowire.com/basketball/injury-report.php` | ✅ **200** | Q/D/P 細分狀態 | 否（HTML 要解析） |
| **NBA 官方賽程** | `cdn.nba.com/static/json/staticData/scheduleLeagueV2_32.json` | ❌ **403** | — | — |
| **stats.nba.com** | `stats.nba.com/stats/leaguedashplayerstats` | ❌ **連線逾時** | — | — |
| **NBA 官方傷病 PDF** | `ak-static.cms.nba.com/referee/injury/Injury-Report_*.pdf` | ⚠️ **403 (AmazonS3)** | 需精確時間戳 | — |
| balldontlie | `api.balldontlie.io/v1/teams` | ⚠️ **401** 需 key | 付費才有價值 | 是 |
| Hashtag Basketball | `hashtagbasketball.com/fantasy-basketball-projections` | ✅ 可讀，免費只有前 30 名 | **投影（最佳性價比）** | 訂閱 |

## 二、結論：用 ESPN，不要用 NBA.com

`cdn.nba.com` 回 403、`stats.nba.com` 直接逾時。這跟 `nba_api` 的已知問題一致 —— NBA 把一批 IP（特別是雲端供應商的 AWS/Heroku 網段）列入黑名單，症狀就是「本機跑得動、部署到雲端就掛住」。而這裡連本機都不通。

`nba_api` 自己也承認 "NBA 官網的資料介面大多沒有文件，而且經常變動"，且 "makes no guarantees about uptime, breaking changes"。GitHub issue #665 就是 `cdn.nba.com` 賽程介面 Access Denied。

**ESPN 的未公開介面反而最穩**：免認證、純 GET、回 JSON、結構多年沒大改。代價是它**沒有官方文件也沒有保證**，所以要做 schema 檢查 + 降級。

### ESPN 傷病資料的實際結構

```jsonc
{
  "timestamp": "2026-10-19T13:52:48Z",
  "season": { "year": 2027, "type": 2, "displayName": "2026-27" },
  "injuries": [{
    "id": "1", "displayName": "Atlanta Hawks",
    "injuries": [{
      "id": "-57577",
      "status": "Out",              // ← 只有 "Out" / "Day-To-Day" 兩種
      "date": "...",
      "shortComment": "Veesaar was diagnosed with a torn right ACL and is expected to miss the 2026-27 season...",
      "longComment": "Veesaar suffered the injury during a workout on Sept. 15, and an MRI confirmed...",
      "athlete": { "displayName": "Henri Veesaar", "position": {"abbreviation": "C"}, "team": {...} },
      "type": {...}, "details": {...}, "source": {...}
    }]
  }]
}
```

實測分布：**28 隊、92 筆、狀態只有 `Out` (28) 和 `Day-To-Day` (64)**。

### ⚠️ 這是 ESPN 最大的缺陷

ESPN **沒有 Q / D / P 的細分**，只有 Out / Day-To-Day。但 Yahoo 的 IL 規則是**只有 O 和 OFS 能放進 IL**。所以：

- **判斷 IL 資格 → 必須用 Yahoo 自己的 `status` 欄位**（`/team/{tk}/roster` 裡每個 player 都有）
- **ESPN 的用途是補充「為什麼」和「大概多久」** —— 那兩段 `shortComment` / `longComment` 自由文字裡有「預計缺席幾場」、「誰會吃到球權」這類訊息，Yahoo 的 player notes 沒那麼詳細
- 要 Q/D/P 細分又還沒拿到 Yahoo API → 解析 **Rotowire 傷病頁**（實測 200）或 **NBA 官方傷病報告**

### NBA 官方傷病報告 PDF 的真相

URL 格式確實是 `https://ak-static.cms.nba.com/referee/injury/Injury-Report_YYYY-MM-DD_HHPM.pdf`（路徑裡的 `referee` 是命名怪癖，內容是球員不是裁判）。

但實測回 **403 來自 AmazonS3** —— S3 在沒有 list 權限時用 403 代替 404，意思是**那個確切時間戳的檔案不存在**。報告一天發好幾次（10AM / 1PM / 3PM / 5PM / 8PM 都出現過），時間不固定。

**正確做法**：先抓 `official.nba.com/nba-injury-report-2025-26/` 頁面，從上面取最新報告的連結，再下載。不要猜時間戳。

而且官方規則不是「每天 5PM ET」：
- 一般比賽：賽前一天**當地時間** 17:00 前申報
- 背靠背第二場：比賽當天**當地時間** 13:00 前
- 比賽當天報告：當地時間 11:00–13:00，若 17:00 或更早開賽則 08:00–10:00
- 而且 "updated on a continual basis throughout the day"

因為是**當地時間**，固定一個 ET 時刻去抓一定會漏。

## 三、投影（projections）：這是唯一值得花錢的地方

推薦引擎需要「每個球員接下來每場比賽、每個類別的期望值」。自己從 game log 做投影可以，但要處理傷病、輪換、賽程強度、休息日，工程量不小。

| 選項 | 價格 | 提供什麼 | 評價 |
|---|---|---|---|
| **Hashtag Basketball** | **$2.50/月** | Rest-of-Season（BLEND7/14/30）+ **Short Term（STREAM7/14/30）**；類別含 FGM/FG%/FTM/FT%/3PM/3P%/PTS/A-TO/DREB/OREB/TREB/AST/STL/BLK/TO/DD | **最佳性價比。STREAM7/14/30 正是為串流設計的短期投影**，直接對應你的需求。免費只能看前 30 名，沒有 CSV 匯出（要解 HTML） |
| Basketball Monster | 付費 | 每日投影（新聞一出即時更新）、H2H 每日/每週對戰工具、Schedule Grid（每週場次/優質場次/賽程難易度） | 工具最完整，但你自己要做引擎的話重疊度高 |
| balldontlie | 免費 / $9.99 / $39.99 | 免費只有 teams/players/games 且 **5 req/min**；stats 和 injuries 要 $9.99 的 ALL-STAR | 免費版對這個系統**沒用**（沒 stats） |
| 自己算 | $0 | 從 Basketball Reference 或 ESPN game log 做加權平均 | v1 可行：近 7 場 ×0.5 + 近 30 場 ×0.3 + 本季 ×0.2，乘上傷病折扣。不精準但**對「比較兩個候補球員」已經夠用** |

**建議**：v1 先自己算（$0），跑一兩週對照實際結果。如果發現投影誤差是主要痛點，再花 $2.50/月訂 Hashtag。$2.50 比 Fantasy+ 的 $2.92 便宜而且更有用。

## 四、球員 ID 對照問題

Yahoo、ESPN、Sleeper、Basketball Reference 用**四套不同的 player ID**。要把 Yahoo 的陣容和 ESPN 的傷病接起來，必須做對照表。

**Sleeper 的 `/v1/players/nba` 是最好的對照來源** —— 實測 2,176 筆，每筆有 `full_name`、`team`、`injury_status`、`injury_body_part`，而且它的資料結構本來就是為跨平台設計的，常帶多個外部 ID。

對照策略（由強到弱）：
1. 外部 ID 直接對應（如果 Sleeper 有帶 espn_id / yahoo_id）
2. 正規化姓名 + 球隊 + 位置
3. 正規化姓名 + 球隊
4. 模糊姓名比對 → **這一層必須記 log 並人工確認**

正規化要處理：變音符號（`Moussa Diabaté`→`Moussa Diabate`、`Kristaps Porziņģis`→`Kristaps Porzingis`）、後綴（Jr./III）、縮寫（`P.J.` vs `PJ`）。

> 實測時 Sleeper 回的前幾筆剛好是 `Moussa Diabaté CHA DTD Elbow` 和 `Kristaps Porziņģis GSW Out Undisclosed` —— 第一筆就是你名單上那位，而且重音字元直接驗證了正規化的必要性。

## 五、穩健性設計

因為所有免費來源都是未公開介面：

1. **原始回應存檔**。每次抓完先把 raw JSON 寫到 `data/cache/YYYY-MM-DD/`。好處有三：可以重現當天的推薦、來源掛掉時有昨天的資料可用、事後檢討決策品質。
2. **Schema 檢查**。抓完先驗必要欄位存在、筆數在合理範圍（例如傷病筆數 20–200）。異常就告警而不是靜默產出垃圾推薦。
3. **降級鏈**：傷病 `ESPN → Sleeper → 上次快照 + 標記過期`；賽程 `ESPN scoreboard → ESPN team schedule 快取`。
4. **禮貌請求**：帶合理 User-Agent、請求之間 sleep、ESPN 每天總共也就 30~40 個請求（30 隊賽程只需開季抓一次）。Basketball Reference 明確要求 ≤20 req/min。
5. **不要在雲端跑**。NBA 封雲端 IP，ESPN 也可能跟進。就在你的 Mac 上跑 —— 反正你需要的時間點（台灣早上）你的電腦本來就開著。
