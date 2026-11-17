# 把 nba_proxy.py 部署到 Cloud Run

`scripts/nba_proxy.py` 要跑在一台能裝 `curl_cffi` 的機器上，App 才拿得到 NBA 官方
即時資料。這個目錄是 Cloud Run 的部署設定。

## 一、部署

一次性準備：

```bash
gcloud auth login
gcloud config set project 你的-gcp-project-id
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com
```

然後在 repo 根目錄：

```bash
PROJECT=你的-gcp-project-id ./deploy/cloudrun/deploy.sh
```

它會印出網址和一個隨機 token。兩個都記下來，App 端要用。

想自己指定 token：`PROJECT=... TOKEN=我自己的密碼 ./deploy/cloudrun/deploy.sh`

## 二、費用上限：每個設定各防掉多少

這是最常被問的一題。`deploy.sh` 已經把該設的都設好了，以下說明它們各自防什麼。

| 設定 | 防掉什麼 | 防不掉什麼 | 重要性 |
|---|---|---|---|
| `--max-instances 1` | **擴容爆炸。** 不設的話 Cloud Run 預設可以自動開到 100 個實例，被人打就是 100 倍費用。設成 1 之後，費用天花板就是「一個容器滿載跑整個月」—— 一個在定價頁查得到的固定數字，不是無上限 | 那一個容器本身的費用 | 🔴 **必要。爆帳單的風險 99% 在這一行** |
| `--min-instances 0` | **沒人用的時候還在收錢。** 0 表示閒置時容器會被收掉，不計費 | — | 🔴 必要（這是預設值，不要改大） |
| `PROXY_TOKEN` | **陌生人拿你的網址當免費 NBA API 用。** 沒帶 token 一律 401 | 請求還是會打進容器、還是會計費（只是立刻被拒、處理極快） | 🟡 建議 |
| `--timeout 30s` | 卡住的請求一直佔著實例 | — | 🟡 建議 |
| 程式內建的 5 秒快取 | 被連續輪詢時每次都真的去打 NBA | — | 🟡 已內建 |
| 預算警示 | **什麼都不防。它只會寄信給你，不會停止服務** | 一切 | 🟢 設了沒壞處，但別當成斷路器 |

**結論：`--max-instances 1` 是真正的斷路器**，其他都是錦上添花。有它在，最糟情況是一個
小容器的月租，不會是新聞上那種天價帳單。

真的想要「超過就自動關掉」，得自己接：預算警示 → Pub/Sub → Cloud Function 去
`gcloud run services update --max-instances 0`。個人用途通常不需要做到這步。

### 你的實際用量

每天看 3 小時球、App 每 5 秒抓一次 ≈ 每月 6.5 萬次請求，每次處理幾百毫秒。
Cloud Run 的免費額度（每月請求數與 vCPU 秒數）吃不完，實際上就是 $0。
具體額度與費率請看 Cloud Run 定價頁的當期數字。

## 三、App 端怎麼用

```
GET https://你的網址/scoreboard              今日所有比賽與即時比分
GET https://你的網址/boxscore/<gameId>       單場 box score（33 欄）
GET https://你的網址/playbyplay/<gameId>     單場逐球（含精確投籃座標）
GET https://你的網址/schedule                整季賽程
GET https://你的網址/healthz                 存活檢查（不需要 token）
```

每個請求帶上 token，兩種方式都可以：

```bash
curl -H "X-Proxy-Token: 你的token" https://你的網址/scoreboard
curl "https://你的網址/scoreboard?token=你的token"
```

回來的 JSON 就是 `cdn.nba.com` 的原樣內容，欄位說明見 `doc/nba-api-usage.md`。

## 四、如果部署完 /scoreboard 回 403

```json
{"error":"upstream_status","status":403}
```

這不是你設定錯，是 **`cdn.nba.com` 擋掉了 Google Cloud 的 IP**。NBA 除了檢查 TLS
指紋，也會擋某些資料中心的 IP 段。本 repo 驗證過的情況：

| 來源 IP | `cdn.nba.com` |
|---|---|
| 住宅網路 | ✅ 可以 |
| Azure（GitHub Actions） | ✅ 可以 |
| Google Cloud | ❓ 未驗證 —— 部署後第一件事就是測這個 |
| Vercel | ❌ 有公開報告被擋 |

若 GCP 被擋，換這兩條：

1. **你家的電腦 + Cloudflare Tunnel** —— 住宅 IP 最不會被擋，完全免費。
   缺點是電腦要一直開著。
2. **Azure Container Apps** —— IP 已經驗證過可行。

程式完全不用改，只是換個地方跑。
