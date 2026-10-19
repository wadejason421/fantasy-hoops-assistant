# 07 — Yahoo API 申請範本（精簡版）

申請頁：<https://sports.yahoo.com/developer/access/>

## 填這些就好

| 欄位 | 填什麼 |
|---|---|
| Name | 你的英文姓名 |
| Business Title | `Independent developer` |
| Email | **跟 Yahoo Fantasy 帳號同一個** |
| Phone | `+886 9xxxxxxxx` |
| Business Name & Address | `Independent developer. <英文姓名>, <城市>, Taiwan` |
| Consumer-Facing Product or App Name | `Fantasy Hoops Assistant` |
| Brief Company Description | `Independent developer. Non-commercial fantasy basketball tool.` |
| Website URL or App Store Details | `https://github.com/wadejason421/fantasy-hoops-assistant` |
| Describe Your Intended Use Case | ↓ 下面那段 |
| Expected Users | **Small (< 1,000 users)** |
| Client ID | **留空**（見下） |
| Notes | **留空**（見下） |

## Use Case 欄（唯一要想的，複製貼上）

```
A read-only tool for Yahoo Fantasy Basketball category leagues.

It reads league settings, weekly matchup category totals, team rosters and
free agents, then recommends daily lineup and waiver moves based on which
categories are still competitive in that week's matchup.

Non-commercial. Used by me and a few managers in my own leagues.
Read-only access is sufficient.
```

就這樣，不用再多。Yahoo 只要三件事：**產品是什麼、讀什麼資料、誰在用**，上面三段剛好各答一件。

## Client ID 和 Notes 都留空

**Client ID**：表單那行字就是在講你這種情況 ——
"New users without a YDN account can leave this blank, access will be provisioned after approval."

網路上「先建 app 再把 Client ID 填進去」的建議，是寫給**已經有 app 的人**看的（意思是別另開新的）。
而且 yfpy #84 有開發者回報：**app 建立時間早於 Fantasy 權限開通的話，改舊 app 沒用、得重建**。
你現在搶先建反而會踩進那個狀況。讓 Yahoo 核准後配發最乾淨。

**Notes**：這欄 Yahoo 寫明是給要申請 read/write 的人用的
（"If your use case is unique and requires read/write access..."）。你不需要寫入，留空。

## 核准後建 app 時，兩個地方不能選錯

1. **Application Type 選 `Web Application`**（新版表單寫 Traditional web app）
   → 選 Installed / Native 的話 Yahoo **不發 Client Secret**，OAuth 直接死掉
2. **Redirect URI 填 `https://localhost:8000`**
   → 不要填 `oob`，Yahoo 2026/6 已經移除 OOB flow

## 送出之後

1. 等 DocuSign 協議 → 簽
2. 去 <https://sports.yahoo.com/developer/application-confirmation/>
   - 還沒有 app → 先建一個（Web Application），再填姓名 + Email + Client ID
   - 後台已出現 Fantasy Sports → 填姓名 + Email + Client ID
   - 後台沒出現 Fantasy Sports → 只填姓名 + Email，**不要填 Client ID**
3. 每天用 `GET /fantasy/v2/game/nba` 測有沒有生效

預期 2–4 週，Yahoo 不保證時程。

## 三個不要

- ❌ 不要在 Notes 要求寫入權限（拿不到，只會拖慢審核）
- ❌ 不要 Expected Users 往大的填
- ❌ 不要為了等核准而不開工 → 先做 [05-system.md](05-system.md) 的 Phase 0

> 台灣的授權問題見 [08-multiuser-and-taiwan.md](08-multiuser-and-taiwan.md)。
