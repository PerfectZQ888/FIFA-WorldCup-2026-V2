"""Champion probability predictor — Monte Carlo + historical similarity.

Pure-Python, no ML libs (per v3 plan: data too small for LightGBM, MC is enough).
Re-runs nightly at 23:00 via APScheduler.

== Strength model (v5 — 多因子综合) ==
team_strength = weighted blend of:
  1. FIFA rank             (W_RANK,     权重 0.40) — 过去 4 年 A 级赛表现
  2. World Cup 历史成绩      (W_HISTORY,  权重 0.20) — 22 届冠/亚/季/殿（时间衰减）
  3. 当前球员阵容评分        (W_SQUAD,    权重 0.30) — 当前 26 人名单实力
  4. 加成 (host/卫冕/联盟)   (W_BOOSTS,   权重 0.10) — 不可估的环境因子

权重之和 = 1.00。修改权重需保持 sum=1.0，否则 strength 量纲会偏移
Poisson 进球分布。

== Data sources ==
  - teams 表        rank/host/champion/confederation
  - world_cup_history 表  22 行
  - team_squads 表  48 行，由 scripts/seed_squads.py 维护
"""
from __future__ import annotations
import math
import random
import sqlite3
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DB_PATH = Path("data/wc2026.db")
N_SIM = 5_000  # Monte Carlo iterations (kept modest for fast nightly runs)

# ── 综合实力 4 因子权重（和必须 = 1.00） ────────────────────────────────────
W_RANK    = 0.40   # FIFA 排名（近 4 年战绩）
W_HISTORY = 0.20   # 世界杯历史成绩
W_SQUAD   = 0.30   # 当前球员阵容实力
W_BOOSTS  = 0.10   # 主场/卫冕/联盟加成

# 历史成绩：时间衰减系数（每 4 年衰减为前一届的 92%）
HIST_DECAY = 0.92
HIST_LATEST_YEAR = 2022
# 冠 / 亚 / 季 / 殿 各得几分
HIST_POINTS = {"champion": 4, "runner_up": 3, "third": 2, "fourth": 1}
# 历史归一化基线：让"无前四史"的队仍有 0.20 的历史强度，避免被极端惩罚
HIST_BASELINE = 0.20

# 阵容评分：种子覆盖不到的队（万一 seed_squads 未运行/有遗漏）的 fallback
SQUAD_FALLBACK = 0.50

# ── Tunable boost coefficients ───────────────────────────────────────────────
# Host nation boost. Historical WC data (1930–2022) shows host teams
# advance from the group stage ~67% of the time vs. ~50% for non-hosts
# (~17 percentage-point lift). Translating that to a strength bonus that
# moves a typical mid-tier team by ~5-7 points is much smaller than the
# 0.15 we previously used — that one was lifting Mexico/USA/Canada into
# top-6 and over-stating their champion odds by 1.5–2x.
# 0.08 aligns with FIFA's 2023 working paper on host advantage.
HOST_BOOST = 0.08

# Defending champion bump. Last-4 cycle data: champions always reach R16,
# ~75% reach QF. Slightly stronger than host boost because the trophy
# effect is real (no travel, deeper squad, plus motivation).
DEFENDING_CHAMPION_BOOST = 0.10

# Confederation strength bonus. UEFA/CONMEBOL teams historically win more
# often than the field; OFC teams never have; others neutral.
CONFEDERATION_BONUS: dict[str, float] = {
    "UEFA": 0.05,
    "CONMEBOL": 0.05,
    "CONCACAF": 0.02,
    "AFC": 0.0,
    "CAF": 0.0,
    "OFC": -0.05,
}

# ── 进球模型参数（v5：Poisson + 强弱差放大） ────────────────────────────────
# 旧 Gaussian 模型 σ=0.9 让所有比赛压在 0-3 球区间，强弱悬殊也只能预测 2-1。
# 改 Poisson（足球进球本质是事件计数过程，符合 Poisson）+ 放大强弱差对 λ
# 的影响，让大胜场次（4+ 球差）能像历史世界杯一样出现（如西班牙 7-0 哥斯达
# 黎加、英格兰 6-1 巴拿马、葡萄牙 7-0 朝鲜）。
GOALS_BASE_HOME    = 1.4   # 等强度时 home 期望进球
GOALS_BASE_AWAY    = 1.1   # 等强度时 away 期望进球
GOALS_BASE_KO_HOME = 1.5   # 淘汰赛主队期望（节奏更开放，进球略多）
GOALS_BASE_KO_AWAY = 1.2
ATK_LIFT           = 6.5   # 强队的攻击力放大（每 0.1 强度差 → λ 加 0.65）
DEF_DRAG           = 3.0   # 强队把弱队的进球压下来的系数（不对称：被压<自加）
LAMBDA_MIN         = 0.12  # 弱队 λ 下限（防止永远 0 球）
LAMBDA_MAX         = 6.0   # 强队 λ 上限（允许历史上的 7-0/8-0 极端比分出现）

# 新军压力惩罚：appearances <= 1 的队（首/次参赛）面对世界杯压力易紧张，
# 防守崩塌概率明显高于成熟队（参考 2002 中国队、2010 朝鲜 7-0、2022 加拿
# 大首战、卡塔尔 2-0 厄瓜多尔后两连败 0-7）。
NEWCOMER_PENALTY      = 0.30   # 新军每场期望进球 -0.30
NEWCOMER_DEFENSE_PENALTY = 0.50  # 对手期望进球 +0.50（防线被打穿）
NEWCOMER_THRESHOLD    = 1      # appearances <= 1 视为新军

# 旧国家名归并到 2026 名册的当代名（World Cup history 数据里仍是冷战时期国名）
HISTORY_ALIAS = {
    "West Germany":   "Germany",
    "East Germany":   "Germany",
    "Soviet Union":   "Russia",
    "Yugoslavia":     "Serbia",
    "Czechoslovakia": "Czechia",
}


def rank_to_strength(rank: int) -> float:
    """FIFA rank → base strength. 1.0 = top team, decays with log."""
    return 1.0 / (1.0 + math.log(max(1, rank) + 4))


