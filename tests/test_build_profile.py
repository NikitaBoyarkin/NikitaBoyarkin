"""Tests for scripts/build_profile.py — pure functions only (no network).

Run: python3 -m pytest tests/test_build_profile.py -v
"""

import math
import re
import sys
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
    monkeypatch.setattr(bp, "update_readme_refresh_block", lambda days: False)
    monkeypatch.setattr(bp, "fetch_languages", _raising(languages_exc))
    monkeypatch.setattr(bp.logging, "exception", lambda *a, **k: logged.append(a))
    return logged


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


# --- analytics-evidence ledger ------------------------------------------------

ALLOWED_EVIDENCE_HOSTS = {"github.com", "nikitaboyarkin.github.io"}


def test_analytics_evidence_rows_are_complete():
    assert bp.ANALYTICS_EVIDENCE, "ledger is empty"
    for row in bp.ANALYTICS_EVIDENCE:
        assert row["method"].strip()
        assert row["evidence"].strip()
        assert row["confidence"] in {"HIGH", "MODERATE", "GAP"}


def test_analytics_evidence_methods_are_unique():
    methods = [row["method"] for row in bp.ANALYTICS_EVIDENCE]
    assert len(methods) == len(set(methods))


def test_analytics_evidence_urls_are_https_on_allowlisted_hosts():
    import urllib.parse

    for row in bp.ANALYTICS_EVIDENCE:
        if not row["repo"]:
            # A row without a source is a declared gap, not an unproven claim.
            assert row["confidence"] == "GAP"
            continue
        parsed = urllib.parse.urlparse(bp.evidence_url(row["repo"]))
        assert parsed.scheme == "https", row["url"]
        assert parsed.hostname in ALLOWED_EVIDENCE_HOSTS, row["url"]


def test_analytics_evidence_fits_the_card():
    proven = [row for row in bp.ANALYTICS_EVIDENCE if row["repo"]]
    gaps = [row for row in bp.ANALYTICS_EVIDENCE if not row["repo"]]
    assert len(proven) <= 8, "card height is fixed; more rows overflow the viewBox"
    assert len(gaps) <= 1, "keep the gap list to one row, not a second section"


def test_evidence_sources_are_distinct_and_ordered():
    urls = bp.evidence_sources()
    assert urls == list(dict.fromkeys(urls)), "sources must be de-duplicated in ledger order"
    covered = {bp.evidence_url(row["repo"]) for row in bp.ANALYTICS_EVIDENCE if row["repo"]}
    assert set(urls) == covered


def test_analytics_evidence_svg_is_well_formed_and_accessible():
    svg = bp.build_analytics_evidence_svg()
    root = ET.fromstring(svg)
    assert root.attrib["role"] == "img"
    assert root.attrib["aria-label"].strip()
    assert root.find("{http://www.w3.org/2000/svg}title") is not None


def test_analytics_evidence_svg_names_every_method():
    svg = bp.build_analytics_evidence_svg()
    for row in bp.ANALYTICS_EVIDENCE:
        assert bp._esc(row["method"]) in svg, row["method"]


def test_analytics_evidence_svg_is_within_budget():
    svg = bp.build_analytics_evidence_svg()
    assert len(svg.encode("utf-8")) < 20_000


def test_analytics_evidence_svg_escapes_untrusted_values(monkeypatch):
    hostile = (
        {
            "method": "A&B <script>",
            "evidence": '"quoted" & <tag>',
            "confidence": "HIGH",
            "repo": "x",
        },
    )
    monkeypatch.setattr(bp, "ANALYTICS_EVIDENCE", hostile)
    svg = bp.build_analytics_evidence_svg()
    assert "&amp;" in svg and "&lt;script&gt;" in svg
    assert "<script>" not in svg
    ET.fromstring(svg)


def test_chip_labels_clear_the_aa_contrast_floor():
    """A chip label drawn translucent over a translucent pill blends twice.

    GHOST_OP cream on this card is ~3.6:1, and MODERATE-over-MODERATE ~2.9:1 — both
    miss WCAG AA's 4.5:1 for small text. Every chip label must stay >= MUTED_OP (~5.8:1).
    """
    root = ET.fromstring(bp.build_analytics_evidence_svg())
    svg_text = "{http://www.w3.org/2000/svg}text"
    labels = {"HIGH", "MODERATE", "GAP"}
    chips = [el for el in root.iter(svg_text) if (el.text or "") in labels]
    assert len(chips) == len(bp.ANALYTICS_EVIDENCE)
    for el in chips:
        op = float(el.attrib.get("fill-opacity", "1"))
        assert op >= float(bp.MUTED_OP), f"{el.text} chip at opacity {op} fails AA"


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


