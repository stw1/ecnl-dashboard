#!/usr/bin/env python3
"""
Conference strength for the national rankings. Conferences only meet at national events and the playoffs
(scripts/national.py), so each age group is fit jointly: attack = conference effect + team effect, likewise for defense
(ratings.fit_conf). Conference games place teams inside their conference; cross-conference games place the
conferences against each other. Conference effects start from last season's (cprior, times WEIGHT).

  python3 scripts/confstrength.py --evaluate   # backtest on past seasons' cross-conference games
  effects(gender, season, brackets, games, cross, prev)   used by refresh.py: {age: {"mu": mu, conf: [ca, cd]}}
"""
import argparse, collections, math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ratings

WEIGHT, PRIOR_AGE = 0.5, "same"   # chosen by --evaluate (see CLAUDE.md)
PREV_AGE = {"U14": "U13", "U15": "U14", "U16": "U15", "U17": "U16", "U18/19": "U17"}

def conf_games(brackets, games, age):
    """(games, team -> conf) for one age group's conference games."""
    tc = {t: b["conf"] for b in brackets if b["age"] == age for t in b["teams"]}
    gs = [(g["home_id"], g["away_id"], int(g["home_score"]), int(g["away_score"])) for g in games
          if g["age"] == age and g["home_score"] != "" and g["home_id"] in tc and g["away_id"] in tc]
    return gs, tc

def cross_games(cross, gender, season, age, before=None):
    return [(r["home_id"], r["away_id"], int(r["home_score"]), int(r["away_score"])) for r in cross
            if r["gender"] == gender and r["season"] == season and r["age"] == age and (before is None or r["date"] < before)]

def fit_age(gs, tc, cprior=None):
    return ratings.fit_conf(gs, tc, cprior=cprior, iters=30)

def prior_for(prev, age, w):
    """Last season's conference effects for this age group (same age, or the same players one age younger)."""
    if not prev or not w:
        return None
    src = prev.get(age if PRIOR_AGE == "same" else PREV_AGE.get(age, age)) or prev.get(age) or {}
    return {c: (w * v[0], w * v[1]) for c, v in src.items() if c != "mu"}

def effects(gender, season, brackets, games, cross, prev=None, w=WEIGHT):
    """{age: {"mu": mu, conf: [ca, cd]}} for one season: its conference games + cross-conference games so far."""
    out = {}
    for age in sorted({b["age"] for b in brackets}):
        gs, tc = conf_games(brackets, games, age)
        cg = cross_games(cross, gender, season, age)
        m = fit_age(gs + cg, tc, prior_for(prev, age, w))
        out[age] = {"mu": round(m["mu"], 4), **{c: [round(m["ca"][c], 4), round(m["cd"][c], 4)] for c in m["ca"]}}
    return out

def neutral_probs(m, h, a):
    return ratings.probs(dict(m, home=0.0), h, a)

def evaluate():
    import pastseasons as P, national
    cross = national.read(f"{national.ROOT}/data/history/cross.csv")
    print(collections.Counter((r["season"], r["gender"]) for r in cross))
    variants = [("equal", 0, False), ("last season x0.5", 0.5, False), ("last season x1", 1.0, False),
                ("in season", 0, True), ("in season + last x0.5", 0.5, True), ("in season + last x1", 1.0, True)]
    for gender in ("boys", "girls"):
        ss = sorted(P.seasons(gender))
        for i, s in enumerate(ss):
            if i == 0 or s < ss[-3]:  # the last three seasons, each with the one before it as the prior
                continue
            pb, pg = P.load(gender, ss[i - 1]); prev = effects(gender, ss[i - 1], pb, pg, cross, None, 0)
            brackets, games = P.load(gender, s)
            res = {v[0]: [0.0, 0, 0] for v in variants}
            for age in sorted({b["age"] for b in brackets}):
                gs, tc = conf_games(brackets, games, age)
                rows = sorted((r for r in cross if r["gender"] == gender and r["season"] == s and r["age"] == age), key=lambda r: r["date"])
                if not rows:
                    continue
                months = sorted({r["date"][:7] for r in rows})
                for name, w, ins in variants:
                    pri = prior_for(prev, age, w)
                    fits = {}
                    for mo in months:
                        key = mo if ins else "all"
                        if key not in fits:
                            fits[key] = fit_age(gs + (cross_games(cross, gender, s, age, before=mo + "-01") if ins else []), tc, pri)
                        m = fits[key]
                        for r in rows:
                            if r["date"][:7] != mo:
                                continue
                            x, y = int(r["home_score"]), int(r["away_score"])
                            ph, pd, pa = neutral_probs(m, r["home_id"], r["away_id"])
                            q = ph if x > y else pd if x == y else pa
                            R = res[name]; R[0] -= math.log(max(q, 1e-9)); R[1] += 1
                            R[2] += ("H" if ph - pa >= .05 else "A" if pa - ph >= .05 else "D") == ("H" if x > y else "A" if x < y else "D")
            n = next(iter(res.values()))[1]
            if not n:
                continue
            print(f"\n{gender} {s}: {n} cross-conference games")
            for name, (ll, k, hit) in res.items():
                print(f"  {name:<24} log-loss {ll / k:.4f}   picks right {hit / k:.1%}", flush=True)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--evaluate", action="store_true")
    if ap.parse_args().evaluate:
        evaluate()
