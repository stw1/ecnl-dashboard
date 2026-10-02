"""
ECNL 2026-27 postseason qualification, per conference and age group, from ECNL's published documents:
  Boys:  theecnl.com/documents/2026/8/17/2026-27_ECNL_Boys_Postseason_Structure.pdf
  Girls: theecnl.com/documents/2026/9/11/2026-27_ECNL_Girls_Post-Season_Structure.docx_1.pdf
Every spot is decided by points per game from conference games only. Update every season.

Each age group has a list of steps, applied in order to the final table. A step is [tier, n, how, partner]:
  how ""   the next n teams in the table that don't have a spot yet
      "g"  the top n of each group (divisions such as East/West)
      "g2" the best n of the teams that finish 2nd in their group
      "lc" the next n teams, unless the League Cup winner takes the spot (the cup isn't in the data)
      "wc" wildcard: the next team, if its points per game beats the partner conference's wildcard team
      "pi" the next n teams play a play-in game against the partner conference's team for a spot
"""

TIERS = {
    "boys": {
        "cl": ["Champions League", "CL", "ECNL National Playoffs (Champions League). The last four go on to the ECNL National Finals."],
    },
    "girls": {
        "cl": ["Champions League", "CL", "ECNL National Playoffs (Champions League). The last four go on to the ECNL National Finals."],
        "pi": ["Champions League play-in", "Play-in", "One play-in game against the other conference's team for a Champions League spot."],
        "nac": ["North American Cup", "NAC", "ECNL National Playoffs: North American Cup (U15–U17)."],
        "sa": ["Showcase Cup A", "SC-A", "ECNL National Playoffs: Showcase Cup A (U16–U17)."],
        "sb": ["Showcase Cup B", "SC-B", "ECNL National Playoffs: Showcase Cup B (U16–U17)."],
    },
}
NOTES = {
    "boys": {"U18/19": "U18/19 has a 32-team Champions League; teams that lose on day 1 move to the North American Cup."},
    "girls": {"U18/19": "U18/19 qualifiers each play one play-in game; the 8 winners go to the ECNL National Finals."},
}

def _ages(spec):
    order = ["U13", "U14", "U15", "U16", "U17", "U18/19"]
    if "-" in spec:
        a, b = spec.split("-")
        return order[order.index(a):order.index(b) + 1]
    return [spec]

def _expand(table):
    out = {}
    for conf, by_age in table.items():
        for spec, steps in by_age.items():
            for age in _ages(spec):
                out.setdefault(conf, {}).setdefault(age, []).extend(steps)
    return out

B = lambda n, how="", partner="": ["cl", n, how, partner]
BOYS = _expand({
    "New England": {"U13": [B(2), B(1, "wc", "North Atlantic")], "U14": [B(4)], "U15-U17": [B(2, "g")],
                    "U18/19": [B(1), B(1, "wc", "North Atlantic")]},
    "North Atlantic": {"U13": [B(2), B(1, "wc", "New England")], "U14-U17": [B(4)],
                       "U18/19": [B(1), B(1, "wc", "New England")]},
    "Mid-Atlantic": {"U13": [B(4)], "U14-U17": [B(6)], "U18/19": [B(3)]},
    "Southeast": {"U13": [B(4)], "U14-U17": [B(5)], "U18/19": [B(3)]},
    "Mid-America": {"U13": [B(2)], "U14-U17": [B(3)], "U18/19": [B(1)]},
    "Florida": {"U13": [B(3)], "U14-U17": [B(3), B(1, "wc", "Mountain")], "U18/19": [B(2)]},
    "Ohio Valley": {"U13": [B(2)], "U14-U17": [B(3), B(1, "wc", "Texas")], "U18/19": [B(1), B(1, "wc", "Midwest")]},
    "Midwest": {"U13": [B(2)], "U14-U17": [B(3)], "U18/19": [B(1), B(1, "wc", "Ohio Valley")]},
    "Texas": {"U13": [B(7)], "U14-U17": [B(9), B(1, "wc", "Ohio Valley")], "U18/19": [B(4)]},
    "Southwest": {"U13": [B(6)], "U14-U17": [B(7)], "U18/19": [B(4)]},
    "Heartland": {"U13": [B(2)], "U14": [B(4)], "U15-U17": [B(1, "g"), B(2)], "U18/19": [B(2)]},
    "Mountain": {"U13": [B(1, "g"), B(1, "g2")], "U14-U17": [B(1, "g"), B(1, "g2"), B(1, "wc", "Florida")],
                 "U18/19": [B(1, "g")]},
    "Northern Cal": {"U13": [B(4)], "U14-U17": [B(5), B(1, "wc", "Far West")], "U18/19": [B(2)]},
    "Northwest": {"U13": [B(3)], "U14-U17": [B(4)], "U18/19": [B(2)]},
    "Far West": {"U13": [B(1)], "U14-U17": [B(2), B(1, "wc", "Northern Cal")], "U18/19": [B(1)]},
})

