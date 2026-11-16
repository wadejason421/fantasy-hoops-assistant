"""即時監看一場比賽的 box score + play-by-play，證明 liveData 真的會更新。

比賽進行中跑這支，它每 N 秒抓一次，只印出「跟上次相比多了什麼」。
比賽已結束的話，第一輪會印出完整現況，之後每輪都是 no change —— 這本身就是對照組。

用法：
  .venv/bin/python scripts/live_watch.py                 # 自動挑今天第一場進行中的比賽
  .venv/bin/python scripts/live_watch.py 0022600244      # 指定 game id
  .venv/bin/python scripts/live_watch.py 0022600244 10   # 每 10 秒抓一次（預設 15）
"""
import sys, time, datetime
from curl_cffi import requests as cffi

HEADERS = {
    "Referer": "https://www.nba.com/",
    "Origin": "https://www.nba.com",
    "Accept": "application/json, text/plain, */*",
}
S = cffi.Session(impersonate="chrome")
CDN = "https://cdn.nba.com/static/json/liveData"


def get(url):
    r = S.get(url, headers=HEADERS, timeout=25)
    r.raise_for_status()
    return r.json()


def pick_game():
    """挑今天的比賽：優先進行中(2)，否則最後一場已結束的(3)，否則第一場未開始的(1)。"""
    sb = get(f"{CDN}/scoreboard/todaysScoreboard_00.json")["scoreboard"]
    games = sb["games"]
    print(f"todaysScoreboard gameDate={sb['gameDate']}  共 {len(games)} 場")
    for g in games:
        tag = {1: "未開始", 2: "進行中", 3: "已結束"}.get(g["gameStatus"], "?")
        print(f"  {g['gameId']}  {g['awayTeam']['teamTricode']:>3} {g['awayTeam']['score']:>3}"
              f" @ {g['homeTeam']['teamTricode']:>3} {g['homeTeam']['score']:>3}  "
              f"[{tag}] {g['gameStatusText']}")
    live = [g for g in games if g["gameStatus"] == 2]
    if live:
        print(f"\n=> 有 {len(live)} 場進行中，選 {live[0]['gameId']}\n")
        return live[0]["gameId"]
    done = [g for g in games if g["gameStatus"] == 3]
    if done:
        print(f"\n=> 沒有進行中的比賽。用已結束的 {done[-1]['gameId']} 當對照組"
              f"（預期：每輪都 no change）\n")
        return done[-1]["gameId"]
    print(f"\n=> 今天還沒有比賽開打，選 {games[0]['gameId']}\n")
    return games[0]["gameId"]


def mmss(iso):
    """PT12M34.00S -> 12:34"""
    import re
    m = re.match(r"PT(\d+)M([\d.]+)S", iso or "")
    return f"{int(m.group(1))}:{int(float(m.group(2))):02d}" if m else "--:--"


def main():
    args = [a for a in sys.argv[1:]]
    gid = args[0] if args and args[0].isdigit() and len(args[0]) == 10 else None
    interval = int(args[-1]) if args and args[-1].isdigit() and len(args[-1]) < 5 else 15
    if gid is None:
        gid = pick_game()

    print(f"監看 {gid}，每 {interval} 秒一次。Ctrl-C 停止。\n" + "=" * 78)

    seen = 0          # 已印出的 action 數
    last_sig = None   # 上一輪的 box score 指紋
    rounds = 0

    while True:
        rounds += 1
        now = datetime.datetime.now().strftime("%H:%M:%S")
        try:
            box = get(f"{CDN}/boxscore/boxscore_{gid}.json")["game"]
            pbp = get(f"{CDN}/playbyplay/playbyplay_{gid}.json")["game"]["actions"]
        except Exception as e:
            print(f"[{now}] 抓取失敗 {type(e).__name__}: {str(e)[:70]}")
            time.sleep(interval)
            continue

        a, h = box["awayTeam"], box["homeTeam"]
        sig = (a["score"], h["score"], box["period"], box["gameClock"], len(pbp))
        head = (f"[{now}] {a['teamTricode']} {a['score']} - {h['score']} {h['teamTricode']}  "
                f"Q{box['period']} {mmss(box['gameClock'])}  "
                f"{box['gameStatusText']}  actions={len(pbp)}")

        if sig == last_sig:
            print(f"{head}   (no change)")
        else:
            print(head)
            # 新增的 play-by-play
            for act in pbp[seen:]:
                desc = act.get("description") or f"[{act.get('actionType')}]"
                shot = ""
                if act.get("isFieldGoal"):
                    shot = f"  ({act.get('shotDistance', 0):.0f}ft {act.get('shotResult')})"
                print(f"    Q{act['period']} {mmss(act['clock'])} "
                      f"{act.get('teamTricode') or '---':>3}  {desc}{shot}")
            # 第一輪印出得分王當基準
            if rounds == 1:
                for t in (a, h):
                    top = sorted((p for p in t["players"] if p["statistics"]["minutes"]),
                                 key=lambda p: -p["statistics"]["points"])[:3]
                    line = "  ".join(f"{p['name']} {p['statistics']['points']}/"
                                     f"{p['statistics']['reboundsTotal']}/"
                                     f"{p['statistics']['assists']}" for p in top)
                    print(f"    {t['teamTricode']} 得分前三 (PTS/REB/AST): {line}")
            seen = len(pbp)
        last_sig = sig

        if box["gameStatus"] == 3 and rounds >= 3:
            print("=" * 78)
            print("比賽已結束且連續多輪無變化，停止監看。")
            break
        time.sleep(interval)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n已停止。")
