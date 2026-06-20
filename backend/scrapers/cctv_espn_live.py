"""Live match data scraper — primary CCTV API, fallback to ESPN.

PRIMARY SOURCE (Chinese, real-time, used by CCTV official website):
  - season schedule : https://cbs-u.sports.cctv.com/pc/game/season_game_list?leagueId=3400&season=2026&client=pc&t=<ts>
  - daily windows   : https://cbs-u.sports.cctv.com/pc/game/date_game_list?startTime=YYYY-MM-DD&endTime=YYYY-MM-DD&leagueId=3400&ran=<ts>
  - live tick (JSONP): https://cbs-u.sports.cctv.com/pc/game/game_status_list?ran=<ts>&callBack=game_status_list
                       (then strip the `game_status_list(...)` wrapper)
  Returns Chinese team names (澳大利亚, 土耳其, etc.) → mapped to DB English names via TEAM_CN_TO_EN.

  **CCTV times are in CST (Asia/Shanghai, UTC+8)**, not UTC. The scraper converts
  them to UTC before comparing to the DB. This is critical for late-night matches:
  e.g. a 03:00 CST kickoff is the previous day in UTC. Without conversion, the
  scraper would fail to match the row and silently drop the match.

FALLBACK SOURCE (English, global):
  - https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard?dates=YYYYMMDD
  Returns English team names matching our DB seed exactly.

Refresh: every 60s (matches CCTV front-end polling cadence of 2 minutes, but tighter for live scores).
Hot-standby: try CCTV first; if it 4xx/5xx, immediately retry ESPN for the same day window.
"""
from __future__ import annotations
import json
import re
import sqlite3
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

from team_name_map import TEAM_CN_TO_EN, en_alias_to_canonical

DB_PATH = Path("data/wc2026.db")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
TIMEOUT = 20.0
LEAGUE_ID_WC2026 = 3400  # CCTV's internal ID for FIFA World Cup 2026

# CCTV's datetimes are Asia/Shanghai (UTC+8). The seed DB stores match_date and
# match_time in UTC. We convert CCTV CST → UTC so the two align.
CCTV_TZ = timezone(timedelta(hours=8))

CCTV_BASE = "https://cbs-u.sports.cctv.com/pc"
ESPN_BASE = "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world"

STATUS_MAP_CCTV = {1: "scheduled", 2: "live", 3: "finished"}
STATUS_MAP_ESPN = {
    "STATUS_SCHEDULED": "scheduled",
    "STATUS_IN_PROGRESS": "live",
    "STATUS_HALFTIME": "live",
    "STATUS_FULL_TIME": "finished",
    "STATUS_POSTPONED": "postponed",
    "STATUS_CANCELED": "cancelled",
}


# ── CCTV ────────────────────────────────────────────────────────────────────

def _cctv_season_url(ts_ms: int) -> str:
    return f"{CCTV_BASE}/game/season_game_list?leagueId={LEAGUE_ID_WC2026}&season=2026&client=pc&t={ts_ms}"


def _cctv_daily_url(start: str, end: str, ts_ms: int) -> str:
    return f"{CCTV_BASE}/game/date_game_list?startTime={start}&endTime={end}&leagueId={LEAGUE_ID_WC2026}&ran={ts_ms}"


def _cctv_status_url(ts_ms: int) -> str:
    return f"{CCTV_BASE}/game/game_status_list?ran={ts_ms}&callBack=game_status_list"


def _cctv_start_to_utc(start_str: str) -> tuple[str, str, str | None]:
    """Parse CCTV's CST datetime and convert to UTC.

    CCTV returns 'YYYY-MM-DD HH:MM:SS' in Asia/Shanghai (UTC+8). The seed DB
    uses UTC dates. We convert: a match at "2026-06-14 03:00:00" CST becomes
    "2026-06-13 19:00" UTC — and that matches the DB's match_id M005.

    Returns:
        (utc_date_iso, utc_time_hhmm, original_cst_str_for_log)
        Returns ("", "", original) if parsing fails.
    """
    if not start_str:
        return "", "", start_str
    try:
        cst_dt = datetime.strptime(start_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=CCTV_TZ)
        utc_dt = cst_dt.astimezone(timezone.utc)
        return utc_dt.date().isoformat(), utc_dt.strftime("%H:%M"), start_str
    except ValueError:
        return "", "", start_str


