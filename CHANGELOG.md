# 📝 Changelog

所有 V2 项目的版本变更记录。格式基于 [Keep a Changelog](https://keepachangelog.com/)。

> 💡 **完整 release notes** 在 [`RELEASE_NOTES/`](./RELEASE_NOTES/) 目录。
> 🌐 **GitHub Releases** 见 https://github.com/PerfectZQ888/FIFA-WorldCup-2026-V2/releases

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
