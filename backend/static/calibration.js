/* ============================================================
   前端概率校准模块 (v1.1 → v1.2)
   - 校准原理: 提升平局概率，缩小主客胜差距
   - 启发自历史数据: 实际平局率 37.5% vs 模型预测 17%
   - 校准策略: p_home*0.95, p_draw+=8pp, p_away*0.95, 归一化
   - 仅影响显示，不修改后端
   - v1.2: 状态持久化到 localStorage，便于调试的参数可保存
   ============================================================ */

'use strict';

window.Calibration = (() => {
  // 校准参数 (网格搜索最优: 24 场样本)
  // Brier 0.6293 → 0.5876, 胜平负 62.5% → 62.5% (保持)
  // 可在控制台 calibTune({...}) 动态调整（v1.2: 同步持久化）
  const DEFAULT_PARAMS = {
    homeScale: 0.95,    // 主胜概率缩放
    awayScale: 0.95,    // 客胜概率缩放
    drawBoost: 8,       // 平局概率绝对加成 (pp)
    scoreDrawBoost: 0.5 // 预测比分接近时向 1-1 微调（保留位）
  };

  const LS_KEY_ENABLED = 'wc2026.calib.enabled';
  const LS_KEY_PARAMS  = 'wc2026.calib.params';

  // 加载持久化的参数和开关状态
  function loadPersisted() {
    let savedParams = null;
    try {
      const raw = localStorage.getItem(LS_KEY_PARAMS);
      if (raw) savedParams = JSON.parse(raw);
    } catch (e) { /* ignore */ }
    let savedEnabled = null;
    try {
      savedEnabled = localStorage.getItem(LS_KEY_ENABLED);
      if (savedEnabled != null) savedEnabled = savedEnabled === '1';
    } catch (e) { /* ignore */ }
    return {
      params: savedParams && typeof savedParams === 'object' ? savedParams : { ...DEFAULT_PARAMS },
      enabled: savedEnabled != null ? savedEnabled : false
    };
  }

  const initial = loadPersisted();
  const params = initial.params;
  let enabled = initial.enabled;

  function isEnabled() { return enabled; }

  function persistEnabled() {
    try { localStorage.setItem(LS_KEY_ENABLED, enabled ? '1' : '0'); } catch (e) { /* ignore */ }
  }
  function persistParams() {
    try { localStorage.setItem(LS_KEY_PARAMS, JSON.stringify(params)); } catch (e) { /* ignore */ }
  }

  function setEnabled(v, { silent = false } = {}) {
    const wasEnabled = enabled;
    enabled = !!v;
    if (wasEnabled !== enabled) persistEnabled();
    if (!silent) updateToggleUI();
  }

  function toggle() { setEnabled(!enabled); }

  // 校准三路概率 (主/平/客)，返回归一化后的百分比
  function calibrate(homePct, drawPct, awayPct) {
    if (!enabled) return { home: homePct, draw: drawPct, away: awayPct };
    let h = homePct * params.homeScale;
    let a = awayPct * params.awayScale;
    let d = drawPct + params.drawBoost;
    const total = h + d + a;
    if (total > 0) {
      h = h / total * 100;
      d = d / total * 100;
      a = a / total * 100;
    }
    return { home: h, draw: d, away: a };
  }

  // 校准预测比分（向平局微调）
  function calibrateScore(predH, predA) {
    if (!enabled) return { home: predH, away: predA };
    const diff = Math.abs(predH - predA);
    if (diff <= 1) return { home: 1, away: 1 };
    return { home: predH, away: predA };
  }

  // 更新顶部切换按钮 UI
  function updateToggleUI() {
    const btn = document.getElementById('calibToggle');
    if (!btn) return;
    btn.classList.toggle('active', enabled);
    const textEl = btn.querySelector('.text');
    if (textEl) textEl.textContent = enabled ? '已启用校准' : '原始概率';
    btn.setAttribute('aria-pressed', enabled ? 'true' : 'false');
  }

  // 触发所有依赖校准状态的渲染
  function reRenderAll() {
    if (typeof window.renderLive === 'function') window.renderLive();
  }

  // 注入切换按钮到预测榜头部
  function injectToggle() {
    const head = document.getElementById('predTag');
    if (!head) return;
    if (document.getElementById('calibToggle')) return;

    const btn = document.createElement('button');
    btn.id = 'calibToggle';
    btn.type = 'button';
    btn.className = 'calib-toggle';
    btn.setAttribute('aria-pressed', enabled ? 'true' : 'false');
    btn.setAttribute('aria-label', '切换前端概率校准');
    btn.innerHTML = '<span class="dot"></span><span class="text">原始概率</span>';
    btn.title = '前端概率校准：提升平局概率以匹配实际数据分布 (v1.2 状态已保存)';
    btn.addEventListener('click', () => {
      toggle();
      reRenderAll();
    });
    head.parentElement.appendChild(btn);
    updateToggleUI();
  }

  // 初始化
  function init() {
    injectToggle();
    updateToggleUI();
  }

  // 暴露给控制台调试（v1.2: 自动持久化）
  window.calibTune = (newParams) => {
    Object.assign(params, newParams);
    persistParams();
    console.log('校准参数已更新并保存:', params);
    reRenderAll();
  };

  // 暴露默认参数（用于 UI 复位）
  window.calibReset = () => {
    Object.assign(params, DEFAULT_PARAMS);
    persistParams();
    console.log('校准参数已恢复默认:', params);
    reRenderAll();
  };

  return {
    init, isEnabled, setEnabled, toggle,
    calibrate, calibrateScore,
    getParams: () => ({ ...params })
  };
})();

// 在脚本末尾调用
// defer 脚本在 DOM 解析完成后才执行，可直接调用
if (document.readyState !== 'loading') {
  if (window.Calibration) window.Calibration.init();
} else {
  document.addEventListener('DOMContentLoaded', () => window.Calibration.init());
}
