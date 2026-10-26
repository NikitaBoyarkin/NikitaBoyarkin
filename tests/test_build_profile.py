"""Tests for scripts/build_profile.py — pure functions only (no network).

Run: python3 -m pytest tests/test_build_profile.py -v
"""

import math
import re
import sys
import urllib.error
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

# scripts/ is not a package — import via sys.path, mirroring the vault pattern.
SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

import build_profile as bp  # noqa: E402


# ---------- compute_streaks ----------


def _days(counts):
    return [{"date": f"2026-01-{i + 1:02d}", "contributionCount": c} for i, c in enumerate(counts)]


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
    langs = [
        ("Python", 120000, "#3776AB"),
        ("SQL", 60000, "#003B57"),
        ("TypeScript", 30000, "#3178C6"),
    ]
    svg = bp.build_top_languages_svg(langs)
    assert svg.startswith("<svg")
    assert "Top Languages" in svg
    assert "Python" in svg
    assert "57.1%" in svg  # 120000 / 210000
    # "Python" appears in the slice <title>, the center label and the legend.
    assert svg.count("Python") >= 3, "legend row missing"


def test_top_languages_donut_dasharray_sums_to_circumference():
    """Each donut slice is a circle with stroke-dasharray='dash (C-dash)' → pair sums to C."""
    langs = [
        ("Python", 120000, "#3776AB"),
        ("SQL", 60000, "#003B57"),
        ("TypeScript", 30000, "#3178C6"),
    ]
    svg = bp.build_top_languages_svg(langs)
    R = 60
    C = 2 * math.pi * R
    dasharrays = re.findall(r"stroke-dasharray='([\d.]+) ([\d.]+)'", svg)
    assert dasharrays, "no dasharray found"
    for dash_str, rest_str in dasharrays:
        dash, rest = float(dash_str), float(rest_str)
        assert abs((dash + rest) - C) < 0.2, f"dash+rest={dash + rest} != C={C}"


def test_top_languages_empty_does_not_crash():
    # total=0 → guarded by `or 1`; should render without exception
    svg = bp.build_top_languages_svg([])
    assert svg.startswith("<svg")


def test_top_languages_folds_long_tail_into_other():
    langs = [(f"Lang{i}", 100 - i, "#123456") for i in range(12)]
    svg = bp.build_top_languages_svg(langs)
    assert "Other" in svg  # tail folded
    assert "Lang7" in svg  # top 8 kept
    assert "Lang8" not in svg


def test_fetch_languages_orders_equal_sizes_by_name(monkeypatch):
    # Repo order from the API is UPDATED_AT DESC, so it changes between runs. Without
    # a name tie-break equal byte counts reshuffle the donut and produce a diff on a
    # day when nothing changed.
    repos = [
        {
            "languages": {
                "edges": [
                    {"size": 10, "node": {"name": "B", "color": "#111111"}},
                    {"size": 10, "node": {"name": "A", "color": "#222222"}},
                    {"size": 30, "node": {"name": "C", "color": "#333333"}},
                ]
            }
        }
    ]
    monkeypatch.setattr(
        bp, "graphql", lambda *args, **kwargs: {"user": {"repositories": {"nodes": repos}}}
    )
    assert bp.fetch_languages() == [
        ("C", 30, "#333333"),
        ("A", 10, "#222222"),
        ("B", 10, "#111111"),
    ]


# ---------- build_stats_svg / build_activity_svg ----------


def _user_data():
    return {
        "user": {
            "createdAt": "2020-03-15T10:00:00Z",
            "repositories": {"totalCount": 42},
            "followers": {"totalCount": 17},
        }
    }


def test_build_stats_svg():
    svg = bp.build_stats_svg(_user_data(), total=100, current=5, longest=12)
    assert svg.startswith("<svg")
    assert "42" in svg  # public repos
    assert "17" in svg  # followers
    assert "2020" in svg  # active since
    assert "Current Streak" in svg and "Longest Streak" in svg  # single source for streaks


def test_build_activity_svg():
    svg = bp.build_activity_svg(_days([0, 1, 2, 3, 4, 5, 6, 7, 8, 9]))
    assert svg.startswith("<svg")
    assert "Activity" in svg
    assert "2026-01-01" in svg and "2026-01-10" in svg  # date labels


def test_build_activity_svg_all_zero():
    svg = bp.build_activity_svg(_days([0] * 10))
    assert svg.startswith("<svg")  # max_val guarded to 1


# ---------- contribution types / monthly activity ----------


def _contrib_user_data():
    return {
        "user": {
            "contributionsCollection": {
                "totalCommitContributions": 500,
                "totalPullRequestContributions": 40,
                "totalIssueContributions": 10,
                "totalPullRequestReviewContributions": 5,
            }
        }
    }


def test_extract_contribution_types():
    types = bp.extract_contribution_types(_contrib_user_data())
    assert types == [
        ("Commits", 500),
        ("Pull Requests", 40),
        ("Issues", 10),
        ("Code Reviews", 5),
    ]


def test_build_contribution_types_svg():
    svg = bp.build_contribution_types_svg(bp.extract_contribution_types(_contrib_user_data()))
    assert svg.startswith("<svg")
    assert "Commits" in svg and "500" in svg and "Code Reviews" in svg


def test_contribution_types_zero_does_not_crash():
    svg = bp.build_contribution_types_svg([("Commits", 0), ("Issues", 0)])
    assert svg.startswith("<svg")  # max guarded to 1


