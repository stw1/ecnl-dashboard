#!/usr/bin/env python3
"""
Cross-conference games: ECNL teams from different conferences meet only at national events (showcases such as Phoenix,
Florida, Las Vegas) and the national playoffs. Those games show which conferences are stronger, which the national
rankings use (scripts/confstrength.py).

  python3 scripts/national.py            # past seasons -> data/history/cross.csv (one-off, needs scripts/history.py first)
  refresh.py calls current() every run   # this season -> data/cross.csv

A game is kept when both teams are in that season's ECNL conference brackets (same TGS team ids), in the same age
group, and in different conferences. The season comes from the game date (August to July).
"""
import csv, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import refresh

ROOT = refresh.ROOT
FIELDS = ["season", "gender", "age", "date", "event", "match_id", "home_id", "away_id", "home_conf", "away_conf",
          "home_score", "away_score"]
# TGS events whose names look like ECNL national events or playoffs (found by scanning event ids; Regional League,
# Pre-ECNL, league cups and conference events left out). Add this season's new ones to CURRENT as they appear.
PAST = [2103, 2104, 2105, 2106, 2107, 2108, 2109, 2110, 2111, 2112, 2113, 2114, 2116, 2117, 2118, 2125, 2219, 2261, 2289,
        2290, 2403, 2404, 2409, 2410, 2411, 2412, 2413, 2415, 2416, 2417, 2418, 2419, 2431, 2433, 2434, 2436, 2437, 2597,
        2673, 2674, 2675, 2676, 2677, 2678, 2680, 2681, 2684, 2686, 2688, 2689, 2690, 2692, 2693, 2694, 2695, 2696, 2697,
        2699, 2700, 2701, 2702, 2703, 2704, 2705, 2706, 2707, 2708, 2709, 2710, 2711, 2712, 2713, 2714, 2715, 2716, 2717,
        2718, 2719, 2720, 2721, 2924, 2988, 2989, 2992, 2999, 3000, 3001, 3002, 3003, 3004, 3005, 3006, 3009, 3010, 3016,
        3028, 3030, 3031, 3033, 3035, 3036, 3064, 3199, 3238, 3240, 3299, 3300, 3301, 3302, 3303, 3304, 3305, 3306, 3307,
        3308, 3309, 3312, 3314, 3381, 3382, 3383, 3385, 3386, 3388, 3389, 3390, 3391, 3392, 3393, 3442, 3852, 3865, 3866,
        3974, 3975, 4029, 4030, 4031, 4034, 4040, 4041, 4042, 4043, 4044, 4045, 4046, 4049, 4051, 4087, 4088, 4119, 4120,
        4121, 4122, 4124, 4132, 4133, 4134, 4136, 4142, 4192, 4219, 4220, 4221, 4249, 4250, 4251]
CURRENT = [4369, 4378, 4396, 4414, 4415, 4416, 4417, 4418, 4428, 4429, 4433, 4434, 4435, 4436, 4448, 4452, 4460, 4462,
           4463, 4465, 4466, 4467, 4468, 4474, 4475, 4476, 4477, 4478, 4479, 4480, 4482]

def season_of(date):
    y, m = int(date[:4]), int(date[5:7])
    y = y if m >= 8 else y - 1
    return f"{y}-{(y + 1) % 100:02d}"

def collect(events, index):
    """index: {season: {team id: (gender, age, conf)}} -> cross-conference rows."""
    rows, seen = [], set()
    for ev in events:
        try:
            divs = refresh.get(f"{refresh.API}/get-event-schedule-or-standings/{ev}")
        except Exception as err:
            print(f"  skip event {ev}: {err}", flush=True)
            continue
        n = 0
        for dv in (divs.get("boysDivAndFlightList") or []) + (divs.get("girlsDivAndFlightList") or []):
            for fl in dv["flightList"]:
                try:
                    games = refresh.get(f"{refresh.API}/get-schedules-by-flight/{ev}/{fl['flightID']}/0") or []
                except Exception as err:
                    print(f"  skip flight {fl['flightID']} of event {ev}: {err}", flush=True)
                    continue
                for g in games:
                    if g["matchID"] in seen or g.get("hometeamscore") is None or g.get("awayteamscore") is None:
                        continue
                    date = (g.get("gameDate") or "")[:10]
                    if date[:4] < "2000":
                        continue
                    s = season_of(date); ix = index.get(s, {})
                    h, a = ix.get(str(g.get("hometeamID"))), ix.get(str(g.get("awayteamID")))
                    if not h or not a or h[0] != a[0] or h[1] != a[1] or h[2] == a[2]:
                        continue
                    seen.add(g["matchID"]); n += 1
                    rows.append({"season": s, "gender": h[0], "age": h[1], "date": date, "event": ev, "match_id": g["matchID"],
                                 "home_id": str(g["hometeamID"]), "away_id": str(g["awayteamID"]), "home_conf": h[2], "away_conf": a[2],
                                 "home_score": g["hometeamscore"], "away_score": g["awayteamscore"]})
        print(f"  event {ev}: {n} cross-conference games", flush=True)
    rows.sort(key=lambda r: (r["season"], r["gender"], r["date"], str(r["match_id"])))
    return rows

def write(path, rows):
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, FIELDS); w.writeheader(); w.writerows(rows)

def read(path):
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return list(csv.DictReader(f))

NATIONAL_NAME = re.compile(r"^(ECNL|Boys ECNL|Girls ECNL)\b")
NOT_NATIONAL = re.compile(r"\bRL\b|regional|pre-ecnl|league cup|alliance|quality|school|\bQA\b|conference|champions cup|"
                          r"texas cup|\d{4}-\d{2}\s*$|registration|composite", re.I)

def discover(known, ahead=120):
    """New national events: TGS ids keep growing, so look at the ids after the last known one."""
    found, last = [], max(known)
    for ev in range(last + 1, last + ahead):
        try:
            name = (refresh.get(f"{refresh.API}/get-event-details-by-eventID/{ev}", tries=1) or {}).get("name") or ""
        except Exception:
            continue
        if NATIONAL_NAME.match(name.strip()) and not NOT_NATIONAL.search(name):
            found.append(ev); print(f"  new national event {ev}: {name.strip()}", flush=True)
    return found

def current(brackets_by_gender):
    """This season's cross-conference games so far -> data/cross.csv (called by refresh.py). Newly listed national
    events are found by id and remembered in data/national_events.json."""
    path = f"{ROOT}/data/national_events.json"
    events = json.load(open(path)) if os.path.exists(path) else list(CURRENT)
    events = sorted(set(events) | set(discover(events)))
    json.dump(events, open(path, "w"))
    index = {refresh.SEASON: {t: (g, b["age"], b["conf"]) for g, bs in brackets_by_gender.items() for b in bs for t in b["teams"]}}
    rows = collect(events, index)
    write(f"{ROOT}/data/cross.csv", rows)
    return rows

if __name__ == "__main__":
    import pastseasons
    index = {}
    for g in ("boys", "girls"):
        for s in pastseasons.seasons(g):
            bs, _ = pastseasons.load(g, s)
            index.setdefault(s, {}).update({t: (g, b["age"], b["conf"]) for b in bs for t in b["teams"]})
    rows = collect(PAST, index)
    write(f"{ROOT}/data/history/cross.csv", rows)
    import collections
    print(collections.Counter((r["season"], r["gender"]) for r in rows))
