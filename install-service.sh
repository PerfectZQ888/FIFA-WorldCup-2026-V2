#!/usr/bin/env bash
# ============================================================
# 安装 V2 为 systemd 服务 (开机自启)
# 平行于 V1 的 wc2026.service (端口 8000)
# ============================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_SRC="$SCRIPT_DIR/backend/wc2026-v2.service"
SERVICE_NAME="wc2026-v2"
SERVICE_DST="/etc/systemd/system/${SERVICE_NAME}.service"

# 1) 检查 systemd
if ! command -v systemctl >/dev/null 2>&1; then
  echo "❌ systemctl 不可用, 此系统不是 systemd"
  echo "   请用 nohup 方式启动: ./start.sh"
  exit 1
fi

# 2) 检查 service 文件
if [ ! -f "$SERVICE_SRC" ]; then
  echo "❌ $SERVICE_SRC 不存在"
  exit 1
fi

# 3) 检查权限
if [ "$EUID" -ne 0 ]; then
  echo "⚠️  需要 root 权限, 重新用 sudo ..."
  exec sudo "$0" "$@"
fi

# 4) 复制 service 文件
echo "📋 复制 service 文件: $SERVICE_SRC → $SERVICE_DST"
cp "$SERVICE_SRC" "$SERVICE_DST"
chmod 644 "$SERVICE_DST"

# 5) 重新加载 systemd
echo "🔄 systemctl daemon-reload ..."
systemctl daemon-reload

# 6) 启用 + 启动
echo "🚀 启用并启动 $SERVICE_NAME ..."
systemctl enable "$SERVICE_NAME"
systemctl restart "$SERVICE_NAME"

# 7) 等待启动
sleep 2

# 8) 显示状态
echo ""
echo "============================================================"
echo "✅ V2 systemd 服务安装完成!"
echo "============================================================"
echo ""
echo "📊 当前状态:"
systemctl status "$SERVICE_NAME" --no-pager -l 2>&1 | head -20 || true
echo ""
echo "🛠  常用命令:"
echo "   查看状态:  sudo systemctl status $SERVICE_NAME"
echo "   启动:      sudo systemctl start $SERVICE_NAME"
echo "   停止:      sudo systemctl stop $SERVICE_NAME"
echo "   重启:      sudo systemctl restart $SERVICE_NAME"
echo "   实时日志:  sudo journalctl -u $SERVICE_NAME -f"
echo "               或: tail -f $SCRIPT_DIR/backend/logs/v2.log"
echo "   卸载:      sudo $SCRIPT_DIR/uninstall-service.sh"
echo ""
echo "🌐 访问地址:"
echo "   主页:     http://localhost:8001/"
echo "   API 文档: http://localhost:8001/docs"
echo "   V1 平行:  http://localhost:8000/  (V1 服务, 互不影响)"
echo ""

# 9) 健康检查
if command -v curl >/dev/null 2>&1; then
  if curl -sf -m 3 "http://127.0.0.1:8001/api/health" >/dev/null; then
    echo "🩺 健康检查: ✅ /api/health 正常"
    curl -s -m 3 "http://127.0.0.1:8001/api/health" | python3 -m json.tool 2>/dev/null | sed 's/^/   /' || true
  else
    echo "🩺 健康检查: ⚠️  /api/health 无响应, 等待几秒再试"
    echo "   查看日志: sudo journalctl -u $SERVICE_NAME -n 30"
  fi
fi
