#!/usr/bin/env python3
"""Build self-hosted profile assets for github.com/NikitaBoyarkin.

Assets generated:
- stats.svg: total contributions, streak, public repos, followers from GraphQL
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
ACCENT = "#ff6643"
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


def fetch_user_data() -> dict:
    end = datetime.now(timezone.utc).date()
    start = end - timedelta(days=364)
    start = start - timedelta(days=(start.weekday() + 1) % 7)
    query = """
    query($login: String!, $from: DateTime!, $to: DateTime!) {
      user(login: $login) {
        login
        createdAt
        followers {
          totalCount
        }
        repositories(isFork: false, privacy: PUBLIC, first: 0) {
          totalCount
        }
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
    return graphql(query, variables)


def fetch_contributions() -> list[dict]:
    data = fetch_user_data()
    calendar = data["user"]["contributionsCollection"]["contributionCalendar"]
    days = [d for w in calendar["weeks"] for d in w["contributionDays"]]
    today_iso = datetime.now(timezone.utc).date().isoformat()
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


def build_stats_svg(user_data: dict, total: int, current: int, longest: int) -> str:
    user = user_data["user"]
    public_repos = user["repositories"]["totalCount"]
    followers = user["followers"]["totalCount"]
    # "Active Since" = year the GitHub account was created (user.createdAt),
    # not the year of the first contribution — so it reflects "on GitHub since".
    active_since = datetime.fromisoformat(user["createdAt"].replace("Z", "+00:00")).year

    W, H = 495, 195
    svg = f"""\
    <svg xmlns='http://www.w3.org/2000/svg' style='isolation: isolate' viewBox='0 0 {W} {H}' width='{W}px' height='{H}px'>
      <defs>
        <clipPath id='rs'><rect width='{W}' height='{H}' rx='4.5'/></clipPath>
      </defs>
      <g clip-path='url(#rs)'>
        <rect fill='{SURFACE}' width='{W}' height='{H}'/>
        <text x='247.5' y='32' text-anchor='middle' fill='{TEXT_MUTED}' font-family='"Segoe UI", Ubuntu, sans-serif' font-size='14px' font-weight='400'>{USER}'s GitHub Stats</text>
        <g transform='translate(0, 55)'>
          <text x='82.5' y='0' text-anchor='middle' fill='{TEXT_MUTED}' font-family='"Segoe UI", Ubuntu, sans-serif' font-size='12px' font-weight='400'>Contributions</text>
          <text x='82.5' y='28' text-anchor='middle' fill='{ACCENT}' font-family='"Segoe UI", Ubuntu, sans-serif' font-size='28px' font-weight='700'>{total}</text>
        </g>
        <g transform='translate(165, 55)'>
          <text x='82.5' y='0' text-anchor='middle' fill='{TEXT_MUTED}' font-family='"Segoe UI", Ubuntu, sans-serif' font-size='12px' font-weight='400'>Public Repos</text>
          <text x='82.5' y='28' text-anchor='middle' fill='{ACCENT}' font-family='"Segoe UI", Ubuntu, sans-serif' font-size='28px' font-weight='700'>{public_repos}</text>
        </g>
        <g transform='translate(330, 55)'>
          <text x='82.5' y='0' text-anchor='middle' fill='{TEXT_MUTED}' font-family='"Segoe UI", Ubuntu, sans-serif' font-size='12px' font-weight='400'>Followers</text>
          <text x='82.5' y='28' text-anchor='middle' fill='{ACCENT}' font-family='"Segoe UI", Ubuntu, sans-serif' font-size='28px' font-weight='700'>{followers}</text>
        </g>
        <g transform='translate(0, 118)'>
          <text x='82.5' y='0' text-anchor='middle' fill='{TEXT_MUTED}' font-family='"Segoe UI", Ubuntu, sans-serif' font-size='12px' font-weight='400'>Current Streak</text>
          <text x='82.5' y='28' text-anchor='middle' fill='{ACCENT}' font-family='"Segoe UI", Ubuntu, sans-serif' font-size='28px' font-weight='700'>{current}</text>
        </g>
        <g transform='translate(165, 118)'>
          <text x='82.5' y='0' text-anchor='middle' fill='{TEXT_MUTED}' font-family='"Segoe UI", Ubuntu, sans-serif' font-size='12px' font-weight='400'>Longest Streak</text>
          <text x='82.5' y='28' text-anchor='middle' fill='{ACCENT}' font-family='"Segoe UI", Ubuntu, sans-serif' font-size='28px' font-weight='700'>{longest}</text>
        </g>
        <g transform='translate(330, 118)'>
          <text x='82.5' y='0' text-anchor='middle' fill='{TEXT_MUTED}' font-family='"Segoe UI", Ubuntu, sans-serif' font-size='12px' font-weight='400'>Active Since</text>
          <text x='82.5' y='28' text-anchor='middle' fill='{ACCENT}' font-family='"Segoe UI", Ubuntu, sans-serif' font-size='28px' font-weight='700'>{active_since}</text>
        </g>
        <text x='247.5' y='182' text-anchor='middle' fill='{TEXT_MUTED}' font-family='"Segoe UI", Ubuntu, sans-serif' font-size='11px' font-weight='400'>Last updated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}</text>
      </g>
    </svg>
    """
    return textwrap.dedent(svg).strip() + "\n"


def build_activity_svg(days: list[dict]) -> str:
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


def fetch_languages() -> list[tuple[str, int, str]]:
    """Aggregate language bytes across public non-fork repos via GraphQL.

    Returns [(name, bytes, color), ...] sorted by bytes desc. Color is the
    GitHub linguist color for the language (falls back to neutral grey).
    """
    query = """
    query($login: String!) {
      user(login: $login) {
        repositories(isFork: false, privacy: PUBLIC, first: 100,
                     ownerAffiliations: OWNER,
                     orderBy: {field: UPDATED_AT, direction: DESC}) {
          nodes {
            languages(first: 50, orderBy: {field: SIZE, direction: DESC}) {
              edges { size node { name color } }
            }
          }
        }
      }
    }
    """
    data = graphql(query, {"login": USER})
    agg: dict[str, list] = {}
    for repo in data["user"]["repositories"]["nodes"]:
        langs = (repo or {}).get("languages")
        if not langs:
            continue
        for edge in langs["edges"]:
            name = edge["node"]["name"]
            color = edge["node"].get("color") or "#666666"
            size = edge["size"]
            agg.setdefault(name, [0, color])[0] += size
    items = [(name, v[0], v[1]) for name, v in agg.items()]
    items.sort(key=lambda x: x[1], reverse=True)
    return items


def build_top_languages_svg(langs: list[tuple[str, int, str]]) -> str:
    import math
    W, H = 340, 210
    cx, cy, R, sw = 70, 100, 52, 16
    circumference = 2 * math.pi * R
    top = langs[:10]
    total = sum(s for _, s, _ in top) or 1
    cum = 0.0
    slices = ""
    for name, size, color in top:
        frac = size / total
        dash = frac * circumference
        offset = -cum * circumference
        slices += (
            f"    <circle cx='{cx}' cy='{cy}' r='{R}' fill='none' stroke='{color}' "
            f"stroke-width='{sw}' stroke-dasharray='{dash:.1f} {circumference - dash:.1f}' "
            f"stroke-dashoffset='{offset:.1f}'>"
            f"<title>{name}: {size / total * 100:.1f}%</title></circle>\n"
        )
        cum += frac
    legend = ""
    for i, (name, size, color) in enumerate(top):
        ly = 30 + i * 17
        pct = size / total * 100
        legend += (
            f"    <rect x='150' y='{ly - 9}' width='10' height='10' rx='2' fill='{color}'/>\n"
            f"    <text x='166' y='{ly}' fill='{TEXT_MAIN}' "
            f"font-family='Segoe UI, Ubuntu, sans-serif' font-size='11px'>"
            f"{name} {pct:.1f}%</text>\n"
        )
    svg = f"""\
    <svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 {W} {H}' width='{W}px' height='{H}px'>
      <rect fill='{BG}' width='{W}' height='{H}' rx='6'/>
      <text x='{W / 2}' y='20' text-anchor='middle' fill='{TEXT_MUTED}'
            font-family='Segoe UI, Ubuntu, sans-serif' font-size='13px' font-weight='400'>Top Languages</text>
      <g transform='rotate(-90 {cx} {cy})'>
        <circle cx='{cx}' cy='{cy}' r='{R}' fill='none' stroke='#1c1c28' stroke-width='{sw}'/>
    {slices}  </g>
    {legend}  <text x='{W / 2}' y='{H - 8}' text-anchor='middle' fill='{TEXT_MUTED}'
            font-family='Segoe UI, Ubuntu, sans-serif' font-size='9px'>Last updated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}</text>
    </svg>
    """
    return textwrap.dedent(svg).strip() + "\n"


def update_readme_refresh_block(days: list[dict]) -> bool:
    """Refresh the 'Last refreshed' marker block in README.

    The timestamp changes every run, so the README always carries a diff and
    git-auto-commit produces a MEANINGFUL commit each day — replacing the
    empty keepalive commits that game the streak (TOS risk mitigation).
    """
    readme_path = REPO_ROOT / "README.md"
    content = readme_path.read_text(encoding="utf-8")
    week = sum(d["contributionCount"] for d in days[-7:])
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    block = (
        f"<!-- LAST-REFRESHED:START -->\n"
        f"_Last refreshed: {now} \u00b7 {week} contributions in the last 7 days_\n"
        f"<!-- LAST-REFRESHED:END -->"
    )
    pattern = re.compile(r"<!-- LAST-REFRESHED:START -->.*?<!-- LAST-REFRESHED:END -->", re.DOTALL)
    if pattern.search(content):
        new_content = pattern.sub(lambda _: block, content)
    else:
        # Fallback: insert under the Activity header if the marker was removed.
        new_content = content.replace(
            "### \u26a1 Activity\n",
            f"### \u26a1 Activity\n\n{block}\n\n",
            1,
        )
    if new_content == content:
        print("Refresh block already up to date")
        return False
    readme_path.write_text(new_content, encoding="utf-8")
    print(f"Refreshed README 'Last refreshed' block: {now} ({week} contribs/7d)")
    return True


def main() -> None:
    print("Fetching user data...")
    user_data = fetch_user_data()
    days = fetch_contributions()
    total, current, longest = compute_streaks(days)
    print(f"total={total} current={current} longest={longest}")

    (REPO_ROOT / "stats.svg").write_text(build_stats_svg(user_data, total, current, longest), encoding="utf-8")
    (REPO_ROOT / "streak.svg").write_text(build_streak_svg(days, total, current, longest), encoding="utf-8")
    (REPO_ROOT / "activity.svg").write_text(build_activity_svg(days), encoding="utf-8")
    print("Wrote stats.svg, streak.svg and activity.svg")

    try:
        langs = fetch_languages()
        (REPO_ROOT / "top-languages.svg").write_text(build_top_languages_svg(langs), encoding="utf-8")
        print(f"Wrote top-languages.svg ({len(langs)} languages)")
    except Exception as exc:
        print(f"top-languages.svg skipped: {exc}")

    update_readme_refresh_block(days)

    update_readme_game_sha()


if __name__ == "__main__":
    main()
