#!/usr/bin/env bash
# One file to set up Claude usage tracking on a Mac or Linux machine.
#
#   bash setup-device.sh
#
# It checks git / python3 / GitHub access, downloads the tracker (only this
# device's data folder), asks what to call this device on the dashboard, then
# schedules the daily sync and imports this device's Claude Code history.
set -euo pipefail

REPO="mariiaivanovacs/claude-usage"
DEST="${CLAUDE_USAGE_HOME:-$HOME/.claude-usage}/repo"

say() { printf '\n==> %s\n' "$*"; }
die() { printf '\nError: %s\n' "$*" >&2; exit 1; }

say "Checking requirements"
command -v git >/dev/null || die "git is not installed. macOS: xcode-select --install   Linux: sudo apt install git"
command -v python3 >/dev/null || die "python3 is not installed. macOS: xcode-select --install   Linux: sudo apt install python3"
python3 -c 'import sys; sys.exit(sys.version_info < (3, 8))' || die "python3 is older than 3.8"
[ -d "$HOME/.claude/projects" ] || [ -n "${CLAUDE_CONFIG_DIR:-}" ] \
  || echo "Note: no Claude Code history found yet (~/.claude/projects). The tracker will pick it up once you use Claude Code."

URL="https://github.com/$REPO.git"
if ! git ls-remote "$URL" >/dev/null 2>&1; then
  if command -v gh >/dev/null; then
    say "Sign in to GitHub (the tracker repo is private)"
    if [ -r /dev/tty ]; then gh auth login --git-protocol https --web </dev/tty; else gh auth login --git-protocol https --web; fi
    gh auth setup-git
    git ls-remote "$URL" >/dev/null 2>&1 || die "this GitHub account has no access to $REPO. Ask the owner to add you as a collaborator."
  else
    die "can't reach the private repo $REPO. Install the GitHub CLI (https://cli.github.com), run 'gh auth login', then run this script again."
  fi
fi
echo "git, python3 and GitHub access: ok"

if [ -d "$DEST/.git" ]; then
  say "Updating the existing copy in $DEST"
  git -C "$DEST" pull -q --rebase
else
  say "Downloading the tracker to $DEST"
  mkdir -p "$(dirname "$DEST")"
  git clone -q --filter=blob:none --no-checkout "$URL" "$DEST"
  git -C "$DEST" sparse-checkout set --no-cone '/*' '!/devices/*'
  git -C "$DEST" checkout -q main
fi

say "Installing"
if [ -t 0 ]; then exec bash "$DEST/install/install.sh" "$@"; fi
if (exec </dev/tty) 2>/dev/null; then exec bash "$DEST/install/install.sh" "$@" </dev/tty; fi
exec bash "$DEST/install/install.sh" "$@"
