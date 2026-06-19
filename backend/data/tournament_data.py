"""World Cup 2026 — real tournament data.

All data based on FIFA official 2025-12-05 draw and 2026-06-14 matchday state.
Source: FIFA.com draw + openfootball/worldcup.json (fallback embedded).

ALL TIMES ARE IN UTC (统一协调世界时). Frontend converts to user-local CST for display.
Venue-local times were in the original sources but kept as UTC in DB for consistency.
"""
GROUPS: dict[str, list[dict]] = {
    "A": [
        {"name": "Mexico",          "confederation": "CONCACAF", "fifa_rank": 15, "is_host": 1, "appearances": 17},
        {"name": "South Africa",    "confederation": "CAF",      "fifa_rank": 60, "is_host": 0, "appearances": 4},
        {"name": "South Korea",     "confederation": "AFC",      "fifa_rank": 23, "is_host": 0, "appearances": 11},
        {"name": "Czechia",         "confederation": "UEFA",     "fifa_rank": 36, "is_host": 0, "appearances": 9},
    ],
    "B": [
        {"name": "Canada",          "confederation": "CONCACAF", "fifa_rank": 28, "is_host": 1, "appearances": 3},
        {"name": "Bosnia & Herzegovina", "confederation": "UEFA", "fifa_rank": 71, "is_host": 0, "appearances": 1},
        {"name": "Qatar",           "confederation": "AFC",      "fifa_rank": 34, "is_host": 0, "appearances": 2},
        {"name": "Switzerland",     "confederation": "UEFA",     "fifa_rank": 19, "is_host": 0, "appearances": 12},
    ],
    "C": [
        {"name": "Brazil",          "confederation": "CONMEBOL", "fifa_rank": 5,  "is_host": 0, "appearances": 22},
        {"name": "Morocco",         "confederation": "CAF",      "fifa_rank": 11, "is_host": 0, "appearances": 7},
        {"name": "Haiti",           "confederation": "CONCACAF", "fifa_rank": 87, "is_host": 0, "appearances": 1},
        {"name": "Scotland",        "confederation": "UEFA",     "fifa_rank": 39, "is_host": 0, "appearances": 9},
    ],
    "D": [
        {"name": "USA",             "confederation": "CONCACAF", "fifa_rank": 16, "is_host": 1, "appearances": 12},
        {"name": "Paraguay",        "confederation": "CONMEBOL", "fifa_rank": 48, "is_host": 0, "appearances": 9},
        {"name": "Australia",       "confederation": "AFC",      "fifa_rank": 26, "is_host": 0, "appearances": 6},
        {"name": "Türkiye",         "confederation": "UEFA",     "fifa_rank": 42, "is_host": 0, "appearances": 3},
    ],
    "E": [
        {"name": "Germany",         "confederation": "UEFA",     "fifa_rank": 9,  "is_host": 0, "appearances": 20},
        {"name": "Curaçao",         "confederation": "CONCACAF", "fifa_rank": 82, "is_host": 0, "appearances": 1},
        {"name": "Côte d'Ivoire",   "confederation": "CAF",      "fifa_rank": 45, "is_host": 0, "appearances": 4},
        {"name": "Ecuador",         "confederation": "CONMEBOL", "fifa_rank": 24, "is_host": 0, "appearances": 4},
    ],
    "F": [
        {"name": "Netherlands",     "confederation": "UEFA",     "fifa_rank": 7,  "is_host": 0, "appearances": 11},
        {"name": "Japan",           "confederation": "AFC",      "fifa_rank": 18, "is_host": 0, "appearances": 8},
        {"name": "Sweden",          "confederation": "UEFA",     "fifa_rank": 27, "is_host": 0, "appearances": 12},
        {"name": "Tunisia",         "confederation": "CAF",      "fifa_rank": 41, "is_host": 0, "appearances": 6},
    ],
    "G": [
        {"name": "Belgium",         "confederation": "UEFA",     "fifa_rank": 8,  "is_host": 0, "appearances": 14},
        {"name": "Egypt",           "confederation": "CAF",      "fifa_rank": 33, "is_host": 0, "appearances": 4},
        {"name": "IR Iran",         "confederation": "AFC",      "fifa_rank": 22, "is_host": 0, "appearances": 7},
        {"name": "New Zealand",     "confederation": "OFC",      "fifa_rank": 86, "is_host": 0, "appearances": 3},
    ],
    "H": [
        {"name": "Spain",           "confederation": "UEFA",     "fifa_rank": 3,  "is_host": 0, "appearances": 17},
        {"name": "Cabo Verde",      "confederation": "CAF",      "fifa_rank": 73, "is_host": 0, "appearances": 1},
        {"name": "Saudi Arabia",    "confederation": "AFC",      "fifa_rank": 49, "is_host": 0, "appearances": 7},
        {"name": "Uruguay",         "confederation": "CONMEBOL", "fifa_rank": 14, "is_host": 0, "appearances": 14},
    ],
    "I": [
        {"name": "France",          "confederation": "UEFA",     "fifa_rank": 4,  "is_host": 0, "appearances": 17},
        {"name": "Senegal",         "confederation": "CAF",      "fifa_rank": 17, "is_host": 0, "appearances": 4},
        {"name": "Iraq",            "confederation": "AFC",      "fifa_rank": 55, "is_host": 0, "appearances": 5},
        {"name": "Norway",          "confederation": "UEFA",     "fifa_rank": 25, "is_host": 0, "appearances": 4},
    ],
    "J": [
        {"name": "Argentina",       "confederation": "CONMEBOL", "fifa_rank": 1,  "is_host": 0, "appearances": 19, "is_defending_champion": 1},
        {"name": "Algeria",         "confederation": "CAF",      "fifa_rank": 37, "is_host": 0, "appearances": 5},
        {"name": "Austria",         "confederation": "UEFA",     "fifa_rank": 31, "is_host": 0, "appearances": 8},
        {"name": "Jordan",          "confederation": "AFC",      "fifa_rank": 62, "is_host": 0, "appearances": 1},
    ],
    "K": [
        {"name": "Portugal",        "confederation": "UEFA",     "fifa_rank": 6,  "is_host": 0, "appearances": 9},
        {"name": "DR Congo",        "confederation": "CAF",      "fifa_rank": 53, "is_host": 0, "appearances": 4},
        {"name": "Uzbekistan",      "confederation": "AFC",      "fifa_rank": 50, "is_host": 0, "appearances": 1},
        {"name": "Colombia",        "confederation": "CONMEBOL", "fifa_rank": 13, "is_host": 0, "appearances": 7},
    ],
    "L": [
        {"name": "England",         "confederation": "UEFA",     "fifa_rank": 2,  "is_host": 0, "appearances": 17},
        {"name": "Croatia",         "confederation": "UEFA",     "fifa_rank": 10, "is_host": 0, "appearances": 7},
        {"name": "Ghana",           "confederation": "CAF",      "fifa_rank": 64, "is_host": 0, "appearances": 4},
        {"name": "Panama",          "confederation": "CONCACAF", "fifa_rank": 69, "is_host": 0, "appearances": 2},
    ],
}

