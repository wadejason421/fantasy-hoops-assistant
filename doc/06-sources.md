# 06 — 來源清單（73 筆）

標記說明：
- **✅ 本次直接讀取/實測** — 我這次自己抓了頁面或發了請求
- **🔎 搜尋結果摘要** — 透過搜尋引擎取得內容摘要，未逐字讀全文
- **⚠️ 已過時** — 你原本清單裡的來源，但內容已被 2026 年的變動推翻

## A. Yahoo API 存取現狀（最關鍵的一組）

| # | 來源 | 讀到的重點 | 狀態 |
|---|---|---|---|
| 1 | [Yahoo 開發者 API 申請頁](https://sports.yahoo.com/developer/access/) | **"The Yahoo Fantasy Sports API currently provides read access only. Write access is not available at this time."** 人工審核、需說明產品與資料需求、估使用者數（Small/Medium/Large）、揭露是否僅個人使用 | ✅ |
| 2 | [Yahoo 官方 API 文件](https://sports.yahoo.com/developer/docs/) | Base URL `fantasysports.yahooapis.com/fantasy/v2`、OAuth 2.0、game/league/team/roster/player/transaction 資源、路徑格式、**Roster PUT 與 Transaction POST 的 XML 範本**、`Data provided by Yahoo! and STATS, LLC` | ✅（讀兩段，共 18 萬字） |
| 3 | [yfpy issue #84](https://github.com/uberfastman/yfpy/issues/84) | **2026-07-22 起 403 `This application is not authorized`**；07-08~07-28 分批斷；改申請核准制；需簽 DocuSign + 填 Confirmation Form；舊 app 可能要重建；回報核准需 2 週~1 個月+；重新授權/PKCE/明確 scope 都無效 | ✅ |
| 4 | [yfpy issue #79](https://github.com/uberfastman/yfpy/issues/79) | **~2025-10 新 app 的 Write 選項消失**；舊 app 仍可寫；2026-06-14 回報 write scope 已移除、OOB flow 也移除；新 app 寫入得到 `You do not have the appropriate OAuth scope permissions` | ✅ |
| 5 | [fantasy-football-mcp-public issue #18](https://github.com/derekrbreese/fantasy-football-mcp-public/issues/18) | 「Yahoo no longer self-serve provisions the Fantasy Sports API」；建議申請時附既有 Client ID；人工審核無 SLA | 🔎 |
| 6 | [Yahoo Fantasy Sports APIs 條款](https://legal.yahoo.com/us/en/yahoo/terms/product-atos/fantasysportsapi/index.html) | 須遵守 per-application rate limit（數字在各 API 文件、Yahoo 可調整）；**程式繞過限制構成違約**；一 app 一 ID 且禁腳本申請多 ID；Yahoo 可隨時變更/終止 | 🔎（直連 404，內容來自搜尋摘要） |
| 7 | [Yahoo 開發者一般條款](https://legal.yahoo.com/us/en/yahoo/terms/product-atos/apiforydn/index.html) | 明文「Fantasy Sports APIs **不**適用本條款」，走獨立條款 | 🔎 |
| 8 | [Yahoo Fantasy 開發者總覽](https://developer.yahoo.com/fantasysports) | 署名要求 `Fantasy data provided by Yahoo Fantasy` + 連回；logo 使用規範；舊 YQL 限制 20,000 signed / 2,000 unsigned calls per hour | 🔎 |
| 9 | [Pipedream issue #21907](https://github.com/PipedreamHQ/pipedream/issues/21907) | 整合方回報 Yahoo Fantasy 存取變動 | 🔎 |
| 10 | [pickandroll issue #1](https://github.com/rjskene/pickandroll/issues/1) | 專案等待 Yahoo API 核准才能套用 position eligibility / ADP | 🔎 |
| 11 | [SituationRoom PR #7](https://github.com/LindsayCole/SituationRoom/pull/7) | 核准前保留手動輸入路徑；write access 不可用，`fspt-r` 是唯一可行 scope | 🔎 |

## B. Yahoo 遊戲規則（排陣容／交易／IL）

| # | 來源 | 讀到的重點 | 狀態 |
|---|---|---|---|
| 12 | [SLN6290 交易與排陣截止](https://help.yahoo.com/kb/SLN6290.html) | Daily-Today：**"No deadline; rosters update immediately after a transaction."**；Daily-Tomorrow：11:59 PM PT 前一晚；Weekly：11:59PM PT；鎖定「**The start of the player's real-life game**」 | ✅ |
| 13 | [SLN28660 Start Active Players / Assistant GM](https://help.yahoo.com/kb/SLN28660.html) | Start Active Players 免費，三種觸發條件；Assistant GM 需 Fantasy Plus、可排整週；**傷病只在按下那刻檢查**；**add/drop/trade 會重設**；Weekly deadline 聯盟不支援 | ✅ |
| 14 | [SLN6863 傷病與 IL](https://help.yahoo.com/kb/SLN6863.html) | 籃球只有 IL 欄位；**僅 O / OFS 可放，P/Q/D 不可**；標記在隔夜更新後出現；IL 球員不計分；移出需空位 | ✅ |
| 15 | [SLN6982 Waiver 總覽](https://help.yahoo.com/kb/SLN6982.html) | Continuous waivers 所有未選走球員隨時在 waiver；**預設 2 天**，私人聯盟 0–7 天；最高 priority 得標 | 🔎 |
| 16 | [SLN6447 H2H 計分](https://help.yahoo.com/kb/SLN6447.html) | H2H 三種格式；類別制「每個 stat 視為 1 game per Game Week」 | 🔎 |
| 17 | [SLN6775 截止時間（另版）](https://help.yahoo.com/kb/SLN6775.html) | 籃球/棒球/冰球的 roster 與 lineup 截止依聯盟設定而不同 | 🔎 |
| 18 | [SLN7137 陣容管理](https://help.yahoo.com/kb/SLN7137.html) | 預先排好的未來陣容可能在撿人後重置 | 🔎 |
| 19 | [SLN22673 陣容管理（另版）](https://help.yahoo.com/kb/SLN22673.html) | 「直到該場比賽表定開打時間」皆可調整 | 🔎 |
| 20 | [SLN6786 錯誤 174](https://help.yahoo.com/kb/SLN6786.html) | 比賽已開打且排在先發的球員當天不能放掉 | ⚠️🔎（你原清單第 4，仍有效） |
| 21 | [SLN6811 Waiver 與自由球員](https://help.yahoo.com/kb/SLN6811.html) | FAB 盲標最高價得；預算用完不補 | 🔎 |
| 22 | [SLN6919 籃球聯盟預設設定](https://help.yahoo.com/kb/SLN6919.html) | 預設 Daily-Today；公開 H2H 聯盟 waiver 1 天 | 🔎 |
| 23 | [SLN7057 位置資格](https://help.yahoo.com/kb/SLN7057.html) | 籃球位置資格規則 | 🔎 |
| 24 | [SLN6941 賽後增刪位置](https://help.yahoo.com/kb/SLN6941.html) | commissioner 可改 roster positions | 🔎 |
| 25 | [SLN6784 位置出賽上限](https://help.yahoo.com/kb/SLN6784.html) | H2H 聯盟無出賽場次上限 | 🔎 |
| 26 | [SLN6118 / SLN8367 Waiver（其他版本）](https://help.yahoo.com/kb/SLN6118.html) | 同 15，不同語系/版本 | 🔎 |

## C. Yahoo Fantasy Plus / Ultra 訂閱

| # | 來源 | 讀到的重點 | 狀態 |
|---|---|---|---|
| 27 | [Yahoo Fantasy+ 頁面](https://fantasysports.yahoo.com/lp/plus) | 標 **$2.92/月（年繳）** | 🔎 |
| 28 | [App Store Yahoo Fantasy](https://apps.apple.com/app/id328415391) | IAP「Yahoo Fantasy Plus: All Sports」$34.99–$59.99（2026-03 快照） | 🔎 |
| 29 | [apppricinglab IAP 紀錄](https://apppricinglab.com/iap/apple/328415391) | 兩個 IAP 項目的價格歷史 | 🔎 |
| 30 | [FantasyNerds：Yahoo 推出 Fantasy Ultra](https://www.fantasynerds.com/news/story/2026/08/13/yahoo-fantasy-launches-fantasy-ultra-subscription-tier-1595307) | 2026-08 推出，**$79.99/年**，建構在 Fantasy Plus 之上，主打美式足球 | 🔎 |
| 31 | [Verizon/Yahoo：Fantasy Plus 發表稿](https://verizon.com/about/node/920873) | 2021 原始功能清單：Research Assistant（sit/start、add/drop）、Start Optimal Players、Trade Insights、Advanced Stats | 🔎 |

## D. Python / 其他語言 Library

| # | 來源 | 讀到的重點 | 狀態 |
|---|---|---|---|
| 32 | [yahoo_fantasy_api 文件](https://yahoo-fantasy-api.readthedocs.io/en/latest/yahoo_fantasy_api.html) | **完整方法清單**：League.settings/stat_categories/standings/matchups/free_agents/waivers/player_stats/week_date_range/edit_date；Team.roster/change_positions/add_and_drop_players/claim_player/claim_and_drop_players/propose_trade。`change_positions(time_frame, modified_lineup)` NBA 傳日期。**文件有多處不一致**（`League.matchup` 實為 `matchups`；`claim_player` 範例誤寫 `add_player(6767, faab=7)`） | ✅ |
| 33 | [yahoo_fantasy_api 索引](https://yahoo-fantasy-api.readthedocs.io/en/latest/genindex.html) | 方法索引 | 🔎 |
| 34 | [yahoo_fantasy_api introduction.rst](https://yahoo-fantasy-api.readthedocs.io/en/latest/_sources/introduction.rst.txt) | 使用範例 | 🔎 |
| 35 | [yfpy (PyPI)](https://pypi.org/project/yfpy/) | 讀取為主、NFL 導向也支援 NBA；首次授權開瀏覽器產生 token.json；新版可 `save_token_data_to_env_file=True`（需 `env_file_location`）。**其 setup 教學叫你勾 Fantasy Sports checkbox 的部分已過時** | 🔎 |
| 36 | [yahoofantasy (PyPI)](https://pypi.org/project/yahoofantasy/1.4.6) | 自帶 `yahoofantasy login` CLI；redirect URI 預設 `https://localhost:8000`；本機 HTTPS 憑證警告要略過 | 🔎 |
| 37 | [yahoo-fantasy-bot (PyPI)](https://pypi.org/project/yahoo-fantasy-bot/) | 能「像經理一樣」自動管理，**只支援 MLB 和 NHL**，籃球不支援 | 🔎 |
| 38 | [yfantasy-api (PyPI)](https://pypi.org/project/yfantasy-api/) | 鏈式寫法，唯讀；roster URL 形如 `/team/{game}.l.{league}.t.{n}/roster/players/stats;type=date;date=...` | 🔎 |
| 39 | [yahoo-fantasy-sports-api (Node)](https://github.com/whatadewitt/yahoo-fantasy-sports-api) | 交易功能曾被移除後只恢復讀取；`roster.fetch` 與 `roster.players` 的差異 | 🔎 |
| 40 | [yahoo-fantasy (npm README)](https://cdn.jsdelivr.net/npm/yahoo-fantasy@5.3.0/README.md) | Node 版用法；`access_token` 可當 query 參數 | 🔎 |
| 41 | [yahoo-fantasy-sports-api-go](https://github.com/n-ae/yahoo-fantasy-sports-api-go) | 「**不支援寫入操作**（lineup changes, add/drop, waivers, trades）」，也不含 OAuth 授權流程 | 🔎 |
| 42 | [goff (Go)](https://pkg.go.dev/github.com/Forestmb/goff) | Go 版唯讀；`Rosters` 可取聯盟全部球隊名單 | 🔎 |
| 43 | [yfantasy (Go)](https://beta.pkg.go.dev/github.com/famendola1/yfantasy) | 指出 Yahoo 官方文件不完整，唯讀 | 🔎 |
| 44 | [deez-stats (PyPI)](https://pypi.org/project/deez-stats) | 建在 spilchen 的 yahoo_fantasy_api 之上 | 🔎 |
| 45 | [espn-api (PyPI)](https://pypi.org/project/espn-api/) | 只適用 ESPN 聯盟，支援美式足球與籃球，978 stars | 🔎 |

## E. MCP / AI 工具

| # | 來源 | 讀到的重點 | 狀態 |
|---|---|---|---|
| 46 | [yahoo_fantasy_mcp (spilchen)](https://glama.ai/mcp/servers/spilchen/yahoo_fantasy_mcp) | 包裝 yahoo_fantasy_api；**"No write operations (roster changes, trades, lineup modifications) are implemented for safety"**；可查 standings/stats/matchups/roster/FA | 🔎 |
| 47 | [fantasy-baseball-mcp (dingyiyi0226)](https://glama.ai/mcp/servers/dingyiyi0226/fantasy-baseball-mcp) | **"automated browser-based workflows handle lineup adjustments... because Yahoo's write-scope API is deprecated"** —— 用登入中的瀏覽器而非 Playwright；未登入則報錯不改用別的瀏覽器 | 🔎 |
| 48 | [fantasy-football-mcp (carterfawson)](https://github.com/carterfawson/fantasy-football-mcp) | 聲稱 add/drop 與單人位置變更可用；修正了 XML 格式與 "position already filled" 錯誤。**與 read-only 的前提衝突，需自行驗證** | 🔎 |
| 49 | [fantasy-football-mcp-public (derekrbreese)](https://glama.ai/mcp/servers/derekrbreese/fantasy-football-mcp-public) | 以最佳化與分析工具為主 | 🔎 |
| 50 | [Yahoo Fantasy Baseball MCP (ChrisArrington)](https://glama.ai/mcp/servers/jimbrig/yahoo-fantasy-baseball-mcp) | 聲稱「一個請求排好每日陣容」，未說明寫入方式 | 🔎 |
| 51 | [ClawHub Yahoo 棒球工具](https://clawhub.ai/khaney64/yahoo-fantasy-baseball) | 刻意做成唯讀，只建議不動手 | ⚠️🔎（你原清單第 39） |
| 52 | [Yahoo Fantasy MCP（籃球）](https://glama.ai/mcp/servers/daqvdx65m1) | 聲稱支援籃球：看 roster、matchup、FA、球員數據；**未提改陣容** | 🔎 |
| 53 | [PixieBrix Yahoo Fantasy 整合](https://www.pixiebrix.com/integration/yahoo-fantasy-sports) | 瀏覽器端把數據拉進 lineup 畫面 | 🔎 |

## F. 演算法與策略（學術 + 社群）

| # | 來源 | 讀到的重點 | 狀態 |
|---|---|---|---|
| 54 | [arXiv:2307.02188 v5 — Static quantification of player value](https://arxiv.org/html/2307.02188v5) | **G-score 完整公式**：計數型 `(μM(q)−μM)/√(σM²+κτM²)`、TO 分子反向、命中率型 `(a_q/μA)(μR(q)−μR)/√(σR²+κτR²)`；κ=2N/(2N−1)≈1.04；**"Z-scores are equivalent to G-scores with \|W\|=1"**；Table 8：**抄截 Z 分母 1.00 vs G 分母 2.28**；模擬 G vs Z 場：Each Category 21.4%、Most Categories **32.5%**（基準 8.33%）；反向只有 0.5%/0.4% | ✅ |
| 55 | [arXiv:2409.09884 — Dynamic quantification of player value](https://arxiv.org/abs/2409.09884) | Zach Rosenof，2024-09-15。H-scoring 框架、H₀ 為 H2H 實作；涵蓋類別權重、位置分配、格式目標；**"H₀ implicitly learns to punt a subset of categories"**；頁面未提供程式碼 | ✅ |
| 56 | [arXiv:2501.00933 — Optimizing for Rotisserie](https://arxiv.org/html/2501.00933v1) | Z-score 與 SGP「fundamentally limited because they do not account for drafting context」 | 🔎 |
| 57 | [SportsEthos H2H 策略指南](https://sportsethos.com/?p=509351) | 選秀、punt、串流、賽程管理、交易的價值「依該週對手與**實際還搶得到的類別**而變」 | 🔎 |
| 58 | [SportsEthos 論壇：串流鎖定 vs 追分](https://sportsethos.com/community/fantasy-hoops-assistant-coach-lineups-trades-rate-my-team/stream-to-guarantee-or-make-up-ground/) | 「串流用來確保拿下類別」 | ⚠️🔎（你原清單第 23） |
| 59 | [Hashtag Basketball 串流教學](https://hashtagbasketball.com/fantasy-basketball/content/how-to-stream-fantasy-basketball) | 先選 6–7 個目標類別；「**贏 8 比 1 也沒有加分**」 | ⚠️🔎（你原清單第 19） |
| 60 | [RotoWire：類別聯盟策略](https://www.rotowire.com/basketball/article/fantasy-basketball-101-category-league-strategy-47437) | 9 類為 Yahoo 預設；punt 在 H2H 比 roto 更適用（只需贏多數）；最常見是 punt FT% 走大個子 | 🔎 |
| 61 | [RotoWire：9-cat 精通](https://www.rotowire.com/basketball/article/master-9-cat-fantasy-basketball-strategies-for-a-winning-season-96454) | 「越不尋常的 build 越好」，避免與其他 punter 重疊 | 🔎 |
| 62 | [AOL/Yahoo：9-cat 101（2025-26）](https://www.aol.com/sports/fantasy-basketball-9-cat-leagues-173554911.html) | 八個核心類別 + TO 為第九；社群近年往 8-cat 移動但 9-cat 仍是 Yahoo 預設 | 🔎 |
| 63 | [Action Network：punting 策略](https://www.actionnetwork.com/nba/season-long-fantasy-basketball-strategy-punting) | 每放棄一類，目標類別就要更紮實 | 🔎 |
| 64 | [RotoWire：什麼是陣容鎖定](https://www.rotowire.com/faq/what-is-lineup-lock-in-fantasy-basketball-77a9c628) | 「盡可能晚一點才鎖定陣容」 | ⚠️🔎（你原清單第 3、50 重複） |
| 65 | [AOL/Yahoo：每日陣容聯盟值得花心力](https://www.aol.com/one-fantasy-basketball-analysts-top-171446708.html) | 球星出賽率從 86% 降到 76%，每晚都要看傷病報告 | ⚠️🔎（你原清單第 24） |
| 66 | [NBA.com：Yahoo High Score 季中策略](https://www.nba.com/news/in-season-strategy-yahoo-high-score) | 最後幾個板凳位當試用；注意 usage rate 與上場時間上升的人；明星缺陣時其替補要進觀察名單 | 🔎 |
| 67 | [pydfs-lineup-optimizer](https://pydfs-lineup-optimizer.readthedocs.io/) | 給 DraftKings/FanDuel 單日賽制，**不適用整季聯盟** | ⚠️🔎（你原清單第 27） |

## G. NBA 數據來源（含本次實測）

| # | 來源 | 讀到的重點 | 狀態 |
|---|---|---|---|
| 68 | ESPN 傷病 `site.api.espn.com/apis/site/v2/sports/basketball/nba/injuries` | **實測 HTTP 200**，1.04 MB，28 隊 92 筆；狀態欄位**只有 `Out`(28) 與 `Day-To-Day`(64)**，無 Q/D/P 細分；含 `shortComment`/`longComment` 自由文字與 athlete/position/team | ✅ **實測** |
| 69 | ESPN scoreboard `.../nba/scoreboard?dates=20261020` | **實測 200**，回 3 場（BOS@DET / PHI@NY / OKC@SA）；`dates=A-B` 區間語法回 400，要逐日抓 | ✅ **實測** |
| 70 | ESPN 球隊賽程 `.../nba/teams/{id}/schedule?season=2027` | **實測 200**，80 場，首場 `2026-10-20T19:00Z Boston Celtics at Detroit Pistons` | ✅ **實測** |
| 71 | Sleeper `api.sleeper.app/v1/players/nba` | **實測 200**，2,176 人，免 key；含 `injury_status`（DTD/Out/IR）與 `injury_body_part`；實測前幾筆含 `Moussa Diabaté CHA DTD Elbow`、`Kristaps Porziņģis GSW Out Undisclosed` | ✅ **實測** |
| 72 | `cdn.nba.com/static/json/staticData/scheduleLeagueV2_32.json` | **實測 403**，加瀏覽器 UA + Referer 仍 403 → 不可用 | ✅ **實測** |
| 73 | `stats.nba.com/stats/leaguedashplayerstats` | **實測連線逾時（HTTP 000）** → 不可用 | ✅ **實測** |
| 74 | `ak-static.cms.nba.com/referee/injury/Injury-Report_*.pdf` | **實測 403 來自 AmazonS3**（S3 以 403 代替 404 → 該時間戳檔案不存在）。URL 格式 `Injury-Report_YYYY-MM-DD_HHPM.pdf` 確認存在（搜尋到 2019–2023 多筆實檔）；路徑的 `referee` 是命名怪癖，內容是球員 | ✅ **實測** |
| 75 | [official.nba.com 傷病報告頁](https://official.nba.com/nba-injury-report-2025-26/) | 申報規則：賽前一天**當地時間** 17:00；背靠背第二場當天 13:00；當天報告 11:00–13:00（17:00 或更早開賽則 08:00–10:00）；"updated on a continual basis throughout the day" → **固定 ET 時刻抓一定會漏** | 🔎 |
| 76 | `basketball-reference.com/leagues/NBA_2027_per_game.html` | **實測 200**；該站要求 ≤20 req/min | ✅ **實測** |
| 77 | `api.balldontlie.io/v1/teams` | **實測 401**，需 key；免費層只有 teams/players/games 且 5 req/min；stats 與 injuries 要 ALL-STAR $9.99/月；GOAT $39.99/月 | ✅ **實測** |
| 78 | `rotowire.com/basketball/injury-report.php` | **實測 200**；有 Q/D/P 細分（需解 HTML） | ✅ **實測** |
| 79 | [nba_api (PyPI)](https://pypi.org/project/nba_api) | 「NBA 官網資料介面大多沒有文件且經常變動」；"makes no guarantees about uptime, breaking changes"；支援 proxy / headers / timeout 參數 | 🔎 |
| 80 | [nba_api issue #665](https://github.com/swar/nba_api/issues/665) | `cdn.nba.com` 賽程介面出現 Access Denied | ⚠️🔎（你原清單第 35，本次實測確認仍然成立） |
| 81 | [nba-injury-report (PyPI)](https://pypi.org/project/nba-injury-report/) | 從 NBA 公開介面抓賽前報告（2021-22 起），輸出 JSON/CSV/pandas；介面無文件、可能隨時變動 | 🔎 |
| 82 | [basketball_reference_web_scraper](https://pypi.org/project/basketball_reference_web_scraper/) | 作者寫來估算球員產量；提供每日 box score 與整季賽程 | ⚠️🔎（你原清單第 34） |
| 83 | [pbpstats 賽程載入器](https://pbpstats.readthedocs.io/en/latest/_modules/pbpstats/data_loader/data_nba/schedule/web.html) | 從 data.nba.com 抓完整賽程 JSON（本次未測，但同網域已證實被擋） | ⚠️🔎（你原清單第 33） |
| 84 | [Zuplo：ESPN hidden API 指南](https://zuplo.com/blog/2024/10/01/espn-hidden-api-guide) | `site.api.espn.com` 免認證純 GET；路徑形如 `/apis/site/v2/sports/basketball/nba/...`；端點未公開但相對穩定；無長期穩定性保證 | 🔎 |
| 85 | [ScrapeCreators：ESPN API](https://scrapecreators.com/blog/espn-api-free-sports-data) | `site.web.api.espn.com/apis` 免 key；需自行探索端點 | 🔎 |
| 86 | [Apify 傷病報告 actors](https://apify.com/wyle/sports-injury-reports-api) | 資料來自 ESPN 與 RotoWire；自稱非官方爬蟲、與聯盟無關；付費 | 🔎 |
| 87 | [Apify NBA 賽程](https://apify.com/pintostudio/nba-schedule/api/python) | 輸入日期回當天賽程，$1.9/1,000 筆 | ⚠️🔎（你原清單第 49） |
| 88 | [Highlightly：2026 最佳 NBA API](https://highlightly.net/blogs/best-nba-apis-in-2026) | balldontlie 分層與價格比較（第三方整理，與官方頁有出入） | 🔎 |
| 89 | [Fantasy Nerds API FAQ](https://api.fantasynerds.com/getting-started/faq) | 有 NBA API；建議自行快取資料 | ⚠️🔎（你原清單第 40） |

## H. 投影與付費工具

| # | 來源 | 讀到的重點 | 狀態 |
|---|---|---|---|
| 90 | [Hashtag Basketball 投影頁](https://hashtagbasketball.com/fantasy-basketball-projections) | Rest-of-Season：BLEND7/14/30；**Short Term：STREAM7/14/30**；類別選項 FGM/FG%/FTM/FT%/3PM/3P%/PTS/A-TO/DREB/OREB/TREB/AST/STL/BLK/TO/DD；**免費只看前 30 名，完整版 $2.50/月**；無 CSV 匯出 | ✅ |
| 91 | [Basketball Monster H2H](https://basketballmonster.com/headtohead.aspx) | H2H 對戰工具與放棄類別建議 | ⚠️🔎（你原清單第 15） |
| 92 | [Basketball Monster 每日總覽](https://basketballmonster.com/DailySummary.aspx) | 每日預估新聞一出即時更新；H2H 每日與每週工具 | ⚠️🔎（你原清單第 14） |
| 93 | [Basketball Monster 賽程表](https://basketballmonster.com/ScheduleGrid.aspx) | 每週各隊場次、優質場次、賽程難易度 | ⚠️🔎（你原清單第 37） |
| 94 | [Razzball 會籍頁](https://basketball.razzball.com/membership-account/membership-checkout?level=4) | $129.99（2026-06-15 到期）—— 對照用，不建議 | 🔎 |

## I. 排程與推播

| # | 來源 | 讀到的重點 | 狀態 |
|---|---|---|---|
| 95 | [ntfy 文件](https://ntfy.readthedocs.io/en/v2.2.0/) | Python CLI `ntfy`（**與 ntfy.sh 推播服務是不同專案**）；Pushover/Telegram backend；macOS 設定檔在 `~/Library/Application Support/ntfy/ntfy.yml`；舊版在 virtualenv 內 macOS 通知失效 | 🔎 |
| 96 | [ntfy (PyPI)](https://pypi.org/project/ntfy/2.4.4/) | Pushover backend 需 YAML 設 user key；Telegram 需 `pip install ntfy[telegram]`；支援 sound/priority/device | 🔎 |

## J. 你原清單中本次未重新驗證、但仍相關的

| # | 來源 | 讀到的重點 |
|---|---|---|
| 97 | [NBA.com：新手基本建議](https://www.nba.com/news/basic-advice-new-fantasy-basketball-players) | 「及時的撿人決定會大幅影響你的賽季」 |
| 98 | [Pitcher List：季中經營](https://pitcherlist.com/fantasy-101-in-season-managing) | 撿人前先確認聯盟允不允許「當天撿、當天用」 |
| 99 | [Razzball：管理出賽場次](https://basketball.razzball.com/2010-fantasy-basketball-strategy-working-the-games-played-count/) | 「每有機會就讓他們上」 |
| 100 | [Sportskeeda：Yahoo waiver 處理時間](https://sportskeeda.com/nfl/what-time-waivers-process-fantasy-football-entire-process-espn-yahoo-explained) | 美東凌晨 3–5 點處理。**⚠️ 這是美式足球，不可套用籃球** |
| 101 | [Pipedream Yahoo 整合](https://pipedream.com/apps/yahoo-fantasy-sports) | OAuth scope `fspt-r`；目前只有棒球與美式足球的交易通知 |
| 102 | [fantasy-ga](https://pypi.org/project/fantasy-ga/) | 基因演算法排 DraftKings 陣容，不適用整季聯盟 |
| 103 | [Yahoo 說明：App 排陣容](https://help.yahoo.com/kb/fantasy-sports-app-for-ios/edit-lineup-yahoo-fantasy-sln26796.html) | App 內點先發位置即可換人 |

---

## 本次研究推翻／修正了你原清單的四件事

| 你原本的結論 | 修正後 |
|---|---|
| 「申請 app 時可以選唯讀或**讀寫**權限」（來源 10、31） | ❌ **寫入已不可用。**2025-10 新 app 失去 Write 選項，2026-06 scope 移除，申請頁明文 "Write access is not available at this time" |
| 「你到 Yahoo 開發者網站申請一個讀寫 app，把 Client ID 和 Secret 給我」 | ❌ **不是自助註冊了。**2026-07 起改人工審核申請制，要簽 DocuSign，社群回報等 2 週~1 個月+，而且只給唯讀 |
| 「我寫一支程式…要不要讓它直接幫你改陣容由你決定」 | ❌ **沒有這個選項了。**只能推薦，不能代改（除非走瀏覽器自動化，不建議 —— 見 [01 第五節](01-yahoo-api.md#五不要做的事瀏覽器自動化)） |
| 「11 月 2 日之後變早上 8 點」 | ✅ **從台灣視角看是對的。**DST 在美國 11/1（週日）結束，而 11/1 美東 19:00 的比賽 = 台灣 11/2 08:00。兩種說法不衝突，但程式要用 `zoneinfo` 換算而非寫死 |
| 「Yahoo 處理 waiver 時間大約美東凌晨 3 到 5 點…籃球應該差不多」 | ⚠️ **這是美式足球的資料，不要套用。**正解是去你聯盟的 Transactions log 看前幾筆實際生效時間 |
