#!/usr/bin/env python3
"""量「資料落後現場多久」—— cdn.nba.com 與 ESPN 同場對照，外加 TLS 指紋檢查。

這支產生的就是 doc/app-design.md 第八節那些數字。**必須在有比賽進行時跑**，
賽後跑只會看到落後秒數一直線性增加（因為沒有新動作了），那不是延遲。

量法：同一時刻分別打兩邊，取「現在時間 − 最後一個動作的實際發生時間」。
      NBA 用 play-by-play 的 timeActual，ESPN 用 plays 的 wallclock。
      死球空檔會讓這個數字膨脹，所以**最小值才是延遲的下限**，中位數包含了空檔。

用法：
    .venv/bin/python scripts/latency_probe.py              # 兩邊對照
    .venv/bin/python scripts/latency_probe.py --rounds 20  # 多測幾輪
    .venv/bin/python scripts/latency_probe.py --tls-only   # 只檢查 TLS 指紋

⚠️ 取樣陷阱：ESPN 的 plays 端點是分頁的。?limit=400 在超過 400 筆的比賽裡回的是
   第 400 筆而不是最新那筆，會量出假的數百秒延遲。所以這裡先讀 count 再要最後一頁。
"""

import argparse, datetime as dt, sys, time, urllib.request

try:
    from curl_cffi import requests as cffi
except ImportError:
    sys.exit("需要 curl_cffi：pip install curl_cffi")

HN = {"Referer": "https://www.nba.com/", "Origin": "https://www.nba.com",
      "Accept": "application/json, text/plain, */*"}
NBA = "https://cdn.nba.com/static/json/liveData"
ESPN_SB = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"
PLAYS = ("https://sports.core.api.espn.com/v2/sports/basketball/leagues/nba"
         "/events/{e}/competitions/{e}/plays")

S = cffi.Session(impersonate="chrome")
utc = lambda s: dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
now = lambda: dt.datetime.now(dt.timezone.utc)


def tls_check():
    """同一個端點、同一組 header，只換客戶端。只有瀏覽器級指紋過得了。"""
    u = f"{NBA}/scoreboard/todaysScoreboard_00.json"
    print("TLS 指紋檢查（同端點、同 header，只換客戶端）")
    for name, fn in (
        ('curl_cffi impersonate="chrome"', lambda: S.get(u, headers=HN, timeout=30).status_code),
        ("curl_cffi 不偽裝（libcurl 指紋）", lambda: cffi.get(u, headers=HN, timeout=30).status_code),
        ("Python 內建 urllib", lambda: urllib.request.urlopen(
            urllib.request.Request(u, headers={**HN, "User-Agent": "Mozilla/5.0"}), timeout=30).status),
    ):
        try:
            print(f"  {name:<34} {fn()}")
        except Exception as e:
            print(f"  {name:<34} 失敗 {type(e).__name__}: {str(e)[:60]}")


def espn_last_play(eid):
    """ESPN plays 分頁，要最後一頁才是最新動作。回傳 (play, 總筆數)。"""
    n = S.get(PLAYS.format(e=eid), params={"limit": 1}, timeout=40).json().get("count", 0)
    items = S.get(PLAYS.format(e=eid), params={"limit": 1, "page": n},
                  timeout=40).json().get("items", [])
    return (items[-1] if items else None), n


def pick_game():
    """挑一場 NBA 與 ESPN 都在進行中、而且最後動作在 60 秒內（確定在推進）的比賽。"""
    sb = S.get(f"{NBA}/scoreboard/todaysScoreboard_00.json", headers=HN,
               timeout=40).json()["scoreboard"]
    live = [g for g in sb["games"] if g["gameStatus"] == 2]
    print(f"NBA gameDate={sb['gameDate']}  進行中 {len(live)} 場：" + ", ".join(
        f"{g['awayTeam']['teamTricode']}@{g['homeTeam']['teamTricode']} "
        f"{g['gameStatusText'].strip()}" for g in live) or "（無）")
    if not live:
        sys.exit("現在沒有比賽在進行 —— 這支腳本只有比賽中跑才有意義。")

    esb = S.get(ESPN_SB, params={"dates": sb["gameDate"].replace("-", "")}, timeout=40).json()
    emap = {}
    for ev in esb.get("events", []):
        c = ev["competitions"][0]
        tri = {t["homeAway"]: t["team"]["abbreviation"] for t in c["competitors"]}
        emap[(tri.get("away"), tri.get("home"))] = (ev["id"], ev["status"]["type"]["state"])

    for g in live:
        k = (g["awayTeam"]["teamTricode"], g["homeTeam"]["teamTricode"])
        if k not in emap or emap[k][1] != "in":
            continue
        acts = S.get(f"{NBA}/playbyplay/playbyplay_{g['gameId']}.json", headers=HN,
                     timeout=40).json()["game"]["actions"]
        lag = (now() - utc(acts[-1]["timeActual"])).total_seconds()
        print(f"  候選 {k[0]}@{k[1]}  NBA 最後動作落後 {lag:.0f}s  共 {len(acts)} 筆")
        if lag < 60:
            return g["gameId"], emap[k][0], k
    sys.exit("沒有正在推進的比賽（都在暫停或剛結束）。稍後再試。")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rounds", type=int, default=9, help="測幾輪（預設 9）")
    ap.add_argument("--interval", type=int, default=7, help="每輪間隔秒數（預設 7）")
    ap.add_argument("--tls-only", action="store_true", help="只做 TLS 指紋檢查")
    a = ap.parse_args()

    tls_check()
    if a.tls_only:
        return 0
    print()

    gid, eid, k = pick_game()
    print(f"\n量 {k[0]}@{k[1]}   NBA={gid}   ESPN={eid}\n")
    print(f"{'時間':<9} | {'NBA 比分':>9} {'落後':>7} | {'ESPN 比分':>10} {'落後':>7} {'筆數':>6} | 差距")
    print("-" * 80)

    nl, el = [], []
    for i in range(a.rounds):
        acts = S.get(f"{NBA}/playbyplay/playbyplay_{gid}.json", headers=HN,
                     timeout=40).json()["game"]["actions"]
        ep, n = espn_last_play(eid)
        t = now()

        na = acts[-1]
        n_lag = (t - utc(na["timeActual"])).total_seconds()
        if ep and ep.get("wallclock"):
            e_lag = (t - utc(ep["wallclock"])).total_seconds()
            e_score = f"{ep.get('awayScore')}-{ep.get('homeScore')}"
        else:
            e_lag, e_score = float("nan"), "?"

        nl.append(n_lag); el.append(e_lag)
        print(f"{t.strftime('%H:%M:%S'):<9} | {na.get('scoreAway')}-{na.get('scoreHome'):<6} "
              f"{n_lag:>6.1f}s | {e_score:>10} {e_lag:>6.1f}s {n:>6} | ESPN 慢 {e_lag - n_lag:+.1f}s")
        if i < a.rounds - 1:
            time.sleep(a.interval)

    mid = lambda v: sorted(v)[len(v) // 2]
    print(f"\ncdn.nba.com  最小 {min(nl):5.1f}s  中位 {mid(nl):5.1f}s")
    print(f"ESPN         最小 {min(el):5.1f}s  中位 {mid(el):5.1f}s")
    print("\n最小值是延遲下限；中位數含死球空檔，不是延遲。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
