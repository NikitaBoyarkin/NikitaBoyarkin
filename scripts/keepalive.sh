#!/bin/zsh
set -euo pipefail

repo="/Users/nikitaboarkin/Desktop/00 ide/00 portfolio/NikitaBoyarkin"
log="/tmp/keepalive-streak.log"

exec >> "$log" 2>&1

cd "$repo"
git pull --ff-only

last=$(git log -1 --format=%ct)
now=$(date -u +%s)
days_since=$(( (now - last) / 86400 ))

if (( days_since >= 1 )); then
  echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] No commit today. Creating keepalive..."
  git commit --allow-empty -m "chore: daily keepalive $(date -u +%Y-%m-%d)"
  git push
  echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Keepalive pushed"
else
  echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Streak safe"
fi