# ── 历史成绩 / 阵容 / 新军 缓存：load_teams 时填充 ─────────────────────────
_HIST_CACHE: dict[str, float] = {}
_SQUAD_CACHE: dict[str, float] = {}
_NEWCOMER_SET: set[str] = set()


def _load_historical_scores(db: sqlite3.Connection) -> dict[str, float]:
    """从 world_cup_history 算出每队 0~1 归一化的历史强度。

    评分 = Σ (placing_points × HIST_DECAY ^ ((latest_year - year) / 4))
    归一化 = HIST_BASELINE + (1 - HIST_BASELINE) × score / max_score
    """
    raw: dict[str, float] = defaultdict(float)
    rows = db.execute(
        "SELECT year, champion, runner_up, third, fourth FROM world_cup_history"
    ).fetchall()
    for r in rows:
        year = r[0]
        cycles_ago = max(0.0, (HIST_LATEST_YEAR - year) / 4)
        decay = HIST_DECAY ** cycles_ago
        for col_idx, placing in enumerate(["champion", "runner_up", "third", "fourth"], start=1):
            name = r[col_idx]
            if not name:
                continue
            canonical = HISTORY_ALIAS.get(name, name)
            raw[canonical] += HIST_POINTS[placing] * decay

    max_s = max(raw.values(), default=0.0)
    if max_s <= 0:
        return {}
    return {
        team: HIST_BASELINE + (1.0 - HIST_BASELINE) * (score / max_s)
        for team, score in raw.items()
    }


def _load_squad_strengths(db: sqlite3.Connection) -> dict[str, float]:
    """从 team_squads 表读阵容评分；表不存在或缺队时返回空 dict（fallback 上层处理）。"""
    try:
        rows = db.execute("SELECT team_name, squad_strength FROM team_squads").fetchall()
        return {r[0]: r[1] for r in rows}
    except sqlite3.OperationalError:
        return {}


def historical_strength(team_name: str) -> float:
    """单队历史成绩强度（0.20-1.00）。无世界杯前四史的队返回 baseline 0.20。"""
    return _HIST_CACHE.get(team_name, HIST_BASELINE)


def squad_strength(team_name: str) -> float:
    """单队当前阵容评分（0.20-1.00）。未种子化的队返回 fallback 0.50。"""
    return _SQUAD_CACHE.get(team_name, SQUAD_FALLBACK)


def boost_only(team: dict[str, Any]) -> float:
    """主场/卫冕/联盟加成累加，用于 W_BOOSTS 项。"""
    s = 0.0
    s += HOST_BOOST if team.get("is_host") else 0.0
    s += DEFENDING_CHAMPION_BOOST if team.get("is_defending_champion") else 0.0
    s += CONFEDERATION_BONUS.get(team["confederation"], 0.0)
    # 归一到 [0, 1]：理论上限约 0.08+0.10+0.05 = 0.23，scale 到约 0.6 满分附近
    return min(1.0, s / 0.25)


def team_strength(team: dict[str, Any]) -> float:
    """4 因子加权综合实力，0.05 下限保留。

    最终值约 0.10-0.95，喂给 win_probability(s_a, s_b) = s_a/(s_a+s_b)
    与 Poisson 进球分布的中心系数。
    """
    rank_s = rank_to_strength(team["fifa_rank"])
    hist_s = historical_strength(team["name"])
    squad_s = squad_strength(team["name"])
    boost_s = boost_only(team)

    s = (
        W_RANK    * rank_s +
        W_HISTORY * hist_s +
        W_SQUAD   * squad_s +
        W_BOOSTS  * boost_s
    )
    return max(0.05, s)


def win_probability(s_a: float, s_b: float) -> float:
    """Probability that team A beats team B (single game, no draw)."""
    return s_a / (s_a + s_b)


def load_teams(db: sqlite3.Connection) -> dict[str, dict[str, Any]]:
    """加载队列同时填充 historical / squad / newcomer 缓存。"""
    global _HIST_CACHE, _SQUAD_CACHE, _NEWCOMER_SET
    _HIST_CACHE = _load_historical_scores(db)
    _SQUAD_CACHE = _load_squad_strengths(db)

    rows = db.execute(
        "SELECT name, group_name, confederation, fifa_rank, is_host, is_defending_champion, appearances FROM teams"
    ).fetchall()
    cols = ["name", "group_name", "confederation", "fifa_rank", "is_host", "is_defending_champion", "appearances"]
    teams = {r[0]: dict(zip(cols, r)) for r in rows}
    _NEWCOMER_SET = {n for n, t in teams.items() if (t.get("appearances") or 0) <= NEWCOMER_THRESHOLD}
    return teams


def _sample_poisson(rng: random.Random, lam: float) -> int:
    """Knuth's algorithm: 单次 Poisson(λ) 采样。λ 越大循环次数越多，但
    球类比赛 λ 通常 <6，迭代上限可控。"""
    if lam <= 0:
        return 0
    L = math.exp(-lam)
    k = 0
    p = 1.0
    while True:
        k += 1
        p *= rng.random()
        if p <= L:
            return k - 1


def _compute_goal_lambdas(
    s_a: float, s_b: float,
    is_knockout: bool,
    a_newcomer: bool, b_newcomer: bool,
) -> tuple[float, float]:
    """根据强度差 + 新军压力，返回 (λ_a, λ_b) Poisson 参数。"""
    base_a = GOALS_BASE_KO_HOME if is_knockout else GOALS_BASE_HOME
    base_b = GOALS_BASE_KO_AWAY if is_knockout else GOALS_BASE_AWAY
    diff = s_a - s_b
    # 不对称：强队多进的多 (ATK_LIFT)，弱队被压相对少 (DEF_DRAG)
    if diff >= 0:
        la = base_a + diff * ATK_LIFT
        lb = base_b - diff * DEF_DRAG
    else:
        la = base_a + diff * DEF_DRAG       # diff<0，la 被压
        lb = base_b - diff * ATK_LIFT       # 双负变正：弱方强势

    # 新军惩罚：自己进得少，对手进得多（防守崩塌）
    if a_newcomer:
        la -= NEWCOMER_PENALTY
        lb += NEWCOMER_DEFENSE_PENALTY
    if b_newcomer:
        lb -= NEWCOMER_PENALTY
        la += NEWCOMER_DEFENSE_PENALTY

    la = max(LAMBDA_MIN, min(LAMBDA_MAX, la))
    lb = max(LAMBDA_MIN, min(LAMBDA_MAX, lb))
    return la, lb


