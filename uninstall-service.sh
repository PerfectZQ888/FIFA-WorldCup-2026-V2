#!/usr/bin/env bash
# ============================================================
# 卸载 V2 systemd 服务
# ============================================================
set -e

SERVICE_NAME="wc2026-v2"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"

if [ "$EUID" -ne 0 ]; then
  echo "⚠️  需要 root 权限, 重新用 sudo ..."
  exec sudo "$0" "$@"
fi

echo "🛑 停止并禁用 $SERVICE_NAME ..."
if systemctl is-active --quiet "$SERVICE_NAME" 2>/dev/null; then
  systemctl stop "$SERVICE_NAME"
  echo "   已停止"
else
  echo "   (未运行)"
fi

if systemctl is-enabled --quiet "$SERVICE_NAME" 2>/dev/null; then
  systemctl disable "$SERVICE_NAME"
  echo "   已禁用开机自启"
else
  echo "   (未启用开机自启)"
fi

if [ -f "$SERVICE_FILE" ]; then
  rm -f "$SERVICE_FILE"
  echo "🗑  删除 $SERVICE_FILE"
fi

systemctl daemon-reload
echo "🔄 systemctl daemon-reload"

# 重置失败状态 (如果之前启动失败)
systemctl reset-failed "$SERVICE_NAME" 2>/dev/null || true

echo ""
echo "✅ V2 systemd 服务卸载完成"
echo "   V1 服务 (wc2026, 端口 8000) 未受影响"