def test_build_monthly_activity_svg():
    svg = bp.build_monthly_activity_svg(_days([1, 2, 3, 4, 5, 6, 7]))
    assert svg.startswith("<svg")
    assert "Monthly Contributions" in svg
    assert "Jan" in svg  # 2026-01 from _days()


def test_monthly_activity_splits_months():
    days = [
        {"date": "2026-01-15", "contributionCount": 3},
        {"date": "2026-02-10", "contributionCount": 7},
    ]
    svg = bp.build_monthly_activity_svg(days)
    assert "Jan" in svg and "Feb" in svg
    assert "<title>2026-02: 7 contributions</title>" in svg


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


# ---------- extract_contributions ----------


def test_default_user_is_profile_login_not_os_user():
    # Regression: the login must never be derived from the shell `$USER`.
    assert bp.DEFAULT_USER == "NikitaBoyarkin"


def test_extract_contributions_flattens_and_drops_future():
    data = {
        "user": {
            "contributionsCollection": {
                "contributionCalendar": {
                    "weeks": [
                        {
                            "contributionDays": [
                                {"date": "2000-01-01", "contributionCount": 1},
                                {"date": "2999-01-01", "contributionCount": 1},
                            ]
                        },
                    ],
                }
            }
        }
    }
    days = bp.extract_contributions(data)
    assert days == [{"date": "2000-01-01", "contributionCount": 1}]


# ---------- build_metrics_svg (slim card, REQ-018 budget) ----------


def test_metrics_svg_is_self_contained_and_within_budget():
    # A full year of days → worst-case payload. Must stay well under the
    # 80 KB REQ-018 budget and never reference an external host.
    days = _days((i % 7) for i in range(371))
    svg = bp.build_metrics_svg(days)
    assert svg.startswith("<svg")
    assert "Contribution Map" in svg
    # Streak/total numbers live in stats.svg only — not repeated here.
    assert "Current streak" not in svg and "Longest" not in svg
    # Zero external requests: no remote images / hrefs, only the SVG namespace.
    assert "<image" not in svg
    assert "url(http" not in svg
    assert 'href="http' not in svg
    assert svg.count("http") == 1  # the xmlns declaration only
    assert len(svg.encode("utf-8")) < 80_000


def test_metrics_svg_title_marks_every_day():
    days = _days([0, 1, 2, 3, 4, 5, 6])
    svg = bp.build_metrics_svg(days)
    # Each day is a rect with an accessible <title>.
    assert svg.count("<rect") >= len(days)
    assert svg.count("<title>") == len(days)


# ---------- F2: empty contribution history ----------


def test_build_activity_svg_empty_days_does_not_crash():
    # Regression: an empty calendar reached `tail[0]` / `tail[-1]` and raised
    # IndexError; both endpoints are now guarded with `if tail else ""`.
    svg = bp.build_activity_svg([])
    assert "<svg" in svg
    ET.fromstring(svg)  # still well-formed XML
    assert not re.search(r"\d{4}-\d{2}-\d{2}", svg)  # no date labels
    assert "<circle" not in svg  # no data points


# ---------- F3: top-languages failure is no longer swallowed ----------


def _full_user_data():
    # build_stats_svg and extract_contribution_types both run inside main(),
    # so the stub payload needs the fields each of them reads.
    return {
        "user": {
            "createdAt": "2020-03-15T10:00:00Z",
            "repositories": {"totalCount": 42},
            "followers": {"totalCount": 17},
            "contributionsCollection": {
                "totalCommitContributions": 500,
                "totalPullRequestContributions": 40,
                "totalIssueContributions": 10,
                "totalPullRequestReviewContributions": 5,
            },
        }
    }


def _raising(exc):
    def _raise():
        raise exc

    return _raise


def _stub_main(monkeypatch, languages_exc):
    """Stub every IO/network dependency of main(); return the logging recorder."""
    logged: list = []
    monkeypatch.setattr(sys, "argv", ["build_profile.py"])
    monkeypatch.setattr(bp, "fetch_user_data", _full_user_data)
    monkeypatch.setattr(bp, "extract_contributions", lambda data: [])
    monkeypatch.setattr(bp, "compute_streaks", lambda days: (0, 0, 0))
    monkeypatch.setattr(bp, "write_asset", lambda path, content: None)
    monkeypatch.setattr(bp, "update_readme_refresh_block", lambda *a, **k: False)
    monkeypatch.setattr(bp, "fetch_languages", _raising(languages_exc))
    monkeypatch.setattr(bp.logging, "exception", lambda *a, **k: logged.append(a))
    return logged


def test_no_card_renders_a_timestamp_the_regex_cannot_strip():
    # Regression: the analytics-evidence footer rendered "last updated:"
    # (lowercase) while _TIMESTAMP_RE matches "Last updated:", so that card was
    # rewritten on every run regardless of whether its data changed.
    with open(bp.__file__, encoding="utf-8") as fh:
        source = fh.read()
    assert "last updated:" not in source


def test_main_reraises_language_failure_but_not_non_network_errors(monkeypatch):
    # Regression: `except Exception` + `print("... skipped ...")` turned a dead
    # top-languages card into a green CI run.
    logged = _stub_main(monkeypatch, RuntimeError("boom"))
    with pytest.raises(RuntimeError, match="boom"):
        bp.main()
    assert logged, "logging.exception must run before the re-raise"

    # Narrowing proof: a non-network error never enters the handler at all, so
    # it escapes unlogged. `except Exception: raise` would have logged it.
    logged.clear()
    monkeypatch.setattr(bp, "fetch_languages", _raising(ValueError("not a network error")))
    with pytest.raises(ValueError, match="not a network error"):
        bp.main()
    assert logged == [], "ValueError must escape the narrowed except clause unlogged"


