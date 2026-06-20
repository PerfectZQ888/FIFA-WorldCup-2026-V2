/* ============================================================
   2026 世界杯分析中心 - 主应用模块 (优化版 v1.1)
   - 修复 ECharts 内存泄漏
   - 单一 resize 监听器（防抖）
   - 集成 accuracy 仪表盘与 calibration 校准
   ============================================================ */

'use strict';

// ============================================================
// 图表管理（修复内存泄漏）
// ============================================================
const ChartManager = (() => {
  const instances = new Map();

  function set(id, option) {
    let chart = instances.get(id);
    if (!chart) {
      const el = document.getElementById(id);
      if (!el) return null;
      chart = echarts.init(el, null, { renderer: 'canvas' });
      instances.set(id, chart);
    }
    chart.setOption(option, true); // notMerge=true 避免配置累积
    return chart;
  }

  function get(id) { return instances.get(id); }

  function resizeAll() {
    for (const c of instances.values()) {
      try { c.resize(); } catch (e) { /* element gone */ }
    }
  }

  function disposeAll() {
    for (const c of instances.values()) c.dispose();
    instances.clear();
  }

  return { set, get, resizeAll, disposeAll };
})();

// 防抖 resize
let resizeTimer = null;
window.addEventListener('resize', () => {
  if (resizeTimer) clearTimeout(resizeTimer);
  resizeTimer = setTimeout(() => ChartManager.resizeAll(), 150);
});

// ============================================================
// 常量与字典
// ============================================================
const FLAG = {
  Mexico: '🇲🇽', 'South Africa': '🇿🇦', 'South Korea': '🇰🇷', Czechia: '🇨🇿',
  Canada: '🇨🇦', 'Bosnia & Herzegovina': '🇧🇦', USA: '🇺🇸', Paraguay: '🇵🇾',
  Qatar: '🇶🇦', Switzerland: '🇨🇭', Brazil: '🇧🇷', Morocco: '🇲🇦',
  Haiti: '🇭🇹', Scotland: '🏴󠁧󠁢󠁳󠁣󠁴󠁿', Australia: '🇦🇺', 'Türkiye': '🇹🇷',
  Germany: '🇩🇪', 'Curaçao': '🇨🇼', Netherlands: '🇳🇱', Japan: '🇯🇵',
  "Côte d'Ivoire": '🇨🇮', Ecuador: '🇪🇨', Sweden: '🇸🇪', Tunisia: '🇹🇳',
  Spain: '🇪🇸', 'Cabo Verde': '🇨🇻', Belgium: '🇧🇪', Egypt: '🇪🇬',
  'Saudi Arabia': '🇸🇦', Uruguay: '🇺🇾', 'IR Iran': '🇮🇷', 'New Zealand': '🇳🇿',
  France: '🇫🇷', Senegal: '🇸🇳', Iraq: '🇮🇶', Norway: '🇳🇴',
  Argentina: '🇦🇷', Algeria: '🇩🇿', Austria: '🇦🇹', Jordan: '🇯🇴',
  Portugal: '🇵🇹', 'DR Congo': '🇨🇩', Uzbekistan: '🇺🇿', Colombia: '🇨🇴',
  England: '🏴󠁧󠁢󠁥󠁮󠁧󠁿', Croatia: '🇭🇷', Ghana: '🇬🇭', Panama: '🇵🇦',
};

// ============================================================
// 国际化 (v1.2) — 中英双语
// ============================================================
const LANG = {
  zh: {
    // 导航
    'nav.standings': '积分榜',
    'nav.schedule': '赛程',
    'nav.scorers': '射手榜',
    'nav.predictions': 'AI 预测',
    'nav.accuracy': '📊 准确率',
    'nav.bracket': '对阵图',
    'nav.history': '历届',
    // Section 标题
    'sec.kpi': '小组赛积分榜',
    'sec.ai_predict': 'AI 冠军预测榜',
    'sec.scorers': '射手榜',
    'sec.accuracy': '🎯 AI 预测准确率仪表盘',
    'sec.hit_highlights': '🎯 预测命中集锦',
    'sec.history': '22 届世界杯历史',
    'sec.live': '赛事直播中心',
    // 按钮
    'btn.refresh': '立即刷新',
    'btn.cctv': '观看 CCTV5 直播',
    'btn.baidu': '百度体育数据',
    'btn.copy_text': '复制文案',
    'btn.export_img': '导出图片',
    'btn.all': '全部',
    'btn.exact': '🎯 精确命中',
    'btn.winner': '✅ 胜方命中',
    // 状态
    'status.live': '● 直播',
    'status.finished': '已结束',
    'status.upcoming': '即将开球',
    // 命中判定
    'verdict.exact': '精确命中',
    'verdict.winner': '胜方命中',
    'verdict.miss': '未命中',
    'verdict.exact_msg': 'AI 预测 {pred}，实际 {actual}',
    'verdict.winner_msg': 'AI 看好 {winner}，{winner} 确实赢了（比分 {score}）',
    'verdict.miss_msg': 'AI 看好 {pred}，实际 {actual} 胜',
    // 时间线
    'timeline.title': '⚽ 进球时间线',
    'timeline.count': '⚽ 进球时间线 · 共 {n} 球',
    'timeline.empty': '本场暂无进球数据',
    'timeline.empty_draw': '本场暂无进球数据（双方均未进球）',
    // 概率分布
    'dist.title': '📊 AI 概率分布 Top 10 · 实际比分高亮',
    'dist.empty': '本场无概率分布数据',
    'dist.actual': '实际比分',
    'dist.predicted': 'AI 预测比分',
    'dist.legend_note': '★ {score} 实际概率 {pct}%（{verdict}）',
    // Modal
    'modal.title_loading': '加载 {id}...',
    // 准确率徽章
    'acc.title': 'AI 历史准确率 {n} 百分之',
    'acc.tooltip': '基于近 {n} 场已完赛 · 胜平负命中 {h}% · 精确比分 {e}% · 近 {t} 场 {w} 中',
    // 翻车榜
    'upset.empty': '无冷门场次',
  },
  en: {
    'nav.standings': 'Standings',
    'nav.schedule': 'Schedule',
    'nav.scorers': 'Scorers',
    'nav.predictions': 'AI Predict',
    'nav.accuracy': '📊 Accuracy',
    'nav.bracket': 'Bracket',
    'nav.history': 'History',
    'sec.kpi': 'Group Standings',
    'sec.ai_predict': 'AI Championship Prediction',
    'sec.scorers': 'Top Scorers',
    'sec.accuracy': '🎯 AI Accuracy Dashboard',
    'sec.hit_highlights': '🎯 Prediction Hit Highlights',
    'sec.history': '22 World Cups History',
    'sec.live': 'Live Center',
    'btn.refresh': 'Refresh',
    'btn.cctv': 'Watch CCTV5',
    'btn.baidu': 'Baidu Sports',
    'btn.copy_text': 'Copy Text',
    'btn.export_img': 'Export Image',
    'btn.all': 'All',
    'btn.exact': '🎯 Exact',
    'btn.winner': '✅ Winner',
    'status.live': '● Live',
    'status.finished': 'Finished',
    'status.upcoming': 'Upcoming',
    'verdict.exact': 'Exact Hit',
    'verdict.winner': 'Winner Hit',
    'verdict.miss': 'Miss',
    'verdict.exact_msg': 'AI predicted {pred}, actual {actual}',
    'verdict.winner_msg': 'AI picked {winner}, {winner} won ({score})',
    'verdict.miss_msg': 'AI picked {pred}, actual winner {actual}',
    'timeline.title': '⚽ Goals Timeline',
    'timeline.count': '⚽ Goals · {n} total',
    'timeline.empty': 'No goal data available',
    'timeline.empty_draw': 'No goals scored',
    'dist.title': '📊 AI Probability Distribution Top 10 · Actual highlighted',
    'dist.empty': 'No probability data',
    'dist.actual': 'Actual',
    'dist.predicted': 'AI Predicted',
    'dist.legend_note': '★ {score} actual prob {pct}% ({verdict})',
    'modal.title_loading': 'Loading {id}...',
    'acc.title': 'AI historical accuracy {n} percent',
    'acc.tooltip': 'Based on {n} finished matches · winner hit {h}% · exact score {e}% · last {t} matches {w} hits',
    'upset.empty': 'No upset games',
  }
};

let CURRENT_LANG = localStorage.getItem('wc2026-lang') || 'zh';
let CURRENT_THEME = localStorage.getItem('wc2026-theme') || 'dark';

function t(key, vars) {
  const dict = LANG[CURRENT_LANG] || LANG.zh;
  let s = dict[key] || LANG.zh[key] || key;
  if (vars) {
    Object.keys(vars).forEach(k => { s = s.replace(new RegExp('\\{'+k+'\\}','g'), vars[k]); });
  }
  return s;
}

function applyLang() {
  document.documentElement.lang = CURRENT_LANG === 'en' ? 'en' : 'zh-CN';
  document.querySelectorAll('[data-i18n]').forEach(el => {
    const key = el.dataset.i18n;
    el.textContent = t(key);
  });
  document.querySelectorAll('[data-i18n-title]').forEach(el => {
    el.title = t(el.dataset.i18nTitle);
  });
  document.querySelectorAll('[data-i18n-aria]').forEach(el => {
    el.setAttribute('aria-label', t(el.dataset.i18nAria));
  });
}

function applyTheme() {
  document.documentElement.dataset.theme = CURRENT_THEME;
}

// ============================================================
// Toast 通知系统 (v1.2) — 替代 alert()
// ============================================================
function toast(msg, type = 'info', duration = 3000) {
  const container = document.getElementById('toastContainer');
  if (!container) return;
  const icons = { success: '✓', error: '✕', warning: '⚠', info: 'ℹ' };
  const t = document.createElement('div');
  t.className = `toast toast-${type}`;
  t.setAttribute('role', type === 'error' ? 'alert' : 'status');
  t.innerHTML = `
    <span class="toast-icon">${icons[type] || icons.info}</span>
    <span class="toast-msg">${msg}</span>
    <button class="toast-close" aria-label="关闭">×</button>
  `;
  t.querySelector('.toast-close').addEventListener('click', () => removeToast(t));
  container.appendChild(t);
  if (duration > 0) {
    setTimeout(() => removeToast(t), duration);
  }
  return t;
}
function removeToast(t) {
  if (!t || !t.parentNode) return;
  t.classList.add('toast-fade-out');
  setTimeout(() => t.remove(), 250);
}

// ============================================================
// 键盘快捷键 (v1.2)
// ============================================================
let KBD_SELECTED_INDEX = -1;
const KBD_HINT_KEY = 'wc2026-kbd-hint-seen';

