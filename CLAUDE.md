# ECNL Boys & Girls dashboard

Personal project (Stephen). Public site: https://stw1.github.io/ecnl-dashboard/ (Boys) and `girls.html` (Girls).
The repo is stw1/ecnl-dashboard, served by GitHub Pages from the `main` branch root. Each page holds every conference
and age group (U13 to U18/19) and shows one at a time: standings, postseason chances, who beat who, power rankings,
results, predictions, national rankings, Insights, club and team pages (with each team's previous seasons and national-event
games), plus past seasons back to 2020-21 and a subscribable calendar per team. Tables match ECNL's official standings.
First-time visitors land on U14 Northwest. It's adapted from the MLS NEXT dashboard (stw1/mlsnext-dashboard) and shares its model and
template. That template's Flex and MLS Cup code paths are unused here.

**Never edit the built `.html` pages by hand.** Edit `template/dashboard_template.html` or the scripts, then rebuild.

## Layout
```
template/dashboard_template.html   the page: all model, simulation and rendering logic is inline JS; data goes in DATA
scripts/refresh.py                 fetch this season from TGS -> data/ -> build every page (stdlib only)
scripts/postseason.py              ECNL's official postseason qualification rules per conference and age group
scripts/history.py                 one-off download of past seasons -> data/history/
scripts/pastseasons.py             past-season data, team history ("same players"), last-season priors
scripts/national.py                cross-conference games from national events and playoffs
scripts/confstrength.py            conference strength for the national rankings (+ --evaluate backtest)
scripts/ratings.py                 Python copy of the goals model (fit, probs, fit_conf)
scripts/priors.py                  backtest that chose the last-season prior setting
scripts/checkstandings.py          compare our tables with ECNL's official standings (the workflow runs it)
data/{boys,girls}_games.csv        this season's games (blank scores = not played); *_brackets.json teams, clubs, groups
data/cross.csv                     this season's cross-conference games; data/national_events.json their event ids
data/meta.json                     snapshot date and season
data/history/                      past seasons' games and brackets, cross.csv, confadj_<gender>.json (cache)
data/national_games.csv            this season's national-event games (played and upcoming) for team pages
cal/<team id>.ics                  one subscribable calendar per team (this season), rebuilt by refresh.py
analytics/                         fa.js + config.json (no API key), copied from the MLS NEXT repo's analytics kit
index.html, girls.html             this season (Boys, Girls)
season-<season>.html, girls-season-<season>.html   finished seasons (same template, DATA.past set)
.github/workflows/refresh.yml      weekend auto-refresh
manifest.webmanifest, icon.svg, *.png   home-screen icons (regenerate PNGs from icon.svg with qlmanage + sips)
```

## Common tasks
- **Update with new scores:** `python3 scripts/refresh.py`. This fetches both genders, collects this season's
  cross-conference games and rebuilds all 14 pages, in about 6 minutes.
- **Rebuild without network** (for example, after editing the template): `python3 scripts/refresh.py --offline` (about 8 s).
- **Auto-refresh:** `.github/workflows/refresh.yml` runs refresh.py on Sat & Sun (~1, 5, 9 pm Pacific) and Mon & Tue
  (~9 am). It commits and pushes only when the games, cross-conference or national-event game files change, then runs
  `checkstandings.py`, which fails the run (GitHub emails) if any table stops matching ECNL's. Run it by hand with
  `gh workflow run refresh.yml -R stw1/ecnl-dashboard`. GitHub pauses scheduled workflows after 60 days with no commits.
- **Publish by hand:** `git pull` first (the bot commits too), then commit and push. Pages redeploys in about a minute.
- **Links:** `?age=U15&conf=southwest` (conference lowercased, spaces become dashes), `&team=seattle-united`
  highlights a team, `&show=<team id>` opens a team page, `?age=U14&conf=national` shows national rankings,
  `?age=U14&conf=insights` shows Insights, and `?club=<club-name>` shows a club page.
- **Testing:** the preview server reads a copy outside iCloud (`.claude/launch.json` "ecnl-dashboard", port 8792). Copy
  the built pages and `cal/` to it and load every bracket in iframes, checking for console errors. After changing
  table logic, run `python3 scripts/checkstandings.py` (needs fresh data: run refresh.py first).

## Every August (new season)
1. Scan TGS event ids (get-event-details-by-eventID) for "ECNL Boys|Girls <conference> <season>". Put them in
   `refresh.LEAGUES` and set `refresh.SEASON`.
2. Add the season that just ended to `history.EVENTS`, then run `python3 scripts/history.py`. Move this season's
   `data/cross.csv` rows into `data/history/cross.csv` (or rerun `scripts/national.py`), and delete
   `data/history/confadj_*.json` so it's recomputed.
3. Replace the tables in `scripts/postseason.py` from the new Boys and Girls postseason PDFs on theecnl.com.
   `postseason.check()` must pass.
4. Reset `national.CURRENT` and `data/national_events.json` to the new season's first national event id.