# ---------- F4: untrusted values are XML-escaped ----------


def test_untrusted_values_are_xml_escaped(monkeypatch):
    # Language names and linguist colors come from the GitHub API; a raw quote
    # in a color used to escape its SVG attribute and break well-formedness.
    svg = bp.build_top_languages_svg([("<&>", 10, "#fe4e02'><script>")])
    ET.fromstring(svg)
    assert "<script>" not in svg
    assert "&lt;" in svg

    monkeypatch.setattr(bp, "USER", "a<b&c")
    stats = bp.build_stats_svg(_full_user_data(), total=1, current=1, longest=1)
    ET.fromstring(stats)
    assert "a<b&c" not in stats
    assert "&lt;" in stats

    types = bp.build_contribution_types_svg([("x<y", 3)])
    ET.fromstring(types)
    assert "x<y" not in types
    assert "&lt;" in types


def test_monthly_activity_escapes_untrusted_date(monkeypatch):
    # A day whose date carries markup must not reach the SVG as raw text.
    monkeypatch.setattr(bp, "USER", "a<b")
    svg = bp.build_monthly_activity_svg([{"date": "2026-01-<script>", "contributionCount": 3}])
    ET.fromstring(svg)
    assert "<script>" not in svg
    assert "&lt;" in svg  # from the escaped login in the card title


# ---------- F5: month labels are locale-independent ----------


def test_monthly_activity_month_label_is_locale_independent():
    # Regression: strftime("%b") under LC_TIME=ru_RU rendered "янв" into an
    # otherwise English card. No locale is set here — the code must not need one.
    svg = bp.build_monthly_activity_svg([{"date": "2026-01-15", "contributionCount": 1}])
    assert ">Jan<" in svg  # label is rendered as `>{label}</text>`
    assert "янв" not in svg


# ---------- build_hero_svg ----------


def test_hero_svg_is_well_formed_and_accessible():
    svg = bp.build_hero_svg()
    root = ET.fromstring(svg)
    assert root.get("role") == "img"
    assert root.get("aria-label"), "hero needs an aria-label"
    titles = list(root.iter("{http://www.w3.org/2000/svg}title"))
    assert titles and bp.HERO_NAME in titles[0].text
    assert bp.HERO_NAME in svg and bp.HERO_ROLE in svg


def test_hero_svg_is_vector_only_and_within_budget():
    """Self-hosted and raster-free — the reference header is ~200 KB of base64 GIF."""
    svg = bp.build_hero_svg()
    assert "base64" not in svg
    assert "<image" not in svg
    assert len(svg.encode()) < 6000, f"hero is {len(svg.encode())} B"


def test_hero_svg_uses_only_brand_tokens():
    svg = bp.build_hero_svg()
    allowed = {bp.BG, bp.ACCENT, bp.TEXT_MAIN}
    assert set(re.findall(r"#[0-9a-fA-F]{6}", svg)) <= allowed


# ---------- normalize_notes_block ----------


def _notes_block(items):
    return (
        "### Recent Notes\n\n"
        "<!-- RECENT-POSTS-LIST:START -->\n"
        f"{items}\n"
        "<!-- RECENT-POSTS-LIST:END -->\n"
    )


def _notes_body(content):
    return content.split("<!-- RECENT-POSTS-LIST:START -->")[1].split(
        "<!-- RECENT-POSTS-LIST:END -->"
    )[0]


def test_notes_block_splits_glued_items():
    glued = _notes_block("- [A](https://a)- [B](https://b)- [C](https://c)")
    out = bp.normalize_notes_block(glued)
    assert _notes_body(out).strip().splitlines() == [
        "- [A](https://a)",
        "- [B](https://b)",
        "- [C](https://c)",
    ]


def test_notes_block_is_idempotent():
    once = bp.normalize_notes_block(_notes_block("- [A](https://a)- [B](https://b)"))
    assert bp.normalize_notes_block(once) == once


def test_notes_block_without_marker_is_untouched():
    content = "### Recent Notes\n\n- [A](https://a)- [B](https://b)\n"
    assert bp.normalize_notes_block(content) == content


def test_notes_block_keeps_utm_urls_intact():
    url = "https://x.dev/posts/a/?utm_source=github&utm_medium=profile_readme&utm_campaign=notes"
    assert f"- [A]({url})" in bp.normalize_notes_block(_notes_block(f"- [A]({url})"))


def test_refresh_block_writes_normalized_notes(tmp_path, monkeypatch):
    """The daily README write is also the repair pass for the glued RSS list."""
    readme = tmp_path / "README.md"
    readme.write_text(
        "### ⚡ Activity\n\n"
        "<!-- LAST-REFRESHED:START -->\n_old_\n<!-- LAST-REFRESHED:END -->\n\n"
        + _notes_block("- [A](https://a)- [B](https://b)")
    )
    monkeypatch.setattr(bp, "REPO_ROOT", tmp_path)
    assert bp.update_readme_refresh_block(_days([1] * 7)) is True
    written = readme.read_text()
    assert "- [A](https://a)\n- [B](https://b)" in written
    assert "- [A](https://a)- [B](https://b)" not in written


