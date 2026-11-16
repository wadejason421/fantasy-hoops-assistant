#!/usr/bin/env python3
"""雲端可行性探針 —— 回答「資料中心 IP 能不能抓 NBA 官方資料」。

背景：本機（住宅 IP）已確認 NBA 擋的是 TLS 指紋，curl_cffi 偽裝 Chrome 就全部 200。
但「資料中心 IP 是否另外被封」沒人驗證過 —— 網路上那些「部署到雲端就掛」的報告
全部用普通 requests 跑，而普通 requests 從住宅 IP 也一樣失敗，所以無法區分這兩件事。

這支就是來分開它們的。在 GitHub Actions（Azure 資料中心 IP）上跑。

判定方式不只看 HTTP 200 —— 每個端點都會驗證回傳內容真的有資料，
避免「200 但內容是錯誤頁」的假陽性。

兩個主機要分開看 —— 實測它們的防護不一樣：
  cdn.nba.com   只做 TLS 指紋檢查。box score、play-by-play（含投籃 x/y 座標）、
                 賽程、今日比分都在這裡。這是真正的核心資料。
  stats.nba.com 指紋檢查之外，還會丟棄資料中心 IP 的封包（表現為逾時）。
                 進階數據（ORtg/TS%/USG%）和 hustle stats 在這裡。

結束碼（以 cdn 這組為準，因為那是核心資料）：
  0  cdn 可用  -> 雲端方案成行，拿得到 box score + play-by-play + 投籃座標
  1  cdn 不可用、ESPN 可用 -> 退回 ESPN
  2  兩者都不可用 -> 需要住宅代理或家用裝置
"""

import argparse, json, os, sys, time

try:
    from curl_cffi import requests as cffi
except ImportError:
    sys.exit("需要 curl_cffi：pip install curl_cffi")

CDN = "https://cdn.nba.com/static/json"
STATS = "https://stats.nba.com/stats"
ESPN_SITE = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba"
ESPN_CORE = "https://sports.core.api.espn.com/v2/sports/basketball/leagues/nba"

CHROME_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
             "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36")
NBA_H = {"Referer": "https://www.nba.com/", "Origin": "https://www.nba.com",
         "Accept": "application/json, text/plain, */*"}
STATS_H = {**NBA_H, "x-nba-stats-origin": "stats", "x-nba-stats-token": "true"}
ESPN_H = {"User-Agent": CHROME_UA, "Accept": "application/json"}

OUT_DIR = "probe-output"


# ----------------------------- 內容驗證 -----------------------------
# 每個 checker 回傳一句「看到了什麼」，內容不合預期就 raise。

def c_scoreboard(j):
    g = j["scoreboard"]["games"]
    return f"{len(g)} 場比賽, gameDate={j['scoreboard']['gameDate']}"

def c_box_live(j):
    g = j["game"]
    hp, ap = len(g["homeTeam"]["players"]), len(g["awayTeam"]["players"])
    assert hp >= 10 and ap >= 10, f"球員數異常 {ap}+{hp}"
    assert g["homeTeam"]["score"] > 0, "比分為 0"
    nstat = len(g["awayTeam"]["players"][0]["statistics"])
    return (f"{g['awayTeam']['teamTricode']} {g['awayTeam']['score']} @ "
            f"{g['homeTeam']['teamTricode']} {g['homeTeam']['score']}, "
            f"{ap}+{hp} 人, 每人 {nstat} 欄")

def c_pbp_live(j):
    a = j["game"]["actions"]
    assert len(a) >= 400, f"actions 只有 {len(a)}"
    shots = [x for x in a if x.get("isFieldGoal") and x.get("x") is not None]
    assert shots, "沒有任何帶座標的投籃"
    return f"{len(a)} actions, {len(shots)} 筆有 x/y 座標"

def c_schedule(j):
    d = j["leagueSchedule"]["gameDates"]
    assert len(d) >= 100, f"gameDates 只有 {len(d)}"
    return f"{len(d)} 個比賽日"

