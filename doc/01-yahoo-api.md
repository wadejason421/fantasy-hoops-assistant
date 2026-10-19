# 01 — Yahoo Fantasy Sports API：2026 年的真實狀況

> **這一節推翻了你先前蒐集到的資料。**你的清單裡寫「申請 app 時可以選唯讀或讀寫權限」，那是 2024 年以前的狀況。2025 年 10 月起 Write 選項消失，2026 年 7 月起整個 API 改成申請制。以下每一條都附證據。

## 一、現在要先「申請」，不是註冊就能用

申請入口：<https://sports.yahoo.com/developer/access/>

Yahoo 自己在這一頁寫的（原文引用）：

> "The Yahoo Fantasy Sports API currently provides read access only. Write access is not available at this time."
>
> "Each application is reviewed by the Yahoo Fantasy Sports team."
>
> "incomplete or insufficiently detailed submissions cannot be evaluated and will be closed without further correspondence."

申請表要填的東西：
- 你在做什麼產品、需要哪些 Yahoo Fantasy 資料
- 預估使用者數量（Small <1,000 / Medium 1,000–100,000 / Large 100,000+）→ 你選 **Small**
- 是否僅限個人或單一聯盟使用 → 要主動揭露，**這對你是加分不是扣分**，因為它說明你的用量極低
- 既有 Client ID（新用戶可留空，核准後才配發）

**時程**：Yahoo 沒有承諾 SLA。社群回報從約 2 週到 1 個月以上。有一位開發者 2026-09-21 送出申請，另一個專案的 issue 記錄「reported turnaround is two to four weeks」。

### 完整流程（從社群實際走通的路徑整理）

```
1. 填 sports.yahoo.com/developer/access/ 表單
   └─ 有舊 app 的話，把現有 Client ID 填進去，核准會掛在那個 app 上
2. 等 Yahoo 寄來 DocuSign「API Access and Use Agreement」→ 簽署
3. 依 Yahoo 信件指示填「Developer Application Confirmation Form」，附上 Client ID
4. 如果你的 app 建立時間早於 Fantasy 權限開通，必須**新建一個 app** 再送 Client ID
   （有開發者回報改舊 app 沒用）
5. 每天用一個真實請求探測（例如 GET /fantasy/v2/game/nba）
   Yahoo 的「access is live」信件常常早於實際生效
6. 預留 Client ID 更換：refresh token 綁在舊 client 上，換了就得重新授權
```

### 失敗的症狀長這樣

- `HTTP 403` + `"This application is not authorized to perform this action"`（舊 app 被收回）
- OAuth token 層的 `additional_authorization_required`（新 app 沒有 Fantasy 權限）
- 請求 `scope=fspt-rw` → `error=invalid_scope`

重試授權、明確帶 `scope=fspt-r`、PKCE、重存 API permissions、refresh token —— **社群試過，都沒用**。這不是程式問題，是帳號權限問題。

## 二、核准後能讀到什麼（對應你的需求）

Base URL：`https://fantasysports.yahooapis.com/fantasy/v2`
認證：OAuth 2.0，scope `fspt-r`
Key 格式：game `nba` 或數字 ID；league `{game_id}.l.{league_id}`；team `{league_key}.t.{n}`；player `{game_id}.p.{player_id}`

### 你每天決策需要的四個請求

| 你要知道的事 | 端點 | 備註 |
|---|---|---|
| **我和對手本週每類別的即時累積** | `/league/{lk}/scoreboard;week={w}` | **最重要的一個**。回傳 matchup 內含雙方 `team_stats` 與 `stat_winners`，一個請求就拿到全部 |
| 我今天的陣容（含傷病狀態） | `/team/{tk}/roster;date=YYYY-MM-DD` | 每個 player 有 `selected_position`、`status`（O/Q/D/P） |
| 對手的陣容 | `/team/{opp_tk}/roster;date=YYYY-MM-DD` | 對手 team_key 從 scoreboard 或 `/team/{tk}/matchups` 取得 |
| 自由球員 | `/league/{lk}/players;status=FA;sort=AR;count=50` | `status=W` 是 waiver、`status=T` 是已被選走 |