def _repo_readme() -> str:
    return (Path(__file__).resolve().parent.parent / "README.md").read_text(encoding="utf-8")


def test_readme_stats_card_height_matches_the_svg():
    """The card is rendered by an explicit height= in the README."""
    match = re.search(r'height="(\d+)"\s+src="[^"]*stats\.svg"', _repo_readme())
    assert match, "stats card tag not found in README"
    svg = bp.build_stats_svg(_full_user_data(), total=1, current=1, longest=1)
    assert float(match.group(1)) == float(re.search(r"height='(\d+)px'", svg).group(1))


# ---------- readability floor for every card ----------

MIN_CARD_FONT_PX = 11


def _all_cards() -> dict:
    days = _days((i % 7) for i in range(371))
    return {
        "hero": bp.build_hero_svg(),
        "stats": bp.build_stats_svg(_full_user_data(), total=100, current=5, longest=12),
        "activity": bp.build_activity_svg(days),
        "metrics": bp.build_metrics_svg(days),
        "contribution-types": bp.build_contribution_types_svg([("Commits", 500), ("Issues", 3)]),
        "monthly-activity": bp.build_monthly_activity_svg(days),
        "top-languages": bp.build_top_languages_svg([("Python", 120000, "#3776AB")]),
    }


def test_no_card_renders_text_below_the_readability_floor():
    """Cards are <img>s rendered at ~1:1, so one SVG px is one screen px.

    The original cards went down to 9px footers and 10px body text. The floor is
    bound here so a later edit cannot quietly shrink the cards back.
    """
    for name, svg in _all_cards().items():
        sizes = [float(s) for s in re.findall(r"font-size='([\d.]+)px'", svg)]
        assert sizes, f"{name} renders no sized text"
        assert min(sizes) >= MIN_CARD_FONT_PX, f"{name} renders {min(sizes)}px text"


# ---------- all-projects registry ----------

# Frozen registry shape: a "projects" list (each project carries its "track")
# plus a "volta_cases" list. Fixtures carry exactly that key set; each project
# carries track/title/description/result/tools/href/github/private.

_START = "<!-- ALL-PROJECTS:START -->"
_END = "<!-- ALL-PROJECTS:END -->"

_CARD_HEADING_RE = re.compile(r"^#### (\d+)\. ")
# Appendix rows start "N. " and may open with either a bold text link or a card
# <a><img></a> once the case has a registered wordmark.
_NUMBERED_ROW_RE = re.compile(r"^\d+\. ")


def _project(
    title,
    track,
    *,
    description="desc",
    result=None,
    tools=(),
    href="https://example.test/case",
    github=None,
    private=False,
):
    return {
        "track": track,
        "title": title,
        "description": description,
        "result": result,
        "tools": list(tools),
        "href": href,
        "github": github,
        "private": private,
    }


def _case(title, *, description="desc", result=None, github=None, href=None, slug=None):
    return {
        "title": title,
        "description": description,
        "result": result,
        "github": github,
        "href": href,
        "slug": slug,
    }


def _registry(*, projects=(), volta_cases=()):
    return {"projects": list(projects), "volta_cases": list(volta_cases)}


def _cards(block):
    """The Featured-style cards of the visible catalogue, in render order."""
    top = block.partition("<details>")[0]
    cards, current = [], None
    for line in top.splitlines():
        if _CARD_HEADING_RE.match(line):
            if current is not None:
                cards.append("\n".join(current).strip())
            current = [line]
        elif current is not None:
            current.append(line)
    if current is not None:
        cards.append("\n".join(current).strip())
    return cards


def _card_for(block, title):
    return next(card for card in _cards(block) if title in card)


def _volta_rows(block):
    """The numbered one-line rows of the collapsed Volta appendix."""
    return [line for line in block.splitlines() if _NUMBERED_ROW_RE.match(line)]


def _volta_row_for(block, title):
    return next(line for line in _volta_rows(block) if title in line)


def test_build_projects_block_lists_every_project_in_track_order():
    # 2 experiments + 1 analytics + 1 engineering; product intentionally empty.
    block = bp.build_projects_block(
        _registry(
            projects=[
                _project("Exp A", "experiments"),
                _project("Exp B", "experiments"),
                _project("Ana A", "analytics"),
                _project("Eng A", "engineering"),
            ]
        )
    )
    assert block.startswith("### 🗂️ All Projects")
    titles = ["Exp A", "Exp B", "Ana A", "Eng A"]
    cards = _cards(block)
    assert len(cards) == len(titles)
    assert [next(t for t in titles if t in card) for card in cards] == titles
    assert [re.match(r"^#### (\d+)\. ", card).group(1) for card in cards] == ["1", "2", "3", "4"]


def test_build_projects_block_repo_and_case_links():
    github = "https://github.com/NikitaBoyarkin/demo"
    href = "https://nikitaboyarkin.github.io/demo/case.html"
    block = bp.build_projects_block(
        _registry(projects=[_project("Demo", "analytics", github=github, href=href)])
    )
    assert "img.shields.io/badge/Repo-demo-0f2a2b" in block
    assert f"]({github})" in block
    assert "img.shields.io/badge/Case_study-fe4e02" in block
    assert f"]({href})" in block


def test_build_projects_block_prefers_en_text():
    project = _project("RU Title", "analytics", description="RU desc")
    project["title_en"] = "EN Title"
    project["description_en"] = "EN desc"
    block = bp.build_projects_block(_registry(projects=[project]))
    assert "EN Title" in block
    assert "RU Title" not in block
    # Cards carry no blurb, so the description preference is asserted where it lives.
    assert bp._row_text(project) == "EN desc"


