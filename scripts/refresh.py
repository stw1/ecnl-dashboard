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
import argparse, collections, csv, json, os, re, sys, time, urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import postseason
API = "https://api.athleteone.com/api/Event"
UA = {"User-Agent": "Mozilla/5.0 (personal ECNL fan dashboard; github.com/stw1/ecnl-dashboard)"}
SEASON = "2026-27"
SITE = "https://stw1.github.io/ecnl-dashboard/"
FEEDBACK = "support@spaikz.com"   # footer "Report a problem or suggest an idea": an email address or a form URL ("" = off)
ANALYTICS_SITE = "ecnl"           # site code in the shared analytics project (analytics/README.md); "" = off
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

def age_of(division, season=SEASON):
    """TGS division name -> age group, or None for ones we skip (U11/U12, composite squads).
    'BU13' -> 'U13', 'GU18/U19' -> 'U18/19', 'B2010' in 2022-23 -> 'U13' (birth years), 'U16 Boys' -> 'U16'."""
    d = division.strip()
    if re.search(r"composite", d, re.I):
        return None
    end = int(season[:4]) + 1
    if m := re.match(r"^[BG]U(\d\d)(?:/U?(\d\d))?$", d) or re.match(r"^U(\d\d)(?:/(\d\d))? (?:Boys|Girls)$", d):
        age, two = int(m[1]), bool(m[2])
    elif m := re.match(r"^[BG](\d{4})(?:/(\d{4}))?$", d):
        age, two = end - max(int(m[1]), int(m[2] or 0)), bool(m[2])
    else:
        return None
    if age < 13:
        return None
    return "U18/19" if two or age >= 18 else f"U{age}"

def age_num(age):
    return int(re.sub(r"\D.*", "", age.lstrip("U")) or 0)

def conf_of(name):
    """'ECNL Boys Northwest 2026-27' / 'ECNL Boys Heartland Confrence 2021-22' -> 'Northwest' / 'Heartland'."""
    c = re.sub(r"^ECNL (Boys|Girls)\s+|\s+\d{4}-\d{2}\s*$", "", name.strip())
    c = re.sub(r"\s+Conf[a-z]*$", "", c, flags=re.I).strip()
    return {"Norcal": "Northern Cal"}.get(c, c)

# flights that were really separate conferences, named as ECNL named them later
FLIGHT_CONF = {("Northwest", "Bay Area"): "Northern Cal", ("Northwest", "Pacific"): "Northwest", ("Northwest", "Mountain"): "Mountain"}

