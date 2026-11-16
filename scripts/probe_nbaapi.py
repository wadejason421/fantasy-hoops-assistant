"""讓 nba_api 走 curl_cffi 的 TLS 指紋，實測是否就能正常使用。

nba_api 的 NBAHTTP 提供官方掛鉤 set_session()，直接塞一個 curl_cffi 的
Session(impersonate="chrome") 進去就好 —— 不用 monkeypatch。

用法：.venv/bin/python scripts/probe_nbaapi.py [GAME_ID]
"""
import sys, warnings
warnings.filterwarnings("ignore")

from curl_cffi import requests as cffi
from nba_api.library.http import NBAHTTP
from nba_api.stats.library.http import NBAStatsHTTP
from nba_api.live.nba.library.http import NBALiveHTTP

session = cffi.Session(impersonate="chrome")
for cls in (NBAHTTP, NBAStatsHTTP, NBALiveHTTP):
    cls.set_session(session)

# nba_api 的 NBALiveHTTP 預設 header 沒有 Referer/Origin，但 cdn.nba.com 一定要，
# 而且它寫死的 UA 是 Chrome/87（2020 年），跟 impersonate 的 TLS 指紋不一致。兩者都補掉。
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36")
NBALiveHTTP.headers = {
    **NBALiveHTTP.headers,
    "Referer": "https://www.nba.com/",
    "Origin": "https://www.nba.com",
    "User-Agent": UA,
}
print('set_session(curl_cffi.Session(impersonate="chrome")) on NBAHTTP / NBAStatsHTTP / NBALiveHTTP')
print('+ NBALiveHTTP.headers 補 Referer / Origin / 新 UA\n')

G = sys.argv[1] if len(sys.argv) > 1 else "0022600244"
fails = []

def step(name, fn):
    try:
        fn()
    except Exception as e:
        fails.append(name)
        print(f"{name:26s} -> FAIL {type(e).__name__}: {str(e)[:100]}")

def trad():
    from nba_api.stats.endpoints import boxscoretraditionalv3
    df = boxscoretraditionalv3.BoxScoreTraditionalV3(game_id=G).get_data_frames()[0]
    print(f"{'boxscoretraditionalv3':26s} -> {len(df)} 列 / {len(df.columns)} 欄")
    for _, r in df.sort_values("points", ascending=False).head(3).iterrows():
        print(f"{'':28s} {r['teamTricode']:4s} {r['firstName']} {r['familyName']:<22s}"
              f"{r['points']:>3.0f} PTS {r['reboundsTotal']:>3.0f} REB {r['assists']:>3.0f} AST")

def adv():
    from nba_api.stats.endpoints import boxscoreadvancedv3
    df = boxscoreadvancedv3.BoxScoreAdvancedV3(game_id=G).get_data_frames()[0]
    cols = [c for c in ("offensiveRating","defensiveRating","trueShootingPercentage","usagePercentage") if c in df.columns]
    print(f"{'boxscoreadvancedv3':26s} -> {len(df)} 列 / {len(df.columns)} 欄  有 {cols}")

def pbp():
    from nba_api.stats.endpoints import playbyplayv3
    df = playbyplayv3.PlayByPlayV3(game_id=G).get_data_frames()[0]
    print(f"{'playbyplayv3':26s} -> {len(df)} 列 / {len(df.columns)} 欄")
    print(f"{'':28s} {df.iloc[25]['description']}")

def hustle():
    from nba_api.stats.endpoints import hustlestatsboxscore
    df = hustlestatsboxscore.HustleStatsBoxScore(game_id=G).get_data_frames()[1]
    print(f"{'hustlestatsboxscore':26s} -> {len(df)} 列 / {len(df.columns)} 欄")

def live_box():
    from nba_api.live.nba.endpoints import boxscore
    g = boxscore.BoxScore(game_id=G).game.get_dict()
    print(f"{'live boxscore':26s} -> {g['awayTeam']['teamTricode']} {g['awayTeam']['score']}"
          f" @ {g['homeTeam']['teamTricode']} {g['homeTeam']['score']}  ({g['gameStatusText']})"
          f"  {len(g['awayTeam']['players'])}+{len(g['homeTeam']['players'])} 人")

def live_pbp():
    from nba_api.live.nba.endpoints import playbyplay
    acts = playbyplay.PlayByPlay(game_id=G).actions.get_dict()
    print(f"{'live playbyplay':26s} -> {len(acts)} actions / {len(acts[20])} 欄")

def live_sb():
    from nba_api.live.nba.endpoints import scoreboard
    games = scoreboard.ScoreBoard().games.get_dict()
    print(f"{'live scoreboard (今天)':26s} -> {len(games)} 場")

for name, fn in [("boxscoretraditionalv3", trad), ("boxscoreadvancedv3", adv),
                 ("playbyplayv3", pbp), ("hustlestatsboxscore", hustle),
                 ("live boxscore", live_box), ("live playbyplay", live_pbp),
                 ("live scoreboard", live_sb)]:
    step(name, fn)

print("\n*** 全部 7 項成功 ***" if not fails else f"\n*** {len(fails)} 項失敗: {fails} ***")
