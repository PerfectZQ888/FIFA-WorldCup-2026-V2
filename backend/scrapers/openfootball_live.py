"""Live match data scraper — pulls real scores from openfootball/worldcup.json.

Source: jsDelivr CDN proxying raw.githubusercontent.com (raw directly is blocked in this env).
URL:   https://cdn.jsdelivr.net/gh/openfootball/worldcup.json@master/2026/worldcup.json
Format: matches[].score.ft = [home, away] if finished; goals1/goals2 lists if scored.
Refresh: every 60s via APScheduler. Writes to SQLite `matches` table.

This is the v3 plan's primary data source — just discovered we can reach it via CDN.
"""
from __future__ import annotations
import json
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx

# Time-based safety net: even if upstream never reports a 'finished' status
# (openfootball's 2026 file is sparse), flip a 'live' match to 'finished' once
# 2.5 hours have elapsed since kickoff. Matches the 2.5h window the frontend
# uses in liveCard() / renderLive().
STALE_LIVE_WINDOW = timedelta(hours=2)

# Ensure project root is on path (so we can import seed)
sys.path.insert(0, str(Path(__file__).parent.parent))

DB_PATH = Path("data/wc2026.db")
DATA_URL = "https://cdn.jsdelivr.net/gh/openfootball/worldcup.json@master/2026/worldcup.json"
TIMEOUT = 20.0


def fetch_live() -> dict[str, Any] | None:
    """Fetch the latest match data. Returns the JSON dict or None on failure."""
    try:
        r = httpx.get(DATA_URL, timeout=TIMEOUT, headers={"User-Agent": "WorldCup-Analytics-Hub/1.0"})
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"[scraper] fetch failed: {e}")
        return None


def team_name_cn_to_db(name: str) -> str:
    """Map openfootball team names to our seed database names (some differ)."""
    # openfootball uses "Czech Republic" while we use "Czechia"
    overrides = {
        "Czech Republic": "Czechia",
        "Bosnia & Herzegovina": "Bosnia & Herzegovina",  # both
        "Türkiye": "Türkiye",
        "Turkey": "Türkiye",
    }
    return overrides.get(name, name)


def parse_match(m: dict) -> dict:
    """Convert openfootball match dict to our DB row format."""
    score = m.get("score") or {}
    ft = score.get("ft")
    ht = score.get("ht")
    # v2.1 修复: openfootball 上游只输出 'finished' / 'scheduled' 两种状态, 不会输出 'live'.
    # 但进球列表 (goals1/goals2) 或半场比分 (ht) 已存在, 说明比赛正在进行, 推断为 'live'.
    has_goals = bool(m.get("goals1") or m.get("goals2"))
    has_score_partial = bool(ft or ht or score.get("i") or score.get("et") or score.get("pen"))
    if ft:
        status = "finished"
    elif has_goals or has_score_partial:
        status = "live"
    else:
        status = "scheduled"

    # Combine goals from both teams
    goals = []
    for g in m.get("goals1", []) or []:
        goals.append({"team": team_name_cn_to_db(m["team1"]), "scorer": g["name"], "minute": int(str(g["minute"]).replace("'", "").replace("+", "").split()[0]) if g.get("minute") else 0})
    for g in m.get("goals2", []) or []:
        goals.append({"team": team_name_cn_to_db(m["team2"]), "scorer": g["name"], "minute": int(str(g["minute"]).replace("'", "").replace("+", "").split()[0]) if g.get("minute") else 0})

    # Parse time "13:00 UTC-6" → "13:00"
    time_str = m.get("time", "").split(" ")[0] if m.get("time") else ""

    # Parse round + group
    round_str = m.get("round", "")
    group_str = m.get("group", "")
    group_letter = ""
    if group_str.startswith("Group "):
        group_letter = group_str.replace("Group ", "").strip()
    matchday = None
    if "Matchday 1" in round_str:
        matchday = 1
    elif "Matchday 2" in round_str:
        matchday = 2
    elif "Matchday 3" in round_str:
        matchday = 3

    # Round normalization (openfootball uses different names)
    round_norm = round_str
    if round_str.startswith("Matchday"):
        round_norm = f"Group {group_letter} {round_str}"

    return {
        "team1": team_name_cn_to_db(m["team1"]),
        "team2": team_name_cn_to_db(m["team2"]),
        "home_score": ft[0] if ft else None,
        "away_score": ft[1] if ft else None,
        "ht_home": ht[0] if ht else None,
        "ht_away": ht[1] if ht else None,
        "status": status,
        "goals": goals,
        "match_date": m.get("date", ""),
        "match_time": time_str,
        "group": group_letter,
        "round": round_norm,
        "venue": m.get("ground", ""),
    }


