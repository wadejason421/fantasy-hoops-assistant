# 02 — 遊戲內建功能：哪些事不用自己寫

你問「是否可以自動安排要上場的人，還是其實遊戲有內建功能做這件事」。答案是**兩者都有，但管的層次不同**。

## 一、Start Active Players（免費，所有人都有）

Yahoo 官方說明它會 "move players from your bench to your starting lineup"，但**只在這三種情況下**動作：

1. 板凳球員有比賽，而先發沒有
2. 板凳球員的位置可以填進那個先發位置
3. 先發球員受傷，且兩人都有比賽

也就是說它解的是「**空轉**」問題：避免你的先發格裡站著今天不打球的人。

## 二、Assistant GM（需要 Fantasy Plus 訂閱）

- 可以**一次排整週**（"start active players for the entire week"），也可以只排單日
- **Weekly roster transaction deadline 的聯盟不支援**

### 三個必須知道的限制（官方自己寫的）

| 限制 | 影響 |
|---|---|
| 傷病狀態**只在你按下按鈕的那一刻**檢查，之後發生的傷病它不管 | 你週日排完整週，週三有人受傷 → 它不會改 |
| 比賽延期同理，按下之後的變動一律忽略 | 同上 |
| **任何 add / drop / trade 都會重設這個設定** | 撿完人一定要回頭重排，這也是你原本資料裡「撿了人之後幾天的陣容會被重置」的根源 |

官方自己的建議是：事後回去檢查一次陣容。

### 價格

- Fantasy+ 頁面標 **$2.92/月（年繳）**
- App Store 的 In-App Purchase 顯示 Yahoo Fantasy Plus: All Sports **$34.99 ~ $59.99**（2026-03 快照），$34.99 應該就是對應年繳
- 另有 2026-08 推出的 **Fantasy Ultra $79.99/年**，主打美式足球，**對籃球沒意義，不要買**
- Fantasy+ 的功能（2021 發表時的清單，可能已變動）：Research Assistant（比較球員決定 start/sit 與 add/drop）、Start Optimal Players、Trade Insights、Advanced Stats

## 三、內建功能的天花板在哪

這是整個專案的立論點，值得講清楚。

內建功能知道的事：
- ✅ 今天誰有比賽
- ✅ 誰的狀態是 O（傷兵）
- ✅ 位置資格（誰能填 PG / C / UTIL）

內建功能**不知道**的事：
- ❌ 你**這週的對手是誰**
- ❌ 你和對手現在每個類別各差多少
- ❌ 哪 4 類你已經穩贏（不必再投資）、哪 4 類穩輸（該放棄）、哪 5 類在搖擺（決勝點）
- ❌ 自由市場上誰能**翻轉搖擺類別**
- ❌ 本週剩幾天、誰剩幾場比賽

舉例說明差別：

> 你本週 STL 落後 2.1、BLK 領先 4.0、3PM 落後 0.3。
> 板凳上 A 球員今天有比賽、場均 18 分 7 籃板 0.4 抄截 0.3 阻攻；B 球員今天也有比賽、場均 9 分 3 籃板 1.8 抄截 1.1 阻攻。
>
> **Start Active Players 只會確保兩個有比賽的人之一上場** —— 它沒有偏好。
> 如果 A 在先發格、B 在板凳，它什麼都不會做。
>
> 但正確答案是上 **B**：A 的 18 分幫不上任何搖擺類別（PTS 你已穩贏或穩輸），B 的 1.8 抄截直接打在你落後 2.1 的那一類上。

這一層判斷 —— **只對搖擺類別投資** —— 就是自建系統的全部價值。它也剛好對應你原本蒐集到的網友共識「優先鎖住你已經領先的類別，不要去追落後的類別」，以及 Hashtag Basketball 的「贏 8 比 1 也沒有加分」。

## 四、建議的組合用法

```
Start Active Players（免費）  →  當保險絲。你早上睡過頭時，至少不會空轉。
                                  前一晚睡前按一次。

你的推薦系統（唯讀 API）      →  當大腦。每天 06:30 推播「今天該把誰換上、該撿誰、為什麼」。

你的手指                       →  當執行器。30 秒內點完。
```

**不要買 Fantasy+ 的 Assistant GM**，理由：
1. 它排整週的邏輯是「有比賽就上」，和你的類別需求無關
2. 它會被你的 add/drop 重設，而你每週要撿 8 次人
3. 它按下之後不追蹤傷病，而 NBA 的傷病變動是每天的事（你原本資料裡提到球星出賽率從 86% 降到 76%）
4. 免費的 Start Active Players 已經涵蓋了保險絲的功能

如果要花錢，**$2.50/月的 Hashtag Basketball 投影（含 STREAM7/14/30）比 Fantasy+ 對這個系統有用得多** —— 見 [03-data-sources.md](03-data-sources.md)。

## 五、排陣容與交易的時間規則（已向 Yahoo 官方說明頁核對）

你原本的資料大致正確，這裡補上原文引用與修正。

### Roster change 設定（三種，看你聯盟的 Settings → Roster Changes）

| 設定 | Yahoo 原文 | 意思 |
|---|---|---|
| **Daily - Today** | "No deadline; rosters update immediately after a transaction." | 撿了馬上生效，沒有截止時間 |
| Daily - Tomorrow | "11:59 PM PT the night before; rosters are updated the following day." | 前一晚太平洋時間 23:59 截止，隔天生效 |
| Weekly | "11:59PM PT the night before the selected 'Weekly Roster' day." | 每週一次 |

### 陣容鎖定時間

- 預設（Public / Public Prize / Private 聯盟）：**"The start of the player's real-life game."**
  → **每個球員各自鎖**，不是當天第一場開打就全鎖。這點你原本的理解正確。
- Private 聯盟用 weekly roster 設定時：當天第一場開打，若當天無賽事則 23:59 PT

### IL（傷兵名單）

- 籃球只有 **IL** 這個欄位
- 可放入的狀態：**Out (O) 或 Out For Season (OFS)**
- **不可放入**：Probable (P)、Questionable (Q)、Doubtful (D)
  → 所以 **Diabaté 目前 DTD/Q，不能放 IL**，你原本的結論正確
- IL 標記在 Yahoo 的**隔夜更新後**才出現（"typically appear after our overnight update"）
- 球員真實復出後仍可一直放在 IL，但 **IL 上的球員不計分**
- 要把人移出 IL，必須有空的 active roster 位置
- 官方該頁未說明籃球有幾個 IL 格 → 去你聯盟 Settings 看

### Waiver

- Continuous waivers：所有未被選走的球員**隨時都在 waiver 上**，有人提出 claim 就啟動倒數讓別人反標
- 預設期間 **2 天**，Private 聯盟 commissioner 可設 0–7 天
- 最高 waiver priority（或 FAB 最高價）得標
- **處理時間**：Yahoo 沒有公布籃球的明確時刻。你原本資料引用的「美東凌晨 3–5 點」出自 Sportskeeda 的**美式足球**文章，不可直接套用。
  → **正確做法：去你聯盟的 Transactions log 看前幾筆 claim 實際是幾點生效的**，那是唯一可靠的答案。

### 其他

- 比賽已開打且排在先發的球員，當天不能放掉（錯誤 174）→ 要放人就在他開賽前放
- H2H 聯盟沒有球員出賽場次上限
