# App 怎麼拿到即時數據

> 調查日期：2026-11-16 ～ 11-17。所有數字都是當場實測，不是查來的。
> 相關文件：[app-design.md](app-design.md)（UI 設計與分階段）、
> [nba-api-usage.md](nba-api-usage.md)（端點與欄位）、
> [../deploy/cloudrun/README.md](../deploy/cloudrun/README.md)（部署與費用上限）

## 一、結論

```
你的 App  ──►  你的中繼站  ──►  cdn.nba.com
             (Cloud Run / 家裡電腦)    官方完整資料，落後現場 8~20 秒
```

一句話：**App 不直接打 NBA，打你自己的中繼站，中繼站用 `curl_cffi` 去打 NBA。**

這樣拿到的是官方完整資料（33 欄 box score、精確投籃座標），延遲跟 NBA 官方 App 同級。
中繼站的程式是 [`scripts/nba_proxy.py`](../scripts/nba_proxy.py)，已經寫好並實測過。

**GitHub 不能當中繼站** —— 它沒有「一直開著、有對外網址、能被打進來」的服務。
Actions 沒有網址、Pages 只能放靜態檔、Codespaces 會休眠。GitHub 在這個架構裡的角色是
**歷史資料倉庫**，不是即時來源。

## 二、為什麼要中繼站：兩道牆

`cdn.nba.com` 有兩道牆，各自擋住一種客戶端。**它們是兩件獨立的事**，常被混為一談。

| 牆 | 誰會中 | 能自己解嗎 |
|---|---|---|
| **CORS 白名單** | 瀏覽器、網頁 App | ❌ **不可能** |
| **TLS 指紋** | 原生 App、Node、Python、curl | ✅ 要能偽裝瀏覽器指紋的客戶端 |

### CORS 是白名單，不是「沒設」

實測同一個端點，只改 `Origin` 標頭：

| 送出的 Origin | 回來的 `access-control-allow-origin` |
|---|---|
| `https://www.nba.com` | `https://www.nba.com` ✅ |
| `https://example.com` | **沒有這個 header** |
| `https://wadejason421.github.io` | **沒有這個 header** |
| 不帶 Origin | **沒有這個 header** |

`OPTIONS` 預檢直接回 **403**，連 CORS header 都沒有。

**所以網頁 App 這條路是死的。** 瀏覽器不准 JavaScript 偽造 `Origin`，沒有任何前端技巧
繞得過去 —— 不是「比較難」，是不可能。

### TLS 指紋：只有瀏覽器級的指紋過得了

實測同一個端點、同一組標頭，只換客戶端：

| 客戶端 | 結果 |
|---|---|
| `curl_cffi` + `impersonate="chrome"` | **200** |
| **Node 原生 `fetch`（undici）** | **200** ← 只需 `Referer`，零相依 |
| `curl_cffi` 不偽裝（普通 libcurl 指紋） | **403** |
| `curl` + 完整瀏覽器標頭 | **403** |
| Python 內建 `urllib` | **403** |

> **2026-11-17 更正。** 這張表原本只有 `curl_cffi` 與 `urllib` 三列，並依社群報告
> 寫下「Node 的 `fetch` 也被擋」。**那句話經實測不成立** —— Node 原生 `fetch`
> 只帶一個 `Referer` 就回 200，內容完整（33 個統計欄位）。
>
> 而且不是標頭的差別：把 Node 送出的每一個標頭（`Sec-Fetch-Mode: cors`、
> `Accept-Language: *`、`User-Agent: node` …）一字不差加到 `curl` 上，**仍然 403**。
> 差異在傳輸層。
>
> 在 **Azure 資料中心 IP**（GitHub Actions，未安裝任何套件）同樣四個 cdn 端點全過。
> 工具：[`scripts/node_probe.mjs`](../scripts/node_probe.mjs)

正確的模型是：**Akamai 對傳輸層指紋做判別，瀏覽器與 Node/undici 在可接受那一邊，
curl 與 Python 的 OpenSSL 握手在被擋那一邊。** `curl_cffi` 是解法之一，不是唯一解法。

有紀錄顯示 `cdn.nba.com` 大約在 **2026-06-16** 開始加上這道檢查，一批專案當時集體掛掉。

**原生 App 怎麼辦？** 原生 App 沒有 CORS 問題，但 iOS 的 `URLSession`、Android 的
`OkHttp` 都屬於「非瀏覽器指紋」這一類，而且手機 App 載不進 `curl_cffi` 這種原生函式庫。
沒有 iOS 專屬的公開報告，但從上表看風險很高。**要確定只能用你真正的 App 去測。**

