# 部署指南 - 2026 世界杯分析中心 V2 (独立版)

## 📦 项目结构

```
FIFA_WorldCup_2026_V2/
├── start.sh                # 临时启动 (端口 8001)
├── stop.sh                 # 停止
├── status.sh               # 状态检查 (智能识别 systemd)
├── install-service.sh      # 安装为 systemd 自启服务 (sudo)
├── uninstall-service.sh    # 卸载 systemd 服务 (sudo)
├── README.md               # 项目说明
├── DEPLOY.md               # 本文档
├── preview.png             # UI 预览图 (v1.2 优化版)
├── .gitignore
└── backend/                # 后端 (独立、与 V1 完全隔离)
    ├── app.py              # FastAPI 入口 (端口 8001)
    ├── analyzer.py         # 蒙特卡洛 5000 次模拟
    ├── seed.py             # SQLite 种子数据
    ├── requirements.txt    # Python 依赖
    ├── data/
    │   ├── tournament_data.py  # 48 球队/104 比赛/22 历届
    │   └── wc2026.db           # SQLite 数据库 (运行时)
    ├── scrapers/           # 实时数据抓取
    │   ├── cctv_espn_live.py
    │   ├── cctv_scorers.py
    │   ├── openfootball_live.py
    │   └── team_name_map.py
    ├── static/             # v1.2 优化版前端 (5 文件拆分)
    │   ├── index.html
    │   ├── style.css       (1.1 MB → 36 KB 外链)
    │   ├── app.js
    │   ├── accuracy.js     (v1.1 新增)
    │   ├── calibration.js  (v1.1 新增)
    │   └── trophy.jpeg
    └── logs/               # V2 独立日志
        ├── v2.log
        └── v2.pid
```

## 🆚 V1 vs V2 对比

| 项 | V1 (FIFA_WorldCup_2026) | V2 (FIFA_WorldCup_2026_V2) |
|---|---|---|
| 路径 | `/data/FIFA_WorldCup_2026/` | `/data/FIFA_WorldCup_2026_V2/` |
| 端口 | **8000** | **8001** |
| 前端 | 单文件 `static/index.html` (72 KB) | 拆分 5 文件 + ECharts 内存修复 + 准确率仪表盘 |
| 数据 | V1 自己的 `data/wc2026.db` | V2 自己的 `backend/data/wc2026.db` |
| 日志 | `V1/logs/` | `V2/backend/logs/` |
| 同时运行 | ✅ 完全独立, 不冲突 |

**V1 完全不动**, V2 是一份完全独立的工程。可以同时跑 `http://host:8000/` (V1) 和 `http://host:8001/` (V2)。

## ⚙️ systemd 部署 (生产推荐, 跟 V1 同款)

V1 用的就是 systemd (`/etc/systemd/system/wc2026.service`), V2 同样用, 平行运行。

### 一键安装

```bash
cd /data/FIFA_WorldCup_2026_V2
sudo ./install-service.sh
```

脚本会自动:
1. 📋 复制 `backend/wc2026-v2.service` → `/etc/systemd/system/`
2. 🔄 `systemctl daemon-reload`
3. 🚀 `systemctl enable --now wc2026-v2` (启用 + 启动)
4. 🩺 健康检查 `/api/health`

### 装好后管理

```bash
sudo systemctl status wc2026-v2    # 状态
sudo systemctl start  wc2026-v2    # 启动
sudo systemctl stop   wc2026-v2    # 停止
sudo systemctl restart wc2026-v2   # 重启
sudo systemctl disable wc2026-v2   # 禁用开机自启 (不卸载)
sudo journalctl -u wc2026-v2 -f    # 实时日志
```

### 卸载

```bash
sudo ./uninstall-service.sh
# 1) 停服务 + 禁用开机自启
# 2) 删除 /etc/systemd/system/wc2026-v2.service
# 3) daemon-reload
# V1 服务 (wc2026, 端口 8000) 不受影响
```

### V1 + V2 systemd 服务对比

| | V1 | V2 |
|---|---|---|
| Service 文件 | `/etc/systemd/system/wc2026.service` | `/etc/systemd/system/wc2026-v2.service` |
| 监听端口 | 8000 | **8001** |
| 工作目录 | `/data/FIFA_WorldCup_2026` | `/data/FIFA_WorldCup_2026_V2/backend` |
| 数据库 | `V1/data/wc2026.db` | `V2/backend/data/wc2026.db` |
| 日志 | `V1/logs/app.log` | `V2/backend/logs/v2.log` |
| Restart | `always`, `RestartSec=5` | `always`, `RestartSec=5` |
| Workers | 1 | 1 |

两个服务**完全独立**, 同时启用不会冲突。

### service 文件关键配置 (`backend/wc2026-v2.service`)

```ini
[Service]
Type=simple
User=root
WorkingDirectory=/data/FIFA_WorldCup_2026_V2/backend
Environment="PYTHONUNBUFFERED=1"
Environment="PYTHONPATH=/data/FIFA_WorldCup_2026_V2/backend"
ExecStart=/usr/bin/python3 -m uvicorn app:app --host 0.0.0.0 --port 8001 --workers 1
Restart=always
RestartSec=5
StartLimitBurst=10
StartLimitIntervalSec=60
StandardOutput=append:/data/FIFA_WorldCup_2026_V2/backend/logs/v2.log
StandardError=append:/data/FIFA_WorldCup_2026_V2/backend/logs/v2.log

# 安全加固
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=full
ProtectHome=true
ReadWritePaths=/data/FIFA_WorldCup_2026_V2/backend/data /data/FIFA_WorldCup_2026_V2/backend/logs
```

---

## 🚀 临时启动 (开发/调试, 无 systemd)

不装服务, 用 `./start.sh` 临时起, 终端关了就停:

