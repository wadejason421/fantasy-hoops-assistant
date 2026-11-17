#!/usr/bin/env python3
"""抓某一天所有已結束比賽的 box score + play-by-play，存成原始檔與表格。

資料來源是 cdn.nba.com —— 雲端（GitHub Actions）實測可用的那個主機。
只用標準函式庫 + curl_cffi，不需要 pandas，所以 Actions 裝起來很快。

產出：
  data/index.csv                        一場比賽一列。**這是入口，GitHub 網頁可直接看**
  data/tables/<date>/box_score.csv      一名球員一列（33 欄）。網頁可直接看
  data/tables/<date>/advanced.csv       自己算的進階數據。網頁可直接看
  data/tables/<date>/play_by_play.csv.gz 一個動作一列（含投籃座標），壓縮存放
  data/raw/<date>/boxscore_<id>.json.gz  原始回應，真相來源，不要改
  data/raw/<date>/playbyplay_<id>.json.gz

重複執行安全：已經抓過的「已結束」比賽會跳過（看 raw 檔在不在）。
進行中的比賽永遠重抓 —— 它的數字還在變，快取沒有意義。

用法：
  python scripts/fetch_games.py                 # 最近一個有已結束比賽的日期
  python scripts/fetch_games.py --date 2026-11-15
  python scripts/fetch_games.py --days-ago 1    # 美東的昨天
  python scripts/fetch_games.py --force         # 已抓過的也重抓
  python scripts/fetch_games.py --live          # 即時模式，見下

即時模式（--live）：
  把**進行中**的比賽也抓進來，給比賽時段每 N 分鐘跑一次的排程用。
  跟平常那一輪的差別只有三點：

  1. 進行中的場次每輪都重抓（快取只對已結束的場次生效）
  2. 進行中的場次**不寫** data/raw/ —— 那是「真相來源」，半場的快照不是真相。
     等它打完，之後任一輪看到 Final 就會把原始檔補上
  3. 該日還有比賽沒打完時，play-by-play 寫成未壓縮的 play_by_play.csv。
     因為這個檔每輪都重寫，而 git 對純文字能做 delta、對 .gz 不能。
     全部打完後的那一輪會寫出 play_by_play.csv.gz 並刪掉未壓縮的那個
"""

import argparse, csv, gzip, json, os, re, sys, time
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from advanced_stats import team_advanced, player_advanced, minutes  # noqa: E402

try:
    from curl_cffi import requests as cffi
except ImportError:
    sys.exit("需要 curl_cffi：pip install curl_cffi")

CDN = "https://cdn.nba.com/static/json"
H = {"Referer": "https://www.nba.com/", "Origin": "https://www.nba.com",
     "Accept": "application/json, text/plain, */*"}
ET = timezone(timedelta(hours=-5))          # 粗略即可，只用來推算日期

PLAYER_STATS = [
    "minutes", "points", "fieldGoalsMade", "fieldGoalsAttempted", "fieldGoalsPercentage",
    "threePointersMade", "threePointersAttempted", "threePointersPercentage",
    "twoPointersMade", "twoPointersAttempted", "twoPointersPercentage",
    "freeThrowsMade", "freeThrowsAttempted", "freeThrowsPercentage",
    "reboundsOffensive", "reboundsDefensive", "reboundsTotal",
    "assists", "steals", "blocks", "blocksReceived", "turnovers",
    "foulsPersonal", "foulsOffensive", "foulsTechnical", "foulsDrawn",
    "plus", "minus", "plusMinusPoints",
    "pointsFastBreak", "pointsInThePaint", "pointsSecondChance", "pointsFromTurnovers",
]

PBP_COLS = [
    "gameId", "actionNumber", "orderNumber", "period", "clock", "timeActual",
    "teamId", "teamTricode", "personId", "playerName", "playerNameI",
    "actionType", "subType", "descriptor", "qualifiers",
    "x", "y", "xLegacy", "yLegacy", "shotDistance", "side",
    "isFieldGoal", "shotResult", "pointsTotal",
    "scoreHome", "scoreAway", "possession",
    "assistPersonId", "assistPlayerNameInitial", "assistTotal",
    "description",
]


def get(session, url):
    r = session.get(url, headers=H, timeout=40)
    r.raise_for_status()
    return r


def mmss(iso):
    m = re.match(r"PT(\d+)M([\d.]+)S", iso or "")
    return f"{int(m.group(1))}:{int(float(m.group(2))):02d}" if m else ""


def write_gz(path, raw_bytes):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with gzip.open(path, "wb") as f:
        f.write(raw_bytes)


