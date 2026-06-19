#!/usr/bin/env bash
# ============================================================
# WorldCup 2026 Analytics Hub — V2 启动脚本
# 端口: 8001 (V1 用 8000)
# 智能识别: 如果已安装 systemd 服务, 用 systemctl; 否则用 nohup
# ============================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
PID_FILE="$BACKEND_DIR/logs/v2.pid"
LOG_FILE="$BACKEND_DIR/logs/v2.log"
PORT="${V2_PORT:-8001}"
HOST="${V2_HOST:-0.0.0.0}"
SERVICE_NAME="wc2026-v2"

mkdir -p "$BACKEND_DIR/logs"

# === 智能选择启动方式 ===
if systemctl list-unit-files "${SERVICE_NAME}.service" 2>/dev/null | grep -q "${SERVICE_NAME}.service"; then
  echo "🔧 检测到 systemd 服务: $SERVICE_NAME"
  echo "   推荐用: sudo systemctl start $SERVICE_NAME"
  echo "   但本脚本仍可用 (用 nohup 启动临时实例)"
  echo ""
fi

# 1) 检查端口
if (echo > /dev/tcp/127.0.0.1/$PORT) 2>/dev/null; then
  EXISTING_PID=$(lsof -ti tcp:$PORT 2>/dev/null || true)
  echo "❌ 端口 $PORT 已被占用 (PID=$EXISTING_PID)"
  if [ -f "$PID_FILE" ]; then
    echo "   旧 V2 实例 PID: $(cat $PID_FILE)"
    echo "   停止: ./stop.sh"
  fi
  exit 1
fi

# 2) Python 依赖
if ! python3 -c "import fastapi, uvicorn, apscheduler" 2>/dev/null; then
  echo "⚠️  Python 依赖未安装, 正在安装..."
  pip install -q -r "$BACKEND_DIR/requirements.txt"
fi

# 3) 数据库
if [ ! -f "$BACKEND_DIR/data/wc2026.db" ]; then
  echo "⚠️  数据库不存在, 正在初始化..."
  (cd "$BACKEND_DIR" && python3 seed.py)
fi

# 4) 启动
echo "🚀 启动 V2 后端 (http://$HOST:$PORT) ..."
cd "$BACKEND_DIR"
nohup python3 -m uvicorn app:app --host "$HOST" --port "$PORT" \
  > "$LOG_FILE" 2>&1 &
echo $! > "$PID_FILE"

# 5) 健康检查
sleep 2
if curl -sf -m 3 "http://127.0.0.1:$PORT/api/health" >/dev/null; then
  HEALTH=$(curl -s -m 3 "http://127.0.0.1:$PORT/api/health")
  echo "✅ V2 启动成功 (PID=$(cat $PID_FILE))"
  echo "   主页:    http://$HOST:$PORT/"
  echo "   准确率:  http://$HOST:$PORT/#accuracy"
  echo "   API:     http://$HOST:$PORT/docs"
  echo "   日志:    tail -f $LOG_FILE"
  echo "   健康:    $HEALTH"
  echo ""
  echo "💡 想要开机自启? 运行: sudo ./install-service.sh"
else
  echo "❌ V2 启动失败, 查看日志: $LOG_FILE"
  tail -20 "$LOG_FILE"
  exit 1
fi