```bash
cd /data/FIFA_WorldCup_2026_V2

# 1) 启动 (会自动安装依赖、初始化数据库、健康检查)
./start.sh

# 2) 查看状态
./status.sh

# 3) 停止
./stop.sh
```

启动成功后输出:

```
🚀 启动 V2 后端 (http://0.0.0.0:8001) ...
✅ V2 启动成功 (PID=12345)
   主页:    http://0.0.0.0:8001/
   准确率:  http://0.0.0.0:8001/#accuracy
   API:     http://0.0.0.0:8001/docs
   日志:    tail -f backend/logs/v2.log
   健康:    {"status":"ok","version":"v2",...}
```

## 🔧 自定义端口

```bash
V2_PORT=9001 ./start.sh     # 改用 9001
V2_PORT=9001 ./status.sh
V2_PORT=9001 ./stop.sh
```

## 🔁 部署更新 (升级 V2 前端)

```bash
# V2 前端是 v1.2 优化版, 升级只需替换 backend/static/ 下的文件
cp new_index.html backend/static/index.html
cp new_style.css  backend/static/style.css
cp new_app.js     backend/static/app.js
cp new_accuracy.js backend/static/accuracy.js
cp new_calibration.js backend/static/calibration.js

# 强制刷新浏览器: Ctrl+Shift+R
# (因为浏览器会缓存 CSS/JS, 改了可能没立刻生效)
```

## 📝 手动启动 (调试用)

```bash
cd /data/FIFA_WorldCup_2026_V2/backend
python3 -m uvicorn app:app --host 0.0.0.0 --port 8001 --reload
# 终端会实时显示日志, 改了代码自动重启
```

## 🐛 故障排查

### 端口被占用
```bash
# 1) 找出占用进程
lsof -i :8001
# 2) 若是旧 V2 实例
./stop.sh
# 3) 若是其他进程
kill <PID>
```

### 数据库为空
```bash
cd /data/FIFA_WorldCup_2026_V2/backend
python3 seed.py    # 重新种子化
```

### 依赖装不上
```bash
cd /data/FIFA_WorldCup_2026_V2/backend
pip install -r requirements.txt
```

### 想看实时日志
```bash
tail -f backend/logs/v2.log
```

### 想清空日志
```bash
> backend/logs/v2.log
```

## ✅ 已完成的优化 (V2 前端 = v1.1 + v1.2)

### v1.1 (2026-06-18) — 性能 + 准确率仪表盘
- 提取 CSS / JS 到外链, 修复 ECharts 内存泄漏
- 新增「预测准确率仪表盘」(4 KPI + 走势 + 校准散点 + 冷门榜)
- 新增前端概率校准开关 (Brier 0.629 → 0.588, -6.6%)
- 增强可访问性 + 移动端

### v1.2 (2026-06-18) — 体验与稳定性补丁
- 🐛 **关键 Bug 修复**：移除 `index.html` 末尾失效的 `TEAM_CN_MAP` 内联脚本
- ♻️ **代码去重**：`accuracy.js` 重复的 `getActualWinner`
- 💾 **校准开关持久化**：`localStorage` 保存开关和参数
- 🔄 **准确率仪表盘自动刷新**：每 30s 检测完赛数变化
- ⬆️ **回到顶部浮动按钮**：滚动 > 480px 浮现
- ⌨️ **赛程日期键盘可访问**：←/→ 切换、Enter/Space 选中
- 🚨 **错误状态加重试**：`.err-state` 卡片 + 顶部 `global-error` 横幅
- 🧹 **错误处理集中**：`renderError` / `showGlobalError` 辅助函数

## 🧪 API 验证

启动后, 在另一终端测试:

```bash
# 健康检查
curl http://127.0.0.1:8001/api/health
# {"status":"ok","version":"v2","now_utc":"...","last_data_update":"..."}

# 摘要
curl http://127.0.0.1:8001/api/summary | python3 -m json.tool | head -20

# 比赛列表
curl "http://127.0.0.1:8001/api/matches?limit=3" | python3 -m json.tool | head -30

# 预测榜
curl http://127.0.0.1:8001/api/predictions | python3 -m json.tool | head -20
```

## 🔄 V1 → V2 数据迁移

如果 V2 启动后想用最新的 V1 数据:

```bash
# 复制 V1 最新数据库 (覆盖 V2 初始库)
cp /data/FIFA_WorldCup_2026/data/wc2026.db \
   /data/FIFA_WorldCup_2026_V2/backend/data/wc2026.db

# 重启 V2 让它加载新数据
./stop.sh && ./start.sh
```

## 📝 版本日志

**V2 (2026-06-18) — 独立工程化**
- 📦 **完全独立**：与 V1 目录、端口、数据、日志全隔离
- 🚀 **一键启动**：`./start.sh` 自动装依赖 + 初始化库 + 健康检查
- ⚙️ **systemd 自启**：跟 V1 (`wc2026.service`) 同款, `wc2026-v2.service` + `install-service.sh` 一键安装
- 🩺 **健康检查**：`/api/health` 返回 `version: "v2"`, 便于区分
- 🛠 **运维脚本**：`start.sh` / `stop.sh` / `status.sh` 完整三件套 (智能识别 systemd vs 临时实例)
- 📖 **文档完整**：`README.md` + `DEPLOY.md` 双文档

**v1.2 (2026-06-18) — 体验与稳定性补丁**
（见上文 v1.2 详情）

**v1.1 (2026-06-18) — 性能 + 准确率仪表盘**
（见上文 v1.1 详情）

**v1.0 (原版)**
- FastAPI + ECharts 单页应用
- 4 因子加权 AI 预测 + 5000 次蒙特卡洛
- 22 场历史、积分榜、赛程、射手榜
