#!/usr/bin/env bash
# Install the Claude usage collector on macOS or Linux.
#
#   install/install.sh [--device NAME] [--only PATTERN ...] [--track-all]
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
ONLY=()
TRACK_ALL=0
while [ $# -gt 0 ]; do
  case "$1" in
    --device) DEVICE="$2"; shift 2 ;;
    --only) ONLY+=("$2"); shift 2 ;;
    --track-all) TRACK_ALL=1; shift ;;
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
# The name is what the dashboard shows for this device ("Device: <name>", legends,
# the device table) and the folder its data goes into (devices/<name>/).
mkdir -p "$BASE"
slug() { printf '%s' "$1" | tr '[:upper:]' '[:lower:]' | tr -c 'a-z0-9-' '-' | sed 's/--*/-/g;s/^-//;s/-$//' | cut -c1-40; }
taken="$(git -C "$REPO_DIR" ls-tree --name-only HEAD devices/ 2>/dev/null | sed 's#^devices/##' | grep -v '^\.gitkeep$' | tr '\n' ' ' || true)"
is_taken() { case " $taken " in *" $1 "*) return 0 ;; *) return 1 ;; esac; }
TTY=""
if [ -t 0 ]; then TTY=/dev/stdin; elif [ -r /dev/tty ] && (exec </dev/tty) 2>/dev/null; then TTY=/dev/tty; fi
ask() { local ans=""; read -r -p "$1" ans <"$TTY" || true; printf '%s' "$ans"; }

current=""
[ -f "$BASE/config.json" ] && current="$("$PY" -c 'import json,sys;print(json.load(open(sys.argv[1])).get("device",""))' "$BASE/config.json" 2>/dev/null || true)"

if [ -n "$DEVICE" ]; then
  DEVICE="$(slug "$DEVICE")"
elif [ -n "$current" ]; then
  DEVICE="$current"
  echo "This device is already set up as \"$DEVICE\" (shown on the dashboard as \"Device: $DEVICE\")."
  echo "To change it later: python3 $COLLECT rename NEW-NAME"
else
  guess="$(slug "$(hostname -s 2>/dev/null || hostname)")"
  [ -n "$guess" ] || guess="device-$(date +%s | tail -c 5)"
  if [ -z "$TTY" ]; then
    DEVICE="$guess"
    echo "No terminal to ask in; naming this device \"$DEVICE\". Rename later with: python3 $COLLECT rename NEW-NAME"
  else
    echo
    echo "Name this device"
    echo "----------------"
    echo "The name is shown on the usage dashboard and its charts, e.g. \"Device: work-laptop\","
    echo "so pick something you will recognise: work-laptop, home-pc, macbook-pro."
    echo "Use latin letters, digits and dashes (other characters become dashes)."
    [ -n "$taken" ] && echo "Already used by other devices: $taken"
    while :; do
      ans="$(ask "Device name [$guess]: ")"
      DEVICE="$(slug "${ans:-$guess}")"
      if [ -z "$DEVICE" ]; then
        echo "  That name has no latin letters or digits left after cleaning it up; try another."
        continue
      fi
      if is_taken "$DEVICE"; then
        echo "  \"$DEVICE\" is already used by a device. Using it again merges both devices' data."
        yn="$(ask "  Is this the same device being set up again? [y/N]: ")"
        case "$yn" in [yY]*) ;; *) continue ;; esac
      fi
      yn="$(ask "  The dashboard will show \"Device: $DEVICE\". OK? [Y/n]: ")"
      case "$yn" in [nN]*) continue ;; *) break ;; esac
    done
  fi
fi
[ -n "$DEVICE" ] || { echo "device name is empty" >&2; exit 1; }
if [ -n "${CLAUDE_USAGE_NAME_ONLY:-}" ]; then echo "NAME=$DEVICE"; exit 0; fi   # used by tests

# ---- what to track (asked before anything is imported or pushed) ---------------
has_rules="$("$PY" -c 'import json,sys
try: c=json.load(open(sys.argv[1]))
except Exception: c={}
print(1 if (c.get("only") or c.get("exclude")) else "")' "$BASE/config.json" 2>/dev/null || true)"
if [ ${#ONLY[@]} -eq 0 ] && [ "$TRACK_ALL" = 0 ] && [ -z "$has_rules" ]; then
  if [ -z "$TTY" ]; then
    echo "No terminal to ask in: tracking ALL projects. Use --only PATTERN to limit it."
  else
    echo
    echo "What should this device track?"
    echo "------------------------------"
    echo "  1) All Claude Code projects on this device"
    echo "  2) Only some projects: everything else is never collected or pushed"
    choice="$(ask "Choice [1]: ")"
    if [ "$choice" = 2 ]; then
      echo "Enter one per line: a folder (~/Desktop/client-work, covers everything inside)"
      echo "or a repo name (my-org/website, my-org/*). Empty line when done."
      while :; do
        pat="$(ask "  keep: ")"
        [ -z "$pat" ] && break
        ONLY+=("$pat")
      done
      [ ${#ONLY[@]} -gt 0 ] || echo "  Nothing entered: tracking all projects."
    fi
  fi
fi
if [ ${#ONLY[@]} -gt 0 ]; then
  echo "Tracking only: ${ONLY[*]}"
fi

"$PY" - "$BASE/config.json" "$DEVICE" "${ONLY[@]+"${ONLY[@]}"}" <<'EOF'
import json, sys
p, dev, only = sys.argv[1], sys.argv[2], sys.argv[3:]
try:
    c = json.load(open(p))
except Exception:
    c = {}
c["device"] = dev
if only:
    c["only"] = only
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
if [ -n "${CLAUDE_USAGE_NO_SCHEDULE:-}" ]; then
  echo "Skipping the scheduler (CLAUDE_USAGE_NO_SCHEDULE is set)."
elif [ "$OS" = Darwin ]; then
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
