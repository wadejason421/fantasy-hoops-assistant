# 08 — 朋友共用、台灣限制，與最快通過的寫法

## 一、台灣的問題：已完整查證

**結論：條款白紙黑字排除台灣，但那份條款是十年以上沒人維護的老文件，而且現在已經下架。沒有任何台灣人被拒的回報 —— 因為根本沒有人在討論這件事。**

### 查證過程

我用網頁封存站（Wayback Machine）調出 **2025-08-18** 的完整條款原文，「Licensed Uses and Restrictions」第一段逐字是：

> "The Yahoo Fantasy Sports APIs are owned by Yahoo and are licensed to you on a worldwide
> **(except for residents of, and sites or applications directed to users in, India, Japan, or Taiwan)**,
> non-exclusive, non-sublicenseable basis..."

同一份文件裡還有一條和你有關的：

> "(ii) use the Yahoo Fantasy Sports API's **in connection with any commercial activity**..." ← 禁止

（所以你和朋友自己用沒問題，**收費就不行**。）

### 這份條款有多舊？

文件裡留著這些連結：

```
http://search.yahooapis.com/webservices/register_application   ← 2010 年代就停用了
http://developer.yahoo.com/attribution/                        ← 已失效
http://developer.yahoo.com/register/                           ← 已失效
```

還自稱「最新版本請見 .../apiforydn/index.html」—— 但那份 YDN 條款自己寫著「Fantasy Sports APIs **不**適用本條款」。**Yahoo 的法務文件自己互相矛盾。**

這幾乎可以確定是十年以上沒人動過的罐頭條款。India / Japan / Taiwan 這三個被排除，最可能的原因是這三地的 Yahoo 歷來是**不同法律實體**（日本的 Yahoo! JAPAN 就是完全獨立的公司），跟「台灣開發者不受歡迎」無關。

### 現狀

| 事實 | 狀態 |
|---|---|
| 舊條款排除台灣 | ✅ 封存站原文確認 |
| 該頁面現已 404 | ✅ 我用瀏覽器實測 |
| 新的 DocuSign 協議有沒有這條 | ❓ 未公開 |
| 有台灣人因此被拒的案例 | ❌ **查不到任何一筆** |
| 台灣論壇（PTT / Dcard）有人討論 | ❌ **完全沒有** |

我搜了中文、日文關鍵字和台灣論壇，**找不到任何人在討論這個限制**。唯一相關的中文資料是一篇五年前的 Medium 文章，講用 Selenium 爬 Yahoo Fantasy NBA matchup 頁面 —— 連他都沒提 API 的地區限制。

日文那邊同樣只有條款本身被引用，沒有實際被拒的案例。

### 所以怎麼辦

**照常申請，地址照實寫 Taiwan。**理由：

1. 申請表沒問「你住哪個國家」，只問 Business Address
2. 沒有任何證據顯示審核的人會拿這條來篩
3. 真正的答案在 DocuSign 協議裡 —— **收到時先搜尋 "Taiwan" 再簽**
4. 最壞情況是被拒，成本只有你填表的十分鐘

**不要為了這條去填假地址。**被抓到是永久失去資格，而且通常在你投入很多之後才爆。

## 二、朋友可以一起用嗎？

**技術上可以，而且不用改架構。**

Yahoo 的 OAuth 2.0 是 **per-user** 模型：

```
你建 1 個 app（1 組 Client ID + Secret）
   ↓
朋友 A 點授權連結 → 在 Yahoo 自己的同意頁登入 → 你拿到 A 的 token
朋友 B 點授權連結 → 同上 → 你拿到 B 的 token
   ↓
拿 A 的 token 呼叫 API = 讀到 A 的聯盟
拿 B 的 token 呼叫 API = 讀到 B 的聯盟
```

重點：
- **一個 app 就夠**，不用每人建一個（而且 Yahoo 規定「Developers may create only a single account and must not use automated tools or other means to create multiple accounts」，想多建也不行）
- 朋友的密碼**永遠不會經過你的程式**，他們是在 Yahoo 的頁面上登入的
- 每個 user 存一組 refresh token 就好，一組 token 涵蓋他所有聯盟
- 申請表的 **Expected Users 選 Small (< 1,000 users)**，這個級距完全涵蓋「我和幾個朋友」

### 要注意的三件事

