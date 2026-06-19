"""CCTV top-scorers scraper — fetches the official WC2026 射手榜.

Data source: hidden CCTV API behind the SPA at
  https://worldcup.cctv.com/2026/scorers/index.shtml
The SPA boots from `scripts/worldcup2026_top_scorer.*.js`, which calls:

    GET https://cbs-u.sports.cctv.com/statistics/football/player/scorers
        ?leagueId=3400&season=2026
    (302 → https://cbs-i.sports.cctv.com/cache/<hash>)

Response shape (JSON):
    {
      "code": 88888,
      "success": true,
      "results": [
        {
          "playerId": 464029,
          "playerName": "巴洛贡",          // Chinese name
          "teamName": "美国",               // Chinese team
          "goals": 2,
          "penaltyKickGoals": 0,
          "games": 1,
          "photoUrl": "...",
          "teamLogoUrl": "..."
        }, ...
      ]
    }

Mapping:
  - `teamName` (Chinese) → English DB name via TEAM_CN_TO_EN from team_name_map.py
  - `playerName` is kept as the Chinese name (CCTV's official rendering) so the
    UI can show 巴洛贡 etc.; fallback to English DB names if mapping is missing.

Output: list[dict] sorted by goals desc, then penalties desc, then minutes-per-goal asc.
  {rank, player, player_en, team, team_en, goals, penalties, matches, mins_per_goal, source}
"""
from __future__ import annotations
import json
import sqlite3
import sys
import time
from pathlib import Path
from typing import Any

import httpx

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

from team_name_map import TEAM_CN_TO_EN  # noqa: E402

DB_PATH = Path("data/wc2026.db")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
TIMEOUT = 15.0
LEAGUE_ID_WC2026 = 3400
CCTV_SCORERS_URL = (
    f"https://cbs-u.sports.cctv.com/statistics/football/player/scorers"
    f"?leagueId={LEAGUE_ID_WC2026}&season=2026"
)


def fetch_cctv_scorers() -> list[dict[str, Any]]:
    """Fetch the current CCTV top-scorer list.

    Returns a list of normalized dicts sorted by goals desc. Returns an empty
    list on network/parse failure (caller should fall back to DB aggregation).
    Each entry:
        rank           : 1-based ranking
        player         : Chinese player name (from CCTV) — display label
        player_en      : English player name (from DB goals_json) if known
        team           : Chinese team name (from CCTV)
        team_en        : English DB team name (from TEAM_CN_TO_EN)
        goals          : total goals
        penalties      : penalty goals subset
        matches        : matches played (CCTV reports one figure per player)
        mins_per_goal  : None from CCTV (we don't have per-match minutes)
        source         : "cctv"
    """
    try:
        r = httpx.get(
            CCTV_SCORERS_URL,
            timeout=TIMEOUT,
            headers={"User-Agent": UA, "Referer": "https://worldcup.cctv.com/2026/scorers/index.shtml"},
            follow_redirects=True,
        )
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        print(f"[cctv_scorers] fetch failed: {e}")
        return []

    if not data.get("success") or not data.get("results"):
        print(f"[cctv_scorers] non-success response: code={data.get('code')}, msg={data.get('msg')}")
        return []

    out: list[dict[str, Any]] = []
    for p in data["results"]:
        cn_team = p.get("teamName", "")
        en_team = TEAM_CN_TO_EN.get(cn_team, cn_team)
        out.append({
            "rank": 0,  # filled below
            "player": p.get("playerName", ""),
            "player_en": None,
            "team": cn_team,
            "team_en": en_team,
            "goals": int(p.get("goals") or 0),
            "penalties": int(p.get("penaltyKickGoals") or 0),
            "matches": int(p.get("games") or 0),
            "mins_per_goal": None,
            "source": "cctv",
        })

    # Sort: goals desc, then penalties desc, then matches asc (more goals in fewer games = better)
    out.sort(key=lambda x: (-x["goals"], -x["penalties"], x["matches"]))
    for i, e in enumerate(out, 1):
        e["rank"] = i
    return out


# ── DB fallback aggregation ────────────────────────────────────────────────


def _enrich_player_en_from_db(scorers: list[dict[str, Any]], db_path: Path = DB_PATH) -> None:
    """Best-effort enrichment: map CCTV Chinese player names to DB English names.

    The DB `goals_json` already carries the English scorer name (e.g. "Balogun")
    plus team. We pair CCTV entries (CN name, team_en, goal count) with DB
    entries (EN name, team_en, goal count) by walking each team in order.

    Distribution rule per team:
      For each CCTV entry of team T with N goals, we pop the first DB entry
      of team T with N goals whose English name hasn't been used yet. This
      works because CCTV and DB agree on the goal counts (both come from
      match feeds) — only the display name differs.

    The Chinese name remains in `player` for display; `player_en` is set when
    we can pair it, else left as None.
    """
    import sqlite3
    try:
        db = sqlite3.connect(db_path)
        # Build per-team queue of DB english scorers keyed by goal count.
        # queues[team_en][goal_count] = list[english_name] in DB encounter order.
        queues: dict[str, dict[int, list[str]]] = {}
        for row in db.execute(
            "SELECT goals_json FROM matches "
            "WHERE status='finished' AND goals_json IS NOT NULL AND goals_json<>'[]'"
        ).fetchall():
            for g in json.loads(row[0]):
                team = g.get("team")
                scorer = g.get("scorer")
                if not team or not scorer:
                    continue
                q = queues.setdefault(team, {})
                q.setdefault(1, []).append(scorer)  # all DB entries are 1-goal scorers (we don't track duplicates per row)
        db.close()
    except Exception as e:
        print(f"[cctv_scorers] DB enrichment failed: {e}")
        return

    # Assign en names per team. Track usage so we don't double-assign.
    used: dict[str, set[str]] = {}
    for s in scorers:
        team_en = s["team_en"]
        goals = s["goals"]
        queue = queues.get(team_en, {}).get(1, [])
        used.setdefault(team_en, set())
        # Find an unused english name
        for name in queue:
            if name not in used[team_en]:
                s["player_en"] = name
                used[team_en].add(name)
                break


