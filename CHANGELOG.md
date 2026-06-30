# 📝 Changelog

所有 V2 项目的版本变更记录。格式基于 [Keep a Changelog](https://keepachangelog.com/)。

> 💡 **完整 release notes** 在 [`RELEASE_NOTES/`](./RELEASE_NOTES/) 目录。
> 🌐 **GitHub Releases** 见 https://github.com/PerfectZQ888/FIFA-WorldCup-2026-V2/releases

## [v1.4.1] - 2026-06-30

### 🐛 Fixed (直播中心数据修复)
- **赛事直播中心名称/数据错误** (用户反馈)
  - 症状: `/api/matches/live` 返回占位符 ("1F"/"2C"/"3rd-ABCDF") 和假比赛 ("Germany vs Third Place Group A/B/C/D/F")
  - 根因 1: R32 比赛 (M073-M088) 在 seed 中用占位符, 小组赛结束前 CCTV 没法匹配
  - 根因 2: CCTV 偶尔会发 "Third Place Group X/Y/Z" / "Group I Winner" 等占位文本当 team name, 之前 scraper 误插入 (M105-M108)
  - 根因 3: 完赛 R32 的 home_score/away_score 用的是含 PK 的"实时比分"(4-5), 应是 90 分钟比分 (1-1) + 单独 PK 字段

### ✨ Added (新功能)
- **bracket slot resolver**: 从小组赛 standings 自动解析 "1A" → Mexico, "3rd-ABCDF" → best 3rd from A,B,C,D,F (排除已分配)
- **CCTV 16 场 R32 真实数据回填**: 3 场已完赛 (含 1 场点球大战 德国 1-1 巴拉圭 PK 3-4) + 13 场待开赛的真队名
- **scraper 防御层**: `_is_placeholder_team()` 12 种占位符 regex 模式, 防止 "Third Place Group ..." / "Group I Winner" / "1A" / "W73" 等污染 DB
- **/api/matches/live 防御层**: SQL `NOT GLOB`/`NOT LIKE` 过滤 8 种占位符模式, 即使 DB 有残留也不返回
- **CCTV scores.Penalties 解析**: `home_pen_score`/`away_pen_score`/`decided_by_penalties` 三个字段从 CCTV `scores.Penalties.team1/2` 自动填充

### 🗑️ Removed
- **M105-M108 (4 个假 3rd place 比赛)**: 由 scraper 误插入, 不存在于 FIFA 2026 真实赛程. 已 DELETE.

### 🐛 Fixed (bug 修复)
- **scraper 4-tuple unpack 错误**: v1.4.0 加了 3 个 PK 字段后, `mid, old_h, old_a, old_status = row` 实际 row 有 7 列, 报 "too many values to unpack". 改为 7-tuple unpack.
- **scraper 实时/全赛分数混用**: 完赛用 `homeFullScore`(90min 比分) 而非 `homeScore`(含 PK 的总比分). 实时/未开赛仍用 `homeScore`.

### 📦 Stats
- Files: 3 modified (app.py, cctv_espn_live.py, CHANGELOG.md)
- API: `/api/matches/live` SQL 加 8 个 NOT GLOB/NOT LIKE 过滤
- DB: M105-M108 4 行 DELETE, M073-M088 16 行 UPDATE 队名/状态/分数, M074 1 行 UPDATE 加 PK 字段
- 防御: 12 个 placeholder regex patterns in scraper

---

## [v1.4.0] - 2026-06-30

### ✨ Added (新功能)
- **点球大战 (Penalty Shootout) 完整支持**
  - Schema: `matches` 加 3 列 (`home_pen_score` / `away_pen_score` / `decided_by_penalties`)
  - Schema: `bracket` 加 1 列 (`winner_via_penalties`)
  - 启动时自动 `migrate_db()` (idempotent, 已存在的列不重复加)
  - Scraper: `fetch_espn_shootout(espn_id)` 解析 ESPN summary 中 "Penalty Shootout ends, ..." 文本
  - 触发条件: 比赛 status = `FT-Pens` → 自动补抓 summary → 写 home/away_pen_score
  - Regex 测试通过 WC 2022 真实点球比赛 (Croatia 4-2 Brazil, Argentina 4-3 Netherlands, 等)
  - 手动补录端点: `POST /api/admin/matches/{id}/shootout` (Pydantic 校验 home/away_pen_score 0-20)
  - 自动同步 `bracket.winner` (从占位 → 实际赢家) + `bracket.winner_via_penalties=1`

### 🔄 Changed
- `/api/matches` / `/api/matches/{id}` / `/api/matches/live`: 自动输出新字段 (用 `SELECT *`)
- `/api/knockout` / `/api/bracket`: SELECT 显式列新字段, 节点 dict 注入 `shootout_score` 等
- 前端: 比赛详情弹窗显示 "⚽ 点球大战 X : Y" 渐变徽章
- 前端: 比赛列表卡已完赛比赛加 "⚽点球 X:Y" 角标
- 前端: bracket 卡片显示实际比分 + "(点球)" 角标, tooltip 加 "点球大战 X-Y 晋级" 行
- CSS: `.shootout-badge` / `.shootout-score` / `.pk-inline` / `.shootout-tag` 4 个新样式

### 📦 Stats
- Files: 6 modified (app.py, cctv_espn_live.py, app.js, bracket.js, style.css, bracket.css)
- 代码: +378 / -14 行
- API 字段: +6 (matches 3, bracket 1, bracket-node 2)
- 新端点: 1 (`POST /api/admin/matches/{id}/shootout`)

---

## [v1.3.0] - 2026-06-19

### ✨ Added (新功能)
- **跨平台支持**
  - macOS launchd 适配 (`backend/wc2026-v2.plist` + install/uninstall 脚本)
  - Windows 启动脚本 (CMD `.bat` + PowerShell `.ps1` 彩色输出)
  - `requirements-windows.txt` (去掉 `uvloop`)
  - `start.sh` 重写为跨平台 (兼容 bash 3.2, 4 级端口检查 fallback)
- **文档**
  - README.md 加「🌐 跨平台支持」章节
  - DEPLOY.md 加 Windows Task Scheduler + macOS launchd 详细部署
  - CHANGELOG.md（本文件）
  - `RELEASE_NOTES/v1.3.0.md` 详细 release notes

### 🔒 Security (安全加固)
- 修复 3 处内网 IP 硬编码泄露 (`http://192.0.2.1:8001/`)
  - `backend/static/app.js` 分享文本 → `window.location.origin`
  - `backend/static/index.html` `og:url` → `http://localhost:8001/`
  - `backend/static/index.html` `canonical` → `http://localhost:8001/`
- 全仓敏感扫描: 36 文件 12 模式 0 命中
- `.gitignore` 加 `REPORT.md` / `.release/` 排除规则

### 🔄 Changed
- `start.sh` / `stop.sh` / `status.sh` 全面跨平台化
- 端口检查改 4 级 fallback: `lsof` → `ss` → `netstat` → `/dev/tcp`
- 服务检测: systemd (Linux) / launchd (macOS) / 手动 (Windows)

### 📦 Stats
- Commits: 2 (a432fa5 → 3e7cea9)
- Files: 39 (新增 10 + 修改 7 + 不变 22)
- 代码: +858 / -98 行

---

## [v1.2] - 2026-06-19 (内部版, 未公开发布)

### ✨ Added
- v1.2 前端优化版（5 文件拆分 + ECharts ChartManager 单例）
- 准确率徽章 + 响应式 + 可访问性优化
- AI 预测文案优化（"主推:" → "🏆 胜方:"）

---

## 链接

- [v1.3.0 Release Notes](./RELEASE_NOTES/v1.3.0.md)
- [GitHub Releases](https://github.com/PerfectZQ888/FIFA-WorldCup-2026-V2/releases)
- [README](./README.md)
- [DEPLOY Guide](./DEPLOY.md)
