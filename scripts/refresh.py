#!/usr/bin/env python3
"""
Refresh ECNL Boys and Girls data and rebuild the dashboard pages:
  index.html  = ECNL Boys,  girls.html = ECNL Girls  (every conference and age group, one bracket shown at a time)

  python3 scripts/refresh.py            # live fetch from TotalGlobalSports (ECNL's results platform)
  python3 scripts/refresh.py --offline  # rebuild from data/ only

Data: the public TotalGlobalSports API behind public.totalglobalsports.com (no key needed):
  Event/get-event-details-by-eventID/{event}            conference name
  Event/get-event-schedule-or-standings/{event}         age groups (divisions) and their flights
  Event/get-schedules-by-flight/{event}/{flight}/0      every game of one age group in one conference
Kickoff times are local to the field (that's how TGS publishes them). Python 3.9+ standard library only.
"""
import argparse, csv, json, os, re, sys, time, urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
API = "https://api.athleteone.com/api/Event"
UA = {"User-Agent": "Mozilla/5.0 (personal ECNL fan dashboard; github.com/stw1/ecnl-dashboard)"}
SEASON = "2026-27"
# One TotalGlobalSports "event" per conference. These are the lists the ECNL standings pages offer for 2026-27
# (org 12 season 81 = Boys, org 9 season 80 = Girls). Update every August for the new season.
LEAGUES = {
    "boys": {"label": "ECNL Boys", "file": "index.html", "default": "U14:Northwest",
             "events": [4273, 4274, 4275, 4276, 4277, 4279, 4280, 4281, 4282, 4283, 4284, 4285, 4286, 4287, 4288]},
    "girls": {"label": "ECNL Girls", "file": "girls.html", "default": "U14:Northwest",
              "events": [4263, 4264, 4265, 4266, 4267, 4268, 4269, 4270, 4271, 4272]},
}
FIELDS = ["age", "conference", "match_id", "start", "home_id", "away_id", "home_team", "away_team",
          "home_score", "away_score", "venue", "home_club_id", "away_club_id", "home_club", "away_club"]

def get(url, tries=4):
    for k in range(tries):
        try:
            time.sleep(0.3)
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                d = json.load(r)
            if d.get("result") != "success":
                raise RuntimeError(str(d)[:200])
            return d["data"]
        except Exception as err:
            if k == tries - 1:
                raise
            print(f"  retry {url} ({err})", flush=True)
            time.sleep(3 * (k + 1))

def age_of(division):  # "BU13" -> "U13", "GU18/19" -> "U18/19"
    return re.sub(r"^[BG]", "", division.strip())

def age_num(age):
    return int(re.sub(r"\D.*", "", age.lstrip("U")) or 0)

def fetch(gender):
    lg = LEAGUES[gender]
    brackets, games = [], []
    for ev in lg["events"]:
        name = get(f"{API}/get-event-details-by-eventID/{ev}")["name"]          # "ECNL Boys Northwest 2026-27"
        conf = re.sub(r"^ECNL (Boys|Girls)\s+|\s+\d{4}-\d{2}$", "", name).strip()
        divs = get(f"{API}/get-event-schedule-or-standings/{ev}")
        divs = divs.get("boysDivAndFlightList" if gender == "boys" else "girlsDivAndFlightList") or []
        for dv in divs:
            age = age_of(dv["divisionName"])
            # a few conferences split an age group into flights (East/West, North/South, Blue/White) that still play
            # each other, with each game listed under one flight: merge the flights into one bracket per conference
            teams, clubs, groups, seen = {}, {}, {}, set()
            multi = len(dv["flightList"]) > 1
            for fl in dv["flightList"]:
                rows = get(f"{API}/get-schedules-by-flight/{ev}/{fl['flightID']}/0") or []
                for g in rows:
                    if g["matchID"] in seen:
                        continue
                    seen.add(g["matchID"])
                    if g.get("friendly") or not g.get("hometeamID") or not g.get("awayteamID"):
                        continue  # friendlies, and fixtures with an opponent still "TBD"
                    for s, sid in (("home", "hometeamID"), ("away", "awayteamID")):
                        teams[str(g[sid])] = g[f"{s}Team"].strip()
                        clubs[str(g[sid])] = [str(g.get(f"{s}TeamClubID") or ""), (g.get(f"{s}TeamClub") or "").strip()]
                    done = g.get("hometeamscore") is not None and g.get("awayteamscore") is not None
                    when = (g.get("gameDate") or "")[:16].replace("T", " ")
                    if not when[:4].isdigit() or when[:4] < "2000":
                        continue  # placeholder fixture with no real date yet (TGS uses 0001-01-01)
                    if when.endswith(" 00:00"):
                        when = when[:10]  # midnight = kickoff time not set yet; the page shows "time TBD"
                    venue = " - ".join(x for x in ((g.get("complex") or "").strip(), (g.get("venue") or "").strip()) if x and x.upper() != "TBD")
                    games.append({"age": age, "conference": conf, "match_id": g["matchID"], "start": when,
                                  "home_id": str(g["hometeamID"]), "away_id": str(g["awayteamID"]),
                                  "home_team": g["homeTeam"].strip(), "away_team": g["awayTeam"].strip(),
                                  "home_score": g["hometeamscore"] if done else "", "away_score": g["awayteamscore"] if done else "",
                                  "venue": venue, "home_club_id": clubs[str(g["hometeamID"])][0], "away_club_id": clubs[str(g["awayteamID"])][0],
                                  "home_club": clubs[str(g["hometeamID"])][1], "away_club": clubs[str(g["awayteamID"])][1]})
                if multi:  # a team's group = the flight whose schedule lists most of its games
                    for g in rows:
                        for sid in ("hometeamID", "awayteamID"):
                            groups.setdefault(str(g[sid]), {}).setdefault(fl["flightName"].title(), 0)
                            groups[str(g[sid])][fl["flightName"].title()] += 1
            if teams:
                brackets.append({"age": age, "conf": conf, "teams": teams, "clubs": clubs,
                                 "groups": {t: max(c, key=c.get) for t, c in groups.items()} if multi else {}})
            print(f"{lg['label']} {conf} {age}: {len(teams)} teams{' in ' + str(len(dv['flightList'])) + ' groups' if multi else ''}", flush=True)
    brackets.sort(key=lambda b: (age_num(b["age"]), b["conf"]))
    games.sort(key=lambda g: (age_num(g["age"]), g["conference"], g["start"], str(g["match_id"])))
    return brackets, games

