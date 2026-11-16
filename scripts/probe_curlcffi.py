"""curl_cffi 能否繞過 NBA 官方 API 的 Akamai 指紋封鎖 — 實測腳本。

用法：.venv/bin/python scripts/probe_curlcffi.py [GAME_ID]
"""
import sys, json, time
from curl_cffi import requests

G = sys.argv[1] if len(sys.argv) > 1 else "0022600244"

CDN_HEADERS = {
    "Referer": "https://www.nba.com/",
    "Origin": "https://www.nba.com",
    "Accept": "application/json, text/plain, */*",
}
STATS_HEADERS = {
    **CDN_HEADERS,
    "x-nba-stats-origin": "stats",
    "x-nba-stats-token": "true",
}

TESTS = [
    ("cdn todaysScoreboard",
     "https://cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_00.json", CDN_HEADERS),
    ("cdn liveData boxscore",
     f"https://cdn.nba.com/static/json/liveData/boxscore/boxscore_{G}.json", CDN_HEADERS),
    ("cdn liveData playbyplay",
     f"https://cdn.nba.com/static/json/liveData/playbyplay/playbyplay_{G}.json", CDN_HEADERS),
    ("cdn scheduleLeagueV2",
     "https://cdn.nba.com/static/json/staticData/scheduleLeagueV2_32.json", CDN_HEADERS),
    ("stats boxscoretraditionalv3",
     f"https://stats.nba.com/stats/boxscoretraditionalv3?GameID={G}"
     "&StartPeriod=0&EndPeriod=14&StartRange=0&EndRange=28800&RangeType=0", STATS_HEADERS),
    ("stats boxscoreadvancedv3",
     f"https://stats.nba.com/stats/boxscoreadvancedv3?GameID={G}"
     "&StartPeriod=0&EndPeriod=14&StartRange=0&EndRange=28800&RangeType=0", STATS_HEADERS),
    ("stats playbyplayv3",
     f"https://stats.nba.com/stats/playbyplayv3?GameID={G}&StartPeriod=0&EndPeriod=14", STATS_HEADERS),
    ("stats hustlestatsboxscore",
     f"https://stats.nba.com/stats/hustlestatsboxscore?GameID={G}", STATS_HEADERS),
]

IMPERSONATE = ["chrome", "safari", None]  # None = 不偽裝，當對照組

for imp in IMPERSONATE:
    label = imp or "NONE (對照組)"
    print(f"\n=== impersonate={label} ===")
    for name, url, hdrs in TESTS:
        t0 = time.time()
        try:
            kw = {"headers": hdrs, "timeout": 25}
            if imp:
                kw["impersonate"] = imp
            r = requests.get(url, **kw)
            ms = int((time.time() - t0) * 1000)
            if r.status_code == 200:
                n = len(r.content)
                try:
                    json.loads(r.content)
                    ok = "JSON ok"
                except Exception:
                    ok = "NOT json"
                print(f"  {name:30s} 200  {n:>9,} bytes  {ms:>5}ms  {ok}")
            else:
                print(f"  {name:30s} {r.status_code}  {ms:>5}ms")
        except Exception as e:
            ms = int((time.time() - t0) * 1000)
            print(f"  {name:30s} ERR  {ms:>5}ms  {type(e).__name__}: {str(e)[:70]}")
        time.sleep(0.4)
