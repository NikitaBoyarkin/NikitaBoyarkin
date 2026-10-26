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

Network calls retry transient GitHub failures (5xx / 429 / timeout) with capped
exponential backoff; a persistent outage is logged and skipped rather than
failing the scheduled refresh. Use --dry-run to preview planned writes without
touching files.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import random
import re
import sys
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
        # ElementTree parses a root element in *no* namespace without complaint, so
        # this gate once waved through a namespace-less card; assert the document is
        # actually an SVG one, not merely well-formed XML.
        root = ET.fromstring(content)
        if root.tag != f"{{{SVG_NS}}}svg":
            raise ValueError(f"{path.name}: root element is {root.tag!r}, not an SVG document")
    if DRY_RUN:
        print(f"[dry-run] would write {path.name} ({len(content)} chars)")
        return
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    os.replace(tmp, path)
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

# Browsers parse a served .svg as XML: a root element outside this namespace is
# not an SVG document, and the card renders as a broken image whose alt text leaks.
SVG_NS = "http://www.w3.org/2000/svg"


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
    a real number here would be an unlinked claim in the header, which is the
    failure mode this profile avoids.
    """
    W, H = 800, 220
    alt = f"{HERO_NAME} — {HERO_ROLE}. {HERO_TAGLINE[0]} {HERO_TAGLINE[1]}"
    desc = (
        "Header banner: name, role, a one-line positioning statement, and a "
        "schematic A/B lift motif."
    )
    tagline = "".join(
        f"      <text x='40' y='{146 + i * 22}' fill='{TEXT_MAIN}' fill-opacity='{MUTED_OP}' "
        f"font-family='Segoe UI, Ubuntu, sans-serif' font-size='15px'>{_esc(line)}</text>\n"
        for i, line in enumerate(HERO_TAGLINE)
    )
    svg = f"""\
    <svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 {W} {H}' width='{W}' height='{H}'
         role='img' aria-label='{_esc(alt)}'>
      <title>{_esc(alt)}</title>
      <desc>{_esc(desc)}</desc>
      <rect fill='{BG}' width='{W}' height='{H}' rx='8'/>
      <text x='40' y='64' fill='{TEXT_MAIN}' font-family='Segoe UI, Ubuntu, sans-serif'
            font-size='34px' font-weight='800' letter-spacing='1.5'>{_esc(HERO_NAME)}</text>
      <text x='40' y='99' fill='{ACCENT}' font-family='Segoe UI, Ubuntu, sans-serif'
            font-size='16px' font-weight='700' letter-spacing='2.6'>{_esc(HERO_ROLE)}</text>
      <line x1='40' y1='117' x2='360' y2='117' stroke='{TEXT_MAIN}' stroke-opacity='{FAINT_OP}' stroke-width='1'/>
{tagline}      <text x='40' y='199' fill='{TEXT_MAIN}' fill-opacity='{MUTED_OP}'
            font-family='Segoe UI, Ubuntu, sans-serif' font-size='12px' font-weight='600'>{_esc(HERO_STRIP)}</text>
      <line x1='490' y1='40' x2='490' y2='180' stroke='{TEXT_MAIN}' stroke-opacity='{FAINT_OP}' stroke-width='1'/>
      <text x='647' y='56' text-anchor='middle' fill='{ACCENT}'
            font-family='Segoe UI, Ubuntu, sans-serif' font-size='12px' font-weight='700'>+lift</text>
      <rect x='584' y='112' width='50' height='58' rx='3' fill='{TEXT_MAIN}' fill-opacity='0.26'/>
      <rect x='660' y='84' width='50' height='86' rx='3' fill='{ACCENT}'/>
      <line x1='550' y1='170' x2='744' y2='170' stroke='{TEXT_MAIN}' stroke-opacity='{FAINT_OP}' stroke-width='1'/>
      <text x='609' y='188' text-anchor='middle' fill='{TEXT_MAIN}' fill-opacity='{MUTED_OP}'
            font-family='Segoe UI, Ubuntu, sans-serif' font-size='12px' font-weight='600'>A</text>
      <text x='685' y='188' text-anchor='middle' fill='{TEXT_MAIN}' fill-opacity='{MUTED_OP}'
            font-family='Segoe UI, Ubuntu, sans-serif' font-size='12px' font-weight='600'>B</text>
    </svg>
    """
    return textwrap.dedent(svg).strip() + "\n"


class GitHubUnavailable(RuntimeError):
    """The GitHub API stayed unreachable (5xx / timeout) after every retry.

    Distinct from a plain ``RuntimeError`` so a caller can treat a transient
    upstream outage differently from a real config error (bad token, bad query).
    """


# HTTP statuses worth retrying: edge/gateway failures and rate limits.
_TRANSIENT_HTTP = frozenset({408, 429, 500, 502, 503, 504})


def graphql(query: str, variables: dict, retries: int = 6) -> dict:
    """POST a GraphQL query, retrying transient GitHub failures with backoff.

    A 5xx / 429 / timeout is transient: the request is retried up to ``retries``
    times with capped exponential backoff plus jitter (honouring ``Retry-After``
    when the API sends it). A 4xx other than 429 is permanent — a bad token or a
    bad query will not heal — so it fails fast. When every attempt is transient,
    ``GitHubUnavailable`` is raised so the caller can tell an upstream outage
    apart from a real config error.
    """
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
        except urllib.error.HTTPError as exc:
            # GitHub reports primary rate limiting as 403, not 429; only that
            # flavour is transient — any other 403 is a bad token and must fail.
            rate_limited = exc.code == 403 and (
                (exc.headers or {}).get("X-RateLimit-Remaining") == "0"
            )
            if exc.code not in _TRANSIENT_HTTP and not rate_limited:
                raise
            last_exc = exc
        except (urllib.error.URLError, TimeoutError) as exc:
            last_exc = exc
        except (json.JSONDecodeError, KeyError) as exc:
            # A 200 carrying an HTML error page or a truncated body: retryable.
            last_exc = exc
        if attempt == retries:
            break
        wait = min(2 ** (attempt - 1), 30)
        headers = getattr(last_exc, "headers", None)
        retry_after = headers.get("Retry-After") if headers else None
        if retry_after and str(retry_after).isdigit():
            wait = max(wait, int(retry_after))
        wait += random.uniform(0, 1)
        print(f"GraphQL attempt {attempt}/{retries} failed: {last_exc}; retrying in {wait:.1f}s")
        time.sleep(wait)
    raise GitHubUnavailable(f"GitHub API unreachable after {retries} attempts: {last_exc}")


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
    # Name is the tie-break so equal byte counts keep a stable order; the repo
    # order from the API is UPDATED_AT, which changes between runs.
    items.sort(key=lambda x: (-x[1], x[0]))
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


# Project registry — the portfolio site publishes every project as JSON, and the
# profile renders that same registry so the README and the site can never disagree
# about which projects exist. The site owns the list; this only formats it.
PROJECTS_REGISTRY_URL = (
    "https://raw.githubusercontent.com/NikitaBoyarkin/"
    "NikitaBoyarkin.github.io/master/public/projects.json"
)

PROJECTS_SVG_NAME = "projects.svg"
PROJECTS_SVG_URL = (
    "https://raw.githubusercontent.com/NikitaBoyarkin/NikitaBoyarkin/main/projects.svg"
)

ALL_PROJECTS_START = "<!-- ALL-PROJECTS:START -->"
ALL_PROJECTS_END = "<!-- ALL-PROJECTS:END -->"

# Site tracks rendered in this order; unknown tracks are ignored, not guessed.
TRACK_ORDER = ("experiments", "analytics", "product", "engineering")

# ASCII-only labels: emoji are dropped because a screen reader reads them verbatim
# ("test tube Experiments"), and the vector card has no emoji font. The README rows
# use the same plain words, so one track name serves both surfaces.
TRACK_PLAIN_LABELS = {
    "experiments": "Experiments",
    "analytics": "Analytics",
    "product": "Product",
    "engineering": "Engineering",
}


def fetch_projects_registry(url: str = PROJECTS_REGISTRY_URL, retries: int = 3) -> dict:
    """GET the project registry JSON, retrying transient network failures.

    Mirrors the ``graphql()`` backoff idiom. Any failure — network, non-200, or
    malformed JSON — surfaces as ``RuntimeError`` so the caller can leave the
    README untouched instead of shipping a half-rendered block.
    """
    last_exc: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "build_profile"})
            with urllib.request.urlopen(req, timeout=60) as resp:
                status = getattr(resp, "status", 200)
                if status != 200:
                    raise RuntimeError(f"registry returned HTTP {status}")
                return json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
            last_exc = exc
            if attempt == retries:
                break
            wait = 2 ** (attempt - 1)
            print(f"registry attempt {attempt}/{retries} failed: {exc}; retrying in {wait}s")
            time.sleep(wait)
    raise RuntimeError(f"could not fetch projects registry: {last_exc}")


def load_projects_registry(source: str = PROJECTS_REGISTRY_URL) -> dict:
    """Read the registry from a local path when it exists, else fetch it as a URL."""
    path = Path(source)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return fetch_projects_registry(source)


def _clean_text(value: object) -> str:
    """Collapse runs of whitespace/newlines so a description stays one markdown line."""
    return " ".join(str(value or "").split())


def _pick(record: dict, en_key: str, ru_key: str) -> str:
    """Prefer the EN field, fall back to the RU one.

    The site registry is bilingual (`title`/`title_en`, `description`/`description_en`);
    the profile renders EN to match the rest of the README. The fallback keeps an
    older RU-only registry rendering instead of producing empty bullets.
    """
    return _clean_text(record.get(en_key)) or _clean_text(record.get(ru_key))


def _links(record: dict) -> str:
    """Repo / case-study links for one project, or a declared gap when there are none."""
    github = _clean_text(record.get("github"))
    href = _clean_text(record.get("href"))
    parts: list[str] = []
    # A private repo 404s for anonymous readers, so advertising its URL here (and
    # in the CI liveness list) is a dead link, not a pointer — mark it private.
    if github and not record.get("private"):
        parts.append(f"[Repo]({github})")
    if href:
        parts.append(f"[Case study]({href})")
    if record.get("private"):
        parts.append("_private_")
    return " · ".join(parts) if parts else "—"


_NUMBER_RE = re.compile(r"\d+(?:[.,]\d+)?")

# Tools are a stack signal for a screener, not a manifest: past four they push
# the row past a line and the title stops being the scan anchor.
TOOL_LIMIT = 4


def _row_text(record: dict) -> str:
    """The blurb for one project: its description, plus the result when it adds numbers.

    ``description`` states the scope ("16,891 synthetic calls", "8,000 users") and
    ``result`` states the outcome. On this registry they overlap often: an EN
    description usually already carries the headline numbers, and its RU result twin
    restates them. Appending such a result only doubles the line, so the two number
    sets are compared and the result is kept only when at least half of its numbers
    are new — a screener reads one sentence per project, not two versions of it.
    """
    description = _pick(record, "description_en", "description")
    result = _pick(record, "result_en", "result")
    if not result:
        return description
    if not description:
        return result
    if result in description:
        return description
    described = set(_NUMBER_RE.findall(description))
    measured = set(_NUMBER_RE.findall(result))
    if not measured or len(measured - described) * 2 < len(measured):
        return description
    return f"{description} {result}"


def _project_line(index: int, record: dict, *, with_result: bool = True) -> str:
    """One numbered row: title · track — blurb · tools · links.

    Used for the collapsed Volta appendix, where 23 cards would be length nobody
    scrolls; the visible catalogue uses ``_project_card`` instead.
    """
    title = _pick(record, "title_en", "title")
    href = _clean_text(record.get("href"))
    parts = [f"{index}. **[{title}]({href})**" if href else f"{index}. **{title}**"]
    track = TRACK_PLAIN_LABELS.get(_clean_text(record.get("track")))
    if track:
        parts.append(f"· *{track}*")
    text = _row_text(record) if with_result else _pick(record, "description_en", "description")
    if text:
        parts.append(f"— {text}")
    tools = [_clean_text(tool) for tool in record.get("tools") or [] if _clean_text(tool)]
    if tools:
        parts.append("· " + " · ".join(f"`{tool}`" for tool in tools[:TOOL_LIMIT]))
    links = _links(record)
    if links:
        parts.append(f"· {links}")
    return " ".join(parts)


# Featured-style cards. Only three projects ship a self-hosted logo card; every
# other project gets a text link in the same heading slot, so the card shape
# (linked title — track) stays identical down the catalogue.
LOGO_BY_SLUG = {
    "volta": "volta-neobank.svg",
    "supabase": "supabase-analytics.svg",
    "sql": "sql-case-study.svg",
}

REPO_BADGE = (
    "https://img.shields.io/badge/Repo-{name}-0f2a2b"
    "?style=for-the-badge&logo=github&logoColor=fe4e02"
)
CASE_STUDY_BADGE = "https://img.shields.io/badge/Case_study-fe4e02?style=for-the-badge"


def _badge_escape(value: str) -> str:
    """shields.io static-badge escaping: '-' → '--', '_' → '__', ' ' → '_'."""
    return value.replace("-", "--").replace("_", "__").replace(" ", "_")


def _repo_name(record: dict) -> str:
    """Last path segment of the github URL — the badge label."""
    github = _clean_text(record.get("github")).rstrip("/")
    return github.rsplit("/", 1)[-1] if github else ""


def _project_card(index: int, record: dict) -> list[str]:
    """One card: linked heading, italic blurb, badges, stack line.

    Logo (when the project has one) sits inside the linked heading, the outcome
    is the italic line, repo and case study are for-the-badge buttons, tools are
    a plain ``**Stack:**`` line — so a screener reads title, result, links and
    stack in the same order for every project.
    """
    title = _pick(record, "title_en", "title")
    href = _clean_text(record.get("href"))
    github = _clean_text(record.get("github"))
    logo = LOGO_BY_SLUG.get(_clean_text(record.get("slug")))

    if href and logo:
        heading = (
            f'#### {index}. <a href="{_esc(href)}">'
            f'<img src="{_esc(logo)}" align="absmiddle" alt="{_esc(title)}" /></a>'
        )
    elif href:
        heading = f'#### {index}. <a href="{_esc(href)}">{_esc(title)}</a>'
    else:
        heading = f"#### {index}. {_esc(title)}"
    track = TRACK_PLAIN_LABELS.get(_clean_text(record.get("track")))
    if track:
        heading += f" — {track}"

    lines = [heading, ""]
    text = _row_text(record)
    if text:
        lines.extend([f"_{text}_", ""])

    badges: list[str] = []
    # A private repo 404s for anonymous readers — a badge there is a dead link.
    if github and not record.get("private"):
        badge_url = REPO_BADGE.format(name=_badge_escape(_repo_name(record)))
        badges.append(f"[![Repo]({badge_url})]({github})")
    if href:
        badges.append(f"[![Case study]({CASE_STUDY_BADGE})]({href})")
    if badges:
        lines.extend(["\n".join(badges) + (" · _private_" if record.get("private") else ""), ""])

    tools = [_clean_text(tool) for tool in record.get("tools") or [] if _clean_text(tool)]
    if tools:
        lines.extend(["**Stack:** " + " · ".join(tools[:TOOL_LIMIT]), ""])
    return lines


def _projects_in_track_order(registry: dict) -> list[tuple[str, dict]]:
    """Resolve the registry into (track, project) pairs, in render order.

    Mirrors ``build_projects_block``: per-track lists contribute their dict
    entries first, then the flat ``projects`` array is routed by its ``track``.
    """
    by_track: dict[str, list[dict]] = {track: [] for track in TRACK_ORDER}
    for track in TRACK_ORDER:
        items = registry.get(track)
        if isinstance(items, list):
            by_track[track].extend(project for project in items if isinstance(project, dict))
    for project in registry.get("projects") or []:
        if isinstance(project, dict) and project.get("track") in by_track:
            by_track[project["track"]].append(project)
    return [(track, project) for track in TRACK_ORDER for project in by_track[track]]


def _track_counts(registry: dict) -> dict[str, int]:
    """Projects per track, resolved exactly as ``build_projects_block`` does.

    A per-track list contributes its raw ``len`` (the site contract guarantees
    dict entries); the flat ``projects`` array contributes one per entry whose
    ``track`` is known. Unknown tracks are ignored; every ``TRACK_ORDER`` key is
    present and defaults to 0.
    """
    counts: dict[str, int] = {track: 0 for track in TRACK_ORDER}
    for track in TRACK_ORDER:
        items = registry.get(track)
        if isinstance(items, list):
            counts[track] += len(items)
    for project in registry.get("projects") or []:
        if isinstance(project, dict) and project.get("track") in counts:
            counts[project["track"]] += 1
    return counts


def _portfolio_summary(registry: dict) -> str:
    """One-line markdown roll-up: projects, active tracks, Volta case studies."""
    counts = _track_counts(registry)
    total = sum(counts.values())
    tracks = sum(1 for count in counts.values() if count > 0)
    summary = f"**{total} projects** across **{tracks} tracks**"
    volta = len(registry.get("volta_cases") or [])
    if volta > 0:
        summary += f" · **{volta} Volta case studies**"
    return summary


def projects_links(registry: dict) -> list[str]:
    """Distinct public github/case-study URLs across the registry, first-seen order.

    Input to the CI link-liveness check: every publicly reachable URL the All
    Projects block can render, deduped, so a dead link is reported once rather
    than per occurrence. A private project's ``github`` is skipped — it 404s for
    anonymous requests — while its public ``href`` case study is still checked.
    """
    records = [project for _, project in _projects_in_track_order(registry)]
    records.extend(case for case in (registry.get("volta_cases") or []) if isinstance(case, dict))
    links: list[str] = []
    seen: set[str] = set()
    for record in records:
        private = bool(record.get("private"))
        for key in ("github", "href"):
            # A private repo's URL is only reachable by its owner; anonymous CI
            # and readers get a 404, so keep it out of the liveness check.
            if key == "github" and private:
                continue
            value = _clean_text(record.get(key))
            if value and value not in seen:
                seen.add(value)
                links.append(value)
    return links


def build_projects_svg(registry: dict) -> str:
    """Stacked-track overview card for the All Projects section.

    Self-contained and vector-only, like the other cards. It is deliberately the
    dark inverse of the cream README cards: it opens the projects section, so it
    reads as that section's header band instead of another body tile. Only the
    three brand tokens appear — tracks are told apart by accent opacity alone.
    The accessible name enumerates the project titles, so a screen reader hears
    the portfolio rather than a bare count.
    """
    counts = _track_counts(registry)
    total = sum(counts.values())
    active = [(track, counts[track]) for track in TRACK_ORDER if counts[track] > 0]
    volta = len(registry.get("volta_cases") or [])
    titles = [
        title
        for title in (
            _pick(project, "title_en", "title") for _, project in _projects_in_track_order(registry)
        )
        if title
    ]

    W, H = 800, 150
    bar_x, bar_y, bar_w, bar_h = 20, 84, 760, 30
    # Contract names the field #1400c3 (module TEXT_MAIN) and the ink #f8f2da
    # (module BG) — i.e. the card inverts the cream cards on purpose.
    card_bg, card_ink, card_accent = TEXT_MAIN, BG, ACCENT
    tones = ("1", "0.82", "0.64", "0.46")

    if total > 0:
        header = f"{total} projects · {len(active)} tracks"
        if volta > 0:
            header += f" · {volta} Volta case studies"
    else:
        header = "0 projects"

    if total > 0:
        segments = ""
        cursor = float(bar_x)
        for i, (track, count) in enumerate(active):
            seg_w = bar_w * count / total
            segments += (
                f"    <rect x='{cursor:.1f}' y='{bar_y}' width='{seg_w:.1f}' "
                f"height='{bar_h}' fill='{card_accent}' fill-opacity='{tones[i % len(tones)]}'>"
                f"<title>{_esc(TRACK_PLAIN_LABELS[track])}: {count}</title></rect>\n"
            )
            cursor += seg_w
    else:
        segments = (
            f"    <rect x='{bar_x}' y='{bar_y}' width='{bar_w}' height='{bar_h}' rx='4' "
            f"fill='{card_ink}' fill-opacity='{FAINT_OP}'/>\n"
        )

    if active:
        legend = ""
        for i, (track, count) in enumerate(active):
            lx = bar_x + i * 190
            legend += (
                f"    <rect x='{lx}' y='122' width='11' height='11' rx='2' "
                f"fill='{card_accent}' fill-opacity='{tones[i % len(tones)]}'/>\n"
                f"    <text x='{lx + 17}' y='131' fill='{card_ink}' fill-opacity='{MUTED_OP}' "
                f"font-family='Segoe UI, Ubuntu, sans-serif' font-size='13px'>"
                f"{_esc(TRACK_PLAIN_LABELS[track])}: {count}</text>\n"
            )
    else:
        legend = (
            f"    <text x='{bar_x}' y='131' fill='{card_ink}' fill-opacity='{MUTED_OP}' "
            f"font-family='Segoe UI, Ubuntu, sans-serif' font-size='13px'>No projects yet</text>\n"
        )

    alt = f"Portfolio overview: {total} projects across {len(active)} tracks"
    if volta > 0:
        alt += f" plus {volta} Volta Neobank case studies"
    if titles:
        alt += " — " + ", ".join(titles)

    svg = f"""\
    <svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 {W} {H}' width='{W}' height='{H}'
         role="img" aria-label='{_esc(alt)}'>
      <title>{_esc(alt)}</title>
      <rect fill='{card_bg}' width='{W}' height='{H}' rx='8'/>
      <text x='24' y='37' fill='{card_ink}' font-family='Segoe UI, Ubuntu, sans-serif'
            font-size='16px' font-weight='700' letter-spacing='0.3'>{_esc(header)}</text>
    {segments}  {legend}    <rect x='{bar_x}' y='{bar_y}' width='{bar_w}' height='{bar_h}'
          rx='4' fill='none' stroke='{card_ink}' stroke-opacity='{FAINT_OP}' stroke-width='1'/>
    </svg>
    """
    return textwrap.dedent(svg).strip()


def build_projects_block(registry: dict) -> str:
    """Render the marker-inner markdown for the 'All Projects' section.

    Two registry shapes are accepted: a single ``projects`` array whose entries
    carry a ``track`` field (the frozen site contract), and one list per track
    keyed by name. Tracks still decide the order (``TRACK_ORDER``, empty tracks
    skipped) but no longer the structure: every project is one card, so the
    catalogue reads top to bottom as one scannable list. The ``volta_cases``
    list folds into a collapsible block below.
    """
    projects = [project for _, project in _projects_in_track_order(registry)]
    counts = _track_counts(registry)
    total = sum(counts.values())
    track_total = sum(1 for count in counts.values() if count > 0)
    volta = [case for case in (registry.get("volta_cases") or []) if isinstance(case, dict)]

    lines: list[str] = ["### 🗂️ All Projects", ""]
    lines.append('<p align="center">')
    lines.append(
        f'  <img src="{PROJECTS_SVG_URL}" width="100%" '
        f'alt="Portfolio overview: {total} projects across {track_total} tracks '
        f'plus {len(volta)} Volta Neobank case studies" />'
    )
    lines.append("</p>")
    lines.append("")
    lines.append(_portfolio_summary(registry))
    lines.append("")
    for index, project in enumerate(projects, 1):
        lines.extend(_project_card(index, project))

    if volta:
        while lines and lines[-1] == "":
            lines.pop()
        lines.append("")
        lines.append("<details>")
        lines.append(f"<summary><b>🏦 Volta Neobank — {len(volta)} case studies</b></summary>")
        lines.append("")
        # Volta parts are authored result-first — their description is the finding —
        # so the star.result twin only repeats it. Inside a collapsed block that no
        # screener opens, the repeat is pure length, and 23 full cards would be an
        # appendix nobody scrolls — so these stay one-line rows.
        lines.extend(
            _project_line(index, case, with_result=False) for index, case in enumerate(volta, 1)
        )
        lines.append("")
        lines.append("</details>")

    return "\n".join(lines).rstrip("\n") + "\n"


_ALL_PROJECTS_RE = re.compile(
    rf"{re.escape(ALL_PROJECTS_START)}.*?{re.escape(ALL_PROJECTS_END)}",
    re.DOTALL,
)


def sync_projects_block(content: str, block: str) -> str:
    """Place a generated projects block into README content, idempotently.

    Existing markers are replaced in place; otherwise the block is inserted just
    above the Playable Games section, or appended at EOF as a last resort.
    """
    body = block.strip("\n")
    replacement = f"{ALL_PROJECTS_START}\n{body}\n{ALL_PROJECTS_END}"
    if _ALL_PROJECTS_RE.search(content):
        return _ALL_PROJECTS_RE.sub(lambda _: replacement, content)
    games_heading = "### 🎮 Playable Games"
    if games_heading in content:
        return content.replace(games_heading, f"{replacement}\n\n{games_heading}", 1)
    if content.endswith("\n"):
        return content + "\n" + replacement + "\n"
    return content + "\n\n" + replacement + "\n"


def update_readme_refresh_block(
    days: list[dict],
    projects_block: str | None = None,
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
    # One write, several repairs: the RSS job leaves the notes list on one line
    # and the All Projects section is rendered from the site registry.
    new_content = normalize_notes_block(new_content)
    if projects_block is not None:
        new_content = sync_projects_block(new_content, projects_block)
    if new_content == content:
        print("README already up to date")
        return False
    tmp_readme = readme_path.with_name(readme_path.name + ".tmp")
    tmp_readme.write_text(new_content, encoding="utf-8")
    os.replace(tmp_readme, readme_path)
    print(f"Refreshed README (refresh + notes + projects): {now} ({week} c/7d)")
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
        "--print-project-links",
        action="store_true",
        help="print one project URL per line and exit (CI link-liveness check)",
    )
    parser.add_argument(
        "--registry",
        default=PROJECTS_REGISTRY_URL,
        help="path or URL to the projects registry JSON (default: live site)",
    )
    args = parser.parse_args()
    if args.print_project_links:
        # Registry-only path: no GraphQL, no token — so CI can check project
        # links even when the reads quota is exhausted.
        try:
            registry = load_projects_registry(args.registry)
        except (RuntimeError, urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
            print(f"could not load projects registry: {exc}", file=sys.stderr)
            raise SystemExit(1) from exc
        for url in projects_links(registry):
            print(url)
        return
    DRY_RUN = args.dry_run
    USER = args.user
    if DRY_RUN:
        print("[dry-run] no files will be written")

    print(f"Fetching user data for {USER}...")
    try:
        user_data = fetch_user_data()
    except GitHubUnavailable as exc:
        # Transient-only, mirroring the projects-registry policy below: a
        # scheduled refresh must not go red (or churn files) because GitHub's API
        # had a bad minute. A bad token or GraphQL error is NOT caught here and
        # still exits non-zero; the ::warning:: keeps the skip visible in the
        # Actions summary instead of a silent stale profile.
        print(f"::warning::GitHub API unavailable; profile assets left untouched: {exc}")
        return
    days = extract_contributions(user_data)
    total, current, longest = compute_streaks(days)
    print(f"total={total} current={current} longest={longest}")

    # Everything that can fail on the network or inside a builder runs BEFORE the
    # first write: a raise between two write_asset calls used to leave half the
    # cards refreshed, half stale, and README unrefreshed.
    try:
        langs = fetch_languages()
    except (RuntimeError, urllib.error.URLError, TimeoutError):
        # A silent skip left a stale card behind on a green CI run.
        logging.exception("top-languages.svg could not be generated")
        raise
    print(f"top-languages: {len(langs)} languages")

    # A profile rebuild must not fail because the site registry is briefly
    # unreachable: fetch the block, but on any failure leave README as-is.
    registry = None
    try:
        registry = load_projects_registry(args.registry)
    except (RuntimeError, urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        logging.warning("projects registry unavailable; README block left untouched: %s", exc)

    cards = {
        "hero.svg": build_hero_svg(),
        "stats.svg": build_stats_svg(user_data, total, current, longest),
        "activity.svg": build_activity_svg(days),
        "metrics.svg": build_metrics_svg(days),
        "contribution-types.svg": build_contribution_types_svg(
            extract_contribution_types(user_data)
        ),
        "monthly-activity.svg": build_monthly_activity_svg(days),
        "top-languages.svg": build_top_languages_svg(langs),
    }
    projects_block: str | None = None
    if registry is not None:
        cards[PROJECTS_SVG_NAME] = build_projects_svg(registry)
        projects_block = build_projects_block(registry)

    for name, content in cards.items():
        write_asset(REPO_ROOT / name, content)

    if DRY_RUN:
        print("[dry-run] skip README refresh block")
    else:
        update_readme_refresh_block(days, projects_block)


if __name__ == "__main__":
    main()