def fetch_cctv_daily(start: str, end: str) -> list[dict]:
    """Fetch CCTV schedule+scores for a date range. start/end are 'YYYY-MM-DD' (CST)."""
    url = _cctv_daily_url(start, end, int(time.time() * 1000))
    try:
        # CCTV 走 302 → cbs-i 缓存, 必须 follow_redirects=True (v2.1 修复)
        r = httpx.get(url, timeout=TIMEOUT, follow_redirects=True,
                      headers={"User-Agent": UA, "Referer": "https://worldcup.cctv.com/2026/schedule/index.shtml"})
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        print(f"[cctv] daily fetch failed: {e}")
        return []
    out: list[dict] = []
    for grp in data.get("results", []):
        for m in grp.get("list", []):
            out.append(_cctv_match_to_dict(m))
    return out


def fetch_cctv_live_status() -> dict[int, dict]:
    """Hit JSONP live-status endpoint. Returns {match_id: minimal_status_dict}."""
    url = _cctv_status_url(int(time.time() * 1000))
    try:
        # CCTV 走 302 → cbs-i 缓存, 必须 follow_redirects=True (v2.1 修复)
        r = httpx.get(url, timeout=TIMEOUT, follow_redirects=True,
                      headers={"User-Agent": UA, "Referer": "https://worldcup.cctv.com/2026/schedule/index.shtml"})
        r.raise_for_status()
    except Exception as e:
        print(f"[cctv] live status fetch failed: {e}")
        return {}
    raw = r.text
    # strip `game_status_list({...})` wrapper
    m = re.match(r"\s*\w+\s*\((.+)\)\s*;?\s*$", raw, re.S)
    body = m.group(1) if m else raw
    try:
        data = json.loads(body)
    except json.JSONDecodeError as e:
        print(f"[cctv] live status JSON parse failed: {e}")
        return {}
    return {m["id"]: m for m in data.get("results", []) if m.get("leagueId") == LEAGUE_ID_WC2026}


def _cctv_match_to_dict(m: dict) -> dict:
    """Convert a raw CCTV match dict to our normalized internal format.

    Time-zone handling: CCTV's startTime is CST (UTC+8). We convert to UTC so the
    match_date / match_time align with the DB (which stores UTC). Without this
    conversion, late-night CST matches (00:00-08:00) would be stored under the
    wrong calendar day and fail to upsert.
    """
    cn_home = m["homeName"]
    cn_away = m["guestName"]
    en_home = TEAM_CN_TO_EN.get(cn_home, cn_home)
    en_away = TEAM_CN_TO_EN.get(cn_away, cn_away)
    # ESPN / openfootball 偶返英文别名（Cape Verde / Ivory Coast 等），
    # 走过 CN→EN 未中后，en_* 可能仍是别名。再走一次 EN→主名 兜底，
    # 避免 upsert 找不到 fixture 重复 INSERT。
    # 2026-06-14 fix.
    en_home = en_alias_to_canonical(en_home)
    en_away = en_alias_to_canonical(en_away)
    utc_date, utc_time, cst_orig = _cctv_start_to_utc(m.get("startTime", ""))
    return {
        "source": "cctv",
        "cctv_id": m["id"],
        "home_team_cn": cn_home,
        "away_team_cn": cn_away,
        "home_team": en_home,
        "away_team": en_away,
        "match_date": utc_date,
        "match_time": utc_time,
        "_cst_start": cst_orig,  # preserved for logging / debugging
        "status": STATUS_MAP_CCTV.get(m.get("gameStatus"), "scheduled"),
        "home_score": m.get("homeScore"),
        "away_score": m.get("guestScore"),
        "ht_home": m.get("homeHalfScore"),
        "ht_away": m.get("guestHalfScore"),
        "group": (m.get("roundType") or "").replace("组", ""),  # A组 → A
        "round": m.get("gameRound", ""),
        "venue": m.get("gamePlace", ""),
        "live_minute": m.get("currentTime") or "",
    }