def reap_stale_live(db: sqlite3.Connection, now: str | None = None) -> int:
    """Flip stale 'live' matches to 'finished' once kickoff + STALE_LIVE_WINDOW has passed.

    Returns the number of matches reaped. Uses match_time stored as UTC ("HH:MM")
    on match_date. Safe to call repeatedly — once a row is 'finished' it is
    skipped. Only reaps rows with a non-null score (i.e. play actually started).
    """
    now_dt = datetime.fromisoformat(now) if now else datetime.now(timezone.utc)
    rows = db.execute("""
        SELECT match_id, match_date, match_time
        FROM matches
        WHERE status = 'live' AND home_score IS NOT NULL
    """).fetchall()
    reaped = 0
    for mid, date, time_str in rows:
        if not date or not time_str:
            continue
        try:
            # match_time is stored as UTC ("HH:MM"), so attach UTC for safe arithmetic
            kickoff = datetime.fromisoformat(f"{date}T{time_str}:00").replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        if now_dt - kickoff < STALE_LIVE_WINDOW:
            continue
        db.execute("""
            UPDATE matches SET status = 'finished', last_updated = ?
            WHERE match_id = ? AND status = 'live'
        """, (now_dt.isoformat(), mid))
        if db.total_changes:
            reaped += 1
    if reaped:
        db.commit()
    return reaped


def promote_scheduled_to_live(db: sqlite3.Connection, now: str | None = None) -> int:
    """Promote stale 'scheduled' matches to 'live' once kickoff time has passed.

    配套 reap_stale_live() 的"反向"操作: 上游若漏标 'live' 状态, 靠开球时间兜底.
    这样 /api/matches/live 不需要每次都做时间推断, DB 本身就是正确状态.
    """
    now_dt = datetime.fromisoformat(now) if now else datetime.now(timezone.utc)
    rows = db.execute("""
        SELECT match_id, match_date, match_time
        FROM matches
        WHERE status = 'scheduled' AND home_score IS NOT NULL
    """).fetchall()
    promoted = 0
    for mid, date, time_str in rows:
        if not date or not time_str:
            continue
        try:
            kickoff = datetime.fromisoformat(f"{date}T{time_str}:00").replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        if now_dt < kickoff:
            continue
        db.execute("""
            UPDATE matches SET status = 'live', last_updated = ?
            WHERE match_id = ? AND status = 'scheduled'
        """, (now_dt.isoformat(), mid))
        if db.total_changes:
            promoted += 1
    if promoted:
        db.commit()
    return promoted


def upsert_matches(matches: list[dict], db_path: Path = DB_PATH) -> dict:
    """Write scraped match data to SQLite. Returns summary stats."""
    db = sqlite3.connect(db_path)
    now = datetime.now(timezone.utc).isoformat()
    updated, finished_added = 0, 0
    for m in matches:
        # Find matching match in DB by (date, team1, team2)
        row = db.execute("""
            SELECT match_id, home_score, away_score, status
            FROM matches
            WHERE match_date = ? AND home_team = ? AND away_team = ?
        """, (m["match_date"], m["team1"], m["team2"])).fetchone()
        if not row:
            # Try reverse
            row = db.execute("""
                SELECT match_id, home_score, away_score, status
                FROM matches
                WHERE match_date = ? AND home_team = ? AND away_team = ?
            """, (m["match_date"], m["team2"], m["team1"])).fetchone()
            if row:
                # Swap home/away in scraped data
                m["team1"], m["team2"] = m["team2"], m["team1"]
                m["home_score"], m["away_score"] = m["away_score"], m["home_score"]
                m["ht_home"], m["ht_away"] = m["ht_away"], m["ht_home"]
                # Also swap goals
                m["goals"] = [
                    {**g, "team": m["team1"] if g["team"] == m["team2"] else m["team2"]}
                    for g in m["goals"]
                ]
        if not row:
            continue
        mid, old_h, old_a, old_status = row
        # Don't downgrade a finished match to live/scheduled (openfootball might lag behind reality).
        # Note: live → finished IS an upgrade and must be allowed.
        if old_status == "finished" and m["status"] != "finished":
            continue
        # Only update if new data has more info or status changed
        if old_h == m["home_score"] and old_a == m["away_score"] and old_status == m["status"]:
            continue  # no change
        db.execute("""
            UPDATE matches SET
                home_score = ?, away_score = ?, status = ?, goals_json = ?, last_updated = ?
            WHERE match_id = ?
        """, (
            m["home_score"], m["away_score"], m["status"],
            json.dumps(m["goals"], ensure_ascii=False), now, mid
        ))
        updated += 1
        if m["status"] == "finished" and old_status != "finished":
            finished_added += 1
    db.commit()

    # 1) Stale-live reaper: if a match has been "live" past kickoff + 2.5h with no
    #    upstream update, freeze it at its current score and mark finished.
    reaped = reap_stale_live(db, now=now)
    if reaped:
        finished_added += reaped
        updated += reaped

    # 2) Scheduled → live promoter: 若 'scheduled' 比赛已过开球时间, 提升为 'live'
    #    兜底: openfootball 上游漏标 live 也能在 DB 中体现, 下一轮 scraper 抓到 'ft' 时再升 'finished'.
    promoted = promote_scheduled_to_live(db, now=now)
    if promoted:
        updated += promoted

    # Recompute standings
    from seed import compute_standings
    compute_standings(db)
    db.close()
    return {"updated": updated, "newly_finished": finished_added, "ts": now}


def run_once() -> dict | None:
    """Single fetch + upsert cycle. Returns stats or None on failure."""
    data = fetch_live()
    if not data or "matches" not in data:
        return None
    matches = [parse_match(m) for m in data["matches"]]
    return upsert_matches(matches)


if __name__ == "__main__":
    result = run_once()
    if result:
        print(f"✅ updated {result['updated']} matches, {result['newly_finished']} newly finished @ {result['ts']}")
    else:
        print("❌ fetch failed")
