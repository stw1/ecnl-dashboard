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