def test_build_projects_block_falls_back_to_ru_text():
    # An older RU-only registry (no *_en keys) must still render its rows.
    project = _project("RU Title", "analytics", description="RU desc")
    block = bp.build_projects_block(_registry(projects=[project]))
    assert "RU Title" in block
    assert bp._row_text(project) == "RU desc"


def test_build_projects_block_volta_prefers_en_text():
    case = _case("Volta RU", description="RU desc")
    case["title_en"] = "Volta EN"
    case["description_en"] = "EN desc"
    block = bp.build_projects_block(_registry(volta_cases=[case]))
    assert "Volta EN" in block and "EN desc" in block
    assert "Volta RU" not in block and "RU desc" not in block


def test_build_projects_block_private_without_repo():
    block = bp.build_projects_block(
        _registry(projects=[_project("Closed", "engineering", github=None, private=True)])
    )
    assert "Repo-" not in block
    assert "Case_study" in block
    assert "_private_" in block


def test_build_projects_block_private_with_repo_omits_dead_repo_link():
    github = "https://github.com/NikitaBoyarkin/secret"
    block = bp.build_projects_block(
        _registry(projects=[_project("Closed", "analytics", github=github, private=True)])
    )
    assert "Repo-secret" not in block
    assert f"]({github})" not in block
    assert "Case_study" in block
    assert "_private_" in block


def test_build_projects_block_volta_details():
    github = "https://github.com/NikitaBoyarkin/volta"
    block = bp.build_projects_block(
        _registry(
            volta_cases=[
                _case("Volta One", github=github),
                _case("Volta Two", github=None),
            ]
        )
    )
    assert "<details>" in block
    assert "2 case studies" in block
    details = block[block.index("<details>") :]
    assert "Volta One" in details and "Volta Two" in details
    one = next(line for line in details.splitlines() if "Volta One" in line)
    two = next(line for line in details.splitlines() if "Volta Two" in line)
    assert f"[Repo]({github})" in one
    assert "[Repo](" not in two  # null github → no repo link on that bullet


def test_build_projects_block_no_volta_omits_details():
    block = bp.build_projects_block(_registry(projects=[_project("X", "experiments")]))
    assert "<details>" not in block


def test_sync_projects_block_replaces_existing():
    doc = f"pre\n{_START}\nOLD\n{_END}\npost\n"
    block = "### 🗂️ All Projects\n\n- **New**"
    out = bp.sync_projects_block(doc, block)
    assert out.count(_START) == 1
    assert out.count(_END) == 1
    assert "OLD" not in out
    assert block in out
    assert "pre" in out and "post" in out


def test_sync_projects_block_inserts_before_games():
    games = "### 🎮 Playable Games"
    out = bp.sync_projects_block(f"body\n\n{games}\nmore\n", "BLOCK")
    assert out.index(_START) < out.index(games)


def test_sync_projects_block_appends_when_no_anchor():
    out = bp.sync_projects_block("just some body text\n", "BLOCK")
    assert "just some body text" in out
    assert out.rstrip().endswith(_END)


def test_sync_projects_block_is_idempotent():
    doc = "body\n\n### 🎮 Playable Games\n"
    once = bp.sync_projects_block(doc, "BLOCK")
    assert bp.sync_projects_block(once, "BLOCK") == once


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def read(self):
        return self._payload

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_fetch_projects_registry_parses_json(monkeypatch):
    # Narrowest patchable symbol: build_profile does a module-scope
    # `import urllib.request` (line 31) and calls urlopen on it, so the call site
    # is bp.urllib.request.urlopen — not a wrapper helper.
    import json

    payload = {"experiments": [{"title": "X"}], "volta_cases": []}
    monkeypatch.setattr(
        bp.urllib.request,
        "urlopen",
        lambda *a, **k: _FakeResponse(json.dumps(payload).encode()),
    )
    assert bp.fetch_projects_registry("https://example.test/projects.json") == payload


def test_fetch_projects_registry_raises_on_error(monkeypatch):
    import urllib.error

    def _fail(*a, **k):
        raise urllib.error.URLError("network down")

    monkeypatch.setattr(bp.urllib.request, "urlopen", _fail)
    with pytest.raises(RuntimeError):
        bp.fetch_projects_registry("https://example.test/projects.json")


# ---------- all-projects visualization + automation ----------


def test_projects_svg_constants():
    assert bp.PROJECTS_SVG_NAME == "projects.svg"
    assert bp.PROJECTS_SVG_URL == (
        "https://raw.githubusercontent.com/NikitaBoyarkin/NikitaBoyarkin/main/projects.svg"
    )


def test_projects_registry_url_uses_default_branch():
    # Regression: the default branch of the site repo is `master`, not `main`.
    assert "/master/" in bp.PROJECTS_REGISTRY_URL


def test_track_counts_counts_projects_per_track():
    counts = bp._track_counts(
        _registry(
            projects=[
                _project("Exp A", "experiments"),
                _project("Exp B", "experiments"),
                _project("Ana A", "analytics"),
            ]
        )
    )
    assert set(counts) <= set(bp.TRACK_ORDER)
    assert counts["experiments"] == 2
    assert counts["analytics"] == 1
    assert sum(counts.values()) == 3