中繼站同時握有兩把鑰匙：用 `curl_cffi` 偽裝 Chrome 去抓（過 TLS 指紋），
回給 App 時加上 `Access-Control-Allow-Origin`（過 CORS）。

## 三、延遲：實測數字

### 兩個資料源一樣快

量法：同一場進行中的比賽、同一時刻分別打兩邊，取「現在時間 − 最後一個動作的實際發生
時間」。死球空檔會讓這個數字膨脹，所以**最小值才是延遲的下限**，中位數包含空檔。

| 比賽 / 輪數 | `cdn.nba.com` 最小 | ESPN 最小 | ESPN 相對官方 |
|---|---|---|---|
| HOU@MIA Q4，9 輪 | 17.8 秒 | 14.7 秒 | 咬在 ±15 秒內 |
| POR@MIN Q4，3 輪 | 7.1 秒 | 44.5 秒 | 持續落後 37 秒 |
| POR@MIN Q4，16 輪 | 15.9 秒 | 9.5 秒 | 多數 ±1 秒，中間一次落後 30 秒後追上 |
| ORL@BOS Q2，12 輪（只測官方） | 7.5 秒 | — | — |

**延遲下限約 7~18 秒，兩邊同一個量級。** 這是 NBA 自己的生產延遲（記錄員輸入 → CDN），
官方 App 讀的也是同一個端點，所以誰都追不過它。官方回應的 `last-modified` 只比請求時間
早 8 秒，而且沒有 `age` / `x-cache` 標頭 —— 這條路上沒有擋著的 CDN 快取層。

差別在**穩定度**：官方平穩推進；ESPN 是突發式的，筆數會卡住十幾秒再一次跳好幾筆。
看比分無感，逐筆播報會感覺到跳動。

> ⚠️ 取樣陷阱：ESPN 的 plays 端點**是分頁的**。`?limit=400` 在超過 400 筆的比賽裡回的是
> 第 400 筆而不是最新那筆 —— 第一次測量就這樣量出 600 秒的假延遲。正確做法是先用
> `?limit=1` 讀 `count`，再要最後一頁。工具：[`scripts/latency_probe.py`](../scripts/latency_probe.py)

### 延遲是疊出來的

那 8~20 秒只存在於「抓資料的那一瞬間」。中間放什麼就加什麼：

| 路徑 | 疊了哪些層 | 你看到的延遲 |
|---|---|---|
| App → 中繼站 → NBA | ① 資料源 | **8~20 秒** |
| 本機跑 `live_watch.py` | ① 資料源 | **8~20 秒** |
| App → raw URL → Actions 存的檔 | ① + ② cron 間隔 + ③ GitHub 排程延遲 + ④ job 執行 + ⑤ raw 快取 | **10~20 分鐘** |

各層實測／已知值：

| 層 | 延遲 |
|---|---|
| ① 球場 → `cdn.nba.com` | 7~18 秒（實測） |
| ② cron 間隔（`live-nba.yml` 每 15 分鐘） | 0~15 分鐘 |
| ③ GitHub 排程本身的延遲 | 常見 5~30 分鐘，忙時整輪跳過 |
| ④ job 跑完（checkout + pip + 抓 + push） | 約 1~2 分鐘 |
| ⑤ `raw.githubusercontent.com` 快取 | **最多 5 分鐘**（實測 `cache-control: max-age=300`，第二次請求就 `x-cache: HIT`） |

**GitHub Actions 就算改成長時 job（6 小時上限、內部每 15 秒抓），天花板也只到 1~2 分鐘**
（用 `git pull` 讀）或 1~7 分鐘（用 raw URL 讀）—— 因為 git 不是即時傳輸層。
而且一天約 450 分鐘的 Actions 用量（private repo 四天就超過免費額度）、一天數百個 commit，
還有 GitHub 條款限制把 Actions 用於與該 repo 軟體開發無關的用途。不建議。

## 四、中繼站放哪裡

有兩種實作，適用的平台不同：

| 實作 | 檔案 | 需要什麼 | 可跑在 |
|---|---|---|---|
| **Node（零相依）** | [`proxy/`](../proxy/) | 只要 Node runtime | Vercel Functions、Netlify、Cloud Run、VPS、家裡電腦 |
| **Python + `curl_cffi`** | [`scripts/nba_proxy.py`](../scripts/nba_proxy.py) | 能裝原生套件 | Cloud Run、VPS、Fly.io、Railway、Render、家裡電腦 |

