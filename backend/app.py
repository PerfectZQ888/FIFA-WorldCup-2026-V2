"""WorldCup 2026 Analytics Hub — FastAPI backend (V2 standalone).

V2 与 V1 完全隔离:
  - 端口 8001 (V1 用 8000)
  - 独立数据目录 backend/data/
  - 独立静态目录 backend/static/ (前端为 v1.2 优化版)
  - 独立日志目录 backend/logs/

Endpoints (all read-only):

  GET  /                      single-page UI
  GET  /bracket               standalone bracket visualisation (v4)
  GET  /api/health            liveness + last update time
  GET  /api/summary           tournament summary (KPIs for hero section)
  GET  /api/groups            12 groups with teams
  GET  /api/standings         12 group standings tables
  GET  /api/matches           full match list (filter by group/status/date)
  GET  /api/matches/live      matches in next 24h or live
  GET  /api/matches/{id}      single match detail with goals
  GET  /api/matches/{id}/prediction   per-match AI prediction (v4)
  GET  /api/knockout          all 32 knockout matches grouped by round (v4)
  GET  /api/bracket           full bracket structure with AI predictions (v4)
  GET  /api/teams             all 48 teams
  GET  /api/teams/{name}      single team profile
  GET  /api/predictions       48 team champion probabilities (sorted)
  GET  /api/history           22 World Cup editions (1930–2022)
  GET  /api/venues            16 host stadiums
  POST /api/admin/refresh     recompute predictions (manual trigger)

Static assets served from /static.
"""
from __future__ import annotations
import json
import re
import sqlite3
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

import analyzer
from scrapers import cctv_espn_live
from scrapers import cctv_scorers
from scrapers import lineup as lineup_scraper  # v2.1: 阵容抓取 (ESPN)

BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "data" / "wc2026.db"
STATIC_DIR = BASE_DIR / "static"


def db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def row_to_dict(row: sqlite3.Row | None) -> dict | None:
    if row is None:
        return None
    return {k: row[k] for k in row.keys()}


def rows_to_list(rows) -> list[dict]:
    return [dict(r) for r in rows]


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = AsyncIOScheduler()
    # Nightly recompute predictions at 23:00
    scheduler.add_job(run_prediction_job, "cron", hour=23, minute=0)
    # Live data fetch every 60s
    scheduler.add_job(run_live_fetch_job, "interval", seconds=60, next_run_time=datetime.now(timezone.utc))
    # Top-scorer refresh every 5 min — CCTV updates less often than match data
    scheduler.add_job(run_scorer_refresh_job, "interval", minutes=5, next_run_time=datetime.now(timezone.utc))
    # v2.1: 阵容刷新每 3 分钟 (赛前 2h 内 + 赛中)
    scheduler.add_job(run_lineup_fetch_job, "interval", minutes=3, next_run_time=datetime.now(timezone.utc))
    scheduler.start()
    yield
    scheduler.shutdown()


def run_prediction_job() -> None:
    """Recompute and persist champion predictions."""
    try:
        preds = analyzer.compute_predictions()
        analyzer.persist_predictions(preds)
        print(f"[{datetime.now(timezone.utc).isoformat()}] predictions refreshed")
    except Exception as e:
        print(f"prediction job failed: {e}")


LIVE_LAST_RUN: dict = {"ts": None, "updated": 0, "ok": False, "error": None}
LINEUP_LAST_RUN: dict = {"ts": None, "stored": 0, "candidates": 0, "ok": False}


def run_lineup_fetch_job() -> None:
    """v2.1: 抓取阵容 (赛前 2h 内 + 赛中), 每 3 分钟. ESPN 阵容赛前 ~1h 公布."""
    try:
        result = lineup_scraper.fetch_and_store_lineups()
        LINEUP_LAST_RUN["ts"] = datetime.now(timezone.utc).isoformat()
        LINEUP_LAST_RUN["candidates"] = result.get("candidates", 0)
        LINEUP_LAST_RUN["stored"] = result.get("stored", 0)
        LINEUP_LAST_RUN["ok"] = True
    except Exception as e:
        LINEUP_LAST_RUN["ok"] = False
        LINEUP_LAST_RUN["ts"] = datetime.now(timezone.utc).isoformat()
        print(f"lineup fetch job failed: {e}")