def c_box_v3(j):
    t = j["boxScoreTraditional"]["homeTeam"]["players"]
    assert len(t) >= 10, f"球員數 {len(t)}"
    return f"{len(t)} 名主隊球員, {len(t[0]['statistics'])} 個統計欄位"

def c_adv_v3(j):
    t = j["boxScoreAdvanced"]["homeTeam"]["players"]
    st = t[0]["statistics"]
    for k in ("offensiveRating", "trueShootingPercentage", "usagePercentage"):
        assert k in st, f"缺欄位 {k}"
    return f"{len(t)} 名球員, {len(st)} 個進階欄位"

def c_pbp_v3(j):
    a = j["game"]["actions"]
    assert len(a) >= 400, f"actions 只有 {len(a)}"
    return f"{len(a)} actions"

def c_hustle(j):
    rs = {r["name"]: r["rowSet"] for r in j["resultSets"]}
    n = len(rs.get("PlayerStats", []))
    assert n >= 15, f"PlayerStats 只有 {n} 列"
    return f"PlayerStats {n} 列"

def c_espn_sb(j):
    e = j.get("events", [])
    assert e, "events 是空的"
    return f"{len(e)} 場比賽"

def c_espn_sum(j):
    p = j["boxscore"]["players"]
    assert len(p) == 2, f"boxscore.players 有 {len(p)} 隊"
    n = len(p[0]["statistics"][0]["athletes"])
    return f"2 隊, 首隊 {n} 人, {len(j.get('plays', []))} 筆 plays"

def c_espn_plays(j):
    i = j.get("items", [])
    assert len(i) >= 400, f"items 只有 {len(i)}"
    return f"{len(i)} 筆 plays"


# ----------------------------- 執行 -----------------------------

def build_tests(gid, espn_id, espn_date):
    rng = "&StartPeriod=0&EndPeriod=14&StartRange=0&EndRange=28800&RangeType=0"
    cdn = [
        ("cdn todaysScoreboard", f"{CDN}/liveData/scoreboard/todaysScoreboard_00.json", NBA_H, c_scoreboard, None),
        ("cdn boxscore",         f"{CDN}/liveData/boxscore/boxscore_{gid}.json",        NBA_H, c_box_live, f"boxscore_{gid}.json"),
        ("cdn playbyplay",       f"{CDN}/liveData/playbyplay/playbyplay_{gid}.json",    NBA_H, c_pbp_live, f"playbyplay_{gid}.json"),
        ("cdn scheduleLeagueV2", f"{CDN}/staticData/scheduleLeagueV2_32.json",          NBA_H, c_schedule, None),
    ]
    stats = [
        ("stats boxscoretradv3", f"{STATS}/boxscoretraditionalv3?GameID={gid}{rng}",    STATS_H, c_box_v3, None),
        ("stats boxscoreadvv3",  f"{STATS}/boxscoreadvancedv3?GameID={gid}{rng}",       STATS_H, c_adv_v3, None),
        ("stats playbyplayv3",   f"{STATS}/playbyplayv3?GameID={gid}&StartPeriod=0&EndPeriod=14", STATS_H, c_pbp_v3, None),
        ("stats hustlestats",    f"{STATS}/hustlestatsboxscore?GameID={gid}",           STATS_H, c_hustle, None),
    ]
    espn = [
        ("espn scoreboard", f"{ESPN_SITE}/scoreboard?dates={espn_date}", ESPN_H, c_espn_sb, None),
        ("espn summary",    f"{ESPN_SITE}/summary?event={espn_id}",      ESPN_H, c_espn_sum, None),
        ("espn plays",      f"{ESPN_CORE}/events/{espn_id}/competitions/{espn_id}/plays?limit=1000",
                            ESPN_H, c_espn_plays, None),
    ]
    return cdn, stats, espn