# ---------- evidence reconciliation ----------

_ALL_PUBLIC = {"volta-banking", "causal-uplift", "ab_test", "sql-analytics-case-study", "airflow"}


def test_reconcile_keeps_rows_whose_repo_is_public():
    rows, warnings = bp.reconcile_evidence(_ALL_PUBLIC)
    assert warnings == []
    assert rows == list(bp.ANALYTICS_EVIDENCE)
    assert rows is not bp.ANALYTICS_EVIDENCE  # a fresh list, not the ledger itself


def test_reconcile_withdraws_rows_whose_repo_vanished():
    rows, warnings = bp.reconcile_evidence({"volta-banking"})
    # The row that was already a declared gap (repo == "") is neither kept nor withdrawn.
    expected = [r for r in bp.ANALYTICS_EVIDENCE if r["repo"] and r["repo"] != "volta-banking"]
    withdrawn = [r for r in rows if "no longer public" in r["evidence"]]
    assert len(withdrawn) == len(expected) == 5
    for row in withdrawn:
        assert row["confidence"] == "GAP"
        assert row["repo"] == "", "a withdrawn claim must not keep its link"
        assert bp.evidence_url(row["repo"]) == ""
    assert warnings and all("is not public" in w for w in warnings)


def test_reconcile_with_empty_repo_list_keeps_every_row():
    """An empty list is missing data, not evidence that every repo is gone."""
    rows, warnings = bp.reconcile_evidence(set())
    assert rows == list(bp.ANALYTICS_EVIDENCE)
    assert len(warnings) == 1


def test_reconcile_does_not_mutate_the_ledger():
    before = [dict(r) for r in bp.ANALYTICS_EVIDENCE]
    bp.reconcile_evidence(set())
    bp.reconcile_evidence({"volta-banking"})
    assert [dict(r) for r in bp.ANALYTICS_EVIDENCE] == before


def test_public_repo_names_reads_the_repository_nodes():
    data = {"user": {"repositories": {"totalCount": 2, "nodes": [{"name": "a"}, {"name": "b"}]}}}
    assert bp.public_repo_names(data) == {"a", "b"}
    # Payload without nodes (older query shape) must not raise.
    assert bp.public_repo_names({"user": {"repositories": {"totalCount": 2}}}) == set()


# ---------- generated README evidence-sources line ----------


def test_evidence_sources_line_lists_each_repo_once_with_its_url():
    line = bp.build_evidence_sources_line()
    assert line.startswith("<sub>Sources: ") and line.endswith("</sub>")
    for repo in dict.fromkeys(r["repo"] for r in bp.ANALYTICS_EVIDENCE if r["repo"]):
        assert f'<a href="{bp.evidence_url(repo)}">{repo}</a>' in line
    assert line.count("volta-banking</a>") == 1, "repo used by 3 rows must appear once"


def test_sync_evidence_sources_block_rewrites_and_is_idempotent():
    doc = "x\n<!-- EVIDENCE-SOURCES:START -->\n<sub>stale</sub>\n<!-- EVIDENCE-SOURCES:END -->\ny\n"
    out = bp.sync_evidence_sources_block(doc)
    assert "stale" not in out
    assert bp.build_evidence_sources_line() in out
    assert bp.sync_evidence_sources_block(out) == out


def test_sync_evidence_sources_block_without_marker_is_untouched():
    doc = "x\n<sub>Sources: hand typed</sub>\n"
    assert bp.sync_evidence_sources_block(doc) == doc


def _repo_readme() -> str:
    return (Path(__file__).resolve().parent.parent / "README.md").read_text(encoding="utf-8")


def test_readme_evidence_sources_block_is_in_sync():
    """README drift is impossible: CI compares the block against the ledger."""
    match = re.search(
        r"<!-- EVIDENCE-SOURCES:START -->\n(.*?)\n<!-- EVIDENCE-SOURCES:END -->",
        _repo_readme(),
        re.DOTALL,
    )
    assert match, "EVIDENCE-SOURCES marker missing from README"
    assert match.group(1) == bp.build_evidence_sources_line()


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
        "analytics-evidence": bp.build_analytics_evidence_svg(),
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
