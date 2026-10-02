#!/usr/bin/env python3
"""
Backtest for rating uncertainty in the season simulation: are "chance of finishing 1st / top 4" honest?

Replays past seasons from checkpoints (after a share of each conference's games), fits ratings on the games so far
(with last-season priors, like the site), simulates the rest of the season, and scores the chances against the real
final tables (Brier score and log-loss; lower is better).

The uncertainty variant draws each run's ratings around the fitted ones: att ~ N(att, (k·sd)²), def likewise, where
sd comes from the fit's curvature (1 / sqrt(1/SIG² + expected goals involved)), so it is wide after a few games and
narrows as the season goes. k = 0 is the old behaviour (ratings treated as exact).

  python3 scripts/simcheck.py                 # 2025-26 and 2024-25, both genders
"""
import math, os, random, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pastseasons as P
from ratings import fit, SIG

SCALES = [0, 0.5, 1.0, 1.5]
CHECKPOINTS = [0.15, 0.3, 0.5]
RUNS, SCENARIOS = 1200, 24

def sds(m, games, teams):
    """Laplace approximation: sd of each team's attack and defense rating."""
    la = {t: 0.0 for t in teams}; ld = {t: 0.0 for t in teams}
    for h, a, _, _ in games:
        lh = math.exp(m["mu"] + m["home"] + m["att"][h] - m["def"][a]); lw = math.exp(m["mu"] + m["att"][a] - m["def"][h])
        la[h] += lh; la[a] += lw; ld[a] += lh; ld[h] += lw
    return ({t: 1 / math.sqrt(1 / SIG ** 2 + la[t]) for t in teams}, {t: 1 / math.sqrt(1 / SIG ** 2 + ld[t]) for t in teams})

def poisson(rng, lam):
    L, k, p = math.exp(-lam), 0, 1.0
    while True:
        p *= rng.random()
        if p <= L:
            return k
        k += 1

def simulate(m, sa, sd, played, future, teams, scale, rng):
    """{team: (P(1st), P(top 4))} from RUNS season runs (ratings redrawn per scenario when scale > 0)."""
    base = {t: [0, 0, 0, 0] for t in teams}  # pts, gd, gf, games
    for h, a, x, y in played:
        for t, f, o in ((h, x, y), (a, y, x)):
            b = base[t]; b[0] += 3 if f > o else 1 if f == o else 0; b[1] += f - o; b[2] += f; b[3] += 1
    fin = {t: base[t][3] + sum(1 for h, a in future if t in (h, a)) or 1 for t in teams}
    first = {t: 0 for t in teams}; top4 = {t: 0 for t in teams}
    for k in range(SCENARIOS):
        att = {t: m["att"][t] + (rng.gauss(0, scale * sa[t]) if scale else 0) for t in teams}
        de = {t: m["def"][t] + (rng.gauss(0, scale * sd[t]) if scale else 0) for t in teams}
        lam = [(math.exp(m["mu"] + m["home"] + att[h] - de[a]), math.exp(m["mu"] + att[a] - de[h])) for h, a in future]
        for _ in range(RUNS // SCENARIOS):
            S = {t: list(base[t]) for t in teams}
            for (h, a), (lh, lw) in zip(future, lam):
                x, y = poisson(rng, lh), poisson(rng, lw)
                S[h][0] += 3 if x > y else 1 if x == y else 0; S[a][0] += 3 if y > x else 1 if x == y else 0
                S[h][1] += x - y; S[a][1] += y - x; S[h][2] += x; S[a][2] += y
            order = sorted(teams, key=lambda t: (S[t][0] / fin[t], S[t][1], S[t][2], rng.random()), reverse=True)
            first[order[0]] += 1
            for t in order[:4]:
                top4[t] += 1
    n = RUNS // SCENARIOS * SCENARIOS
    return {t: (first[t] / n, top4[t] / n) for t in teams}

def evaluate(gender, season, prev):
    brackets, games = P.load(gender, season)
    pri = P.priors(gender, brackets, prev, 0.75, "avg") if prev else {}
    rng = random.Random(7)
    score = {(c, s): [0.0, 0.0, 0.0, 0] for c in CHECKPOINTS for s in SCALES}  # brier 1st, brier top4, logloss top4, n
    for b in brackets:
        teams = list(b["teams"])
        if len(teams) < 6:
            continue
        gs = sorted((g["start"], g["home_id"], g["away_id"], g["home_score"], g["away_score"]) for g in games
                    if g["age"] == b["age"] and g["conference"] == b["conf"] and g["home_id"] in b["teams"] and g["away_id"] in b["teams"])
        done = [(h, a, int(x), int(y)) for _, h, a, x, y in gs if x != ""]
        final = [t for t, _ in P.ranked(done, teams)]
        for c in CHECKPOINTS:
            cut = gs[int(len(gs) * c)][0] if gs else ""
            played = [(h, a, int(x), int(y)) for d, h, a, x, y in gs if x != "" and d < cut]
            future = [(h, a) for d, h, a, x, y in gs if x != "" and d >= cut]
            if len(played) < len(teams) or not future:
                continue
            m = fit(played, teams, prior={t: tuple(pri[t]) for t in teams if t in pri}, iters=40)
            sa, sd = sds(m, played, teams)
            for s in SCALES:
                r = simulate(m, sa, sd, played, future, teams, s, rng)
                acc = score[(c, s)]
                for t in teams:
                    p1, p4 = r[t]; o1, o4 = final[0] == t, t in final[:4]
                    acc[0] += (p1 - o1) ** 2; acc[1] += (p4 - o4) ** 2
                    q = min(max(p4 if o4 else 1 - p4, 1e-3), 1); acc[2] -= math.log(q); acc[3] += 1
    print(f"\n{gender} {season} (priors from {prev})")
    print(f"{'after':>7}{'uncertainty':>13}{'Brier 1st':>11}{'Brier top4':>12}{'logloss top4':>14}")
    for c in CHECKPOINTS:
        for s in SCALES:
            b1, b4, ll, n = score[(c, s)]
            if n:
                print(f"{c:>7.0%}{('x' + str(s)) if s else 'none':>13}{b1 / n:>11.4f}{b4 / n:>12.4f}{ll / n:>14.4f}", flush=True)

if __name__ == "__main__":
    for gender in ("boys", "girls"):
        ss = P.seasons(gender)
        for i, s in enumerate(ss[:2]):
            evaluate(gender, s, ss[i + 1] if i + 1 < len(ss) else None)