def write_csv(path, cols, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def write_csv_gz(path, cols, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with gzip.open(path, "wt", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


_SB = {}


def scoreboard(session):
    """todaysScoreboard，一次執行只抓一次。

    這支是 liveData，比賽進行中的 gameStatus / gameStatusText 會即時變動
    （約 10~20 秒延遲）。判斷「現在打到哪」只能靠它。
    """
    if "v" not in _SB:
        _SB["v"] = get(
            session, f"{CDN}/liveData/scoreboard/todaysScoreboard_00.json").json()["scoreboard"]
    return _SB["v"]


def pick_date(session, args):
    """決定要抓哪一天（美東日期，YYYY-MM-DD）。"""
    if args.date:
        return args.date
    if args.days_ago is not None:
        return (datetime.now(ET) - timedelta(days=args.days_ago)).strftime("%Y-%m-%d")
    # 預設：用 todaysScoreboard 的 gameDate（它指向最近一輪比賽，不是本地午夜換日）
    return scoreboard(session)["gameDate"]


def games_on(session, date_str):
    """回傳該日所有比賽 [(gameId, away, home, statusInt, statusText)]。

    目標日就是 todaysScoreboard 指向的那一輪時用 scoreboard —— 狀態是即時的。
    其他日期才去翻 staticData 的完整賽程；staticData 有 CDN 快取，
    進行中的狀態不可靠，所以不拿它判斷即時狀態（順便省下幾 MB 的下載）。
    """
    sb = scoreboard(session)
    if sb.get("gameDate") == date_str:
        return [(g["gameId"], g["awayTeam"]["teamTricode"], g["homeTeam"]["teamTricode"],
                 g["gameStatus"], g["gameStatusText"]) for g in sb["games"]]
    want = datetime.strptime(date_str, "%Y-%m-%d").strftime("%m/%d/%Y")
    sch = get(session, f"{CDN}/staticData/scheduleLeagueV2_32.json").json()
    for d in sch["leagueSchedule"]["gameDates"]:
        if d["gameDate"].startswith(want):
            return [(g["gameId"], g["awayTeam"]["teamTricode"], g["homeTeam"]["teamTricode"],
                     g["gameStatus"], g["gameStatusText"]) for g in d["games"]]
    return []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", help="美東日期 YYYY-MM-DD")
    ap.add_argument("--days-ago", type=int, help="美東的 N 天前")
    ap.add_argument("--out", default="data", help="輸出根目錄（預設 data）")
    ap.add_argument("--force", action="store_true", help="已抓過的也重抓")
    ap.add_argument("--live", action="store_true",
                    help="即時模式：進行中的比賽也抓，每輪重抓未結束的場次")
    a = ap.parse_args()

    S = cffi.Session(impersonate="chrome")
    date_str = pick_date(S, a)
    print(f"目標日期（美東）：{date_str}")

    sched = games_on(S, date_str)
    if not sched:
        print("這一天沒有比賽，結束。")
        return 0
    # gameStatus: 1=未開始 2=進行中 3=已結束
    wanted = {2, 3} if a.live else {3}
    label = "已結束或進行中" if a.live else "已結束"
    targets = [g for g in sched if g[3] in wanted]
    print(f"賽程 {len(sched)} 場，其中{label} {len(targets)} 場")
    for gid, aw, hm, st, txt in sched:
        if st not in wanted:
            print(f"  跳過 {gid} {aw}@{hm} — {txt}")
    if not targets:
        print(f"沒有{label}的比賽，結束。")
        return 0

    raw_dir = os.path.join(a.out, "raw", date_str)
    tbl_dir = os.path.join(a.out, "tables", date_str)

    box_rows, adv_rows, pbp_rows, index_rows = [], [], [], []
    fetched = skipped = live_n = 0

    for gid, aw, hm, st, txt in targets:
        is_final = st == 3
        bpath = os.path.join(raw_dir, f"boxscore_{gid}.json.gz")
        ppath = os.path.join(raw_dir, f"playbyplay_{gid}.json.gz")

        # 快取只對已結束的場次生效。進行中的數字還在變，沿用舊檔等於拿舊數據。
        if is_final and os.path.exists(bpath) and os.path.exists(ppath) and not a.force:
            with gzip.open(bpath, "rb") as f:
                box = json.load(f)
            with gzip.open(ppath, "rb") as f:
                pbp = json.load(f)
            skipped += 1
        else:
            rb = get(S, f"{CDN}/liveData/boxscore/boxscore_{gid}.json")
            rp = get(S, f"{CDN}/liveData/playbyplay/playbyplay_{gid}.json")
            # 只有打完的才寫 raw/ —— 那裡是真相來源，半場的快照不是真相。
            # 等這場打完，之後任一輪看到 Final 就會補上。
            if is_final:
                write_gz(bpath, rb.content)
                write_gz(ppath, rp.content)
            else:
                live_n += 1
                print(f"  即時 {gid} {aw}@{hm} — {txt}")
            box, pbp = rb.json(), rp.json()
            fetched += 1
            time.sleep(0.5)

        g = box["game"]
        A, Hm = g["awayTeam"], g["homeTeam"]

        index_rows.append({
            "date": date_str, "gameId": gid,
            "away": A["teamTricode"], "awayScore": A["score"],
            "home": Hm["teamTricode"], "homeScore": Hm["score"],
            "status": g["gameStatusText"], "periods": g["period"],
            "arena": g["arena"]["arenaName"], "attendance": g.get("attendance", ""),
            "durationMin": g.get("duration", ""),
            "awayQ": "/".join(str(p["score"]) for p in A.get("periods", [])),
            "homeQ": "/".join(str(p["score"]) for p in Hm.get("periods", [])),
        })

        for team, opp in ((A, Hm), (Hm, A)):
            ta = team_advanced(team, opp)
            adv_rows.append({"date": date_str, "gameId": gid, "scope": "TEAM",
                             "team": team["teamTricode"], "player": "", "personId": "", **ta})
            for p in team["players"]:
                st = p["statistics"]
                row = {"date": date_str, "gameId": gid, "team": team["teamTricode"],
                       "personId": p["personId"], "player": p["name"],
                       "position": p.get("position", ""), "jerseyNum": p.get("jerseyNum", ""),
                       "starter": p.get("starter"), "played": p.get("played"),
                       "minutesDisplay": mmss(st.get("minutes")),
                       "minutesFloat": round(minutes(st.get("minutes")), 2)}
                for k in PLAYER_STATS:
                    row[k] = st.get(k)
                box_rows.append(row)

                pa = player_advanced(p, team)
                if pa and pa["minutes"] > 0:
                    adv_rows.append({"date": date_str, "gameId": gid, "scope": "PLAYER",
                                     "team": team["teamTricode"], "player": p["name"],
                                     "personId": p["personId"], **pa})

        for act in pbp["game"]["actions"]:
            r = {c: act.get(c) for c in PBP_COLS}
            r["gameId"] = gid
            r["clock"] = mmss(act.get("clock"))
            q = act.get("qualifiers")
            r["qualifiers"] = "|".join(q) if isinstance(q, list) else q
            pbp_rows.append(r)

    box_cols = ["date", "gameId", "team", "personId", "player", "position", "jerseyNum",
                "starter", "played", "minutesDisplay", "minutesFloat"] + PLAYER_STATS
    adv_cols = ["date", "gameId", "scope", "team", "player", "personId", "minutes",
                "possessions", "offensiveRating", "defensiveRating", "netRating", "pace",
                "trueShootingPercentage", "effectiveFieldGoalPercentage",
                "usagePercentage", "assistToTurnover"]
    idx_cols = list(index_rows[0].keys())

    write_csv(os.path.join(tbl_dir, "box_score.csv"), box_cols, box_rows)
    write_csv(os.path.join(tbl_dir, "advanced.csv"), adv_cols, adv_rows)

    # play-by-play：這個檔在即時模式下每輪都會重寫。git 對純文字能做 delta，
    # 對 .gz 不能（改一個 byte 就是一顆全新的 blob），所以還有比賽沒打完時寫純文字，
    # 全部打完的那一輪才壓成 .csv.gz 並刪掉純文字版。
    all_final = all(g[3] == 3 for g in targets)
    pbp_gz = os.path.join(tbl_dir, "play_by_play.csv.gz")
    pbp_plain = os.path.join(tbl_dir, "play_by_play.csv")
    if all_final:
        write_csv_gz(pbp_gz, PBP_COLS, pbp_rows)
        if os.path.exists(pbp_plain):
            os.remove(pbp_plain)
        pbp_path = pbp_gz
    else:
        write_csv(pbp_plain, PBP_COLS, pbp_rows)
        if os.path.exists(pbp_gz):
            os.remove(pbp_gz)
        pbp_path = pbp_plain

    # data/index.csv：累積所有日期，依 gameId 去重
    idx_path = os.path.join(a.out, "index.csv")
    existing = {}
    if os.path.exists(idx_path):
        with open(idx_path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                existing[row["gameId"]] = row
    for r in index_rows:
        existing[r["gameId"]] = {k: str(v) for k, v in r.items()}
    write_csv(idx_path, idx_cols,
              sorted(existing.values(), key=lambda r: (r["date"], r["gameId"])))

    def kb(p):
        return f"{os.path.getsize(p)/1024:.0f} KB" if os.path.exists(p) else "-"

    live_note = f"，其中進行中 {live_n} 場" if live_n else ""
    print(f"\n新抓 {fetched} 場{live_note}，沿用已存在 {skipped} 場")
    print(f"  {tbl_dir}/box_score.csv        {len(box_rows):>5} 列  {kb(os.path.join(tbl_dir,'box_score.csv'))}")
    print(f"  {tbl_dir}/advanced.csv         {len(adv_rows):>5} 列  {kb(os.path.join(tbl_dir,'advanced.csv'))}")
    print(f"  {pbp_path}  {len(pbp_rows):>5} 列  {kb(pbp_path)}")
    print(f"  {idx_path}                {len(existing):>5} 場  {kb(idx_path)}")
    raw_files = sorted(os.listdir(raw_dir)) if os.path.isdir(raw_dir) else []
    if raw_files:
        raw_total = sum(os.path.getsize(os.path.join(raw_dir, f)) for f in raw_files)
        print(f"  {raw_dir}/  {len(raw_files)} 個檔  {raw_total/1024:.0f} KB")
    else:
        print(f"  {raw_dir}/  （還沒有打完的比賽，原始檔等 Final 才寫）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