def run_live_fetch_job() -> None:
    """Fetch live match data from CCTV (primary) + ESPN (fallback)."""
    try:
        result = cctv_espn_live.run_once()
        LIVE_LAST_RUN["ts"] = datetime.now(timezone.utc).isoformat()
        LIVE_LAST_RUN["ok"] = result is not None
        if result:
            LIVE_LAST_RUN["updated"] = LIVE_LAST_RUN.get("updated", 0) + result["updated"]
        LIVE_LAST_RUN["error"] = None
        if result and result["updated"] > 0:
            print(f"[{LIVE_LAST_RUN['ts']}] live fetch: updated {result['updated']}, new finished {result['newly_finished']}")
    except Exception as e:
        LIVE_LAST_RUN["error"] = str(e)
        LIVE_LAST_RUN["ts"] = datetime.now(timezone.utc).isoformat()
        print(f"live fetch job failed: {e}")


SCORER_LAST_RUN: dict = {"ts": None, "ok": False, "count": 0, "src": None, "error": None}


def run_scorer_refresh_job() -> None:
    """Refresh the top-scorers cache from CCTV (with DB fallback)."""
    try:
        data = cctv_scorers.refresh_cache(limit=20)
        SCORER_LAST_RUN["ts"] = datetime.now(timezone.utc).isoformat()
        SCORER_LAST_RUN["ok"] = True
        SCORER_LAST_RUN["count"] = len(data)
        SCORER_LAST_RUN["src"] = data[0]["source"] if data else None
        SCORER_LAST_RUN["error"] = None
    except Exception as e:
        SCORER_LAST_RUN["ts"] = datetime.now(timezone.utc).isoformat()
        SCORER_LAST_RUN["ok"] = False
        SCORER_LAST_RUN["error"] = str(e)
        print(f"scorer refresh job failed: {e}")


app = FastAPI(
    title="WorldCup 2026 Analytics Hub",
    description="Real-time 2026 FIFA World Cup data + AI champion predictions",
    version="1.0.0",
    lifespan=lifespan,
)

# Static assets
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
async def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/bracket", include_in_schema=False)
async def bracket_page() -> FileResponse:
    """Standalone bracket visualisation page (v4)."""
    return FileResponse(STATIC_DIR / "bracket.html")


@app.get("/favicon.ico", include_in_schema=False)
async def favicon() -> FileResponse:
    return FileResponse(STATIC_DIR / "trophy.jpeg", media_type="image/jpeg")


@app.get("/api/health")
async def health() -> dict:
    last = db().execute("SELECT MAX(last_updated) as lu FROM matches").fetchone()
    return {
        "status": "ok",
        "version": "v2",
        "now_utc": datetime.now(timezone.utc).isoformat(),
        "last_data_update": last["lu"] if last else None,
        "db_size_kb": round(DB_PATH.stat().st_size / 1024, 1) if DB_PATH.exists() else 0,
    }


@app.get("/api/summary")
async def summary() -> dict:
    """Hero KPIs: total matches, finished, goals, teams, days to final."""
    conn = db()
    total = conn.execute("SELECT COUNT(*) FROM matches").fetchone()[0]
    finished = conn.execute("SELECT COUNT(*) FROM matches WHERE status='finished'").fetchone()[0]
    goals = conn.execute("SELECT COALESCE(SUM(home_score+away_score),0) FROM matches WHERE status='finished'").fetchone()[0]
    teams = conn.execute("SELECT COUNT(*) FROM teams").fetchone()[0]
    upcoming = conn.execute("SELECT COUNT(*) FROM matches WHERE status='scheduled' AND match_date<=date('now','+1 day')").fetchone()[0]
    # Days to final
    final_date = datetime.fromisoformat("2026-07-19").replace(tzinfo=timezone.utc)
    days_to_final = (final_date - datetime.now(timezone.utc)).days
    # Top scorers (优先用 CCTV 缓存, 数据全; 失败回退到本地 DB goals_json)
    top5: list[tuple[str, int]] = []
    try:
        from scrapers import cctv_scorers as _cs
        _csc = _cs.fetch_scorers(limit=5, prefer="cctv") or _cs.fetch_scorers(limit=5, prefer="db")
        for s_ in _csc:
            top5.append((s_["player"], s_["goals"]))
        # 兼容旧格式 (player + team), 这里 team 由前端再补
        scorer_team = {row["player"]: row["team"] for row in _csc} if _csc else {}
    except Exception:
        scorer_team = {}
        scorer_count: dict[str, int] = {}
        for row in conn.execute("SELECT goals_json FROM matches WHERE status='finished' AND goals_json IS NOT NULL AND goals_json<>'[]'").fetchall():
            for g in json.loads(row["goals_json"]):
                scorer_team[g["scorer"]] = g["team"]
                scorer_count[g["scorer"]] = scorer_count.get(g["scorer"], 0) + 1
        top5 = sorted(scorer_count.items(), key=lambda x: x[1], reverse=True)[:5]
    conn.close()
    return {
        "total_matches": total,
        "finished_matches": finished,
        "scheduled_matches": total - finished,
        "total_goals": goals,
        "teams_count": teams,
        "upcoming_24h": upcoming,
        "days_to_final": max(0, days_to_final),
        "top_scorers": [{"player": p, "team": scorer_team.get(p, ""), "goals": c} for p, c in top5],
        "tournament": {
            "name": "FIFA World Cup 2026",
            "host": "USA / Canada / Mexico",
            "edition": 23,
            "teams": 48,
            "matches": 104,
            "groups": 12,
            "stadiums": 16,
        }
    }


