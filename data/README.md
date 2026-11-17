# data/

自動寫入，兩支 workflow 分工：

| workflow | 什麼時候跑 | 抓什麼 |
|---|---|---|
| [`live-nba.yml`](../.github/workflows/live-nba.yml) | 比賽時段每 15 分鐘（UTC 23:00~07:59）、早場每 30 分鐘（UTC 17:00~22:59） | **進行中**的比賽，數據邊打邊更新 |
| [`fetch-nba.yml`](../.github/workflows/fetch-nba.yml) | 每天 UTC 08:23（台北 16:23）一次 | 收尾。那時全部 Final，補齊原始 JSON 與壓縮檔 |

沒有比賽在打的那幾輪不會產生 commit。

## 從哪裡開始看

**[index.csv](index.csv)** —— 一場比賽一列，累積所有日期。點進去 GitHub 會直接排成表格。
欄位：`date, gameId, away, awayScore, home, homeScore, status, periods, arena, attendance, durationMin, awayQ, homeQ`

## 目錄

```
data/
├── index.csv                           ← 入口，網頁可直接看
├── tables/<date>/
│   ├── box_score.csv                   ← 一名球員一列，44 欄，網頁可直接看
│   ├── advanced.csv                    ← 自己算的進階數據，網頁可直接看
│   ├── play_by_play.csv                ← 只在該日還有比賽沒打完時存在（未壓縮）
│   └── play_by_play.csv.gz             ← 全部打完後才出現，未壓縮的那個會被刪掉
└── raw/<date>/
    ├── boxscore_<gameId>.json.gz       ← 原始回應，真相來源，不要改
    └── playbyplay_<gameId>.json.gz
```

`<date>` 是**美東**比賽日（`YYYY-MM-DD`）。台灣時間的早上對應美東前一天晚上。

## 即時資料

比賽進行中時，`index.csv` 的 `status` 欄就是即時狀態（`Q2 1:00`、`Q3 12:00`），
`awayScore` / `homeScore` 是當下比分，`box_score.csv` 是當下的個人數據。

```bash
git pull -q && awk -F, 'NR==1 || $1=="'"$(date -u -d '5 hours ago' +%F)"'"' data/index.csv
```

三件事要先知道：

1. **延遲大約 15 分鐘，不是秒級。** GitHub 的排程 cron 經常延遲 5~30 分鐘，
   負載高時還會直接跳過某幾輪。要秒級即時只能從瀏覽器直接打 API，
   見 [`doc/app-design.md`](../doc/app-design.md)
2. **進行中的場次不寫 `raw/`。** 那裡是真相來源，半場的快照不是真相。
   等那場打完，之後任一輪看到 Final 就會補上原始 JSON
3. **`play_by_play` 在比賽中是未壓縮的 `.csv`**，全部打完後才換成 `.csv.gz`。
   因為這個檔每輪都重寫，而 git 對純文字能做 delta、對 `.gz` 不能
   （改一個 byte 就是一顆全新的 blob）。讀的時候兩個都要考慮：

```python
import glob, pandas as pd
hit = glob.glob("data/tables/2026-11-16/play_by_play.csv*")
pbp = pd.read_csv(hit[0])      # pandas 看副檔名自動解壓
```

## 每天的量

| 檔案 | 一天（約 9 場） |
|---|---|
| `box_score.csv` | 約 315 列 / 53 KB |
| `advanced.csv` | 約 217 列 / 18 KB |
| `play_by_play.csv.gz` | 約 5,255 列 / 174 KB |
| `raw/` | 18 個檔 / 334 KB |

一季（約 170 個比賽日）合計約 100 MB。

## 怎麼知道有沒有更新

由快到慢：

| 方法 | 怎麼做 |
|---|---|
| **看最後一筆資料** | 開 [index.csv](index.csv)，捲到最後一列看日期 |
| **看 commit 紀錄** | repo 首頁的 commit 列表，`data: NBA box score...` 就是自動抓的那筆 |
| **看 Actions** | Actions 分頁 → `fetch-nba`，綠勾代表成功，點進去的 Summary 有抓了幾場 |
| **手機** | 裝 GitHub App，Watch 這個 repo |
| **本機一行指令** | `git pull -q && tail -3 data/index.csv` |

**失敗會自動寄信。** 排程的 workflow 失敗時 GitHub 會寄 email 給你，所以
「沒收到信」通常就代表正常。不用每天主動檢查。

> 另一個要留意的：repo 連續 60 天沒有任何活動，GitHub 會**自動停用排程 workflow**
> 並寄信通知。這個 workflow 每天都會 commit，所以只要它在跑就不會觸發這條規則。

## 怎麼用

```bash
git pull
```

```python
import pandas as pd

idx = pd.read_csv("data/index.csv")
box = pd.read_csv("data/tables/2026-11-15/box_score.csv")
pbp = pd.read_csv("data/tables/2026-11-15/play_by_play.csv.gz")   # pandas 自動解壓

# 某人的投籃分佈（x / y 是官方座標）
sga = pbp[(pbp.playerNameI == "S. Gilgeous-Alexander") & (pbp.isFieldGoal == 1)]
sga[["period", "clock", "shotDistance", "x", "y", "descriptor", "shotResult"]]

# 整季疊起來
import glob
all_box = pd.concat(map(pd.read_csv, sorted(glob.glob("data/tables/*/box_score.csv"))))
```

原始 JSON：

```python
import gzip, json
with gzip.open("data/raw/2026-11-15/playbyplay_0022600244.json.gz") as f:
    actions = json.load(f)["game"]["actions"]
```

## 欄位說明

`box_score.csv` 的 33 個統計欄位、`play_by_play.csv.gz` 的 31 個欄位，
以及 `advanced.csv` 各指標的算法與誤差，見 [`doc/nba-api-usage.md`](../doc/nba-api-usage.md)。

## 注意

- `advanced.csv` 的 ORtg / DRtg / PACE / USG% 是**自己算的**，跟官方差 1~2%
  （`stats.nba.com` 在雲端不可用）。TS% / eFG% 與官方一致。
- **Hustle stats 沒有** —— 那是獨立的人工記錄，推導不出來。
- 重跑同一天不會重複抓：已存在的 `raw/` 檔會直接沿用，除非加 `--force`。
  這只對**已結束**的場次成立 —— 進行中的場次每輪都重抓，因為數字還在變。
- 即時模式一天會 commit 數十次（`data: NBA live snapshot (...)`）。
  repo 的 commit 紀錄會被它淹掉；不想要的話把 `live-nba.yml` 的 cron 調疏，
  或讓它推到另一個分支。
