#!/usr/bin/env bash
# ============================================================
# WorldCup 2026 Analytics Hub — V2 状态检查
# 显示: systemd 服务状态 / 临时实例状态 / 健康检查 / 最近日志
# ============================================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$SCRIPT_DIR/backend/logs/v2.pid"
PORT="${V2_PORT:-8001}"
LOG_FILE="$SCRIPT_DIR/backend/logs/v2.log"
SERVICE_NAME="wc2026-v2"

echo "=== V2 状态 ==="

# systemd 服务
if systemctl list-unit-files "${SERVICE_NAME}.service" 2>/dev/null | grep -q "${SERVICE_NAME}.service"; then
  if systemctl is-active --quiet "$SERVICE_NAME" 2>/dev/null; then
    ACTIVE="✅ 运行中 (systemd)"
    SVC_PID=$(systemctl show -p MainPID --value "$SERVICE_NAME" 2>/dev/null)
    ENABLED="启用: $(systemctl is-enabled $SERVICE_NAME 2>/dev/null)"
  else
    ACTIVE="❌ systemd 服务未运行"
    ENABLED="启用: $(systemctl is-enabled $SERVICE_NAME 2>/dev/null)"
  fi
  echo "systemd: $SERVICE_NAME"
  echo "  状态:   $ACTIVE"
  echo "  $ENABLED"
  if [ -n "$SVC_PID" ] && [ "$SVC_PID" != "0" ]; then
    echo "  PID:    $SVC_PID"
  fi
fi

# 临时实例
if [ -f "$PID_FILE" ] && kill -0 "$(cat $PID_FILE)" 2>/dev/null; then
  PID=$(cat "$PID_FILE")
  echo "临时实例: 运行中 (PID=$PID)"
elif [ -f "$PID_FILE" ]; then
  echo "临时实例: PID 文件残留 ($(cat $PID_FILE) 已退出)"
fi

echo "端口:   $PORT"
echo "日志:   $LOG_FILE"
echo ""

# 健康检查
if curl -sf -m 3 "http://127.0.0.1:$PORT/api/health" >/dev/null 2>&1; then
  echo "健康:   ✅ 正常"
  curl -s -m 3 "http://127.0.0.1:$PORT/api/health" | python3 -m json.tool 2>/dev/null | sed 's/^/         /'
else
  echo "健康:   ❌ 无响应"
fi

echo ""
echo "=== 最近 10 行日志 ==="
if [ -f "$LOG_FILE" ]; then
  tail -10 "$LOG_FILE"
else
  echo "(无日志)"
fi
