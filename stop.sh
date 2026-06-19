#!/usr/bin/env bash
# ============================================================
# WorldCup 2026 Analytics Hub — V2 停止脚本
# 智能识别: systemd 服务 → systemctl stop; 临时实例 → kill PID
# ============================================================
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$SCRIPT_DIR/backend/logs/v2.pid"
PORT="${V2_PORT:-8001}"
SERVICE_NAME="wc2026-v2"

# 优先: systemd 服务
if systemctl is-active --quiet "$SERVICE_NAME" 2>/dev/null; then
  echo "🛑 检测到 systemd 服务运行中, 用 systemctl stop ..."
  if [ "$EUID" -ne 0 ]; then
    sudo systemctl stop "$SERVICE_NAME"
  else
    systemctl stop "$SERVICE_NAME"
  fi
  sleep 1
  if ! systemctl is-active --quiet "$SERVICE_NAME" 2>/dev/null; then
    echo "✅ V2 (systemd) 已停止"
    rm -f "$PID_FILE"
    exit 0
  fi
fi

# fallback: PID 文件
if [ -f "$PID_FILE" ]; then
  PID=$(cat "$PID_FILE")
  if kill -0 "$PID" 2>/dev/null; then
    echo "🛑 停止 V2 (PID=$PID) ..."
    kill "$PID"
    sleep 1
    if kill -0 "$PID" 2>/dev/null; then
      echo "   强制 kill ..."
      kill -9 "$PID" 2>/dev/null || true
    fi
    rm -f "$PID_FILE"
    echo "✅ V2 已停止"
    exit 0
  else
    echo "⚠️  PID 文件存在但进程已退出, 清理"
    rm -f "$PID_FILE"
  fi
fi

# 兜底: 按端口找
PID=$(lsof -ti tcp:$PORT 2>/dev/null || true)
if [ -n "$PID" ]; then
  echo "🛑 发现占用端口 $PORT 的进程 (PID=$PID) ..."
  kill "$PID" 2>/dev/null || true
  sleep 1
  kill -9 "$PID" 2>/dev/null || true
  echo "✅ V2 已停止"
else
  echo "ℹ️  V2 未在运行"
fi