def test_portfolio_summary_format():
    reg = _registry(
        projects=[_project("A", "experiments"), _project("B", "analytics")],
        volta_cases=[_case("V1"), _case("V2"), _case("V3")],
    )
    assert (
        bp._portfolio_summary(reg)
        == "**2 projects** across **2 tracks** · **3 Volta case studies**"
    )


def test_projects_svg_is_self_contained_and_accessible():
    svg = bp.build_projects_svg(_registry(projects=[_project("Demo", "analytics")]))
    assert svg.startswith("<svg")
    assert 'role="img"' in svg
    assert "aria-label" in svg
    assert "<title>" in svg
    assert svg.strip().endswith("</svg>")
    assert "<script" not in svg
    # Self-contained: no remote resource is referenced. "http" appears exactly once
    # — the xmlns declaration, without which the card is not an SVG document at all.
    assert "<image" not in svg
    assert "url(http" not in svg
    assert 'href="http' not in svg
    assert svg.count("http") == 1
    ET.fromstring(svg)


def test_projects_svg_root_is_a_namespaced_svg_with_intrinsic_size():
    # Regression: the root was emitted as `<svg viewBox=... width='100%'>` — no
    # xmlns, no height. Served as image/svg+xml that is not an SVG document, so
    # Chrome paints an unstyled XML tree, the <img> breaks and its alt text leaks
    # onto the profile. ElementTree parsed it fine, so the write gate waved it
    # through. Keep both: the namespace, and the size the <img> scales from.
    svg = bp.build_projects_svg(_registry(projects=[_project("Demo", "analytics")]))
    root = ET.fromstring(svg)
    assert root.tag == "{http://www.w3.org/2000/svg}svg"
    assert root.get("width") and root.get("height")


def test_write_asset_rejects_svg_that_is_not_an_svg_document(tmp_path):
    # The gate that should have stopped the namespace-less card: a root element in
    # no namespace is well-formed XML but renders as a broken image.
    target = tmp_path / "card.svg"
    with pytest.raises(ValueError):
        bp.write_asset(target, "<svg viewBox='0 0 10 10'/>")
    assert not target.exists()


def test_projects_svg_empty_registry_is_valid():
    svg = bp.build_projects_svg({})
    assert svg.startswith("<svg")
    assert svg.strip().endswith("</svg>")
    assert "<script" not in svg
    ET.fromstring(svg)


def test_projects_svg_is_deterministic():
    reg = _registry(
        projects=[_project("A", "experiments"), _project("B", "analytics")],
        volta_cases=[_case("V")],
    )
    assert bp.build_projects_svg(reg) == bp.build_projects_svg(reg)


def test_projects_svg_escapes_untrusted_text():
    svg = bp.build_projects_svg(
        _registry(
            projects=[_project("A<script>&", "analytics", description="<b>&")],
        )
    )
    ET.fromstring(svg)
    assert "<script>" not in svg
    assert "&lt;" in svg


def test_projects_links_collects_github_and_href_distinct_in_order():
    a = "https://github.com/NikitaBoyarkin/a"
    b = "https://example.test/case-b"
    reg = _registry(
        projects=[
            _project("P1", "analytics", github=a, href=b),
            _project("P2", "analytics", github=a, href=None),
            _project("P3", "engineering", github=None, href=None),
        ]
    )
    assert bp.projects_links(reg) == [a, b]


def test_projects_links_skips_private_repo_but_keeps_case_study():
    secret = "https://github.com/NikitaBoyarkin/secret"
    case = "https://example.test/private-case"
    reg = _registry(
        projects=[_project("Closed", "analytics", github=secret, href=case, private=True)]
    )
    links = bp.projects_links(reg)
    assert secret not in links
    assert case in links


def test_projects_links_covers_track_lists_and_volta():
    p = "https://github.com/NikitaBoyarkin/p"
    t = "https://github.com/NikitaBoyarkin/t"
    v = "https://github.com/NikitaBoyarkin/v"
    reg = {
        "projects": [_project("P", "analytics", github=p)],
        "experiments": [_project("T", "experiments", github=t)],
        "volta_cases": [_case("V", github=v), _case("NoRepo", github=None)],
    }
    links = bp.projects_links(reg)
    assert {p, t, v} <= set(links)
    assert "" not in links
    assert len(links) == len(set(links))


def test_build_projects_block_embeds_svg_and_summary_after_heading():
    reg = _registry(
        projects=[_project("Exp", "experiments"), _project("Ana", "analytics")],
        volta_cases=[_case("V")],
    )
    block = bp.build_projects_block(reg)
    assert block.startswith("### 🗂️ All Projects")
    assert "<img" in block
    assert bp.PROJECTS_SVG_URL in block
    summary = bp._portfolio_summary(reg)
    assert summary in block
    heading = block.index("### 🗂️ All Projects")
    assert heading < block.index(bp.PROJECTS_SVG_URL)
    assert heading < block.index(summary) < block.index(_cards(block)[0])


def test_build_projects_block_card_carries_track_badges_and_stack():
    github = "https://github.com/NikitaBoyarkin/demo"
    href = "https://example.test/case"
    block = bp.build_projects_block(
        _registry(
            projects=[
                _project(
                    "Demo",
                    "analytics",
                    github=github,
                    href=href,
                    tools=["Python", "SQL", "pytest", "uv", "dbt"],
                )
            ]
        )
    )
    card = _card_for(block, "Demo")
    assert card.startswith(f'#### 1. <a href="{href}">Demo</a> — Analytics')
    assert "img.shields.io/badge/Repo-demo-0f2a2b" in card
    assert f"]({github})" in card
    assert "img.shields.io/badge/Case_study-fe4e02" in card
    assert f"]({href})" in card
    assert "**Stack:** ![Python](https://img.shields.io/badge/Python-3776AB" in card
    assert "&logo=python&logoColor=white)" in card
    assert "dbt" not in card, "tools are capped so the title stays the scan anchor"


