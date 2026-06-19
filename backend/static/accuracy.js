/* ============================================================
   预测命中率仪表盘 (v1.1)
   - 4 项核心 KPI
   - 累计准确率走势
   - 概率校准散点图
   - 校准区间对比表
   - 冷门榜
   ============================================================ */

'use strict';

window.AccuracyDashboard = (() => {
  const GOLD = '#d4af37', GOLD2 = '#f9d76b';
  const GREEN = '#00d68f', RED = '#ff5577', BLUE = '#4ea8ff';
  const TEXT = '#e9eef7', DIM = '#93a3bd', MUTE = '#5d6d85';

  let matches = [];
  let initialized = false;

  async function init() {
    if (initialized) return;
    try {
      const data = await fetch('/api/matches?limit=500').then(r => r.json());
      matches = data.filter(m => m.status === 'finished' 
        && m.predicted_winner && m.predicted_winner !== 'TBD'
        && m.predicted_home_score != null && m.predicted_away_score != null);
      
      if (!matches.length) {
        renderEmpty();
        return;
      }
      
      renderKPIs();
      renderTrendChart();
      renderCalibrationChart();
      renderCalibrationTable();
      renderUpsets();
      
      initialized = true;
    } catch (e) {
      console.error('Accuracy dashboard init failed', e);
    }
  }

  // 共享工具: 实际胜者 (从 app.js 复用, v1.2 去重)
  const getActualWinner = (m) => {
    if (m.home_score > m.away_score) return m.home_team;
    if (m.home_score < m.away_score) return m.away_team;
    return 'draw';
  };

  // ============================================================
  // KPI 卡片
  // ============================================================
  function renderKPIs() {
    const n = matches.length;
    let w = 0, e = 0, gd = 0, dir = 0;
    for (const m of matches) {
      const actual = getActualWinner(m);
      if (m.predicted_winner === actual) w++;
      if (m.predicted_home_score === m.home_score && m.predicted_away_score === m.away_score) e++;
      if ((m.predicted_home_score - m.predicted_away_score) === (m.home_score - m.away_score)) gd++;
      const pDir = m.predicted_home_score > m.predicted_away_score ? 'H' 
                  : m.predicted_home_score < m.predicted_away_score ? 'A' : 'D';
      const aDir = m.home_score > m.away_score ? 'H' : m.home_score < m.away_score ? 'A' : 'D';
      if (pDir === aDir) dir++;
    }
    
    // Brier Score
    let brier = 0;
    for (const m of matches) {
      const a = [0, 0, 0];
      if (m.home_score > m.away_score) a[0] = 1;
      else if (m.home_score === m.away_score) a[1] = 1;
      else a[2] = 1;
      const p = [m.home_win_prob/100, m.draw_prob/100, m.away_win_prob/100];
      brier += (p[0]-a[0])**2 + (p[1]-a[1])**2 + (p[2]-a[2])**2;
    }
    brier /= n;

    const drawActual = matches.filter(m => m.home_score === m.away_score).length;
    const drawPredAvg = matches.reduce((s, m) => s + m.draw_prob, 0) / n;

    const html = `
      <div class="acc-kpi green">
        <div class="label">胜平负命中率</div>
        <div class="value">${(w/n*100).toFixed(1)}%</div>
        <div class="detail"><strong>${w}</strong> / ${n} 场 · 预测胜方与实际一致</div>
      </div>
      <div class="acc-kpi">
        <div class="label">精确比分命中率</div>
        <div class="value">${(e/n*100).toFixed(1)}%</div>
        <div class="detail"><strong>${e}</strong> / ${n} 场 · 完全猜中比分</div>
      </div>
      <div class="acc-kpi blue">
        <div class="label">Brier Score</div>
        <div class="value">${brier.toFixed(3)}</div>
        <div class="detail">越低越好 · 随机基线 0.667 · 完美 0.000</div>
      </div>
      <div class="acc-kpi ${drawActual/n > drawPredAvg/100 ? 'red' : 'green'}">
        <div class="label">平局偏差</div>
        <div class="value">${drawActual/n*100 > drawPredAvg ? '↑' : '↓'}${Math.abs(drawActual/n*100 - drawPredAvg).toFixed(1)}pp</div>
        <div class="detail">实际 <strong>${(drawActual/n*100).toFixed(1)}%</strong> vs 预测均值 <strong>${drawPredAvg.toFixed(1)}%</strong></div>
      </div>
    `;
    const el = document.getElementById('accKpiGrid');
    if (el) el.innerHTML = html;
  }

  // ============================================================
  // 累计准确率走势
  // ============================================================
  function renderTrendChart() {
    const sorted = [...matches].sort((a, b) => (a.match_date + a.match_time).localeCompare(b.match_date + b.match_time));
    let cumW = 0, cumE = 0, cumDir = 0;
    const labels = [], winnerPct = [], scorePct = [], dirPct = [];
    
    sorted.forEach((m, i) => {
      const actual = getActualWinner(m);
      if (m.predicted_winner === actual) cumW++;
      if (m.predicted_home_score === m.home_score && m.predicted_away_score === m.away_score) cumE++;
      const pDir = m.predicted_home_score > m.predicted_away_score ? 'H' 
                  : m.predicted_home_score < m.predicted_away_score ? 'A' : 'D';
      const aDir = m.home_score > m.away_score ? 'H' : m.home_score < m.away_score ? 'A' : 'D';
      if (pDir === aDir) cumDir++;
      const t = i + 1;
      labels.push(`${m.match_date.slice(5)} ${(m.match_time||'').slice(0,5)}`);
      winnerPct.push((cumW/t*100).toFixed(1));
      scorePct.push((cumE/t*100).toFixed(1));
      dirPct.push((cumDir/t*100).toFixed(1));
    });

    ChartManager.set('chartAccTrend', {
      backgroundColor: 'transparent',
      tooltip: { trigger: 'axis',
        backgroundColor: 'rgba(15,28,48,0.95)', borderColor: GOLD, textStyle: { color: TEXT } },
      legend: { data: ['胜平负命中率', '结果方向命中率', '精确比分命中率'], 
        textStyle: { color: DIM, fontSize: 11 }, top: 0 },
      grid: { left: 50, right: 30, top: 36, bottom: 30 },
      xAxis: { type: 'category', data: labels, 
        axisLine: { lineStyle: { color: MUTE } }, 
        axisLabel: { color: DIM, fontSize: 10, rotate: 30 } },
      yAxis: { type: 'value', min: 0, max: 100,
        axisLine: { lineStyle: { color: MUTE } },
        axisLabel: { color: DIM, formatter: '{value}%' },
        splitLine: { lineStyle: { color: 'rgba(255,255,255,0.04)' } } },
      series: [
        { name: '胜平负命中率', type: 'line', smooth: true, data: winnerPct,
          itemStyle: { color: GREEN }, lineStyle: { width: 2.5 },
          areaStyle: { opacity: 0.15, color: GREEN }, symbol: 'circle', symbolSize: 5 },
        { name: '结果方向命中率', type: 'line', smooth: true, data: dirPct,
          itemStyle: { color: BLUE }, lineStyle: { width: 2 }, symbol: 'circle', symbolSize: 4 },
        { name: '精确比分命中率', type: 'line', smooth: true, data: scorePct,
          itemStyle: { color: GOLD2 }, lineStyle: { width: 2, type: 'dashed' }, symbol: 'circle', symbolSize: 4 }
      ]
    });
  }

  // ============================================================
  // 概率校准散点图
  // ============================================================
  function renderCalibrationChart() {
    // 按预测概率区间分组，计算实际胜率
    const buckets = [
      { lo: 0, hi: 10 }, { lo: 10, hi: 20 }, { lo: 20, hi: 30 }, { lo: 30, hi: 40 },
      { lo: 40, hi: 50 }, { lo: 50, hi: 60 }, { lo: 60, hi: 70 }, { lo: 70, hi: 80 },
      { lo: 80, hi: 90 }, { lo: 90, hi: 100.1 }
    ];
    const points = [];
    
    buckets.forEach(b => {
      // 收集该概率区间内的所有"最看好选项"实际命中情况
      let total = 0, hits = 0;
      for (const m of matches) {
        const probs = { H: m.home_win_prob, D: m.draw_prob, A: m.away_win_prob };
        for (const [key, p] of Object.entries(probs)) {
          if (p >= b.lo && p < b.hi) {
            total++;
            const aDir = m.home_score > m.away_score ? 'H' : m.home_score < m.away_score ? 'A' : 'D';
            if (key === aDir) hits++;
          }
        }
      }
      if (total > 0) {
        points.push({
          value: [(b.lo + b.hi) / 2, hits / total * 100],
          count: total,
          lo: b.lo, hi: b.hi
        });
      }
    });

    ChartManager.set('chartAccCalib', {
      backgroundColor: 'transparent',
      tooltip: { trigger: 'item',
        formatter: p => {
          const d = p.data;
          return `预测概率: <b>${d.lo}-${d.hi}%</b><br/>实际频率: <b style="color:${GOLD2}">${d.value[1].toFixed(1)}%</b><br/>样本数: ${d.count}`;
        },
        backgroundColor: 'rgba(15,28,48,0.95)', borderColor: GOLD, textStyle: { color: TEXT } },
      grid: { left: 50, right: 30, top: 20, bottom: 40 },
      xAxis: { type: 'value', name: '预测概率', min: 0, max: 100,
        nameTextStyle: { color: DIM, fontSize: 10 },
        axisLine: { lineStyle: { color: MUTE } },
        axisLabel: { color: DIM, formatter: '{value}%' },
        splitLine: { lineStyle: { color: 'rgba(255,255,255,0.04)' } } },
      yAxis: { type: 'value', name: '实际频率', min: 0, max: 100,
        nameTextStyle: { color: DIM, fontSize: 10 },
        axisLine: { lineStyle: { color: MUTE } },
        axisLabel: { color: DIM, formatter: '{value}%' },
        splitLine: { lineStyle: { color: 'rgba(255,255,255,0.04)' } } },
      series: [
        // y=x 完美校准线
        { type: 'line', data: [[0,0],[100,100]], showSymbol: false,
          lineStyle: { color: MUTE, width: 1, type: 'dashed' }, 
          name: '完美校准', tooltip: { show: false } },
        // 实际散点
        { type: 'scatter', data: points,
          symbolSize: v => Math.min(40, 8 + v.count * 2),
          itemStyle: { 
            color: GOLD2, opacity: 0.85, 
            borderColor: GOLD, borderWidth: 1 
          },
          name: '实际校准' }
      ]
    });
  }

  // ============================================================
  // 校准区间对比表
  // ============================================================
  function renderCalibrationTable() {
    const buckets = [
      { lo: 0, hi: 50 }, { lo: 50, hi: 65 }, { lo: 65, hi: 75 },
      { lo: 75, hi: 85 }, { lo: 85, hi: 100.1 }
    ];
    const rows = [];
    
    buckets.forEach(b => {
      let total = 0, hits = 0, drawHits = 0, drawTotal = 0;
      for (const m of matches) {
        const probs = { H: m.home_win_prob, D: m.draw_prob, A: m.away_win_prob };
        for (const [key, p] of Object.entries(probs)) {
          if (p >= b.lo && p < b.hi) {
            total++;
            const aDir = m.home_score > m.away_score ? 'H' : m.home_score < m.away_score ? 'A' : 'D';
            if (key === aDir) hits++;
            if (key === 'D') {
              drawTotal++;
              if (m.home_score === m.away_score) drawHits++;
            }
          }
        }
      }
      if (total > 0) {
        const mid = (b.lo + b.hi) / 2;
        const actual = hits / total * 100;
        const dev = actual - mid;
        let cls = 'ok';
        if (Math.abs(dev) < 5) cls = 'good';
        else if (Math.abs(dev) > 15) cls = 'bad';
        rows.push(`
          <tr class="${cls}">
            <td>${b.lo}-${b.hi}%</td>
            <td class="num">${total}</td>
            <td class="num">${mid.toFixed(0)}%</td>
            <td class="num">${actual.toFixed(1)}%</td>
            <td class="num"><span class="badge">${dev > 0 ? '+' : ''}${dev.toFixed(1)}pp</span></td>
          </tr>
        `);
      }
    });
    
    const html = `
      <table class="calib-table">
        <thead><tr><th>预测区间</th><th class="num">样本</th><th class="num">预测均值</th><th class="num">实际频率</th><th class="num">偏差</th></tr></thead>
        <tbody>${rows.join('')}</tbody>
      </table>
      <div style="margin-top:10px;font-size:10px;color:var(--text-mute)">
        偏差 = 实际频率 - 预测均值 · <span style="color:var(--green)">绿</span> &lt; 5pp · <span style="color:var(--text-dim)">灰</span> 5-15pp · <span style="color:var(--red)">红</span> &gt; 15pp
      </div>
    `;
    const el = document.getElementById('calibTable');
    if (el) el.innerHTML = html;
  }

  // ============================================================
  // 冷门榜
  // ============================================================
  function renderUpsets() {
    // 找到模型"最大概率预测"失误的场次
    const upsets = [];
    for (const m of matches) {
      const probs = { 
        [m.home_team]: m.home_win_prob, 
        'draw': m.draw_prob, 
        [m.away_team]: m.away_win_prob 
      };
      const actual = getActualWinner(m);
      const maxTeam = Object.entries(probs).reduce((a, c) => c[1] > a[1] ? c : a);
      if (maxTeam[0] !== actual) {
        upsets.push({
          m, 
          predicted: maxTeam[0], 
          predPct: maxTeam[1], 
          actual
        });
      }
    }
    upsets.sort((a, b) => b.predPct - a.predPct);
    
    const html = upsets.slice(0, 15).map(u => {
      const m = u.m;
      const homeCn = window.TEAM_CN?.[m.home_team] || m.home_team;
      const awayCn = window.TEAM_CN?.[m.away_team] || m.away_team;
      const predCn = u.predicted === 'draw' ? '平' : (window.TEAM_CN?.[u.predicted] || u.predicted);
      const actCn = u.actual === 'draw' ? '平' : (window.TEAM_CN?.[u.actual] || u.actual);
      return `
        <div class="upset-item">
          <div class="id">${m.match_id}</div>
          <div class="match">${homeCn} <span class="score">${m.home_score}-${m.away_score}</span> ${awayCn}</div>
          <div class="picked">看好<br><strong>${predCn}</strong></div>
          <div class="actual">${u.predPct.toFixed(0)}%<br><strong>${actCn}</strong></div>
        </div>
      `;
    }).join('');
    
    const el = document.getElementById('upsetList');
    if (el) el.innerHTML = html || '<div style="padding:20px;text-align:center;color:var(--text-mute);font-size:12px">无冷门场次</div>';
    
    // 显示统计
    const statEl = document.getElementById('upsetStat');
    if (statEl) {
      statEl.innerHTML = `共 <strong style="color:var(--gold-2)">${upsets.length}</strong> 场 · 占已结束 <strong>${matches.length}</strong> 场的 <strong>${(upsets.length/matches.length*100).toFixed(1)}%</strong>`;
    }
  }

  function renderEmpty() {
    const el = document.getElementById('accKpiGrid');
    if (el) el.innerHTML = '<div style="grid-column:1/-1;padding:40px;text-align:center;color:var(--text-mute)">尚无已结束比赛</div>';
  }

  // 公开：返回当前准确率快照（供 app.js 在直播卡 AI 预测块复用）
  //  - 返回 null 表示数据未就绪或尚无已结束比赛
  //  - 返回 { n, hitRate, exactRate, brier, last10Hits } 供调用方展示
  function getStats() {
    if (!matches || !matches.length) return null;
    const n = matches.length;
    let w = 0, e = 0, brierSum = 0;
    for (const m of matches) {
      const actual = getActualWinner(m);
      if (m.predicted_winner === actual) w++;
      if (m.predicted_home_score === m.home_score && m.predicted_away_score === m.away_score) e++;
      const a = [0, 0, 0];
      if (m.home_score > m.away_score) a[0] = 1;
      else if (m.home_score === m.away_score) a[1] = 1;
      else a[2] = 1;
      const p = [m.home_win_prob/100, m.draw_prob/100, m.away_win_prob/100];
      brierSum += (p[0]-a[0])**2 + (p[1]-a[1])**2 + (p[2]-a[2])**2;
    }
    // 近 10 场命中数
    const recent = matches.slice(-10);
    const last10Hits = recent.reduce((s, m) => s + (m.predicted_winner === getActualWinner(m) ? 1 : 0), 0);
    return {
      n,
      hitRate: w / n * 100,
      exactRate: e / n * 100,
      brier: brierSum / n,
      last10Hits,
      last10Total: recent.length
    };
  }

  return { init, refresh: () => { initialized = false; init(); }, getStats };
})();
