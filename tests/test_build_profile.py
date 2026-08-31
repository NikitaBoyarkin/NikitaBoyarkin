"""Tests for scripts/build_profile.py — pure functions only (no network).

Run: python3 -m pytest tests/test_build_profile.py -v
"""
import math
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# scripts/ is not a package — import via sys.path, mirroring the vault pattern.
SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

import build_profile as bp  # noqa: E402


# ---------- compute_streaks ----------

def _days(counts):
    return [{"date": f"2026-01-{i+1:02d}", "contributionCount": c} for i, c in enumerate(counts)]


def test_streaks_empty():
    assert bp.compute_streaks([]) == (0, 0, 0)


def test_streaks_all_zero():
    assert bp.compute_streaks(_days([0, 0, 0, 0])) == (0, 0, 0)


def test_streaks_full_run():
    # 4 consecutive nonzero days from the start → current=4 (all), longest=4
    assert bp.compute_streaks(_days([1, 1, 1, 1])) == (4, 4, 4)


def test_streaks_current_from_end():
    # last 4 nonzero before a trailing... actually [0,3,5,0,2,2,2,1] → current=4, longest=4
    assert bp.compute_streaks(_days([0, 3, 5, 0, 2, 2, 2, 1])) == (15, 4, 4)


def test_streaks_current_broken_today():
    # today (last) is 0 → current=0 even though yesterday was active
    assert bp.compute_streaks(_days([1, 1, 1, 0])) == (3, 0, 3)


def test_streaks_longest_in_middle():
    assert bp.compute_streaks(_days([1, 1, 0, 1, 1, 1, 0, 1])) == (6, 1, 3)


# ---------- build_top_languages_svg (donut math) ----------

def test_top_languages_svg_renders():
    langs = [("Python", 120000, "#3776AB"), ("SQL", 60000, "#003B57"),
             ("TypeScript", 30000, "#3178C6")]
    svg = bp.build_top_languages_svg(langs)
    assert svg.startswith("<svg")
    assert "Top Languages" in svg
    assert "Python" in svg
    assert "57.1%" in svg  # 120000 / 210000


def test_top_languages_donut_dasharray_sums_to_circumference():
    """Each donut slice is a circle with stroke-dasharray='dash (C-dash)' → pair sums to C."""
    langs = [("Python", 120000, "#3776AB"), ("SQL", 60000, "#003B57"),
             ("TypeScript", 30000, "#3178C6")]
    svg = bp.build_top_languages_svg(langs)
    R = 52
    C = 2 * math.pi * R
    dasharrays = re.findall(r"stroke-dasharray='([\d.]+) ([\d.]+)'", svg)
    assert dasharrays, "no dasharray found"
    for dash_str, rest_str in dasharrays:
        dash, rest = float(dash_str), float(rest_str)
        assert abs((dash + rest) - C) < 0.2, f"dash+rest={dash+rest} != C={C}"


def test_top_languages_empty_does_not_crash():
    # total=0 → guarded by `or 1`; should render without exception
    svg = bp.build_top_languages_svg([])
    assert svg.startswith("<svg")


# ---------- build_stats_svg / build_streak_svg / build_activity_svg ----------

def _user_data():
    return {"user": {
        "createdAt": "2020-03-15T10:00:00Z",
        "repositories": {"totalCount": 42},
        "followers": {"totalCount": 17},
    }}


def test_build_stats_svg():
    svg = bp.build_stats_svg(_user_data(), total=100, current=5, longest=12)
    assert svg.startswith("<svg")
    assert "42" in svg  # public repos
    assert "17" in svg  # followers
    assert "2020" in svg  # active since


def test_build_streak_svg():
    svg = bp.build_streak_svg(_days([1, 2, 3]), total=6, current=3, longest=3)
    assert svg.startswith("<svg")
    assert "6" in svg and "3" in svg


def test_build_activity_svg():
    svg = bp.build_activity_svg(_days([0, 1, 2, 3, 4, 5, 6, 7, 8, 9]))
    assert svg.startswith("<svg")
    assert "Activity" in svg
    assert "2026-01-01" in svg and "2026-01-10" in svg  # date labels


def test_build_activity_svg_all_zero():
    svg = bp.build_activity_svg(_days([0] * 10))
    assert svg.startswith("<svg")  # max_val guarded to 1


# ---------- update_readme_refresh_block ----------

def test_refresh_block_updates_existing_marker(tmp_path, monkeypatch):
    readme = tmp_path / "README.md"
    readme.write_text(
        "### ⚡ Activity\n\n"
        "<!-- LAST-REFRESHED:START -->\n"
        "_Last refreshed: OLD · 0 contributions in the last 7 days_\n"
        "<!-- LAST-REFRESHED:END -->\n\n"
        "rest of file\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(bp, "REPO_ROOT", tmp_path)
    assert bp.update_readme_refresh_block(_days([1, 1, 1, 1, 1, 1, 1])) is True
    content = readme.read_text(encoding="utf-8")
    assert "OLD" not in content
    assert "Last refreshed:" in content
    assert "7 contributions in the last 7 days" in content
    assert "rest of file" in content  # rest preserved


def test_refresh_block_inserts_when_marker_missing(tmp_path, monkeypatch):
    readme = tmp_path / "README.md"
    readme.write_text("### ⚡ Activity\n\nbody\n", encoding="utf-8")
    monkeypatch.setattr(bp, "REPO_ROOT", tmp_path)
    assert bp.update_readme_refresh_block(_days([0] * 7)) is True
    content = readme.read_text(encoding="utf-8")
    assert "LAST-REFRESHED:START" in content
    assert "0 contributions in the last 7 days" in content