## Data source (TotalGlobalSports / AthleteOne, public JSON, no key)
- `api.athleteone.com/api/Event/get-event-details-by-eventID/{event}` gives the name ("ECNL Boys Northwest 2026-27").
  `.../get-event-schedule-or-standings/{event}` lists divisions and flights. `.../get-schedules-by-flight/{event}/{flight}/0`
  returns games: matchID, gameDate (local to the field, no time zone), team and club ids and names, scores
  (null = not played), complex, venue and friendly.
- One event per conference. Some conferences split an age group into flights. Flights that play each other become one
  bracket, with each team's flight as a group tag. Flights that never meet become separate brackets ("Northeast North").
- Feed quirks handled: friendlies and "TBD" opponents dropped, placeholder dates (0001-01-01) dropped, and midnight
  kickoffs mean the time isn't set ("time TBD"). Unplayed games dated before today show as "waiting for a score",
  not as upcoming, but are still simulated.
- **Standings match ECNL's official ones:** `python3 scripts/checkstandings.py` compares every team's GP/W/D/L/GF/GA and the
  order in each flight with `Event/get-standings-by-div-and-flight/{division}/{flight}/{event}`. The workflow runs it as a
  warning-only step. ECNL's order is points per game, then head-to-head for two tied teams, then **total** goal
  difference and total goals scored. On 2026-10-02 every record and position matched for all 1,812 teams. Rerun after
  changing table logic.
- Two-division conferences (a third or more of the games between divisions) are one bracket with group tags. Flights that
  rarely meet are separate conferences (`refresh.FLIGHT_CONF`). Girls 2020-22 "Northwest" is really Northern Cal (Bay Area),
  Northwest (Pacific) and Mountain.
- Team names are cleaned by `refresh.team_label` ("XF ECNL B2013/14 2" becomes "XF 2"). Clubs are grouped by TGS club id.

## Postseason
`scripts/postseason.py` copies the 2026-27 Boys and Girls postseason PDFs from theecnl.com. It covers Champions League
spots, the top teams in each group, cross-conference wildcards, play-ins, and the girls' North American Cup and
Showcase Cups. `check()` asserts that the Champions League spots add up to the documents' field sizes, and every build
runs it. The page simulates each season with these rules, with wildcard partner conferences simulated side by side.
It shows chances per tier, lines in the standings, and a tag for where each team would go if the season ended today.
League Cup winners can't be predicted, so those spots go to the team in the table.

## Past seasons (2020-21 to 2025-26)
- `scripts/history.py` downloads each past season, about 3 min per season and gender. TGS has full conference seasons
  only from 2020-21; its older ECNL "conference" events are empty.
- Age groups appear as "BU13", birth years ("B2010" in 2022-23 = U13) or "U13 Boys". `refresh.age_of` converts all
  three and skips U11/U12 and composite squads. "Norcal" becomes Northern Cal; "Northeast" (later split into New
  England and North Atlantic) is kept as is.
- Team history (`pastseasons.team_history`, shown as "Same players, earlier seasons"): each season, step back one age
  group. Match by TGS team id when it carried over (about half do), else the same club id with the same cleaned team
  name, else the club's only team at that age. About 89% of this season's U14+ teams match.
- Last-season priors: `refresh.PRIOR_WEIGHT, PRIOR_MODE = 0.75, "avg"`. Each team's starting rating is 0.75 × the average
  of its cohort match (one age younger) and its same-age match last season. `scripts/priors.py` replays past seasons:
  2025-26 log-loss boys 0.863 → 0.842, girls 0.826 → 0.773. On 2026-27's first games (the school-year switch season),
  correct picks went from 52% to 59% (boys) and 55% to 65% (girls).

## National rankings: conference strength
- Conferences meet only at ECNL national events (Phoenix, Florida, Las Vegas, ...) and the playoffs. `scripts/national.py`
  keeps a game when both teams are in that season's conference brackets (same TGS team ids, same age group,
  different conferences). There are about 1,100–2,900 per past season and gender. This season's go to `data/cross.csv`
  on every live refresh. New national events are found automatically: ids after the last known one are checked by name
  and remembered in `data/national_events.json`.
- `scripts/confstrength.py`: per age group, a joint fit (`ratings.fit_conf`: attack = conference + team effect) of
  conference games plus cross-conference games. Conference effects start from last season's same age group
  (`WEIGHT = 1.0`). Past seasons are cached in `data/history/confadj_<gender>.json`. Embedded as
  `DATA.confAdj[age] = {mu, conf: [attack, defense]}`. The national rating is exp(mu + att + ca) − exp(mu − def − cd),
  and the national page lists each conference's strength.
