#!/usr/bin/env bash
# ============================================================
# WorldCup 2026 V2 - macOS 启动服务安装 (launchd)
# 平行于 Linux 版的 install-service.sh (systemd)
# ============================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
PLIST_SRC="$SCRIPT_DIR/backend/wc2026-v2.plist"
PLIST_LABEL="com.wc2026-v2"
PLIST_DST_USER="$HOME/Library/LaunchAgents/${PLIST_LABEL}.plist"
SERVICE_NAME="wc2026-v2"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  WorldCup 2026 V2 - macOS 服务安装"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 1) 检查 OS
if [ "$(uname -s)" != "Darwin" ]; then
    echo "❌ 此脚本仅适用于 macOS"
    echo "   Linux 用 ./install-service.sh (systemd)"
    echo "   Windows 用 NSSM/Task Scheduler"
    exit 1
fi

# 2) 检查 launchctl
if ! command -v launchctl >/dev/null 2>&1; then
    echo "❌ launchctl 不可用"
    exit 1
fi

# 3) 检查 plist 源文件
if [ ! -f "$PLIST_SRC" ]; then
    echo "❌ plist 源文件不存在: $PLIST_SRC"
    exit 1
fi

# 4) macOS LaunchAgents 目录
mkdir -p "$HOME/Library/LaunchAgents"
echo "📋 复制 plist: $PLIST_SRC → $PLIST_DST_USER"

# 5) 替换 plist 里的硬编码路径为当前用户路径
#    (因为 macOS 多用户, 把 /data/... 替换为 $SCRIPT_DIR)
TMP_PLIST="/tmp/${PLIST_LABEL}.plist"
sed "s|/data/FIFA_WorldCup_2026_V2|$SCRIPT_DIR|g" "$PLIST_SRC" > "$TMP_PLIST"
mv "$TMP_PLIST" "$PLIST_DST_USER"
echo "   (路径已适配当前目录: $SCRIPT_DIR)"

# 6) 加载服务
echo "🔄 launchctl load ..."
launchctl unload "$PLIST_DST_USER" 2>/dev/null || true
launchctl load -w "$PLIST_DST_USER"
sleep 2

# 7) 验证
if launchctl list 2>/dev/null | grep -q "$PLIST_LABEL"; then
    echo ""
    echo "✅ V2 服务已安装并启动 (label: $PLIST_LABEL)"
    echo ""
    echo "常用命令:"
    echo "   查看状态:    launchctl list | grep $PLIST_LABEL"
    echo "   手动启动:    launchctl start $PLIST_LABEL"
    echo "   手动停止:    launchctl stop $PLIST_LABEL"
    echo "   重新加载:    launchctl unload $PLIST_DST_USER && launchctl load -w $PLIST_DST_USER"
    echo "   查看日志:    tail -f $SCRIPT_DIR/backend/logs/v2.log"
    echo "   开机自启:    ✅ 已启用 (RunAtLoad=true)"
    echo ""
    echo "卸载:   ./uninstall-service-macos.sh"
else
    echo "❌ 服务加载失败, 查看日志: $SCRIPT_DIR/backend/logs/v2.err.log"
    exit 1
fi
