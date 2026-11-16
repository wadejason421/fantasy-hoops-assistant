# Fantasy Hoops Assistant

A read-only analytics tool for Yahoo Fantasy Basketball head-to-head **category**
leagues with daily roster changes.

Yahoo's built-in "Start Active Players" only checks whether a player has a game
scheduled. It does not know which statistical categories you are currently
winning or losing against that week's opponent. This tool closes that gap.

## What it does

Each morning, before the first game locks, it:

1. Reads the current week's matchup — your category totals and your opponent's
2. Reads the remaining schedule and injury news for the players involved
3. Classifies every category as **locked**, **lost**, or **still competitive**
4. Recommends which players to start and which free agents are worth a pickup,
   weighted toward the categories that are still competitive
5. Sends the recommendation as a short daily notification

The reasoning is deterministic and shown with every recommendation, for example:

```
Pick up Keon Ellis (SAC) — 3 games remaining this week
  STL win probability 31% -> 58%
  Expected categories won 6.2 -> 6.9
```

## Why category context matters

Suppose you trail in steals by 2.1 but lead blocks by 4.0, and two benched
players both have games tonight: one averages 18 points with 0.4 steals, the
other 9 points with 1.8 steals.

Yahoo's built-in tool does nothing here — both players have games. A points-based
ranking prefers the first. The correct move is the second, because its production
lands in the category that is still winnable.

## Data sources

| Data | Source |
|---|---|
| League settings, weekly matchup category totals, rosters, free agents | Yahoo Fantasy Sports API (read-only, `fspt-r`) |
| Game schedule | ESPN public endpoints |
| Injury status and news | ESPN, Sleeper |
| Player statistics | Basketball Reference |

## Scope

- Non-commercial. Not monetised, no advertising, no paid tier.
- Read-only. All roster moves are made by hand in the Yahoo Fantasy app;
  the tool only produces recommendations.
- Runs locally on a personal machine on a daily schedule.
- Roughly 20–50 Yahoo API requests per day per user, cached locally.

## Status

Current work is the NBA official API investigation. Those are the only
documents under [`doc/`](doc/) (written in Traditional Chinese):

| Document | Contents |
|---|---|
| [nba-api-usage.md](doc/nba-api-usage.md) | How to call the NBA API: endpoints, fields, formats, limits |
| [research.md](doc/research.md) | Full investigation log — what was tested, what the blocking was, how it was solved |
| [app-design.md](doc/app-design.md) | Feasibility and UI design for a live box score / play-by-play app |

The earlier Yahoo Fantasy design documents are archived in
[`archive/doc/`](archive/doc/) — see [archive/doc/README.md](archive/doc/README.md).

Fetched data lands in [`data/`](data/), written daily by
[`fetch-nba.yml`](.github/workflows/fetch-nba.yml) — see [data/README.md](data/README.md).

---

Fantasy data provided by [Yahoo Fantasy](https://fantasysports.yahoo.com/).
