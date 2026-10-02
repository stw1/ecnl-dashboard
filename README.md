# ECNL Boys & Girls dashboard

Unofficial standings, predictions and national rankings for every ECNL Boys and Girls conference and age group.

- **Boys:** https://stw1.github.io/ecnl-dashboard/
- **Girls:** https://stw1.github.io/ecnl-dashboard/girls.html

## What's on it
- **Standings** ranked by points per game (ECNL's rule), with a 10,000-run season simulation: projected points,
  chance of finishing 1st, and chances of each postseason spot.
- **Postseason:** ECNL's official 2026–27 qualification rules for each conference and age group, covering the
  Champions League, wildcards and play-ins, and the girls' North American Cup and Showcase Cups. Each team is tagged
  with where it would go if the season ended today.
- **Who beat who, power rankings, results and predictions** for every remaining game, including national-event
  (showcase) games, and an accuracy check that replays the season.
- **National rankings** across all conferences, adjusted for conference strength measured from games between
  conferences at ECNL national events and the playoffs.
- **Club pages** (all of a club's teams) and **team pages**, including where the same players finished in earlier seasons.
- **Past seasons** back to 2020–21, and each team's previous seasons on its team page.
- **Insights:** the interesting stuff for each age group, such as turnarounds from last season, unbeaten teams, upsets, streaks, title races and playoff bubble teams.
- **Calendars:** subscribe to any team's schedule on iPhone, Mac or Google Calendar; it updates by itself.
- **Matches ECNL's official standings:** every record and position, checked after each update.
- **Follow a team:** shareable links (`?age=U14&conf=northwest&team=seattle-united`), "new since your last visit"
  markers, dark mode and add-to-home-screen support.

Scores update automatically on weekends (Saturday to Tuesday) through GitHub Actions, and every update is checked
against ECNL's official standings. The site counts anonymous page views (no cookies; open it once with `?fa=off` to
opt out). Problems or ideas: support@spaikz.com.

## How it works
Data comes from TotalGlobalSports, ECNL's results platform (public JSON). `scripts/refresh.py` fetches it and builds
self-contained HTML pages from `template/dashboard_template.html`. Predictions use a Poisson goals model with a
Dixon-Coles adjustment. Each team starts the season from last season's rating, which raised correct picks on this
season's early games from 52% to 59% (boys) and 55% to 65% (girls). See `CLAUDE.md` for the details and maintenance steps.

```bash
python3 scripts/refresh.py            # fetch the latest scores and rebuild every page
python3 scripts/refresh.py --offline  # rebuild from data/ only
```

Not affiliated with ECNL. Sister project: [MLS NEXT dashboard](https://stw1.github.io/mlsnext-dashboard/).
