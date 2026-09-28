#!/usr/bin/env bash
# Install the Claude usage collector on macOS or Linux.
#
#   install/install.sh [--device NAME]
#   install/install.sh --uninstall
#
# Runs the collector every day at 08:00 Malaysia time (converted to this
# device's clock), catches up after sleep, and adds a Claude Code SessionEnd hook.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BASE="${CLAUDE_USAGE_HOME:-$HOME/.claude-usage}"
LABEL="com.claude-usage.collect"
RUN_AT_TZ="Asia/Kuala_Lumpur"
RUN_AT="08:00"

DEVICE=""
UNINSTALL=0
while [ $# -gt 0 ]; do
  case "$1" in
    --device) DEVICE="$2"; shift 2 ;;
    --uninstall) UNINSTALL=1; shift ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
done

PY="$(command -v python3 || true)"
[ -n "$PY" ] || { echo "python3 is required" >&2; exit 1; }
command -v git >/dev/null || { echo "git is required" >&2; exit 1; }
OS="$(uname -s)"
COLLECT="$REPO_DIR/collector/collect.py"

plist="$HOME/Library/LaunchAgents/$LABEL.plist"
unit_dir="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"

if [ "$UNINSTALL" = 1 ]; then
  if [ "$OS" = Darwin ]; then
    launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
    rm -f "$plist"
  elif command -v systemctl >/dev/null; then
    systemctl --user disable --now claude-usage.timer 2>/dev/null || true
    rm -f "$unit_dir/claude-usage.service" "$unit_dir/claude-usage.timer"
    systemctl --user daemon-reload || true
  fi
  (crontab -l 2>/dev/null | grep -v "claude-usage" | crontab -) 2>/dev/null || true
  "$PY" "$COLLECT" settings uninstall
  echo "Uninstalled. Data already pushed stays in the repo; local state is in $BASE."
  exit 0
fi

# ---- device name ------------------------------------------------------------
mkdir -p "$BASE"
if [ -z "$DEVICE" ] && [ -f "$BASE/config.json" ]; then
  DEVICE="$("$PY" -c 'import json,sys;print(json.load(open(sys.argv[1])).get("device",""))' "$BASE/config.json")"
fi
if [ -z "$DEVICE" ]; then
  guess="$(hostname -s 2>/dev/null || hostname)"
  guess="$(printf '%s' "$guess" | tr '[:upper:]' '[:lower:]' | tr -c 'a-z0-9-' '-' | sed 's/--*/-/g;s/^-//;s/-$//')"
  if [ -t 0 ]; then
    read -r -p "Device name [$guess]: " DEVICE
  fi
  DEVICE="${DEVICE:-$guess}"
fi
DEVICE="$(printf '%s' "$DEVICE" | tr '[:upper:]' '[:lower:]' | tr -c 'a-z0-9-' '-' | sed 's/--*/-/g;s/^-//;s/-$//')"
[ -n "$DEVICE" ] || { echo "device name is empty" >&2; exit 1; }
"$PY" - "$BASE/config.json" "$DEVICE" <<'EOF'
import json, sys
p, dev = sys.argv[1], sys.argv[2]
try:
    c = json.load(open(p))
except Exception:
    c = {}
c["device"] = dev
json.dump(c, open(p, "w"), indent=2)
EOF

# ---- repo: only this device's folder is checked out -------------------------
if git -C "$REPO_DIR" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  git -C "$REPO_DIR" sparse-checkout set --no-cone '/*' '!/devices/*' "/devices/$DEVICE/" >/dev/null 2>&1 || true
fi

# ---- when to run: 08:00 Malaysia time on this device's clock ----------------
read -r LOCAL_H LOCAL_M <<<"$("$PY" - "$RUN_AT_TZ" "$RUN_AT" <<'EOF'
import sys
from datetime import datetime, timedelta, timezone
h, m = map(int, sys.argv[2].split(":"))
now = datetime.now(timezone(timedelta(hours=8)))   # Malaysia: UTC+8 all year, no DST
t = now.replace(hour=h, minute=m, second=0, microsecond=0).astimezone()
print(t.hour, t.minute)
EOF
)"
echo "Daily run: $RUN_AT $RUN_AT_TZ = $(printf '%02d:%02d' "$LOCAL_H" "$LOCAL_M") on this device"

# ---- scheduler ----------------------------------------------------------------
if [ "$OS" = Darwin ]; then
  mkdir -p "$(dirname "$plist")"
  cat >"$plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key>
  <array><string>$PY</string><string>$COLLECT</string></array>
  <key>StartCalendarInterval</key>
  <dict><key>Hour</key><integer>$LOCAL_H</integer><key>Minute</key><integer>$LOCAL_M</integer></dict>
  <key>RunAtLoad</key><true/>
  <key>EnvironmentVariables</key>
  <dict><key>PATH</key><string>$PATH</string><key>HOME</key><string>$HOME</string></dict>
  <key>StandardOutPath</key><string>$BASE/launchd.log</string>
  <key>StandardErrorPath</key><string>$BASE/launchd.log</string>
  <key>ProcessType</key><string>Background</string>
</dict>
</plist>
EOF
  launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
  launchctl bootstrap "gui/$(id -u)" "$plist"
  echo "Scheduled with launchd ($plist). Missed runs happen when the Mac wakes up."
elif command -v systemctl >/dev/null && systemctl --user show-environment >/dev/null 2>&1; then
  mkdir -p "$unit_dir"
  cat >"$unit_dir/claude-usage.service" <<EOF
[Unit]
Description=Claude usage collector

[Service]
Type=oneshot
Environment=PATH=$PATH
ExecStart=$PY $COLLECT
EOF
  cat >"$unit_dir/claude-usage.timer" <<EOF
[Unit]
Description=Claude usage collector, daily at $RUN_AT $RUN_AT_TZ

[Timer]
OnCalendar=*-*-* $RUN_AT:00 $RUN_AT_TZ
Persistent=true

[Install]
WantedBy=timers.target
EOF
  systemctl --user daemon-reload
  systemctl --user enable --now claude-usage.timer
  echo "Scheduled with a systemd user timer. Missed runs happen at next boot."
else
  line="$LOCAL_M $LOCAL_H * * * \"$PY\" \"$COLLECT\" # claude-usage"
  (crontab -l 2>/dev/null | grep -v "claude-usage"; echo "$line") | crontab -
  echo "Scheduled with cron (runs missed while the machine is off are skipped; the hook still syncs)."
fi

# ---- Claude Code settings: SessionEnd hook + keep transcripts a year --------
"$PY" "$COLLECT" settings install

# ---- first run: import all history now ---------------------------------------
echo "Importing existing history (can take a minute the first time)..."
"$PY" "$COLLECT"
echo "Done. Device '$DEVICE' is set up. Log: $BASE/collect.log"