@app.get("/api/groups")
async def groups() -> dict:
    conn = db()
    out = {}
    for row in conn.execute("SELECT * FROM teams ORDER BY group_name, fifa_rank").fetchall():
        out.setdefault(row["group_name"], []).append(dict(row))
    conn.close()
    return out


@app.get("/api/standings")
async def standings() -> dict:
    """Compute live standings from finished matches. Each group returns teams sorted by pts,gd,gf."""
    conn = db()
    # Reset + recompute
    standings_raw: dict[str, list[dict]] = {}
    for row in conn.execute("SELECT name, group_name FROM teams ORDER BY group_name, fifa_rank").fetchall():
        standings_raw.setdefault(row["group_name"], []).append({
            "team": row["name"], "played": 0, "won": 0, "draw": 0, "lost": 0,
            "gf": 0, "ga": 0, "gd": 0, "pts": 0, "form": [],
        })
    for row in conn.execute("""
        SELECT group_name, home_team, away_team, home_score, away_score
        FROM matches WHERE status='finished' AND group_name IS NOT NULL
        ORDER BY match_date
    """).fetchall():
        g, h, a, hs, as_ = row["group_name"], row["home_team"], row["away_team"], row["home_score"], row["away_score"]
        for team_name, gf, ga in ((h, hs, as_), (a, as_, hs)):
            for entry in standings_raw[g]:
                if entry["team"] == team_name:
                    entry["played"] += 1
                    entry["gf"] += gf
                    entry["ga"] += ga
                    if gf > ga:
                        entry["won"] += 1
                        entry["pts"] += 3
                        entry["form"].append("W")
                    elif gf == ga:
                        entry["draw"] += 1
                        entry["pts"] += 1
                        entry["form"].append("D")
                    else:
                        entry["lost"] += 1
                        entry["form"].append("L")
                    entry["gd"] = entry["gf"] - entry["ga"]
                    break
    # Sort each group
    for g in standings_raw:
        standings_raw[g].sort(key=lambda x: (x["pts"], x["gd"], x["gf"]), reverse=True)
        for i, e in enumerate(standings_raw[g]):
            e["position"] = i + 1
            e["qualified"] = i < 2  # top 2 advance directly
            e["form_str"] = "".join(e["form"][-3:])
    conn.close()
    return standings_raw


@app.get("/api/matches")
async def matches(
    group: str | None = None,
    status: str | None = None,
    date: str | None = None,
    limit: int = Query(200, le=500),
) -> list[dict]:
    conn = db()
    q = "SELECT * FROM matches WHERE 1=1"
    params: list = []
    if group:
        q += " AND group_name = ?"
        params.append(group)
    if status:
        q += " AND status = ?"
        params.append(status)
    if date:
        q += " AND match_date = ?"
        params.append(date)
    q += " ORDER BY match_date, match_time LIMIT ?"
    params.append(limit)
    rows = conn.execute(q, params).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        try:
            d["goals"] = json.loads(d.pop("goals_json") or "[]")
        except Exception:
            d["goals"] = []
        out.append(d)
    conn.close()
    return out


@app.get("/api/matches/live")
async def matches_live() -> dict:
    """Matches in next 24h + currently live + recently kicked-off (last 6h).

    v2.1 修复 (date range):
      原 SQL 只查 match_date IN [今天, 明天], 会漏掉"昨天开赛但刚结束"的比赛
      (e.g. M016 巴拉圭 vs 土耳其 2026-06-19 23:00 UTC). 现扩展窗口:
        - 已开赛 ≤ 6h  (status='live' 或 'finished')
        - match_date 范围 [昨天, 明天+1]
      然后 _infer_live_status() 把 status='scheduled' 但已过开球时间的提升为 'live'/'finished'.
    """
    conn = db()
    now = datetime.now(timezone.utc)
    # 6h 前 (含跨日, 最多回看 1 天)
    window_start = (now - timedelta(hours=6)).date()
    window_end = (now + timedelta(days=1)).date()
    rows = conn.execute("""
        SELECT * FROM matches
        WHERE match_date BETWEEN ? AND ?
           OR status='live'
        ORDER BY match_date, match_time
    """, (window_start.isoformat(), window_end.isoformat())).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        try:
            d["goals"] = json.loads(d.pop("goals_json") or "[]")
        except Exception:
            d["goals"] = []
        # 兜底: 用开球时间推算 'live' / 'finished', 避免前端误判
        d["status"] = _infer_live_status(d)
        out.append(d)
    conn.close()
    return {"count": len(out), "matches": out}