def fetch_events(label, events, season=SEASON):
    """Every conference game of these TGS events: (brackets, games). Games of one age group are merged across the
    event's divisions and flights. Two-division conferences (a third or more of the games between divisions, e.g.
    Heartland Blue/White) stay one bracket with each team's flight as its group. Flights that rarely or never meet
    become separate conferences ('Northeast North'; Girls 2020-22 'Northwest' Bay Area -> 'Northern Cal'), and their
    few games against each other are left out, as in ECNL's own standings."""
    by = {}  # (age, conf) -> {"rows": {match id: game}, "flight": {team: Counter of flights}}
    for ev in events:
        conf = conf_of(get(f"{API}/get-event-details-by-eventID/{ev}")["name"])
        divs = get(f"{API}/get-event-schedule-or-standings/{ev}")
        for dv in (divs.get("boysDivAndFlightList") or []) + (divs.get("girlsDivAndFlightList") or []):
            age = age_of(dv["divisionName"], season)
            if not age:
                continue
            B = by.setdefault((age, conf), {"rows": {}, "flight": {}})
            for fl in dv["flightList"]:
                for g in get(f"{API}/get-schedules-by-flight/{ev}/{fl['flightID']}/0") or []:
                    if g.get("friendly") or not g.get("hometeamID") or not g.get("awayteamID"):
                        continue  # friendlies, and fixtures with an opponent still "TBD"
                    B["rows"].setdefault(g["matchID"], g)
                    for sid in ("hometeamID", "awayteamID"):
                        f = B["flight"].setdefault(str(g[sid]), {})
                        f[fl["flightName"].title()] = f.get(fl["flightName"].title(), 0) + 1
    brackets, games = [], []
    for (age, conf), B in by.items():
        grp = {t: max(c, key=c.get) for t, c in B["flight"].items()}
        names = sorted(set(grp.values()))
        rows = list(B["rows"].values())
        cross = sum(1 for g in rows if grp[str(g["hometeamID"])] != grp[str(g["awayteamID"])])
        if len(names) == 1 or cross >= 0.3 * len(rows):
            parts = [(conf, rows, grp if len(names) > 1 else {})]
        else:
            parts = [(FLIGHT_CONF.get((conf, n), f"{conf} {n}"), [g for g in rows if grp[str(g["hometeamID"])] == grp[str(g["awayteamID"])] == n], {})
                     for n in names]
        for cname, rs, groups in parts:
            teams, clubs = {}, {}
            for g in rs:
                when = (g.get("gameDate") or "")[:16].replace("T", " ")
                if not when[:4].isdigit() or when[:4] < "2000":
                    continue  # placeholder fixture with no real date yet (TGS uses 0001-01-01)
                if when.endswith(" 00:00"):
                    when = when[:10]  # midnight = kickoff time not set yet; the page shows "time TBD"
                for s, sid in (("home", "hometeamID"), ("away", "awayteamID")):
                    teams[str(g[sid])] = g[f"{s}Team"].strip()
                    clubs[str(g[sid])] = [str(g.get(f"{s}TeamClubID") or ""), (g.get(f"{s}TeamClub") or "").strip()]
                done = g.get("hometeamscore") is not None and g.get("awayteamscore") is not None
                venue = " - ".join(x for x in ((g.get("complex") or "").strip(), (g.get("venue") or "").strip()) if x and x.upper() != "TBD")
                h, a = str(g["hometeamID"]), str(g["awayteamID"])
                games.append({"age": age, "conference": cname, "match_id": g["matchID"], "start": when, "home_id": h, "away_id": a,
                              "home_team": g["homeTeam"].strip(), "away_team": g["awayTeam"].strip(),
                              "home_score": g["hometeamscore"] if done else "", "away_score": g["awayteamscore"] if done else "",
                              "venue": venue, "home_club_id": clubs[h][0], "away_club_id": clubs[a][0],
                              "home_club": clubs[h][1], "away_club": clubs[a][1]})
            if teams:
                brackets.append({"age": age, "conf": cname, "teams": teams, "clubs": clubs, "groups": {t: groups[t] for t in teams if t in groups}})
                print(f"{label} {cname} {age}: {len(teams)} teams{' in groups ' + '/'.join(names) if groups else ''}", flush=True)
    brackets.sort(key=lambda b: (age_num(b["age"]), b["conf"]))
    games.sort(key=lambda g: (age_num(g["age"]), g["conference"], g["start"], str(g["match_id"])))
    return brackets, games