function setupKeyboardShortcuts() {
  document.addEventListener('keydown', (e) => {
    // 输入框内不响应
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.isContentEditable) return;
    // 弹窗打开时让 modal 自己处理 Escape
    const modalOpen = !document.getElementById('matchModal')?.hidden;
    
    const key = e.key.toLowerCase();
    
    // ? — 切换快捷键提示
    if (key === '?' && e.shiftKey) {
      e.preventDefault();
      toggleKbdHint();
      return;
    }
    
    // 弹窗打开时只响应 Esc
    if (modalOpen) return;
    
    // j/k — 上一/下一张命中卡
    if (key === 'j' || key === 'k' || key === 'arrowdown' || key === 'arrowup') {
      const cards = Array.from(document.querySelectorAll('.hit-card'));
      if (!cards.length) return;
      e.preventDefault();
      if (key === 'j' || key === 'arrowdown') KBD_SELECTED_INDEX = Math.min(KBD_SELECTED_INDEX + 1, cards.length - 1);
      else KBD_SELECTED_INDEX = Math.max(KBD_SELECTED_INDEX - 1, 0);
      cards.forEach((c, i) => c.classList.toggle('kbd-selected', i === KBD_SELECTED_INDEX));
      cards[KBD_SELECTED_INDEX]?.scrollIntoView({ behavior: 'smooth', block: 'center' });
      return;
    }
    
    // Enter — 打开选中卡
    if (key === 'enter' && KBD_SELECTED_INDEX >= 0) {
      const cards = Array.from(document.querySelectorAll('.hit-card'));
      const sel = cards[KBD_SELECTED_INDEX];
      if (sel && sel.dataset.matchId) {
        e.preventDefault();
        showMatchDetail(sel.dataset.matchId);
      }
      return;
    }
    
    // ←/→ — 滚到上/下个 section
    if (key === 'arrowleft' || key === 'arrowright') {
      e.preventDefault();
      const sections = Array.from(document.querySelectorAll('section[id]'));
      const y = window.scrollY + 100;
      let target;
      if (key === 'arrowright') {
        target = sections.find(s => s.offsetTop > y);
      } else {
        for (let i = sections.length - 1; i >= 0; i--) {
          if (sections[i].offsetTop < y - 50) { target = sections[i]; break; }
        }
      }
      if (target) target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      return;
    }
    
    // T — 主题切换
    if (key === 't' && !e.ctrlKey && !e.metaKey) {
      e.preventDefault();
      toggleTheme();
      toast(`已切换到${CURRENT_THEME === 'dark' ? '暗黑' : '明亮'}主题`, 'info', 1500);
      return;
    }
    
    // L — 语言切换
    if (key === 'l' && !e.ctrlKey && !e.metaKey) {
      e.preventDefault();
      const old = CURRENT_LANG;
      toggleLang();
      toast(`已切换到${CURRENT_LANG === 'zh' ? '中文' : 'English'}`, 'info', 1500);
      return;
    }
  });
  
  // 关闭提示按钮
  document.getElementById('kbdHintClose')?.addEventListener('click', () => {
    document.getElementById('kbdHint').hidden = true;
    localStorage.setItem(KBD_HINT_KEY, '1');
  });
  
  // 首次访问显示提示
  if (!localStorage.getItem(KBD_HINT_KEY)) {
    setTimeout(() => {
      const hint = document.getElementById('kbdHint');
      if (hint) hint.hidden = false;
    }, 2000);
  }
}

function toggleKbdHint() {
  const hint = document.getElementById('kbdHint');
  if (hint) hint.hidden = !hint.hidden;
}

// ============================================================
// URL 状态同步 (v1.2) — 过滤条件写进 hash
// ============================================================
function syncUrlState() {
  const params = new URLSearchParams();
  if (HIT_FILTER_STATE.filter !== 'all') params.set('filter', HIT_FILTER_STATE.filter);
  if (KBD_SELECTED_INDEX >= 0) params.set('card', String(KBD_SELECTED_INDEX));
  const hash = params.toString();
  history.replaceState(null, '', hash ? `?${hash}` : window.location.pathname);
}

function loadUrlState() {
  const params = new URLSearchParams(window.location.search);
  const filter = params.get('filter');
  if (filter && ['all', 'exact', 'winner'].includes(filter)) {
    HIT_FILTER_STATE.filter = filter;
    // 同步 UI
    document.querySelectorAll('.hit-filter').forEach(b => {
      b.classList.toggle('active', b.dataset.filter === filter);
      b.setAttribute('aria-selected', b.dataset.filter === filter ? 'true' : 'false');
    });
  }
  const card = parseInt(params.get('card') || '-1', 10);
  if (card >= 0) KBD_SELECTED_INDEX = card;
}

function toggleLang() {
  CURRENT_LANG = CURRENT_LANG === 'zh' ? 'en' : 'zh';
  localStorage.setItem('wc2026-lang', CURRENT_LANG);
  applyLang();
}

function toggleTheme() {
  CURRENT_THEME = CURRENT_THEME === 'dark' ? 'light' : 'dark';
  localStorage.setItem('wc2026-theme', CURRENT_THEME);
  applyTheme();
}

// 启动时应用
applyTheme();
applyLang();

const TEAM_CN = {
  Mexico: '墨西哥', 'South Africa': '南非', 'South Korea': '韩国', Czechia: '捷克',
  Canada: '加拿大', 'Bosnia & Herzegovina': '波黑', USA: '美国', Paraguay: '巴拉圭',
  Qatar: '卡塔尔', Switzerland: '瑞士', Brazil: '巴西', Morocco: '摩洛哥',
  Haiti: '海地', Scotland: '苏格兰', Australia: '澳大利亚', 'Türkiye': '土耳其',
  Germany: '德国', 'Curaçao': '库拉索', Netherlands: '荷兰', Japan: '日本',
  "Côte d'Ivoire": '科特迪瓦', Ecuador: '厄瓜多尔', Sweden: '瑞典', Tunisia: '突尼斯',
  Spain: '西班牙', 'Cabo Verde': '佛得角', Belgium: '比利时', Egypt: '埃及',
  'Saudi Arabia': '沙特', Uruguay: '乌拉圭', 'IR Iran': '伊朗', 'New Zealand': '新西兰',
  France: '法国', Senegal: '塞内加尔', Iraq: '伊拉克', Norway: '挪威',
  Argentina: '阿根廷', Algeria: '阿尔及利亚', Austria: '奥地利', Jordan: '约旦',
  Portugal: '葡萄牙', 'DR Congo': '刚果民主共和国', Uzbekistan: '乌兹别克', Colombia: '哥伦比亚',
  England: '英格兰', Croatia: '克罗地亚', Ghana: '加纳', Panama: '巴拿马',
};

// 暴露到 window 供 accuracy.js 跨文件使用（v1.2 修复 TEAM_CN_MAP 时序问题）
window.TEAM_CN = TEAM_CN;
window.FLAG = FLAG;

const GOLD = '#d4af37', GOLD2 = '#f9d76b';
const GREEN = '#00d68f', RED = '#ff5577', BLUE = '#4ea8ff';
const TEXT = '#e9eef7', DIM = '#93a3bd', MUTE = '#5d6d85';
const CHART_BG = 'transparent';

const WEEKDAY_CN = ['周日','周一','周二','周三','周四','周五','周六'];

let ALL_MATCHES = [];
let SELECTED_DATE = null;
let LIVE_REFRESH_TIMER = null;
let SCORERS_TIMER = null;
let PREDICTIONS_DATA = null; // 缓存冠军榜
let ACCURACY_TIMER = null;     // v1.2: 准确率仪表盘自动刷新
let LAST_FINISHED_COUNT = -1;  // v1.2: 用于判断是否有新比赛完赛

// ============================================================
// 时区工具
// ============================================================
function utcToCst(utcIso) { return new Date(utcIso); }
function matchUtcIso(m) { return `${m.match_date}T${m.match_time}:00Z`; }
function cstDateStr(m) {
  return utcToCst(matchUtcIso(m)).toLocaleDateString('en-CA', { timeZone: 'Asia/Shanghai' });
}
function cstTimeStr(m) {
  return utcToCst(matchUtcIso(m)).toLocaleTimeString('zh-CN', { timeZone: 'Asia/Shanghai', hour: '2-digit', minute: '2-digit', hour12: false });
}
function cstHour(m) {
  return parseInt(utcToCst(matchUtcIso(m)).toLocaleTimeString('en-US', { timeZone: 'Asia/Shanghai', hour: '2-digit', hour12: false }));
}
function todayCst() { return new Date().toLocaleDateString('en-CA', { timeZone: 'Asia/Shanghai' }); }
function tomorrowCst() {
  const d = new Date(); d.setDate(d.getDate() + 1);
  return d.toLocaleDateString('en-CA', { timeZone: 'Asia/Shanghai' });
}
function addDaysCst(isoDate, n) {
  const [y, m, d] = isoDate.split('-').map(Number);
  const dt = new Date(Date.UTC(y, m - 1, d));
  dt.setUTCDate(dt.getUTCDate() + n);
  return dt.toISOString().slice(0, 10);
}
function addDays(isoDate, n) {
  const d = new Date(isoDate + 'T00:00:00');
  d.setDate(d.getDate() + n);
  return d.toISOString().slice(0, 10);
}

// ============================================================
// 轮次标签
// ============================================================
function roundCN(round, group) {
  if (!round) return '';
  if (round.startsWith('Group')) {
    const md = round.match(/Matchday (\d+)/);
    return md ? `${group}组 第${md[1]}轮` : round;
  }
  if (round.includes('Round of 32')) return '32强';
  if (round.includes('Round of 16')) return '16强';
  if (round.includes('Quarter')) return '1/4决赛';
  if (round.includes('Semi')) return '半决赛';
  if (round.includes('3rd Place')) return '季军赛';
  if (round.includes('Final')) return '决赛';
  return round;
}
function roundTagClass(round) {
  if (!round) return '';
  if (round.startsWith('Group')) return 'tag-group';
  if (round.includes('Final')) return 'tag-final';
  if (round.includes('Semi')) return 'tag-semi';
  if (round.includes('Quarter')) return 'tag-qf';
  return 'tag-ko';
}

// ============================================================
// 实际胜者推断
// ============================================================
function getActualWinner(m) {
  if (m.home_score == null || m.away_score == null) return null;
  if (m.home_score > m.away_score) return m.home_team;
  if (m.home_score < m.away_score) return m.away_team;
  return 'draw';
}
function getActualOutcome(m) { // 'H' | 'D' | 'A'
  if (m.home_score > m.away_score) return 'H';
  if (m.home_score < m.away_score) return 'A';
  return 'D';
}

