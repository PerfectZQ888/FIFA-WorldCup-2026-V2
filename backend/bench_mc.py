#!/usr/bin/env python3
"""
蒙特卡洛性能基准 (regression test)

对比 monte_carlo (原) vs monte_carlo_vec (新) 的耗时, 以及统计等价性.

用法:
  cd backend && python3 bench_mc.py [n_sim]
  
退出码:
  0 = 通过
  1 = 统计差异超阈值 (5%)  ← 这通常意味着代码有 bug
"""
import sys, time, json, hashlib
import sqlite3

sys.path.insert(0, '.')
import analyzer


def _fingerprint(counts: dict) -> str:
    sig = json.dumps({k: v for k, v in sorted(counts.items())}, sort_keys=True)
    return hashlib.md5(sig.encode()).hexdigest()[:12]


def main() -> int:
    n_sim = int(sys.argv[1]) if len(sys.argv) > 1 else 5000

    db = sqlite3.connect("data/wc2026.db")
    teams = analyzer.load_teams(db)
    db.close()
    print(f"加载 {len(teams)} 队, n_sim={n_sim}")
    print()

    results = {}
    for name, fn in [
        ("py (原)", analyzer.monte_carlo),
        ("vec (新)", analyzer.monte_carlo_vec),
    ]:
        # Warm up
        _ = fn(teams, n=50)
        # Timed run
        t0 = time.perf_counter()
        counts = fn(teams, n=n_sim)
        elapsed = time.perf_counter() - t0
        top5 = sorted(counts.items(), key=lambda x: -x[1]["champion"])[:5]
        print(f"[{name}] {elapsed*1000:6.1f}ms  ({n_sim/elapsed:>5.0f} iter/s)")
        for tn, c in top5:
            print(f"   {tn:25s}  冠军 {c['champion']/n_sim*100:5.2f}%  "
                  f"SF {c['sf']/n_sim*100:5.2f}%  QF {c['qf']/n_sim*100:5.2f}%  "
                  f"R16 {c['r16']/n_sim*100:5.2f}%")
        print(f"   fingerprint: {_fingerprint(counts)}")
        print()
        results[name] = {
            "elapsed_ms": elapsed * 1000,
            "iter_per_sec": n_sim / elapsed,
            "fingerprint": _fingerprint(counts),
            "top5": [(n, c["champion"]/n_sim*100, c["sf"]/n_sim*100,
                      c["qf"]/n_sim*100, c["r16"]/n_sim*100) for n, c in top5],
        }

    # 对比
    py_t = results["py (原)"]["elapsed_ms"]
    vec_t = results["vec (新)"]["elapsed_ms"]
    speedup = py_t / vec_t
    print(f"{'='*60}")
    print(f"⚡ 加速: {speedup:.2f}x  ({py_t:.0f}ms → {vec_t:.0f}ms)")

    # 统计差异检查 (Top 5 冠军概率)
    py_top = {n: c for n, c, _, _, _ in results["py (原)"]["top5"]}
    vec_top = {n: c for n, c, _, _, _ in results["vec (新)"]["top5"]}
    max_diff = 0.0
    for n in py_top:
        if n in vec_top:
            diff = abs(py_top[n] - vec_top[n])
            max_diff = max(max_diff, diff)
            marker = " ⚠️" if diff > 5.0 else ""
            print(f"   {n:25s}  冠军差异: {diff:5.2f}%{marker}")
    print()
    if max_diff > 5.0:
        print(f"❌ FAIL: 最大统计差异 {max_diff:.2f}% 超阈值 5%")
        return 1
    if speedup < 1.2:
        print(f"⚠️  WARN: 加速仅 {speedup:.2f}x (期望 ≥ 1.2x), 优化效果不显著")
    print(f"✅ PASS: 加速 {speedup:.2f}x, 统计差异 {max_diff:.2f}% ≤ 5%")
    return 0


if __name__ == "__main__":
    sys.exit(main())
