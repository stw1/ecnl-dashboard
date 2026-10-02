#!/usr/bin/env python3
"""
Backtest for last-season priors: replay a past season week by week, predicting each weekend from the games before it,
with each team's ratings starting from the season before (pastseasons.priors) instead of average.

  python3 scripts/priors.py                       # 2025-26 (priors from 2024-25) and 2024-25 (from 2023-24), both genders
  python3 scripts/priors.py --target 2023-24

The setting with the lowest log-loss goes in refresh.PRIOR_WEIGHT / PRIOR_MODE.
"""
import argparse, datetime, math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pastseasons as P
from ratings import fit, probs

VARIANTS = [("none", 0)] + [("cohort", w) for w in (0.5, 0.75, 1.0)] + [("same", 0.75)] + [("avg", w) for w in (0.5, 0.75, 1.0)]

def evaluate(gender, target, before):
    brackets, games = P.load(gender, target)
    week = lambda d: datetime.date.fromisoformat(d[:10]).isocalendar()[:2]
    res = {v: [0.0, 0, 0.0, 0, 0] for v in VARIANTS}  # log-loss, n, log-loss first 6 weeks, n, picks right
    cover = [0, 0]
    pri = {v: P.priors(gender, brackets, before, v[1], v[0]) if v[0] != "none" else {} for v in VARIANTS}
    for b in brackets:
        tl = list(b["teams"])
        gs = sorted((g["start"], g["home_id"], g["away_id"], int(g["home_score"]), int(g["away_score"])) for g in games
                    if g["age"] == b["age"] and g["conference"] == b["conf"] and g["home_score"] != ""
                    and g["home_id"] in b["teams"] and g["away_id"] in b["teams"])
        weeks = sorted({week(g[0]) for g in gs})
        cover[0] += len(tl); cover[1] += sum(1 for t in tl if t in pri[("avg", 0.75)])
        for v in VARIANTS:
            p = {t: tuple(pri[v][t]) for t in tl if t in pri[v]}
            for i, wk in enumerate(weeks):
                train = [(h, a, x, y) for d, h, a, x, y in gs if week(d) < wk]
                m = fit(train, tl, prior=p, iters=25)
                for d, h, a, x, y in gs:
                    if week(d) != wk:
                        continue
                    ph, pd, pa = probs(m, h, a)
                    q = ph if x > y else pd if x == y else pa
                    r = res[v]; r[0] -= math.log(max(q, 1e-9)); r[1] += 1
                    if i < 6: r[2] -= math.log(max(q, 1e-9)); r[3] += 1
                    pick = "H" if ph - pa >= 0.05 else "A" if pa - ph >= 0.05 else "D"
                    r[4] += pick == ("H" if x > y else "A" if x < y else "D")
    print(f"\n{gender} {target} (priors from {before}): {cover[1]} of {cover[0]} teams matched to the season before")
    print(f"{'setting':<14}{'log-loss all':>13}{'first 6 wks':>13}{'picks right':>13}")
    for v, (ll, n, le, ne, hits) in res.items():
        print(f"{v[0] + (' x' + str(v[1]) if v[1] else ''):<14}{ll / n:>13.4f}{le / max(ne, 1):>13.4f}{hits / n:>12.1%}", flush=True)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", default="all")
    a = ap.parse_args()
    for gender in ("boys", "girls"):
        ss = P.seasons(gender)
        for i, s in enumerate(ss[:-1]):
            if a.target in ("all", s) and (a.target != "all" or i < 2):
                evaluate(gender, s, ss[i + 1])
