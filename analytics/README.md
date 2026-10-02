# Analytics

`fa.js` and `config.json` are copies of the first-party analytics kit from the MLS NEXT dashboard
(stw1/mlsnext-dashboard, `analytics/`). That repo holds the full README, the Firestore rules and the report page.
No API key is used or committed: the tracker writes to Firestore's REST API without one, and the security rules
decide what's accepted (create-only, schema-checked, for listed sites).
Both dashboards write to the same Firebase project (`spaikz-dashboards`); this site's code is `ecnl`.

- Report (pick "ecnl" in the site menu): https://spaikz-dashboards.web.app/
- refresh.py inlines `fa.js` into every page, configured from `config.json` with `ANALYTICS_SITE = "ecnl"`.
- No cookies; Do Not Track and Global Privacy Control are respected. Open the site once with `?fa=off` on your own
  devices so your visits don't count (`?fa=on` undoes it).
- To update the tracker, copy `fa.js` from the MLS repo again. Rules and report changes happen there.
