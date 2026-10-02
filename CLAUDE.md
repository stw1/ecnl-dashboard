# ECNL Boys & Girls dashboard

Public site: https://stw1.github.io/ecnl-dashboard/ (repo stw1/ecnl-dashboard, GitHub Pages from main).
`index.html` = ECNL Boys, `girls.html` = ECNL Girls. Both are built from `template/dashboard_template.html`
by `scripts/refresh.py`. Don't edit the HTML pages by hand; edit the template and rebuild.

- `python3 scripts/refresh.py`: live fetch from the public TotalGlobalSports API (api.athleteone.com/api/Event), then rebuild
- `python3 scripts/refresh.py --offline`: rebuild from `data/` only
- `.github/workflows/refresh.yml` runs this on Sat/Sun and Mon/Tue and commits when `data/*_games.csv` changes

The data is one TGS "event" per conference (`LEAGUES` in refresh.py). Update the event ids and `SEASON` every August.
Some conferences split an age group into flights that still play each other. Those flights are merged into one
bracket, and each team's flight is shown as a group tag. Kickoff times are local to the field, as TGS publishes them.
Clubs are grouped by TGS club id. The template is adapted from the MLS NEXT dashboard (stw1/mlsnext-dashboard).
Its Flex, Cup and past-season code paths are unused here.

Postseason: `scripts/postseason.py` holds ECNL's official qualification rules per conference and age group,
copied from the season's Boys and Girls postseason PDFs on theecnl.com. These cover Champions League spots,
group winners, wildcards, play-ins, and the girls' North American Cup and Showcase Cups. `check()` asserts that the
Champions League spots add up to the documents' field sizes, and every build runs it. Replace the tables every season.
The template simulates each season with these rules. It simulates wildcard partner conferences side by side and
tags each team with where it would go if the season ended today.

## Past seasons (2020-21 to 2025-26)
- `scripts/history.py` downloads each past season's conference games from TGS into `data/history/<gender>_<season>.csv`
  and `_brackets.json`. It's a one-off (about 3 min per season and gender), not part of the weekend refresh. TGS has full
  conference seasons from 2020-21 on; its older ECNL "conference" events are empty. The event ids are listed in
  `history.EVENTS`, found by scanning get-event-details-by-eventID. Next August, add the season that just ended.
- Age groups appear as "BU13", birth years ("B2010" in 2022-23 = U13) or "U13 Boys". `refresh.age_of` converts all
  three and skips U11/U12 and composite squads. Some conference names changed: "Norcal" is now Northern Cal, and
  "Northeast" (later split into New England and North Atlantic) is kept as is. Flights that never play each other
  become separate brackets ("Northeast North"); flights that do are merged with group tags.
- refresh.py builds `season-<season>.html` (Boys) and `girls-season-<season>.html` from these files on every run. They
  use the same template with `DATA.past` set. The season picker and the Boys|Girls switch link the matching pages.
- Team history (`pastseasons.team_history`, shown as "Same players, earlier seasons"): each season, step back one age
  group. Match by TGS team id when it carried over (about half do), else the same club id with the same cleaned team
  name, else the club's only team at that age. About 89% of this season's U14+ teams match.
- Last-season priors: `refresh.PRIOR_WEIGHT, PRIOR_MODE = 0.75, "avg"`. Each team's starting rating is 0.75 × the average
  of its cohort match (one age younger) and its same-age match last season. `scripts/priors.py` replays past seasons:
  2025-26 log-loss boys 0.863 → 0.842, girls 0.826 → 0.773. On 2026-27's first games (the school-year switch season),
  correct picks went from 52% to 59% (boys) and 55% to 65% (girls).

## National rankings: conference strength
- Conferences meet only at ECNL national events (Phoenix, Florida, Las Vegas, ...) and the playoffs. `scripts/national.py`
  keeps those games when both teams are in that season's conference brackets (same TGS team ids, same age group,
  different conferences): past seasons go to `data/history/cross.csv` (one-off, about 1,100–2,900 per season and gender),
  this season to `data/cross.csv`, which refresh.py updates on every live run (about 2 min). Add new national event ids
  to `national.CURRENT` as they appear (scan get-event-details-by-eventID past the last known id).
- `scripts/confstrength.py`: per age group, a joint fit (`ratings.fit_conf`: attack = conference + team effect) of
  conference games plus cross-conference games. Conference effects start from last season's same age group
  (`WEIGHT = 1.0`). Past seasons are cached in `data/history/confadj_<gender>.json`; delete it after adding a season.
  Embedded as `DATA.confAdj[age] = {mu, conf: [attack, defense]}`. The page's national rating is
  exp(mu + att + ca) − exp(mu − def − cd), and the national page lists each conference's strength.
- Backtest (`confstrength.py --evaluate`, predicting each month's cross-conference games from earlier ones):
  log-loss 0.99 → 0.95 (boys 2025-26), 0.99 → 0.94 (girls 2025-26), 0.96 → 0.91 (girls 2024-25). Correct picks went
  from about 50% to 55%. Last season alone helps; this season's games plus last season's is best. The model's
  conference strengths track the raw goal difference per game in those games.