def fetch(gender):
    lg = LEAGUES[gender]
    return fetch_events(lg["label"], lg["events"])

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
    'El Paso Locomotive ECNL B13/14' -> 'El Paso Locomotive'; 'OK Energy FC Academy B2013/14' -> 'OK Energy FC Academy';
    past seasons: 'Alabama FC ECNL B06' -> 'Alabama FC', 'Sting ECNL G2010 Black' -> 'Sting Black'."""
    s = re.sub(r"\s*\bECNL\b\s*(?:[BG] ?)?(?:\d{4}|\d{2})(?:/\d{2,4})?\b", " ", name)
    s = re.sub(r"\s*\b(?:[BG] ?)?(?:\d{4}|\d{2})/\d{2,4}\b|\s*\b[BG](?:20)?\d\d\b", " ", s)
    s = re.sub(r"\s*\bECNL\b", " ", s)
    s = re.sub(r"\s*\b[BG]U\d\d(?:/U?\d\d)?\b", " ", s)  # 'Boston Bolts ECNL BU18/19' -> 'Boston Bolts'  # 'XF ECNL Academy B11' -> 'XF Academy'
    return re.sub(r"\s+", " ", s).strip() or name

# Starting ratings from the season before (scripts/priors.py chose these). 0 = start everyone at average.
PRIOR_WEIGHT, PRIOR_MODE = 0.75, "avg"

def page_file(gender, season=SEASON):
    """index.html / girls.html for this season; season-2025-26.html / girls-season-2025-26.html for past ones."""
    if season == SEASON:
        return LEAGUES[gender]["file"]
    return f"{'girls-' if gender == 'girls' else ''}season-{season}.html"

def page_data(gender, brackets, games, snap, season=SEASON, national=None):
    """national: games at ECNL national events and the playoffs (national.py rows), shown with each team's games and
    in the template's "extra games" slot (b.flex): not in the league table, and only games between two teams of the
    same conference feed its ratings."""
    lg = LEAGUES[gender]
    venues, vix, league = [], {}, {}
    for g in games:
        v = g.get("venue") or ""
        if v and v not in vix:
            vix[v] = len(venues); venues.append(v)
        league.setdefault((g["age"], g["conference"]), []).append(",".join([str(g["match_id"]), g["start"], g["home_id"], g["away_id"],
                                                                           str(g["home_score"]), str(g["away_score"]), str(vix[v]) if v else ""]))
    where = {t: (b["age"], b["conf"]) for b in brackets for t in b["teams"]}
    extra, xnames = {}, {}
    for g in national or []:
        if g.get("gender", gender) != gender or (str(g["home_score"]) == "" and (g.get("start") or g["date"])[:10] < snap):
            continue  # other gender, or an unplayed national-event game dated before today (cancelled or never reported)
        v = " · ".join(x for x in (g.get("event_name") or "", g.get("venue") or "") if x)
        if v and v not in vix:
            vix[v] = len(venues); venues.append(v)
        row = ",".join([str(g["match_id"]), g.get("start") or g["date"], g["home_id"], g["away_id"],
                        str(g["home_score"]), str(g["away_score"]), str(vix[v]) if v else ""])
        for t in {g["home_id"], g["away_id"]}:
            if t in where:
                extra.setdefault(where[t], []).append(row)
        for t, n in ((g["home_id"], g.get("home_team")), (g["away_id"], g.get("away_team"))):
            if t not in where and n:
                xnames[t] = team_label(n)
    clubs = {}
    for b in brackets:
        for cid, cname in b["clubs"].values():
            if cid:
                clubs[cid] = cname
    dage, dconf = lg["default"].split(":", 1)
    if not any(b["age"] == dage and b["conf"] == dconf for b in brackets):  # past seasons may lack the default conference
        dage, dconf = next(((b["age"], b["conf"]) for b in brackets if b["age"] == dage), (brackets[0]["age"], brackets[0]["conf"]))
    return {"default": {"age": dage, "conf": dconf}, "snap": snap, "venues": venues, "brand": lg["label"],
            "leagues": [{"key": "Boys" if k == "boys" else "Girls", "file": page_file(k, season), "on": k == gender} for k in LEAGUES],
            "clubs": clubs, "localTimes": True, "xnames": xnames, "feedback": FEEDBACK, "flexName": "ECNL national events", "flexShort": "National",
            "histPre": "girls-season-" if gender == "girls" else "season-",
            "tiers": postseason.TIERS[gender], "postNotes": postseason.NOTES[gender],
            "brackets": [{"age": b["age"], "conf": b["conf"], "teams": {k: team_label(n) for k, n in b["teams"].items()},
                          "club": {k: v[0] for k, v in b["clubs"].items() if v[0]}, "groups": b.get("groups") or {},
                          "post": postseason.RULES[gender].get(b["conf"], {}).get(b["age"], []) if season == SEASON else [],
                          "raw": ";".join(league.get((b["age"], b["conf"]), [])),
                          "flex": ";".join(sorted(set(extra.get((b["age"], b["conf"]), []))))} for b in brackets]}

def analytics_tag():
    """analytics/fa.js inlined (the page stays one file), configured from analytics/config.json."""
    if not ANALYTICS_SITE:
        return ""
    try:
        cfg = json.load(open(f"{ROOT}/analytics/config.json"))
        js = open(f"{ROOT}/analytics/fa.js").read().replace("</", "<\\/")  # a "</script>" in it would end the tag
    except OSError:
        return ""
    conf = {"site": ANALYTICS_SITE, "projectId": cfg.get("projectId", ""), "apiKey": cfg.get("apiKey", ""),
            "sections": '.card[id^="s-"]'}
    return f"<script>window.FA_CONFIG={json.dumps(conf)};</script>\n<script>\n{js}</script>"

def write_calendars(gender, brackets, games, national):
    """cal/<team id>.ics for every team this season: its league and national-event games, with the result in the title
    once played. Calendar apps subscribe to these (webcal://), so new kickoff times and results reach phones by
    themselves. Times are local to the field (floating). Nothing time-dependent goes in (fixed DTSTAMP), so a file only
    changes when its games do, and only changed files are rewritten (a synced folder like iCloud Drive leaves
    "123 2.ics" duplicates when many files are deleted and recreated)."""
    out = f"{ROOT}/cal"
    os.makedirs(out, exist_ok=True)
    where = {t: b for b in brackets for t in b["teams"]}
    tx = lambda t: re.sub(r"([\\,;])", r"\\\1", str(t)).replace("\n", "\\n")
    def fold(line):  # RFC 5545: at most 75 octets a line, continuation lines start with a space
        b, parts = line.encode(), []
        while len(b) > (75 if not parts else 74):
            cut = 75 if not parts else 74
            while (b[cut] & 0xC0) == 0x80:  # don't split a UTF-8 character
                cut -= 1
            parts.append(b[:cut]); b = b[cut:]
        parts.append(b)
        return "\r\n ".join(x.decode() for x in parts)
    mine = {}
    for g in games:
        for side in ("home_id", "away_id"):
            if g[side] in where:
                mine.setdefault(g[side], {})[str(g["match_id"])] = dict(g, nat="")
    for g in national:
        if g.get("gender") != gender:
            continue
        for side in ("home_id", "away_id"):
            if g[side] in where:
                mine.setdefault(g[side], {})[str(g["match_id"]) + "n"] = dict(g, nat=g.get("event_name") or "national event")
    lg = LEAGUES[gender]
    for t, b in where.items():
        name, age = team_label(b["teams"][t]), b["age"]
        page = f"{SITE}{lg['file']}?age={age}&conf={re.sub(r'[^a-z0-9]+', '-', b['conf'].lower()).strip('-')}&show={t}"
        ev = []
        for g in sorted(mine.get(t, {}).values(), key=lambda g: g["start"]):
            home = g["home_id"] == t
            opp_id = g["away_id"] if home else g["home_id"]
            ob = where.get(opp_id)
            opp = team_label(ob["teams"][opp_id]) if ob else team_label(g["away_team"] if home else g["home_team"])
            res = ""
            if str(g["home_score"]) != "":
                f, a = (int(g["home_score"]), int(g["away_score"])) if home else (int(g["away_score"]), int(g["home_score"]))
                res = f" ({'W' if f > a else 'L' if f < a else 'D'} {f}–{a})"
            start = g["start"]
            when = ([f"DTSTART;VALUE=DATE:{start.replace('-', '')}"] if len(start) == 10 else
                    [f"DTSTART:{start.replace('-', '').replace(':', '').replace(' ', 'T')}00", "DURATION:PT2H"])
            title = f"{age} {name} {'vs' if home else 'at'} {opp}" + (" (national event)" if g["nat"] else "") + res
            desc = f"{lg['label']} · {age} {b['conf']}" + (f" · {g['nat']}" if g["nat"] else "") + (" · kickoff time not set yet" if len(start) == 10 else "")
            ev += ["BEGIN:VEVENT", f"UID:ecnl-{g['match_id']}{'-n' if g['nat'] else ''}-{t}@stw1.github.io", "DTSTAMP:20260801T000000Z", *when,
                   f"SUMMARY:{tx(title)}", *([f"LOCATION:{tx(g['venue'])}"] if g.get("venue") else []),
                   f"DESCRIPTION:{tx(desc)}\\n{tx(page)}", f"URL:{page}", "END:VEVENT"]
        cal = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//ecnl-dashboard//EN", "CALSCALE:GREGORIAN", "METHOD:PUBLISH",
               "X-WR-CALNAME:" + tx(f"{name} {age} · {lg['label']}"),
               "REFRESH-INTERVAL;VALUE=DURATION:PT6H", "X-PUBLISHED-TTL:PT6H", *ev, "END:VCALENDAR"]
        text, path = "\r\n".join(fold(l) for l in cal) + "\r\n", f"{out}/{t}.ics"
        try:
            same = open(path, newline="").read() == text
        except OSError:
            same = False
        if not same:
            with open(path, "w", newline="") as fh:
                fh.write(text)
    return {f"{t}.ics" for t in where}

def prune_calendars(wanted):
    """Remove calendars of teams no longer in any bracket, and sync-service duplicates."""
    for f in os.listdir(f"{ROOT}/cal"):
        if f not in wanted:
            os.remove(f"{ROOT}/cal/{f}")

def write_page(gender, data, season):
    lg = LEAGUES[gender]
    tpl = open(f"{ROOT}/template/dashboard_template.html").read().replace("<!--__ANALYTICS__-->", analytics_tag())
    text = f"{season.replace('-', '–')} season" + ("" if season == SEASON else " · final")
    html = (tpl.replace("/*__DATA__*/{}", json.dumps(data, ensure_ascii=False, separators=(",", ":")))
               .replace("__TITLE__", f"{lg['label']} standings and predictions").replace("__SEASON__", text))
    open(f"{ROOT}/{page_file(gender, season)}", "w").write(html)
    return len(html)

def add_priors(gender, data, brackets, before):
    import pastseasons
    if not before or not PRIOR_WEIGHT:
        return
    pri = pastseasons.priors(gender, brackets, before, PRIOR_WEIGHT, PRIOR_MODE)
    for d, b in zip(data["brackets"], brackets):
        d["prior"] = {k: pri[k] for k in b["teams"] if k in pri}

def build(gender, brackets, games, meta):
    import pastseasons
    past = pastseasons.seasons(gender)
    seasons = [{"key": SEASON.replace("-", "–"), "file": page_file(gender)}] + \
              [{"key": pastseasons.label(s), "file": page_file(gender, s), "past": True} for s in past]
    ng = f"{ROOT}/data/national_games.csv"
    nat = list(csv.DictReader(open(ng))) if os.path.exists(ng) else []
    data = page_data(gender, brackets, games, meta["snapshot"], national=nat)
    data["seasons"] = seasons
    data["hist"] = pastseasons.team_history(gender, brackets) if past else {}
    add_priors(gender, data, brackets, past[0] if past else None)
    # conference strength from games between conferences: this season's so far, starting from last season's
    import confstrength, national
    eff = confstrength.season_effects(gender)
    cross = national.read(f"{ROOT}/data/cross.csv")
    data["confAdj"] = confstrength.effects(gender, SEASON, brackets, games, cross, eff["alone"].get(past[0]) if past else None)
    data["confPrior"] = bool(past)
    data["crossN"] = dict(collections.Counter(r["age"] for r in cross if r["gender"] == gender))
    size = write_page(gender, data, SEASON)
    cals = write_calendars(gender, brackets, games, nat)
    played = sum(1 for g in games if str(g["home_score"]) != "")
    print(f"Built {page_file(gender)} ({size//1024} KB): {len(brackets)} brackets, {sum(len(b['teams']) for b in brackets)} teams, "
          f"{played}/{len(games)} games played, history for {len(data['hist'])} teams")
    hist_cross = national.read(f"{ROOT}/data/history/cross.csv")
    for i, s in enumerate(past):  # finished seasons: same template with DATA.past set
        pb, pg = pastseasons.load(gender, s)
        d = page_data(gender, pb, pg, max(g["start"][:10] for g in pg), s,
                      national=[r for r in hist_cross if r["gender"] == gender and r["season"] == s])
        d.update(seasons=seasons, past=pastseasons.label(s), hist=pastseasons.team_history(gender, pb, before=s),
                 confAdj=eff["final"].get(s), confPrior=i + 1 < len(past), crossN=dict(collections.Counter(r["age"] for r in hist_cross
                                                                               if r["gender"] == gender and r["season"] == s)))
        add_priors(gender, d, pb, past[i + 1] if i + 1 < len(past) else None)  # the replayed accuracy starts from the season before
        size = write_page(gender, d, s)
        print(f"Built {page_file(gender, s)} ({size//1024} KB): {len(pb)} brackets")
    return cals

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--tz", default="America/Los_Angeles", help="time zone for the snapshot date")
    a = ap.parse_args()
    postseason.check()
    meta = {"snapshot": datetime.now(ZoneInfo(a.tz)).date().isoformat(), "season": SEASON}
    if a.offline:
        meta = json.load(open(f"{ROOT}/data/meta.json"))
    got = {}
    for gender in LEAGUES:
        if a.offline:
            got[gender] = load(gender)
        else:
            got[gender] = fetch(gender)
            if not got[gender][0]:
                sys.exit(f"No {gender} brackets found - check LEAGUES event ids")
            save(gender, *got[gender], meta)
    if not a.offline:  # games between conferences at this season's national events (for the national rankings)
        import national
        national.current({g: v[0] for g, v in got.items()})
    wanted = set()
    for gender, (brackets, games) in got.items():
        wanted |= build(gender, brackets, games, meta)
    prune_calendars(wanted)
