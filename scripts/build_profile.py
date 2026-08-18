#!/usr/bin/env python3
"""Build self-hosted profile assets for github.com/NikitaBoyarkin.

Assets generated:
- streak.svg: current / longest / total contributions from GitHub GraphQL
- activity.svg: 30-day contribution activity sparkline
- README.md: update pinned commit SHA for playable games to the latest stable commit
"""

from __future__ import annotations

import json
import os
import re
import textwrap
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
USER = os.environ.get("USER", "NikitaBoyarkin")
TOKEN = os.environ.get("GH_TOKEN", "")

# Palette (matches README dark theme)
BG = "#0a0a12"
SURFACE = "#151515"
ACCENT = "#00ff9c"
TEXT_MAIN = "#f4f4f5"
TEXT_MUTED = "#9E9E9E"


def graphql(query: str, variables: dict) -> dict:
    if not TOKEN:
        raise RuntimeError("GH_TOKEN is not set")
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": variables}).encode(),
        headers={
            "Authorization": f"bearer {TOKEN}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode())
    if "errors" in data:
        raise RuntimeError("GraphQL errors: " + json.dumps(data["errors"]))
    return data["data"]


def fetch_contributions() -> list[dict]:
    end = datetime.now(timezone.utc).date()
    start = end - timedelta(days=364)
    start = start - timedelta(days=(start.weekday() + 1) % 7)
    query = """
    query($login: String!, $from: DateTime!, $to: DateTime!) {
      user(login: $login) {
        contributionsCollection(from: $from, to: $to) {
          contributionCalendar {
            totalContributions
            weeks { contributionDays { date contributionCount } }
          }
        }
      }
    }
    """
    variables = {
        "login": USER,
        "from": start.isoformat() + "T00:00:00Z",
        "to": end.isoformat() + "T23:59:59Z",
    }
    data = graphql(query, variables)
    calendar = data["user"]["contributionsCollection"]["contributionCalendar"]
    days = [d for w in calendar["weeks"] for d in w["contributionDays"]]
    today_iso = end.isoformat()
    return [d for d in days if d["date"] <= today_iso]


def compute_streaks(days: list[dict]) -> tuple[int, int, int]:
    total = sum(d["contributionCount"] for d in days)
    current = 0
    for d in reversed(days):
        if d["contributionCount"] > 0:
            current += 1
        else:
            break
    longest = 0
    running = 0
    for d in days:
        if d["contributionCount"] > 0:
            running += 1
            longest = max(longest, running)
        else:
            running = 0
    return total, current, longest


def build_streak_svg(days: list[dict], total: int, current: int, longest: int) -> str:
    W, H = 495, 195
    svg = f"""\
    <svg xmlns='http://www.w3.org/2000/svg' style='isolation: isolate' viewBox='0 0 {W} {H}' width='{W}px' height='{H}px'>
      <defs>
        <clipPath id='r'><rect width='{W}' height='{H}' rx='4.5'/></clipPath>
      </defs>
      <g clip-path='url(#r)'>
        <rect fill='{SURFACE}' width='{W}' height='{H}'/>
        <text x='247.5' y='32' text-anchor='middle' fill='{TEXT_MUTED}' font-family='"Segoe UI", Ubuntu, sans-serif' font-size='14px' font-weight='400'>{USER}'s GitHub Streak</text>
        <g transform='translate(0, 55)'>
          <text x='82.5' y='0' text-anchor='middle' fill='{TEXT_MUTED}' font-family='"Segoe UI", Ubuntu, sans-serif' font-size='12px' font-weight='400'>Total Contributions</text>
          <text x='82.5' y='28' text-anchor='middle' fill='{ACCENT}' font-family='"Segoe UI", Ubuntu, sans-serif' font-size='28px' font-weight='700'>{total}</text>
        </g>
        <g transform='translate(165, 55)'>
          <text x='82.5' y='0' text-anchor='middle' fill='{TEXT_MUTED}' font-family='"Segoe UI", Ubuntu, sans-serif' font-size='12px' font-weight='400'>Current Streak</text>
          <text x='82.5' y='28' text-anchor='middle' fill='{ACCENT}' font-family='"Segoe UI", Ubuntu, sans-serif' font-size='28px' font-weight='700'>{current}</text>
        </g>
        <g transform='translate(330, 55)'>
          <text x='82.5' y='0' text-anchor='middle' fill='{TEXT_MUTED}' font-family='"Segoe UI", Ubuntu, sans-serif' font-size='12px' font-weight='400'>Longest Streak</text>
          <text x='82.5' y='28' text-anchor='middle' fill='{ACCENT}' font-family='"Segoe UI", Ubuntu, sans-serif' font-size='28px' font-weight='700'>{longest}</text>
        </g>
        <text x='247.5' y='155' text-anchor='middle' fill='{TEXT_MUTED}' font-family='"Segoe UI", Ubuntu, sans-serif' font-size='11px' font-weight='400'>Last updated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}</text>
      </g>
    </svg>
    """
    return textwrap.dedent(svg).strip() + "\n"


def build_activity_svg(days: list[dict]) -> str:
    # Take last 30 days with contributions.
    tail = days[-30:]
    W, H = 800, 140
    pad_left, pad_right = 40, 20
    pad_top, pad_bottom = 30, 30
    chart_w = W - pad_left - pad_right
    chart_h = H - pad_top - pad_bottom
    n = len(tail)
    max_val = max((d["contributionCount"] for d in tail), default=1)
    if max_val == 0:
        max_val = 1

    points = []
    for i, d in enumerate(tail):
        x = pad_left + (i / (n - 1)) * chart_w if n > 1 else pad_left + chart_w / 2
        y = pad_top + chart_h - (d["contributionCount"] / max_val) * chart_h
        points.append((x, y, d["contributionCount"], d["date"]))

    polyline = " ".join(f"{x:.1f},{y:.1f}" for x, y, _, _ in points)

    # Add small circles + tooltips as title elements.
    circles = ""
    for x, y, count, day in points:
        circles += f"    <circle cx='{x:.1f}' cy='{y:.1f}' r='3' fill='{ACCENT}'><title>{day}: {count} contributions</title></circle>\n"

    svg = f"""\
    <svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 {W} {H}' width='{W}px' height='{H}px'>
      <rect fill='{BG}' width='{W}' height='{H}'/>
      <text x='{W/2}' y='20' text-anchor='middle' fill='{TEXT_MUTED}' font-family='"Segoe UI", Ubuntu, sans-serif' font-size='13px' font-weight='400'>Last 30 Days Activity</text>
      <polyline points='{polyline}' fill='none' stroke='{ACCENT}' stroke-width='2' stroke-linecap='round' stroke-linejoin='round' opacity='0.8'/>
    {circles}  <text x='{pad_left}' y='{H - 8}' fill='{TEXT_MUTED}' font-family='"Segoe UI", Ubuntu, sans-serif' font-size='10px'>{tail[0]['date']}</text>
      <text x='{W - pad_right}' y='{H - 8}' text-anchor='end' fill='{TEXT_MUTED}' font-family='"Segoe UI", Ubuntu, sans-serif' font-size='10px'>{tail[-1]['date']}</text>
    </svg>
    """
    return textwrap.dedent(svg).strip() + "\n"


def latest_commit_sha(paths: list[str]) -> str:
    """Return full SHA of the most recent commit touching any of the given paths."""
    import subprocess
    repo = REPO_ROOT
    cmd = ["git", "log", "-1", "--format=%H", "--", *paths]
    result = subprocess.run(cmd, cwd=repo, capture_output=True, text=True, check=True)
    return result.stdout.strip()


def update_readme_game_sha() -> bool:
    readme_path = REPO_ROOT / "README.md"
    content = readme_path.read_text(encoding="utf-8")
    game_files = ["snake.svg", "ab-test.svg", "pong.svg", "2048.svg", "funnel-drop.svg"]
    new_sha = latest_commit_sha(game_files)
    old_sha_match = re.search(r"@([a-f0-9]{7,40})/", content)
    old_sha = old_sha_match.group(1) if old_sha_match else None
    if old_sha == new_sha:
        print(f"README game SHA already up to date: {new_sha[:7]}")
        return False
    updated = re.sub(r"@([a-f0-9]{7,40})/", f"@{new_sha}/", content)
    readme_path.write_text(updated, encoding="utf-8")
    print(f"Updated README game SHA: {old_sha[:7] if old_sha else 'none'} -> {new_sha[:7]}")
    return True


def main() -> None:
    print("Fetching contributions...")
    days = fetch_contributions()
    total, current, longest = compute_streaks(days)
    print(f"total={total} current={current} longest={longest}")

    (REPO_ROOT / "streak.svg").write_text(build_streak_svg(days, total, current, longest), encoding="utf-8")
    (REPO_ROOT / "activity.svg").write_text(build_activity_svg(days), encoding="utf-8")
    print("Wrote streak.svg and activity.svg")

    update_readme_game_sha()


if __name__ == "__main__":
    main()
