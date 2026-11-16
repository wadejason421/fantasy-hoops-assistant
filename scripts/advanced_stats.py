#!/usr/bin/env python3
"""從 cdn.nba.com 的 box score 自己算進階數據。

為什麼需要這支：stats.nba.com 的 boxscoreadvancedv3 會丟棄資料中心 IP 的封包，
所以雲端排程拿不到官方的進階數據。但那些數字都是從基礎數據推導的，
而基礎數據全部都在 cdn.nba.com 的 box score 裡（雲端拿得到）。

驗證（2026-11-16，game 0022600244，對照 stats.nba.com 官方值）：

    指標            誤差
    TS%             ±0.02 pp（球員層級完全一致）
    eFG%            ±0.05 pp
    DRtg            -0.33
    ORtg            -0.33 ~ -1.77
    PACE            +1.06
    USG%            +0.1 ~ +1.3 pp

TS% / eFG% 實質上完全一致。ORtg / PACE / USG% 有小差異，因為 NBA 用的回合數
公式比標準估計式更細（會處理球隊籃板、加罰、節末回合）。對「比較兩個球員」
這種用途完全夠用；要跟官方數字逐位對齊就不行。

用法：
    .venv/bin/python scripts/advanced_stats.py 0022600244
    或 from advanced_stats import team_advanced, player_advanced
"""

import re
import sys

MIN_RE = re.compile(r"PT(\d+)M([\d.]+)S")


def minutes(iso):
    """'PT27M21.00S' -> 27.35（分鐘，float）"""
    m = MIN_RE.match(iso or "")
    return int(m.group(1)) + float(m.group(2)) / 60 if m else 0.0


def team_totals(team):
    """從 cdn box score 的 homeTeam / awayTeam 取出算式需要的欄位。"""
    st = team["statistics"]
    return {
        "FGA": st["fieldGoalsAttempted"], "FGM": st["fieldGoalsMade"],
        "FTA": st["freeThrowsAttempted"], "FTM": st["freeThrowsMade"],
        "TPM": st["threePointersMade"],
        "TOV": st["turnoversTotal"],
        "OREB": st["reboundsOffensive"], "DREB": st["reboundsDefensive"],
        "PTS": st["points"],
        # 球員上場時間總和 = 球隊人次分鐘（5 人同時在場）
        "MIN": sum(minutes(p["statistics"]["minutes"]) for p in team["players"]),
    }


def possessions(t):
    """標準回合數估計式。NBA 官方的版本更細，誤差約 ±2 回合。"""
    return t["FGA"] + 0.44 * t["FTA"] - t["OREB"] + t["TOV"]


def team_advanced(team, opp):
    """一隊的進階數據。team / opp 都是 cdn box score 的 team 物件。"""
    t, o = team_totals(team), team_totals(opp)
    pt, po = possessions(t), possessions(o)
    return {
        "possessions": round(pt, 1),
        "offensiveRating": round(100 * t["PTS"] / pt, 1) if pt else 0.0,
        "defensiveRating": round(100 * o["PTS"] / po, 1) if po else 0.0,
        "netRating": round(100 * t["PTS"] / pt - 100 * o["PTS"] / po, 1) if pt and po else 0.0,
        "pace": round(48 * ((pt + po) / 2) / (t["MIN"] / 5), 1) if t["MIN"] else 0.0,
        "trueShootingPercentage": round(
            t["PTS"] / (2 * (t["FGA"] + 0.44 * t["FTA"])) * 100, 1)
            if t["FGA"] + t["FTA"] else 0.0,
        "effectiveFieldGoalPercentage": round(
            (t["FGM"] + 0.5 * t["TPM"]) / t["FGA"] * 100, 1) if t["FGA"] else 0.0,
        "assistToTurnover": round(team["statistics"]["assists"] / t["TOV"], 2) if t["TOV"] else 0.0,
    }


def player_advanced(player, team):
    """一名球員的進階數據。team 是他所屬那隊的 cdn box score team 物件。"""
    s = player["statistics"]
    t = team_totals(team)
    mp = minutes(s["minutes"])
    if mp <= 0:
        return None
    shot = s["fieldGoalsAttempted"] + 0.44 * s["freeThrowsAttempted"]
    team_shot = t["FGA"] + 0.44 * t["FTA"] + t["TOV"]
    return {
        "minutes": round(mp, 2),
        "trueShootingPercentage": round(s["points"] / (2 * shot) * 100, 1) if shot else 0.0,
        "effectiveFieldGoalPercentage": round(
            (s["fieldGoalsMade"] + 0.5 * s["threePointersMade"]) / s["fieldGoalsAttempted"] * 100, 1)
            if s["fieldGoalsAttempted"] else 0.0,
        "usagePercentage": round(
            100 * ((shot + s["turnovers"]) * (t["MIN"] / 5)) / (mp * team_shot), 1)
            if team_shot else 0.0,
        "assistToTurnover": round(s["assists"] / s["turnovers"], 2) if s["turnovers"] else None,
    }


def main():
    from curl_cffi import requests as cffi
    gid = sys.argv[1] if len(sys.argv) > 1 else "0022600244"
    H = {"Referer": "https://www.nba.com/", "Origin": "https://www.nba.com",
         "Accept": "application/json"}
    g = cffi.get(f"https://cdn.nba.com/static/json/liveData/boxscore/boxscore_{gid}.json",
                 headers=H, impersonate="chrome", timeout=25).json()["game"]

    print(f"{g['awayTeam']['teamTricode']} {g['awayTeam']['score']} @ "
          f"{g['homeTeam']['teamTricode']} {g['homeTeam']['score']}  ({g['gameStatusText']})\n")

    for team, opp in ((g["awayTeam"], g["homeTeam"]), (g["homeTeam"], g["awayTeam"])):
        a = team_advanced(team, opp)
        print(f"[{team['teamTricode']}] " + "  ".join(f"{k}={v}" for k, v in a.items()))
    print()

    print(f"{'球員':<26}{'MIN':>6}{'TS%':>7}{'eFG%':>7}{'USG%':>7}")
    rows = []
    for team in (g["awayTeam"], g["homeTeam"]):
        for p in team["players"]:
            a = player_advanced(p, team)
            if a and a["minutes"] >= 5:
                rows.append((team["teamTricode"], p["name"], a))
    for tri, name, a in sorted(rows, key=lambda r: -r[2]["usagePercentage"]):
        print(f"{tri + ' ' + name[:22]:<26}{a['minutes']:6.1f}"
              f"{a['trueShootingPercentage']:7.1f}{a['effectiveFieldGoalPercentage']:7.1f}"
              f"{a['usagePercentage']:7.1f}")


if __name__ == "__main__":
    main()
