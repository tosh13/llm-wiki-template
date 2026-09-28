#!/usr/bin/env bash
# Mac を llm-wiki の発信側にする：llm-wiki-rehydrate.py serve を launchd で30分ごとに回す。
#
#   bash llm-wiki-serve-launchd.sh install     # 登録（やり直しにも使う）
#   bash llm-wiki-serve-launchd.sh status      # 動いているか
#   bash llm-wiki-serve-launchd.sh uninstall   # やめる
#
# 発信側は vault ごとに1台だけにする。選び方は icloud-stuck-pages.md「発信側の条件」。
# ログは ~/.claude/state/llm-wiki-rehydrate/ の serve.log（本体が書く）と launchd.log（異常終了の出力）。
set -euo pipefail

LABEL="llm-wiki.rehydrate-serve"
PLIST="$HOME/Library/LaunchAgents/${LABEL}.plist"
STATE="$HOME/.claude/state/llm-wiki-rehydrate"
DOMAIN="gui/$(id -u)"
# 呼ばれたパスのまま使う。~/.claude/llm-wiki-template 経由で呼べば、clone を移しても別名の張り直しで追随する
SCRIPT="$(cd "$(dirname "$0")" && pwd -L)/llm-wiki-rehydrate.py"

case "${1:-}" in
  install)
    [ -f "$SCRIPT" ] || { echo "本体が見つからない: $SCRIPT" >&2; exit 1; }
    [ -d "$HOME/llm-wiki" ] || { echo "vault（~/llm-wiki）が無い端末では発信側になれない" >&2; exit 1; }
    PY="$(command -v python3 || true)"
    [ -n "$PY" ] || { echo "python3 が見つからない" >&2; exit 1; }
    "$PY" -c 'import sys; sys.exit(sys.version_info < (3, 8))' || { echo "python3 が 3.8 より古い: $PY" >&2; exit 1; }
    mkdir -p "$HOME/Library/LaunchAgents" "$STATE"
    cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>${LABEL}</string>
  <key>ProgramArguments</key>
  <array>
    <string>${PY}</string>
    <string>${SCRIPT}</string>
    <string>serve</string>
  </array>
  <key>StartInterval</key><integer>1800</integer>
  <key>RunAtLoad</key><true/>
  <key>ProcessType</key><string>Background</string>
  <key>StandardOutPath</key><string>${STATE}/launchd.log</string>
  <key>StandardErrorPath</key><string>${STATE}/launchd.log</string>
</dict>
</plist>
EOF
    plutil -lint "$PLIST" >/dev/null
    launchctl bootout "$DOMAIN/$LABEL" 2>/dev/null || true
    launchctl bootstrap "$DOMAIN" "$PLIST"
    echo "登録した: ${LABEL}（30分ごと。python3 は ${PY}）"
    ;;
  status)
    if launchctl print "$DOMAIN/$LABEL" >/dev/null 2>&1; then
      launchctl print "$DOMAIN/$LABEL" | grep -E "state =|runs =|last exit code =|run interval =" | sed 's/^[[:space:]]*/  /'
    else
      echo "登録されていない: $LABEL"
    fi
    [ -f "$STATE/serve.log" ] && { echo "serve.log の最後:"; tail -3 "$STATE/serve.log" | sed 's/^/  /'; }
    exit 0
    ;;
  uninstall)
    launchctl bootout "$DOMAIN/$LABEL" 2>/dev/null || true
    rm -f "$PLIST"
    echo "外した: $LABEL"
    ;;
  *)
    echo "使い方: bash $(basename "$0") install|status|uninstall" >&2
    exit 64
    ;;
esac
