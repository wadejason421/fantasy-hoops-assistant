# 05 — 系統設計與落地計畫

## 一、為什麼要分兩階段

因為 Yahoo API 要人工審核，社群回報 **2 週到 1 個月以上**，而且**可能不核准**。如果整個系統都建立在 Yahoo API 上，你這一個月什麼都沒有，而 NBA 球季已經開打了。

```
Phase 0  今天就能跑，完全不需要 Yahoo API
         手動維護一份 roster.yaml + ESPN 資料
         → 每天 06:30 推播：今天幾場、你名單上誰有比賽、誰的傷病狀態變了

Phase 1  Yahoo API 核准後接上
         自動抓陣容、對手、類別累積、自由球員
         → 完整的 swing 類別推薦
```

Phase 0 不是臨時替代品 —— 它的「傷病狀態變動偵測」和「今日賽程」在 Phase 1 之後仍然是系統的一部分，因為 Yahoo 的傷病標記要等隔夜更新，而 ESPN 是即時的。

## 二、架構

```
NBA_Fantasy/
├── doc/                      ← 這些設計文件
├── src/
│   ├── sources/
│   │   ├── espn.py           賽程 + 傷病（免 key，實測可用）
│   │   ├── sleeper.py        傷病備援 + 球員 ID 對照
│   │   └── yahoo.py          Phase 1：OAuth + league/team/roster/scoreboard/FA
│   ├── ids.py                四套 player ID 的對照與姓名正規化
│   ├── project.py            每球員每場的類別期望值與標準差
│   ├── engine.py             swing 類別偵測 + 勝率 + 候選排序（04 的演算法）
│   ├── explain.py            模板化的「為什麼」
│   ├── notify.py             推播
│   └── daily.py              入口
├── data/
│   ├── cache/YYYY-MM-DD/     每日原始 JSON 快照（可重現 + 降級 + 事後檢討）
│   ├── roster.yaml           Phase 0 手動名單
│   ├── league.json           Phase 1：聯盟設定快取（類別、位置、waiver 規則）
│   └── history.jsonl         每日推薦 + 實際結果，用於驗證（04 第七節）
├── secrets/                  OAuth token、推播 key（加到 .gitignore）
└── tests/
    └── test_schema.py        來源 schema 檢查
```

設計原則：
- **冪等**。同一天跑兩次結果一樣，不會重複推播
- **原始資料先落地再處理**。抓取和計算分開，計算可以離線重跑
- **來源可抽換**。`sources/` 底下每個模組回傳同一套內部資料結構

## 三、排程時間（台灣時間）

2026 年 11 月 1 日前 ET+12，之後 ET+13。程式裡**不要寫死 offset**，用 `zoneinfo` 處理：

```python
from zoneinfo import ZoneInfo
from datetime import datetime
et = datetime.now(ZoneInfo("America/New_York"))
tw = et.astimezone(ZoneInfo("Asia/Taipei"))
```

| 台灣時間 | 任務 | 為什麼是這個時間 |
|---|---|---|
| **06:30** | **主推播**：今天該排誰、該撿誰、為什麼 | 最早場（美東 19:00）台灣 07:00 開打（11/1 後 08:00）。留 30 分鐘給你操作 |
| 23:00（前一晚） | 預排 + 隔天預告 | 睡前把陣容排好 + 按一次 Start Active Players 當保險絲 |
| 週一 09:00 | 本週規劃：對手是誰、賽程格、8 次撿人額度怎麼分 | 新的一週開始，週初撿人最值錢（04 第五節） |
| 選配 10:30 | 傷病二次確認 | 美東晚場（22:00 ET = 台灣 10:00/11:00）開打前 |

> **週末注意**：美東下午場（如 13:00 ET）對應台灣凌晨 01:00–04:00。那些球員會在你睡覺時鎖定。所以**週末的陣容必須在前一晚排好**，06:30 的推播對他們已經來不及。程式要在週五晚上的推播裡特別標示這件事。