def simulate_group_match(
    rng: random.Random,
    team_a: str,
    team_b: str,
    strength: dict[str, float],
) -> tuple[tuple[int, int], str, float, float]:
    """Simulate a single group-stage match.

    Returns:
        (home_goals, away_goals, winner_team_or_draw_marker, p_home_win, p_draw)

    进球数走 Poisson 分布 — 用 _compute_goal_lambdas 算 (λ_a, λ_b)，
    再独立采样。胜负由真实进球数比较决定（平局也保留，小组赛允许）。
    p_home_win / p_draw 仍按强度差给出解析值供前端展示。
    """
    s_a = strength[team_a]
    s_b = strength[team_b]
    p_home = win_probability(s_a, s_b)
    # 平局概率：强度差越大，平局越罕见
    imbalance = abs(s_a - s_b)
    p_draw = max(0.08, 0.28 - imbalance * 0.5)

    la, lb = _compute_goal_lambdas(
        s_a, s_b, is_knockout=False,
        a_newcomer=team_a in _NEWCOMER_SET,
        b_newcomer=team_b in _NEWCOMER_SET,
    )
    ga = _sample_poisson(rng, la)
    gb = _sample_poisson(rng, lb)

    if ga > gb:
        winner = team_a
    elif gb > ga:
        winner = team_b
    else:
        winner = "draw"
    return ((ga, gb), winner, p_home, p_draw)


def simulate_knockout_match(
    rng: random.Random,
    team_a: str,
    team_b: str,
    strength: dict[str, float],
) -> tuple[tuple[int, int], str, float]:
    """Simulate a knockout match (no draws — go to extra-time / pens if tied).

    Returns:
        (home_goals, away_goals, winner_team, p_home_win)
    """
    s_a = strength[team_a]
    s_b = strength[team_b]
    p_home = win_probability(s_a, s_b)

    la, lb = _compute_goal_lambdas(
        s_a, s_b, is_knockout=True,
        a_newcomer=team_a in _NEWCOMER_SET,
        b_newcomer=team_b in _NEWCOMER_SET,
    )
    ga = _sample_poisson(rng, la)
    gb = _sample_poisson(rng, lb)

    # 平局 → 加时 + 点球：重采用强度差作为 Bernoulli 决出胜方，
    # 比分维持平手时硬加 1 球给胜方（视作点球绝杀）
    if ga == gb:
        if rng.random() < p_home:
            ga += 1
            winner = team_a
        else:
            gb += 1
            winner = team_b
    elif ga > gb:
        winner = team_a
    else:
        winner = team_b
    return ((ga, gb), winner, p_home)


def simulate_group(
    rng: random.Random,
    members: list[str],
    strength: dict[str, float],
    match_predictions: list[tuple[str, str, str, str, int, int]] | None = None,
) -> list[list[str]]:
    """Return qualifying teams: 1st, 2nd, 3rd, 4th (3rd and 4th ordered).

    If `match_predictions` is provided, append (round_name, match_id, home,
    away, home_g, away_g) for every simulated group match (we don't have
    match_ids at this layer, so the caller fills in match_id as '?' and
    later correlates by (home, away, round) — see simulate_match_predictions).
    """
    table: dict[str, dict[str, int]] = {m: {"pts": 0, "gd": 0, "gf": 0, "ga": 0} for m in members}
    for i in range(4):
        for j in range(i + 1, 4):
            a, b = members[i], members[j]
            (ga, gb), _winner, _ph, _pd = simulate_group_match(rng, a, b, strength)
            if match_predictions is not None:
                match_predictions.append(("Group", "?", a, b, ga, gb))
            if ga > gb:
                table[a]["pts"] += 3
            elif ga < gb:
                table[b]["pts"] += 3
            else:
                table[a]["pts"] += 1
                table[b]["pts"] += 1
            table[a]["gf"] += ga
            table[a]["ga"] += gb
            table[b]["gf"] += gb
            table[b]["ga"] += ga
    for m in table:
        table[m]["gd"] = table[m]["gf"] - table[m]["ga"]
    ranked = sorted(table.items(), key=lambda x: (x[1]["pts"], x[1]["gd"], x[1]["gf"]), reverse=True)
    return [[r[0] for r in ranked]]  # flat list of 4 in order


def simulate_knockout(rng: random.Random, teams: list[str], strength: dict[str, float]) -> str:
    """Single-elimination among `teams` (must be power of 2). Return champion."""
    current = list(teams)
    rng.shuffle(current)
    while len(current) > 1:
        nxt: list[str] = []
        for i in range(0, len(current), 2):
            a, b = current[i], current[i + 1]
            if rng.random() < win_probability(strength[a], strength[b]):
                nxt.append(a)
            else:
                nxt.append(b)
        current = nxt
    return current[0]


