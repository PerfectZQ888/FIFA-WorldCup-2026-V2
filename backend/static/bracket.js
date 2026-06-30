/* ============================================================
 *  V2 对阵图渲染 (CSS Grid + HTML 卡片, 非 ECharts)
 *  - 32 强 (16) → 16 强 (8) → QF (4) → SF (2) → F (1) + 季军赛
 *  - 卡片: 国旗 + 队名 + 胜率条 + 百分比
 *  - AI 预测胜方用青色高亮, TBD 用灰色虚线
 *  - 悬停 tooltip: 时间/场地/详细胜率
 * ============================================================ */
(function () {
  'use strict';

  // ─── 简易国旗/中文名映射 (核心 48 队, 没匹配就用通用符号) ───
  const FLAG = {
    // A–D 已决出
    'Canada': '🇨🇦', 'South Korea': '🇰🇷', 'Qatar': '🇶🇦', 'Switzerland': '🇨🇭',
    'Brazil': '🇧🇷', 'Morocco': '🇲🇦', 'Haiti': '🇭🇹', 'Scotland': '🏴󠁧󠁢󠁳󠁣󠁴󠁿',
    'USA': '🇺🇸', 'Paraguay': '🇵🇾', 'Australia': '🇦🇺', 'Turkey': '🇹🇷',
    'Mexico': '🇲🇽', 'South Africa': '🇿🇦', 'Denmark': '🇩🇰', 'Iraq': '🇮🇶',
    // 待定分组
    'Germany': '🇩🇪', 'Netherlands': '🇳🇱', 'Japan': '🇯🇵', 'France': '🇫🇷',
    'Argentina': '🇦🇷', 'Spain': '🇪🇸', 'Portugal': '🇵🇹', 'England': '🏴󠁧󠁢󠁥󠁮󠁧󠁿',
    'Belgium': '🇧🇪', 'Croatia': '🇭🇷', 'Italy': '🇮🇹', 'Uruguay': '🇺🇾',
    'Colombia': '🇨🇴', 'Ecuador': '🇪🇨', 'Chile': '🇨🇱', 'Peru': '🇵🇪',
    'Iran': '🇮🇷', 'Saudi Arabia': '🇸🇦', 'UAE': '🇦🇪', 'China': '🇨🇳',
    'India': '🇮🇳', 'Thailand': '🇹🇭', 'Vietnam': '🇻🇳', 'Indonesia': '🇮🇩',
    'Poland': '🇵🇱', 'Sweden': '🇸🇪', 'Norway': '🇳🇴', 'Ukraine': '🇺🇦',
    'Serbia': '🇷🇸', 'Slovakia': '🇸🇰', 'Czechia': '🇨🇿', 'Austria': '🇦🇹',
    'Ghana': '🇬🇭', 'Senegal': '🇸🇳', 'Nigeria': '🇳🇬', 'Cameroon': '🇨🇲',
    'Egypt': '🇪🇬', 'Tunisia': '🇹🇳', 'Algeria': '🇩🇿', 'Ivory Coast': '🇨🇮',
    'New Zealand': '🇳🇿', 'Jamaica': '🇯🇲', 'Costa Rica': '🇨🇷', 'Panama': '🇵🇦',
  };
  const TEAM_CN = {
    'Canada': '加拿大', 'South Korea': '韩国', 'Qatar': '卡塔尔', 'Switzerland': '瑞士',
    'Brazil': '巴西', 'Morocco': '摩洛哥', 'Haiti': '海地', 'Scotland': '苏格兰',
    'USA': '美国', 'Paraguay': '巴拉圭', 'Australia': '澳大利亚', 'Turkey': '土耳其',
    'Mexico': '墨西哥', 'South Africa': '南非', 'Denmark': '丹麦', 'Iraq': '伊拉克',
    'Germany': '德国', 'Netherlands': '荷兰', 'Japan': '日本', 'France': '法国',
    'Argentina': '阿根廷', 'Spain': '西班牙', 'Portugal': '葡萄牙', 'England': '英格兰',
    'Belgium': '比利时', 'Croatia': '克罗地亚', 'Italy': '意大利', 'Uruguay': '乌拉圭',
    'Colombia': '哥伦比亚', 'Ecuador': '厄瓜多尔', 'Chile': '智利', 'Peru': '秘鲁',
    'Iran': '伊朗', 'Saudi Arabia': '沙特', 'UAE': '阿联酋', 'China': '中国',
    'India': '印度', 'Thailand': '泰国', 'Vietnam': '越南', 'Indonesia': '印尼',
    'Poland': '波兰', 'Sweden': '瑞典', 'Norway': '挪威', 'Ukraine': '乌克兰',
    'Serbia': '塞尔维亚', 'Slovakia': '斯洛伐克', 'Czechia': '捷克', 'Austria': '奥地利',
    'Ghana': '加纳', 'Senegal': '塞内加尔', 'Nigeria': '尼日利亚', 'Cameroon': '喀麦隆',
    'Egypt': '埃及', 'Tunisia': '突尼斯', 'Algeria': '阿尔及利亚', 'Ivory Coast': '科特迪瓦',
    'New Zealand': '新西兰', 'Jamaica': '牙买加', 'Costa Rica': '哥斯达黎加', 'Panama': '巴拿马',
  };

  const ROUND_CN = {
    'Round of 32':    '32 强',
    'Round of 16':    '16 强',
    'Quarter-finals': '1/4 决赛',
    'Semi-finals':    '半决赛',
    'Final':          '决赛',
    'Third place':    '季军赛',
  };
  const ROUND_TBD_LABEL = { 0: '小组赛', 1: '32 强', 2: '16 强', 3: '8 强' };
  const ROUND_COUNT     = { 0: 16, 1: 8, 2: 4, 3: 2, 4: 1 };

  let matches = [];
  let tooltipEl = null;

  document.addEventListener('DOMContentLoaded', init);

  async function init() {
    tooltipEl = document.getElementById('tooltip');
    const grid = document.getElementById('bracketGrid');

    bindToolbar();

    // V2 状态条: 健康轮询
    pollHealth();

    try {
      const resp = await fetch('/api/bracket');
      if (!resp.ok) throw new Error('HTTP ' + resp.status);
      const data = await resp.json();
      matches = data.matches.filter(m => m.round !== 'Third place');
      // 季军赛单独存
      const third = data.matches.find(m => m.round === 'Third place');

      updateHeaderStats();
      render(grid, third);
      drawWires();

      document.getElementById('updateTs').textContent = new Date().toLocaleString('zh-CN', { hour12: false });
    } catch (e) {
      grid.innerHTML = '<div class="error">❌ 加载失败: ' + e.message + '</div>';
    }
  }

  function bindToolbar() {
    document.getElementById('btnReload').addEventListener('click', () => location.reload());
    var explain = document.getElementById('bkExplain');
    document.getElementById('btnToggleHelp').addEventListener('click', function() {
      explain.style.display = explain.style.display === 'none' ? 'block' : 'none';
    });
    document.getElementById('btnCloseHelp').addEventListener('click', function() {
      explain.style.display = 'none';
    });
  }

  function pollHealth() {
    const lastEl = document.getElementById('v2LastUpdate');
    const healthEl = document.getElementById('v2Health');
    if (!lastEl) return;
    const pad = n => n < 10 ? '0' + n : n;
    const fmt = d => pad(d.getHours()) + ':' + pad(d.getMinutes()) + ':' + pad(d.getSeconds());
    async function tick() {
      try {
        const r = await fetch('/api/health', { cache: 'no-store' });
        if (!r.ok) throw new Error(r.status);
        lastEl.textContent = '更新 ' + fmt(new Date());
        if (healthEl) { healthEl.textContent = '健康 ✓'; healthEl.classList.remove('bad'); }
      } catch (e) {
        if (healthEl) { healthEl.textContent = '异常 ✗'; healthEl.classList.add('bad'); }
      }
    }
    tick();
    setInterval(tick, 10000);
  }

  function updateHeaderStats() {
    document.getElementById('statMatches').textContent = matches.length;
    const r32 = matches.filter(m => m.round === 'Round of 32').length;
    document.getElementById('statTeams').textContent = r32 * 2;
    const rounds = new Set(matches.map(m => m.round)).size;
    document.getElementById('statRounds').textContent = rounds;
    const predicted = matches.filter(m => m.predicted_winner && m.predicted_winner !== 'TBD').length;
    document.getElementById('statPredicted').textContent = predicted + ' / ' + matches.length;

    const setPill = (id, n, label) => {
      const el = document.getElementById(id);
      if (el) el.textContent = label + ' · ' + n + ' 场';
    };
    setPill('pillR32', matches.filter(m => m.round === 'Round of 32').length,    '32 强');
    setPill('pillR16', matches.filter(m => m.round === 'Round of 16').length,    '16 强');
    setPill('pillQF',  matches.filter(m => m.round === 'Quarter-finals').length, '1/4 决赛');
    setPill('pillSF',  matches.filter(m => m.round === 'Semi-finals').length,    '半决赛');
    setPill('pillF',   matches.filter(m => m.round === 'Final').length,          '决赛');
  }

  // ─── 渲染网格 ───
  function render(grid, thirdPlace) {
    grid.innerHTML = '';

    // 5 个轮次标题
    ['Round of 32', 'Round of 16', 'Quarter-finals', 'Semi-finals', 'Final'].forEach((round, col) => {
      const head = document.createElement('div');
      head.className = 'round-head col-' + col;
      head.innerHTML = ROUND_CN[round] + '<span class="count">' + ROUND_COUNT[col] + ' 场</span>';
      grid.appendChild(head);
    });

    // 31 张比赛卡 - 显式设置 grid-row (按 col + row 计算, 避免 auto-placement 问题)
    matches.forEach(m => {
      const card = buildCard(m);
      // 显式指定 grid-row:
      //   R32 (col=0): 1 行/卡, grid row = m.row + 1
      //   R16 (col=1): 2 行/卡, grid row = m.row * 2 + 1, span 2
      //   QF  (col=2): 4 行/卡, grid row = m.row * 4 + 1, span 4
      //   SF  (col=3): 8 行/卡, grid row = m.row * 8 + 1, span 8
      //   F   (col=4): 16 行/卡, grid row = 1,             span 16
      const gridRowStart = m.row * Math.pow(2, m.col) + 1;
      const gridRowSpan  = Math.pow(2, m.col);
      card.style.gridRow = gridRowStart + ' / span ' + gridRowSpan;
      grid.appendChild(card);
    });

    // 季军赛放最右侧额外列 (用 col-4 同行, 偏移)
    if (thirdPlace) {
      const card = buildCard(thirdPlace);
      card.style.gridColumn = '5';
      card.style.gridRow = '14 / span 2';
      card.classList.add('is-third');
      grid.appendChild(card);
    }
  }

  function buildCard(m) {
    const card = document.createElement('div');
    card.className = 'card col-' + m.col;
    card.dataset.matchId = m.match_id;
    card.dataset.round = m.round;

    const predicted = m.predicted_winner && m.predicted_winner !== 'TBD';
    if (predicted) {
      card.classList.add('is-predicted');
      if (m.round === 'Final') card.classList.add('is-champion');
    } else {
      card.classList.add('is-tbd');
    }

    // 顶部条: 比赛ID + 预测比分
    const top = document.createElement('div');
    top.className = 'top-bar';
    // v1.4.0: 如果该比赛已踢完且点球决胜, 在 top-bar 加 PK 角标
    const isFinished = m.status === 'finished';
    const isShootout = isFinished && m.decided_by_penalties;
    const actualScore = isFinished && m.home_score != null
      ? (m.home_score + '-' + m.away_score
          + (isShootout ? ' <span class="shootout-tag" title="点球大战 ' + esc(m.home_pen_score + '-' + m.away_pen_score) + ' 晋级">(点球)</span>' : ''))
      : null;
    top.innerHTML =
      '<span class="match-id">' + esc(m.match_id) + '</span>' +
      '<span class="score">' + (actualScore || (predicted ? esc(m.predicted_score) : '—')) + '</span>';
    card.appendChild(top);

    if (predicted) {
      card.appendChild(buildTeamRow(m, 'home'));
      card.appendChild(buildTeamRow(m, 'away'));

      // 不再在卡片内显示时间/场地 (移到 tooltip), 避免卡片过高撑爆行
    } else {
      const tbd = document.createElement('div');
      tbd.className = 'tbd-msg';
      let label = '待 AI 预测';
      if (m.col === 0) {
        label = m.is_placeholder ? '⏳ 待小组赛决出' : '⏳ 待 AI 预测';
      } else if (m.col > 0) {
        label = '⏳ 等待 ' + (ROUND_TBD_LABEL[m.col - 1] || '') + ' 决出';
      }
      const lblEl = document.createElement('div');
      lblEl.className = 'tbd-label';
      lblEl.textContent = label;
      tbd.appendChild(lblEl);

      const up = document.createElement('div');
      up.className = 'tbd-upstream';
      const home = m.home_team_resolved || m.home_team || '?';
      const away = m.away_team_resolved || m.away_team || '?';
      up.textContent = teamLabel(home) + '  vs  ' + teamLabel(away);
      tbd.appendChild(up);

      const tag = document.createElement('div');
      tag.className = 'tbd-tag';
      tag.textContent = 'M' + (m.match_id || '').replace(/\D/g, '');
      tbd.appendChild(tag);

      card.appendChild(tbd);
    }

    card.addEventListener('mouseenter', e => showTooltip(m, card));
    card.addEventListener('mouseleave', hideTooltip);
    card.addEventListener('mousemove',  e => moveTooltip(e));

    return card;
  }

  function buildTeamRow(m, side) {
    const row = document.createElement('div');
    row.className = 'team-row';

    const resolved  = side === 'home' ? m.home_team_resolved : m.away_team_resolved;
    const rawName   = side === 'home' ? m.home_team : m.away_team;
    const winner    = m.predicted_winner;
    const homeRes   = m.home_team_resolved || m.home_team;
    const awayRes   = m.away_team_resolved || m.away_team;
    const isWin     = (side === 'home' && winner === homeRes) || (side === 'away' && winner === awayRes);
    row.classList.add(isWin ? 'winner' : 'loser');

    const name = resolved || rawName || '—';
    const cn   = resolved ? (TEAM_CN[resolved] || resolved) : (W_WINNER.test(rawName) ? '上游胜者' : rawName);

    const flag = document.createElement('span');
    flag.className = 'flag';
    // 优先用 emoji 国旗; 若字体不支持 (显示成方框) 浏览器会回退到 country code
    var flagEmoji = FLAG[resolved] || (resolved ? '🏳️' : (W_WINNER.test(rawName) ? '⬆️' : '·'));
    flag.textContent = flagEmoji;
    row.appendChild(flag);

    const nm = document.createElement('span');
    nm.className = 'team-name';
    nm.textContent = cn;
    row.appendChild(nm);

    const prob = side === 'home' ? (m.home_win_prob || 0) : (m.away_win_prob || 0);
    const track = document.createElement('div');
    track.className = 'prob-track';
    track.innerHTML = '<span class="prob-fill" style="width:' + Math.max(2, prob).toFixed(1) + '%"></span>';
    row.appendChild(track);

    const pct = document.createElement('span');
    pct.className = 'pct';
    pct.textContent = (prob || 0).toFixed(0) + '%';
    row.appendChild(pct);

    return row;
  }

  const W_WINNER = /^W\d+$/;

  function teamLabel(name) {
    if (!name) return '—';
    if (W_WINNER.test(name)) return 'W 胜者';
    return (FLAG[name] || '🏳️') + ' ' + (TEAM_CN[name] || name);
  }

  // ─── Tooltip ───
  function showTooltip(m, cardEl) {
    const lines = [];
    lines.push('<div class="t-head">' + esc(m.match_id) + ' · ' + (ROUND_CN[m.round] || m.round) + '</div>');

    const predicted = m.predicted_winner && m.predicted_winner !== 'TBD';
    if (predicted) {
      const home = teamLabel(m.home_team_resolved || m.home_team);
      const away = teamLabel(m.away_team_resolved || m.away_team);
      lines.push('<div class="t-row"><b>' + home + '</b>  vs  <b>' + away + '</b></div>');
      lines.push('<div class="t-row">胜率 · 主 <b>' + (m.home_win_prob || 0).toFixed(1) + '%</b> / 客 <b>' + (m.away_win_prob || 0).toFixed(1) + '%</b></div>');
      if (m.predicted_score) {
        lines.push('<div class="t-row">预测比分 · <b style="color:#d4af37">' + esc(m.predicted_score) + '</b></div>');
      }
      // v1.4.0: 实际比分 + 点球大战信息
      if (isFinished && m.home_score != null) {
        lines.push('<div class="t-row">实际比分 · <b style="color:#a3e635">' + esc(m.home_score + '-' + m.away_score) + '</b></div>');
        if (isShootout && m.home_pen_score != null) {
          lines.push('<div class="t-row">点球大战 · <b style="color:#ff8a9e">' + esc(m.home_pen_score + '-' + m.away_pen_score) + '</b> 晋级</div>');
        }
      }
      lines.push('<div class="t-pred">🏆 AI 预测胜方: ' + esc(m.predicted_winner) + '</div>');
    } else {
      lines.push('<div class="t-tbd">⏳ 对阵尚未确定</div>');
      lines.push('<div class="t-row">等待上游比赛决出</div>');
    }

    const t = m.match_date ? m.match_date + (m.match_time ? ' ' + m.match_time : '') : '';
    if (t)    lines.push('<div class="t-meta">⏰ ' + esc(t) + '</div>');
    if (m.venue) lines.push('<div class="t-meta">📍 ' + esc(m.venue) + '</div>');

    tooltipEl.innerHTML = lines.join('');
    tooltipEl.classList.add('show');
    positionTooltip(cardEl);
  }

  function positionTooltip(cardEl) {
    const r = cardEl.getBoundingClientRect();
    const tw = tooltipEl.offsetWidth;
    const th = tooltipEl.offsetHeight;
    let left = r.right + 12;
    let top  = r.top;
    if (left + tw > window.innerWidth - 10)  left = r.left - tw - 12;
    if (left < 10) left = 10;
    if (top + th > window.innerHeight - 10) top = window.innerHeight - th - 10;
    if (top < 10) top = 10;
    tooltipEl.style.left = left + 'px';
    tooltipEl.style.top  = top + 'px';
  }

  function moveTooltip(e) {
    if (!tooltipEl.classList.contains('show')) return;
    const tw = tooltipEl.offsetWidth, th = tooltipEl.offsetHeight;
    let left = e.clientX + 14, top = e.clientY + 14;
    if (left + tw > window.innerWidth - 10)  left = e.clientX - tw - 14;
    if (top  + th > window.innerHeight - 10) top  = e.clientY - th - 14;
    tooltipEl.style.left = left + 'px';
    tooltipEl.style.top  = top + 'px';
  }

  function hideTooltip() { tooltipEl.classList.remove('show'); }

  function esc(s) { return String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }

  // ─── SVG 连线 (ECharts 替代方案, 改用 SVG 更稳定) ───
  function drawWires() {
    const grid = document.getElementById('bracketGrid');
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.classList.add('wires-layer');
    svg.style.cssText = 'position:absolute;inset:60px 32px 40px;width:calc(100% - 64px);height:calc(100% - 100px);pointer-events:none;z-index:1;';
    grid.appendChild(svg);

    // 等 DOM 布局完再算坐标
    requestAnimationFrame(() => {
      const gridRect = grid.getBoundingClientRect();
      const colWidth = parseInt(getComputedStyle(grid).getPropertyValue('--col-w'));
      const rowHeight = parseInt(getComputedStyle(grid).getPropertyValue('--row-h'));
      const colGap = 32, rowGap = 10;

      // 对每场比赛画一条从右边缘出发的横线
      matches.forEach(m => {
        if (m.col >= 4) return; // 决赛不画
        const card = grid.querySelector('.card[data-match-id="' + m.match_id + '"]');
        if (!card) return;
        const r = card.getBoundingClientRect();
        const x1 = r.right - gridRect.left;
        const y1 = r.top + r.height / 2 - gridRect.top;
        // 终点: 下一轮该 match 的 row = floor(m.row/2) 的卡片左边
        const target = matches.find(x => x.col === m.col + 1 && x.row === Math.floor(m.row / 2));
        if (!target) return;
        const tCard = grid.querySelector('.card[data-match-id="' + target.match_id + '"]');
        if (!tCard) return;
        const tr = tCard.getBoundingClientRect();
        const x2 = tr.left - gridRect.left;
        const y2 = tr.top + tr.height / 2 - gridRect.top;
        const xm = (x1 + x2) / 2;

        const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        path.setAttribute('d', 'M ' + x1 + ' ' + y1 + ' L ' + xm + ' ' + y1 + ' L ' + xm + ' ' + y2 + ' L ' + x2 + ' ' + y2);
        path.setAttribute('stroke', m.predicted_winner && m.predicted_winner !== 'TBD' ? 'rgba(79,209,197,0.35)' : 'rgba(255,255,255,0.12)');
        path.setAttribute('stroke-width', '1.5');
        path.setAttribute('fill', 'none');
        svg.appendChild(path);
      });
    });

    window.addEventListener('resize', () => {
      // 重新画线
      svg.innerHTML = '';
      requestAnimationFrame(() => {
        const gridRect = grid.getBoundingClientRect();
        matches.forEach(m => {
          if (m.col >= 4) return;
          const card = grid.querySelector('.card[data-match-id="' + m.match_id + '"]');
          if (!card) return;
          const r = card.getBoundingClientRect();
          const x1 = r.right - gridRect.left;
          const y1 = r.top + r.height / 2 - gridRect.top;
          const target = matches.find(x => x.col === m.col + 1 && x.row === Math.floor(m.row / 2));
          if (!target) return;
          const tCard = grid.querySelector('.card[data-match-id="' + target.match_id + '"]');
          if (!tCard) return;
          const tr = tCard.getBoundingClientRect();
          const x2 = tr.left - gridRect.left;
          const y2 = tr.top + tr.height / 2 - gridRect.top;
          const xm = (x1 + x2) / 2;
          const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
          path.setAttribute('d', 'M ' + x1 + ' ' + y1 + ' L ' + xm + ' ' + y1 + ' L ' + xm + ' ' + y2 + ' L ' + x2 + ' ' + y2);
          path.setAttribute('stroke', m.predicted_winner && m.predicted_winner !== 'TBD' ? 'rgba(79,209,197,0.35)' : 'rgba(255,255,255,0.12)');
          path.setAttribute('stroke-width', '1.5');
          path.setAttribute('fill', 'none');
          svg.appendChild(path);
        });
      });
    });
  }
})();
