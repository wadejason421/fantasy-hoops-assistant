# 06 — 參考 Repo（開發前的研究筆記）

開發時要抄／參考的五個開源專案，以及各自要拿什麼。
其他 Dashboard、單純排先發、Draft-only、Points League 的專案都已排除。

## 核實狀態（2026-10-20 查）

五個 repo 都存在且可公開存取。但要先有心理準備：

| Repo | ★ | 語言 | 最後更新 | 說明 |
|---|---|---|---|---|
| [zer2/fantasy-basketball-optimizer](https://github.com/zer2/fantasy-basketball-optimizer) | 2 | Python | 2026-10-19 | Streamlit app for fantasy basketball optimization |
| [timurchak/Fantasy-yahoo-basketball-mcp](https://github.com/timurchak/Fantasy-yahoo-basketball-mcp) | 0 | Python | 2026-09-19 | （無描述） |
| [sharadmv/nba-fantasy-optimize](https://github.com/sharadmv/nba-fantasy-optimize) | 4 | Python | **2022-12-08** | Optimizes NBA fantasy lineup |
| [leo110047/fantasy-basketball-assistant](https://github.com/leo110047/fantasy-basketball-assistant) | 0 | Python | 2026-10-03 | Config-driven local Yahoo auction assistant |
| [E-Feng/FantasyBBallAnalytics](https://github.com/E-Feng/FantasyBBallAnalytics) | 12 | JavaScript | 2026-10-16 | Analytics to optimize fantasy basketball decisions |

> ⚠️ **星數 0–12，全都是個人小專案，不是經過驗證的函式庫。**
> sharadmv 停在 2022 年，Yahoo API 和 NBA 資料層幾乎確定已經壞掉 —— 它的價值在**演算法思路**，不是可執行的程式碼。
> 全部都要當「讀程式碼學作法」，不要當「pip install 就能用」。

---

## 1. zer2/fantasy-basketball-optimizer — 數學核心 ★★★★★

最值得當**數學核心**的參考。

有 Season Mode；Waiver 功能會把要丟的球員拿掉、把可用球員放進去重新評估整隊；Trade 會同時算**你和對方交易前後是否都變強**，支援 1x1、2x2、3x3 搜尋。

重點是它不是單純 Z-score，它的 H-score 會理解：

- Punt 某些 Category
- 已經很強的 Category 不要繼續 overkill
- 每項 Category 的邊際價值
- Position / roster slot 的機會成本

而且支援標準 9-Cat 以外的項目，程式裡已經有 **DD、FGM、FTM、3P%** 等欄位，所以 13 項結構可以直接參考。

**要拿：** 長期隊伍強度模型、13-Cat valuation、Punt / marginal value、Waiver replacement、Trade optimizer（雙方是否都受益）

> 補充：H-score 出自 Rosenof 的論文，數學推導見 [04-engine.md](04-engine.md) 第三節（含 G-score 完整公式與模擬勝率）。

---

## 2. timurchak/Fantasy-yahoo-basketball-mcp — 資料層 ★★★★★

當 **Yahoo 資料入口**。已實作 Yahoo read-only：

```
League / Roster / FA
evaluate_add_drop / evaluate_trade
recommend_adds / recommend_streamers
analyze_matchup
```

可接 BALLDONTLIE schedule，也可以透過 MCP 讓 Agent 直接使用。

FG% / FT% 的算法正確 —— 用**總命中／總出手**，不是平均球員百分比。也處理了 TO 反向、position matching、replacement cost。

**要拿：** Yahoo OAuth、自動抓 14 隊 Roster、自動抓所有 FA/Waiver、Yahoo eligibility、Matchup 資料、MCP 介面

**它自己承認的不足：**
- 沒有 calibrated category win probability
- 沒有自動 injury/news projection
- Streaming 還不是整週多次操作的 global optimizer

所以適合當**底層資料層**，不是最終決策引擎。

---

## 3. sharadmv/nba-fantasy-optimize — 勝率 objective ★★★★★

舊，但解的問題跟最終目標最接近：

```
Yahoo → 你＋對手
→ 模擬本週數據
→ 每個 Category 預估
→ 整場 matchup win probability
→ 搜尋 FA
→ random hill-climbing 找「贏球率最高的 roster」
```

它直接把 **win probability 當 optimizer 的 objective**。這點很重要，因為最後要的不是：

> Player A 的 PR 比 Player B 高

而是：

> 換 A 進來 → 這週 ≥7 Cat 勝率 **51.2% → 57.8%**

**要拿：** Monte Carlo / matchup simulation、Category 勝率、Roster 搜尋演算法、FA 候選組合搜尋

**不要拿** 它的 player model —— 主要靠近期歷史數據，而且是舊的 9-Cat 架構。

---

## 4. leo110047/fantasy-basketball-assistant — 整週實際操作 ★★★★★

解的是最麻煩的部分：**整週實際操作**。

季中系統已經會考慮 Yahoo 目前比分、剩餘每天合法先發、Daily lineup、IL 回歸、鎖定球員、本週勝率、Trade 搜尋、不等人數 Trade ＋ replacement、傷病預計回歸、加人額度、Fantasy 季後賽。

最想保留的功能是 **Backtest** —— 可以重播過去整季每天的 lineup / IL / add / matchup 結果 / playoffs，然後驗證：

> 如果真的按照這套 optimizer 操作，歷史上到底有沒有比較會贏。

**這比「模型看起來合理」重要很多。**（呼應 [04-engine.md](04-engine.md) 第七節的驗證流程。）

**要拿：** Daily 10 格排程、IL 邏輯、每週 add 限制、剩餘賽程、Playoff planning、Backtesting

**限制：** 正式 NBA data provider 還沒完全接好，Yahoo live 驗證也有限 → 參考**演算法與架構**，不要直接部署。

---

## 5. E-Feng/FantasyBBallAnalytics — 聯盟分析與 UI ★★★★☆

要它兩塊：

**全聯盟 Category strength** —— 直接計算「如果你每週跟聯盟所有隊伍打，你的 REB / AST / STL / BLK 各自勝率多少」。它的 Scoreboard 有「每隊對所有其他隊」的 Category record 概念。

**Monte Carlo matchup probability** —— 程式裡有 `getMatchupWinProbability()`，跑 10,000 次模擬。

**要拿：** League-wide PR/strength、Category win probability、Monte Carlo 呈現方式、Dashboard / UI 思路

不需要當主要 optimizer。

---

## 組合方式（不是挑一個）

```text
① timurchak      Yahoo 資料：Roster / FA / 對手 / Matchup
        ↓
② zer2           13-Cat 隊伍價值、Punt / Category balance、Trade / Waiver
        ↓
③ sharadmv       本週 Monte Carlo、P(贏 7 項以上)
        ↓
④ leo110047      Daily 10 格、IL、8 次 Add、Streaming path、Playoff
        ↓
⑤ E-Feng         全聯盟比較、Category 勝率、Dashboard
```

**第一階段最重要的三個：`timurchak + zer2 + sharadmv`。**
`leo110047` 補 Daily / Streaming / Backtest，`E-Feng` 補 league analytics 與勝率 UI。

## 五個 repo 都沒有、要自己補的

1. **Projection + Minutes + Usage + Starter + Injury**
2. **一次規劃整週 8 次 Add/Drop**（全域最佳化，不是每天貪心）
3. **完整 13-Cat Monte Carlo**
4. **直接最大化 P(至少贏 7 項)**

第 1 項的資料來源評估見 [03-data-sources.md](03-data-sources.md)，第 3、4 項的數學見 [04-engine.md](04-engine.md)。