def monte_carlo(
    teams: dict[str, dict[str, Any]],
    n: int = N_SIM,
    record_predictions: bool = False,
) -> tuple[dict[str, dict[str, int]], list[tuple[str, str, int, int]]] | dict[str, dict[str, int]]:
    """Simulate full tournament n times.

    When `record_predictions=True`, returns (counts, per_match_outcomes)
    where per_match_outcomes is a list of (round, home_team, away_team,
    home_goals, away_goals) — one entry per simulated match across all
    rounds (group stage included). When False, returns just counts for
    backward compatibility with the original signature.
    """
    counts: dict[str, dict[str, int]] = {t: {"champion": 0, "sf": 0, "qf": 0, "r16": 0, "r32": 0} for t in teams}
    rng = random.Random(42)
    strength = {name: team_strength(t) for name, t in teams.items()}

    # Group composition
    group_members: dict[str, list[str]] = {}
    for t in teams.values():
        group_members.setdefault(t["group_name"], []).append(t["name"])

    # Recorded match outcomes (caller decides whether to use them).
    # Each entry is (round_label, home_team, away_team, home_goals, away_goals).
    # Knockout round labels: "R32", "R16", "QF", "SF", "3rd", "F".
    outcomes: list[tuple[str, str, str, int, int]] = []

    for _ in range(n):
        # 1) Group stage — 12 groups of 4, top 2 + 8 best 3rd qualify for R32
        qualifiers: list[str] = []  # 32 total
        third_placers: list[tuple[str, int, int, int]] = []  # (team, pts, gd, gf) for 3rd-place tiebreaker
        for g, members in sorted(group_members.items()):
            preds_buf: list[tuple[str, str, str, str, int, int]] = []
            ranking = simulate_group(rng, members, strength,
                                     match_predictions=preds_buf if record_predictions else None)[0]
            if record_predictions:
                for _round, _mid, h, a, gh, ga in preds_buf:
                    outcomes.append((f"Group {g}", h, a, gh, ga))
            qualifiers.append(ranking[0])  # 1st
            qualifiers.append(ranking[1])  # 2nd
            third = ranking[2]
            # Need pts/gd/gf — recompute quickly
            t = teams[third]
            # Reuse the team_strength proxy: track via a simple Pts/GD heuristic
            third_placers.append((third, strength[third] * 100, 0, 0))
        # Sort 3rd placers by strength proxy, take top 8
        third_placers.sort(key=lambda x: x[1], reverse=True)
        for tpl in third_placers[:8]:
            qualifiers.append(tpl[0])

        # 32 qualified for R32
        for t in qualifiers:
            counts[t]["r32"] += 1

        # Knockout R32 (16 matches → 16 winners)
        r16_winners, r32_pairs = simulate_knockout_collect(
            rng, qualifiers, strength, 16, return_pairs=True
        )
        if record_predictions:
            for gh, ga, h, a in r32_pairs:
                outcomes.append(("R32", h, a, gh, ga))
        for t in r16_winners:
            counts[t]["r16"] += 1

        # R16 → QF (8 matches)
        qf_winners, r16_pairs = simulate_knockout_collect(
            rng, r16_winners, strength, 8, return_pairs=True
        )
        if record_predictions:
            for gh, ga, h, a in r16_pairs:
                outcomes.append(("R16", h, a, gh, ga))
        for t in qf_winners:
            counts[t]["qf"] += 1

        # QF → SF (4 matches)
        sf_winners, qf_pairs = simulate_knockout_collect(
            rng, qf_winners, strength, 4, return_pairs=True
        )
        if record_predictions:
            for gh, ga, h, a in qf_pairs:
                outcomes.append(("QF", h, a, gh, ga))
        for t in sf_winners:
            counts[t]["sf"] += 1

        # SF → F (2 matches)
        finalists, sf_pairs = simulate_knockout_collect(
            rng, sf_winners, strength, 2, return_pairs=True
        )
        if record_predictions:
            for gh, ga, h, a in sf_pairs:
                outcomes.append(("SF", h, a, gh, ga))

        # F → Champion (single match)
        (gh_f, ga_f), champ, _ph = simulate_knockout_match(
            rng, finalists[0], finalists[1], strength
        )
        if record_predictions:
            outcomes.append(("F", finalists[0], finalists[1], gh_f, ga_f))
        counts[champ]["champion"] += 1

    if record_predictions:
        return counts, outcomes
    return counts


def simulate_knockout_collect(
    rng: random.Random,
    teams: list[str],
    strength: dict[str, float],
    n_winners: int,
    return_pairs: bool = False,
) -> list[str] | tuple[list[str], list[tuple[int, int, str, str]]]:
    """Single-elimination returning all winners of a round (size must be power of 2).

    When `return_pairs=True`, also returns the per-match (home_g, away_g,
    home_team, away_team) tuples in match order (post-shuffle). Caller
    can persist these for per-match AI prediction.
    """
    current = list(teams)
    rng.shuffle(current)
    pairs: list[tuple[int, int, str, str]] = []
    while len(current) > n_winners:
        nxt: list[str] = []
        for i in range(0, len(current), 2):
            a, b = current[i], current[i + 1]
            (gh, ga), _w, _ph = simulate_knockout_match(rng, a, b, strength)
            if return_pairs:
                pairs.append((gh, ga, a, b))
            if gh > ga:
                nxt.append(a)
            else:
                nxt.append(b)
        current = nxt
    if return_pairs:
        return current, pairs
    return current


def historical_similarity(teams: dict[str, dict[str, Any]], history) -> dict[str, float]:
    """Champion profile similarity 0..100. Top FIFA ranks historically win more."""
    sims: dict[str, float] = {}
    for name, t in teams.items():
        rank = t["fifa_rank"]
        sims[name] = max(0.0, min(100.0, 100.0 - (rank - 1) * 1.5))
    return sims


def compute_predictions(db_path: Path = DB_PATH, n: int = N_SIM) -> dict[str, dict[str, float]]:
    db = sqlite3.connect(db_path)
    teams = load_teams(db)
    history = db.execute("SELECT * FROM world_cup_history").fetchall()
    db.close()

    counts = monte_carlo(teams, n=n)
    sims = historical_similarity(teams, history)

    preds: dict[str, dict[str, float]] = {}
    for name, c in counts.items():
        preds[name] = {
            "champion_prob": round(c["champion"] / n * 100, 2),
            "sf_prob":       round(c["sf"] / n * 100, 2),
            "qf_prob":       round(c["qf"] / n * 100, 2),
            "r16_prob":      round(c["r16"] / n * 100, 2),
            "r32_prob":      round(c["r32"] / n * 100, 2),
            "historical_similarity": round(sims.get(name, 0), 2),
        }
        mc = preds[name]["champion_prob"]
        hs = preds[name]["historical_similarity"]
        preds[name]["final_score"] = round(0.7 * mc + 0.3 * hs, 2)
    return preds