def run(tests, impersonate, save=False):
    """回傳 [(名稱, ok, 說明)]。

    每組都用**全新的 Session**。這很重要：Akamai 會在成功的請求上發 bot-manager
    cookie（_abck / bm_sz 等），如果三組共用一個 session，偽裝組拿到的 cookie 會被
    對照組沿用，對照組就會假性通過 —— 實測踩過這個坑。
    """
    session = cffi.Session()
    rows = []
    for name, url, hdrs, check, fname in tests:
        t0 = time.time()
        try:
            kw = {"headers": hdrs, "timeout": 30}
            if impersonate:
                kw["impersonate"] = impersonate
            r = session.get(url, **kw)
            ms = int((time.time() - t0) * 1000)
            if r.status_code != 200:
                rows.append((name, False, f"HTTP {r.status_code} ({ms}ms)"))
                continue
            try:
                j = r.json()
            except Exception:
                rows.append((name, False, f"200 但不是 JSON ({ms}ms)"))
                continue
            try:
                detail = check(j)
            except Exception as e:
                rows.append((name, False, f"200 但內容不合預期: {e} ({ms}ms)"))
                continue
            rows.append((name, True, f"{detail} · {len(r.content):,}B · {ms}ms"))
            if save and fname:
                os.makedirs(OUT_DIR, exist_ok=True)
                with open(os.path.join(OUT_DIR, fname), "wb") as f:
                    f.write(r.content)
        except Exception as e:
            ms = int((time.time() - t0) * 1000)
            kind = type(e).__name__
            msg = str(e)
            if "timed out" in msg.lower() or "Timeout" in kind:
                rows.append((name, False, f"逾時 ({ms}ms)"))
            else:
                rows.append((name, False, f"{kind} ({ms}ms)"))
        time.sleep(0.4)
    return rows


def table(rows):
    w = max(len(r[0]) for r in rows)
    return "\n".join(f"  {'PASS' if ok else 'FAIL'}  {n:<{w}}  {d}" for n, ok, d in rows)


def md_table(rows):
    out = ["| 端點 | 結果 | 內容 |", "|---|---|---|"]
    for n, ok, d in rows:
        out.append(f"| `{n}` | {'✅ PASS' if ok else '❌ FAIL'} | {d} |")
    return "\n".join(out)