> 原本這裡寫「必須是能裝 `curl_cffi` 的環境」，因為當時以為只有偽裝指紋過得了。
> Node 的實測推翻了這個前提，可選平台因此多了一批（不用包 Docker）。

**Cloudflare Workers / Deno Deploy 仍是未知數** —— 它們用自己的 TLS stack
（既不是 undici 也不是 libcurl），兩種實作都不保證能過。兩份程式都內建
`/__selftest`，部署後打一下就知道，不用猜。

### 免費方案

| 選擇 | 免費夠用？ | 注意 |
|---|---|---|
| **Google Cloud Run** | ✅ 閒置不收費，請求數與 CPU 秒數有免費額度 | 要綁卡；冷啟動 1~2 秒 |
| Oracle Cloud Always Free | ✅ 一台永久免費 VM | 要綁卡，註冊較繁瑣 |
| 家裡電腦 + Cloudflare Tunnel | ✅ 完全免費、不綁卡 | 電腦要一直開 |
| Render 免費層 | ⚠️ 閒置會休眠，第一次請求要等 | 免費流量已縮減 |
| PythonAnywhere 免費 | ❌ **不能用** | 免費層只能連白名單網站，連不到 `cdn.nba.com` |

（免費條款變動頻繁，部署前自己確認當期條件。）

用量估算：每天看 3 小時球、每 5 秒抓一次 ≈ 每月 6.5 萬次請求，每次處理幾百毫秒。
落在 Cloud Run 免費額度內。

### ⚠️ 最大的未驗證風險：IP 會不會被擋

NBA 除了檢查 TLS 指紋，也會擋某些資料中心的 IP 段。

| 來源 IP | `cdn.nba.com` |
|---|---|
| 住宅網路 | ✅ 已驗證（`curl_cffi` 與 Node 都通） |
| Azure（GitHub Actions） | ✅ 已驗證（Node，四個端點全過） |
| **Google Cloud** | ❓ **沒人驗證過** |
| **Vercel** | ❓ **沒人驗證過** |

> 原本這裡把 Vercel 標成「有公開報告被擋」。再查之後**找不到 Vercel 專屬的報告** ——
> 找到的是一則「`cdn.nba.com` 拒絕資料中心流量」的泛論，而那則泛論**與我們的 Azure
> 實測矛盾**（Azure 是資料中心，四個端點全過）。
>
> 目前的證據是：**`cdn.nba.com` 不擋資料中心 IP，只有 `stats.nba.com` 擋**。
> 中繼站用不到 `stats.nba.com`，所以多數平台應該都可以 —— 但沒實測過的就是沒實測過。

**部署到 Cloud Run 後第一件事就是測 `/scoreboard`。** 若回
`{"error":"upstream_status","status":403}`，那不是設定錯誤，是這條路在 GCP 走不通。
換家裡電腦（住宅 IP 最安全）或 Azure Container Apps，程式不用改。

## 五、費用上限：每個設定防掉多少

| 設定 | 防掉什麼 | 防不掉什麼 | 重要性 |
|---|---|---|---|
| `--max-instances 1` | **擴容爆炸。** 預設可自動開到 100 個實例，被打就是 100 倍。設 1 之後天花板＝一個容器滿載整個月，是定價頁查得到的固定數字 | 那一個容器的月租 | 🔴 **真正的斷路器，99% 風險在這** |
| `--min-instances 0` | 閒置時還在收錢 | — | 🔴 必要（預設值，別改大） |
| `PROXY_TOKEN` | 陌生人拿你的網址當免費 NBA API 用 | 請求還是會進容器並計費（但立刻被拒） | 🟡 建議 |
| `--timeout 30s` | 卡住的請求一直佔著實例 | — | 🟡 建議 |
| 程式內建 5 秒快取 | 連續輪詢時每次都真的去打 NBA | — | 🟡 已內建 |
| 預算警示 | **什麼都不防，只寄信** | 一切 | 🟢 設了沒壞處，別當斷路器 |

要「超過自動關掉」得自己接：預算警示 → Pub/Sub → Cloud Function 把 max-instances 改成 0。
個人用途通常不需要。

## 六、業界實際怎麼做

架構形狀跟我們一樣 —— **App 從不直接碰數據源，一律經過自己的後端**：

```
App  ◄── 推播(WebSocket/SSE) 或輪詢 ──  自己的後端(快取 1~3 秒)  ◄── 抓 ──  數據源
```

差別在**數據源怎麼來**：