G = lambda tier, n, how="", partner="": [tier, n, how, partner]
GIRLS = _expand({
    "Mid-Atlantic": {"U13-U14": [G("cl", 4)], "U15-U17": [G("cl", 3), G("cl", 1, "lc"), G("nac", 2)],
                     "U16-U17": [G("sa", 1), G("sb", 1)], "U18/19": [G("cl", 2)]},
    "Midwest": {"U13-U14": [G("cl", 2, "g"), G("cl", 2)], "U15-U17": [G("cl", 6), G("nac", 2)],
                "U16-U17": [G("sa", 2), G("sb", 1)], "U18/19": [G("cl", 2)]},
    "North Atlantic": {"U13-U14": [G("cl", 3), G("pi", 1, "pi", "New England")],
                       "U15-U17": [G("cl", 2), G("cl", 1, "lc"), G("pi", 1, "pi", "New England"), G("nac", 1)],
                       "U16-U17": [G("sa", 1), G("sb", 1)], "U18/19": [G("cl", 1)]},
    "New England": {"U13-U17": [G("cl", 3), G("pi", 1, "pi", "North Atlantic")], "U15-U17": [G("nac", 1)],
                    "U16-U17": [G("sa", 1)], "U18/19": [G("cl", 1)]},
    "Northern Cal": {"U13-U17": [G("cl", 4)], "U15-U17": [G("nac", 1)], "U16-U17": [G("sa", 1), G("sb", 1)],
                     "U18/19": [G("cl", 1)]},
    "Northwest": {"U13-U17": [G("cl", 3)], "U15-U17": [G("nac", 1)], "U16-U17": [G("sa", 2), G("sb", 1)],
                  "U18/19": [G("cl", 1)]},
    "Ohio Valley": {"U13-U14": [G("cl", 4)], "U15-U17": [G("cl", 2, "g"), G("nac", 2)], "U16-U17": [G("sa", 2)],
                    "U18/19": [G("cl", 2)]},
    "Southeast": {"U13-U17": [G("cl", 5)], "U15-U17": [G("nac", 2)], "U16-U17": [G("sa", 2), G("sb", 1)],
                  "U18/19": [G("cl", 2)]},
    "Southwest": {"U13-U17": [G("cl", 8)], "U15-U17": [G("nac", 2)], "U16-U17": [G("sa", 2), G("sb", 1)],
                  "U18/19": [G("cl", 2)]},
    "Texas": {"U13-U17": [G("cl", 6), G("cl", 1, "lc")], "U15-U17": [G("nac", 2)], "U16-U17": [G("sa", 2), G("sb", 1)],
              "U18/19": [G("cl", 2)]},
})
RULES = {"boys": BOYS, "girls": GIRLS}

# Champions League spots per age group, to check the tables above against the documents' totals
TOTALS = {"boys": {"U13": 48, "U14": 68, "U15": 68, "U16": 68, "U17": 68, "U18/19": 32},
          "girls": {"U13": 48, "U14": 48, "U15": 48, "U16": 48, "U17": 48, "U18/19": 16}}

def check():
    """Champions League spots add up to the documents' field sizes (a wildcard or play-in pair = one spot)."""
    for gender, rules in RULES.items():
        for age, want in TOTALS[gender].items():
            got, pairs = 0, set()
            for conf, by_age in rules.items():
                for tier, n, how, partner in by_age.get(age, []):
                    if how in ("wc", "pi"):
                        pairs.add(tuple(sorted((conf, partner))))
                    elif tier == "cl":
                        got += n * (2 if how == "g" else 1)
            got += len(pairs)
            assert got == want, f"{gender} {age}: {got} Champions League spots, documents say {want}"

if __name__ == "__main__":
    check()
    print("Postseason tables match the documents' totals.")