def egress():
    try:
        j = cffi.get("https://ipinfo.io/json", timeout=15, impersonate="chrome").json()
        return (f"{j.get('ip')} · {j.get('city')}, {j.get('country')} · "
                f"{j.get('org')}")
    except Exception as e:
        return f"(取不到: {type(e).__name__})"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--game-id", default="0022600244", help="NBA 官方 game id（需為已結束的比賽）")
    ap.add_argument("--espn-id", default="401909993", help="同一場比賽的 ESPN event id")
    ap.add_argument("--espn-date", default="20261115", help="ESPN scoreboard 日期 yyyymmdd")
    a = ap.parse_args()

    cdn_t, stats_t, espn_t = build_tests(a.game_id, a.espn_id, a.espn_date)

    print("=" * 78)
    print("NBA 雲端可行性探針")
    print("=" * 78)
    ip = egress()
    print(f"出口 IP : {ip}")
    print(f"game id : {a.game_id} (NBA) / {a.espn_id} (ESPN)")
    print()

    # 對照組先跑：用全新 session，確保它沒有任何來自偽裝請求的 cookie
    print("--- 1. 對照組：cdn.nba.com，不偽裝指紋（預期全部失敗）---")
    ctrl_rows = run(cdn_t, None)
    print(table(ctrl_rows)); print()

    print("--- 2. cdn.nba.com，impersonate=chrome（核心資料：box score + play-by-play）---")
    cdn_rows = run(cdn_t, "chrome", save=True)
    print(table(cdn_rows)); print()

    print("--- 3. stats.nba.com，impersonate=chrome（進階數據 / hustle，非必要）---")
    stats_rows = run(stats_t, "chrome")
    print(table(stats_rows)); print()

    print("--- 4. ESPN（備援方案，不需要偽裝）---")
    espn_rows = run(espn_t, None)
    print(table(espn_rows)); print()

    cdn_ok = all(ok for _, ok, _ in cdn_rows)
    stats_ok = all(ok for _, ok, _ in stats_rows)
    ctrl_blocked = not any(ok for _, ok, _ in ctrl_rows)
    espn_ok = all(ok for _, ok, _ in espn_rows)
    nba_rows = cdn_rows + stats_rows

    if cdn_ok and stats_ok:
        code, verdict = 0, "NBA 官方全部可用 —— 雲端方案成行"
        action = ("直接用 GitHub Actions 排程抓官方資料（box score、play-by-play 含投籃座標、"
                  "進階數據、hustle stats），寫進 Google Sheets 或 commit 進 repo。")
    elif cdn_ok:
        code, verdict = 0, "核心資料可用（cdn.nba.com），進階數據不可用（stats.nba.com）"
        action = ("雲端方案成行：box score、play-by-play（含投籃 x/y 座標）、賽程、即時比分都拿得到。"
                  "進階數據（ORtg/TS%/USG%）和 hustle stats 要另外想辦法 —— "
                  "住宅代理，或接受沒有。")
    elif espn_ok:
        code, verdict = 1, "NBA 官方在這個 IP 不可用，但 ESPN 可用"
        action = ("退回 ESPN：用 scripts/appscript_espn_to_sheets.gs（純 Apps Script，免費），"
                  "或在 Actions 裡抓 ESPN。代價是沒有精確投籃座標。")
    else:
        code, verdict = 2, "兩邊都不可用"
        action = "需要住宅代理，或把抓取放在家用裝置（Raspberry Pi / 常開的電腦）。"

    note = ""
    if cdn_ok and not ctrl_blocked:
        note = ("⚠️ 對照組也通過了 —— 代表 NBA 目前沒在擋任何客戶端，"
                "這次的成功不能歸因於 curl_cffi。日後若又失敗，先重跑這支確認。")
    if cdn_ok and not stats_ok:
        note += ("\nℹ️ cdn 通、stats 逾時，是已知的差異：stats.nba.com 除了指紋檢查，"
                 "還會丟棄資料中心 IP 的封包；cdn.nba.com 只檢查指紋。")

    print("=" * 78)
    print(f"結論：{verdict}")
    print(f"下一步：{action}")
    if note:
        print(note)
    print(f"exit {code}")
    print("=" * 78)

    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a") as f:
            f.write(f"# NBA 雲端可行性探針\n\n")
            f.write(f"## 結論：{verdict}\n\n**下一步**：{action}\n\n")
            if note:
                f.write(f"> {note}\n\n")
            f.write(f"- 出口 IP：`{ip}`\n")
            f.write(f"- 測試比賽：`{a.game_id}` (NBA) / `{a.espn_id}` (ESPN)\n")
            f.write(f"- 判定：cdn.nba.com **{'可用' if cdn_ok else '不可用'}** ／ "
                    f"stats.nba.com **{'可用' if stats_ok else '不可用'}** ／ "
                    f"對照組 **{'被擋（符合預期）' if ctrl_blocked else '未被擋'}** ／ "
                    f"ESPN **{'可用' if espn_ok else '不可用'}**\n\n")
            f.write("## 1. 對照組（不偽裝指紋，預期失敗）\n\n" + md_table(ctrl_rows) + "\n\n")
            f.write("## 2. cdn.nba.com — 核心資料（impersonate=chrome）\n\n" + md_table(cdn_rows) + "\n\n")
            f.write("## 3. stats.nba.com — 進階數據（impersonate=chrome）\n\n" + md_table(stats_rows) + "\n\n")
            f.write("## 4. ESPN\n\n" + md_table(espn_rows) + "\n")

    return code


if __name__ == "__main__":
    sys.exit(main())