### 其他有用的端點

```
/league/{lk}/settings                    聯盟類別清單、roster positions、waiver 規則、roster change 設定
/league/{lk}/standings                   戰績
/league/{lk}/transactions;type=add,drop  交易紀錄（看別人在撿誰）
/league/{lk}/players;player_keys={k}/stats;type=date;date=YYYY-MM-DD   指定日期的球員數據
/team/{tk}/stats;type=week;week={w}      單隊單週各類別統計
/users;use_login=1/games;game_keys=nba/leagues   找出「我」在哪些聯盟、我的 team_key
/game/nba                                最輕量的探測請求，用來測試權限是否生效
```

`format=json` 參數可以把 XML 換成 JSON，但 Yahoo 的 JSON 是從 XML 機械轉換來的，結構很醜（大量數字索引的 dict）。建議用 library 處理，不要自己解。

### 可用的 Python library

| Library | 定位 | 建議 |
|---|---|---|
| **yahoo_fantasy_api** (spilchen) | 物件化封裝，`League` / `Team` / `Game` 三個類別 | **首選**。方法見下表 |
| yfpy (uberfastman) | 讀取為主，資料模型完整，以 NFL 為主但支援 NBA | 次選 |
| yahoofantasy | 自帶 `yahoofantasy login` CLI 處理 OAuth | OAuth 階段好用 |
| yfantasy-api | 鏈式寫法，唯讀 | 不需要 |

`yahoo_fantasy_api` 的方法（實際查過文件索引）：

```python
# 讀取 — 這些核准後都能用
League.settings()            League.stat_categories()     League.standings()
League.matchups(week=None)   League.teams()               League.team_key()
League.free_agents(position) League.waivers(position)      League.taken_players()
League.player_stats(ids, req_type, date=, week=, season=)
League.player_details(player)  League.percent_owned(ids)   League.ownership(ids)
League.week_date_range(week)   League.current_week()       League.edit_date()
Team.roster(week=None, day=None)   Team.matchup(week)      Team.details()

# 寫入 — 這些現在會失敗（見第三節）
Team.change_positions(time_frame, modified_lineup)   # NBA 傳日期
Team.add_and_drop_players(add_id, drop_id)
Team.claim_player(player_id, faab=None)
Team.claim_and_drop_players(add_id, drop_id, faab=None)
Team.add_player(id) / Team.drop_player(id)
Team.propose_trade(...) / accept_trade(...) / reject_trade(...)
```

> 文件有幾處不一致（`League.matchup` 其實是 `matchups`；`claim_player` 的範例誤寫成 `add_player(6767, faab=7)` 而 `add_player` 不收 faab）。拿到實際回傳再對照，不要照抄文件。

## 三、寫入已經關閉

這是整件事的轉折點，證據鏈：

| 時間 | 事件 | 來源 |
|---|---|---|
| ~2025-10 | 新建 app 的 API Permissions 不再出現 Write 選項，只有 Read。舊 app 的 key 還能寫 | yfpy issue #79（維護者在自己帳號上確認） |
| 2025-10 | 新 app 嘗試寫入 → `"You do not have the appropriate OAuth scope permissions to perform this action"` | 同上 |
| 2026-06-14 | 寫入 scope 已被移除；OAuth 的 OOB flow 也被移除 | 同上 |
| 2026-07-08 ~ 07-28 | **分批**把既有 app 的讀取權限也收掉，403 `This application is not authorized` | yfpy issue #84 |
| 2026-07 下旬～08 | 改為 sports.yahoo.com/developer 的申請核准制；建 app 時已無 Fantasy Sports 權限選項 | yfpy issue #84 |
| 2026-09 | 部分開發者簽 DocuSign + 新建 app 後恢復讀取 | yfpy issue #84 |
| 2026-10-01 | 部分恢復、部分仍在等；Yahoo 始終沒有官方公告 | yfpy issue #84 最後留言 |
| 現在 | 申請頁明文：read only，write not available | sports.yahoo.com/developer/access/ |