| 等級 | 做法 | 成本 | 被擋風險 |
|---|---|---|---|
| 個人專案 | 爬未公開端點 + 偽裝指紋（**就是我們現在這個**） | $0~5/月 | 🔴 高 |
| 獨立 App | 付費體育數據 API（BallDontLie 付費層約 $10~40/月、API-NBA 約 $15/月、SportsDataIO） | $15~100/月 | 🟢 低 |
| 商業 App | Sportradar（NBA 官方數據夥伴），B2B 合約 | 數千美元/月起 | 🟢 無 |

**沒有人在正式產品裡靠爬官方未公開端點。** Yahoo Fantasy、ESPN 都是**買授權**
（Sportradar、Stats Perform 這類官方數據商），付錢換「不會被擋、有文件、有 SLA」。

有趣的是：本專案原本要用的 Yahoo Fantasy API，就是大公司買了授權之後再開給開發者用的
結果 —— 我們站在那條鏈的下游。

**建議路線**：自己玩就爬 + 中繼站（$0）；哪天要上架給別人用就換付費 API。
爬的那條隨時會斷，而且斷的時機不是你能控制的。

## 七、已驗證 vs 未驗證

| 項目 | 狀態 |
|---|---|
| `cdn.nba.com` 的 CORS 是 Origin 白名單 | ✅ 實測 |
| ~~只有偽裝瀏覽器的 TLS 指紋過得了~~ **Node 原生 fetch 也可以** | ✅ 實測五種客戶端 + Azure |
| 條件式請求（`If-Modified-Since`）回 304、0 bytes | ✅ 實測，兩個中繼站實作都已支援 |
| 官方 feed 延遲下限 7~18 秒 | ✅ 實測四輪 |
| ESPN 與官方同級但突發式更新 | ✅ 實測三輪 |
| `raw.githubusercontent.com` 快取 5 分鐘 | ✅ 實測 |
| 中繼站能同時拆掉兩道牆 | ✅ 本機實測（33 欄 + 精確座標 + CORS header + token 401/200） |
| `nba_proxy.py` 讀 `PORT`、token 檢查 | ✅ 實測 |
| **Cloud Run 的 Docker 映像能建起來** | ❌ **未驗證**（沙箱的 proxy 用自簽憑證，容器內 pip 驗不過；繞過需要 host 網路，權限被擋） |
| **Google Cloud 的 IP 會不會被擋** | ❌ **未驗證 —— 部署後第一件要測的事** |
| **原生 App（URLSession / OkHttp）能否直連官方** | ❌ 未驗證，從指紋實測推測風險高 |

## 八、repo 裡的對應檔案

| 檔案 | 做什麼 |
|---|---|
| [`scripts/nba_proxy.py`](../scripts/nba_proxy.py) | 中繼站（Python + `curl_cffi`）。拆掉 CORS + TLS 兩道牆 |
| [`proxy/`](../proxy/) | 中繼站（Node，零相依）。Vercel / Workers 兩種部署 |
| [`scripts/node_probe.mjs`](../scripts/node_probe.mjs) | 驗證 Node 指紋過不過得了，可在任何平台跑 |
| [`deploy/cloudrun/`](../deploy/cloudrun/) | Cloud Run 部署：`Dockerfile`、`deploy.sh`、`README.md` |
| [`scripts/latency_probe.py`](../scripts/latency_probe.py) | 量延遲與 TLS 指紋。本文那些數字就是它產生的 |
| [`scripts/live_watch.py`](../scripts/live_watch.py) | 本機輪詢一場比賽，8~20 秒延遲，不需要任何基礎設施 |
| [`scripts/fetch_games.py`](../scripts/fetch_games.py) | 抓完整比賽資料寫成 CSV；`--live` 連進行中的也抓 |
| [`.github/workflows/live-nba.yml`](../.github/workflows/live-nba.yml) | 比賽時段每 15 分鐘跑上面那支（歷史資料用，不是即時） |
| [`.github/workflows/fetch-nba.yml`](../.github/workflows/fetch-nba.yml) | 每天收尾，補齊原始 JSON |

## 九、下一步

| 順序 | 做什麼 |
|---|---|
| 1 | 本機 `python scripts/nba_proxy.py`，確認整條路通（不用註冊任何服務） |
| 2 | 寫 App，打 `localhost:8080` 開發 |
| 3 | 部署中繼站（Cloud Run 或家裡電腦 + Cloudflare Tunnel），**第一件事測 `/scoreboard` 有沒有 403** |
| 4 | `live-nba.yml` merge 到 `main`，開始累積歷史資料（排程只讀預設分支） |
| 5 | 哪天要上架給別人用 → 換付費 API |
