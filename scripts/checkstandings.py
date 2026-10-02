#!/usr/bin/env python3
"""
Compare our standings with ECNL's official ones (the TGS standings feed behind theecnl.com):
every team's games played, W-D-L and goals, and the order inside each flight.

  python3 scripts/checkstandings.py            # this season, from data/ (run refresh.py first for fresh data)

Official standings: Event/get-standings-by-div-and-flight/{division id}/{flight id}/{event id} (no key needed).
Our order uses the same rules as the page: points per game, head-to-head for two tied teams, then total goal
difference and total goals scored (worked out from the official order: it matched all 368 tied pairs on 2026-10-02).
Teams level on all of those are treated as tied.
"""
import collections, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import refresh

def official(events):
    """{team id: (event, flight, position in flight, row)} from the official feed."""
    out = {}
    for ev in events:
        divs = refresh.get(f"{refresh.API}/get-event-schedule-or-standings/{ev}")
        for dv in (divs.get("boysDivAndFlightList") or []) + (divs.get("girlsDivAndFlightList") or []):
            for fl in dv["flightList"]:
                groups = refresh.get(f"{refresh.API}/get-standings-by-div-and-flight/{dv['divisionID']}/{fl['flightID']}/{ev}") or []
                for g in groups:
                    for i, r in enumerate(g.get("teamStandings") or []):
                        out[str(r["teamID"])] = (ev, f"{dv['divisionName']} {fl['flightName']} {g.get('flightGroupName') or ''}".strip(), i, r)
    return out

def ours(brackets, games):
    """{team id: stats} and {team id: sort key} from our games (same rules as the page's table)."""
    st = collections.defaultdict(lambda: dict(mp=0, w=0, d=0, l=0, gf=0, ga=0, pts=0))
    res = collections.defaultdict(list)
    for g in games:
        if str(g["home_score"]) == "":
            continue
        h, a, x, y = g["home_id"], g["away_id"], int(g["home_score"]), int(g["away_score"])
        for t, f, o in ((h, x, y), (a, y, x)):
            s = st[t]; s["mp"] += 1; s["gf"] += f; s["ga"] += o
            k = "w" if f > o else "l" if f < o else "d"; s[k] += 1; s["pts"] += 3 if k == "w" else 1 if k == "d" else 0
        res[(h, a)].append((x, y))
    def key(t, tied):
        s = st[t]; n = s["mp"] or 1; ppg = round(s["pts"] / n, 6)
        h2h = 0
        if len(tied.get(ppg, [])) == 2:
            u = next(x for x in tied[ppg] if x != t)
            for x, y in res.get((t, u), []): h2h += 3 if x > y else 1 if x == y else 0
            for x, y in res.get((u, t), []): h2h += 3 if y > x else 1 if x == y else 0
        return (ppg, h2h, s["gf"] - s["ga"], s["gf"])
    return st, key

def check(gender):
    lg = refresh.LEAGUES[gender]
    brackets, games = refresh.load(gender)
    off = official(lg["events"])
    st, key = ours(brackets, games)
    names = {t: n for b in brackets for t, n in b["teams"].items()}
    rec_bad, order_bad, missing, flights = [], [], [], collections.defaultdict(list)
    for t, n in names.items():
        if t not in off:
            missing.append(n); continue
        ev, fl, pos, r = off[t]
        s = st[t]
        mine = (s["mp"], s["w"], s["d"], s["l"], s["gf"], s["ga"])
        theirs = (r["gp"], r["wins"], r["draws"], r["losses"], r["goalsfor"], r["goalsagainst"])
        if mine != theirs:
            rec_bad.append(f"{n}: ours {mine} vs official {theirs} (GP W D L GF GA)")
        flights[(ev, fl)].append((pos, t))
    for (ev, fl), rows in flights.items():
        rows.sort(); ids = [t for _, t in rows]
        tied = collections.defaultdict(list)
        for t in ids:
            tied[round(st[t]["pts"] / (st[t]["mp"] or 1), 6)].append(t)
        ks = [key(t, tied) for t in ids]
        for i in range(len(ids) - 1):
            if ks[i] < ks[i + 1]:  # official order puts a team above one we rank strictly higher
                order_bad.append(f"{fl} (event {ev}): official has {names[ids[i]]} above {names[ids[i + 1]]}, "
                                 f"ours {ks[i]} vs {ks[i + 1]}")
    n = len(names)
    print(f"{lg['label']}: {n} teams, {n - len(missing)} in the official standings, {len(flights)} flights")
    print(f"  records that differ: {len(rec_bad)}")
    for x in rec_bad[:15]: print("   ", x)
    print(f"  order disagreements: {len(order_bad)}")
    for x in order_bad[:15]: print("   ", x)
    if missing: print(f"  not in the official standings: {len(missing)} e.g. {missing[:5]}")
    return len(rec_bad) + len(order_bad)

if __name__ == "__main__":
    bad = sum(check(g) for g in refresh.LEAGUES)
    sys.exit(1 if bad else 0)