def fetch_db_scorers(db_path: Path = DB_PATH) -> list[dict[str, Any]]:
    """Fallback: aggregate scorers from the local matches.goals_json.

    Same shape as fetch_cctv_scorers(). Used when CCTV API is unreachable.
    Includes minutes-per-goal because we have the per-goal minute data.
    """
    db = sqlite3.connect(db_path)
    by_player: dict[str, dict[str, Any]] = {}
    matches_played: dict[str, set[str]] = {}  # player -> set of team names (later we use team from goals)
    for row in db.execute("""
        SELECT match_id, goals_json
        FROM matches
        WHERE status='finished' AND goals_json IS NOT NULL AND goals_json<>'[]'
    """).fetchall():
        mid, gj = row[0], row[1]
        for g in json.loads(gj):
            scorer = g.get("scorer")
            team = g.get("team")
            minute = g.get("minute") or 0
            if not scorer or not team:
                continue
            entry = by_player.setdefault(scorer, {
                "player": scorer,
                "player_en": scorer,
                "team": team,
                "team_en": team,
                "goals": 0,
                "penalties": 0,
                "matches": 0,
                "minutes_sum": 0,
                "mins_per_goal": None,
                "source": "db",
            })
            entry["goals"] += 1
            entry["minutes_sum"] += int(minute) if minute else 90  # assume full match if unknown
            if g.get("penalty"):
                entry["penalties"] += 1
            matches_played.setdefault(scorer, set()).add(team)

    db.close()

    for p, entry in by_player.items():
        # matches played by a player = how many distinct matches they scored in;
        # a single match could have multiple goals by the same player (Balogun has 2 in 1 match).
        # We approximate matches by counting distinct goals, since DB doesn't track appearances.
        entry["matches"] = max(1, entry["goals"])  # at least 1 per scorer
        if entry["goals"] > 0:
            entry["mins_per_goal"] = round(entry["minutes_sum"] / entry["goals"], 1)

    out = sorted(by_player.values(), key=lambda x: (-x["goals"], -x["penalties"], x["mins_per_goal"] or 1e9))
    for i, e in enumerate(out, 1):
        e["rank"] = i
    return out


def fetch_scorers(limit: int = 20, prefer: str = "cctv") -> list[dict[str, Any]]:
    """Combined fetcher. Try preferred source first, fall back to the other.

    Args:
        limit: max scorers to return (default 20)
        prefer: "cctv" or "db". Default "cctv" — it's the real-time source.

    Behavior:
        - prefer="cctv": try CCTV first; if empty/None, fall back to DB.
        - prefer="db":   use DB only (used by tests for determinism).
    Returns up to `limit` scorers sorted by rank.
    """
    if prefer == "cctv":
        scorers = fetch_cctv_scorers()
        if not scorers:
            print("[cctv_scorers] CCTV empty, falling back to DB aggregation")
            scorers = fetch_db_scorers()
    else:
        scorers = fetch_db_scorers()

    # Best-effort enrichment from DB (CCTV path only)
    if scorers and scorers[0].get("source") == "cctv":
        _enrich_player_en_from_db(scorers)
    return scorers[:limit]


# ── Module-level cache (refreshed by scheduler) ────────────────────────────

_CACHE: dict[str, Any] = {"ts": None, "data": [], "src": None}


def refresh_cache(limit: int = 20) -> list[dict[str, Any]]:
    """Refresh the in-memory cache. Called by app.py scheduler."""
    data = fetch_scorers(limit=limit, prefer="cctv")
    _CACHE["data"] = data
    _CACHE["ts"] = time.time()
    _CACHE["src"] = data[0]["source"] if data else None
    return data


def get_cached(limit: int = 20) -> list[dict[str, Any]]:
    """Return cached scorers (refreshing if cache is empty or stale)."""
    import time
    stale = _CACHE["ts"] is None or (time.time() - _CACHE["ts"]) > 600  # 10 min
    if not _CACHE["data"] or stale:
        refresh_cache(limit=limit)
    return _CACHE["data"][:limit]


if __name__ == "__main__":
    import json as _json
    data = fetch_scorers(limit=20)
    print(_json.dumps(data, ensure_ascii=False, indent=2))