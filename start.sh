#!/usr/bin/env bash
# ============================================================
# WorldCup 2026 Analytics Hub — V2 启动脚本 (跨平台)
# 端口: 8001 (V1 用 8000)
# 智能识别:
#   - Linux systemd  → 提示用 systemctl
#   - macOS launchd   → 提示用 launchctl
#   - 临时启动        → nohup (Linux/macOS) / 单独 .bat (Windows)
# ============================================================
# 兼容性: bash 3.2+ (macOS 默认) / bash 4+ (Linux 现代)
# ============================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
PID_FILE="$BACKEND_DIR/logs/v2.pid"
LOG_FILE="$BACKEND_DIR/logs/v2.log"
PORT="${V2_PORT:-8001}"
HOST="${V2_HOST:-0.0.0.0}"
SERVICE_NAME="wc2026-v2"

mkdir -p "$BACKEND_DIR/logs"

# === OS 检测 ===
OS_TYPE="$(uname -s 2>/dev/null || echo Unknown)"
case "$OS_TYPE" in
  Linux*)   OS_NAME="Linux" ;;
  Darwin*)  OS_NAME="macOS" ;;
  FreeBSD*) OS_NAME="FreeBSD" ;;
  MINGW*|CYGWIN*|MSYS*) OS_NAME="Windows" ;;
  *)        OS_NAME="Unix" ;;
esac
echo "🖥️  检测到操作系统: $OS_NAME"

# === 服务管理检测 (systemd / launchd) ===
HAS_SYSTEMD=false
HAS_LAUNCHD=false
if [ "$OS_NAME" = "Linux" ] && command -v systemctl >/dev/null 2>&1; then
  HAS_SYSTEMD=true
fi
if [ "$OS_NAME" = "macOS" ] && command -v launchctl >/dev/null 2>&1; then
  HAS_LAUNCHD=true
fi

if [ "$HAS_SYSTEMD" = "true" ]; then
  if systemctl list-unit-files "${SERVICE_NAME}.service" 2>/dev/null | grep -q "${SERVICE_NAME}.service"; then
    echo "🔧 检测到 systemd 服务: $SERVICE_NAME"
    echo "   推荐用: sudo systemctl start $SERVICE_NAME"
    echo "   但本脚本仍可用 (用 nohup 启动临时实例)"
    echo ""
  fi
fi

if [ "$HAS_LAUNCHD" = "true" ]; then
  PLIST_DST="$HOME/Library/LaunchAgents/com.wc2026-v2.plist"
  if [ -f "$PLIST_DST" ]; then
    echo "🔧 检测到 launchd 服务: $SERVICE_NAME"
    echo "   推荐用: launchctl load -w $PLIST_DST"
    echo "   但本脚本仍可用 (用 nohup 启动临时实例)"
    echo ""
  fi
fi

if [ "$OS_NAME" = "Windows" ]; then
  echo "❌ Windows 上请使用 start.bat 或 start.ps1 启动"
  echo "   本 bash 脚本不适用于 Windows"
  exit 1
fi

# === 端口检查 (跨平台) ===
check_port() {
  local port=$1
  # 跨平台端口检查: lsof → ss → netstat → /dev/tcp → Python socket
  if command -v lsof >/dev/null 2>&1; then
    lsof -ti tcp:"$port" >/dev/null 2>&1
    return $?
  fi
  if command -v ss >/dev/null 2>&1; then
    ss -tln 2>/dev/null | grep -qE "[:.]${port}"
    return $?
  fi
  if command -v netstat >/dev/null 2>&1; then
    netstat -an 2>/dev/null | grep -qE "[.:]${port}.*LISTEN"
    return $?
  fi
  # /dev/tcp 是 bash 编译选项依赖, 不一定可用
  if (echo > "/dev/tcp/127.0.0.1/${port}") 2>/dev/null; then
    return 0
  else
    return 1
  fi
}


if check_port "$PORT"; then
  echo "❌ 端口 $PORT 已被占用"
  if [ -f "$PID_FILE" ]; then
    echo "   旧 V2 实例 PID: $(cat $PID_FILE)"
    echo "   停止: ./stop.sh"
  fi
  exit 1
fi

# === Python 检查 ===
PYTHON_BIN="python3"
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "❌ python3 不在 PATH 中"
  echo "   macOS: brew install python3   或   pyenv install 3.11+"
  echo "   Linux: sudo apt install python3   或   编译安装"
  exit 1
fi

# === Python 依赖 ===
if ! "$PYTHON_BIN" -c "import fastapi, uvicorn, apscheduler" 2>/dev/null; then
  echo "⚠️  Python 依赖未安装, 正在安装..."
  "$PYTHON_BIN" -m pip install -q -r "$BACKEND_DIR/requirements.txt"
fi

# === 数据库 ===
if [ ! -f "$BACKEND_DIR/data/wc2026.db" ]; then
  echo "⚠️  数据库不存在, 正在初始化..."
  (cd "$BACKEND_DIR" && "$PYTHON_BIN" seed.py)
fi

# === 启动 ===
echo "🚀 启动 V2 后端 (http://$HOST:$PORT) ..."
cd "$BACKEND_DIR"
nohup "$PYTHON_BIN" -m uvicorn app:app --host "$HOST" --port "$PORT" \
  > "$LOG_FILE" 2>&1 &
NEW_PID=$!
echo "$NEW_PID" > "$PID_FILE"

# === 健康检查 ===
sleep 2
if curl -sf -m 3 "http://127.0.0.1:$PORT/api/health" >/dev/null 2>&1; then
  HEALTH=$(curl -s -m 3 "http://127.0.0.1:$PORT/api/health" 2>/dev/null || echo "(健康检查失败)")
  echo "✅ V2 启动成功 (PID=$NEW_PID)"
  echo "   主页:    http://$HOST:$PORT/"
  echo "   准确率:  http://$HOST:$PORT/#accuracy"
  echo "   API:     http://$HOST:$PORT/docs"
  echo "   日志:    tail -f $LOG_FILE"
  echo "   健康:    $HEALTH"
  echo ""
  if [ "$OS_NAME" = "Linux" ] && [ "$HAS_SYSTEMD" = "true" ]; then
    echo "💡 想要开机自启? 运行: sudo ./install-service.sh"
  elif [ "$OS_NAME" = "macOS" ]; then
    echo "💡 想要开机自启? 运行: ./install-service-macos.sh"
  fi
else
  echo "❌ V2 启动失败, 查看日志: $LOG_FILE"
  tail -20 "$LOG_FILE" 2>/dev/null
  exit 1
fi