# 与 scrapers/openfootball_live.py:STALE_LIVE_WINDOW 保持一致
_STALE_LIVE_WINDOW = timedelta(hours=2)


def _infer_live_status(m: dict) -> str:
    """根据开球时间推断比赛状态 (兜底).

    规则 (DB status 已是 'finished' / 'live' 则原样返回):
      - 'scheduled' + 距开球 < 0                → 'scheduled'
      - 'scheduled' + 0 <= 距开球 < 2h          → 'live'
      - 'scheduled' + 距开球 >= 2h              → 'finished' (兜底, 等下次 scraper 校正)

    时间字段 match_date (YYYY-MM-DD) + match_time (HH:MM, UTC) 直接拼 ISO, 附加 UTC tz.
    """
    raw = m.get("status") or "scheduled"
    if raw in ("finished", "live"):
        return raw
    md, mt = m.get("match_date"), m.get("match_time")
    if not md or not mt:
        return raw
    try:
        kickoff = datetime.fromisoformat(f"{md}T{mt}:00").replace(tzinfo=timezone.utc)
    except ValueError:
        return raw
    delta = datetime.now(timezone.utc) - kickoff
    if delta >= _STALE_LIVE_WINDOW:
        return "finished"
    if delta >= timedelta(0):
        return "live"
    return "scheduled"