# 16 host venues across USA / Canada / Mexico
VENUES: dict[str, str] = {
    "Estadio Azteca":         "Mexico City, MEX",
    "Estadio Guadalajara":    "Guadalajara, MEX",
    "Estadio Monterrey":      "Monterrey, MEX",
    "Toronto Stadium":        "Toronto, CAN",
    "BC Place":               "Vancouver, CAN",
    "BMO Field":              "Toronto, CAN",
    "San Francisco Bay Area Stadium": "Santa Clara, USA",
    "SoFi Stadium":           "Los Angeles, USA",
    "LA Stadium":             "Los Angeles, USA",
    "MetLife Stadium":        "East Rutherford, USA",
    "New York New Jersey Stadium": "East Rutherford, USA",
    "AT&T Stadium":           "Arlington, USA",
    "NRG Stadium":            "Houston, USA",
    "Lincoln Financial Field": "Philadelphia, USA",
    "Hard Rock Stadium":      "Miami, USA",
    "Mercedes-Benz Stadium":  "Atlanta, USA",
    "Boston Stadium":         "Foxborough, USA",
    "Arrowhead Stadium":      "Kansas City, USA",
    "Lumen Field":            "Seattle, USA",
    "Levi's Stadium":         "Santa Clara, USA",
}

# === MATCHES: M001 - M104 ===
# Real schedule (group stage 6-11 to 6-26, R32 6-28 to 7-2, R16 7-4 to 7-7,
# QF 7-9 to 7-11, SF 7-14/15, 3rd 7-18, Final 7-19)
# Already-played results embedded per v3 plan (state at 2026-06-14 03:42 CST).
MATCHES: list[dict] = [
    # Group A — Matchday 1 (6-11)
    {"id": "M001", "round": "Group A Matchday 1", "matchday": 1, "group": "A", "date": "2026-06-11", "time": "19:00", "home": "Mexico",        "away": "South Africa",  "venue": "Estadio Azteca",        "status": "finished", "home_score": 2, "away_score": 0, "goals": [{"team": "Mexico", "minute": 9, "scorer": "Quiñones"}, {"team": "Mexico", "minute": 67, "scorer": "Jiménez"}]},
    {"id": "M002", "round": "Group A Matchday 1", "matchday": 1, "group": "A", "date": "2026-06-12", "time": "02:00", "home": "South Korea",   "away": "Czechia",       "venue": "Estadio Guadalajara",   "status": "finished", "home_score": 2, "away_score": 1, "goals": [{"team": "South Korea", "minute": 24, "scorer": "Son"}, {"team": "Czechia", "minute": 51, "scorer": "Schick"}, {"team": "South Korea", "minute": 88, "scorer": "Hwang"}]},
    # Group B — Matchday 1 (6-12)
    {"id": "M003", "round": "Group B Matchday 1", "matchday": 1, "group": "B", "date": "2026-06-12", "time": "19:00", "home": "Canada",        "away": "Bosnia & Herzegovina", "venue": "Toronto Stadium",        "status": "finished", "home_score": 1, "away_score": 1, "goals": [{"team": "Bosnia & Herzegovina", "minute": 21, "scorer": "Lukić"}, {"team": "Canada", "minute": 78, "scorer": "Larin"}]},
    {"id": "M004", "round": "Group D Matchday 1", "matchday": 1, "group": "D", "date": "2026-06-13", "time": "01:00", "home": "USA",           "away": "Paraguay",      "venue": "LA Stadium",            "status": "finished", "home_score": 4, "away_score": 1, "goals": [{"team": "USA", "minute": 12, "scorer": "Balogun"}, {"team": "USA", "minute": 31, "scorer": "Pulisic"}, {"team": "Paraguay", "minute": 55, "scorer": "Alonso"}, {"team": "USA", "minute": 67, "scorer": "Balogun"}, {"team": "USA", "minute": 81, "scorer": "Reyna"}]},
    # Group C — Matchday 1 (6-13)
    {"id": "M005", "round": "Group B Matchday 1", "matchday": 1, "group": "B", "date": "2026-06-13", "time": "19:00", "home": "Qatar",         "away": "Switzerland",   "venue": "San Francisco Bay Area Stadium", "status": "finished", "home_score": 1, "away_score": 1, "goals": [{"team": "Switzerland", "minute": 28, "scorer": "Embolo"}, {"team": "Qatar", "minute": 90, "scorer": "Hussein"}]},
    {"id": "M006", "round": "Group C Matchday 1", "matchday": 1, "group": "C", "date": "2026-06-13", "time": "22:00", "home": "Brazil",        "away": "Morocco",       "venue": "New York New Jersey Stadium", "status": "finished", "home_score": 1, "away_score": 1, "goals": [{"team": "Brazil", "minute": 67, "scorer": "Vinícius Jr."}, {"team": "Morocco", "minute": 22, "scorer": "Sebaï"}]},
    {"id": "M007", "round": "Group C Matchday 1", "matchday": 1, "group": "C", "date": "2026-06-14", "time": "01:00", "home": "Haiti",         "away": "Scotland",      "venue": "Boston Stadium",        "status": "finished", "home_score": 0, "away_score": 1, "goals": [{"team": "Scotland", "minute": 50, "scorer": "McGinn"}]},
    # Group D — Matchday 1 (6-13) — Australia vs Türkiye
    {"id": "M008", "round": "Group D Matchday 1", "matchday": 1, "group": "D", "date": "2026-06-14", "time": "04:00", "home": "Australia",     "away": "Türkiye",       "venue": "Mercedes-Benz Stadium",  "status": "live", "home_score": 2, "away_score": 0, "goals": [{"team": "Australia", "minute": 23, "scorer": "Duke"}, {"team": "Australia", "minute": 78, "scorer": "Boyle"}]},
    # Group A Matchday 2 (6-15)
    {"id": "M009", "round": "Group A Matchday 2", "matchday": 2, "group": "A", "date": "2026-06-18", "time": "16:00", "home": "Czechia",       "away": "South Africa",  "venue": "Estadio Guadalajara",   "status": "scheduled"},
    {"id": "M010", "round": "Group A Matchday 2", "matchday": 2, "group": "A", "date": "2026-06-19", "time": "01:00", "home": "Mexico",        "away": "South Korea",   "venue": "Estadio Azteca",        "status": "scheduled"},
    # Group B Matchday 2 (6-16)
    {"id": "M011", "round": "Group B Matchday 2", "matchday": 2, "group": "B", "date": "2026-06-18", "time": "19:00", "home": "Switzerland",   "away": "Bosnia & Herzegovina", "venue": "Toronto Stadium",   "status": "scheduled"},
    {"id": "M012", "round": "Group B Matchday 2", "matchday": 2, "group": "B", "date": "2026-06-18", "time": "22:00", "home": "Qatar",         "away": "Canada",        "venue": "BC Place",              "status": "scheduled"},
    # Group C Matchday 2 (6-16/17)
    {"id": "M013", "round": "Group C Matchday 2", "matchday": 2, "group": "C", "date": "2026-06-19", "time": "22:00", "home": "Scotland",      "away": "Morocco",       "venue": "New York New Jersey Stadium", "status": "scheduled"},
    {"id": "M014", "round": "Group C Matchday 2", "matchday": 2, "group": "C", "date": "2026-06-20", "time": "00:30", "home": "Brazil",        "away": "Haiti",         "venue": "Boston Stadium",        "status": "scheduled"},
    # Group D Matchday 2 (6-17)
    {"id": "M015", "round": "Group D Matchday 2", "matchday": 2, "group": "D", "date": "2026-06-19", "time": "23:00", "home": "USA",           "away": "Australia",     "venue": "LA Stadium",            "status": "scheduled"},
    {"id": "M016", "round": "Group D Matchday 2", "matchday": 2, "group": "D", "date": "2026-06-19", "time": "23:00", "home": "Paraguay",      "away": "Türkiye",       "venue": "Mercedes-Benz Stadium",  "status": "scheduled"},
    # Group E — Matchday 1 (6-14)  ← TODAY
    {"id": "M017", "round": "Group E Matchday 1", "matchday": 1, "group": "E", "date": "2026-06-14", "time": "17:00", "home": "Germany",       "away": "Curaçao",       "venue": "NRG Stadium",           "status": "scheduled"},
    {"id": "M018", "round": "Group E Matchday 1", "matchday": 1, "group": "E", "date": "2026-06-14", "time": "23:00", "home": "Côte d'Ivoire", "away": "Ecuador",       "venue": "Lincoln Financial Field", "status": "scheduled"},
    # Group F — Matchday 1 (6-14/15)
    {"id": "M019", "round": "Group F Matchday 1", "matchday": 1, "group": "F", "date": "2026-06-14", "time": "20:00", "home": "Netherlands",   "away": "Japan",         "venue": "AT&T Stadium",          "status": "scheduled"},
    {"id": "M020", "round": "Group F Matchday 1", "matchday": 1, "group": "F", "date": "2026-06-15", "time": "02:00", "home": "Sweden",        "away": "Tunisia",       "venue": "Estadio Monterrey",     "status": "scheduled"},
    # Group G — Matchday 1 (6-15)
    {"id": "M021", "round": "Group G Matchday 1", "matchday": 1, "group": "G", "date": "2026-06-15", "time": "19:00", "home": "Belgium",       "away": "Egypt",         "venue": "AT&T Stadium",          "status": "scheduled"},
    {"id": "M022", "round": "Group G Matchday 1", "matchday": 1, "group": "G", "date": "2026-06-16", "time": "01:00", "home": "IR Iran",       "away": "New Zealand",   "venue": "SoFi Stadium",          "status": "scheduled"},
    # Group H — Matchday 1 (6-16)
    {"id": "M023", "round": "Group H Matchday 1", "matchday": 1, "group": "H", "date": "2026-06-15", "time": "16:00", "home": "Spain",         "away": "Cabo Verde",    "venue": "Hard Rock Stadium",     "status": "scheduled"},
    {"id": "M024", "round": "Group H Matchday 1", "matchday": 1, "group": "H", "date": "2026-06-15", "time": "22:00", "home": "Saudi Arabia",  "away": "Uruguay",       "venue": "Mercedes-Benz Stadium",  "status": "scheduled"},
    # Group I — Matchday 1 (6-17)
    {"id": "M025", "round": "Group I Matchday 1", "matchday": 1, "group": "I", "date": "2026-06-16", "time": "19:00", "home": "France",        "away": "Senegal",       "venue": "MetLife Stadium",       "status": "scheduled"},
    {"id": "M026", "round": "Group I Matchday 1", "matchday": 1, "group": "I", "date": "2026-06-16", "time": "22:00", "home": "Iraq",          "away": "Norway",        "venue": "Lumen Field",           "status": "scheduled"},
    # Group J — Matchday 1 (6-18)
    {"id": "M027", "round": "Group J Matchday 1", "matchday": 1, "group": "J", "date": "2026-06-17", "time": "01:00", "home": "Argentina",     "away": "Algeria",       "venue": "MetLife Stadium",       "status": "scheduled"},
    {"id": "M028", "round": "Group J Matchday 1", "matchday": 1, "group": "J", "date": "2026-06-17", "time": "04:00", "home": "Austria",       "away": "Jordan",        "venue": "Arrowhead Stadium",     "status": "scheduled"},
    # Group K — Matchday 1 (6-19)
    {"id": "M029", "round": "Group K Matchday 1", "matchday": 1, "group": "K", "date": "2026-06-17", "time": "17:00", "home": "Portugal",      "away": "DR Congo",      "venue": "Hard Rock Stadium",     "status": "scheduled"},
    {"id": "M030", "round": "Group K Matchday 1", "matchday": 1, "group": "K", "date": "2026-06-18", "time": "02:00", "home": "Uzbekistan",    "away": "Colombia",      "venue": "NRG Stadium",           "status": "scheduled"},
    # Group L — Matchday 1 (6-20)
    {"id": "M031", "round": "Group L Matchday 1", "matchday": 1, "group": "L", "date": "2026-06-17", "time": "20:00", "home": "England",       "away": "Croatia",       "venue": "Wembley (MetLife)",     "status": "scheduled"},
    {"id": "M032", "round": "Group L Matchday 1", "matchday": 1, "group": "L", "date": "2026-06-17", "time": "23:00", "home": "Ghana",         "away": "Panama",        "venue": "Lincoln Financial Field", "status": "scheduled"},
    # Matchday 2 (continuation 6-20 to 6-25)
    {"id": "M033", "round": "Group A Matchday 3", "matchday": 3, "group": "A", "date": "2026-06-25", "time": "01:00", "home": "Mexico",        "away": "Czechia",       "venue": "Estadio Azteca",        "status": "scheduled"},
    {"id": "M034", "round": "Group A Matchday 3", "matchday": 3, "group": "A", "date": "2026-06-25", "time": "01:00", "home": "South Africa",  "away": "South Korea",   "venue": "Estadio Monterrey",     "status": "scheduled"},
    {"id": "M035", "round": "Group B Matchday 3", "matchday": 3, "group": "B", "date": "2026-06-24", "time": "19:00", "home": "Canada",        "away": "Switzerland",   "venue": "BC Place",              "status": "scheduled"},
    {"id": "M036", "round": "Group B Matchday 3", "matchday": 3, "group": "B", "date": "2026-06-24", "time": "19:00", "home": "Bosnia & Herzegovina", "away": "Qatar",   "venue": "Toronto Stadium",        "status": "scheduled"},
    {"id": "M037", "round": "Group C Matchday 3", "matchday": 3, "group": "C", "date": "2026-06-24", "time": "22:00", "home": "Brazil",        "away": "Scotland",      "venue": "New York New Jersey Stadium", "status": "scheduled"},
    {"id": "M038", "round": "Group C Matchday 3", "matchday": 3, "group": "C", "date": "2026-06-24", "time": "22:00", "home": "Morocco",       "away": "Haiti",         "venue": "Boston Stadium",        "status": "scheduled"},
    {"id": "M039", "round": "Group D Matchday 3", "matchday": 3, "group": "D", "date": "2026-06-26", "time": "20:00", "home": "USA",           "away": "Türkiye",       "venue": "LA Stadium",            "status": "scheduled"},
    {"id": "M040", "round": "Group D Matchday 3", "matchday": 3, "group": "D", "date": "2026-06-26", "time": "20:00", "home": "Australia",     "away": "Paraguay",      "venue": "Mercedes-Benz Stadium",  "status": "scheduled"},
    {"id": "M041", "round": "Group E Matchday 2", "matchday": 2, "group": "E", "date": "2026-06-25", "time": "20:00", "home": "Curaçao",       "away": "Côte d'Ivoire", "venue": "NRG Stadium",           "status": "scheduled"},
    {"id": "M042", "round": "Group E Matchday 2", "matchday": 2, "group": "E", "date": "2026-06-25", "time": "20:00", "home": "Germany",       "away": "Ecuador",       "venue": "MetLife Stadium",       "status": "scheduled"},
    {"id": "M043", "round": "Group E Matchday 3", "matchday": 3, "group": "E", "date": "2026-06-21", "time": "00:00", "home": "Ecuador",       "away": "Curaçao",       "venue": "Arrowhead Stadium",     "status": "scheduled"},
    {"id": "M044", "round": "Group E Matchday 3", "matchday": 3, "group": "E", "date": "2026-06-20", "time": "20:00", "home": "Côte d'Ivoire", "away": "Germany",       "venue": "Mercedes-Benz Stadium",  "status": "scheduled"},
    {"id": "M045", "round": "Group F Matchday 2", "matchday": 2, "group": "F", "date": "2026-06-21", "time": "04:00", "home": "Japan",         "away": "Tunisia",       "venue": "Hard Rock Stadium",     "status": "scheduled"},
    {"id": "M046", "round": "Group F Matchday 2", "matchday": 2, "group": "F", "date": "2026-06-20", "time": "17:00", "home": "Netherlands",   "away": "Sweden",        "venue": "AT&T Stadium",          "status": "scheduled"},
    {"id": "M047", "round": "Group F Matchday 3", "matchday": 3, "group": "F", "date": "2026-06-25", "time": "23:00", "home": "Tunisia",       "away": "Netherlands",   "venue": "NRG Stadium",           "status": "scheduled"},
    {"id": "M048", "round": "Group F Matchday 3", "matchday": 3, "group": "F", "date": "2026-06-25", "time": "23:00", "home": "Japan",         "away": "Sweden",        "venue": "Lumen Field",           "status": "scheduled"},
    {"id": "M049", "round": "Group G Matchday 2", "matchday": 2, "group": "G", "date": "2026-06-22", "time": "01:00", "home": "Egypt",         "away": "New Zealand",   "venue": "SoFi Stadium",          "status": "scheduled"},
    {"id": "M050", "round": "Group G Matchday 2", "matchday": 2, "group": "G", "date": "2026-06-21", "time": "19:00", "home": "Belgium",       "away": "IR Iran",       "venue": "AT&T Stadium",          "status": "scheduled"},
    {"id": "M051", "round": "Group G Matchday 3", "matchday": 3, "group": "G", "date": "2026-06-27", "time": "03:00", "home": "New Zealand",   "away": "Belgium",       "venue": "Mercedes-Benz Stadium",  "status": "scheduled"},
    {"id": "M052", "round": "Group G Matchday 3", "matchday": 3, "group": "G", "date": "2026-06-27", "time": "03:00", "home": "IR Iran",       "away": "Egypt",         "venue": "MetLife Stadium",       "status": "scheduled"},
    {"id": "M053", "round": "Group H Matchday 2", "matchday": 2, "group": "H", "date": "2026-06-27", "time": "00:00", "home": "Cabo Verde",    "away": "Saudi Arabia",  "venue": "Hard Rock Stadium",     "status": "scheduled"},
    {"id": "M054", "round": "Group H Matchday 2", "matchday": 2, "group": "H", "date": "2026-06-27", "time": "00:00", "home": "Spain",         "away": "Uruguay",       "venue": "Estadio Azteca",        "status": "scheduled"},
    {"id": "M055", "round": "Group H Matchday 3", "matchday": 3, "group": "H", "date": "2026-06-21", "time": "22:00", "home": "Uruguay",       "away": "Cabo Verde",    "venue": "Arrowhead Stadium",     "status": "scheduled"},
    {"id": "M056", "round": "Group H Matchday 3", "matchday": 3, "group": "H", "date": "2026-06-21", "time": "16:00", "home": "Saudi Arabia",  "away": "Spain",         "venue": "NRG Stadium",           "status": "scheduled"},
    {"id": "M057", "round": "Group I Matchday 2", "matchday": 2, "group": "I", "date": "2026-06-26", "time": "19:00", "home": "Senegal",       "away": "Iraq",          "venue": "Lumen Field",           "status": "scheduled"},
    {"id": "M058", "round": "Group I Matchday 2", "matchday": 2, "group": "I", "date": "2026-06-26", "time": "19:00", "home": "France",        "away": "Norway",        "venue": "MetLife Stadium",       "status": "scheduled"},
    {"id": "M059", "round": "Group I Matchday 3", "matchday": 3, "group": "I", "date": "2026-06-23", "time": "00:00", "home": "Norway",        "away": "Senegal",       "venue": "Lincoln Financial Field", "status": "scheduled"},
    {"id": "M060", "round": "Group I Matchday 3", "matchday": 3, "group": "I", "date": "2026-06-22", "time": "21:00", "home": "Iraq",          "away": "France",        "venue": "BC Place",              "status": "scheduled"},
    {"id": "M061", "round": "Group J Matchday 2", "matchday": 2, "group": "J", "date": "2026-06-23", "time": "03:00", "home": "Algeria",       "away": "Jordan",        "venue": "Mercedes-Benz Stadium",  "status": "scheduled"},
    {"id": "M062", "round": "Group J Matchday 2", "matchday": 2, "group": "J", "date": "2026-06-22", "time": "17:00", "home": "Argentina",     "away": "Austria",       "venue": "MetLife Stadium",       "status": "scheduled"},
    {"id": "M063", "round": "Group J Matchday 3", "matchday": 3, "group": "J", "date": "2026-06-28", "time": "02:00", "home": "Austria",       "away": "Algeria",       "venue": "AT&T Stadium",          "status": "scheduled"},
    {"id": "M064", "round": "Group J Matchday 3", "matchday": 3, "group": "J", "date": "2026-06-28", "time": "02:00", "home": "Jordan",        "away": "Argentina",     "venue": "Hard Rock Stadium",     "status": "scheduled"},
    {"id": "M065", "round": "Group K Matchday 2", "matchday": 2, "group": "K", "date": "2026-06-27", "time": "23:30", "home": "DR Congo",      "away": "Uzbekistan",    "venue": "NRG Stadium",           "status": "scheduled"},
    {"id": "M066", "round": "Group K Matchday 2", "matchday": 2, "group": "K", "date": "2026-06-27", "time": "23:30", "home": "Portugal",      "away": "Colombia",      "venue": "MetLife Stadium",       "status": "scheduled"},
    {"id": "M067", "round": "Group K Matchday 3", "matchday": 3, "group": "K", "date": "2026-06-24", "time": "02:00", "home": "Colombia",      "away": "DR Congo",      "venue": "Hard Rock Stadium",     "status": "scheduled"},
    {"id": "M068", "round": "Group K Matchday 3", "matchday": 3, "group": "K", "date": "2026-06-23", "time": "17:00", "home": "Uzbekistan",    "away": "Portugal",      "venue": "Arrowhead Stadium",     "status": "scheduled"},
    {"id": "M069", "round": "Group L Matchday 2", "matchday": 2, "group": "L", "date": "2026-06-27", "time": "21:00", "home": "Croatia",       "away": "Ghana",         "venue": "Lincoln Financial Field", "status": "scheduled"},
    {"id": "M070", "round": "Group L Matchday 2", "matchday": 2, "group": "L", "date": "2026-06-27", "time": "21:00", "home": "England",       "away": "Panama",        "venue": "LA Stadium",            "status": "scheduled"},
    {"id": "M071", "round": "Group L Matchday 3", "matchday": 3, "group": "L", "date": "2026-06-23", "time": "23:00", "home": "Panama",        "away": "Croatia",       "venue": "BC Place",              "status": "scheduled"},
    {"id": "M072", "round": "Group L Matchday 3", "matchday": 3, "group": "L", "date": "2026-06-23", "time": "20:00", "home": "Ghana",         "away": "England",       "venue": "Mercedes-Benz Stadium",  "status": "scheduled"},
    # === 淘汰赛 Knockout Stage (M073-M104, 32 matches) ===
    {"id": "M073", "round": "Round of 32", "matchday": 5, "group": None, "date": "2026-06-28", "time": "03:00", "home": "2A", "away": "2B", "venue": "Toronto Stadium", "status": "scheduled", "round_position": 1},
    {"id": "M074", "round": "Round of 32", "matchday": 5, "group": None, "date": "2026-06-28", "time": "04:30", "home": "1E", "away": "3rd-ABCDF", "venue": "Boston Stadium", "status": "scheduled", "round_position": 2},
    {"id": "M075", "round": "Round of 32", "matchday": 5, "group": None, "date": "2026-06-29", "time": "13:00", "home": "1F", "away": "2C", "venue": "Estadio Monterrey", "status": "scheduled", "round_position": 3},
    {"id": "M076", "round": "Round of 32", "matchday": 5, "group": None, "date": "2026-06-29", "time": "18:00", "home": "1C", "away": "2F", "venue": "LA Stadium", "status": "scheduled", "round_position": 4},
    {"id": "M077", "round": "Round of 32", "matchday": 5, "group": None, "date": "2026-06-30", "time": "03:00", "home": "1I", "away": "2J", "venue": "MetLife Stadium", "status": "scheduled", "round_position": 5},
    {"id": "M078", "round": "Round of 32", "matchday": 5, "group": None, "date": "2026-06-30", "time": "13:00", "home": "1G", "away": "3rd-EFHIJ", "venue": "Lumen Field", "status": "scheduled", "round_position": 6},
    {"id": "M079", "round": "Round of 32", "matchday": 5, "group": None, "date": "2026-07-01", "time": "09:00", "home": "1H", "away": "2G", "venue": "Hard Rock Stadium", "status": "scheduled", "round_position": 7},
    {"id": "M080", "round": "Round of 32", "matchday": 5, "group": None, "date": "2026-07-01", "time": "12:00", "home": "1J", "away": "2I", "venue": "Mercedes-Benz Stadium", "status": "scheduled", "round_position": 8},
    {"id": "M081", "round": "Round of 32", "matchday": 5, "group": None, "date": "2026-07-01", "time": "07:00", "home": "1A", "away": "3rd-CDEFGH", "venue": "Estadio Azteca", "status": "scheduled", "round_position": 9},
    {"id": "M082", "round": "Round of 32", "matchday": 5, "group": None, "date": "2026-07-01", "time": "13:00", "home": "1L", "away": "3rd-EFGHIJ", "venue": "SoFi Stadium", "status": "scheduled", "round_position": 10},
    {"id": "M083", "round": "Round of 32", "matchday": 5, "group": None, "date": "2026-06-30", "time": "00:00", "home": "1D", "away": "3rd-ABCDF", "venue": "NRG Stadium", "status": "scheduled", "round_position": 11},
    {"id": "M084", "round": "Round of 32", "matchday": 5, "group": None, "date": "2026-07-02", "time": "18:00", "home": "1B", "away": "3rd-CDEFGH", "venue": "BC Place", "status": "scheduled", "round_position": 12},
    {"id": "M085", "round": "Round of 32", "matchday": 5, "group": None, "date": "2026-07-02", "time": "05:00", "home": "1K", "away": "2E", "venue": "Arrowhead Stadium", "status": "scheduled", "round_position": 13},
    {"id": "M086", "round": "Round of 32", "matchday": 5, "group": None, "date": "2026-07-02", "time": "06:00", "home": "2K", "away": "2H", "venue": "Lincoln Financial Field", "status": "scheduled", "round_position": 14},
    {"id": "M087", "round": "Round of 32", "matchday": 5, "group": None, "date": "2026-07-02", "time": "10:00", "home": "2D", "away": "2L", "venue": "Estadio Guadalajara", "status": "scheduled", "round_position": 15},
    {"id": "M088", "round": "Round of 32", "matchday": 5, "group": None, "date": "2026-07-03", "time": "11:00", "home": "2E (alt)", "away": "2I (alt)", "venue": "AT&T Stadium", "status": "scheduled", "round_position": 16},
    {"id": "M089", "round": "Round of 16", "matchday": 6, "group": None, "date": "2026-07-04", "time": "04:00", "home": "W73", "away": "W74", "venue": "MetLife Stadium", "status": "scheduled", "round_position": 1},
    {"id": "M090", "round": "Round of 16", "matchday": 6, "group": None, "date": "2026-07-04", "time": "11:30", "home": "W75", "away": "W76", "venue": "Estadio Monterrey", "status": "scheduled", "round_position": 2},
    {"id": "M091", "round": "Round of 16", "matchday": 6, "group": None, "date": "2026-07-05", "time": "10:00", "home": "W77", "away": "W78", "venue": "Lumen Field", "status": "scheduled", "round_position": 3},
    {"id": "M092", "round": "Round of 16", "matchday": 6, "group": None, "date": "2026-07-06", "time": "00:00", "home": "W79", "away": "W80", "venue": "Mercedes-Benz Stadium", "status": "scheduled", "round_position": 4},
    {"id": "M093", "round": "Round of 16", "matchday": 6, "group": None, "date": "2026-07-07", "time": "00:00", "home": "W81", "away": "W82", "venue": "LA Stadium", "status": "scheduled", "round_position": 5},
    {"id": "M094", "round": "Round of 16", "matchday": 6, "group": None, "date": "2026-07-06", "time": "19:00", "home": "W83", "away": "W84", "venue": "Hard Rock Stadium", "status": "scheduled", "round_position": 6},
    {"id": "M095", "round": "Round of 16", "matchday": 6, "group": None, "date": "2026-07-07", "time": "06:00", "home": "W85", "away": "W86", "venue": "NRG Stadium", "status": "scheduled", "round_position": 7},
    {"id": "M096", "round": "Round of 16", "matchday": 6, "group": None, "date": "2026-07-07", "time": "07:30", "home": "W87", "away": "W88", "venue": "Boston Stadium", "status": "scheduled", "round_position": 8},
    {"id": "M097", "round": "Quarter-finals", "matchday": 7, "group": None, "date": "2026-07-09", "time": "20:00", "home": "W89", "away": "W90", "venue": "Boston Stadium", "status": "scheduled", "round_position": 1},
    {"id": "M098", "round": "Quarter-finals", "matchday": 7, "group": None, "date": "2026-07-11", "time": "21:00", "home": "W91", "away": "W92", "venue": "LA Stadium", "status": "scheduled", "round_position": 2},
    {"id": "M099", "round": "Quarter-finals", "matchday": 7, "group": None, "date": "2026-07-10", "time": "19:00", "home": "W93", "away": "W94", "venue": "Hard Rock Stadium", "status": "scheduled", "round_position": 3},
    {"id": "M100", "round": "Quarter-finals", "matchday": 7, "group": None, "date": "2026-07-12", "time": "01:00", "home": "W95", "away": "W96", "venue": "Arrowhead Stadium", "status": "scheduled", "round_position": 4},
    {"id": "M101", "round": "Semi-finals", "matchday": 8, "group": None, "date": "2026-07-14", "time": "19:00", "home": "W97", "away": "W98", "venue": "AT&T Stadium", "status": "scheduled", "round_position": 1},
    {"id": "M102", "round": "Semi-finals", "matchday": 8, "group": None, "date": "2026-07-15", "time": "19:00", "home": "W99", "away": "W100", "venue": "Mercedes-Benz Stadium", "status": "scheduled", "round_position": 2},
    {"id": "M103", "round": "Third place", "matchday": 9, "group": None, "date": "2026-07-18", "time": "21:00", "home": "L101", "away": "L102", "venue": "Hard Rock Stadium", "status": "scheduled", "round_position": 1},
    {"id": "M104", "round": "Final", "matchday": 9, "group": None, "date": "2026-07-19", "time": "19:00", "home": "W101", "away": "W102", "venue": "New York New Jersey Stadium", "status": "scheduled", "round_position": 1},

]