## 四、怎麼實作排程與推播

### 選項 A：Claude Code 的 Scheduled Task（最快上手）

這個 app 有排程功能，cron 用**本機時間**。好處是任務本身就是一段 prompt，不用寫 code 就能跑起來；壞處是**app 必須開著**，關著的話下次啟動才補跑。

適合 Phase 0 ——「讀 ESPN、跟昨天比對、把變動推給我」這件事用 prompt 描述就夠了。

### 選項 B：launchd + Python（最可靠，建議 Phase 1 用）

macOS 原生排程，不依賴任何 app 開著。

```xml
<!-- ~/Library/LaunchAgents/com.user.nbafantasy.daily.plist -->
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>com.user.nbafantasy.daily</string>
  <key>ProgramArguments</key>
  <array>
    <string>/Users/wubinghan/Documents/NBA_Fantasy/.venv/bin/python</string>
    <string>/Users/wubinghan/Documents/NBA_Fantasy/src/daily.py</string>
  </array>
  <key>WorkingDirectory</key><string>/Users/wubinghan/Documents/NBA_Fantasy</string>
  <key>StartCalendarInterval</key>
  <array>
    <dict><key>Hour</key><integer>6</integer><key>Minute</key><integer>30</integer></dict>
    <dict><key>Hour</key><integer>23</integer><key>Minute</key><integer>0</integer></dict>
  </array>
  <key>StandardOutPath</key><string>/tmp/nbafantasy.log</string>
  <key>StandardErrorPath</key><string>/tmp/nbafantasy.err</string>
</dict></plist>
```

載入：

```bash
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.user.nbafantasy.daily.plist
```

兩個 launchd 的坑：
1. **不會載入你的 shell profile** → 所有路徑用絕對路徑，環境變數在 plist 裡的 `EnvironmentVariables` 設
2. **Mac 睡眠中不會跑，醒來才補跑** → 06:30 的推播如果你的 Mac 夜間睡眠，會在你掀開筆電時才送出。要準時就在系統設定開「排定喚醒」，或接電源時不睡眠

### 推播到手機

| 方式 | 設定成本 | 評價 |
|---|---|---|
| **Telegram Bot** | 低：BotFather 建 bot 拿 token，`getUpdates` 拿 chat_id | **建議這個**。免費、支援 Markdown 排版（表格、粗體）、訊息長度充裕、有歷史紀錄可以往回翻 |
| Pushover | 中：一次性 $5，POST 到 messages API | 可靠、可設 priority 和聲音，但排版能力弱 |
| ntfy | 低：自架或用 ntfy.sh 公開 topic | 免費但公開 topic 等於公開你的陣容；要隱私就得自架 |
| macOS 通知 | 最低：`osascript` 或 terminal-notifier | 只在電腦前有用，字數太少，**不適合當主推播** |

推薦：**Telegram 當主推播 + macOS 通知當備援**。Telegram 的好處是你可以在手機上看完整的推薦表格，而且躺在床上就能決定，起來直接點 Yahoo app。

### 推播內容範例

```
🏀 10/20 (一) · 今日 11 場 · 台灣 07:00 首場
本週對手：Jason's Team  (目前 5–6–2)

【立即處理】
❌ Diabaté (CHA) 狀態 DTD → 今天 CHA 有比賽但他賽前決定
   ⚠️ DTD 不符 IL 資格（只有 O/OFS 可放）→ 只能放板凳
✅ 把 Keon Ellis 換上 UTIL（CHA 那格空出來）

【本週類別戰況】
🔒 已鎖定 (4)：REB 86%・FG% 91%・DD 88%・BLK 94%
⚔️ 搖擺 (5)：STL 31%・3PM 44%・AST 52%・FT% 48%・PTS 57%
🏳️ 放棄 (4)：TO 8%・FTM 11%・OREB 13%・A-TO 9%

【撿人建議】用掉第 4 次額度（本週剩 5 次）
  Keon Ellis (SAC) — 剩 3 場
  → STL 31% → 58% (+27pp)、3PM 44% → 51% (+7pp)
  → 預期贏得類別數 6.2 → 6.9
  放掉：Diabaté（主貢獻 REB/FG%，兩者都已鎖定）

📊 完整對照表：data/cache/2026-10-20/report.md
```