def persist_predictions(preds: dict[str, dict[str, float]], db_path: Path = DB_PATH) -> None:
    db = sqlite3.connect(db_path)
    now = datetime.now(timezone.utc).isoformat()
    for name, p in preds.items():
        db.execute("""
            INSERT OR REPLACE INTO predictions
                (team, champion_prob, sf_prob, qf_prob, r16_prob, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (name, p["champion_prob"], p["sf_prob"], p["qf_prob"], p["r16_prob"], now))
    db.commit()
    db.close()


# ── Round labels used by monte_carlo outcomes → matches.round mapping ────────
# `monte_carlo` records outcomes with round labels: "Group A".."Group L",
# "R32", "R16", "QF", "SF", "F".  The matches table uses longer labels:
# "Group A Matchday 1" etc. (one per matchday), "Round of 32",
# "Round of 16", "Quarter-finals", "Semi-finals", "Third place", "Final".
# The mapping below maps (round_label, group_or_team) → matches.match_id.
ROUND_LABEL_TO_DB: dict[str, str] = {
    "R32": "Round of 32",
    "R16": "Round of 16",
    "QF":  "Quarter-finals",
    "SF":  "Semi-finals",
    "F":   "Final",
    "3rd": "Third place",
}


def aggregate_match_predictions(
    outcomes: list[tuple[str, str, str, int, int]],
    db_path: Path = DB_PATH,
) -> dict[str, dict[str, Any]]:
    """Aggregate per-match simulated outcomes into per-match_id prediction dicts.

    Args:
        outcomes: list of (round_label, home_team, away_team, home_goals,
            away_goals) from monte_carlo(..., record_predictions=True).
        db_path:  path to wc2026.db (used to correlate rounds → match_ids).

    Returns:
        dict keyed by match_id (M001..M113). Each value contains:
          - home_team, away_team (resolved names, possibly TBD_* for
            future knockout placeholders)
          - p_home_win, p_draw (only for group), p_away_win
          - predicted_home_score, predicted_away_score
          - predicted_winner (None for draws)
          - score_distribution: dict of "H-A" → probability (top 5)
          - simulated_count: number of MC iterations that included this
            match (will be 0 for TBD-bracket matches that were never
            simulated because they reference a winner placeholder).
    """
    db = sqlite3.connect(db_path)
    db.row_factory = sqlite3.Row

    # Bucket outcomes by (round_label, sorted_pair). 用字典序 sorted tuple
    # 而非 frozenset 作 key，确保 mc_home/mc_away 顺序可复现（frozenset →
    # tuple 顺序不定会导致 wins_first/wins_second 与 mc_home/mc_away 错配，
    # 进而 flip 判定相反，整张表的胜负概率被翻转）。存储时把 (gh, ga) 一并
    # 翻转到 sorted 方向，下游 mc_home == _pair[0] 永远成立。
    bucket: dict[tuple[str, tuple[str, str]], list[tuple[int, int]]] = {}
    for rnd, h, a, gh, ga in outcomes:
        if h <= a:
            key_pair = (h, a)
            rec = (gh, ga)
        else:
            key_pair = (a, h)
            rec = (ga, gh)  # 翻转到 sorted 方向
        bucket.setdefault((rnd, key_pair), []).append(rec)

    # Build a lookup from match_id → (home_team, away_team, round_label,
    # group_name) so we can correlate outcomes with DB rows.
    match_lookup: dict[str, tuple[str, str, str, str | None]] = {}
    for row in db.execute(
        "SELECT match_id, round, group_name, home_team, away_team FROM matches"
    ).fetchall():
        match_lookup[row["match_id"]] = (
            row["home_team"], row["away_team"], row["round"], row["group_name"]
        )

    db.close()

    # We need the actual directional (home_team, away_team) for each
    # match_id to record accurate predicted scores and winner.  Since
    # multiple match_ids can share the same unordered pair (e.g. M002
    # South Korea vs Czechia and M009 Czechia vs South Africa share
    # the pair {South Korea, Czechia}), we keep a per-match_id
    # direction map.
    match_direction: dict[str, tuple[str, str]] = {}
    for mid, (h, a, _rnd, _grp) in match_lookup.items():
        match_direction[mid] = (h, a)

    # Helper: round labels for group matches (one per group) — we map
    # back to ANY match in that group with the matching (home, away)
    # pair. If two matchdays share the pair (shouldn't happen), we
    # split equally below.
    result: dict[str, dict[str, Any]] = {}

    # Reverse index: (round_label, sorted_pair) → [match_id, ...]
    rev_index: dict[tuple[str, tuple[str, str]], list[str]] = {}
    for mid, (h, a, rnd, grp) in match_lookup.items():
        sorted_pair = (h, a) if h <= a else (a, h)
        if grp:  # group stage: round_label is "Group A".."Group L"
            rev_index.setdefault((f"Group {grp}", sorted_pair), []).append(mid)
        else:
            # knockout: round_label is R32 / R16 / QF / SF / F / 3rd
            label = next((k for k, v in ROUND_LABEL_TO_DB.items() if v == rnd), None)
            if label is None:
                continue
            rev_index.setdefault((label, sorted_pair), []).append(mid)

    for (rnd_label, _pair), sims in bucket.items():
        match_ids = rev_index.get((rnd_label, _pair), [])
        if not match_ids:
            # Knockout pair that was never resolved to a real match
            # (e.g. W73 vs W74 — those placeholders don't exist in the
            # DB as home/away, only as competition slots). Skip; they
            # will be filled in when actual winners are known.
            continue
        # Aggregate stats over all sims for this pair
        n = len(sims)
        wins_first = sum(1 for gh, ga in sims if gh > ga)
        wins_second = sum(1 for gh, ga in sims if gh < ga)
        draws = sum(1 for gh, ga in sims if gh == ga)
        # Score distribution (counted in MC ordering)
        score_count: dict[tuple[int, int], int] = {}
        for gh, ga in sims:
            score_count[(gh, ga)] = score_count.get((gh, ga), 0) + 1
        top_scores = sorted(score_count.items(), key=lambda x: x[1], reverse=True)[:5]
        # Predicted score = most common (tie-broken by smaller total, then smaller home goals)
        top_score_pair = max(
            score_count.items(),
            key=lambda kv: (kv[1], -(kv[0][0] + kv[0][1]), -kv[0][0])
        )[0]

        # For each match_id, the home/away direction may differ from
        # the MC (sorted) ordering.  We recompute p_home/p_away and the score
        # distribution accordingly so the front-end gets the right
        # view (M009 Czechia vs South Africa gets the same data as
        # any other SA-vs-CZ match, just direction-flipped).
        for mid in match_ids:
            home, away = match_direction[mid]
            mc_home, mc_away = _pair  # 已 sorted tuple，顺序确定
            # Map MC outcomes (sorted) to DB direction.
            if mc_home == home and mc_away == away:
                flip = False
            elif mc_home == away and mc_away == home:
                flip = True
            else:
                # Shouldn't happen — bucket key contains both names.
                flip = False

            # Per-direction win/draw counts
            if flip:
                p_home = wins_second / n
                p_away = wins_first / n
            else:
                p_home = wins_first / n
                p_away = wins_second / n
            p_draw = draws / n

            # Score distribution per direction (top 5)
            per_dir_count: dict[tuple[int, int], int] = {}
            for (gh, ga), cnt in score_count.items():
                key = (ga, gh) if flip else (gh, ga)
                per_dir_count[key] = per_dir_count.get(key, 0) + cnt
            top_per_dir = sorted(per_dir_count.items(), key=lambda x: x[1], reverse=True)[:5]
            score_dist = {f"{k[0]}-{k[1]}": round(v / n * 100, 2) for k, v in top_per_dir}

            # Predicted score in DB direction
            if flip:
                ph, pa = top_score_pair[1], top_score_pair[0]
            else:
                ph, pa = top_score_pair[0], top_score_pair[1]

            # Winner (in DB direction)
            if wins_first > wins_second and wins_first > draws:
                # MC home (first of pair) wins
                winner_mc_first = True
            elif wins_second > wins_first and wins_second > draws:
                winner_mc_first = False
            elif draws > wins_first and draws > wins_second:
                winner = "draw"
                winner_mc_first = None
            else:
                # Tie — pick whichever side has higher p
                winner_mc_first = wins_first >= wins_second

            if winner_mc_first is None:
                winner = "draw"
            elif winner_mc_first:
                # winner_mc_first 已基于 (gh, ga) 在 sorted 方向下计票；
                # mc_home/mc_away 是真实队名，赢队的名字与 DB 方向无关。
                winner = mc_home
            else:
                winner = mc_away

            result[mid] = {
                "home_team": home,
                "away_team": away,
                "home_win_prob": round(p_home * 100, 2),
                "draw_prob": round(p_draw * 100, 2),
                "away_win_prob": round(p_away * 100, 2),
                "predicted_home_score": ph,
                "predicted_away_score": pa,
                "predicted_winner": winner,
                "score_distribution": score_dist,
                "simulated_count": n,
            }
    return result


def persist_match_predictions(
    preds: dict[str, dict[str, Any]],
    db_path: Path = DB_PATH,
) -> int:
    """Write per-match predictions to the matches table (predicted_winner,
    predicted_home_score, predicted_away_score, home_win_prob, draw_prob,
    away_win_prob, score_distribution_json).

    Returns the number of rows written.
    """
    import json
    if not preds:
        return 0
    db = sqlite3.connect(db_path)
    written = 0
    for mid, p in preds.items():
        db.execute("""
            UPDATE matches SET
                predicted_winner = ?,
                predicted_home_score = ?,
                predicted_away_score = ?,
                home_win_prob = ?,
                draw_prob = ?,
                away_win_prob = ?,
                score_distribution_json = ?
            WHERE match_id = ?
        """, (
            p["predicted_winner"],
            p["predicted_home_score"],
            p["predicted_away_score"],
            p["home_win_prob"],
            p["draw_prob"],
            p["away_win_prob"],
            json.dumps(p["score_distribution"]),
            mid,
        ))
        written += 1
    db.commit()
    db.close()
    return written


# ── Bracket slot resolution for knockout matches ───────────────────────────────
# R32 matches use bracket slots like "1A" (group winner), "2A" (runner-up),
# "3rd-ABCDF" (best 3rd from {A,B,C,D,F}), etc.  Before group stage finishes
# these are unresolved placeholders.  We resolve them by predicting which
# team will fill each slot based on team strength (1st = strongest, 2nd =
# second-strongest, 3rd = third-strongest in the group).  We do NOT
# compute cross-group "best 3rd" tiebreakers — those stay "TBD" per the
# v3 spec.  Later rounds (R16, QF, SF, F) reference the winners of prior
# rounds (e.g. "W73", "W101") which we can't know until those matches
# resolve; they stay "TBD" too.

# Pattern: e.g. "1A", "2B", "3rd-ABCDF", "2E (alt)", "W73", "L101"
import re as _re
_GROUP_SLOT_RE = _re.compile(r"^(?P<rank>[123])(?P<alt> \(alt\))?(?P<grp>[A-L])$")
_3RD_SLOT_RE = _re.compile(r"^3rd-[A-L]+$")
_WINNER_SLOT_RE = _re.compile(r"^W\d+$")
_LOSER_SLOT_RE = _re.compile(r"^L\d+$")


def _resolve_group_slot(
    slot: str,
    group_members: dict[str, list[tuple[str, float]]],
) -> str | None:
    """Resolve a "1A"/"2B"/"3C"-style slot to a real team name.

    Returns None for unresolvable slots (3rd place / alternate / unknown).
    """
    m = _GROUP_SLOT_RE.match(slot.strip())
    if not m:
        return None
    rank = int(m["rank"])
    grp = m["grp"]
    if grp not in group_members:
        return None
    members_sorted = sorted(group_members[grp], key=lambda x: x[1], reverse=True)
    if rank - 1 >= len(members_sorted):
        return None
    return members_sorted[rank - 1][0]


def _is_placeholder(slot: str) -> bool:
    """Return True if `slot` is a placeholder (TBD, group slot, winner ref)."""
    if slot.startswith("TBD") or slot.startswith("tbd"):
        return True
    if _GROUP_SLOT_RE.match(slot.strip()):
        return True
    if _3RD_SLOT_RE.match(slot.strip()):
        return True
    if _WINNER_SLOT_RE.match(slot.strip()):
        return True
    if _LOSER_SLOT_RE.match(slot.strip()):
        return True
    return False


def predict_knockout_placeholders(
    teams: dict[str, dict[str, Any]],
    db_path: Path = DB_PATH,
) -> dict[str, dict[str, Any]]:
    """Predict knockout matches whose teams are still bracket-slot
    placeholders (e.g. "1A", "2B", "W73", "3rd-ABCDF").

    For matches with resolvable group slots on BOTH sides (e.g. M073
    "2A" vs "2B"), compute a real prediction by treating the resolved
    teams as a normal knockout match.
    For matches with unresolvable slots (3rd-XXXXX, W73, L101), set
    predicted_winner = "TBD" and leave scores null.

    Returns dict keyed by match_id, same shape as the group-match
    prediction dicts.
    """
    db = sqlite3.connect(db_path)
    db.row_factory = sqlite3.Row

    # Group members with strength (rank by FIFA rank so "1A" is
    # strongest, "2A" is second-strongest).
    group_members: dict[str, list[tuple[str, float]]] = {}
    for row in db.execute("""
        SELECT name, group_name, fifa_rank, is_host, is_defending_champion, confederation
        FROM teams
    """).fetchall():
        s = team_strength(dict(row))
        group_members.setdefault(row["group_name"], []).append((row["name"], s))

    rows = db.execute("""
        SELECT match_id, round, home_team, away_team
        FROM matches
        WHERE group_name IS NULL
    """).fetchall()
    db.close()

    result: dict[str, dict[str, Any]] = {}
    for r in rows:
        mid = r["match_id"]
        rnd = r["round"]
        h, a = r["home_team"], r["away_team"]
        h_resolved = _resolve_group_slot(h, group_members) if _is_placeholder(h) else None
        a_resolved = _resolve_group_slot(a, group_members) if _is_placeholder(a) else None

        if h_resolved and a_resolved:
            # Both sides resolvable -> real prediction.
            sh = team_strength(teams[h_resolved])
            sa = team_strength(teams[a_resolved])
            p_home = win_probability(sh, sa)
            p_away = 1.0 - p_home
            # Predicted score scales with the strength ratio.  The
            # mean goals are 1.3 home / 1.1 away baseline; the team
            # with more strength gets a goal bump proportional to its
            # advantage.
            strength_ratio = sh / (sh + sa)  # 0..1, 0.5 == even
            gh_mean = 1.3 * (0.5 + (strength_ratio - 0.5) * 0.8)
            ga_mean = 1.1 * (0.5 + (0.5 - strength_ratio) * 0.8)
            ph = max(0, int(round(gh_mean)))
            pa = max(0, int(round(ga_mean)))
            # Knockout: no draws.  Bump the favourite by 1.
            if ph == pa:
                if p_home >= 0.5:
                    ph += 1
                else:
                    pa += 1
            winner = h_resolved if ph > pa else a_resolved
            score_dist = {
                f"{ph}-{pa}": round(100.0 * p_home if ph > pa else 100.0 * p_away, 2),
            }
            result[mid] = {
                "home_team": h_resolved,
                "away_team": a_resolved,
                "home_win_prob": round(p_home * 100, 2),
                "draw_prob": 0.0,
                "away_win_prob": round(p_away * 100, 2),
                "predicted_home_score": ph,
                "predicted_away_score": pa,
                "predicted_winner": winner,
                "score_distribution": score_dist,
                "simulated_count": 0,
                "knockout_round": rnd,
            }
        else:
            # One or both sides unresolvable \u2192 mark as TBD.
            result[mid] = {
                "home_team": h if not _is_placeholder(h) else None,
                "away_team": a if not _is_placeholder(a) else None,
                "home_win_prob": None,
                "draw_prob": None,
                "away_win_prob": None,
                "predicted_home_score": None,
                "predicted_away_score": None,
                "predicted_winner": "TBD",
                "score_distribution": {},
                "simulated_count": 0,
                "knockout_round": rnd,
            }
    return result


def compute_and_persist_all(db_path: Path = DB_PATH, n: int = N_SIM) -> dict[str, Any]:
    """Run the full pipeline: MC predictions → match-level predictions →
    persist to DB. Returns a summary dict suitable for logging.

    Args:
        db_path: path to wc2026.db
        n:       number of MC iterations
    """
    db = sqlite3.connect(db_path)
    teams = load_teams(db)
    history = db.execute("SELECT * FROM world_cup_history").fetchall()
    db.close()

    # 1) Tournament-wide predictions (existing flow)
    counts, outcomes = monte_carlo(teams, n=n, record_predictions=True)
    sims = historical_similarity(teams, history)
    team_preds: dict[str, dict[str, float]] = {}
    for name, c in counts.items():
        team_preds[name] = {
            "champion_prob": round(c["champion"] / n * 100, 2),
            "sf_prob":       round(c["sf"] / n * 100, 2),
            "qf_prob":       round(c["qf"] / n * 100, 2),
            "r16_prob":      round(c["r16"] / n * 100, 2),
            "r32_prob":      round(c["r32"] / n * 100, 2),
            "historical_similarity": round(sims.get(name, 0), 2),
        }
        mc = team_preds[name]["champion_prob"]
        hs = team_preds[name]["historical_similarity"]
        team_preds[name]["final_score"] = round(0.7 * mc + 0.3 * hs, 2)
    persist_predictions(team_preds, db_path=db_path)

    # 2) Per-match predictions for group stage (MC-derived)
    match_preds = aggregate_match_predictions(outcomes, db_path=db_path)
    n_group_written = persist_match_predictions(match_preds, db_path=db_path)

    # 3) Per-match predictions for knockout matches (bracket-slot
    #    resolution for the 16 R32 matches; TBD for R16+).
    ko_preds = predict_knockout_placeholders(teams, db_path=db_path)
    n_ko_written = persist_match_predictions(ko_preds, db_path=db_path)

    return {
        "team_predictions": len(team_preds),
        "group_match_predictions_written": n_group_written,
        "knockout_match_predictions_written": n_ko_written,
        "match_predictions_written": n_group_written + n_ko_written,
        "iterations": n,
        "outcomes_recorded": len(outcomes),
    }


def calibrate_on_finished(db_path: Path = DB_PATH) -> dict[str, Any]:
    """Sanity-check team_strength on already-played matches.

    For each finished match we compute P(home wins) and P(away wins) using
    the current boost coefficients, then check the Brier score (lower is
    better) and simple accuracy (did the higher-P team actually win?).
    Also reports host-team win rate (Mexico/USA/Canada).
    Useful for tuning HOST_BOOST without waiting for the whole tournament.
    """
    import json
    db = sqlite3.connect(db_path)
    teams = load_teams(db)
    rows = db.execute("""
        SELECT home_team, away_team, home_score, away_score
        FROM matches
        WHERE status='finished' AND home_score IS NOT NULL
        ORDER BY match_date, match_time
    """).fetchall()

    if not rows:
        db.close()
        return {"matches": 0, "note": "no finished matches yet"}

    n = 0
    brier = 0.0  # sum of squared errors per match (1 outcome, 3-way)
    correct_pick = 0
    host_matches: list[dict] = []
    for h, a, hs, as_ in rows:
        if h not in teams or a not in teams:
            continue
        sh = team_strength(teams[h])
        sa = team_strength(teams[a])
        p_home = sh / (sh + sa)
        p_away = 1.0 - p_home  # ties collapsed into both-lose for calibration purposes
        # Actual outcome: 1 if home win, 0 if draw or away win (binary calibration)
        actual_home_win = 1.0 if hs > as_ else 0.0
        brier += (p_home - actual_home_win) ** 2
        predicted_winner = h if p_home >= 0.5 else a
        actual_winner = h if hs > as_ else (a if as_ > hs else "draw")
        if actual_winner != "draw" and predicted_winner == actual_winner:
            correct_pick += 1
        n += 1
        is_host_match = teams[h].get("is_host") or teams[a].get("is_host")
        if is_host_match:
            host_team = h if teams[h].get("is_host") else a
            opp = a if teams[h].get("is_host") else h
            host_score = hs if teams[h].get("is_host") else as_
            opp_score = as_ if teams[h].get("is_host") else hs
            host_matches.append({
                "host": host_team,
                "opponent": opp,
                "score": f"{host_score}-{opp_score}",
                "p_host_win": round(p_home if teams[h].get("is_host") else (1 - p_home), 3),
                "result": "win" if host_score > opp_score else ("draw" if host_score == opp_score else "loss"),
            })

    db.close()
    return {
        "matches": n,
        "brier_score": round(brier / max(n, 1), 4),  # 0..1, lower=better
        "winner_pick_accuracy": round(correct_pick / max(n, 1), 3),
        "host_matches": host_matches,
        "host_record": {
            "played": len(host_matches),
            "wins": sum(1 for m in host_matches if m["result"] == "win"),
            "draws": sum(1 for m in host_matches if m["result"] == "draw"),
            "losses": sum(1 for m in host_matches if m["result"] == "loss"),
            "host_boost_used": HOST_BOOST,
        },
    }


def main() -> None:
    summary = compute_and_persist_all()
    preds = compute_predictions()
    top = sorted(preds.items(), key=lambda x: x[1]["final_score"], reverse=True)[:15]
    print("Top 15 champion probabilities (MC + historical similarity):")
    for i, (team, p) in enumerate(top, 1):
        print(f"  {i:2d}. {team:25s}  final={p['final_score']:5.2f}%  "
              f"MC={p['champion_prob']:5.2f}%  SF={p['sf_prob']:5.1f}%  "
              f"QF={p['qf_prob']:5.1f}%  R16={p['r16_prob']:5.1f}%")
    print()
    print("=" * 60)
    print(f"Per-match predictions: {summary['match_predictions_written']} matches written "
          f"({summary['group_match_predictions_written']} group + "
          f"{summary['knockout_match_predictions_written']} knockout) "
          f"across {summary['iterations']} MC iterations")
    print("=" * 60)
    # Sample: show predicted_winner for a few group + knockout matches
    db = sqlite3.connect(DB_PATH)
    print("\nSample group-stage predictions:")
    for row in db.execute("""
        SELECT match_id, home_team, away_team, predicted_winner,
               predicted_home_score, predicted_away_score,
               home_win_prob, draw_prob, away_win_prob
        FROM matches
        WHERE group_name IS NOT NULL AND status='scheduled'
          AND predicted_winner IS NOT NULL
        ORDER BY match_date LIMIT 6
    """).fetchall():
        print(f"  {row[0]} {row[1]:20s} vs {row[2]:20s} → "
              f"predicted {row[5]}-{row[4]} ({row[3]} wins, "
              f"P={row[6]:.1f}/{row[7]:.1f}/{row[8]:.1f})")
    print("\nSample knockout predictions (R32):")
    for row in db.execute("""
        SELECT match_id, home_team, away_team, predicted_winner,
               predicted_home_score, predicted_away_score,
               home_win_prob, draw_prob, away_win_prob
        FROM matches
        WHERE round='Round of 32' AND predicted_winner IS NOT NULL
          AND predicted_winner != 'TBD'
        ORDER BY match_date LIMIT 8
    """).fetchall():
        print(f"  {row[0]} {row[1]:12s} vs {row[2]:12s} -> "
              f"predicted {row[5]}-{row[4]} ({row[3]} wins, "
              f"P={row[6]:.1f}/{row[7]:.1f}/{row[8]:.1f})")
    db.close()
    print()
    print("=" * 60)
    print("Calibration on finished matches (lower Brier = better)")
    print("=" * 60)
    cal = calibrate_on_finished()
    if cal.get("matches", 0) > 0:
        print(f"  matches evaluated:  {cal['matches']}")
        print(f"  Brier score:        {cal['brier_score']:.4f}   (random=0.25, perfect=0.0)")
        print(f"  winner pick acc:    {cal['winner_pick_accuracy']*100:.1f}%")
        print(f"  host_boost used:    {cal['host_record']['host_boost_used']}")
        print(f"  host matches:       {cal['host_record']['played']}  "
              f"(W{cal['host_record']['wins']} D{cal['host_record']['draws']} L{cal['host_record']['losses']})")
        for m in cal["host_matches"]:
            print(f"    {m['host']:8s} vs {m['opponent']:25s}  {m['score']:>5s}  "
                  f"P(host wins)={m['p_host_win']:.2f}  → {m['result']}")


if __name__ == "__main__":
    main()
