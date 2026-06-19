#!/usr/bin/env bash
# ============================================================
# WorldCup 2026 Analytics Hub — V2 状态检查 (跨平台)
# ============================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
PID_FILE="$BACKEND_DIR/logs/v2.pid"
SERVICE_NAME="wc2026-v2"
PORT="${V2_PORT:-8001}"

OS_TYPE="$(uname -s 2>/dev/null || echo Unknown)"
case "$OS_TYPE" in
  Linux*)   OS_NAME="Linux" ;;
  Darwin*)  OS_NAME="macOS" ;;
  *)        OS_NAME="Other" ;;
esac

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  WorldCup 2026 V2 状态"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  操作系统:    $OS_NAME"
echo "  端口:        $PORT"
echo ""

# === systemd (Linux) ===
if [ "$OS_NAME" = "Linux" ] && command -v systemctl >/dev/null 2>&1; then
  if systemctl list-unit-files "${SERVICE_NAME}.service" 2>/dev/null | grep -q "${SERVICE_NAME}.service"; then
    if systemctl is-active --quiet "$SERVICE_NAME" 2>/dev/null; then
      SVC_PID=$(systemctl show -p MainPID --value "$SERVICE_NAME" 2>/dev/null)
      ENABLED=$(systemctl is-enabled "$SERVICE_NAME" 2>/dev/null)
      echo "  [systemd 服务]"
      echo "    状态:    🟢 运行中"
      echo "    PID:     $SVC_PID"
      echo "    自启:    $ENABLED"
      echo ""
    else
      echo "  [systemd 服务]"
      echo "    状态:    🔴 已停止"
      echo ""
    fi
  fi
fi

# === launchd (macOS) ===
if [ "$OS_NAME" = "macOS" ] && command -v launchctl >/dev/null 2>&1; then
  PLIST_LABEL="com.wc2026-v2"
  if launchctl list 2>/dev/null | grep -q "$PLIST_LABEL"; then
    PID_LINE=$(launchctl list 2>/dev/null | grep "$PLIST_LABEL")
    PID=$(echo "$PID_LINE" | awk '{print $1}')
    echo "  [launchd 服务]"
    if [ "$PID" != "-" ] && [ -n "$PID" ]; then
      echo "    状态:    🟢 运行中 (PID=$PID)"
    else
      echo "    状态:    🔴 已停止"
    fi
    echo ""
  fi
fi

# === 临时实例 (PID 文件) ===
if [ -f "$PID_FILE" ]; then
  PID=$(cat "$PID_FILE")
  if kill -0 "$PID" 2>/dev/null; then
    echo "  [临时实例 / nohup]"
    echo "    状态:    🟢 运行中"
    echo "    PID:     $PID"
    echo "    日志:    $BACKEND_DIR/logs/v2.log"
    echo ""
  fi
fi

# === HTTP 健康检查 ===
HEALTH_URL="http://127.0.0.1:$PORT/api/health"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -m 3 "$HEALTH_URL" 2>/dev/null || echo "000")
if [ "$HTTP_CODE" = "200" ]; then
  HEALTH=$(curl -s -m 3 "$HEALTH_URL" 2>/dev/null)
  echo "  [HTTP 健康检查]"
  echo "    端点:    $HEALTH_URL"
  echo "    状态:    🟢 HTTP 200"
  echo "    响应:    $HEALTH"
  echo ""
  echo "  访问地址:"
  echo "    主页:    http://localhost:$PORT/"
  echo "    准确率:  http://localhost:$PORT/#accuracy"
  echo "    API 文档: http://localhost:$PORT/docs"
elif [ "$HTTP_CODE" = "000" ]; then
  echo "  [HTTP 健康检查]"
  echo "    端点:    $HEALTH_URL"
  echo "    状态:    ⚪ 无响应 (服务可能未启动)"
else
  echo "  [HTTP 健康检查]"
  echo "    端点:    $HEALTH_URL"
  echo "    状态:    🟡 HTTP $HTTP_CODE (服务异常)"
fi
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
