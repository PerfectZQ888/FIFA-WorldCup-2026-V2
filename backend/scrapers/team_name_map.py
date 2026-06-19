"""CCTV Chinese team name → DB English team name map.

The project seed.py uses English team names (matching FIFA WC 2026 standard);
CCTV's official WC2026 API returns Chinese names. This map translates them.

**Coverage: 48/48 DB teams (verified against live CCTV date_game_list
2026-06-14..2026-06-22 on 2026-06-14).**

Naming notes:
- FIFA renamed "Cape Verde" → "Cabo Verde" for WC2026 — DB uses "Cabo Verde".
- Türkiye uses the dotted lowercase 'ü' (matching FIFA's official spelling).
- "刚果（金）" with full-width parens is the standard CCTV rendering for
  DR Congo. The full-width form must match exactly (CCTV never emits
  half-width parens for this team).
"""
TEAM_CN_TO_EN: dict[str, str] = {
    # ── Group A ───────────────────────────────────────────
    "墨西哥": "Mexico",
    "南非": "South Africa",
    "韩国": "South Korea",
    "捷克": "Czechia",
    # ── Group B ───────────────────────────────────────────
    "加拿大": "Canada",
    "波黑": "Bosnia & Herzegovina",
    "美国": "USA",
    "巴拉圭": "Paraguay",
    # ── Group C ───────────────────────────────────────────
    "卡塔尔": "Qatar",
    "瑞士": "Switzerland",
    "巴西": "Brazil",
    "摩洛哥": "Morocco",
    # ── Group D ───────────────────────────────────────────
    "海地": "Haiti",
    "苏格兰": "Scotland",
    "澳大利亚": "Australia",
    "土耳其": "Türkiye",
    # ── Group E ───────────────────────────────────────────
    "德国": "Germany",
    "库拉索": "Curaçao",
    "科特迪瓦": "Côte d'Ivoire",
    "厄瓜多尔": "Ecuador",
    # ── Group F ───────────────────────────────────────────
    "荷兰": "Netherlands",
    "日本": "Japan",
    "瑞典": "Sweden",
    "突尼斯": "Tunisia",
    # ── Group G ───────────────────────────────────────────
    "比利时": "Belgium",
    "埃及": "Egypt",
    "伊朗": "IR Iran",
    "新西兰": "New Zealand",  # added 2026-06-14 (was missing)
    # ── Group H ───────────────────────────────────────────
    "西班牙": "Spain",
    "佛得角": "Cabo Verde",  # 2026-06-14: renamed to "Cabo Verde" (was wrongly "Cape Verde")
    "沙特阿拉伯": "Saudi Arabia",
    "乌拉圭": "Uruguay",  # added 2026-06-14 (was missing)
    # ── Group I ───────────────────────────────────────────
    "法国": "France",
    "塞内加尔": "Senegal",
    "伊拉克": "Iraq",
    "挪威": "Norway",
    # ── Group J ───────────────────────────────────────────
    "阿根廷": "Argentina",
    "阿尔及利亚": "Algeria",  # added 2026-06-14 (was missing)
    "奥地利": "Austria",
    "约旦": "Jordan",  # added 2026-06-14 (was missing)
    # ── Group K ───────────────────────────────────────────
    "葡萄牙": "Portugal",
    "刚果（金）": "DR Congo",
    "乌兹别克斯坦": "Uzbekistan",
    "哥伦比亚": "Colombia",  # added 2026-06-14 (was missing)
    # ── Group L ───────────────────────────────────────────
    "英格兰": "England",
    "克罗地亚": "Croatia",
    "加纳": "Ghana",
    "巴拿马": "Panama",
    # ── Common CCTV aliases / 替补写法 ─────────────────────
    "捷克共和国": "Czechia",
    "中国": "China PR",
    "中国台北": "Chinese Taipei",
    "中国香港": "Hong Kong",
    # Cabo Verde aliases (some CCTV strings may use the older "Cape Verde" spelling)
    "Cape Verde": "Cabo Verde",
    "Cape-Verde": "Cabo Verde",
    "cape verde": "Cabo Verde",
    # DR Congo aliases (different bracket / spacing variants seen in some CCTV feeds)
    "刚果(金)": "DR Congo",
    "刚果（DR）": "DR Congo",
    "民主刚果": "DR Congo",
}


def cn_to_en(name: str) -> str:
    """Translate a CCTV Chinese name to our DB English name (idempotent).

    Strips surrounding whitespace before lookup so trailing spaces in
    CCTV payloads don't break the mapping.
    """
    if not name:
        return name
    return TEAM_CN_TO_EN.get(name, TEAM_CN_TO_EN.get(name.strip(), name))


# ── 英文别名 → 主名 ────────────────────────────────────────────────────────
# ESPN / openfootball 等英文源偶用别名（Ivory Coast / Iran / United States
# / Bosnia-Herzegovina / Cape Verde / Congo DR），如果直接写入 DB 会和
# fixture 的主名（Côte d'Ivoire / IR Iran / USA / Bosnia & Herzegovina /
# Cabo Verde / DR Congo）不匹配，upsert 失败 → INSERT 重复行
# （M123 'Ivory Coast' vs M018 'Côte d'Ivoire' 同一场赛事两个记录）。
# 2026-06-14 修复。
TEAM_EN_ALIAS_TO_CANONICAL: dict[str, str] = {
    "Ivory Coast": "Côte d'Ivoire",
    "Iran": "IR Iran",
    "United States": "USA",
    "Bosnia-Herzegovina": "Bosnia & Herzegovina",
    "Cape Verde": "Cabo Verde",
    "Congo DR": "DR Congo",
}


def en_alias_to_canonical(name: str) -> str:
    """ESPN/openfootball 用的英文别名 → FIFA 官方主名。幂等。
    主名返主名（不变），未知返原值。
    """
    if not name:
        return name
    return TEAM_EN_ALIAS_TO_CANONICAL.get(name, name)


def all_mapped_db_teams() -> set[str]:
    """Return the set of DB team names that the map CAN resolve to.

    Used by tests to assert full 48-team coverage of the live CCTV feed.
    """
    return set(TEAM_CN_TO_EN.values())