// ============================================================
// 启动
// ============================================================
async function load() {
  try {
    const [summary, groups, standings, predictions, history] = await Promise.all([
      fetch('/api/summary').then(r => r.json()),
      fetch('/api/groups').then(r => r.json()),
      fetch('/api/standings').then(r => r.json()),
      fetch('/api/predictions').then(r => r.json()),
      fetch('/api/history').then(r => r.json()),
    ]);

    renderHero(summary);
    renderKPIs(summary);
    renderStandings(standings, groups);
    await renderLive();
    await renderSchedule();
    await renderFullScorers();
    renderPredictions(predictions);
    PREDICTIONS_DATA = predictions;
    renderScorers(summary.top_scorers || []);
    renderHistory(history);
    updateTs(summary.last_data_update);

    // 准确率仪表盘
    if (window.AccuracyDashboard) {
      await window.AccuracyDashboard.init();
    }

    if (LIVE_REFRESH_TIMER) clearInterval(LIVE_REFRESH_TIMER);
    LIVE_REFRESH_TIMER = setInterval(renderLive, 30000);
    if (SCORERS_TIMER) clearInterval(SCORERS_TIMER);
    SCORERS_TIMER = setInterval(renderFullScorers, 300000);
    // v1.2: 准确率仪表盘自动刷新（每 30s 检查一次是否有新完赛）
    if (ACCURACY_TIMER) clearInterval(ACCURACY_TIMER);
    ACCURACY_TIMER = setInterval(maybeRefreshAccuracy, 30000);
    maybeRefreshAccuracy();

    // 命中集锦：首次渲染 + 每 60s 刷新（新完赛会冒出）
    loadUrlState();  // 优先从 URL 读取过滤条件
    renderHitHighlights();
    if (HIT_HIGHLIGHTS_TIMER) clearInterval(HIT_HIGHLIGHTS_TIMER);
    HIT_HIGHLIGHTS_TIMER = setInterval(() => { renderHitHighlights(); syncUrlState(); }, 60000);
    
    // 启动快捷键
    setupKeyboardShortcuts();
  } catch (e) {
    console.error('加载失败', e);
    showGlobalError('数据加载失败', e?.message || String(e));
  }
}

// ============================================================
// 错误状态辅助 (v1.2)
// ============================================================
function renderError(title, detail, onRetry) {
  const retryHtml = typeof onRetry === 'function'
    ? `<button type="button" class="retry-btn" data-retry="1">↻ 重试</button>`
    : '';
  return `
    <div class="err-state">
      <div class="err-icon">⚠️</div>
      <div class="err-title">${title}</div>
      <div class="err-detail">${detail}</div>
      ${retryHtml}
    </div>
  `;
}

// 错误事件委托: 点击重试按钮时调用对应回调
document.addEventListener('click', (e) => {
  const btn = e.target.closest('.retry-btn[data-retry="1"]');
  if (!btn) return;
  const state = btn.closest('.err-state');
  if (!state) return;
  const parent = state.parentElement;
  if (!parent) return;
  parent.innerHTML = '<div class="skeleton" style="height:120px"></div>';
  // 触发对应的重新加载（按 parent.id 分发）
  const id = parent.id;
  if (id === 'liveGrid' && typeof renderLive === 'function') renderLive();
  else if (id === 'scorersTableWrap' && typeof renderFullScorers === 'function') renderFullScorers();
  else if (id === 'scheduleList' && typeof renderScheduleList === 'function') renderScheduleList();
  else if (id === 'standingsGrid' && typeof load === 'function') load();
});

let GLOBAL_ERROR_SHOWN = false;
function showGlobalError(title, detail) {
  if (GLOBAL_ERROR_SHOWN) return;
  GLOBAL_ERROR_SHOWN = true;
  let bar = document.getElementById('globalErrorBar');
  if (!bar) {
    bar = document.createElement('div');
    bar.id = 'globalErrorBar';
    bar.className = 'global-error';
    document.body.appendChild(bar);
  }
  bar.innerHTML = `
    <span class="err-icon">⚠️</span>
    <span><strong>${title}</strong> · ${detail}</span>
    <button type="button" class="retry-btn" id="globalErrorRetry">↻ 重新加载</button>
    <button type="button" class="dismiss-btn" id="globalErrorDismiss">×</button>
  `;
  bar.classList.add('visible');
  document.getElementById('globalErrorRetry')?.addEventListener('click', () => location.reload());
  document.getElementById('globalErrorDismiss')?.addEventListener('click', () => {
    bar.classList.remove('visible');
    GLOBAL_ERROR_SHOWN = false;
  });
  // 8 秒后自动消失
  setTimeout(() => {
    if (bar.classList.contains('visible')) {
      bar.classList.remove('visible');
      GLOBAL_ERROR_SHOWN = false;
    }
  }, 8000);
}

// ============================================================
// 准确率自动刷新 (v1.2)
// 检测是否有新完赛 → 触发仪表盘重算
// ============================================================
async function maybeRefreshAccuracy() {
  if (!window.AccuracyDashboard) return;
  try {
    const res = await fetch('/api/matches?status=finished&limit=500');
    const finished = await res.json();
    const count = (finished || []).length;
    if (LAST_FINISHED_COUNT === -1) {
      // 首次: 同步一次即可（init 已触发）
      LAST_FINISHED_COUNT = count;
      return;
    }
    if (count !== LAST_FINISHED_COUNT) {
      LAST_FINISHED_COUNT = count;
      console.log(`[v1.2] 检测到完赛数变化 (${count}) → 刷新准确率仪表盘`);
      await window.AccuracyDashboard.refresh();
    }
  } catch (e) { /* ignore */ }
}

// ============================================================
// Hero
// ============================================================
function renderHero(s) {
  document.getElementById('heroDays').textContent = s.days_to_final;
  document.getElementById('heroMatches').textContent = s.finished_matches;
  document.getElementById('heroGoals').textContent = s.total_goals;
  document.getElementById('heroTeams').textContent = s.teams_count;
  document.getElementById('heroTitle').innerHTML = `距离决赛<br>还有 ${s.days_to_final} 天`;
}

// ============================================================
// KPI
// ============================================================
function renderKPIs(s) {
  document.getElementById('kpiFinished').textContent = s.finished_matches;
  document.getElementById('kpiFinishedSub').textContent = `共 ${s.total_matches} 场`;
  document.getElementById('kpiRemaining').textContent = s.scheduled_matches;
  document.getElementById('kpiUpcoming').textContent = s.upcoming_24h;
  document.getElementById('kpiGpg').textContent = s.finished_matches > 0
    ? (s.total_goals / s.finished_matches).toFixed(2) : '0';
  fetch('/api/standings').then(r => r.json()).then(st => {
    const active = Object.values(st).filter(g => g.some(t => t.played > 0)).length;
    document.getElementById('kpiGroups').textContent = active;
  });
}