- Backtest (`confstrength.py --evaluate`, predicting each month's cross-conference games from earlier ones):
  log-loss 0.99 → 0.95 (boys 2025-26), 0.99 → 0.94 (girls 2025-26), 0.96 → 0.91 (girls 2024-25), and correct picks went
  from about 50% to 55%. The model's conference strengths track the raw goal difference per game in those games.

## National-event games on team pages
- `national.current()` also writes `data/national_games.csv`: every game at this season's national events involving an
  ECNL conference team, played or upcoming, with the event name, time and venue. refresh.py puts them in each bracket's
  `flex` slot (a name kept from MLS NEXT "Flex" games). Venue = "event name · field", and opponents outside ECNL
  conferences are named via `DATA.xnames`. Past season pages get that season's cross-conference games from
  `data/history/cross.csv`. Unplayed ones dated before today are dropped.
- They show with a "National" tag in results, upcoming games, the My team card (separate W-D-L), team pages
  (schedule, form, "National events" record), club pages and the calendar. Never in the league table.
- Predictions (`predictG` in the template): neutral field (no home edge). Against another conference, each team's rating
  inside its conference plus its conference's strength (`crossModel`, `DATA.confAdj`). No prediction when the opponent
  isn't in an ECNL conference. Games between two teams of the same conference also feed that conference's ratings.

## Model (template JS, search for "fit penalised Poisson model")
Poisson goals model with attack and defense ratings per team, ridge priors (σ 0.35, centered on last season's
rating when there is one), home edge, and a Dixon-Coles low-score adjustment. The season sim plays out every remaining
game 10,000 times and ranks the way ECNL does (points per game, then total GD and GF). "How accurate are the
predictions?" is a walk-forward backtest of the current model.

## Insights and team history
- **Insights** (`?age=U14&conf=insights`, "Insights (interesting facts)" in the conference menu; `drawInsights` in the
  template): one age group across all conferences. It covers the biggest turnarounds and drops (points per game vs the
  same players last season, from `DATA.hist`), unbeaten and winless teams, current winning streaks, goals for and
  against per game, biggest upsets (wins the current ratings gave under 25%), best records at national events, closest
  title races and Champions League bubble teams (season sim, this season only), strongest conferences (`DATA.confAdj`)
  and the strongest clubs across age groups (average table position, 4+ teams). Teams need 3+ games. It works on past
  season pages too.
- **Team pages: "Previous seasons"** lists this season and every earlier one for the same players: finish (with a bar),
  W-D-L, points per game and goals, each linked to that season's team page. A line compares last season with now and
  gives the best finish. "In other age groups" lists the club's other teams (matched by club id).

## Calendars, feedback, analytics
- **Calendars:** `refresh.write_calendars` writes `cal/<team id>.ics` for every team this season: league and national-event
  games, results in the title once played, times local to the field (floating), and a fixed DTSTAMP so a file only
  changes when its games do. Only changed files are rewritten and stray ones removed (`prune_calendars`), which avoids
  iCloud "123 2.ics" duplicates (also in .gitignore). "Add to calendar" opens a panel: subscribe on iPhone/Mac (webcal),
  Google Calendar, copy the link, or download the remaining games once. Past-season pages only download.
- **Feedback:** `refresh.FEEDBACK = "support@spaikz.com"` adds "Report a problem or suggest an idea" to the footer, as an
  email link with the page address.
- **Analytics:** `refresh.ANALYTICS_SITE = "ecnl"`. `analytics_tag()` inlines `analytics/fa.js` into every page
  (`<!--__ANALYTICS__-->` in the head), configured from `analytics/config.json`. This is the shared Firebase project
  `spaikz-dashboards`, where the MLS NEXT repo owns the rules and report. No API key is published or committed:
  the tracker writes to Firestore without one, and the security rules decide. The page calls `fa.view({view, league, season,
  age, conf, team, club, following, page})`, and the footer notes anonymous stats with an opt-out (`?fa=off`). There are
  no cookies, and DNT/GPC are respected. Report: https://spaikz-dashboards.web.app/ (pick "ecnl"). To update the tracker, copy fa.js from the MLS repo.
- **Home:** the site title links home, and club, national and team pages get a "‹ Home" button.
- **Official check in the workflow:** runs after publishing and fails (GitHub emails a warning) on any record or order
  difference. Teams with a game in the last 48 hours are reported, not flagged.

## Security
- No API keys or other secrets in the repo or the pages. GitHub secret scanning and push protection are on. In October 2026 a
  Firebase web key was committed for analytics. It was deleted in Google Cloud (requests now fail with "API key expired")
  and the alert was closed as revoked. Analytics now works without a key, and the report's restricted key lives only
  in the deployed report (MLS NEXT repo, `analytics/deploy_report.sh`).
- The only outside writes are anonymous analytics events, which the Firestore rules limit to create-only, schema-checked
  events for listed sites. The Google Cloud project has no billing enabled.

## Conventions
- Each page is a single self-contained HTML file with all data embedded and no external scripts.
- Kickoff times are stored and shown local to the field ("YYYY-MM-DD HH:MM"). The calendar export uses floating local times.
- Python 3.9+ standard library only (the workflow uses 3.12).