def save(gender, brackets, games, meta):
    os.makedirs(f"{ROOT}/data", exist_ok=True)
    with open(f"{ROOT}/data/{gender}_games.csv", "w", newline="") as f:
        w = csv.DictWriter(f, FIELDS); w.writeheader(); w.writerows(games)
    json.dump(brackets, open(f"{ROOT}/data/{gender}_brackets.json", "w"), indent=1, ensure_ascii=False)
    json.dump(meta, open(f"{ROOT}/data/meta.json", "w"), indent=1)

def load(gender):
    brackets = json.load(open(f"{ROOT}/data/{gender}_brackets.json"))
    with open(f"{ROOT}/data/{gender}_games.csv") as f:
        games = list(csv.DictReader(f))
    return brackets, games

def team_label(name):
    """'Seattle United ECNL B2013/14' -> 'Seattle United'; 'XF ECNL B2013/14 2' -> 'XF 2';
    'El Paso Locomotive ECNL B13/14' -> 'El Paso Locomotive'; 'OK Energy FC Academy B2013/14' -> 'OK Energy FC Academy'."""
    s = re.sub(r"\s*(\bECNL\b\s*)?\b([BG] ?)?(\d{4}|\d{2})/\d{2,4}\b|\s*\bECNL\b\s*([BG] ?)?\d{4}\b", " ", name)
    return re.sub(r"\s+", " ", s).strip() or name

def build(gender, brackets, games, meta):
    lg = LEAGUES[gender]
    tpl = open(f"{ROOT}/template/dashboard_template.html").read()
    venues, vix, league = [], {}, {}
    for g in games:
        v = g.get("venue") or ""
        if v and v not in vix:
            vix[v] = len(venues); venues.append(v)
        league.setdefault((g["age"], g["conference"]), []).append(",".join([str(g["match_id"]), g["start"], g["home_id"], g["away_id"],
                                                                           str(g["home_score"]), str(g["away_score"]), str(vix[v]) if v else ""]))
    clubs = {}
    for b in brackets:
        for cid, cname in b["clubs"].values():
            if cid:
                clubs[cid] = cname
    dage, dconf = lg["default"].split(":", 1)
    data = {"default": {"age": dage, "conf": dconf}, "snap": meta["snapshot"], "venues": venues, "brand": lg["label"],
            "leagues": [{"key": "Boys" if k == "boys" else "Girls", "file": v["file"], "on": k == gender} for k, v in LEAGUES.items()],
            "clubs": clubs, "localTimes": True,
            "brackets": [{"age": b["age"], "conf": b["conf"], "teams": {k: team_label(n) for k, n in b["teams"].items()},
                          "club": {k: v[0] for k, v in b["clubs"].items() if v[0]}, "groups": b.get("groups") or {},
                          "raw": ";".join(league.get((b["age"], b["conf"]), [])), "flex": ""} for b in brackets]}
    html = (tpl.replace("/*__DATA__*/{}", json.dumps(data, ensure_ascii=False, separators=(",", ":")))
               .replace("__TITLE__", f"{lg['label']} standings and predictions").replace("__SEASON__", f"{SEASON.replace('-', '–')} season"))
    open(f"{ROOT}/{lg['file']}", "w").write(html)
    played = sum(1 for g in games if str(g["home_score"]) != "")
    print(f"Built {lg['file']} ({len(html)//1024} KB): {len(brackets)} brackets, {sum(len(b['teams']) for b in brackets)} teams, "
          f"{played}/{len(games)} games played")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--tz", default="America/Los_Angeles", help="time zone for the snapshot date")
    a = ap.parse_args()
    meta = {"snapshot": datetime.now(ZoneInfo(a.tz)).date().isoformat(), "season": SEASON}
    if a.offline:
        meta = json.load(open(f"{ROOT}/data/meta.json"))
    for gender in LEAGUES:
        if a.offline:
            brackets, games = load(gender)
        else:
            brackets, games = fetch(gender)
            if not brackets:
                sys.exit(f"No {gender} brackets found - check LEAGUES event ids")
            save(gender, brackets, games, meta)
        build(gender, brackets, games, meta)
