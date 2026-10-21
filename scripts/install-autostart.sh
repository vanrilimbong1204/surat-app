#!/usr/bin/env bash
# macOS: jalankan Arsip Surat otomatis setiap login (LaunchAgent). Hapus: --uninstall
set -euo pipefail
cd "$(dirname "$0")/.."
LABEL=com.arsipsurat.api
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"

if [ "${1:-}" = "--uninstall" ]; then
  launchctl unload "$PLIST" 2>/dev/null || true
  rm -f "$PLIST"; echo "Auto-start dihapus."; exit 0
fi

mkdir -p "$HOME/Library/LaunchAgents"
cat > "$PLIST" <<PL
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key><array><string>$PWD/scripts/start.sh</string></array>
  <key>WorkingDirectory</key><string>$PWD</string>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>StandardOutPath</key><string>$HOME/Library/Logs/arsipsurat.log</string>
  <key>StandardErrorPath</key><string>$HOME/Library/Logs/arsipsurat.log</string>
</dict>
</plist>
PL
launchctl unload "$PLIST" 2>/dev/null || true
launchctl load "$PLIST"
echo "Auto-start aktif. Log: ~/Library/Logs/arsipsurat.log"
