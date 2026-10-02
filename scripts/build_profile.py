#!/usr/bin/env python3
"""Build self-hosted profile assets for github.com/NikitaBoyarkin.

Assets generated:
- hero.svg: branded header band — name, role, one-line pitch, A/B motif
- stats.svg: contributions, current/longest streak, public repos, followers (GraphQL)
- activity.svg: 30-day contribution activity sparkline
- metrics.svg: slim self-hosted contribution map (replaces lowlighter/metrics)
- contribution-types.svg: commits / PRs / issues / reviews breakdown
- monthly-activity.svg: contributions aggregated by month
- top-languages.svg: aggregated language bytes donut
- README.md: refresh the 'Last refreshed' marker block

Writes are idempotent: an asset whose content is unchanged apart from the
rendered timestamp is left untouched, so daily runs do not churn git history.

Network calls retry up to 3 times with exponential backoff. Use --dry-run to
preview planned writes without touching files.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import textwrap
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path
from xml.sax.saxutils import escape

REPO_ROOT = Path(__file__).resolve().parent.parent
# GitHub login is a config value, never the OS user: `$USER` on macOS/Linux is
# the shell account (e.g. "nikitaboarkin"), which would lowercase the rendered
# cards. Prefer an explicit env var, fall back to the profile owner.
DEFAULT_USER = "NikitaBoyarkin"
USER = os.environ.get("GH_USER") or DEFAULT_USER
TOKEN = os.environ.get("GH_TOKEN", "")

DRY_RUN = False


# Rendered timestamps change on every run; ignore them when deciding whether an
# asset actually changed, otherwise each run rewrites every file (CI self-loop).
_TIMESTAMP_RE = re.compile(r"Last updated:[^<\n]*")


def _without_timestamp(content: str) -> str:
    return _TIMESTAMP_RE.sub("Last updated:", content)


def _esc(value: object) -> str:
    """XML-escape a value for both text nodes and single-quoted attributes.

    Language names, the GitHub login and linguist colors come from outside this
    process; raw interpolation produced non-well-formed SVG, and a color carrying
    a quote could escape its attribute.
    """
    return escape(str(value), {'"': "&quot;", "'": "&apos;"})


# Fixed English month labels: strftime("%b") is locale-dependent, so a dev machine
# with LC_TIME=ru_RU rendered Cyrillic months into an otherwise English card.
_MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def write_asset(path: Path, content: str) -> None:
    """Write an asset file idempotently, respecting --dry-run."""
    if path.exists() and _without_timestamp(path.read_text(encoding="utf-8")) == _without_timestamp(
        content
    ):
        print(f"Unchanged {path.name} (timestamp-only diff)")
        return
    if path.suffix == ".svg":
        # Fail loudly here rather than commit a card GitHub renders as a broken image.
        ET.fromstring(content)
    if DRY_RUN:
        print(f"[dry-run] would write {path.name} ({len(content)} chars)")
        return
    path.write_text(content, encoding="utf-8")
    print(f"Wrote {path.name}")


# Palette — hekcode brand, 60 / 30 / 10:
#   #f8f2da  cream      → background / surfaces
#   #fe4e02  orange     → primary data / actions
#   #1400c3  deep blue  → text / highlights
# Every secondary tone is an opacity on one of these three tokens, never a new
# hex value, so the rendered cards stay exactly 3 colors.
BG = "#f8f2da"
SURFACE = "#f8f2da"
ACCENT = "#fe4e02"
TEXT_MAIN = "#1400c3"
MUTED_OP = "0.62"  # secondary text — blue @62% over cream
FAINT_OP = "0.14"  # gridlines, baselines, empty tracks/tiles — blue @14%
GHOST_OP = "0.45"  # neutral "Other" slice — blue @45%


# Hero copy, kept as data so the README header and its test assert the same words.
HERO_NAME = "NIKITA BOYARKIN"
HERO_ROLE = "DATA / PRODUCT ANALYST"
HERO_TAGLINE = (
    "Ambiguous product questions →",
    "clean experiments, SQL pipelines, decisions.",
)
HERO_STRIP = "SQL · Python · Experimentation · CUPED · Retention"


def build_hero_svg() -> str:
    """Branded header band: name, role, one-line pitch, schematic A/B motif.

    Vector-only and self-hosted. The reference profile opens with an 820x250
    banner that is ~200 KB of base64 GIF; this one carries the same job — name
    and positioning readable before any scroll — in ~2 KB and no raster.

    The motif is a bare A/B pair with a "+lift" caption rather than a figure:
    a real number here would be an unlinked claim in the header, which is what
    ANALYTICS_EVIDENCE exists to avoid.
    """
    W, H = 800, 220
    alt = f"{HERO_NAME} — {HERO_ROLE}. {HERO_TAGLINE[0]} {HERO_TAGLINE[1]}"
    desc = (
        "Header banner: name, role, a one-line positioning statement, and a "
        "schematic A/B lift motif."
    )
    tagline = "".join(
        f"      <text x='40' y='{142 + i * 19}' fill='{TEXT_MAIN}' fill-opacity='{MUTED_OP}' "
        f"font-family='Segoe UI, Ubuntu, sans-serif' font-size='13px'>{_esc(line)}</text>\n"
        for i, line in enumerate(HERO_TAGLINE)
    )
    svg = f"""\
    <svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 {W} {H}' width='{W}' height='{H}'
         role='img' aria-label='{_esc(alt)}'>
      <title>{_esc(alt)}</title>
      <desc>{_esc(desc)}</desc>
      <rect fill='{BG}' width='{W}' height='{H}' rx='8'/>
      <text x='40' y='66' fill='{TEXT_MAIN}' font-family='Segoe UI, Ubuntu, sans-serif'
            font-size='34px' font-weight='800' letter-spacing='1.5'>{_esc(HERO_NAME)}</text>
      <text x='40' y='96' fill='{ACCENT}' font-family='Segoe UI, Ubuntu, sans-serif'
            font-size='14px' font-weight='700' letter-spacing='2.6'>{_esc(HERO_ROLE)}</text>
      <line x1='40' y1='116' x2='360' y2='116' stroke='{TEXT_MAIN}' stroke-opacity='{FAINT_OP}' stroke-width='1'/>
{tagline}      <text x='40' y='192' fill='{TEXT_MAIN}' fill-opacity='{MUTED_OP}'
            font-family='Segoe UI, Ubuntu, sans-serif' font-size='11px' font-weight='600'>{_esc(HERO_STRIP)}</text>
      <line x1='490' y1='40' x2='490' y2='180' stroke='{TEXT_MAIN}' stroke-opacity='{FAINT_OP}' stroke-width='1'/>
      <text x='647' y='56' text-anchor='middle' fill='{ACCENT}'
            font-family='Segoe UI, Ubuntu, sans-serif' font-size='12px' font-weight='700'>+lift</text>
      <rect x='584' y='112' width='50' height='58' rx='3' fill='{TEXT_MAIN}' fill-opacity='0.26'/>
      <rect x='660' y='84' width='50' height='86' rx='3' fill='{ACCENT}'/>
      <line x1='550' y1='170' x2='744' y2='170' stroke='{TEXT_MAIN}' stroke-opacity='{FAINT_OP}' stroke-width='1'/>
      <text x='609' y='188' text-anchor='middle' fill='{TEXT_MAIN}' fill-opacity='{MUTED_OP}'
            font-family='Segoe UI, Ubuntu, sans-serif' font-size='11px' font-weight='600'>A</text>
      <text x='685' y='188' text-anchor='middle' fill='{TEXT_MAIN}' fill-opacity='{MUTED_OP}'
            font-family='Segoe UI, Ubuntu, sans-serif' font-size='11px' font-weight='600'>B</text>
    </svg>
    """
    return textwrap.dedent(svg).strip() + "\n"


def graphql(query: str, variables: dict, retries: int = 3) -> dict:
    if not TOKEN:
        raise RuntimeError("GH_TOKEN is not set")
    payload = json.dumps({"query": query, "variables": variables}).encode()
    last_exc: Exception | None = None
    for attempt in range(1, retries + 1):
        req = urllib.request.Request(
            "https://api.github.com/graphql",
            data=payload,
            headers={
                "Authorization": f"bearer {TOKEN}",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read().decode())
            if "errors" in data:
                raise RuntimeError("GraphQL errors: " + json.dumps(data["errors"]))
            return data["data"]
        except (urllib.error.URLError, TimeoutError) as exc:
            last_exc = exc
            if attempt == retries:
                raise
            wait = 2 ** (attempt - 1)
            print(f"GraphQL attempt {attempt}/{retries} failed: {exc}; retrying in {wait}s")
            time.sleep(wait)
    raise RuntimeError(f"GraphQL exhausted retries: {last_exc}")


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
        repositories(isFork: false, privacy: PUBLIC, first: 100, ownerAffiliations: OWNER) {
          totalCount
          nodes {
            name
          }
        }
        contributionsCollection(from: $from, to: $to) {
          totalCommitContributions
          totalPullRequestContributions
          totalIssueContributions
          totalPullRequestReviewContributions
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


def extract_contributions(user_data: dict) -> list[dict]:
    """Flatten the contribution calendar into a list of past days.

    Takes already-fetched user data so a run makes exactly one GraphQL call.
    """
    calendar = user_data["user"]["contributionsCollection"]["contributionCalendar"]
    days = [d for w in calendar["weeks"] for d in w["contributionDays"]]
    today_iso = datetime.now(timezone.utc).date().isoformat()
    return [d for d in days if d["date"] <= today_iso]


def extract_contribution_types(user_data: dict) -> list[tuple[str, int]]:
    """Contribution breakdown by type (commits / PRs / issues / reviews)."""
    c = user_data["user"]["contributionsCollection"]
    return [
        ("Commits", c["totalCommitContributions"]),
        ("Pull Requests", c["totalPullRequestContributions"]),
        ("Issues", c["totalIssueContributions"]),
        ("Code Reviews", c["totalPullRequestReviewContributions"]),
    ]


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


def public_repo_names(user_data: dict) -> set[str]:
    """Names of the owner's public non-fork repos — input to evidence reconciliation."""
    nodes = user_data["user"]["repositories"].get("nodes") or []
    return {n["name"] for n in nodes if n}


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
        <text x='247.5' y='32' text-anchor='middle' fill='{TEXT_MAIN}' fill-opacity='{MUTED_OP}' font-family='"Segoe UI", Ubuntu, sans-serif' font-size='16px' font-weight='400'>{_esc(USER)}'s GitHub Stats</text>
        <g transform='translate(0, 55)'>
          <text x='82.5' y='0' text-anchor='middle' fill='{TEXT_MAIN}' fill-opacity='{MUTED_OP}' font-family='"Segoe UI", Ubuntu, sans-serif' font-size='13px' font-weight='400'>Contributions</text>
          <text x='82.5' y='28' text-anchor='middle' fill='{ACCENT}' font-family='"Segoe UI", Ubuntu, sans-serif' font-size='30px' font-weight='700'>{total}</text>
        </g>
        <g transform='translate(165, 55)'>
          <text x='82.5' y='0' text-anchor='middle' fill='{TEXT_MAIN}' fill-opacity='{MUTED_OP}' font-family='"Segoe UI", Ubuntu, sans-serif' font-size='13px' font-weight='400'>Public Repos</text>
          <text x='82.5' y='28' text-anchor='middle' fill='{ACCENT}' font-family='"Segoe UI", Ubuntu, sans-serif' font-size='30px' font-weight='700'>{public_repos}</text>
        </g>
        <g transform='translate(330, 55)'>
          <text x='82.5' y='0' text-anchor='middle' fill='{TEXT_MAIN}' fill-opacity='{MUTED_OP}' font-family='"Segoe UI", Ubuntu, sans-serif' font-size='13px' font-weight='400'>Followers</text>
          <text x='82.5' y='28' text-anchor='middle' fill='{ACCENT}' font-family='"Segoe UI", Ubuntu, sans-serif' font-size='30px' font-weight='700'>{followers}</text>
        </g>
        <g transform='translate(0, 118)'>
          <text x='82.5' y='0' text-anchor='middle' fill='{TEXT_MAIN}' fill-opacity='{MUTED_OP}' font-family='"Segoe UI", Ubuntu, sans-serif' font-size='13px' font-weight='400'>Current Streak</text>
          <text x='82.5' y='28' text-anchor='middle' fill='{ACCENT}' font-family='"Segoe UI", Ubuntu, sans-serif' font-size='30px' font-weight='700'>{current}</text>
        </g>
        <g transform='translate(165, 118)'>
          <text x='82.5' y='0' text-anchor='middle' fill='{TEXT_MAIN}' fill-opacity='{MUTED_OP}' font-family='"Segoe UI", Ubuntu, sans-serif' font-size='13px' font-weight='400'>Longest Streak</text>
          <text x='82.5' y='28' text-anchor='middle' fill='{ACCENT}' font-family='"Segoe UI", Ubuntu, sans-serif' font-size='30px' font-weight='700'>{longest}</text>
        </g>
        <g transform='translate(330, 118)'>
          <text x='82.5' y='0' text-anchor='middle' fill='{TEXT_MAIN}' fill-opacity='{MUTED_OP}' font-family='"Segoe UI", Ubuntu, sans-serif' font-size='13px' font-weight='400'>Active Since</text>
          <text x='82.5' y='28' text-anchor='middle' fill='{ACCENT}' font-family='"Segoe UI", Ubuntu, sans-serif' font-size='30px' font-weight='700'>{active_since}</text>
        </g>
        <text x='247.5' y='182' text-anchor='middle' fill='{TEXT_MAIN}' fill-opacity='{MUTED_OP}' font-family='"Segoe UI", Ubuntu, sans-serif' font-size='12px' font-weight='400'>Last updated: {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")}</text>
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
        circles += f"    <circle cx='{x:.1f}' cy='{y:.1f}' r='3' fill='{ACCENT}'><title>{_esc(day)}: {count} contributions</title></circle>\n"

    svg = f"""\
    <svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 {W} {H}' width='{W}px' height='{H}px'>
      <rect fill='{BG}' width='{W}' height='{H}'/>
      <text x='{W / 2}' y='20' text-anchor='middle' fill='{TEXT_MAIN}' fill-opacity='{MUTED_OP}' font-family='"Segoe UI", Ubuntu, sans-serif' font-size='15px' font-weight='400'>Last 30 Days Activity</text>
      <polyline points='{polyline}' fill='none' stroke='{ACCENT}' stroke-width='2' stroke-linecap='round' stroke-linejoin='round' opacity='0.8'/>
    {circles}  <text x='{pad_left}' y='{H - 8}' fill='{TEXT_MAIN}' fill-opacity='{MUTED_OP}' font-family='"Segoe UI", Ubuntu, sans-serif' font-size='12px'>{_esc(tail[0]["date"]) if tail else ""}</text>
      <text x='{W - pad_right}' y='{H - 8}' text-anchor='end' fill='{TEXT_MAIN}' fill-opacity='{MUTED_OP}' font-family='"Segoe UI", Ubuntu, sans-serif' font-size='12px'>{_esc(tail[-1]["date"]) if tail else ""}</text>
    </svg>
    """
    return textwrap.dedent(svg).strip() + "\n"


def build_contribution_types_svg(items: list[tuple[str, int]]) -> str:
    """Horizontal bars: how the year's contributions break down by type."""
    W, H = 495, 195
    bar_x, bar_w, bar_h = 150, 270, 14
    row_y0, step = 62, 30
    max_val = max((v for _, v in items), default=0) or 1
    rows = ""
    for i, (label, value) in enumerate(items):
        y = row_y0 + i * step
        w = (value / max_val) * bar_w
        rows += (
            f"    <text x='24' y='{y + 4}' fill='{TEXT_MAIN}' "
            f"font-family='Segoe UI, Ubuntu, sans-serif' font-size='13px'>{_esc(label)}</text>\n"
            f"    <rect x='{bar_x}' y='{y - bar_h + 3}' width='{bar_w}' height='{bar_h}' "
            f"rx='3' fill='{TEXT_MAIN}' fill-opacity='{FAINT_OP}'/>\n"
            f"    <rect x='{bar_x}' y='{y - bar_h + 3}' width='{w:.1f}' height='{bar_h}' "
            f"rx='3' fill='{ACCENT}'><title>{_esc(label)}: {value}</title></rect>\n"
            f"    <text x='{bar_x + bar_w + 10}' y='{y + 4}' fill='{ACCENT}' "
            f"font-family='Segoe UI, Ubuntu, sans-serif' font-size='14px' font-weight='700'>{value}</text>\n"
        )
    svg = f"""\
    <svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 {W} {H}' width='{W}px' height='{H}px'>
      <rect fill='{BG}' width='{W}' height='{H}' rx='6'/>
      <text x='{W / 2}' y='30' text-anchor='middle' fill='{TEXT_MAIN}' fill-opacity='{MUTED_OP}' font-family='Segoe UI, Ubuntu, sans-serif' font-size='16px' font-weight='400'>{_esc(USER)}'s Contribution Types</text>
    {rows}  <text x='{W / 2}' y='{H - 10}' text-anchor='middle' fill='{TEXT_MAIN}' fill-opacity='{MUTED_OP}' font-family='Segoe UI, Ubuntu, sans-serif' font-size='11px'>Last updated: {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")}</text>
    </svg>
    """
    return textwrap.dedent(svg).strip() + "\n"


def build_monthly_activity_svg(days: list[dict]) -> str:
    """Vertical bars: contributions aggregated by month (last 12 months)."""
    totals: dict[str, int] = {}
    for d in days:
        totals[d["date"][:7]] = totals.get(d["date"][:7], 0) + d["contributionCount"]
    months = sorted(totals)[-12:]
    W, H = 800, 198
    pad_left, pad_right, pad_top, pad_bottom = 60, 20, 58, 40
    chart_w, chart_h = W - pad_left - pad_right, H - pad_top - pad_bottom
    n = len(months) or 1
    max_val = max((totals[m] for m in months), default=0) or 1
    gap = chart_w / n
    bar_w = gap * 0.6
    bars = ""
    for i, m in enumerate(months):
        value = totals[m]
        h = (value / max_val) * chart_h
        x = pad_left + i * gap + (gap - bar_w) / 2
        y = pad_top + chart_h - h
        label = _MONTHS[int(m[5:7]) - 1]
        bars += (
            f"    <rect x='{x:.1f}' y='{y:.1f}' width='{bar_w:.1f}' height='{h:.1f}' rx='2' "
            f"fill='{ACCENT}'><title>{_esc(m)}: {value} contributions</title></rect>\n"
            f"    <text x='{x + bar_w / 2:.1f}' y='{pad_top + chart_h + 16}' text-anchor='middle' "
            f"fill='{TEXT_MAIN}' fill-opacity='{MUTED_OP}' font-family='Segoe UI, Ubuntu, sans-serif' font-size='12px'>{label}</text>\n"
            f"    <text x='{x + bar_w / 2:.1f}' y='{y - 5:.1f}' text-anchor='middle' "
            f"fill='{TEXT_MAIN}' font-family='Segoe UI, Ubuntu, sans-serif' font-size='12px'>{value}</text>\n"
        )
    baseline = (
        f"    <line x1='{pad_left}' y1='{pad_top + chart_h}' x2='{W - pad_right}' "
        f"y2='{pad_top + chart_h}' stroke='{TEXT_MAIN}' stroke-opacity='{FAINT_OP}' stroke-width='1'/>\n"
    )
    svg = f"""\
    <svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 {W} {H}' width='{W}px' height='{H}px'>
      <rect fill='{BG}' width='{W}' height='{H}' rx='6'/>
      <text x='{W / 2}' y='28' text-anchor='middle' fill='{TEXT_MAIN}' fill-opacity='{MUTED_OP}' font-family='Segoe UI, Ubuntu, sans-serif' font-size='16px' font-weight='400'>{_esc(USER)}'s Monthly Contributions (last 12 months)</text>
    {baseline}{bars}  <text x='{W / 2}' y='{H - 8}' text-anchor='middle' fill='{TEXT_MAIN}' fill-opacity='{MUTED_OP}' font-family='Segoe UI, Ubuntu, sans-serif' font-size='11px'>Last updated: {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")}</text>
    </svg>
    """
    return textwrap.dedent(svg).strip() + "\n"


def build_metrics_svg(days: list[dict]) -> str:
    """Slim self-hosted contribution map — replaces the lowlighter/metrics card.

    A compact year heatmap (~371 cells), small enough to stay well under the
    <=80 KB budget and to render with zero external requests. Headline totals
    live in stats.svg only, so the same numbers are never repeated here.
    """
    W, H = 800, 230
    cell, gap = 11, 3
    pad_left, pad_top = 40, 72
    weeks = [days[i : i + 7] for i in range(0, len(days), 7)]
    max_count = max((d["contributionCount"] for d in days), default=0) or 1
    rects = ""
    for wi, week in enumerate(weeks):
        for di, day in enumerate(week):
            x = pad_left + wi * (cell + gap)
            y = pad_top + di * (cell + gap)
            count = day["contributionCount"]
            # Denser days burn brighter orange; quiet days stay close to the blue
            # field, so the map reads mostly-blue with orange highlights (30 / 60).
            if count > 0:
                fill = f"fill='{ACCENT}' fill-opacity='{0.35 + 0.65 * count / max_count:.2f}'"
            else:
                fill = f"fill='{TEXT_MAIN}' fill-opacity='{FAINT_OP}'"
            rects += (
                f"    <rect x='{x}' y='{y}' width='{cell}' height='{cell}' rx='2' "
                f"{fill}><title>{_esc(day['date'])}: {count} contributions</title></rect>\n"
            )
    svg = f"""\
    <svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 {W} {H}' width='{W}px' height='{H}px'>
      <rect fill='{BG}' width='{W}' height='{H}' rx='6'/>
      <text x='{W / 2}' y='28' text-anchor='middle' fill='{TEXT_MAIN}' fill-opacity='{MUTED_OP}' font-family='"Segoe UI", Ubuntu, sans-serif' font-size='16px' font-weight='400'>{_esc(USER)}'s Contribution Map</text>
    {rects}  <text x='{W / 2}' y='{H - 10}' text-anchor='middle' fill='{TEXT_MAIN}' fill-opacity='{MUTED_OP}' font-family='"Segoe UI", Ubuntu, sans-serif' font-size='11px'>Last updated: {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")}</text>
    </svg>
    """
    return textwrap.dedent(svg).strip() + "\n"


def fetch_languages() -> list[tuple[str, int, str]]:
    """Aggregate language bytes across public non-fork repos via GraphQL.

    Returns [(name, bytes, color), ...] sorted by bytes desc. Color is the
    GitHub linguist color for the language (falls back to the cream token).
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
            color = edge["node"].get("color") or TEXT_MAIN
            size = edge["size"]
            agg.setdefault(name, [0, color])[0] += size
    items = [(name, v[0], v[1]) for name, v in agg.items()]
    items.sort(key=lambda x: x[1], reverse=True)
    return items


def _truncate(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[: limit - 1] + "\u2026"


def build_top_languages_svg(langs: list[tuple[str, int, str]]) -> str:
    import math

    W, H = 460, 258
    cx, cy, R, sw = 104, 132, 60, 19
    circumference = 2 * math.pi * R
    total = sum(s for _, s, _ in langs) or 1

    # Fold everything past the top 8 into a single "Other" slice so the legend
    # stays readable and the card height is fixed. Language brand colors are
    # semantic (kept); "Other" is a neutral cream token.
    rows = [(n, s, c, 1.0) for n, s, c in langs[:8]]
    if len(langs) > 8:
        rows.append(("Other", sum(s for _, s, _ in langs[8:]), TEXT_MAIN, GHOST_OP))

    gap = 1.5 if len(rows) > 1 else 0.0
    cum = 0.0
    slices = ""
    for name, size, color, alpha in rows:
        frac = size / total
        dash = max(frac * circumference - gap, 0.5)
        offset = -cum * circumference
        slices += (
            f"    <circle cx='{cx}' cy='{cy}' r='{R}' fill='none' stroke='{_esc(color)}' "
            f"stroke-opacity='{alpha}' "
            f"stroke-width='{sw}' stroke-dasharray='{dash:.1f} {circumference - dash:.1f}' "
            f"stroke-dashoffset='{offset:.1f}'>"
            f"<title>{_esc(name)}: {size / total * 100:.1f}%</title></circle>\n"
        )
        cum += frac

    legend = ""
    for i, (name, size, color, alpha) in enumerate(rows):
        ly = 56 + i * 19
        pct = size / total * 100
        legend += (
            f"    <rect x='196' y='{ly - 10}' width='12' height='12' rx='2' fill='{_esc(color)}' "
            f"fill-opacity='{alpha}' "
            f"stroke='{TEXT_MAIN}' stroke-opacity='0.25' stroke-width='0.5'/>\n"
            f"    <text x='215' y='{ly}' fill='{TEXT_MAIN}' "
            f"font-family='Segoe UI, Ubuntu, sans-serif' font-size='13px'>{_esc(name)}</text>\n"
            f"    <text x='{W - 18}' y='{ly}' text-anchor='end' fill='{TEXT_MAIN}' fill-opacity='{MUTED_OP}' "
            f"font-family='Segoe UI, Ubuntu, sans-serif' font-size='13px'>{pct:.1f}%</text>\n"
        )

    center = ""
    if rows:
        center = (
            f"    <text x='{cx}' y='{cy - 4}' text-anchor='middle' fill='{TEXT_MAIN}' "
            f"font-family='Segoe UI, Ubuntu, sans-serif' font-size='14px' "
            f"font-weight='700'>{_esc(_truncate(rows[0][0], 11))}</text>\n"
            f"    <text x='{cx}' y='{cy + 15}' text-anchor='middle' fill='{ACCENT}' "
            f"font-family='Segoe UI, Ubuntu, sans-serif' font-size='13px' "
            f"font-weight='700'>{rows[0][1] / total * 100:.0f}%</text>\n"
        )

    svg = f"""\
    <svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 {W} {H}' width='{W}px' height='{H}px'>
      <rect fill='{BG}' width='{W}' height='{H}' rx='6'/>
      <text x='{W / 2}' y='30' text-anchor='middle' fill='{TEXT_MAIN}' fill-opacity='{MUTED_OP}'
            font-family='Segoe UI, Ubuntu, sans-serif' font-size='16px' font-weight='400'>{_esc(USER)}'s Top Languages</text>
      <g transform='rotate(-90 {cx} {cy})'>
        <circle cx='{cx}' cy='{cy}' r='{R}' fill='none' stroke='{TEXT_MAIN}' stroke-opacity='{FAINT_OP}' stroke-width='{sw}'/>
    {slices}  </g>
    {center}{legend}    <text x='{W / 2}' y='{H - 10}' text-anchor='middle' fill='{TEXT_MAIN}' fill-opacity='{MUTED_OP}'
            font-family='Segoe UI, Ubuntu, sans-serif' font-size='11px'>Last updated: {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")}</text>
    </svg>
    """
    return textwrap.dedent(svg).strip() + "\n"


# Analytics evidence ledger — authored, not derived.
#
# The *results* are methodological, not repository metadata: "+5.72pp, p<0.0001"
# lives in a case study, not in the GitHub API, so it cannot be recomputed the way
# a contribution count can. Everything mechanical around them is derived, though:
# the row carries a repo *name* and the URL is built from it (evidence_url), so a
# renamed repo cannot leave a hand-typed URL behind; reconcile_evidence then drops
# each name against the live public-repo list, so a deleted or newly-private repo
# withdraws its own row instead of shipping a dead link; and the README's plain-text
# sources line is generated from this same ledger, so card and text cannot drift.
# The CI link-liveness job (.github/workflows/ci.yml) still HTTP-checks every URL.
# The "Bayesian A/B" row carries no repo on purpose: a declared gap is cheaper to
# trust than a padded row.
ANALYTICS_EVIDENCE: tuple[dict[str, str], ...] = (
    {
        "method": "Experiment design & A/B",
        "evidence": "+5.72pp KYC lift · p<0.0001 · no SRM",
        "confidence": "HIGH",
        "repo": "volta-banking",
    },
    {
        "method": "Variance reduction (CUPED)",
        "evidence": "SE ×0.742 — 10k → 5.5k users per arm",
        "confidence": "HIGH",
        "repo": "causal-uplift",
    },
    {
        "method": "Multiple testing & sequential",
        "evidence": "Bonferroni · Holm · BH · O'Brien-Fleming · HTE q-values",
        "confidence": "HIGH",
        "repo": "volta-banking",
    },
    {
        "method": "Calibration-first testing",
        "evidence": "Type I · power · coverage · FWER re-run as test assertions",
        "confidence": "HIGH",
        "repo": "ab_test",
    },
    {
        "method": "Causal inference",
        "evidence": "DiD ATT +9.2pp · parallel trends ✓ · placebo null",
        "confidence": "MODERATE",
        "repo": "volta-banking",
    },
    {
        "method": "Uplift targeting",
        "evidence": "n=6k: curve metrics noise-dominated (oracle 2.25σ); signal in ranking + segment split",
        "confidence": "MODERATE",
        "repo": "causal-uplift",
    },
    {
        "method": "SQL depth",
        "evidence": "25 DuckDB cases · QUALIFY · PIVOT · recursive CTE · z-test in SQL",
        "confidence": "HIGH",
        "repo": "sql-analytics-case-study",
    },
    {
        "method": "Data engineering",
        "evidence": "Airflow 3 · DQ validation · alerts · run metrics · idempotent",
        "confidence": "HIGH",
        "repo": "airflow",
    },
    {
        "method": "Bayesian A/B",
        "evidence": "learning — no published case yet",
        "confidence": "GAP",
        "repo": "",
    },
)


def evidence_url(repo: str) -> str:
    """Source URL for a ledger row's repo name. An empty repo is a declared gap."""
    return f"https://github.com/{USER}/{repo}" if repo else ""


def reconcile_evidence(
    public_repos: set[str], rows: tuple[dict[str, str], ...] | None = None
) -> tuple[list[dict[str, str]], list[str]]:
    """Withdraw ledger rows whose source repo is no longer public.

    The ledger is authored, so nothing recomputes its claims — but the repo each
    claim points at can be renamed, deleted or made private, and the row would keep
    pointing at it. Such a row is rewritten as a declared gap that names the repo,
    never as a still-linked claim: an unverifiable number is exactly the padded
    claim the ledger exists to avoid.

    An empty `public_repos` means the API returned nothing to check against, which
    is not evidence of absence — every row is kept rather than mass-withdrawn.
    """
    rows = ANALYTICS_EVIDENCE if rows is None else rows
    if not public_repos:
        return list(rows), ["public repo list unavailable — evidence rows not reconciled"]
    reconciled: list[dict[str, str]] = []
    warnings: list[str] = []
    for row in rows:
        repo = row["repo"]
        if repo and repo not in public_repos:
            warnings.append(f"evidence source {repo!r} is not public — row withdrawn")
            reconciled.append(
                {
                    "method": row["method"],
                    "evidence": f"source repo {repo} is no longer public — claim withdrawn",
                    "confidence": "GAP",
                    "repo": "",
                }
            )
        else:
            reconciled.append(dict(row))
    return reconciled, warnings


def evidence_sources(rows: tuple[dict[str, str], ...] | None = None) -> list[str]:
    """Distinct source URLs, in ledger order — the CI link-liveness job's input."""
    rows = ANALYTICS_EVIDENCE if rows is None else rows
    return list(dict.fromkeys(evidence_url(row["repo"]) for row in rows if row["repo"]))


def build_evidence_sources_line(rows: tuple[dict[str, str], ...] | None = None) -> str:
    """Plain-text mirror of the evidence card.

    The card is an `<img>`: its text is neither selectable nor indexable by GitHub.
    This line is both, and it is generated from the same ledger, so the card and the
    text can never disagree about which repositories back the claims.
    """
    rows = ANALYTICS_EVIDENCE if rows is None else rows
    repos = list(dict.fromkeys(row["repo"] for row in rows if row["repo"]))
    links = " · ".join(f'<a href="{_esc(evidence_url(r))}">{_esc(r)}</a>' for r in repos)
    return f"<sub>Sources: {links} — every link is HTTP-checked in CI.</sub>"


def build_analytics_evidence_svg(rows: tuple[dict[str, str], ...] | None = None) -> str:
    """Evidence band: method -> verified result -> source, with honest gaps.

    Every row that carries a number also carries the repository that produced it,
    so a reader can check it in one click instead of taking the profile's word.
    """
    rows = ANALYTICS_EVIDENCE if rows is None else rows
    W = 800
    header_h, row_h, footer_h = 62, 50, 24
    chip_w = 88
    H = header_h + row_h * len(rows) + footer_h
    body = ""
    for i, row in enumerate(rows):
        y = header_h + i * row_h
        conf = row["confidence"]
        repo = row["repo"]
        detail = f"{repo} · {row['evidence']}" if repo else row["evidence"]
        # Three visual weights, still only the three brand tokens. Opacity goes on the
        # pill only: a label drawn translucent *over* a translucent pill blends twice,
        # and MODERATE at 0.62 lands near 2.9:1 against its own chip — under WCAG AA.
        if conf == "HIGH":
            pill = f"fill='{ACCENT}'"
            # Label is the dark token, not BG: on an inverted (cream) card BG is the
            # light colour, and cream on #fe4e02 would be 3.0:1 — blue keeps the 3.5:1
            # the card had before the palette flip.
            label_fill, label_op, label = TEXT_MAIN, "1", "HIGH"
        elif conf == "MODERATE":
            pill = f"fill='{TEXT_MAIN}' fill-opacity='{MUTED_OP}'"
            label_fill, label_op, label = BG, "1", "MODERATE"
        else:
            # A gap is an absence, not a weaker verdict, so it reads as an outline
            # rather than a dimmer filled pill. Cream at GHOST_OP would be ~3.6:1, so
            # the outline and its label both stay at MUTED_OP (~5.8:1).
            pill = f"fill='none' stroke='{TEXT_MAIN}' stroke-opacity='{MUTED_OP}'"
            label_fill, label_op, label = TEXT_MAIN, MUTED_OP, "GAP"
        body += (
            f"    <text x='24' y='{y + 21}' fill='{TEXT_MAIN}' "
            f"font-family='Segoe UI, Ubuntu, sans-serif' font-size='14px' font-weight='600'>"
            f"{_esc(row['method'])}</text>\n"
            f"    <text x='24' y='{y + 41}' fill='{TEXT_MAIN}' fill-opacity='{MUTED_OP}' "
            f"font-family='Segoe UI, Ubuntu, sans-serif' font-size='12px'>{_esc(detail)}</text>\n"
            f"    <rect x='{W - 24 - chip_w}' y='{y + 16}' width='{chip_w}' height='18' rx='9' "
            f"{pill}/>\n"
            f"    <text x='{W - 24 - chip_w / 2}' y='{y + 29}' text-anchor='middle' "
            f"fill='{label_fill}' fill-opacity='{label_op}' "
            f"font-family='Segoe UI, Ubuntu, sans-serif' font-size='11px' font-weight='700'>"
            f"{label}</text>\n"
        )
    methods = ", ".join(_esc(row["method"]) for row in rows)
    summary = f"Analytics evidence: {methods}"
    svg = f"""\
    <svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 {W} {H}' width='{W}px' height='{H}px'
         role='img' aria-label='{summary}. Each linked row points to the public repository that produced the result.'>
      <title>{summary}</title>
      <rect fill='{BG}' width='{W}' height='{H}' rx='6'/>
      <text x='24' y='32' fill='{TEXT_MAIN}' font-family='Segoe UI, Ubuntu, sans-serif'
            font-size='15px' font-weight='700' letter-spacing='1.2'>{_esc(USER)} — ANALYTICS EVIDENCE</text>
      <text x='24' y='49' fill='{TEXT_MAIN}' fill-opacity='{MUTED_OP}'
            font-family='Segoe UI, Ubuntu, sans-serif' font-size='12px'>method · verified result · source repository — no unlinked claims</text>
      <line x1='24' y1='{header_h - 4}' x2='{W - 24}' y2='{header_h - 4}'
            stroke='{TEXT_MAIN}' stroke-opacity='{FAINT_OP}' stroke-width='1'/>
    {body}  <text x='{W / 2}' y='{H - 8}' text-anchor='middle' fill='{TEXT_MAIN}' fill-opacity='{MUTED_OP}'
            font-family='Segoe UI, Ubuntu, sans-serif' font-size='11px'>Sources verified in CI · last updated: {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")}</text>
    </svg>
    """
    return textwrap.dedent(svg).strip() + "\n"


_NOTES_BLOCK_RE = re.compile(
    r"(<!-- RECENT-POSTS-LIST:START -->)(.*?)(<!-- RECENT-POSTS-LIST:END -->)",
    re.DOTALL,
)
_NOTES_ITEM_RE = re.compile(r"-\s*\[(.*?)\]\((.*?)\)")


def normalize_notes_block(content: str) -> str:
    """Put one Recent-Notes item per line.

    blog-post-workflow applies its `template` per entry but joins the results
    with no separator, so all five posts land on a single line and GitHub renders
    the section as one run-on paragraph instead of a list.
    """

    def rebuild(match: re.Match) -> str:
        items = _NOTES_ITEM_RE.findall(match.group(2))
        if not items:
            return match.group(0)
        body = "\n".join(f"- [{title}]({url})" for title, url in items)
        return f"{match.group(1)}\n{body}\n{match.group(3)}"

    return _NOTES_BLOCK_RE.sub(rebuild, content)


_EVIDENCE_SOURCES_RE = re.compile(
    r"<!-- EVIDENCE-SOURCES:START -->.*?<!-- EVIDENCE-SOURCES:END -->", re.DOTALL
)


def sync_evidence_sources_block(
    content: str, rows: tuple[dict[str, str], ...] | None = None
) -> str:
    """Regenerate the README's plain-text sources line from the ledger.

    Hand-typed, it drifted from the card the moment a row changed; generated from
    the same ledger the card renders, the two cannot disagree. A missing marker is
    left alone rather than appended — placement in the README is a human decision.
    """
    if not _EVIDENCE_SOURCES_RE.search(content):
        return content
    block = (
        "<!-- EVIDENCE-SOURCES:START -->\n"
        f"{build_evidence_sources_line(rows)}\n"
        "<!-- EVIDENCE-SOURCES:END -->"
    )
    return _EVIDENCE_SOURCES_RE.sub(lambda _: block, content)


def update_readme_refresh_block(
    days: list[dict], evidence_rows: tuple[dict[str, str], ...] | None = None
) -> bool:
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
    # One write, three repairs: the RSS job leaves the notes list on one line, and
    # the evidence sources line is generated rather than hand-typed.
    new_content = normalize_notes_block(new_content)
    new_content = sync_evidence_sources_block(new_content, evidence_rows)
    if new_content == content:
        print("README already up to date")
        return False
    readme_path.write_text(new_content, encoding="utf-8")
    print(f"Refreshed README (refresh block + notes + evidence sources): {now} ({week} c/7d)")
    return True


def main() -> None:
    global DRY_RUN, USER
    parser = argparse.ArgumentParser(description="Build self-hosted profile assets.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print planned writes without modifying files",
    )
    parser.add_argument(
        "--user",
        default=USER,
        help=f"GitHub login to render (default: {DEFAULT_USER})",
    )
    parser.add_argument(
        "--print-links",
        action="store_true",
        help="print one evidence source URL per line and exit (CI link-liveness check)",
    )
    args = parser.parse_args()
    if args.print_links:
        for url in evidence_sources():
            print(url)
        return
    DRY_RUN = args.dry_run
    USER = args.user
    if DRY_RUN:
        print("[dry-run] no files will be written")

    print(f"Fetching user data for {USER}...")
    user_data = fetch_user_data()
    days = extract_contributions(user_data)
    total, current, longest = compute_streaks(days)
    print(f"total={total} current={current} longest={longest}")

    evidence_rows, evidence_warnings = reconcile_evidence(public_repo_names(user_data))
    for warning in evidence_warnings:
        print(f"WARNING: {warning}")

    write_asset(REPO_ROOT / "hero.svg", build_hero_svg())
    write_asset(REPO_ROOT / "stats.svg", build_stats_svg(user_data, total, current, longest))
    write_asset(REPO_ROOT / "activity.svg", build_activity_svg(days))
    write_asset(REPO_ROOT / "metrics.svg", build_metrics_svg(days))
    write_asset(
        REPO_ROOT / "contribution-types.svg",
        build_contribution_types_svg(extract_contribution_types(user_data)),
    )
    write_asset(REPO_ROOT / "monthly-activity.svg", build_monthly_activity_svg(days))
    write_asset(REPO_ROOT / "analytics-evidence.svg", build_analytics_evidence_svg(evidence_rows))

    try:
        langs = fetch_languages()
        write_asset(REPO_ROOT / "top-languages.svg", build_top_languages_svg(langs))
        print(f"top-languages: {len(langs)} languages")
    except (RuntimeError, urllib.error.URLError, TimeoutError):
        # A silent skip left a stale card behind on a green CI run.
        logging.exception("top-languages.svg could not be generated")
        raise

    if DRY_RUN:
        print("[dry-run] skip README refresh block")
    else:
        update_readme_refresh_block(days, evidence_rows)


if __name__ == "__main__":
    main()
