"""Seed SQLite with real World Cup 2026 data.

Idempotent: drops + recreates tables on each run.
Data source: data/tournament_data.py (real FIFA 2025-12-05 draw + 2026-06-14 state).
"""
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from data.tournament_data import GROUPS, MATCHES, HISTORY, VENUES

DB_PATH = Path("data/wc2026.db")
SCHEMA = """
DROP TABLE IF EXISTS matches;
DROP TABLE IF EXISTS teams;
DROP TABLE IF EXISTS standings;
DROP TABLE IF EXISTS bracket;
DROP TABLE IF EXISTS world_cup_history;
DROP TABLE IF EXISTS predictions;
DROP TABLE IF EXISTS match_predictions;
DROP TABLE IF EXISTS venues;

CREATE TABLE matches (
    match_id   TEXT PRIMARY KEY,
    round      TEXT,
    matchday   INTEGER,
    group_name TEXT,
    match_date TEXT,
    match_time TEXT,
    home_team  TEXT,
    away_team  TEXT,
    venue      TEXT,
    home_score INTEGER,
    away_score INTEGER,
    status     TEXT,
    goals_json TEXT,
    last_updated TEXT,
    -- Per-match AI predictions (added in v4 — knockout + bracket feature)
    predicted_winner      TEXT,
    predicted_home_score  INTEGER,
    predicted_away_score  INTEGER,
    home_win_prob         REAL,
    draw_prob             REAL,
    away_win_prob         REAL,
    score_distribution_json TEXT
);

CREATE TABLE teams (
    name          TEXT PRIMARY KEY,
    group_name    TEXT,
    confederation TEXT,
    fifa_rank     INTEGER,
    is_host       INTEGER DEFAULT 0,
    is_defending_champion INTEGER DEFAULT 0,
    appearances   INTEGER DEFAULT 0
);

CREATE TABLE standings (
    group_name TEXT,
    team       TEXT,
    played     INTEGER DEFAULT 0,
    won        INTEGER DEFAULT 0,
    draw       INTEGER DEFAULT 0,
    lost       INTEGER DEFAULT 0,
    gf         INTEGER DEFAULT 0,
    ga         INTEGER DEFAULT 0,
    gd         INTEGER DEFAULT 0,
    pts        INTEGER DEFAULT 0,
    fair_play  INTEGER DEFAULT 0,
    PRIMARY KEY (group_name, team)
);
-- NOTE: This table is seeded with 0-rows initially. It is recomputed on every
-- /api/standings request (see app.py:standings) AND every time
-- scrapers/openfootball_live.py runs compute_standings(). It is kept here
-- only for ad-hoc SQL inspection and tool compatibility; the canonical
-- standings data comes from the dynamic endpoint.

CREATE TABLE bracket (
    match_id  TEXT PRIMARY KEY,
    round     TEXT,
    match_date TEXT,
    team1     TEXT,
    team2     TEXT,
    winner    TEXT,
    venue     TEXT
);

CREATE TABLE world_cup_history (
    year          INTEGER PRIMARY KEY,
    host          TEXT,
    champion      TEXT,
    runner_up     TEXT,
    third         TEXT,
    fourth        TEXT,
    matches_played INTEGER,
    goals_scored   INTEGER,
    teams          INTEGER
);

CREATE TABLE predictions (
    team          TEXT PRIMARY KEY,
    champion_prob REAL,
    sf_prob       REAL,
    qf_prob       REAL,
    r16_prob      REAL,
    r32_prob      REAL,
    updated_at    TEXT
);

-- Per-match prediction details (knockout matches primarily, but also group).
-- One row per match with: win/draw/lose probabilities, most likely score,
-- full score distribution (JSON), and predicted winner (NULL for unfinished
-- group matches with draws).
CREATE TABLE match_predictions (
    match_id        TEXT PRIMARY KEY,
    home_team       TEXT,
    away_team       TEXT,
    home_win_prob   REAL,
    draw_prob       REAL,
    away_win_prob   REAL,
    predicted_score TEXT,
    predicted_winner TEXT,
    score_distribution_json TEXT,
    updated_at      TEXT,
    FOREIGN KEY(match_id) REFERENCES matches(match_id)
);

CREATE TABLE venues (
    name    TEXT PRIMARY KEY,
    city    TEXT,
    country TEXT
);
"""