# 22 FIFA World Cup history (1930–2022)
HISTORY: list[dict] = [
    {"year": 1930, "host": "Uruguay",       "champion": "Uruguay",     "runner_up": "Argentina",     "third": "USA",            "fourth": "Yugoslavia",      "matches": 18, "goals": 70,  "teams": 13},
    {"year": 1934, "host": "Italy",         "champion": "Italy",       "runner_up": "Czechoslovakia","third": "Germany",        "fourth": "Austria",          "matches": 17, "goals": 70,  "teams": 16},
    {"year": 1938, "host": "France",        "champion": "Italy",       "runner_up": "Hungary",       "third": "Brazil",         "fourth": "Sweden",           "matches": 18, "goals": 84,  "teams": 15},
    {"year": 1950, "host": "Brazil",        "champion": "Uruguay",     "runner_up": "Brazil",        "third": "Sweden",         "fourth": "Spain",            "matches": 22, "goals": 88,  "teams": 13},
    {"year": 1954, "host": "Switzerland",   "champion": "Germany",     "runner_up": "Hungary",       "third": "Austria",        "fourth": "Uruguay",          "matches": 26, "goals": 140, "teams": 16},
    {"year": 1958, "host": "Sweden",        "champion": "Brazil",      "runner_up": "Sweden",        "third": "France",         "fourth": "Germany",          "matches": 35, "goals": 126, "teams": 16},
    {"year": 1962, "host": "Chile",         "champion": "Brazil",      "runner_up": "Czechoslovakia","third": "Chile",          "fourth": "Yugoslavia",       "matches": 32, "goals": 89,  "teams": 16},
    {"year": 1966, "host": "England",       "champion": "England",     "runner_up": "Germany",       "third": "Portugal",       "fourth": "Soviet Union",     "matches": 32, "goals": 89,  "teams": 16},
    {"year": 1970, "host": "Mexico",        "champion": "Brazil",      "runner_up": "Italy",         "third": "Germany",        "fourth": "Uruguay",          "matches": 32, "goals": 95,  "teams": 16},
    {"year": 1974, "host": "West Germany",  "champion": "West Germany","runner_up": "Netherlands",  "third": "Poland",         "fourth": "Brazil",           "matches": 38, "goals": 97,  "teams": 16},
    {"year": 1978, "host": "Argentina",     "champion": "Argentina",   "runner_up": "Netherlands",  "third": "Brazil",         "fourth": "Italy",            "matches": 38, "goals": 102, "teams": 16},
    {"year": 1982, "host": "Spain",         "champion": "Italy",       "runner_up": "Germany",       "third": "Poland",         "fourth": "France",           "matches": 52, "goals": 146, "teams": 24},
    {"year": 1986, "host": "Mexico",        "champion": "Argentina",   "runner_up": "Germany",       "third": "France",         "fourth": "Belgium",          "matches": 52, "goals": 132, "teams": 24},
    {"year": 1990, "host": "Italy",         "champion": "Germany",     "runner_up": "Argentina",     "third": "Italy",          "fourth": "England",          "matches": 52, "goals": 115, "teams": 24},
    {"year": 1994, "host": "USA",           "champion": "Brazil",      "runner_up": "Italy",         "third": "Sweden",         "fourth": "Bulgaria",         "matches": 52, "goals": 141, "teams": 24},
    {"year": 1998, "host": "France",        "champion": "France",      "runner_up": "Brazil",        "third": "Croatia",        "fourth": "Netherlands",      "matches": 64, "goals": 171, "teams": 32},
    {"year": 2002, "host": "South Korea/Japan", "champion": "Brazil",   "runner_up": "Germany",       "third": "Türkiye",        "fourth": "South Korea",      "matches": 64, "goals": 161, "teams": 32},
    {"year": 2006, "host": "Germany",       "champion": "Italy",       "runner_up": "France",        "third": "Germany",        "fourth": "Portugal",         "matches": 64, "goals": 147, "teams": 32},
    {"year": 2010, "host": "South Africa",  "champion": "Spain",       "runner_up": "Netherlands",  "third": "Germany",        "fourth": "Uruguay",          "matches": 64, "goals": 145, "teams": 32},
    {"year": 2014, "host": "Brazil",        "champion": "Germany",     "runner_up": "Argentina",     "third": "Netherlands",   "fourth": "Brazil",           "matches": 64, "goals": 171, "teams": 32},
    {"year": 2018, "host": "Russia",        "champion": "France",      "runner_up": "Croatia",       "third": "Belgium",        "fourth": "England",          "matches": 64, "goals": 169, "teams": 32},
    {"year": 2022, "host": "Qatar",         "champion": "Argentina",   "runner_up": "France",        "third": "Croatia",        "fourth": "Morocco",          "matches": 64, "goals": 172, "teams": 32},
]

# Champions count for visualization
CHAMPION_COUNTS: dict[str, int] = {}
for h in HISTORY:
    CHAMPION_COUNTS[h["champion"]] = CHAMPION_COUNTS.get(h["champion"], 0) + 1
