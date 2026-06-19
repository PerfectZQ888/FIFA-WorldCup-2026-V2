# ⚽ 世界杯 2026 · 数据分析中心 (V2 独立版)

> 2026 美加墨世界杯 · 48 强 · 104 场 · 实时数据 + AI 冠军预测 + 预测准确率仪表盘

![python](https://img.shields.io/badge/python-3.11%2B-blue) ![fastapi](https://img.shields.io/badge/fastapi-0.115-green) ![port](https://img.shields.io/badge/port-8001-orange)

V2 是 V1 (`/data/FIFA_WorldCup_2026/`) 的**完全独立**优化版, 共享同一份数据血缘但**目录、端口、日志、配置全隔离**。

## 🌐 跨平台支持 (Linux / macOS / Windows)

V2 已全面跨平台适配，**Web 应用本体在任何 OS 都能跑**，部署脚本按系统分别提供：

| OS | 临时启动 | 开机自启 |
|---|---|---|
| **Linux** (systemd) | `./start.sh` | `sudo ./install-service.sh` |
| **macOS** (launchd) | `./start.sh` | `./install-service-macos.sh` |
| **Windows** | `start.bat` 或 `start.ps1` | Task Scheduler (见 DEPLOY.md) |

**Python 代码 100% 跨平台** — 用了 `pathlib.Path`、无 `subprocess`、无硬编码路径。
**前端 100% 跨平台** — 纯 HTML/CSS/JS、无 `navigator.platform` 检测。

### Windows 特别注意
- 用 `start.bat` 或 `start.ps1`（bash 脚本跑不了）
- 依赖装 `requirements-windows.txt`（去掉 `uvloop`，因为它不支持 Windows）
- 开机自启用 Task Scheduler（详细步骤见 DEPLOY.md）

### macOS 特别注意
- macOS 默认 bash 3.2 也能跑 `./start.sh`（专门做了兼容）
- 系统 Python 可能在 `/opt/homebrew/bin/python3`，需要 `brew install python@3.11`

## 🚀 两种部署方式


### A) 临时启动 (开发/调试)

```bash
cd /data/FIFA_WorldCup_2026_V2
./start.sh     # 一键启动 (端口 8001), 终端关闭则停
```

### B) 开机自启 (生产/服务化) ✨ 推荐

跟 V1 (`wc2026.service`, 端口 8000) 同款 systemd 自启:

```bash
cd /data/FIFA_WorldCup_2026_V2
sudo ./install-service.sh
```

启动后:

- ✅ 开机自启
- ✅ 进程挂了自动重启 (RestartSec=5)
- ✅ 日志统一写到 `backend/logs/v2.log`
- ✅ 完全独立于 V1, 互不影响

常用命令:

```bash
sudo systemctl status wc2026-v2    # 状态
sudo systemctl start  wc2026-v2    # 启动
sudo systemctl stop   wc2026-v2    # 停止
sudo systemctl restart wc2026-v2   # 重启
sudo journalctl -u wc2026-v2 -f    # 实时日志

# 卸载
sudo ./uninstall-service.sh
```

启动后访问:
- 🏠 主页: **http://localhost:8001/**
- 📊 准确率仪表盘: **http://localhost:8001/#accuracy**
- 📖 API 文档: **http://localhost:8001/docs**
- 🩺 健康检查: **http://localhost:8001/api/health**

## 🆚 V1 vs V2 关键差异

| 项 | V1 | V2 |
|---|---|---|
| 目录 | `/data/FIFA_WorldCup_2026/` | `/data/FIFA_WorldCup_2026_V2/` |
| 端口 | 8000 | **8001** |
| 前端 | 单文件 72 KB (CSS/JS 内联) | **拆分 5 文件 + 性能优化** (v1.2 优化版) |
| ECharts | 每次重渲染 init() → **内存泄漏** | `ChartManager` 单例 + 单一 resize |
| 预测校准 | ❌ | ✅ 前端概率校准 (Brier -6.6%) |
| 准确率仪表盘 | ❌ | ✅ 4 KPI + 走势 + 校准散点 + 冷门榜 |
| 校准状态持久化 | ❌ | ✅ localStorage 记忆 |
| 自动刷新仪表盘 | ❌ | ✅ 完赛即刷新 |
| 回到顶部按钮 | ❌ | ✅ 滚动浮现 |
| 键盘日期导航 | ❌ | ✅ ←/→ 切换 |
| 错误重试 | ❌ | ✅ err-state + global-error 横幅 |

**V1 始终在 8000 端口可用**, V2 在 8001 端口, **两者互不影响**。

## 📦 项目结构

```
FIFA_WorldCup_2026_V2/
├── start.sh / stop.sh / status.sh    # 运维三件套
├── README.md / DEPLOY.md             # 文档
├── preview.png                       # UI 预览
└── backend/                          # 完全独立的后端
    ├── app.py                        # FastAPI 入口
    ├── analyzer.py                   # 蒙特卡洛预测
    ├── seed.py                       # 种子数据
    ├── requirements.txt
    ├── data/                         # 独立数据 (wc2026.db)
    ├── scrapers/                     # 实时数据抓取
    ├── static/                       # v1.2 优化版前端
    │   ├── index.html
    │   ├── style.css                 # 36 KB (从 29 KB 内联优化)
    │   ├── app.js                    # 主应用 (含 ChartManager)
    │   ├── accuracy.js               # 准确率仪表盘模块
    │   └── calibration.js            # 概率校准模块
    └── logs/                         # V2 独立日志
```

## ✨ v1.2 前端特性 (本次新增)

1. **TEAM_CN_MAP 时序 bug 修复** — 冷门榜球队名从英文回退修复
2. **校准开关持久化** — `localStorage` 记住用户偏好
3. **准确率仪表盘自动刷新** — 30s 检测完赛变化
4. **回到顶部浮动按钮** — 滚动 > 480px 浮现
5. **赛程日期键盘导航** — ←/→ 切换、Enter/Space 选中
6. **错误状态加重试** — 直播/射手榜失败显示重试卡片
7. **顶部错误横幅** — 整页加载失败时显示
8. **代码去重** — `getActualWinner` 合并

## 🛠 常用命令

### 临时实例 (./start.sh 方式)

```bash
./start.sh                       # 启动
./status.sh                      # 状态 + 健康检查 + 最近日志
./stop.sh                        # 停止
tail -f backend/logs/v2.log      # 实时日志
V2_PORT=9001 ./start.sh          # 自定义端口
```

### macOS launchd 服务 (./install-service-macos.sh 后)
```bash
launchctl list | grep wc2026-v2    # 状态
launchctl start  com.wc2026-v2     # 启动
launchctl stop   com.wc2026-v2     # 停止
launchctl unload ~/Library/LaunchAgents/com.wc2026-v2.plist   # 卸载
tail -f backend/logs/v2.log        # 实时日志
```

### Windows (手动开 cmd)
```cmd
start.bat                          # 启动
stop.bat                           # 停止
status.bat                         # 状态
```
或 PowerShell (推荐, 彩色输出)：
```powershell
powershell -ExecutionPolicy Bypass -File .\start.ps1
powershell -ExecutionPolicy Bypass -File .\stop.ps1
powershell -ExecutionPolicy Bypass -File .\status.ps1
```

### systemd 服务 (sudo ./install-service.sh 后)

```bash
sudo systemctl status wc2026-v2  # 状态 (含最近 10 行日志)
sudo systemctl start  wc2026-v2  # 启动
sudo systemctl stop   wc2026-v2  # 停止
sudo systemctl restart wc2026-v2 # 重启
sudo journalctl -u wc2026-v2 -f  # systemd 日志 (与 v2.log 是同一份)
sudo ./uninstall-service.sh      # 完全卸载
```

## 📝 详细文档

- 📖 [DEPLOY.md](./DEPLOY.md) — 完整部署指南、故障排查、API 验证
- 📜 [v1.2 增量详情](./DEPLOY.md#v12-2026-06-18--体验与稳定性补丁)
- 🔄 [V1 → V2 数据迁移](./DEPLOY.md#v1--v2-数据迁移)

## 📊 核心 API

| Endpoint | 用途 |
|---|---|
| `GET /api/health` | 健康检查 (`version: "v2"`) |
| `GET /api/summary` | 顶部 KPI 摘要 |
| `GET /api/standings` | 12 组积分榜 |
| `GET /api/matches` | 全部比赛 (支持 group/status/date 过滤) |
| `GET /api/matches/live` | 直播 + 24h 内 |
| `GET /api/predictions` | 48 队冠军预测 (蒙特卡洛 5000 次) |
| `GET /api/scorers` | 完整射手榜 |
| `GET /api/history` | 22 届世界杯历史 |
| `GET /api/knockout` | 32 场淘汰赛 |
| `GET /api/bracket` | 完整对阵图 (v4) |

## 📝 版本

- **V2 后端** (2026-06-18) — 独立工程化、独立端口 8001、独立数据
  - ⚙️ **systemd 自启**: `wc2026-v2.service` + `install-service.sh` 一键安装, 跟 V1 (`wc2026.service`) 同款平行运行
  - 🛠 **运维三件套**: `start.sh` / `stop.sh` / `status.sh` 智能识别 systemd vs 临时实例
- **v1.2 前端** (2026-06-18) — 体验与稳定性补丁
- **v1.1 前端** (2026-06-18) — 性能 + 准确率仪表盘
- **v1.0** — FastAPI + ECharts 原版
