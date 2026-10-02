#!/usr/bin/env python3
"""
Download past ECNL seasons (conference games) from TotalGlobalSports into data/history/<gender>_<season>.csv
and data/history/<gender>_<season>_brackets.json. Past seasons don't change, so this is a one-off, not part of the
weekend refresh; refresh.py builds the season pages from these files.

  python3 scripts/history.py                    # every season below that isn't downloaded yet
  python3 scripts/history.py --season 2025-26 --force

TGS has full conference seasons from 2020-21 on. Its older ECNL "conference" events are empty, because before 2020-21
ECNL results were kept per national event. Event ids found by scanning get-event-details-by-eventID for
"ECNL Boys|Girls <conference> <season>" (Regional League, League Cup and Champions Cup events left out).
"""
import argparse, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import refresh

ROOT = refresh.ROOT
EVENTS = {
    "2025-26": {"boys": list(range(3876, 3891)), "girls": list(range(3925, 3935))},
    "2024-25": {"boys": list(range(3167, 3179)) + [3182, 3183], "girls": list(range(3157, 3167))},
    "2023-24": {"boys": list(range(2858, 2870)), "girls": [2837, 2838, 2839, 2849, 2850, 2853, 2854, 2855, 2856, 2857]},
    "2022-23": {"boys": list(range(2532, 2542)) + [2594, 2595], "girls": list(range(2522, 2532))},
    "2021-22": {"boys": list(range(2353, 2364)) + [2365], "girls": list(range(2366, 2375))},
    "2020-21": {"boys": list(range(2041, 2051)), "girls": list(range(2033, 2041)) + [2051]},
}

def path(gender, season, kind):
    return f"{ROOT}/data/history/{gender}_{season}{'_brackets.json' if kind == 'brackets' else '.csv'}"

def save(gender, season, brackets, games):
    import csv
    os.makedirs(f"{ROOT}/data/history", exist_ok=True)
    with open(path(gender, season, "games"), "w", newline="") as f:
        w = csv.DictWriter(f, refresh.FIELDS); w.writeheader(); w.writerows(games)
    json.dump(brackets, open(path(gender, season, "brackets"), "w"), indent=1, ensure_ascii=False)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--season", default="all")
    ap.add_argument("--gender", default="all")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    for season, by in EVENTS.items():
        if a.season not in ("all", season):
            continue
        for gender, events in by.items():
            if a.gender not in ("all", gender) or (os.path.exists(path(gender, season, "games")) and not a.force):
                continue
            brackets, games = refresh.fetch_events(f"{season} {gender}", events, season)
            save(gender, season, brackets, games)
            played = sum(1 for g in games if g["home_score"] != "")
            print(f"Saved {gender} {season}: {len(brackets)} brackets, {played}/{len(games)} games played", flush=True)