def test_build_projects_block_card_shows_live_star_count():
    """Public repos get a linked stars badge; private ones must not.

    The count is shields' live endpoint, not a snapshot, so the assertion pins the
    owner/repo path — a registry rename has to move the badge with it.
    """
    github = "https://github.com/NikitaBoyarkin/demo"
    block = bp.build_projects_block(
        _registry(
            projects=[
                _project("Public", "analytics", github=github),
                _project(
                    "Secret",
                    "analytics",
                    github="https://github.com/NikitaBoyarkin/hidden",
                    private=True,
                ),
            ]
        )
    )
    card = _card_for(block, "Public")
    assert "img.shields.io/github/stars/NikitaBoyarkin/demo?style=for-the-badge" in card
    assert "[![Stars](https://img.shields.io/github/stars/NikitaBoyarkin/demo" in card
    assert f")]({github})" in card
    secret = _card_for(block, "Secret")
    assert "github/stars" not in secret, "a private repo's star badge is a dead link"


def test_build_projects_block_known_project_gets_a_logo_card():
    project = _project("Volta Neobank", "experiments", href="https://example.test/volta")
    project["slug"] = "volta"
    card = _card_for(bp.build_projects_block(_registry(projects=[project])), "Volta Neobank")
    assert 'src="volta-neobank.svg"' in card
    assert 'alt="Volta Neobank"' in card


def test_build_projects_block_unknown_project_links_its_title():
    project = _project("Plain", "analytics", href="https://example.test/plain")
    project["slug"] = "plain"
    card = _card_for(bp.build_projects_block(_registry(projects=[project])), "Plain")
    assert "<img" not in card
    assert card.startswith('#### 1. <a href="https://example.test/plain">Plain</a>')


def test_build_projects_block_numbers_cards_across_the_section():
    block = bp.build_projects_block(
        _registry(
            projects=[_project("A", "experiments"), _project("B", "analytics")],
            volta_cases=[_case("V1"), _case("V2")],
        )
    )
    assert [re.match(r"^#### (\d+)\. ", card).group(1) for card in _cards(block)] == ["1", "2"]
    assert [line.split(".", 1)[0] for line in _volta_rows(block)] == ["1", "2"]


def test_build_projects_block_card_has_no_description_text():
    """A card is a directory entry: title, badges, stack — the case study carries the claim."""
    block = bp.build_projects_block(
        _registry(
            projects=[_project("Demo", "analytics", description="16,891 synthetic sales calls.")]
        )
    )
    card = _card_for(block, "Demo")
    assert "16,891 synthetic sales calls" not in card
    assert "**Stack:**" not in card and "#### 1." in card


def test_row_text_appends_result_when_it_adds_numbers():
    record = _project(
        "Demo",
        "analytics",
        description="16,891 synthetic sales calls across 4 funnel steps.",
        result="Funnel drop is 41.2% at the offer step.",
    )
    text = bp._row_text(record)
    assert "16,891 synthetic sales calls" in text and "41.2% at the offer step" in text


def test_row_text_skips_result_that_restates_description():
    description = "CUPED cuts variance 17.7% and the SRM check reads p = 0.8376."
    record = _project(
        "Demo",
        "experiments",
        description=description,
        result="CUPED cuts variance 17.7%; SRM p = 0.8376.",
    )
    text = bp._row_text(record)
    assert text == description
    assert text.count("17.7%") == 1, "a restated result would double the metric"


def test_row_text_skips_result_without_numbers():
    # A result sentence with no measurement is scope restated, not an outcome.
    record = _project(
        "Demo",
        "analytics",
        description="Narrative and visuals stay in sync as the reader scrolls.",
        result="The narrative and the visualization are synchronised.",
    )
    assert "synchronised" not in bp._row_text(record)


def test_row_text_skips_result_that_mostly_restates_description():
    # One new number out of four is not worth a second sentence on the row.
    description = "SRM holds at p=0.266, GCG uplift 0.9968, net effect +50.5."
    record = _project(
        "Demo",
        "experiments",
        description=description,
        result="SRM p=0.266, GCG uplift 0.9968 [0.9433, 1.0502], net effect +50.5.",
    )
    text = bp._row_text(record)
    assert text == description
    assert "0.9433" not in text


def test_build_projects_block_volta_rows_keep_description_only():
    # Volta parts are result-first already; appending star.result would repeat them.
    case = _case(
        "V",
        description="Travelers lose €0.45 per €100 of FX volume.",
        result="Travelers lose €0.45 per €100 of FX volume; break-even needs 0.55%.",
    )
    block = bp.build_projects_block(_registry(volta_cases=[case]))
    volta = block[block.index("<details>") :]
    assert "Travelers lose €0.45 per €100 of FX volume." in volta
    assert "0.55%" not in volta