// ============================================================
// 积分榜
// ============================================================
function renderStandings(standings, groups) {
  const grid = document.getElementById('standingsGrid');
  grid.innerHTML = '';
  const groupsSorted = Object.keys(groups).sort();
  for (const g of groupsSorted) {
    const teams = groups[g];
    const table = standings[g] || teams.map(t => ({ team: t.name, played: 0, won: 0, draw: 0, lost: 0, gf: 0, ga: 0, gd: 0, pts: 0, form: [], form_str: '' }));
    const hasMatches = table.some(t => t.played > 0);
    const card = document.createElement('div');
    card.className = 'group-card';
    card.innerHTML = `
      <div class="group-head">
        <span class="name">${g} 组</span>
        <span class="${hasMatches ? 'live' : 'pending'}">${hasMatches ? `已踢 ${table.reduce((s,t)=>s+t.played,0)/2} 场` : '未开赛'}</span>
      </div>
      <table class="group-table">
        <thead><tr><th>#</th><th>球队</th><th class="num">赛</th><th class="num">胜</th><th class="num">平</th><th class="num">负</th><th class="num">净</th><th class="num">分</th><th>近况</th></tr></thead>
        <tbody>
          ${table.map((t, i) => `
            <tr class="${i < 2 ? 'qualified qual-pos' : ''}">
              <td class="pos">${i+1}</td>
              <td class="team">${FLAG[t.team]||'🏳️'} ${TEAM_CN[t.team]||t.team}</td>
              <td class="num">${t.played}</td>
              <td class="num">${t.won}</td>
              <td class="num">${t.draw}</td>
              <td class="num">${t.lost}</td>
              <td class="num">${t.gd > 0 ? '+'+t.gd : t.gd}</td>
              <td class="pts">${t.pts}</td>
              <td class="form">${(t.form_str||'').split('').map(c => `<span class="form-${c}">${c}</span>`).join(' ')}</td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    `;
    grid.appendChild(card);
  }
}

// ============================================================
// 直播中心
// ============================================================
async function renderLive() {
  const el = document.getElementById('liveGrid');
  const meta = document.getElementById('liveMeta');
  el.style.opacity = '0.5';
  try {
    try { await fetch('/api/live/fetch', { method: 'POST' }); } catch (e) { /* ignore */ }
    const res = await fetch('/api/matches/live');
    const data = await res.json();
    let matches = data.matches || [];
    const recent = await fetch('/api/matches?status=finished&limit=10').then(r => r.json());
    const now = new Date();
    const recentFiltered = recent.filter(m => {
      const matchTs = new Date(matchUtcIso(m)).getTime();
      return (now - matchTs) < 12 * 3600 * 1000;
    });
    matches = [...matches, ...recentFiltered];

    if (data.last_update) {
      const dt = new Date(data.last_update);
      meta.textContent = `更新于 ${dt.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })}`;
    }

    if (!matches.length) {
      el.innerHTML = '<div class="live-empty">暂无直播或近期比赛</div>';
      el.style.opacity = '1';
      return;
    }

    matches.sort((a, b) => {
      const aLive = a.status === 'live' ? 0 : (a.status === 'finished' ? 1 : 2);
      const bLive = b.status === 'live' ? 0 : (b.status === 'finished' ? 1 : 2);
      if (aLive !== bLive) return aLive - bLive;
      return matchUtcIso(a).localeCompare(matchUtcIso(b));
    });

    el.innerHTML = matches.map(m => liveCard(m)).join('');
    el.style.opacity = '1';
    // v1.2: 顺手检测是否有新完赛（避免等 30s 定时器）
    maybeRefreshAccuracy();
  } catch (e) {
    console.error('Live render failed', e);
    el.innerHTML = renderError('直播数据加载失败', '请检查网络后重试', () => renderLive());
    el.style.opacity = '1';
  }
}

function liveCard(m) {
  const isFinished = m.status === 'finished';
  const isLive = m.status === 'live';
  const isUpcoming = m.status === 'scheduled' || (!isFinished && !isLive);
  const home = TEAM_CN[m.home_team] || m.home_team;
  const away = TEAM_CN[m.away_team] || m.away_team;

  const timeCst = cstTimeStr(m);
  const dateCst = cstDateStr(m);

  let scoreHtml, stateCls;
  if (isFinished) {
    scoreHtml = `<span>${m.home_score}</span><span class="sep">:</span><span>${m.away_score}</span><span class="extra">已结束</span>`;
    stateCls = 'finished';
  } else if (isLive) {
    scoreHtml = `<span>${m.home_score ?? 0}</span><span class="sep">:</span><span>${m.away_score ?? 0}</span><span class="extra">进行中</span>`;
    stateCls = 'live';
  } else {
    scoreHtml = `<span>—</span><span class="sep">vs</span><span>—</span><span class="extra">${timeCst}</span>`;
    stateCls = 'scheduled';
  }

  // AI 预测块 - 仅 upcoming 状态
  let aiBlock = '';
  if (isUpcoming && m.predicted_winner && m.predicted_winner !== 'TBD'
      && m.predicted_home_score != null && m.predicted_away_score != null) {
    // 应用前端校准（如果启用）
    let hPct = m.home_win_prob, dPct = m.draw_prob, aPct = m.away_win_prob;
    let pHS = m.predicted_home_score, pAS = m.predicted_away_score;
    if (window.Calibration && window.Calibration.isEnabled()) {
      const cal = window.Calibration.calibrate(m.home_win_prob, m.draw_prob, m.away_win_prob);
      hPct = cal.home; dPct = cal.draw; aPct = cal.away;
      const cs = window.Calibration.calibrateScore(m.predicted_home_score, m.predicted_away_score);
      pHS = cs.home; pAS = cs.away;
    }

    const winnerCn = m.predicted_winner === 'draw' ? '平局' : (TEAM_CN[m.predicted_winner] || m.predicted_winner);
    const winnerPct = m.predicted_winner === 'draw' ? dPct : (m.predicted_winner === m.home_team ? hPct : aPct);
    const isCal = window.Calibration && window.Calibration.isEnabled();
    aiBlock = `
      <div class="live-pred">
        <div class="live-pred-head">
          <span class="ai-tag" title="综合 4 因子${isCal ? '（已前端校准）' : ''}" aria-label="AI 预测区块">🤖 AI 预测${isCal ? ' · 校准' : ''}</span>
          ${(() => {
            const acc = window.AccuracyDashboard && window.AccuracyDashboard.getStats && window.AccuracyDashboard.getStats();
            if (!acc) return '';
            const cls = acc.hitRate >= 60 ? 'acc-high' : acc.hitRate >= 45 ? 'acc-mid' : 'acc-low';
            return `<span class="ai-acc ${cls}" role="button" tabindex="0"
              title="基于近 ${acc.n} 场已完赛 · 胜平负命中 ${acc.hitRate.toFixed(1)}% · 精确比分 ${acc.exactRate.toFixed(1)}% · 近 ${acc.last10Total} 场 ${acc.last10Hits} 中\n点击查看 AI 翻车记录"
              aria-label="AI 历史准确率 ${acc.hitRate.toFixed(0)} 百分之，点击跳到翻车榜"
              data-scroll-target="upsetList"
              data-stat-n="${acc.n}"
              data-stat-hits="${acc.last10Hits}"
              data-stat-total="${acc.last10Total}">· 准 ${acc.hitRate.toFixed(0)}%</span>`;
          })()}
          <span class="ai-pick">🏆 胜方: <strong class="winner-name" title="${winnerCn} 胜率 ${winnerPct.toFixed(1)}%" aria-label="AI 预测胜方 ${winnerCn}，胜率 ${winnerPct.toFixed(0)} 百分之" tabindex="0">${winnerCn}</strong></span>
        </div>
        <div class="live-pred-score">
          <span>${pHS}</span><span class="sep">:</span><span>${pAS}</span>
        </div>
        <div class="live-pred-probs" title="${home} 胜 ${hPct.toFixed(1)}% · 平 ${dPct.toFixed(1)}% · ${away} 胜 ${aPct.toFixed(1)}%">
          <div class="prob-bar"><div class="prob-h" style="width:${hPct}%"></div><div class="prob-d" style="width:${dPct}%"></div><div class="prob-a" style="width:${aPct}%"></div></div>
          <div class="prob-labels"><span class="ph">${hPct.toFixed(0)}%</span><span class="pd">${dPct.toFixed(0)}%</span><span class="pa">${aPct.toFixed(0)}%</span></div>
        </div>
        <div class="live-pred-legend"><span class="lh">${home.slice(0,2)}</span><span class="ld">平</span><span class="la">${away.slice(0,2)}</span></div>
      </div>
    `;
  }

  return `
    <div class="live-card ${stateCls}">
      <div class="live-card-head">
        <span class="live-card-time"><strong>${timeCst}</strong> ${dateCst}</span>
        <span class="live-card-status ${stateCls}">${stateCls === 'live' ? '● 直播' : stateCls === 'finished' ? '已结束' : '即将开球'}</span>
      </div>
      <div class="live-card-body">
        <div class="live-team home">
          <span class="flag">${FLAG[m.home_team] || '🏳️'}</span>
          <span class="name">${home}</span>
        </div>
        <div class="live-score ${stateCls}">${scoreHtml}</div>
        <div class="live-team away">
          <span class="name">${away}</span>
          <span class="flag">${FLAG[m.away_team] || '🏳️'}</span>
        </div>
      </div>
      ${aiBlock}
      <div class="live-card-foot">
        <span>${roundCN(m.round, m.group_name)}</span>
        <span>${m.venue || ''}</span>
      </div>
    </div>
  `;
}

// ============================================================
// 赛程
// ============================================================
async function renderSchedule() {
  const all = await fetch('/api/matches?limit=500').then(r => r.json());
  ALL_MATCHES = all;
  const byDate = {};
  for (const m of all) {
    const d = cstDateStr(m);
    (byDate[d] = byDate[d] || []).push(m);
  }
  const dates = Object.keys(byDate).sort();
  const today = todayCst();
  const bar = document.getElementById('dateBar');
  bar.innerHTML = '';
  SELECTED_DATE = dates.includes(today) ? today : dates[0];
  const displayedDates = dates.slice(0, 14);
  for (const d of displayedDates) {
    const matches = byDate[d];
    const [y, m, day] = d.split('-').map(Number);
    const dt = new Date(y, m - 1, day);
    const isToday = d === today;
    const isTomorrow = d === tomorrowCst();
    const relLabel = isToday ? '今天' : (isTomorrow ? '明天' : (d < today ? '已结束' : WEEKDAY_CN[dt.getDay()]));
    const pill = document.createElement('div');
    pill.className = 'date-pill' + (d === SELECTED_DATE ? ' active' : '');
    pill.dataset.date = d;
    pill.setAttribute('role', 'button');
    pill.setAttribute('tabindex', '0');
    pill.setAttribute('aria-label', `${relLabel} ${m}月${day}日，共 ${matches.length} 场比赛`);
    pill.innerHTML = `<div class="day">${m}/${day}</div><div class="rel">${relLabel}</div><div class="count">${matches.length} 场</div>`;
    const selectDate = () => {
      SELECTED_DATE = d;
      bar.querySelectorAll('.date-pill').forEach(p => p.classList.toggle('active', p.dataset.date === d));
      renderScheduleList();
      // 滚动到选中的日期
      pill.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' });
    };
    pill.addEventListener('click', selectDate);
    pill.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); selectDate(); }
    });
    bar.appendChild(pill);
  }

  // v1.2: 日期条支持键盘 ←/→ 切换
  bar.tabIndex = 0;
  bar.setAttribute('role', 'tablist');
  bar.setAttribute('aria-label', '赛程日期切换');
  bar.addEventListener('keydown', (e) => {
    if (e.key !== 'ArrowLeft' && e.key !== 'ArrowRight') return;
    const idx = displayedDates.indexOf(SELECTED_DATE);
    const next = e.key === 'ArrowLeft'
      ? Math.max(0, idx - 1)
      : Math.min(displayedDates.length - 1, idx + 1);
    if (next === idx) return;
    e.preventDefault();
    SELECTED_DATE = displayedDates[next];
    bar.querySelectorAll('.date-pill').forEach(p => p.classList.toggle('active', p.dataset.date === SELECTED_DATE));
    renderScheduleList();
    const target = bar.querySelector(`.date-pill[data-date="${SELECTED_DATE}"]`);
    if (target) target.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' });
  });

  renderScheduleList();
}

function renderScheduleList() {
  const el = document.getElementById('scheduleList');
  const matches = ALL_MATCHES
    .filter(m => cstDateStr(m) === SELECTED_DATE)
    .sort((a, b) => a.match_time.localeCompare(b.match_time));
  if (!matches.length) {
    el.innerHTML = '<div class="panel" style="text-align:center;color:var(--text-mute);padding:32px">该日期暂无比赛</div>';
    return;
  }
  let html = '';
  let lastTimeBucket = '';
  for (const m of matches) {
    const hour = cstHour(m);
    const bucket = hour < 6 ? '凌晨档' : hour < 12 ? '上午档' : hour < 18 ? '下午档' : '晚间档';
    if (bucket !== lastTimeBucket) {
      html += `<div class="match-day-title"><strong>${bucket}</strong> · ${cstTimeStr(m)} 后开球</div>`;
      lastTimeBucket = bucket;
    }
    html += matchRow(m);
  }
  el.innerHTML = html;
}

function matchRow(m) {
  const isFinished = m.status === 'finished';
  const isLive = m.status === 'live';
  const isToday = cstDateStr(m) === todayCst();
  const roundLabel = roundCN(m.round, m.group_name);
  const roundCls = roundTagClass(m.round);
  let scoreHtml;
  if (isFinished) scoreHtml = `<span>${m.home_score}</span><span class="sep">:</span><span>${m.away_score}</span>`;
  else if (isLive) scoreHtml = `<span>${m.home_score ?? 0}</span><span class="sep">:</span><span>${m.away_score ?? 0}</span><span class="extra">进行中</span>`;
  else scoreHtml = `<span>—</span><span class="sep">vs</span><span>—</span>`;
  const home = TEAM_CN[m.home_team] || m.home_team;
  const away = TEAM_CN[m.away_team] || m.away_team;
  let statusLabel, statusCls;
  if (isLive) { statusLabel = '直播中'; statusCls = 'live'; }
  else if (isFinished) { statusLabel = '已结束'; statusCls = 'finished'; }
  else if (isToday) { statusLabel = '今日'; statusCls = 'today'; }
  else { statusLabel = '未开赛'; statusCls = 'scheduled'; }
  return `
    <div class="match-row">
      <div class="time"><strong>${cstTimeStr(m)}</strong>${cstDateStr(m).slice(5)}</div>
      <div class="round-tag ${roundCls}">${roundLabel}</div>
      <div class="team home">
        <span class="flag">${FLAG[m.home_team] || '🏳️'}</span>
        <span class="name">${home}</span>
      </div>
      <div class="score ${m.status}">${scoreHtml}</div>
      <div class="team away">
        <span class="name">${away}</span>
        <span class="flag">${FLAG[m.away_team] || '🏳️'}</span>
      </div>
      <div class="venue">${m.venue || ''}</div>
      <div class="status ${statusCls}">${statusLabel}</div>
    </div>
  `;
}

// ============================================================
// 预测榜
// ============================================================
// ============================================================
// 预测命中集锦 (v1.2) — 已猜对比赛的"截图证据"
// ============================================================
const HIT_FILTER_STATE = { filter: 'all' };
let HIT_HIGHLIGHTS_DATA = [];
let HIT_HIGHLIGHTS_TIMER = null;

function getActualWinnerLocal(m) {
  if (m.home_score > m.away_score) return m.home_team;
  if (m.home_score < m.away_score) return m.away_team;
  return 'draw';
}

async function renderHitHighlights() {
  const grid = document.getElementById('hitGrid');
  if (!grid) return;
  try {
    const data = await fetch('/api/matches?limit=500').then(r => r.json());
    const finished = data.filter(m => m.status === 'finished' 
      && m.predicted_winner && m.predicted_winner !== 'TBD'
      && m.predicted_home_score != null && m.predicted_away_score != null);
    
    if (!finished.length) {
      grid.innerHTML = '<div class="hit-empty">尚无已结束比赛 · 完赛后将自动展示命中场次</div>';
      document.getElementById('hitCountAll').textContent = '0';
      document.getElementById('hitCountExact').textContent = '0';
      document.getElementById('hitCountWinner').textContent = '0';
      document.getElementById('hitStatTotal').textContent = '0';
      document.getElementById('hitStatExact').textContent = '0';
      document.getElementById('hitStatRate').textContent = '—';
      document.getElementById('hitStatLast').textContent = '—';
      return;
    }
    
    // 计算每场命中情况
    const enriched = finished.map(m => {
      const actual = getActualWinnerLocal(m);
      const pw = m.predicted_winner;
      const isHit = pw === actual;
      const isExact = m.predicted_home_score === m.home_score && m.predicted_away_score === m.away_score;
      return { ...m, _actual: actual, _isHit: isHit, _isExact: isExact };
    });
    
    const hits = enriched.filter(m => m._isHit);
    const exactHits = enriched.filter(m => m._isExact);
    
    // 更新顶部统计
    document.getElementById('hitCountAll').textContent = hits.length;
    document.getElementById('hitCountExact').textContent = exactHits.length;
    document.getElementById('hitCountWinner').textContent = hits.length - exactHits.length;
    document.getElementById('hitStatTotal').textContent = hits.length;
    document.getElementById('hitStatExact').textContent = exactHits.length;
    document.getElementById('hitStatRate').textContent = (hits.length / finished.length * 100).toFixed(1) + '%';
    
    // 最近命中时间
    const latest = hits.sort((a, b) => (b.match_date + b.match_time).localeCompare(a.match_date + a.match_time))[0];
    if (latest) {
      document.getElementById('hitStatLast').textContent = latest.match_date.slice(5);
    }
    
    HIT_HIGHLIGHTS_DATA = hits.sort((a, b) => (b.match_date + b.match_time).localeCompare(a.match_date + a.match_time));
    
    // 应用过滤
    applyHitFilter();
    
    // 绑定过滤按钮（只绑一次）
    bindHitFilterButtons();
  } catch (e) {
    console.error('renderHitHighlights failed', e);
    grid.innerHTML = '<div class="hit-empty hit-empty-error">加载失败 · ' + (e?.message || e) + '</div>';
  }
}

function bindHitFilterButtons() {
  if (bindHitFilterButtons._bound) return;
  bindHitFilterButtons._bound = true;
  document.querySelectorAll('.hit-filter').forEach(btn => {
    btn.addEventListener('click', () => {
      HIT_FILTER_STATE.filter = btn.dataset.filter;
      document.querySelectorAll('.hit-filter').forEach(b => {
        b.classList.toggle('active', b === btn);
        b.setAttribute('aria-selected', b === btn ? 'true' : 'false');
      });
      applyHitFilter();
      syncUrlState();
      // 切换过滤时给个反馈
      const labels = { all: '全部命中', exact: '精确命中', winner: '胜方命中' };
      toast(`已筛选：${labels[HIT_FILTER_STATE.filter] || HIT_FILTER_STATE.filter}`, 'info', 1500);
    });
  });
}

function applyHitFilter() {
  const grid = document.getElementById('hitGrid');
  if (!grid) return;
  let list = HIT_HIGHLIGHTS_DATA;
  if (HIT_FILTER_STATE.filter === 'exact') {
    list = list.filter(m => m._isExact);
  } else if (HIT_FILTER_STATE.filter === 'winner') {
    list = list.filter(m => !m._isExact);
  }
  
  if (!list.length) {
    grid.innerHTML = '<div class="hit-empty">该筛选下暂无命中场次</div>';
    return;
  }
  
  grid.innerHTML = list.slice(0, 12).map(m => renderHitCard(m)).join('');
}

function renderHitCard(m) {
  const homeCn = TEAM_CN[m.home_team] || m.home_team;
  const awayCn = TEAM_CN[m.away_team] || m.away_team;
  const homeFlag = FLAG[m.home_team] || '🏳️';
  const awayFlag = FLAG[m.away_team] || '🏳️';
  const winnerCn = m._actual === 'draw' ? '平局' : (TEAM_CN[m._actual] || m._actual);
  const predCn = m.predicted_winner === 'draw' ? '平局' : (TEAM_CN[m.predicted_winner] || m.predicted_winner);
  
  // 计算胜方胜率
  const predPct = m.predicted_winner === 'draw' ? m.draw_prob :
                  m.predicted_winner === m.home_team ? m.home_win_prob : m.away_win_prob;
  
  // 卡片类型
  const cardCls = m._isExact ? 'hit-card exact' : 'hit-card winner';
  const badgeHtml = m._isExact 
    ? '<span class="hit-badge hit-badge-exact" title="预测比分与实际完全一致">🎯 精确命中</span>'
    : '<span class="hit-badge hit-badge-winner" title="预测胜方正确，比分有偏差">✅ 胜方命中</span>';
  
  return `
    <article class="${cardCls}" data-match-id="${m.match_id}" role="button" tabindex="0"
             aria-label="${homeCn} vs ${awayCn} 预测命中证据，点击查看详情" title="点击查看比赛详情">
      <span class="hit-card-hint">点击查看详情 →</span>
      <header class="hit-card-head">
        <span class="hit-match-id">${m.match_id}</span>
        <span class="hit-match-time">${m.match_date} ${m.match_time}</span>
        <span class="hit-match-group">Group ${m.group_name || '?'}</span>
        ${badgeHtml}
      </header>
      <div class="hit-card-match">
        <div class="hit-team hit-team-home">
          <span class="hit-flag">${homeFlag}</span>
          <span class="hit-name">${homeCn}</span>
        </div>
        <div class="hit-card-score">
          <div class="hit-score-col hit-score-pred">
            <div class="hit-score-label">🤖 AI 预测</div>
            <div class="hit-score-value">${m.predicted_home_score} : ${m.predicted_away_score}</div>
            <div class="hit-score-sub">${predCn} · 胜率 ${predPct.toFixed(1)}%</div>
          </div>
          <div class="hit-score-arrow">→</div>
          <div class="hit-score-col hit-score-actual">
            <div class="hit-score-label">📊 实际结果</div>
            <div class="hit-score-value">${m.home_score} : ${m.away_score}</div>
            <div class="hit-score-sub">${winnerCn} 胜</div>
          </div>
        </div>
        <div class="hit-team hit-team-away">
          <span class="hit-name">${awayCn}</span>
          <span class="hit-flag">${awayFlag}</span>
        </div>
      </div>
      <footer class="hit-card-foot">
        <span class="hit-foot-item">⏱️ 预测时间: 赛前 ≥ 24h</span>
        <span class="hit-foot-item">🎯 胜方置信: ${predPct.toFixed(0)}%</span>
        <span class="hit-foot-item">📈 完赛: ${m.match_date}</span>
      </footer>
    </article>
  `;
}

function renderPredictions(preds) {
  const top = preds.slice(0, 20);
  const sorted = [...top].reverse();
  ChartManager.set('chartPredictions', {
    backgroundColor: CHART_BG,
    grid: { left: 120, right: 60, top: 8, bottom: 24 },
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' },
      formatter: p => {
        const i = p[0].dataIndex;
        const d = sorted[sorted.length - 1 - i];
        return `<b>${TEAM_CN[d.team]||d.team}</b><br/>冠军: <b style="color:${GOLD2}">${d.champion_prob.toFixed(2)}%</b><br/>4强: ${d.sf_prob.toFixed(1)}% · 8强: ${d.qf_prob.toFixed(1)}% · 16强: ${d.r16_prob.toFixed(1)}%`;
      },
      backgroundColor: 'rgba(15,28,48,0.95)', borderColor: GOLD, textStyle: { color: TEXT }
    },
    xAxis: { type: 'value', axisLine: { lineStyle: { color: MUTE } }, axisLabel: { color: DIM, formatter: '{value}%' }, splitLine: { lineStyle: { color: 'rgba(255,255,255,0.04)' } } },
    yAxis: { type: 'category', data: sorted.map(p => `${FLAG[p.team]||''} ${TEAM_CN[p.team]||p.team}`), axisLine: { lineStyle: { color: MUTE } }, axisLabel: { color: TEXT, fontSize: 11 } },
    series: [{
      type: 'bar', data: sorted.map(p => p.champion_prob),
      itemStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
          { offset: 0, color: GOLD }, { offset: 1, color: GOLD2 }
        ]),
        borderRadius: [0, 4, 4, 0]
      },
      label: { show: true, position: 'right', color: GOLD2, fontSize: 11, formatter: '{c}%' },
      barWidth: 14,
    }]
  });

  const top6 = top.slice(0, 6);
  const colors = [GOLD, GOLD2, BLUE, GREEN, RED, '#b794f6'];
  ChartManager.set('chartStages', {
    backgroundColor: CHART_BG,
    legend: { data: top6.map(p => TEAM_CN[p.team]||p.team), textStyle: { color: DIM, fontSize: 10 }, bottom: 0, type: 'scroll' },
    tooltip: { trigger: 'item' },
    radar: {
      indicator: [{name: '32强', max: 100},{name: '16强', max: 100},{name: '8强', max: 100},{name: '4强', max: 100},{name: '冠军', max: 50}],
      shape: 'polygon', splitNumber: 4,
      axisName: { color: TEXT, fontSize: 10 },
      splitLine: { lineStyle: { color: 'rgba(255,255,255,0.1)' } },
      splitArea: { areaStyle: { color: ['rgba(255,255,255,0.02)', 'rgba(255,255,255,0.04)'] } },
      axisLine: { lineStyle: { color: 'rgba(255,255,255,0.1)' } },
    },
    series: [{
      type: 'radar',
      data: top6.map((p, i) => ({
        name: TEAM_CN[p.team]||p.team,
        value: [p.r32_prob, p.r16_prob, p.qf_prob, p.sf_prob, p.champion_prob],
        areaStyle: { opacity: 0.12 },
        lineStyle: { width: 2, color: colors[i] },
        itemStyle: { color: colors[i] },
      }))
    }]
  });
}

// ============================================================
// 射手榜
// ============================================================
function renderScorers(scorers) {
  const el = document.getElementById('topScorers');
  if (!scorers.length) {
    el.innerHTML = '<div style="padding:20px;color:var(--text-mute);text-align:center;font-size:12px">尚无进球</div>';
    return;
  }
  el.innerHTML = scorers.map((s, i) => `
    <div class="scorer-row">
      <span class="scorer-rank">${i+1}</span>
      <span class="scorer-team">${FLAG[s.team]||''} ${TEAM_CN[s.team]||s.team}</span>
      <span class="scorer-name">${s.player}</span>
      <span class="scorer-goals">${s.goals}</span>
    </div>
  `).join('');
}

async function renderFullScorers() {
  const wrap = document.getElementById('scorersTableWrap');
  const tsEl = document.getElementById('scorersTs');
  const sourceTag = document.getElementById('scorersSourceTag');
  try {
    const data = await fetch('/api/scorers?limit=20').then(r => r.json());
    const list = data.scorers || [];
    if (sourceTag) sourceTag.textContent = (data.source || 'auto').toUpperCase();
    if (tsEl && data.ts) tsEl.textContent = data.ts.slice(0, 19).replace('T', ' ') + ' UTC';
    if (!list.length) {
      wrap.innerHTML = '<div class="scorers-empty"><div class="icon">⚽</div>暂无射手数据</div>';
      return;
    }
    const rows = list.map((s, i) => `
      <tr>
        <td class="rank-cell">${s.rank ?? i+1}</td>
        <td>${FLAG[s.team]||''} ${TEAM_CN[s.team]||s.team}</td>
        <td>${s.player}</td>
        <td class="goals-cell">${s.goals}</td>
        <td class="pk-cell ${s.penalties > 0 ? 'has-pk' : ''}">${s.penalties || 0}</td>
        <td class="matches-cell">${s.matches || '-'}</td>
        <td class="mpg-cell">${s.mins_per_goal ? `<strong>${s.mins_per_goal}</strong>'` : '—'}</td>
      </tr>
    `).join('');
    wrap.innerHTML = `
      <table class="scorers-table">
        <colgroup><col><col><col><col><col><col><col></colgroup>
        <thead><tr><th>排名</th><th>球队</th><th>球员</th><th>进球</th><th>点球</th><th>出场</th><th>分钟/球</th></tr></thead>
        <tbody>${rows}</tbody>
      </table>
    `;
  } catch (e) {
    console.error('Scorers failed', e);
    wrap.innerHTML = renderError('射手榜加载失败', '请稍后再试', () => renderFullScorers());
  }
}

document.getElementById('refreshScorersBtn')?.addEventListener('click', () => {
  document.getElementById('scorersTableWrap').innerHTML = '<div class="scorers-loading">刷新中...</div>';
  renderFullScorers();
});

// ============================================================
// 历史
// ============================================================
function renderHistory(history) {
  const champCounts = {};
  history.forEach(h => { champCounts[h.champion] = (champCounts[h.champion] || 0) + 1; });
  const champList = Object.entries(champCounts).sort((a, b) => b[1] - a[1]);

  ChartManager.set('chartChampions', {
    backgroundColor: CHART_BG,
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' },
      backgroundColor: 'rgba(15,28,48,0.95)', borderColor: GOLD, textStyle: { color: TEXT } },
    grid: { left: 90, right: 24, top: 16, bottom: 24 },
    xAxis: { type: 'value', axisLine: { lineStyle: { color: MUTE } }, axisLabel: { color: DIM }, splitLine: { lineStyle: { color: 'rgba(255,255,255,0.04)' } } },
    yAxis: { type: 'category', data: champList.reverse().map(c => `${FLAG[c[0]]||''} ${TEAM_CN[c[0]]||c[0]}`), axisLine: { lineStyle: { color: MUTE } }, axisLabel: { color: TEXT, fontSize: 11 } },
    series: [{
      type: 'bar', data: champList.map(c => c[1]),
      itemStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
          { offset: 0, color: '#8a6a1a' }, { offset: 1, color: GOLD2 }
        ]),
        borderRadius: [0, 4, 4, 0]
      },
      label: { show: true, position: 'right', color: GOLD2, fontSize: 11, formatter: '{c} 次' },
      barWidth: 16,
    }]
  });

  ChartManager.set('chartEvolution', {
    backgroundColor: CHART_BG,
    tooltip: { trigger: 'axis',
      backgroundColor: 'rgba(15,28,48,0.95)', borderColor: GOLD, textStyle: { color: TEXT } },
    legend: { data: ['场次', '进球数', '参赛队数'], textStyle: { color: DIM, fontSize: 11 }, top: 0 },
    grid: { left: 50, right: 50, top: 36, bottom: 36 },
    xAxis: { type: 'category', data: history.map(h => h.year), axisLine: { lineStyle: { color: MUTE } }, axisLabel: { color: DIM } },
    yAxis: [
      { type: 'value', name: '场次 / 进球', axisLine: { lineStyle: { color: MUTE } }, axisLabel: { color: DIM }, splitLine: { lineStyle: { color: 'rgba(255,255,255,0.04)' } } },
      { type: 'value', name: '队数', axisLine: { lineStyle: { color: MUTE } }, axisLabel: { color: DIM }, splitLine: { show: false } }
    ],
    series: [
      { name: '场次', type: 'line', smooth: true, data: history.map(h => h.matches_played), itemStyle: { color: GOLD }, lineStyle: { width: 2 }, areaStyle: { opacity: 0.1, color: GOLD }, symbol: 'circle', symbolSize: 6 },
      { name: '进球数', type: 'line', smooth: true, data: history.map(h => h.goals_scored), itemStyle: { color: GREEN }, lineStyle: { width: 2 }, symbol: 'circle', symbolSize: 6 },
      { name: '参赛队数', type: 'bar', yAxisIndex: 1, data: history.map(h => h.teams), itemStyle: { color: 'rgba(78, 168, 255, 0.5)', borderRadius: [3,3,0,0] }, barWidth: 10 },
    ]
  });
}

// ============================================================
// 时间戳 + 比赛日
// ============================================================
function updateTs(ts) {
  const el = document.getElementById('updateTs');
  if (ts && el) el.textContent = ts.slice(0, 19).replace('T', ' ') + ' UTC';
}

function updateLiveStatus() {
  const nowCst = new Date().toLocaleDateString('en-CA', { timeZone: 'Asia/Shanghai' });
  const startCst = '2026-06-11';
  const day = Math.round((new Date(nowCst) - new Date(startCst)) / 86400000) + 1;
  const el = document.getElementById('liveStatus');
  if (el) el.textContent = `实时 · 第 ${day} 比赛日 · CST`;
}

updateLiveStatus();
setInterval(updateLiveStatus, 60000);

// ============================================================
// 回到顶部按钮 (v1.2)
// ============================================================
(() => {
  const btn = document.getElementById('backToTop');
  if (!btn) return;
  const THRESHOLD = 480;
  let ticking = false;
  const update = () => {
    btn.classList.toggle('visible', window.scrollY > THRESHOLD);
    ticking = false;
  };
  window.addEventListener('scroll', () => {
    if (!ticking) { requestAnimationFrame(update); ticking = true; }
  }, { passive: true });
  btn.addEventListener('click', () => {
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    window.scrollTo({ top: 0, behavior: reduced ? 'auto' : 'smooth' });
  });
  update();
})();

// ============================================================
// AI 准确率徽章 → 翻车榜联动（事件委托）
// ============================================================
(() => {
  const handler = (el, evt) => {
    evt?.preventDefault?.();
    // v1.2: 改为打开翻车榜弹窗
    showUpsetModal();
  };

  document.addEventListener('click', (e) => {
    const el = e.target.closest('.ai-acc');
    if (el) {
      handler(el, e);
    }
  });
  document.addEventListener('keydown', (e) => {
    if (e.key !== 'Enter' && e.key !== ' ') return;
    const el = e.target.closest && e.target.closest('.ai-acc');
    if (el && document.activeElement === el) {
      handler(el, e);
    }
  });
})();

// ============================================================
// 比赛详情弹窗 (v1.2) — 点击 hit-card / 键盘 Enter 触发
// ============================================================
let CURRENT_MATCH = null;

async function showMatchDetail(matchId) {
  const modal = document.getElementById('matchModal');
  const body = document.getElementById('matchModalBody');
  const title = document.getElementById('matchModalTitle');
  if (!modal || !body) return;
  
  body.innerHTML = '<div class="skeleton" style="height:40px"></div><div class="skeleton" style="height:200px"></div>';
  title.textContent = `加载 ${matchId}...`;
  modal.hidden = false;
  document.body.style.overflow = 'hidden';
  
  try {
    const m = await fetch(`/api/matches/${matchId}`).then(r => {
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      return r.json();
    });
    CURRENT_MATCH = m;
    
    // 命中判定
    const actual = m.home_score > m.away_score ? m.home_team : (m.home_score < m.away_score ? m.away_team : 'draw');
    const isHit = m.predicted_winner === actual;
    const isExact = m.predicted_home_score === m.home_score && m.predicted_away_score === m.away_score;
    
    const homeCn = TEAM_CN[m.home_team] || m.home_team;
    const awayCn = TEAM_CN[m.away_team] || m.away_team;
    const homeFlag = FLAG[m.home_team] || '🏳️';
    const awayFlag = FLAG[m.away_team] || '🏳️';
    
    title.textContent = `${m.match_id} · ${homeCn} vs ${awayCn}`;
    
    body.innerHTML = `
      ${renderVerdictBadge(m, actual, isHit, isExact)}
      
      <div class="modal-matchup">
        <div class="modal-team modal-team-home">
          <span class="flag">${homeFlag}</span>
          <span>${homeCn}</span>
        </div>
        <div class="modal-score-final">
          <span class="vs">FINAL</span>
          ${m.home_score} : ${m.away_score}
        </div>
        <div class="modal-team modal-team-away">
          <span>${awayCn}</span>
          <span class="flag">${awayFlag}</span>
        </div>
      </div>
      
      <div class="modal-meta-grid">
        <div class="modal-meta-item">
          <div class="modal-meta-v">${m.match_date}</div>
          <div class="modal-meta-l">比赛日期</div>
        </div>
        <div class="modal-meta-item">
          <div class="modal-meta-v">${m.match_time}</div>
          <div class="modal-meta-l">开球时间</div>
        </div>
        <div class="modal-meta-item">
          <div class="modal-meta-v">Group ${m.group_name || '?'}</div>
          <div class="modal-meta-l">${m.round || ''}</div>
        </div>
        <div class="modal-meta-item">
          <div class="modal-meta-v">${m.venue || '—'}</div>
          <div class="modal-meta-l">球场</div>
        </div>
        <div class="modal-meta-item">
          <div class="modal-meta-v">${m.home_win_prob.toFixed(0)}% / ${m.draw_prob.toFixed(0)}% / ${m.away_win_prob.toFixed(0)}%</div>
          <div class="modal-meta-l">主 / 平 / 客 胜率</div>
        </div>
        <div class="modal-meta-item">
          <div class="modal-meta-v">${m.predicted_home_score} : ${m.predicted_away_score}</div>
          <div class="modal-meta-l">🤖 预测比分</div>
        </div>
      </div>
      
      ${renderGoalsTimeline(m)}
      ${renderScoreDistribution(m, isExact)}
      ${renderLineupSection(m.match_id)}
    `;

    // 异步拉阵容 (不阻塞 modal 主显示)
    loadLineup(m.match_id, homeCn, awayCn, homeFlag, awayFlag);
  } catch (e) {
    body.innerHTML = `<div class="dist-empty" style="color:#ff8a9e">❌ 加载失败: ${e.message}</div>`;
  }
}

// ============================================================
// v2.1: 阵容 (lineup) 显示
// ============================================================
function renderLineupSection(matchId) {
  // 占位: 由 loadLineup() 异步填充
  return `
    <div class="lineup-section" id="lineup-${matchId}">
      <div class="lineup-section-head">
        <span class="lineup-ic">⚽</span>
        <span class="lineup-title">首发阵容</span>
        <span class="lineup-hint">点击展开</span>
      </div>
      <div class="lineup-loading">⏳ 加载中...</div>
    </div>
  `;
}

async function loadLineup(matchId, homeCn, awayCn, homeFlag, awayFlag) {
  const el = document.getElementById(`lineup-${matchId}`);
  if (!el) return;
  try {
    const r = await fetch(`/api/matches/${matchId}/lineup`);
    if (r.status === 404) {
      el.innerHTML = `
        <div class="lineup-section-head">
          <span class="lineup-ic">⚽</span>
          <span class="lineup-title">首发阵容</span>
          <span class="lineup-hint">尚未公布</span>
        </div>
        <div class="lineup-empty">尚未公布 (CCTV 赛前 1h / 赛中 公布)</div>
      `;
      return;
    }
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    const d = await r.json();
    el.innerHTML = `
      <div class="lineup-section-head" data-lineup-toggle>
        <span class="lineup-ic">⚽</span>
        <span class="lineup-title">首发阵容</span>
        <span class="lineup-source">来源: ESPN</span>
        <span class="lineup-hint">点击收起 / 展开</span>
      </div>
      <div class="lineup-grid">
        ${renderLineupTeam('home', homeCn, homeFlag, d.home)}
        ${renderLineupTeam('away', awayCn, awayFlag, d.away)}
      </div>
    `;
    // 折叠交互
    el.querySelector('[data-lineup-toggle]')?.addEventListener('click', () => {
      el.classList.toggle('collapsed');
    });
  } catch (e) {
    el.innerHTML = `
      <div class="lineup-section-head">
        <span class="lineup-ic">⚽</span>
        <span class="lineup-title">首发阵容</span>
        <span class="lineup-hint">加载失败</span>
      </div>
      <div class="lineup-empty">❌ 加载失败: ${e.message}</div>
    `;
  }
}

function renderLineupTeam(side, teamCn, flag, lu) {
  if (!lu || !lu.players || !lu.players.length) {
    return `<div class="lineup-team lineup-${side}">
      <div class="lineup-team-head">
        <span class="flag">${flag}</span>
        <span class="name">${teamCn}</span>
      </div>
      <div class="lineup-empty">阵容数据不可用</div>
    </div>`;
  }
  const starters = lu.players.filter(p => p.starter);
  const subs = lu.players.filter(p => !p.starter);
  // 阵型 4-3-3 → 4 3 3 数字
  const formationNums = (lu.formation || '').split('-').map(s => parseInt(s, 10)).filter(n => !isNaN(n));

  return `<div class="lineup-team lineup-${side}">
    <div class="lineup-team-head">
      <span class="flag">${flag}</span>
      <span class="name">${teamCn}</span>
      <span class="formation">${lu.formation || '?'}</span>
      <span class="coach">主帅: ${lu.coach || '—'}</span>
    </div>

    <!-- 球场可视化 -->
    <div class="lineup-pitch">
      <div class="lineup-pitch-lines">
        <div class="lineup-pitch-center-circle"></div>
        <div class="lineup-pitch-center-line"></div>
        <div class="lineup-pitch-penalty-top"></div>
        <div class="lineup-pitch-penalty-bot"></div>
      </div>
      ${renderPitchPlayers(starters, formationNums, side)}
    </div>

    <div class="lineup-starters-list">
      <div class="lineup-list-head">首发 (${starters.length})</div>
      ${starters.map(p => `
        <div class="lineup-player ${p.starter ? 'is-starter' : 'is-sub'}">
          <span class="lp-jersey">${p.jersey || '-'}</span>
          <span class="lp-name">${p.name}</span>
          <span class="lp-pos">${p.position || ''}</span>
        </div>
      `).join('')}
    </div>

    ${subs.length ? `
    <details class="lineup-subs">
      <summary>替补 (${subs.length})</summary>
      <div class="lineup-subs-list">
        ${subs.map(p => `
          <div class="lineup-player is-sub">
            <span class="lp-jersey">${p.jersey || '-'}</span>
            <span class="lp-name">${p.name}</span>
            <span class="lp-pos">${p.position || ''}</span>
          </div>
        `).join('')}
      </div>
    </details>
    ` : ''}
  </div>`;
}

function renderPitchPlayers(starters, formationNums, side) {
  // 阵型可视化: 4-3-3 → [GK, 4 defenders, 3 mids, 3 fwds]
  // 守门员在最底 (主队) 或最顶 (客队), 然后倒序
  // 11 = 1 GK + formationNums 之和
  // 渲染行: formationNums + 1
  if (!formationNums.length || !starters.length) {
    // 退化为单行
    return `<div class="lineup-pitch-row" style="bottom:10%">
      ${starters.map(p => `<div class="lineup-pitch-player" title="#${p.jersey} ${p.name}">
        <div class="lpp-num">${p.jersey || '-'}</div>
      </div>`).join('')}
    </div>`;
  }
  const totalOutfield = formationNums.reduce((a,b)=>a+b, 0);
  if (totalOutfield + 1 !== starters.length) {
    // 阵型数字和首发数不匹配
    return `<div class="lineup-pitch-row" style="bottom:10%">
      ${starters.map(p => `<div class="lineup-pitch-player" title="#${p.jersey} ${p.name}">
        <div class="lpp-num">${p.jersey || '-'}</div>
      </div>`).join('')}
    </div>`;
  }
  // 按 formationPlace 排序
  const sorted = [...starters].sort((a,b) => (a.formation_place||0) - (b.formation_place||0));
  // GK + formation 行 (从守门员到前场)
  const rows = [];
  // GK (formation_place=1) 放最底
  rows.push([sorted[0]]);
  // formation 倒序放: 4-3-3 实际是 3 前 / 3 中 / 4 后 / 1 GK
  // 所以 rows = [GK, 4 defenders, 3 mids, 3 fwds] (从下到上)
  // 实际按 formationPlace: 1=GK, 2-5=defenders, 6-8=mids, 9-11=fwds
  let idx = 1;
  for (let i = formationNums.length - 1; i >= 0; i--) {
    const count = formationNums[i];
    rows.push(sorted.slice(idx, idx + count));
    idx += count;
  }
  // 渲染: row 0 (GK) 在最底, row 1+ 向上
  // 球场从底到顶: 0%, 20%, 40%, 60%, 80% (depending on rows)
  const totalRows = rows.length;
  return rows.map((row, rowIdx) => {
    const bottomPct = rowIdx === 0 ? 5 : 5 + rowIdx * (90 / totalRows);
    return `<div class="lineup-pitch-row" style="bottom:${bottomPct}%">
      ${row.map(p => `<div class="lineup-pitch-player" title="#${p.jersey} ${p.name}">
        <div class="lpp-num">${p.jersey || '-'}</div>
      </div>`).join('')}
    </div>`;
  }).join('');
}

function renderVerdictBadge(m, actual, isHit, isExact) {
  if (isExact) {
    return `<div class="modal-verdict exact">
      <span class="modal-verdict-icon">🎯</span>
      <span>精确比分命中！AI 预测 ${m.predicted_home_score}-${m.predicted_away_score}，实际 ${m.home_score}-${m.away_score}</span>
    </div>`;
  } else if (isHit) {
    const winnerCn = actual === 'draw' ? '平局' : (TEAM_CN[actual] || actual);
    return `<div class="modal-verdict winner">
      <span class="modal-verdict-icon">✅</span>
      <span>胜方命中！AI 看好 <strong>${winnerCn}</strong>，${winnerCn} 确实赢了（比分 ${m.home_score}-${m.away_score}）</span>
    </div>`;
  } else {
    return `<div class="modal-verdict miss">
      <span class="modal-verdict-icon">❌</span>
      <span>未命中：AI 看好 <strong>${TEAM_CN[m.predicted_winner] || m.predicted_winner}</strong>，实际 <strong>${TEAM_CN[actual] || actual}</strong> 胜</span>
    </div>`;
  }
}

function renderGoalsTimeline(m) {
  // 优先用 m.goals（API 详情），fallback 用 m._goals
  const goals = m.goals || m._goals || [];
  if (!goals.length) {
    return `
      <div class="modal-section">
        <div class="modal-section-title">⚽ 进球时间线</div>
        <div class="dist-empty">本场暂无进球数据 ${m.home_score === 0 && m.away_score === 0 ? '（双方均未进球）' : ''}</div>
      </div>
    `;
  }
  // 收集所有分钟数 + 计算位置百分比
  const maxMin = 95;
  const events = goals.map(g => {
    const min = Math.max(1, Math.min(95, g.minute || 0));
    const pct = (min / maxMin) * 100;
    const team = g.team === m.home_team ? 'home' : 'away';
    return { ...g, pct, team };
  });
  
  return `
    <div class="modal-section">
      <div class="modal-section-title">⚽ 进球时间线 · 共 ${goals.length} 球</div>
      <div class="goals-timeline">
        <div class="goals-timeline-marks">
          <span>1'</span><span>15'</span><span>30'</span><span>45'</span><span>60'</span><span>75'</span><span>90+</span>
        </div>
        <div class="goals-timeline-track"></div>
        <div class="goals-timeline-events">
          ${events.map(g => {
            const top = g.team === m.home_team ? '0' : '20px';
            return `
              <div class="goal-event" style="left:${g.pct}%; top:${top}" 
                   title="${g.minute}' ${TEAM_CN[g.team] || g.team} - ${g.scorer || '匿名'}">
                <span class="goal-icon">⚽</span>
                <span class="goal-min">${g.minute}'</span>
                <span class="goal-scorer">${g.scorer || ''}</span>
              </div>
            `;
          }).join('')}
        </div>
      </div>
    </div>
  `;
}

function renderScoreDistribution(m, isExact) {
  if (!m.score_distribution_json) {
    return `
      <div class="modal-section">
        <div class="modal-section-title">📊 AI 概率分布</div>
        <div class="dist-empty">本场无概率分布数据</div>
      </div>
    `;
  }
  let dist;
  try {
    dist = JSON.parse(m.score_distribution_json);
  } catch (e) {
    return `<div class="modal-section"><div class="modal-section-title">📊 AI 概率分布</div><div class="dist-empty">概率数据解析失败</div></div>`;
  }
  const entries = Object.entries(dist)
    .map(([k, v]) => ({ score: k, pct: parseFloat(v) }))
    .sort((a, b) => b.pct - a.pct)
    .slice(0, 10);
  const actualKey = `${m.home_score}-${m.away_score}`;
  const max = Math.max(...entries.map(e => e.pct), 1);
  
  return `
    <div class="modal-section">
      <div class="modal-section-title">📊 AI 概率分布 Top 10 · 实际比分高亮</div>
      <div class="dist-chart">
        ${entries.map(e => {
          const isActual = e.score === actualKey;
          const isPredicted = e.score === `${m.predicted_home_score}-${m.predicted_away_score}`;
          const rowCls = isActual ? 'is-actual' : (isPredicted ? 'is-predicted' : '');
          return `
            <div class="dist-row ${rowCls}">
              <div class="dist-label">${e.score}</div>
              <div class="dist-bar-track">
                <div class="dist-bar-fill" style="width:${(e.pct / max) * 100}%"></div>
              </div>
              <div class="dist-value">${e.pct.toFixed(2)}%</div>
            </div>
          `;
        }).join('')}
      </div>
      <div style="margin-top:8px; font-size:10px; color:var(--text-mute); display:flex; gap:12px; flex-wrap:wrap">
        <span><span style="display:inline-block;width:10px;height:10px;background:linear-gradient(90deg,#4ade80,#f9d76b);border-radius:2px;vertical-align:middle"></span> 实际比分</span>
        <span><span style="display:inline-block;width:10px;height:10px;background:linear-gradient(90deg,#c084fc,#a855f7);border-radius:2px;vertical-align:middle"></span> AI 预测比分</span>
        <span style="color:var(--gold-2)">★ ${actualKey} 实际概率 ${dist[actualKey]?.toFixed(2) || '0.00'}%（${isExact ? 'AI 押对了' : 'AI 未押中此比分'}）</span>
      </div>
    </div>
  `;
}

function closeMatchModal() {
  const modal = document.getElementById('matchModal');
  if (modal) {
    modal.hidden = true;
    document.body.style.overflow = '';
    CURRENT_MATCH = null;
  }
}

// 事件委托：点击 / 键盘 hit-card → 弹窗
document.addEventListener('click', (e) => {
  const card = e.target.closest('.hit-card');
  if (card && card.dataset.matchId) {
    showMatchDetail(card.dataset.matchId);
  }
  // 关闭按钮 / overlay 点击
  if (e.target.closest('[data-close-modal]')) {
    closeMatchModal();
  }
  // 分享按钮
  if (e.target.closest('#matchModalShare')) {
    shareMatchAsImage();
  }
  // 复制按钮
  if (e.target.closest('#matchModalCopy')) {
    copyMatchShareText();
  }
});
document.addEventListener('keydown', (e) => {
  // 关闭弹窗
  if (e.key === 'Escape' && !document.getElementById('matchModal').hidden) {
    closeMatchModal();
  }
  // 键盘 enter 触发 hit-card
  if ((e.key === 'Enter' || e.key === ' ') && document.activeElement && document.activeElement.classList && document.activeElement.classList.contains('hit-card')) {
    e.preventDefault();
    const card = document.activeElement;
    if (card.dataset.matchId) showMatchDetail(card.dataset.matchId);
  }
});

// 复制分享文案到剪贴板
async function copyMatchShareText() {
  if (!CURRENT_MATCH) return;
  const m = CURRENT_MATCH;
  const actual = m.home_score > m.away_score ? m.home_team : (m.home_score < m.away_score ? m.away_team : 'draw');
  const isHit = m.predicted_winner === actual;
  const isExact = m.predicted_home_score === m.home_score && m.predicted_away_score === m.away_score;
  
  const homeCn = TEAM_CN[m.home_team] || m.home_team;
  const awayCn = TEAM_CN[m.away_team] || m.away_team;
  const winnerCn = actual === 'draw' ? '平局' : (TEAM_CN[actual] || actual);
  const predCn = m.predicted_winner === 'draw' ? '平局' : (TEAM_CN[m.predicted_winner] || m.predicted_winner);
  const predPct = m.predicted_winner === 'draw' ? m.draw_prob :
                  m.predicted_winner === m.home_team ? m.home_win_prob : m.away_win_prob;
  
  const verdictIcon = isExact ? '🎯' : (isHit ? '✅' : '❌');
  const verdictText = isExact ? '精确命中' : (isHit ? '胜方命中' : '未命中');
  
  const text = [
    `${verdictIcon} AI 预测证据 | ${m.match_id}`,
    `${homeCn} ${m.home_score} : ${m.away_score} ${awayCn}`,
    ``,
    `🤖 AI 预测: ${predCn} ${m.predicted_home_score}-${m.predicted_away_score} (胜率 ${predPct.toFixed(1)}%)`,
    `📊 实际结果: ${winnerCn} ${m.home_score}-${m.away_score}`,
    `✨ 命中判定: ${verdictText}`,
    ``,
    `🕐 ${m.match_date} ${m.match_time} · ${m.venue || ''}`,
    `🏆 WorldCup 2026 · AI Analytics Hub V2`,
    `🔗 ${window.location.origin}/`
  ].join('\n');
  
  try {
    await navigator.clipboard.writeText(text);
    toast('已复制到剪贴板', 'success', 2000);
  } catch (e) {
    // 降级
    const ta = document.createElement('textarea');
    ta.value = text;
    document.body.appendChild(ta);
    ta.select();
    try {
      document.execCommand('copy');
      toast('已复制到剪贴板（兼容模式）', 'success', 2000);
    } catch(_) {
      toast('复制失败，请手动复制', 'error', 3000);
      console.log(text);
    }
    document.body.removeChild(ta);
  }
}

// 分享比赛详情为图片（html2canvas）
async function shareMatchAsImage() {
  if (!CURRENT_MATCH) return;
  const btn = document.getElementById('matchModalShare');
  if (!window.html2canvas) {
    toast('html2canvas 还没加载完，请稍候再试', 'warning', 3000);
    return;
  }
  const origText = btn.innerHTML;
  btn.innerHTML = '<span>⏳</span><span>生成中...</span>';
  btn.disabled = true;
  
  try {
    // 临时克隆 modal-card，移除滚动条，给纯色背景
    const modal = document.getElementById('matchModal');
    const card = modal.querySelector('.match-modal-card');
    const body = document.getElementById('matchModalBody');
    body.style.maxHeight = 'none';
    body.style.overflow = 'visible';
    
    const canvas = await window.html2canvas(card, {
      backgroundColor: '#0a1428',
      scale: 2,
      logging: false,
      useCORS: true,
      allowTaint: true
    });
    
    // 触发下载
    const link = document.createElement('a');
    link.download = `prediction-evidence-${CURRENT_MATCH.match_id}-${CURRENT_MATCH.match_date}.png`;
    link.href = canvas.toDataURL('image/png');
    link.click();
    
    // 恢复
    body.style.maxHeight = '';
    body.style.overflow = '';
    btn.innerHTML = '<span>✓</span><span>已下载</span>';
    setTimeout(() => { btn.innerHTML = origText; btn.disabled = false; }, 1800);
  } catch (e) {
    console.error('share image failed', e);
    btn.innerHTML = '<span>❌</span><span>失败</span>';
    setTimeout(() => { btn.innerHTML = origText; btn.disabled = false; }, 2000);
  }
}

// ============================================================
// 翻车榜弹窗 (v1.2)
// ============================================================
async function showUpsetModal() {
  const modal = document.getElementById('matchModal');
  const body = document.getElementById('matchModalBody');
  const title = document.getElementById('matchModalTitle');
  if (!modal || !body) return;
  
  title.textContent = '🤯 AI 翻车榜';
  body.innerHTML = '<div class="skeleton" style="height:40px"></div><div class="skeleton" style="height:200px"></div>';
  modal.hidden = false;
  document.body.style.overflow = 'hidden';
  
  try {
    const data = await fetch('/api/matches?limit=500').then(r => r.json());
    const finished = data.filter(m => m.status === 'finished' 
      && m.predicted_winner && m.predicted_winner !== 'TBD'
      && m.predicted_home_score != null && m.predicted_away_score != null);
    
    // 计算翻车：AI 看好某队但实际胜者是另一队
    const upsets = [];
    for (const m of finished) {
      const actual = m.home_score > m.away_score ? m.home_team : (m.home_score < m.away_score ? m.away_team : 'draw');
      if (m.predicted_winner !== actual) {
        // AI 给出概率最高的队
        const probs = { [m.home_team]: m.home_win_prob, 'draw': m.draw_prob, [m.away_team]: m.away_win_prob };
        const maxTeam = Object.entries(probs).reduce((a, c) => c[1] > a[1] ? c : a);
        upsets.push({
          match_id: m.match_id,
          home_team: m.home_team, away_team: m.away_team,
          home_score: m.home_score, away_score: m.away_score,
          match_date: m.match_date, match_time: m.match_time,
          predicted: m.predicted_winner,
          predPct: maxTeam[1],
          actual: actual
        });
      }
    }
    // 按 AI 信心降序（最大翻车 = AI 信心最高但翻车）
    upsets.sort((a, b) => b.predPct - a.predPct);
    
    body.innerHTML = `
      <div class="modal-verdict miss">
        <span class="modal-verdict-icon">🤯</span>
        <span>AI 翻车 ${upsets.length} 场 · 信心越高翻车越尴尬</span>
      </div>
      ${upsets.length ? `
        <div class="upset-modal-list">
          ${upsets.slice(0, 15).map(u => {
            const predCn = TEAM_CN[u.predicted] || u.predicted;
            const actCn = TEAM_CN[u.actual] || u.actual;
            const homeCn = TEAM_CN[u.home_team] || u.home_team;
            const awayCn = TEAM_CN[u.away_team] || u.away_team;
            return `
              <div class="upset-modal-item">
                <div class="upset-modal-head">
                  <span class="hit-match-id">${u.match_id}</span>
                  <span class="hit-match-time">${u.match_date}</span>
                  <span class="upset-modal-pred">看好 ${predCn} <strong>${u.predPct.toFixed(0)}%</strong></span>
                </div>
                <div class="upset-modal-body">
                  <span>${homeCn} <strong>${u.home_score}-${u.away_score}</strong> ${awayCn}</span>
                  <span class="upset-modal-arrow">→</span>
                  <span class="upset-modal-act"><strong>${actCn}</strong> 胜</span>
                </div>
              </div>
            `;
          }).join('')}
        </div>
      ` : '<div class="dist-empty">暂无翻车场次 · AI 全部猜对 🎉</div>'}
    `;
  } catch (e) {
    body.innerHTML = `<div class="dist-empty" style="color:#ff8a9e">❌ 加载失败: ${e.message}</div>`;
  }
}

// ============================================================
// 启动
// ============================================================
document.getElementById('themeToggle')?.addEventListener('click', toggleTheme);
document.getElementById('langToggle')?.addEventListener('click', toggleLang);
load();