## 五、Phase 0 具體怎麼開始（今天）

不需要等 Yahoo。

1. **手動建 `data/roster.yaml`**：你 13 個球員的名字 + 位置 + 目前先發/板凳。從 Yahoo app 抄一次，之後有變動手動改（一週改幾次而已）
2. **寫 `sources/espn.py`**：抓 injuries + 當日 scoreboard，存進 `data/cache/`
3. **寫比對邏輯**：今天的傷病狀態 vs 昨天的快照 → 列出變動
4. **寫 `notify.py`**：Telegram
5. **掛 launchd 06:30**

這五步大概半天工作量，產出的價值已經有：**你每天早上不用自己開 app 翻 13 個球員的傷病和賽程。**

同時：
6. **立刻送出 Yahoo API 申請**。申請表裡誠實寫「個人單一聯盟使用、每天約 10 個請求、用於計算每日陣容建議」。預估使用者選 Small。這件事越早送越好，因為它是整個 Phase 1 的瓶頸，而且不花你什麼時間。

## 六、Phase 1 接上 Yahoo 的檢查清單

核准後：

- [ ] OAuth 2.0 跑通，refresh token 存到 `secrets/`（**注意：如果 Yahoo 要你換 Client ID，舊的 refresh token 會失效，要重新授權**）
- [ ] `GET /fantasy/v2/game/nba` 探測成功（最輕量的測試）
- [ ] `/users;use_login=1/games;game_keys=nba/leagues` 找出你的 league_key 和 team_key
- [ ] `/league/{lk}/settings` 抓下來存 `data/league.json` —— **逐一確認 13 個類別是哪些、方向、哪些是比率型**
- [ ] `/league/{lk}/scoreboard;week={w}` 確認能拿到雙方 team_stats
- [ ] `/team/{tk}/roster;date=...` 確認 `status` 欄位有 O/Q/D/P 細分
- [ ] `/league/{lk}/players;status=FA` 確認自由球員清單
- [ ] 建立 Yahoo ↔ ESPN ↔ Sleeper 的 player ID 對照，**模糊比對的筆數要印出來人工確認**
- [ ] 加上署名 `Fantasy data provided by Yahoo Fantasy`（條款要求，即使只有你自己看）
- [ ] 所有請求加 cache，每天總量控制在 20 個以內

## 七、風險與對策

| 風險 | 機率 | 對策 |
|---|---|---|
| Yahoo API 申請被拒或拖很久 | **中高** | Phase 0 獨立運作，不依賴它。被拒就維持手動 roster.yaml + 自己從 Yahoo app 抄類別累積（一天抄一次 13 個數字，1 分鐘） |
| Yahoo 要求換 Client ID | 中 | 預期它會發生，OAuth 流程要能重跑 |
| ESPN 未公開介面改版或封鎖 | 中 | schema 檢查 + 降級到 Sleeper + 快照 |
| 投影不準導致推薦沒價值 | **中** | 04 第七節的驗證流程。**如果每週只多贏 0.2 類就停掉**，誠實面對 |
| Mac 睡眠導致推播遲到 | 高 | 排定喚醒，或接電源不睡眠 |
| 自己每天不想看推播 | **高** | 推播要短。長報告丟檔案，推播只給三行行動項 |

最後一個風險是真的。**這個系統成功的標準不是功能多完整，是你每天早上願意花 30 秒看它。**所以推播設計比引擎設計更重要 —— 訊息開頭三行就要是「立即處理」的動作，類別戰況和理由放後面。