def test_build_projects_block_volta_row_uses_registered_card():
    """A registered case renders the wordmark card, not a bold text link."""
    case = _case(
        "Volta — Funnel Analysis", href="https://example.test/volta/funnel/", slug="funnel"
    )
    block = bp.build_projects_block(_registry(volta_cases=[case]))
    row = _volta_row_for(block, "Volta — Funnel Analysis")
    assert '<img src="volta-card-funnel.svg"' in row
    assert f'<a href="{case["href"]}">' in row
    assert "**[Volta — Funnel Analysis]" not in row


def test_build_projects_block_volta_card_escapes_alt_text():
    # Titles carry "&" (Retention & Cohorts); a raw one breaks the attribute.
    case = _case("Volta — Retention & Cohorts", href="https://example.test/r/", slug="retention")
    block = bp.build_projects_block(_registry(volta_cases=[case]))
    assert 'alt="Volta — Retention &amp; Cohorts"' in block


def test_build_projects_block_volta_card_falls_back_without_slug():
    """An unregistered case keeps the bold link instead of an <img> that 404s."""
    case = _case("Unmapped Case", href="https://example.test/volta/unmapped/")
    block = bp.build_projects_block(_registry(volta_cases=[case]))
    assert "**[Unmapped Case](https://example.test/volta/unmapped/)**" in block


def test_volta_card_map_matches_files_on_disk():
    """The registry of cards and the shipped assets are the same set."""
    root = Path(bp.__file__).resolve().parent.parent
    on_disk = {path.name for path in root.glob("volta-card-*.svg")}
    assert on_disk == set(bp.VOLTA_CARD_BY_SLUG.values())


def test_volta_cards_use_the_cream_and_blue_palette():
    root = Path(bp.__file__).resolve().parent.parent
    for name in bp.VOLTA_CARD_BY_SLUG.values():
        svg = (root / name).read_text(encoding="utf-8")
        assert 'fill="#F8F2D8"' in svg, f"{name}: no cream card background"
        assert 'fill="#1400C3"' in svg, f"{name}: no blue text"


def test_catalogue_wordmarks_use_the_cream_and_blue_palette():
    root = Path(bp.__file__).resolve().parent.parent
    for slug, name in bp.LOGO_BY_SLUG.items():
        path = root / name
        assert path.exists(), f"{slug}: {name} is missing"
        svg = path.read_text(encoding="utf-8")
        assert 'fill="#F8F2D8"' in svg, f"{slug}: no cream card background"
        assert 'fill="#1400C3"' in svg, f"{slug}: no blue text"


def test_build_projects_block_renders_no_tables():
    """The section is a list; a '| ...' row means a partial migration."""
    block = bp.build_projects_block(
        _registry(projects=[_project("A", "experiments")], volta_cases=[_case("V")])
    )
    assert not any(line.startswith("|") for line in block.splitlines())


# ---------- graphql retry / build resilience ----------


def _http_error(code):
    return urllib.error.HTTPError("https://api.github.com/graphql", code, "err", {}, None)


def test_graphql_retries_transient_5xx_then_raises_unavailable(monkeypatch):
    # A scheduled build died on a burst of 504/502s that outlasted 3 quick tries.
    monkeypatch.setattr(bp, "TOKEN", "x")
    monkeypatch.setattr(bp.time, "sleep", lambda *a, **k: None)
    calls = []

    def boom(*a, **k):
        calls.append(1)
        raise _http_error(502)

    monkeypatch.setattr(bp.urllib.request, "urlopen", boom)
    with pytest.raises(bp.GitHubUnavailable):
        bp.graphql("q", {}, retries=4)
    assert len(calls) == 4, "every attempt must retry a transient status"


def test_graphql_fails_fast_on_permanent_4xx(monkeypatch):
    # A bad token (401) will not heal: no retries, the error surfaces immediately.
    monkeypatch.setattr(bp, "TOKEN", "x")
    monkeypatch.setattr(bp.time, "sleep", lambda *a, **k: None)
    calls = []

    def boom(*a, **k):
        calls.append(1)
        raise _http_error(401)

    monkeypatch.setattr(bp.urllib.request, "urlopen", boom)
    with pytest.raises(urllib.error.HTTPError):
        bp.graphql("q", {}, retries=4)
    assert len(calls) == 1, "a permanent 4xx must not be retried"


def test_graphql_recovers_after_a_transient_failure(monkeypatch):
    monkeypatch.setattr(bp, "TOKEN", "x")
    monkeypatch.setattr(bp.time, "sleep", lambda *a, **k: None)
    state = {"n": 0}

    def flaky(*a, **k):
        state["n"] += 1
        if state["n"] == 1:
            raise _http_error(503)
        return _FakeResponse(b'{"data": {"ok": true}}')

    monkeypatch.setattr(bp.urllib.request, "urlopen", flaky)
    assert bp.graphql("q", {}) == {"ok": True}
    assert state["n"] == 2


def test_main_is_soft_when_github_api_is_unavailable(monkeypatch, capsys):
    # Transient-only: the scheduled refresh must exit 0 and touch nothing, but
    # warn loudly. (A permanent error still propagates — see the language test.)
    monkeypatch.setattr(sys, "argv", ["build_profile.py"])
    monkeypatch.setattr(bp, "fetch_user_data", _raising(bp.GitHubUnavailable("502")))
    touched = []
    monkeypatch.setattr(bp, "write_asset", lambda path, content: touched.append(path))
    monkeypatch.setattr(bp, "update_readme_refresh_block", lambda *a, **k: touched.append("readme"))
    bp.main()
    assert touched == [], "no files may be written when the API is down"
    assert "::warning::" in capsys.readouterr().out