1. **安全性**：OAuth 的 `state` 參數必須綁定到發起授權的那個帳號。不然有人可以把同意連結丟給別人，然後透過自己的帳號讀到對方的聯盟。這是實際專案提過的真實風險。
2. **Token 到期**：access token 很短命，必須存 refresh token 並自動續期。
3. **⚠️ 和台灣條款疊加**：條款排除的是「residents of **and sites or applications directed to users in** Taiwan」。你的朋友如果也在台灣，那這個工具就更明確地落在「directed to users in Taiwan」裡面。**加朋友讓台灣這件事更尖銳，不是更安全。**

所以順序建議：**先自己一個人跑通、確認引擎真的有用（[04 第七節](04-engine.md) 的驗證），再考慮開放給朋友。**反正前者本來就是後者的前提。

---

## 三、★ 最快通過的寫法（不自我設限版）

你說範本不要寫會卡你之後的東西 —— 這點**完全合理，而且我上一版確實寫過頭了**。

上一版我寫了 `expected users: 1`、`not distributed`、`no other users`。那些不是 Yahoo 要求的，是我自己加的，而且如果你之後真的加了朋友，等於和申請內容不符。拿掉。

**原則：講得具體（這是通過的關鍵），但不要承諾你不需要承諾的事。**

### 逐欄（直接複製）

| 欄位 | 填這個 |
|---|---|
| Name | 你的英文姓名 |
| Business Title | `Independent developer` |
| Email | **跟 Yahoo Fantasy 帳號同一個** |
| Phone | `+886 9xxxxxxxx` |
| Business Name & Address | `Independent developer. <英文姓名>, <城市>, Taiwan` |
| Product or App Name | `Fantasy Hoops Assistant` |
| Brief Company Description | `Independent developer building a non-commercial analytics tool for Yahoo Fantasy Basketball managers.` |
| Website URL or App Store Details | **GitHub repo 網址**（見下） |
| Describe Your Intended Use Case | **見下方四行版** |
| Expected Users | **Small (< 1,000 users)** ← 這個級距就涵蓋朋友了 |
| Client ID | **留空** —— 沒有 YDN 帳號的新用戶，Yahoo 核准後才配發 |
| Notes | **留空** |

### Use Case（唯一需要用心的欄位）

```
A read-only analytics tool for Yahoo Fantasy Basketball head-to-head category
leagues with daily roster changes.

It reads league settings, weekly matchup category totals, team rosters, and
free agent lists, then computes which statistical categories are still
competitive in a manager's current weekly matchup and recommends daily lineup
and waiver decisions accordingly.

Used by me and a small group of managers in my own leagues. Expected volume is
roughly 20-50 API requests per day per user, cached locally.

Read-only access (fspt-r) is sufficient for this use case.
```

**這版拿掉了什麼**（相較我上一版）：
- ❌ `expected users: 1` → 改成 "a small group of managers"
- ❌ `not distributed` / `no public interface` / `not monetised` → 全刪
- ❌ `I will make all roster changes manually in the Yahoo Fantasy app` → 刪（沒必要承諾）
- ❌ 逐條列出端點 → 刪（講資料類別就夠，列端點反而把自己框死在那幾個）

**保留了什麼**（這些是通過的關鍵，不是枷鎖）：
- ✅ 說清楚產品是什麼、讀什麼資料、誰在用 ← Yahoo 明文要求的三件事
- ✅ `non-commercial` ← 幫助通過，而且不影響你和朋友用
- ✅ `read-only (fspt-r) is sufficient` ← **不要要求 write**，會讓審核變複雜而且你反正也拿不到

### Website 欄：把 doc/ 推上 GitHub

這欄空白或 N/A 最容易被當成 "insufficiently detailed" 直接關掉。

**最快的做法：把你現在的 `doc/` 開一個 public repo，填那個網址。**審核的人要確認這東西真實存在，而你已經有 1,000+ 行設計文件了，比任何文案都有說服力。

README 開頭放這段就好：

```markdown
# Fantasy Hoops Assistant

A read-only analytics tool for Yahoo Fantasy Basketball head-to-head category
leagues. It compares a manager's weekly category totals against their opponent's,
identifies which categories are still competitive, and recommends daily lineup
and waiver moves.

Fantasy data provided by Yahoo Fantasy.
```

推之前確認 `secrets/`、token、Client ID 沒被 commit。

---

## 四、最快通過的完整順序