@app.get("/api/matches/{match_id}")
async def match_detail(match_id: str) -> dict:
    conn = db()
    row = conn.execute("SELECT * FROM matches WHERE match_id=?", (match_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(404, "match not found")
    d = dict(row)
    try:
        d["goals"] = json.loads(d.pop("goals_json") or "[]")
    except Exception:
        d["goals"] = []
    return d


# ── v2.1: 阵容 (lineup) 端点 ────────────────────────────────────────────────
@app.get("/api/matches/{match_id}/lineup")
async def match_lineup(match_id: str) -> dict:
    """Return lineups for a match: {home: {formation, coach, players[]}, away: {...}}.

    数据源: ESPN summary API. 写库逻辑: scrapers/lineup.py.
    通常赛前 1h 公布; 已完赛的比赛一次性回填.
    """
    conn = db()
    rows = conn.execute(
        "SELECT side, formation, coach_name, players_json, source, fetched_at FROM lineups WHERE match_id=?",
        (match_id,),
    ).fetchall()
    if not rows:
        conn.close()
        raise HTTPException(404, "lineup not yet available (尚未公布或不在 ESPN 列表)")
    out: dict = {"match_id": match_id, "home": None, "away": None}
    for side, formation, coach, pjson, source, fetched_at in rows:
        try:
            players = json.loads(pjson or "[]")
        except Exception:
            players = []
        out[side] = {
            "formation": formation,
            "coach": coach,
            "players": players,
            "source": source,
            "fetched_at": fetched_at,
        }
    conn.close()
    return out


@app.post("/api/admin/refresh_lineups")
async def refresh_lineups() -> dict:
    """手动触发阵容刷新. 用于测试或紧急情况."""
    stats = lineup_scraper.fetch_and_store_lineups()
    return {"ok": True, **stats}


# ── v4 — per-match AI prediction endpoint ──────────────────────────────────────
@app.get("/api/matches/{match_id}/prediction")
async def match_prediction(match_id: str) -> dict:
    """Single-match AI prediction.

    Returns the resolved prediction (winner, score, win probabilities,
    score distribution) for a given match_id.

    For group-stage matches this is computed by Monte-Carlo over
    5000 iterations. For knockout matches, predictions are derived by
    resolving bracket slot placeholders (e.g. "1A" → strongest team
    in group A). Later knockout rounds (R16+) whose teams reference
    earlier winners return `predicted_winner = "TBD"` until those
    upstream matches resolve.

    Response shape:
        {
          "match_id": "M019",
          "round": "Group F Matchday 1",
          "match_date": "2026-06-14",
          "match_time": "20:00",
          "venue": "AT&T Stadium",
          "status": "scheduled",
          "home_team": "Netherlands",
          "away_team": "Japan",
          "home_win_prob": 41.5,
          "draw_prob": 29.7,
          "away_win_prob": 28.8,
          "predicted_home_score": 1,
          "predicted_away_score": 1,
          "predicted_winner": "Netherlands",
          "predicted_score": "1-1",
          "score_distribution": {"1-1": 18.0, "2-1": 13.0, ...},
          "simulated_count": 5000,
          "is_knockout": false,
          "resolved_teams": true
        }
    """
    conn = db()
    row = conn.execute("SELECT * FROM matches WHERE match_id=?", (match_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(404, "match not found")
    d = dict(row)

    # Decide whether this match is knockout (no group_name) AND has
    # placeholder team names — those need the resolved names from the
    # analyzer so the front-end doesn't show "1A vs 2B" literally.
    is_knockout = d.get("group_name") is None
    placeholder_re = re.compile(r"^(?:[123][A-L](?:\s*\(alt\))?|3rd-[A-L]+|W\d+|L\d+|TBD.*)$")
    h_is_placeholder = bool(placeholder_re.match(d.get("home_team") or ""))
    a_is_placeholder = bool(placeholder_re.match(d.get("away_team") or ""))

    # Score distribution JSON
    score_dist = {}
    if d.get("score_distribution_json"):
        try:
            score_dist = json.loads(d["score_distribution_json"])
        except Exception:
            score_dist = {}

    # Compose response
    ph = d.get("predicted_home_score")
    pa = d.get("predicted_away_score")
    pw = d.get("predicted_winner")
    out = {
        "match_id": d["match_id"],
        "round": d.get("round"),
        "match_date": d.get("match_date"),
        "match_time": d.get("match_time"),
        "venue": d.get("venue"),
        "status": d.get("status"),
        "home_team": d.get("home_team"),
        "away_team": d.get("away_team"),
        "home_win_prob": d.get("home_win_prob"),
        "draw_prob": d.get("draw_prob"),
        "away_win_prob": d.get("away_win_prob"),
        "predicted_home_score": ph,
        "predicted_away_score": pa,
        "predicted_winner": pw,
        "predicted_score": f"{ph}-{pa}" if ph is not None and pa is not None else None,
        "score_distribution": score_dist,
        "simulated_count": 5000 if (not is_knockout and pw not in (None, "TBD")) else 0,
        "is_knockout": is_knockout,
        "resolved_teams": not (h_is_placeholder or a_is_placeholder),
    }

    # If this is a knockout match with placeholder teams AND we have
    # a real predicted_winner, surface the resolved team names so the
    # front-end can display them.
    if is_knockout and pw and pw not in (None, "TBD", "draw"):
        # For matches where BOTH sides are resolvable bracket slots
        # (e.g. M073 "2A" vs "2B"), the analyzer has already resolved
        # the home/away names internally; we recompute them here so
        # the API response is self-contained.
        try:
            teams = analyzer.load_teams(conn)
            out["home_team"] = _resolve_bracket_slot(d.get("home_team"), teams) or d.get("home_team")
            out["away_team"] = _resolve_bracket_slot(d.get("away_team"), teams) or d.get("away_team")
            out["resolved_teams"] = True
        except Exception:
            pass
    conn.close()
    return out


# ── v4 — knockout matches endpoint ────────────────────────────────────────────
@app.get("/api/knockout")
async def knockout() -> dict:
    """All 32 knockout matches grouped by round.

    Response:
        {
          "total": 32,
          "rounds": {
            "Round of 32": [match1, match2, ...],   # 16 matches
            "Round of 16": [...],                    # 8 matches
            "Quarter-finals": [...],                 # 4 matches
            "Semi-finals": [...],                    # 2 matches
            "Third place": [...],                    # 1 match
            "Final": [...]                           # 1 match
          },
          "by_round": {
            "Round of 32": 16, ... }
        }
    """
    conn = db()
    rows = conn.execute("""
        SELECT match_id, round, matchday, match_date, match_time, home_team, away_team,
               venue, status, predicted_winner, predicted_home_score, predicted_away_score,
               home_win_prob, away_win_prob
        FROM matches
        WHERE round IN ('Round of 32','Round of 16','Quarter-finals',
                        'Semi-finals','Third place','Final')
        ORDER BY
            CASE round
                WHEN 'Round of 32' THEN 1
                WHEN 'Round of 16' THEN 2
                WHEN 'Quarter-finals' THEN 3
                WHEN 'Semi-finals' THEN 4
                WHEN 'Third place' THEN 5
                WHEN 'Final' THEN 6
            END,
            match_date, match_time
    """).fetchall()
    conn.close()

    rounds_order = ["Round of 32", "Round of 16", "Quarter-finals",
                    "Semi-finals", "Third place", "Final"]
    by_round: dict[str, list[dict]] = {r: [] for r in rounds_order}
    for row in rows:
        r = dict(row)
        by_round.setdefault(r["round"], []).append(r)

    return {
        "total": sum(len(v) for v in by_round.values()),
        "rounds": by_round,
        "by_round_count": {k: len(v) for k, v in by_round.items() if v},
        "round_order": [k for k in rounds_order if by_round.get(k)],
    }


# ── v4 — bracket endpoint (full structure with AI predictions) ─────────────────
@app.get("/api/bracket")
async def bracket() -> dict:
    """Tournament bracket structure (left-to-right: R32 → R16 → QF → SF → Final)
    with AI predictions per match.

    Each node is positioned by `col` (0=R32, 1=R16, 2=QF, 3=SF, 4=Final)
    and `row` (vertical position within the round). Wires (edges) between
    rounds describe the bracket flow.

    Response shape:
        {
          "tournament": "FIFA World Cup 2026",
          "rounds": [
            {"name": "Round of 32", "col": 0, "count": 16},
            {"name": "Round of 16", "col": 1, "count": 8},
            ...
          ],
          "matches": [
            {
              "match_id": "M073", "round": "Round of 32", "col": 0, "row": 0,
              "home_team": "2A",  "away_team": "2B",
              "home_team_resolved": "Czechia", "away_team_resolved": "Switzerland",
              "predicted_winner": "Switzerland",
              "predicted_score": "1-2",
              "home_win_prob": 47.43, "away_win_prob": 52.57,
              "match_date": "2026-06-28", "venue": "Toronto Stadium",
              "status": "scheduled",
              "resolved_teams": true,
              "winner_label": "Switzerland"
            },
            ...
          ],
          "wires": [
            {"from": "M073", "to": "M089"},   # R32 → R16 mapping (placeholder)
            ...
          ],
          "generated_at": "2026-06-14T...Z"
        }
    """
    import re as _re
    conn = db()
    rows = conn.execute("""
        SELECT match_id, round, match_date, match_time, home_team, away_team,
               venue, status, predicted_winner, predicted_home_score,
               predicted_away_score, home_win_prob, draw_prob, away_win_prob,
               score_distribution_json
        FROM matches
        WHERE round IN ('Round of 32','Round of 16','Quarter-finals',
                        'Semi-finals','Third place','Final')
        ORDER BY
            CASE round
                WHEN 'Round of 32' THEN 1
                WHEN 'Round of 16' THEN 2
                WHEN 'Quarter-finals' THEN 3
                WHEN 'Semi-finals' THEN 4
                WHEN 'Third place' THEN 5
                WHEN 'Final' THEN 6
            END,
            match_date, match_time
    """).fetchall()
    teams = analyzer.load_teams(conn)
    conn.close()

    placeholder_re = _re.compile(r"^(?:[123][A-L](?:\s*\(alt\))?|3rd-[A-L]+|W\d+|L\d+|TBD.*)$")

    rounds_meta = [
        {"name": "Round of 32", "col": 0, "count": 16},
        {"name": "Round of 16", "col": 1, "count": 8},
        {"name": "Quarter-finals", "col": 2, "count": 4},
        {"name": "Semi-finals", "col": 3, "count": 2},
        {"name": "Final", "col": 4, "count": 1},
    ]
    round_col = {r["name"]: r["col"] for r in rounds_meta}
    round_counts = {r["name"]: r["count"] for r in rounds_meta}

    # Group by round, assign row index (top to bottom within the round)
    by_round: dict[str, list[dict]] = {}
    for r in rows:
        d = dict(r)
        by_round.setdefault(d["round"], []).append(d)

    nodes: list[dict] = []
    for rnd_name, items in by_round.items():
        col = round_col.get(rnd_name, -1)
        for idx, m in enumerate(items):
            h = m["home_team"]
            a = m["away_team"]
            h_resolved = _resolve_bracket_slot(h, teams)
            a_resolved = _resolve_bracket_slot(a, teams)
            ph = m.get("predicted_home_score")
            pa = m.get("predicted_away_score")
            pw = m.get("predicted_winner")
            nodes.append({
                "match_id": m["match_id"],
                "round": rnd_name,
                "col": col,
                "row": idx,
                "match_date": m["match_date"],
                "match_time": m["match_time"],
                "venue": m["venue"],
                "status": m["status"],
                "home_team": h,
                "away_team": a,
                "home_team_resolved": h_resolved or h,
                "away_team_resolved": a_resolved or a,
                "predicted_winner": pw,
                "predicted_score": f"{ph}-{pa}" if ph is not None and pa is not None else None,
                "home_win_prob": m.get("home_win_prob"),
                "away_win_prob": m.get("away_win_prob"),
                "draw_prob": m.get("draw_prob"),
                "resolved_teams": bool(h_resolved and a_resolved),
                "is_placeholder": bool(placeholder_re.match(h) or placeholder_re.match(a)),
                "winner_label": pw if pw and pw not in (None, "TBD") else "TBD",
            })

    # Wires — connect R32 → R16 → QF → SF → Final.  FIFA's standard
    # bracket ordering: M073+M074 → M089, M075+M076 → M090, ... etc.
    # R32 pairs: (M073,M074)->M089, (M075,M076)->M090, (M077,M078)->M091,
    #            (M079,M080)->M092, (M081,M082)->M093, (M083,M084)->M094,
    #            (M085,M086)->M095, (M087,M088)->M096
    # R16 pairs: (M089,M090)->M097, (M091,M092)->M098,
    #            (M093,M094)->M099, (M095,M096)->M100
    # QF pairs:  (M097,M098)->M101, (M099,M100)->M102
    # SF:       M101/M102 → M104 (Final); SF losers → M103 (3rd place)
    wires = [
        {"from": "M073", "to": "M089"},
        {"from": "M074", "to": "M089"},
        {"from": "M075", "to": "M090"},
        {"from": "M076", "to": "M090"},
        {"from": "M077", "to": "M091"},
        {"from": "M078", "to": "M091"},
        {"from": "M079", "to": "M092"},
        {"from": "M080", "to": "M092"},
        {"from": "M081", "to": "M093"},
        {"from": "M082", "to": "M093"},
        {"from": "M083", "to": "M094"},
        {"from": "M084", "to": "M094"},
        {"from": "M085", "to": "M095"},
        {"from": "M086", "to": "M095"},
        {"from": "M087", "to": "M096"},
        {"from": "M088", "to": "M096"},
        {"from": "M089", "to": "M097"},
        {"from": "M090", "to": "M097"},
        {"from": "M091", "to": "M098"},
        {"from": "M092", "to": "M098"},
        {"from": "M093", "to": "M099"},
        {"from": "M094", "to": "M099"},
        {"from": "M095", "to": "M100"},
        {"from": "M096", "to": "M100"},
        {"from": "M097", "to": "M101"},
        {"from": "M098", "to": "M101"},
        {"from": "M099", "to": "M102"},
        {"from": "M100", "to": "M102"},
        {"from": "M101", "to": "M104"},
        {"from": "M102", "to": "M104"},
        {"from": "M101", "to": "M103"},  # SF losers → 3rd place
        {"from": "M102", "to": "M103"},
    ]

    return {
        "tournament": "FIFA World Cup 2026",
        "rounds": rounds_meta,
        "matches": nodes,
        "wires": wires,
        "total_matches": len(nodes),
        "predicted_matches": sum(1 for n in nodes if n["predicted_winner"] and n["predicted_winner"] != "TBD"),
        "tbd_matches": sum(1 for n in nodes if n["predicted_winner"] == "TBD"),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


# ── helpers used by /api/matches/{id}/prediction and /api/bracket ──────────────
def _resolve_bracket_slot(slot: str, teams: dict) -> str | None:
    """Resolve a "1A"/"2B"/"3C"-style slot to a real team name.

    Returns None for unresolvable slots (3rd place, winner references,
    etc.). Used by both /api/matches/{id}/prediction and /api/bracket
    to surface human-readable team names even before the group stage
    has resolved.
    """
    import re as _re
    if not slot:
        return None
    m = _re.match(r"^(?P<rank>[123])(?:\s*\(alt\))?(?P<grp>[A-L])$", slot.strip())
    if not m:
        return None
    rank = int(m["rank"])
    grp = m["grp"]
    members = [(t["name"], analyzer.team_strength(t)) for t in teams.values() if t["group_name"] == grp]
    if not members:
        return None
    members_sorted = sorted(members, key=lambda x: x[1], reverse=True)
    if rank - 1 >= len(members_sorted):
        return None
    return members_sorted[rank - 1][0]  


@app.get("/api/teams")
async def teams(group: str | None = None) -> list[dict]:
    conn = db()
    if group:
        rows = conn.execute("SELECT * FROM teams WHERE group_name=? ORDER BY fifa_rank", (group,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM teams ORDER BY group_name, fifa_rank").fetchall()
    out = [dict(r) for r in rows]
    conn.close()
    return out


@app.get("/api/teams/{name}")
async def team_detail(name: str) -> dict:
    conn = db()
    row = conn.execute("SELECT * FROM teams WHERE name=?", (name,)).fetchone()
    if not row:
        raise HTTPException(404, "team not found")
    info = dict(row)
    # Upcoming + recent matches
    upcoming = conn.execute("""
        SELECT * FROM matches WHERE (home_team=? OR away_team=?) AND status='scheduled'
        ORDER BY match_date LIMIT 5
    """, (name, name)).fetchall()
    finished = conn.execute("""
        SELECT * FROM matches WHERE (home_team=? OR away_team=?) AND status='finished'
        ORDER BY match_date DESC LIMIT 5
    """, (name, name)).fetchall()
    info["upcoming"] = [dict(r) for r in upcoming]
    info["recent_results"] = [dict(r) for r in finished]
    # Prediction
    pred = conn.execute("SELECT * FROM predictions WHERE team=?", (name,)).fetchone()
    info["prediction"] = dict(pred) if pred else None
    conn.close()
    return info


@app.get("/api/predictions")
async def predictions(limit: int = Query(48, le=48)) -> list[dict]:
    conn = db()
    rows = conn.execute("""
        SELECT p.*, t.group_name, t.fifa_rank, t.confederation
        FROM predictions p
        JOIN teams t ON t.name = p.team
        ORDER BY p.champion_prob DESC, t.fifa_rank ASC LIMIT ?
    """, (limit,)).fetchall()
    out = [dict(r) for r in rows]
    conn.close()
    # Add final_score
    for p in out:
        mc = p.get("champion_prob") or 0
        hs = max(0.0, min(100.0, 100.0 - (p.get("fifa_rank", 50) - 1) * 1.5))
        p["final_score"] = round(0.7 * mc + 0.3 * hs, 2)
    # Sort in Python by (champion_prob desc, final_score desc) for stable,
    # deterministic ordering even when multiple teams share the same
    # champion_prob. The SQL above provides the primary sort key; this
    # Python pass handles the tiebreaker cleanly.
    out.sort(key=lambda p: (-(p.get("champion_prob") or 0), -(p.get("final_score") or 0)))
    return out


@app.get("/api/history")
async def history() -> list[dict]:
    conn = db()
    rows = conn.execute("SELECT * FROM world_cup_history ORDER BY year").fetchall()
    out = [dict(r) for r in rows]
    conn.close()
    return out


@app.get("/api/venues")
async def venues() -> list[dict]:
    conn = db()
    rows = conn.execute("SELECT * FROM venues ORDER BY name").fetchall()
    out = [dict(r) for r in rows]
    # Count matches per venue
    counts = dict(conn.execute("SELECT venue, COUNT(*) FROM matches GROUP BY venue").fetchall())
    for v in out:
        v["match_count"] = counts.get(v["name"], 0)
    conn.close()
    return out


@app.post("/api/admin/refresh")
async def refresh() -> dict:
    """Manually trigger prediction recompute."""
    run_prediction_job()
    return {"status": "ok", "ts": datetime.now(timezone.utc).isoformat()}


@app.get("/api/live/status")
async def live_status() -> dict:
    """Status of the live data fetcher (last run, error, count)."""
    return LIVE_LAST_RUN


@app.post("/api/live/fetch")
async def live_fetch() -> dict:
    """Manually trigger a live data fetch (admin)."""
    run_live_fetch_job()
    return {"status": "ok", "last_run": LIVE_LAST_RUN}


@app.get("/api/scorers")
async def scorers(limit: int = Query(20, ge=1, le=100), source: str = Query("auto")) -> dict:
    """Full top-scorers list (CCTV style — multiple columns).

    Query params:
        limit  : max scorers to return (default 20, max 100)
        source : "auto" (default, CCTV-first with DB fallback),
                 "cctv"  (force CCTV, may return [] if API down),
                 "db"    (aggregate from local matches.goals_json)

    Returns:
        {
          "count": 16,
          "source": "cctv",
          "ts": "2026-06-14T...Z",
          "scorers": [
            {"rank": 1, "player": "巴洛贡", "player_en": "Balogun",
             "team": "美国", "team_en": "USA",
             "goals": 2, "penalties": 0, "matches": 1,
             "mins_per_goal": null},
            ...
          ]
        }
    """
    prefer = "cctv" if source == "auto" else source
    data = cctv_scorers.fetch_scorers(limit=limit, prefer=prefer)
    src = data[0]["source"] if data else (prefer if prefer != "auto" else "cctv")
    return {
        "count": len(data),
        "source": src,
        "ts": SCORER_LAST_RUN.get("ts"),
        "scorers": data,
    }


@app.get("/api/scorers/status")
async def scorers_status() -> dict:
    """Status of the scorer fetcher (last run, error, count, source)."""
    return SCORER_LAST_RUN


@app.post("/api/scorers/refresh")
async def scorers_refresh() -> dict:
    """Manually trigger a scorer refresh (admin)."""
    run_scorer_refresh_job()
    return {"status": "ok", "last_run": SCORER_LAST_RUN}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8001, reload=False)
