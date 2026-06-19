#!/usr/bin/env bash
# ============================================================
# WorldCup 2026 V2 - macOS 服务卸载
# ============================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
PLIST_LABEL="com.wc2026-v2"
PLIST_DST_USER="$HOME/Library/LaunchAgents/${PLIST_LABEL}.plist"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  WorldCup 2026 V2 - macOS 服务卸载"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 1) 停止并卸载
if launchctl list 2>/dev/null | grep -q "$PLIST_LABEL"; then
    echo "🛑 停止并卸载 $PLIST_LABEL ..."
    if [ -f "$PLIST_DST_USER" ]; then
        launchctl unload -w "$PLIST_DST_USER" 2>/dev/null || true
    else
        launchctl remove "$PLIST_LABEL" 2>/dev/null || true
    fi
    echo "✅ launchd 服务已停止"
else
    echo "ℹ️  $PLIST_LABEL 未在运行"
fi

# 2) 删除 plist 文件
if [ -f "$PLIST_DST_USER" ]; then
    echo "🗑️  删除 plist: $PLIST_DST_USER"
    rm -f "$PLIST_DST_USER"
fi

# 3) (可选) 清理日志
if [ -d "$SCRIPT_DIR/backend/logs" ]; then
    echo "🗑️  清理日志目录: $SCRIPT_DIR/backend/logs"
    rm -rf "$SCRIPT_DIR/backend/logs"
fi

echo ""
echo "✅ 卸载完成"