社群推測（無官方說法）這跟 Yahoo 推 Fantasy Plus 訂閱有關 —— 自動排陣容本來是 Fantasy+ 的賣點之一。

### 寫入的 API 格式（留作紀錄，核准 read/write 才用得到）

Yahoo 官方文件還有這些格式。**除非你的申請在 notes 欄說明了特殊需求並被核准 read/write，否則送出去會 401/403。**

改陣容 `PUT /fantasy/v2/team/{team_key}/roster`：
```xml
<?xml version="1.0"?>
<fantasy_content><roster>
  <coverage_type>date</coverage_type><date>2026-10-20</date>
  <players>
    <player><player_key>466.p.6025</player_key><position>PG</position></player>
    <player><player_key>466.p.5482</player_key><position>BN</position></player>
  </players>
</roster></fantasy_content>
```
（官方範例是 NFL 的 `coverage_type=week`；NBA 用 `date`。沒列到的球員位置保持不變，可以一次移動任意多人。）

撿人／放人／FAAB 出價 `POST /fantasy/v2/league/{league_key}/transactions`：
```xml
<?xml version='1.0'?>
<fantasy_content><transaction>
  <type>add/drop</type>
  <faab_bid>25</faab_bid>
  <players>
    <player><player_key>466.p.5484</player_key><transaction_data>
      <type>add</type><destination_team_key>466.l.1000.t.6</destination_team_key>
    </transaction_data></player>
    <player><player_key>466.p.6327</player_key><transaction_data>
      <type>drop</type><source_team_key>466.l.1000.t.6</source_team_key>
    </transaction_data></player>
  </players>
</transaction></fantasy_content>
```
（有 FAAB 的話回傳的是 waiver claim 而不是立即加入。注意官方 FAAB 範例在 drop 用了 `destination_team_key`，而純 drop 範本用 `source_team_key` —— 官方文件自己不一致，實測為準。）

## 四、用量限制與條款

- Fantasy Sports API 有**自己的**條款，不走 Yahoo 一般開發者條款（後者明文說 Fantasy 不適用）
- 條款要求遵守每個 application 的 rate limit，實際數字寫在各 API 文件裡，**Yahoo 可自行調整**
- 舊的 YQL 時代數字：signed 20,000 calls/hr、unsigned 2,000 calls/hr。現行 REST 介面的數字 Yahoo 沒有公布
- **以程式手段繞過 rate limit 構成違約**
- 一個 application 一個 ID，每個請求都要帶；**禁止用腳本申請多個 ID**
- 顯示資料要署名：`Fantasy data provided by Yahoo Fantasy` + 連回 Yahoo Fantasy。Logo 有使用規範（不可變形、改色、與其他品牌混用）
- 資料同時標注 `Data provided by Yahoo! and STATS, LLC`
- Yahoo 保留隨時變更、暫停、終止 API 的權利 —— 2026 年 7 月的事件就是這條的實踐

你的用量估計：**每天 5–10 個請求**（scoreboard 1 + 我的 roster 1 + 對手 roster 1 + FA 1~2 + settings 快取），遠低於任何可能的上限。但還是要做本地 cache，理由是穩定性不是配額。

## 五、不要做的事：瀏覽器自動化

有人做過。`dingyiyi0226/fantasy-baseball-mcp` 的 README 寫：

> automated browser-based workflows handle lineup adjustments and approved add/drop actions (Claude in Chrome or the Codex browser plugin), because Yahoo's write-scope API is deprecated

技術上可行（用你已登入的瀏覽器 session 去點 Yahoo 的網頁）。**但不建議**：

1. 繞過 Yahoo 刻意關閉的功能，等於規避產品限制
2. Yahoo 的條款禁止以程式手段規避限制
3. 風險落在你的 Yahoo **帳號**上，不只是 API key
4. 收益很低 —— 每天就是點 2~3 下。真正省時間的是「知道該點什麼」，那部分唯讀 API 就夠了

所以這份設計刻意把邊界畫在：**程式算到最後一步，推播給你，你花 30 秒點完。**
