"""
Past ECNL seasons (data/history/, downloaded by scripts/history.py) for the dashboard build:
  seasons(gender)                  past seasons on disk, newest first
  load(gender, season)             (brackets, games), the same shape as this season's data/
  team_history(gender, brackets)   this season's teams -> how the same players finished in earlier seasons
  priors(gender, brackets, season, weight)   starting ratings from the season before

Players move up an age group each season (this season's U14 = last season's U13). A team is followed back by its TGS
team id when the id carries over (about half do), else by the same club with the same team name one age group
younger, else by the club's only team at that age. In 2026-27 ECNL switched from birth years to school years
(B2012/13), so for that switch some players of a 2026-27 team were in the same age group the season before.
"""
import collections, csv, glob, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from refresh import ROOT, team_label, age_num
import ratings

AGES = ["U13", "U14", "U15", "U16", "U17", "U18/19"]
PREV_AGE = {"U14": "U13", "U15": "U14", "U16": "U15", "U17": "U16", "U18/19": "U17"}

def seasons(gender):
    return sorted((re.search(r"_(\d{4}-\d{2})\.csv$", p)[1] for p in glob.glob(f"{ROOT}/data/history/{gender}_*.csv")), reverse=True)

def label(season):  # "2025-26" -> "2025–26"
    return season.replace("-", "–")

_cache = {}
def load(gender, season):
    if (gender, season) not in _cache:
        brackets = json.load(open(f"{ROOT}/data/history/{gender}_{season}_brackets.json"))
        with open(f"{ROOT}/data/history/{gender}_{season}.csv") as f:
            games = list(csv.DictReader(f))
        _cache[(gender, season)] = (brackets, games)
    return _cache[(gender, season)]

def ranked(games, teams):
    """ECNL order: points per game, then head-to-head for two tied teams, total goal difference, total goals scored.
    games: [(h, a, hs, as)] -> [(team, stats)] best first."""
    T = {t: dict(mp=0, w=0, d=0, l=0, gf=0, ga=0, pts=0) for t in teams}
    for h, a, x, y in games:
        H, A = T[h], T[a]
        H["mp"] += 1; A["mp"] += 1; H["gf"] += x; H["ga"] += y; A["gf"] += y; A["ga"] += x
        if x > y: H["w"] += 1; A["l"] += 1; H["pts"] += 3
        elif x < y: A["w"] += 1; H["l"] += 1; A["pts"] += 3
        else: H["d"] += 1; A["d"] += 1; H["pts"] += 1; A["pts"] += 1
    pm = lambda t, v: v / T[t]["mp"] if T[t]["mp"] else 0
    ppm = {t: round(pm(t, T[t]["pts"]), 6) for t in teams}
    tied = collections.Counter(ppm.values())
    def h2h(t):
        if tied[ppm[t]] != 2:
            return 0
        u = next(x for x in teams if x != t and ppm[x] == ppm[t]); p = 0
        for h, a, x, y in games:
            if (h, a) == (t, u): p += 3 if x > y else 1 if x == y else 0
            elif (h, a) == (u, t): p += 3 if y > x else 1 if x == y else 0
        return p
    key = lambda t: (ppm[t], h2h(t), T[t]["gf"] - T[t]["ga"], T[t]["gf"])
    return [(t, T[t]) for t in sorted(teams, key=key, reverse=True)]

def played(games, b):
    return [(g["home_id"], g["away_id"], int(g["home_score"]), int(g["away_score"])) for g in games
            if g["age"] == b["age"] and g["conference"] == b["conf"] and g["home_score"] != ""
            and g["home_id"] in b["teams"] and g["away_id"] in b["teams"]]

def tables(gender, season):
    """{team id: (age, conf, rank, of, stats, label)} for one past season's final tables."""
    key = ("tables", gender, season)
    if key not in _cache:
        brackets, games = load(gender, season)
        out = {}
        for b in brackets:
            tb = ranked(played(games, b), list(b["teams"]))
            for i, (t, st) in enumerate(tb):
                out[t] = (b["age"], b["conf"], i + 1, len(tb), st, team_label(b["teams"][t]))
        _cache[key] = out
    return _cache[key]

def norm(label):
    return re.sub(r"[^a-z0-9]+", " ", label.lower()).strip()

def index(gender, season):
    """Lookups for matching: team ids, and (club id, age) -> [(team id, normalised label)]."""
    key = ("index", gender, season)
    if key not in _cache:
        brackets, _ = load(gender, season)
        by_club = collections.defaultdict(list)
        ids = {}
        for b in brackets:
            for t, n in b["teams"].items():
                ids[t] = b["age"]
                cid = (b["clubs"].get(t) or [""])[0]
                if cid:
                    by_club[(cid, b["age"])].append((t, norm(team_label(n))))
        _cache[key] = (ids, by_club)
    return _cache[key]

def match(gender, season, team, label_, club, age):
    """The team id in `season` (at age group `age`) that is the same squad, or None."""
    if not age:
        return None
    ids, by_club = index(gender, season)
    if ids.get(team) == age:
        return team
    cands = by_club.get((club, age), []) if club else []
    if len(cands) == 1:
        return cands[0][0]
    hits = [t for t, n in cands if n == norm(label_)]
    return hits[0] if len(hits) == 1 else None

def team_history(gender, brackets, before=None):
    """{team id: [[season, age, conf, rank, of, w, d, l, gf, ga, name then], ...]} newest first, following the same players
    back one age group per season. `before`: only seasons older than this one (for past-season pages)."""
    past = [s for s in seasons(gender) if not before or s < before]
    out = {}
    for b in brackets:
        for t, name in b["teams"].items():
            club = (b["clubs"].get(t) or [""])[0]
            cur, lab, age, hist = t, team_label(name), b["age"], []
            for s in past:
                age = PREV_AGE.get(age)
                m = match(gender, s, cur, lab, club, age)
                if not m:
                    break
                a, conf, rk, n, st, lab = tables(gender, s)[m]
                hist.append([s, a, conf, rk, n, st["w"], st["d"], st["l"], st["gf"], st["ga"], lab])
                cur = m
            if hist:
                out[t] = hist
    return out

def season_ratings(gender, season):
    """Final model ratings of every team in a past season: {team id: (att, def)}, fit per conference."""
    key = ("ratings", gender, season)
    if key not in _cache:
        brackets, games = load(gender, season)
        out = {}
        for b in brackets:
            m = ratings.fit(played(games, b), list(b["teams"]))
            for t in b["teams"]:
                out[t] = (m["att"][t], m["def"][t])
        _cache[key] = out
    return _cache[key]

def priors(gender, brackets, season, weight, mode="avg"):
    """Starting ratings from `season` (the one before): {team id: [att, def]} with the weight applied.
    "cohort" = the same players one age group younger; "same" = the same team id or club team at the same age;
    "avg" = the average of whichever of the two exist."""
    last = season_ratings(gender, season)
    out = {}
    for b in brackets:
        for t, name in b["teams"].items():
            club, lab = (b["clubs"].get(t) or [""])[0], team_label(name)
            hits = []
            if mode in ("cohort", "avg"):
                hits.append(match(gender, season, t, lab, club, PREV_AGE.get(b["age"])))
            if mode in ("same", "avg"):
                hits.append(match(gender, season, t, lab, club, b["age"]))
            r = [last[h] for h in hits if h]
            if r:
                out[t] = [round(weight * sum(x[0] for x in r) / len(r), 3), round(weight * sum(x[1] for x in r) / len(r), 3)]
    return out