def compute_standings(db: sqlite3.Connection) -> None:
    """Aggregate group standings from finished matches."""
    cur = db.execute("DELETE FROM standings")
    # Get all finished group matches
    rows = db.execute("""
        SELECT group_name, home_team, away_team, home_score, away_score
        FROM matches
        WHERE status = 'finished' AND group_name IS NOT NULL
    """).fetchall()
    for g, h, a, hs, as_ in rows:
        if hs is None or as_ is None:
            continue
        for team, gf, ga in ((h, hs, as_), (a, as_, hs)):
            won = 1 if gf > ga else 0
            draw = 1 if gf == ga else 0
            lost = 1 if gf < ga else 0
            pts = won * 3 + draw
            db.execute("""
                INSERT INTO standings (group_name, team, played, won, draw, lost, gf, ga, gd, pts)
                VALUES (?, ?, 1, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(group_name, team) DO UPDATE SET
                    played = played + 1,
                    won    = won    + excluded.won,
                    draw   = draw   + excluded.draw,
                    lost   = lost   + excluded.lost,
                    gf     = gf     + excluded.gf,
                    ga     = ga     + excluded.ga,
                    gd     = gd     + (excluded.gf - excluded.ga),
                    pts    = pts    + excluded.pts
            """, (g, team, won, draw, lost, gf, ga, gf - ga, pts))
    db.commit()


def main() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB_PATH)
    db.executescript(SCHEMA)

    # Teams
    for group, teams in GROUPS.items():
        for t in teams:
            db.execute("""
                INSERT INTO teams (name, group_name, confederation, fifa_rank, is_host, is_defending_champion, appearances)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (t["name"], group, t["confederation"], t["fifa_rank"],
                  t.get("is_host", 0), t.get("is_defending_champion", 0), t.get("appearances", 0)))

    # Venues
    for name, city_country in VENUES.items():
        parts = city_country.rsplit(", ", 1)
        city, country = (parts[0], parts[1]) if len(parts) == 2 else (city_country, "")
        db.execute("INSERT INTO venues (name, city, country) VALUES (?, ?, ?)",
                   (name, city, country))

    # Matches
    now = datetime.now(timezone.utc).isoformat()
    for m in MATCHES:
        db.execute("""
            INSERT INTO matches
                (match_id, round, matchday, group_name, match_date, match_time,
                 home_team, away_team, venue, home_score, away_score, status, goals_json, last_updated,
                 predicted_winner, predicted_home_score, predicted_away_score,
                 home_win_prob, draw_prob, away_win_prob, score_distribution_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (m["id"], m["round"], m.get("matchday"), m.get("group"),
              m["date"], m["time"], m["home"], m["away"], m["venue"],
              m.get("home_score"), m.get("away_score"), m.get("status", "scheduled"),
              json.dumps(m.get("goals", [])), now,
              # Predictions start as NULL — populated by analyzer.py
              None, None, None, None, None, None, None))

    # History
    for h in HISTORY:
        db.execute("""
            INSERT INTO world_cup_history
                (year, host, champion, runner_up, third, fourth, matches_played, goals_scored, teams)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (h["year"], h["host"], h["champion"], h["runner_up"], h["third"], h["fourth"],
              h["matches"], h["goals"], h["teams"]))

    db.commit()
    compute_standings(db)
    db.close()

    # Summary
    db = sqlite3.connect(DB_PATH)
    print(f"✅ Seeded {DB_PATH}")
    print(f"   matches: {db.execute('SELECT COUNT(*) FROM matches').fetchone()[0]}")
    print(f"   teams:   {db.execute('SELECT COUNT(*) FROM teams').fetchone()[0]}")
    print(f"   venues:  {db.execute('SELECT COUNT(*) FROM venues').fetchone()[0]}")
    print(f"   history: {db.execute('SELECT COUNT(*) FROM world_cup_history').fetchone()[0]}")
    print(f"   standings rows: {db.execute('SELECT COUNT(*) FROM standings').fetchone()[0]}")
    finished = db.execute("SELECT COUNT(*) FROM matches WHERE status='finished'").fetchone()[0]
    print(f"   finished matches: {finished}")
    ko = db.execute("SELECT COUNT(*) FROM matches WHERE group_name IS NULL").fetchone()[0]
    print(f"   knockout matches: {ko}")
    db.close()


if __name__ == "__main__":
    main()
