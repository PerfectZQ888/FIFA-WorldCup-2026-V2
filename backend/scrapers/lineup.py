"""Match lineup (roster) scraper — pulls starting XI, subs, coach from ESPN.

Source: ESPN summary API (free, no auth)
  https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/summary?event=<ESPN_EVENT_ID>
  
Returns `rosters[]` array (one per team) with:
  - team.displayName, team.id
  - formation (e.g. '4-3-3')
  - coach.name (sometimes null)
  - roster[]: [{jersey, athlete.{id, fullName, displayName, position}, starter, formationPlace,
                subbedIn (min), subbedOut (min)}, ...]

CCTV doesn't expose lineup via JSON (HTML-only). ESPN is the canonical lineup source
for free, multi-language teams (player names from ESPN are English, mapped via
external_ids table).

Refresh strategy:
  - Pre-match (kickoff - 2h  ~  kickoff - 10min): every 5 min
  - In-match (live): every 3 min (substitutions update)
  - Post-match (finished): once, then stop (lineups are frozen)

Usage:
  from scrapers.lineup import fetch_and_store_lineups
  stats = fetch_and_store_lineups()  # auto-detect which matches to refresh
"""
from __future__ import annotations
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

DB_PATH = Path("data/wc2026.db")
ESPN_BASE = "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
TIMEOUT = 15.0


def fetch_espn_summary(espn_event_id: str) -> dict | None:
    """Fetch ESPN summary JSON for a match. Returns dict or None on failure."""
    url = f"{ESPN_BASE}/summary?event={espn_event_id}"
    try:
        r = httpx.get(url, timeout=TIMEOUT, headers={"User-Agent": UA})
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"[lineup] ESPN summary fetch failed for {espn_event_id}: {e}")
        return None


def _parse_player(entry: dict) -> dict:
    """Normalize one ESPN roster entry to our DB shape."""
    athlete = entry.get("athlete", {}) or {}
    # ESPN v3: position 在 entry.position (不是 athlete.position)
    pos = entry.get("position") or athlete.get("position") or {}
    return {
        "athlete_id": str(athlete.get("id", "")),
        "jersey": entry.get("jersey", ""),
        "name": athlete.get("fullName") or athlete.get("displayName") or athlete.get("shortName") or "",
        "short_name": athlete.get("shortName") or "",
        "position": pos.get("abbreviation") or pos.get("name") or "",
        "position_full": pos.get("displayName") or pos.get("name") or "",
        "starter": bool(entry.get("starter")),
        "formation_place": entry.get("formationPlace"),
        "subbed_in_min": entry.get("subbedIn"),
        "subbed_out_min": entry.get("subbedOut"),
        "active": bool(entry.get("active", True)),
    }


def _parse_roster(roster: dict) -> dict | None:
    """Parse one ESPN rosters[]. Returns {team_id, team_name, formation, coach, players[]}.
    Returns None if no team info (skips empty rosters like pre-kickoff)."""
    team = roster.get("team", {}) or {}
    team_id = str(team.get("id", ""))
    team_name = team.get("displayName") or team.get("name") or ""
    if not team_name:
        return None
    coach = roster.get("coach") or {}
    return {
        "team_id": team_id,
        "team_name": team_name,
        "formation": roster.get("formation"),
        "coach": coach.get("name") if coach else None,
        "players": [_parse_player(e) for e in roster.get("roster", []) if e.get("athlete")],
    }


def _match_team_to_side(team_name: str, match_row: tuple) -> str:
    """Determine if a team is 'home' or 'away' for a given DB match.
    match_row: (match_id, home_team, away_team). Uses en_alias_to_canonical.
    """
    from team_name_map import en_alias_to_canonical
    if not team_name or len(match_row) < 3:
        return "home"
    canonical = en_alias_to_canonical(team_name)
    _, home_team, away_team = match_row
    if canonical == en_alias_to_canonical(home_team):
        return "home"
    if canonical == en_alias_to_canonical(away_team):
        return "away"
    return "home"  # fallback


def store_lineup(conn: sqlite3.Connection, match_id: str, side: str, parsed: dict) -> bool:
    """Write a parsed roster to lineups table. Returns True if row was inserted/updated."""
    now = datetime.now(timezone.utc).isoformat()
    players_json = json.dumps(parsed["players"], ensure_ascii=False)
    try:
        conn.execute("""
            INSERT INTO lineups (match_id, side, formation, coach_name, players_json, source, fetched_at)
            VALUES (?, ?, ?, ?, ?, 'espn', ?)
            ON CONFLICT(match_id, side) DO UPDATE SET
                formation = excluded.formation,
                coach_name = excluded.coach_name,
                players_json = excluded.players_json,
                source = excluded.source,
                fetched_at = excluded.fetched_at
        """, (match_id, side, parsed["formation"], parsed["coach"], players_json, now))
        conn.commit()
        return True
    except Exception as e:
        print(f"[lineup] store failed for {match_id} {side}: {e}")
        return False