# ── ESPN ─────────────────────────────────────────────────────────────────────

def fetch_espn_day(date_yyyymmdd: str) -> list[dict]:
    url = f"{ESPN_BASE}/scoreboard?dates={date_yyyymmdd}"
    try:
        r = httpx.get(url, timeout=TIMEOUT, headers={"User-Agent": UA})
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        print(f"[espn] fetch failed for {date_yyyymmdd}: {e}")
        return []
    out: list[dict] = []
    for ev in data.get("events", []):
        comp = (ev.get("competitions") or [{}])[0]
        status_type = (comp.get("status") or {}).get("type") or {}
        status_id = status_type.get("id") or status_type.get("name") or ""
        # ESPN names are English — match DB directly
        competitors = comp.get("competitors") or []
        if len(competitors) < 2:
            continue
        home = next((c for c in competitors if c.get("homeAway") == "home"), competitors[0])
        away = next((c for c in competitors if c.get("homeAway") == "away"), competitors[1])
        dt = ev.get("date", "")  # ISO 8601 UTC
        try:
            kickoff = datetime.fromisoformat(dt.replace("Z", "+00:00"))
            local = kickoff.astimezone(timezone(timedelta(hours=-6)))  # WC host tz range, fallback
        except Exception:
            kickoff = None
            local = None
        out.append({
            "source": "espn",
            "espn_id": ev.get("id"),
            "home_team": en_alias_to_canonical(home.get("team", {}).get("displayName") or home.get("team", {}).get("name")),
            "away_team": en_alias_to_canonical(away.get("team", {}).get("displayName") or away.get("team", {}).get("name")),
            "match_date": (local.date().isoformat() if local else ""),
            "match_time": (local.strftime("%H:%M") if local else ""),
            "status": _espn_status(status_id),
            "home_score": int(home.get("score") or 0) if home.get("score") is not None else None,
            "away_score": int(away.get("score") or 0) if away.get("score") is not None else None,
            "ht_home": None,  # ESPN summary doesn't expose HT by default
            "ht_away": None,
            "group": "",
            "round": "",
            "venue": (comp.get("venue") or {}).get("fullName") or "",
        })
    return out


def _espn_status(status_id: str) -> str:
    if status_id in STATUS_MAP_ESPN:
        return STATUS_MAP_ESPN[status_id]
    # Fallback heuristic by description
    if "Full Time" in status_id or "FT" == status_id:
        return "finished"
    if "Half" in status_id:
        return "live"
    if "Progress" in status_id:
        return "live"
    if "Scheduled" in status_id:
        return "scheduled"
    return "scheduled"


# ── DB upsert (same pattern as openfootball_live.py) ────────────────────────


def _next_match_id(db: sqlite3.Connection) -> str:
    """Return the next free match_id (M105, M106, ...).

    Inspects existing match_id values, finds the highest numeric suffix
    among IDs matching the M### pattern, and returns M<that+1>. We sort
    by the integer suffix, not lexicographically, to avoid the M100/M101
    ordering trap. Pads to 3 digits to keep match_id format consistent
    with the existing seed (M001-M104).
    """
    rows = db.execute(
        "SELECT match_id FROM matches WHERE match_id GLOB 'M[0-9][0-9][0-9]'"
    ).fetchall()
    max_n = 0
    for (mid,) in rows:
        try:
            n = int(mid[1:])
            if n > max_n:
                max_n = n
        except ValueError:
            continue
    return f"M{max_n + 1:03d}"


def _canonical_team_name(db: sqlite3.Connection, name: str) -> str:
    """Resolve a team name to the DB-canonical form.

    ESPN sometimes returns slightly different spellings than our seed DB
    (e.g. 'Cape Verde' instead of FIFA 2026's official 'Cabo Verde'). When
    we INSERT a new match, we must store the DB-canonical name, otherwise
    future scraper runs will fail to match the row and create a duplicate.

    Resolution order:
      1. Exact match in teams table
      2. Case-insensitive match
      3. Pass-through (unknown)
    """
    if not name:
        return name
    row = db.execute("SELECT name FROM teams WHERE name = ?", (name,)).fetchone()
    if row:
        return row[0]
    # Case-insensitive fallback
    row = db.execute("SELECT name FROM teams WHERE LOWER(name) = LOWER(?)", (name,)).fetchone()
    if row:
        return row[0]
    return name


