#!/usr/bin/env bash
# ============================================================
# WorldCup 2026 Analytics Hub — V2 停止脚本 (跨平台)
# ============================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
PID_FILE="$BACKEND_DIR/logs/v2.pid"
SERVICE_NAME="wc2026-v2"

# === OS / 服务检测 ===
OS_TYPE="$(uname -s 2>/dev/null || echo Unknown)"
case "$OS_TYPE" in
  Linux*)   OS_NAME="Linux" ;;
  Darwin*)  OS_NAME="macOS" ;;
  *)        OS_NAME="Other" ;;
esac
HAS_SYSTEMD=false
HAS_LAUNCHD=false
if [ "$OS_NAME" = "Linux" ] && command -v systemctl >/dev/null 2>&1; then
  HAS_SYSTEMD=true
fi
if [ "$OS_NAME" = "macOS" ] && command -v launchctl >/dev/null 2>&1; then
  HAS_LAUNCHD=true
fi

# 1) 优先 systemd (Linux)
if [ "$HAS_SYSTEMD" = "true" ] && systemctl is-active --quiet "$SERVICE_NAME" 2>/dev/null; then
  echo "🛑 检测到 systemd 服务运行中, 用 systemctl stop ..."
  if [ "$(id -u)" -ne 0 ]; then
    sudo systemctl stop "$SERVICE_NAME"
  else
    systemctl stop "$SERVICE_NAME"
  fi
  if ! systemctl is-active --quiet "$SERVICE_NAME" 2>/dev/null; then
    echo "✅ systemd 服务已停止"
    exit 0
  fi
fi

# 2) 再试 launchd (macOS)
if [ "$HAS_LAUNCHD" = "true" ]; then
  PLIST_LABEL="com.wc2026-v2"
  if launchctl list 2>/dev/null | grep -q "$PLIST_LABEL"; then
    echo "🛑 检测到 launchd 服务运行中, 用 launchctl unload ..."
    PLIST_SRC="$HOME/Library/LaunchAgents/${PLIST_LABEL}.plist"
    [ -f "$PLIST_SRC" ] || PLIST_SRC="/Library/LaunchDaemons/${PLIST_LABEL}.plist"
    if [ -f "$PLIST_SRC" ]; then
      launchctl unload -w "$PLIST_SRC" 2>/dev/null && echo "✅ launchd 服务已停止" && exit 0
    fi
    launchctl remove "$PLIST_LABEL" 2>/dev/null && echo "✅ launchd 服务已移除" && exit 0
  fi
fi

# 3) 临时实例: 用 PID 文件
if [ -f "$PID_FILE" ]; then
  PID=$(cat "$PID_FILE")
  if kill -0 "$PID" 2>/dev/null; then
    echo "🛑 停止临时 V2 实例 (PID=$PID) ..."
    kill "$PID" 2>/dev/null || true
    sleep 1
    if kill -0 "$PID" 2>/dev/null; then
      kill -9 "$PID" 2>/dev/null || true
    fi
    rm -f "$PID_FILE"
    echo "✅ 临时 V2 实例已停止"
    exit 0
  else
    echo "⚠️  PID 文件存在但进程不在运行, 清理 PID 文件"
    rm -f "$PID_FILE"
  fi
fi

# 4) 最后: 用 lsof/ss/netstat 找占用端口的进程
PORT="${V2_PORT:-8001}"
found_pid=""
if command -v lsof >/dev/null 2>&1; then
  found_pid=$(lsof -ti tcp:"$PORT" 2>/dev/null || true)
elif command -v ss >/dev/null 2>&1; then
  # ss 没有直接 "by port" 的 PID 输出, 用 fuser
  found_pid=$(fuser "$PORT/tcp" 2>/dev/null | tr -d ' ' || true)
elif command -v fuser >/dev/null 2>&1; then
  found_pid=$(fuser "$PORT/tcp" 2>/dev/null | tr -d ' ' || true)
elif command -v netstat >/dev/null 2>&1 && command -v grep >/dev/null 2>&1; then
  # netstat + ps (Linux ps 风格)
  found_pid=$(netstat -tlnp 2>/dev/null | grep ":$PORT " | awk '{print $7}' | cut -d/ -f1 | head -1)
fi

if [ -n "$found_pid" ] && [ "$found_pid" != "-" ]; then
  echo "🛑 发现占用端口 $PORT 的进程 (PID=$found_pid), 杀掉 ..."
  kill "$found_pid" 2>/dev/null || true
  sleep 1
  kill -9 "$found_pid" 2>/dev/null || true
  echo "✅ 已停止"
else
  echo "ℹ️  没有 V2 实例在运行 (端口 $PORT 空闲)"
fi