def fetch_and_store_one(conn: sqlite3.Connection, match_id: str, espn_event_id: str) -> dict:
    """Fetch + store lineup for a single match. Returns stats {fetched, stored, error}."""
    if not espn_event_id:
        return {"fetched": False, "stored": 0, "error": "no espn_event_id"}
    summary = fetch_espn_summary(espn_event_id)
    if not summary:
        return {"fetched": False, "stored": 0, "error": "fetch failed"}
    rosters = summary.get("rosters") or []
    if not rosters:
        return {"fetched": True, "stored": 0, "error": None, "rosters_empty": True}

    # 拿 DB match 的 home/away 用于判定 side
    row = conn.execute(
        "SELECT match_id, home_team, away_team FROM matches WHERE match_id=?",
        (match_id,),
    ).fetchone()
    if not row:
        return {"fetched": True, "stored": 0, "error": "match not in DB"}

    stored = 0
    for r in rosters:
        parsed = _parse_roster(r)
        if not parsed:
            continue
        side = _match_team_to_side(parsed["team_name"], row)
        if store_lineup(conn, match_id, side, parsed):
            stored += 1

    # 记录同步时间
    conn.execute(
        "UPDATE external_ids SET espn_synced_at=? WHERE match_id=?",
        (datetime.now(timezone.utc).isoformat(), match_id),
    )
    conn.commit()
    return {"fetched": True, "stored": stored, "error": None}


def candidates_to_refresh(conn: sqlite3.Connection) -> list[tuple[str, str]]:
    """Return list of (match_id, espn_event_id) to refresh.

    Strategy:
      - Pre-match: kickoff in 2h ~ 10min, refresh every 5 min
      - Live: status='live', refresh every 3 min
      - Post-match: status='finished', lineups frozen — refresh only if not yet stored
    """
    now = datetime.now(timezone.utc)
    cur = conn.execute("""
        SELECT m.match_id, e.espn_event_id, m.status, m.match_date, m.match_time
        FROM matches m
        JOIN external_ids e ON e.match_id = m.match_id
        WHERE e.espn_event_id IS NOT NULL
    """)
    out = []
    for match_id, espn_eid, status, mdate, mtime in cur.fetchall():
        if not mdate or not mtime:
            continue
        try:
            kickoff = datetime.fromisoformat(f"{mdate}T{mtime}:00").replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        delta_min = (kickoff - now).total_seconds() / 60
        should_refresh = False
        if status == "live":
            should_refresh = True  # always refresh live games (substitutions)
        elif status == "finished":
            # 完赛只刷一次 (lineup 表里没数据时)
            have = conn.execute("SELECT 1 FROM lineups WHERE match_id=?", (match_id,)).fetchone()
            if not have:
                should_refresh = True
        else:  # scheduled
            # 赛前 2h ~ 10min 之间刷新
            if -120 <= delta_min <= -10:
                should_refresh = True
        if should_refresh:
            out.append((match_id, espn_eid))
    return out


def fetch_and_store_lineups() -> dict:
    """Main entrypoint. Refreshes lineups for all eligible matches."""
    conn = sqlite3.connect(DB_PATH)
    cands = candidates_to_refresh(conn)
    print(f"[lineup] candidates: {len(cands)} matches")
    total_stored = 0
    for match_id, espn_eid in cands:
        r = fetch_and_store_one(conn, match_id, espn_eid)
        if r.get("error"):
            print(f"  ❌ {match_id}: {r['error']}")
        elif r.get("rosters_empty"):
            # ESPN 还没公布 lineup (赛前 > 1h 通常空)
            print(f"  ⏳ {match_id}: rosters empty (not yet announced)")
        else:
            print(f"  ✅ {match_id}: stored {r['stored']} teams")
            total_stored += r["stored"]
    conn.close()
    return {"candidates": len(cands), "stored": total_stored}


if __name__ == "__main__":
    print(fetch_and_store_lineups())


# ── 一次性回填 (admin) ─────────────────────────────────────────────────────────
def backfill_all() -> dict:
    """一次性回填所有 external_ids 已关联 ESPN 比赛 的阵容. 不受 candidates 过滤限制."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.execute("""
        SELECT m.match_id, e.espn_event_id, m.status
        FROM matches m
        JOIN external_ids e ON e.match_id = m.match_id
        WHERE e.espn_event_id IS NOT NULL
    """)
    rows = cur.fetchall()
    print(f"[lineup] backfill: {len(rows)} matches")
    total = 0
    empty = 0
    failed = 0
    for match_id, espn_eid, status in rows:
        summary = fetch_espn_summary(espn_eid)
        if not summary:
            failed += 1
            print(f"  ❌ {match_id}: fetch failed")
            continue
        rosters = summary.get("rosters") or []
        if not rosters:
            empty += 1
            continue
        db_row = conn.execute("SELECT match_id, home_team, away_team FROM matches WHERE match_id=?",
                              (match_id,)).fetchone()
        if not db_row:
            continue
        stored_this = 0
        for r in rosters:
            parsed = _parse_roster(r)
            if not parsed:
                continue
            side = _match_team_to_side(parsed["team_name"], db_row)
            if store_lineup(conn, match_id, side, parsed):
                stored_this += 1
        if stored_this:
            total += stored_this
            conn.execute("UPDATE external_ids SET espn_synced_at=? WHERE match_id=?",
                         (datetime.now(timezone.utc).isoformat(), match_id))
            conn.commit()
    conn.close()
    print(f"[lineup] backfill done: {total} rosters stored, {empty} empty (likely not yet played), {failed} fetch failed")
    return {"total": total, "empty": empty, "failed": failed, "candidates": len(rows)}


if __name__ == "__main__" and len(sys.argv) > 1 and sys.argv[1] == "backfill":
    print(backfill_all())