```
1. 去 Yahoo Developer 建 app
   ⚠️ Application Type 必須選 Web Application / Traditional web app
      （選 Installed/Native 就拿不到 Client Secret，整條路死掉）
   ⚠️ Redirect URI 填 https://localhost:8000
      （不要填 oob — 2026/6 Yahoo 已移除 OOB flow）
   → 存下 Client ID 和 Client Secret

2. 把 doc/ 推上 GitHub public repo（10 分鐘）

3. 填 sports.yahoo.com/developer/access/
   → 用上面的四行版，Client ID 填步驟 1 拿到的
   → Expected Users 選 Small
   → Notes 留空

4. 送出，然後去做 Phase 0（不要等）

5. DocuSign 寄來時 → 先搜尋全文有沒有 "Taiwan" 再決定簽不簽

6. 簽完填 sports.yahoo.com/developer/application-confirmation/
   - 後台已出現 Fantasy Sports → 填 Name + Email + Client ID
   - 後台沒出現 → 只填 Name + Email，不填 Client ID

7. 每天用 GET /fantasy/v2/game/nba 探測
   （Yahoo 的「access is live」信常常早於實際生效）
```

預期 2–4 週，無 SLA。

### 三個不要

- ❌ 不要在 Notes 要求 read/write
- ❌ 不要 Expected Users 往大的填（Small 對你有利）
- ❌ 不要為了等核准而延後 Phase 0

---

## 五、如果最後過不了，你還有什麼

| 需要的資料 | 沒有 Yahoo API 的話 |
|---|---|
| 賽程 | ESPN（實測 200，無地區限制） |
| 傷病 | ESPN + Sleeper（實測 200，無地區限制） |
| 球員數據 | Basketball Reference（實測 200）／自己算投影 |
| **本週雙方 13 類累積** | **從 Yahoo app 手抄到 yaml，一天 60 秒** |
| 自由球員 | 從 Yahoo app 看，把有興趣的幾個名字貼進 yaml |
| 我的陣容 | `roster.yaml` 手動維護 |

**引擎完全不用改。**它吃的是數字，不在乎數字是 API 來的還是你打的。

其他平台（Sleeper 的公開 API 免認證、Fantrax 有非官方 Python wrapper）對你沒用 —— 因為**你的聯盟在 Yahoo 上，搬不走**。

---

## 本輪新增來源（32 筆）