def _lookup_group(db: sqlite3.Connection, *team_names: str) -> str | None:
    """Look up the group_name for a match by checking its teams.

    Both home and away teams should belong to the same group; if either
    is unknown to the teams table, returns None.
    """
    groups: set[str] = set()
    for t in team_names:
        row = db.execute("SELECT group_name FROM teams WHERE name = ?", (t,)).fetchone()
        if row and row[0]:
            groups.add(row[0])
    if len(groups) == 1:
        return next(iter(groups))
    return None  # ambiguous or unknown


def upsert_matches(matches: list[dict], db_path: Path = DB_PATH) -> dict:
    """Upsert scraped match data into SQLite. Returns coverage stats.

    Stats returned (all ints, except `ts`):
        fetched               : input list length
        matched               : upserted into existing DB rows
        inserted              : NEW DB rows created (DB was missing the match)
        updated               : rows whose score/status actually changed
        newly_finished        : rows that flipped to 'finished' this run
        skipped_no_db         : no DB match AND we couldn't insert (unknown team, etc.)
        skipped_finished_downgrade: DB had 'finished' but CCTV reported non-finished
        ts                    : ISO8601 UTC timestamp of the run
    """
    db = sqlite3.connect(db_path)
    now = datetime.now(timezone.utc).isoformat()
    matched = 0
    inserted = 0
    updated = 0
    newly_finished = 0
    skipped_no_db = 0
    skipped_finished_downgrade = 0

    for m in matches:
        # ── 1) Find the existing DB row (with home/away swap tolerance) ──
        row = db.execute("""
            SELECT match_id, home_score, away_score, status
            FROM matches
            WHERE match_date = ? AND home_team = ? AND away_team = ?
        """, (m["match_date"], m["home_team"], m["away_team"])).fetchone()
        swapped = False
        if not row:
            row = db.execute("""
                SELECT match_id, home_score, away_score, status
                FROM matches
                WHERE match_date = ? AND home_team = ? AND away_team = ?
            """, (m["match_date"], m["away_team"], m["home_team"])).fetchone()
            if row:
                # Swap to match DB's home/away orientation
                m["home_team"], m["away_team"] = m["away_team"], m["home_team"]
                m["home_score"], m["away_score"] = m["away_score"], m["home_score"]
                m["ht_home"], m["ht_away"] = m["ht_away"], m["ht_home"]
                swapped = True

        # ── 1b) Date-tolerance lookup ────────────────────────────────
        # The seed DB and ESPN/CCTV sometimes disagree on which calendar day
        # a match belongs to (seed stores times that look like local kickoff
        # but are labeled "UTC" in the data file; ESPN returns UTC-6
        # "Mexico City" local). If exact-date lookup missed, look ±1 day
        # for the same team pair. This avoids creating duplicate rows for
        # the same match just because one source says "2026-06-14 01:00 UTC"
        # and the other says "2026-06-13 19:00 local".
        if not row and m.get("match_date"):
            try:
                base = datetime.fromisoformat(m["match_date"]).date()
            except ValueError:
                base = None
            if base:
                for offset in (-1, 1):
                    probe = (base + timedelta(days=offset)).isoformat()
                    cand = db.execute("""
                        SELECT match_id, home_score, away_score, status
                        FROM matches
                        WHERE match_date = ? AND home_team = ? AND away_team = ?
                    """, (probe, m["home_team"], m["away_team"])).fetchone()
                    if not cand:
                        cand = db.execute("""
                            SELECT match_id, home_score, away_score, status
                            FROM matches
                            WHERE match_date = ? AND home_team = ? AND away_team = ?
                        """, (probe, m["away_team"], m["home_team"])).fetchone()
                        if cand:
                            m["home_team"], m["away_team"] = m["away_team"], m["home_team"]
                            m["home_score"], m["away_score"] = m["away_score"], m["home_score"]
                            m["ht_home"], m["ht_away"] = m["ht_away"], m["ht_home"]
                    if cand:
                        row = cand
                        # Don't rewrite match_date on the DB row — keep the
                        # original schedule. Just sync the scores/status.
                        print(f"[scraper] date-tol hit: scraped={m['match_date']} "
                              f"db={probe} (offset={offset:+d}d) match_id={cand[0]} "
                              f"({m['home_team']} vs {m['away_team']})")
                        break

        # ── 2) If DB has no row, try to INSERT a new one ──
        if not row:
            # Normalize team names to DB-canonical form before storing
            # (ESPN may return "Cape Verde" while DB uses FIFA 2026's "Cabo Verde")
            m["home_team"] = _canonical_team_name(db, m["home_team"])
            m["away_team"] = _canonical_team_name(db, m["away_team"])
            # We need a group_name for INSERT (it's NOT NULL in practice — the
            # standings query and /api/groups both key on it). Derive from teams.
            group_name = _lookup_group(db, m["home_team"], m["away_team"])
            if not group_name:
                # Last-ditch: CCTV sometimes reports "roundType" like "A组" — use it,
                # but only if it's a valid WC group letter (A-L).
                group_from_cctv = (m.get("group") or "").strip().upper()
                if group_from_cctv in {chr(ord("A") + i) for i in range(12)}:
                    group_name = group_from_cctv
            if not group_name:
                skipped_no_db += 1
                print(f"[scraper] skip {m.get('home_team')!r} vs {m.get('away_team')!r} "
                      f"on {m.get('match_date')}: not in DB and group unknown "
                      f"(CCTV names: {m.get('home_team_cn')!r} / {m.get('away_team_cn')!r})")
                continue

            # Avoid duplicate insert if a (swapped) row was just inserted in
            # this loop iteration (shouldn't normally happen, but be safe).
            new_id = _next_match_id(db)
            try:
                db.execute("""
                    INSERT INTO matches
                        (match_id, round, matchday, group_name, match_date, match_time,
                         home_team, away_team, venue, home_score, away_score, status,
                         goals_json, last_updated)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    new_id,
                    m.get("round") or "",
                    None,  # matchday unknown from CCTV
                    group_name,
                    m["match_date"],
                    m.get("match_time") or "",
                    m["home_team"],
                    m["away_team"],
                    m.get("venue") or "",
                    m.get("home_score"),
                    m.get("away_score"),
                    m.get("status", "scheduled"),
                    "[]",
                    now,
                ))
                inserted += 1
                print(f"[scraper] INSERT {new_id} {m['home_team']} vs {m['away_team']} "
                      f"on {m['match_date']} {m.get('match_time')} (group {group_name}, "
                      f"from CCTV cctv_id={m.get('cctv_id')})")
                continue  # row was just created; nothing to UPDATE
            except sqlite3.IntegrityError as e:
                # Most likely: someone else (scheduler) inserted in parallel.
                # Re-query and fall through to the UPDATE path.
                print(f"[scraper] INSERT race for {m['home_team']} vs {m['away_team']}: {e}")
                row = db.execute("""
                    SELECT match_id, home_score, away_score, status
                    FROM matches
                    WHERE match_date = ? AND home_team = ? AND away_team = ?
                """, (m["match_date"], m["home_team"], m["away_team"])).fetchone()
                if not row:
                    skipped_no_db += 1
                    continue

        # ── 3) UPDATE existing row ──
        mid, old_h, old_a, old_status = row

        if old_status == "finished" and m["status"] != "finished":
            skipped_finished_downgrade += 1
            continue  # don't downgrade (CCTV might lag behind a manually-finished match)

        matched += 1
        if old_h == m["home_score"] and old_a == m["away_score"] and old_status == m["status"]:
            continue  # no change, just touched

        db.execute("""
            UPDATE matches SET home_score=?, away_score=?, status=?, last_updated=?
            WHERE match_id = ?
        """, (m["home_score"], m["away_score"], m["status"], now, mid))
        updated += 1
        if m["status"] == "finished" and old_status != "finished":
            newly_finished += 1

    db.commit()
    from seed import compute_standings
    compute_standings(db)
    db.close()
    return {
        "matched": matched,
        "inserted": inserted,
        "updated": updated,
        "newly_finished": newly_finished,
        "skipped_no_db": skipped_no_db,
        "skipped_finished_downgrade": skipped_finished_downgrade,
        "ts": now,
    }


# ── Orchestrator ────────────────────────────────────────────────────────────

def run_once() -> dict | None:
    """One fetch cycle: CCTV primary for [today-1, today+7], ESPN fallback."""
    today = datetime.now(timezone.utc).date()
    start = (today - timedelta(days=1)).isoformat()
    end = (today + timedelta(days=7)).isoformat()

    print(f"[scraper] window {start}..{end} (CCTV CST window for query)")

    # Try CCTV daily. Note: CCTV's startTime/endTime query params appear to be
    # treated as CST dates (CCTV's local), but the scraper converts the returned
    # match timestamps to UTC before writing to the DB. The window is in CST too.
    matches = fetch_cctv_daily(start, end)
    src = "cctv"
    if not matches:
        print("[scraper] CCTV daily empty/failed, falling back to ESPN")
        matches = []
        for offset in range(-1, 8):
            d = today + timedelta(days=offset)
            matches.extend(fetch_espn_day(d.strftime("%Y%m%d")))
        src = "espn"

    if not matches:
        return None

    # Enrich live matches with status endpoint
    live_ids = {m["cctv_id"] for m in matches if m["source"] == "cctv" and m["status"] == "live"}
    if live_ids:
        live_status = fetch_cctv_live_status()
        for m in matches:
            if m["source"] == "cctv" and m["cctv_id"] in live_ids:
                ls = live_status.get(m["cctv_id"])
                if ls:
                    m["home_score"] = ls.get("homeScore", m["home_score"])
                    m["away_score"] = ls.get("guestScore", m["away_score"])
                    if ls.get("homeHalfScore") is not None:
                        m["ht_home"] = ls["homeHalfScore"]
                        m["ht_away"] = ls["guestHalfScore"]
                    if ls.get("currentTime"):
                        m["live_minute"] = ls["currentTime"]
                    gs = ls.get("gameStatus")
                    if gs == 2:
                        m["status"] = "live"
                    elif gs == 3:
                        m["status"] = "finished"

    res = upsert_matches(matches)
    res["source"] = src
    res["fetched"] = len(matches)

    # v2.1 修复: CCTV 窗口只覆盖 today-1 ~ today+7, 超出此范围的 'live' 比赛 (如 seed 写错 /
    # openfootball scraper 漏标) 永远不会被 reap. 这里在 CCTV run 末尾统一跑一次 reaper.
    # 调用 openfootball 的 reap/promote (它们是时间推断, 不依赖上游状态).
    try:
        from scrapers.openfootball_live import reap_stale_live, promote_scheduled_to_live
        # 用刚 upsert 的 db 连接 (避免锁竞争)
        reap_db = sqlite3.connect(str(DB_PATH))
        try:
            reap_now = datetime.now(timezone.utc).isoformat()
            reaped = reap_stale_live(reap_db, now=reap_now)
            promoted = promote_scheduled_to_live(reap_db, now=reap_now)
            res["reaped"] = reaped
            res["promoted"] = promoted
            if reaped or promoted:
                print(f"[scraper] reaper: reaped={reaped} promoted={promoted}")
                # 重算 standings (因为 reaped 的比赛从 'live' 变 'finished' 会影响积分)
                from seed import compute_standings
                compute_standings(reap_db)
        finally:
            reap_db.close()
    except Exception as e:
        print(f"[scraper] reaper skipped: {e}")
        res["reaped"] = 0
        res["promoted"] = 0

    print(f"[scraper] source={src} fetched={len(matches)} "
          f"matched={res['matched']} inserted={res['inserted']} updated={res['updated']} "
          f"newly_finished={res['newly_finished']} "
          f"reaped={res.get('reaped',0)} promoted={res.get('promoted',0)} "
          f"skipped_no_db={res['skipped_no_db']} "
          f"skipped_finished_downgrade={res['skipped_finished_downgrade']}")
    return res


if __name__ == "__main__":
    out = run_once()
    print("✅" if out else "❌", out or "fetch failed")