### Yahoo 條款與授權
1. [Yahoo Fantasy Sports APIs: Terms of Use](https://legal.yahoo.com/us/en/yahoo/terms/product-atos/fantasysportsapi/index.html) — **授權排除 India, Japan, Taiwan 居民與面向該地使用者的應用**；非專屬、不可再授權；違約自動終止；Yahoo 可無預警修改條款。**⚠️ 本頁現已 404（我用瀏覽器實測），引文出自搜尋索引的舊版**
2. 同上（實測）— 用內建瀏覽器開啟回 `Page Not Found | Yahoo`，確認舊條款頁已撤下
3. [Yahoo Developer API Terms of Use](https://legal.yahoo.com/us/en/yahoo/terms/product-atos/apiforydn/index.html) — 明文「Fantasy Sports APIs 不適用本條款」
4. [Yahoo Developer Network Guidelines](https://legal.yahoo.com/us/en/yahoo/guidelines/ydn/index.html) — 商業用途政策依各 API 而異；非商業類禁止用於高流量商業網站、含廣告/聯盟連結/訂閱的變現 app、付費產品。**未提地區限制**
5. [Yahoo Terms of Service](https://legal.yahoo.com/us/en/frontier/terms/otos/index.html) — 母條款
6. [Yahoo 開發者入口](https://sports.yahoo.com/developer/) — 須先同意 API Access and Use Agreement；**監控使用量，過量時可暫時限流**；單一開發者帳號、禁自動化建立多帳號；署名 "Fantasy data provided by Yahoo Fantasy" 並連回
7. [Yahoo Fantasy API 申請頁](https://sports.yahoo.com/developer/access/) — read only；人工審核；須載明產品/資料/使用者基礎含是否限個人或單一聯盟；資料不足直接關閉
8. [Yahoo 申請確認頁](https://sports.yahoo.com/developer/application-confirmation/) — **三種情境的不同填法**：後台有 Fantasy Sports → Name+Email+Client ID；沒有 → 先簽協議再填 Name+Email（不填 Client ID）；無 app → 先建再填
9. [Yahoo Fantasy API 官方文件](https://sports.yahoo.com/developer/docs/) — base URL、資源、路徑格式

### 多人使用 / OAuth
10. [juke PR #290 — Yahoo OAuth grant](https://github.com/playjukeff/juke/pull/290) — **多人模型實作**：使用者在 Yahoo 同意頁授權，密碼與 cookie 不經過 app；每帳號一組 sealed token，`league_id="*"` 涵蓋該使用者所有聯盟；**警告 OAuth `state` 必須綁定發起帳號，否則可被誘導讀取他人聯盟**
11. [Medium: YahooSportsApi](https://medium.com/@dcheng47/yahoosportsapi-1265b0e25954) — 註冊一次取得 Consumer Key/Secret；access_token 短命須用 refresh token（該文數字較舊，需驗證）
12. [TNCasino issue #15](https://github.com/sfaizi24/TNCasino/issues/15) — 以 OAuth 接 Yahoo 作為投影來源
13. [yahoofantasy (PyPI)](https://pypi.org/project/yahoofantasy/1.4.5) — 「app 只需 read 權限」；`yahoofantasy login` CLI；`dump` 指令可匯出每週每球員表現成 CSV
14. [YahooFantasyWrapper (C#)](https://github.com/isaacrlevin/YahooFantasyWrapper) — 含授權與資料擷取的 .NET 包裝

### 核准流程實例與回報
15. [yfpy issue #84](https://github.com/uberfastman/yfpy/issues/84) — 2026-07-22 起全面 403；分批斷線；DocuSign 流程；部分人需新建 app；有人回報 2026-09-21 送件
16. [yfpy issue #79](https://github.com/uberfastman/yfpy/issues/79) — 2025-10 Write 選項消失；2026-06 write scope 與 OOB flow 移除
17. [derekrbreese/fantasy-football-mcp-public](https://github.com/derekrbreese/fantasy-football-mcp-public) — **「Creating a Yahoo developer application is no longer sufficient by itself」**；須把核准掛在既有 Client ID 上；**必須選 Web Application，Installed/Native 不發 Client Secret**
18. [同上 issue #18](https://github.com/derekrbreese/fantasy-football-mcp-public/issues/18) — Yahoo 不再自助配發；人工審核無 SLA
19. [同上 INSTALLATION.md](https://github.com/derekrbreese/fantasy-football-mcp-public/blob/main/INSTALLATION.md) — 未核准前一律 401 `additional_authorization_required`；「Refreshing tokens or recreating the app will not fix this」；**該文件建議 Redirect URI 填 `oob`，但 OOB 已於 2026-06 移除，此處已過時**
20. [tonychu805/fantasy-2026](https://github.com/tonychu805/fantasy-2026) — **籃球專案實際建議的申請用語**：「personal, non-commercial, read-only 12-team basketball league analytics tool; expected users: 1」
21. [pickandroll issue #1](https://github.com/rjskene/pickandroll/issues/1) — 等待核准才能套用 Yahoo position eligibility
22. [SituationRoom PR #7](https://github.com/LindsayCole/SituationRoom/pull/7) — 核准前保留手動輸入；`fspt-r` 是唯一可行 scope
23. [Pipedream issue #21907](https://github.com/PipedreamHQ/pipedream/issues/21907) — 整合方回報存取變動
24. [edwarddistel/yahoo-fantasy-baseball-reader](https://github.com/edwarddistel/yahoo-fantasy-baseball-reader) — 下載自己的 fantasy 資料
25. [seanconnollydev/yahoo-fantasy-football-tools](https://github.com/seanconnollydev/yahoo-fantasy-football-tools) — 個人工具案例

### 商業用途的歷史脈絡
26. [HN: 如何合法取得運動數據](https://news.ycombinator.com/item?id=1791588) — 2010 年討論授權管道
27. [HN 評論（2011）](https://news.ycombinator.com/item?id=3030594) — 「Yahoo Sports has a free API... 無商業授權選項」
28. [HN 評論（2011）](https://news.ycombinator.com/item?id=3030489) — 是否需付費給 Yahoo
29. [FanGraphs: The Yahoo Fantasy Baseball API](https://blogs.fangraphs.com/the-yahoo-fantasy-baseball-api/) — 2011 年文章稱「限非商業工具與應用」。**年代久遠，僅供脈絡**

### 替代平台（結論：對你無用，因為聯盟搬不走）
30. [Sleeper API（API Evangelist 整理）](https://providers.apievangelist.com/providers/sleeper/) — 免費唯讀 HTTP API，多數端點免認證；建議 <1,000 req/min 避免 IP 封鎖
31. [Zuplo: Sleeper API 指南](https://zuplo.com/learning-center/sleeper-api) — 無須 API key
32. [FantraxAPI（非官方）](https://github.com/meisnate12/FantraxAPI) — 作者僅以 NHL H2H Points 聯盟測試；私人聯盟需存 cookie（Selenium 登入）；徵求公開籃球聯盟以增加支援
