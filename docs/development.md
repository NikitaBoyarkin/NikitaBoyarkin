# Development notes

Repo hygiene, build pipeline, and the policies behind the profile README.
The rendered artifact is `README.md`; everything here is for whoever maintains it.

## Layout

| Path | What |
|---|---|
| `README.md` | The profile (rendered on github.com/NikitaBoyarkin). |
| `scripts/build_profile.py` | Generates `hero/stats/activity/metrics/contribution-types/monthly-activity/top-languages/projects.svg`, `llms.txt`, `profile.json` + the README "Last refreshed" block. The All Projects block and both GEO files are derived from the projects registry, read from `NikitaBoyarkin.github.io` at `master` (`public/projects.json`). |
| `llms.txt` | Generated compact LLM index: role, headline numbers, every project with its result and case-study URL. Text twin of the SVG cards. |
| `profile.json` | Generated JSON-LD (`Person` + two `ItemList`s) for AI search and ATS parsers. No timestamp: it changes only when the work does. |
| `scripts/preview.sh` | Renders `README.md` locally as GitHub-flavored markdown and opens it in the browser (`scripts/preview.sh`). |
| `tests/test_build_profile.py` | Pure-function tests for the generator (no network). |
| `.github/workflows/ci.yml` | Lint + tests on every push/PR, plus liveness checks for the evidence-ledger and project links. |
| `.github/workflows/profile.yml` | Daily (04:23 UTC) asset refresh; also runs on changes to the generator. |
| `.github/workflows/snake.yml` | Daily contribution-snake refresh. |
| `.github/workflows/update-notes.yml` | Daily "Recent notes" refresh from the site RSS. |

## Commands

```bash
uv sync --all-groups              # dev deps: pytest, pytest-cov, ruff (see [dependency-groups])
uv run pytest                     # tests (pure functions, no network)
uv run ruff check scripts tests   # lint
GH_USER=NikitaBoyarkin GH_TOKEN=$(gh auth token) uv run python scripts/build_profile.py --dry-run
GH_USER=NikitaBoyarkin GH_TOKEN=$(gh auth token) uv run python scripts/build_profile.py
GH_USER=NikitaBoyarkin uv run python scripts/build_profile.py --print-project-links  # one project/repo/case-study URL per line
uv run python scripts/build_profile.py --audit   # local artifact gate (no network)
scripts/preview.sh                # local README preview
```

`GH_USER` selects the GitHub login to render; it never falls back to the shell
`$USER` (which on macOS/Linux is the OS account, not the login). `GH_TOKEN` needs
`read:user`/`repo` scope for the GraphQL calls.

## GEO surface (`llms.txt`, `profile.json`)

The cards are pixels to a crawler; before these two files existed, an AI search
index or an ATS reading this repo saw badge URLs and alt text and had nothing it
could quote. Both are generated from the same registry as the cards, so the count
in the prose, the count in the catalogue and the count in the machine layer cannot
drift apart.

- `llms.txt` — plain-text index: role, headline numbers, availability, then one
  bullet per project (`**title** — result (case-study URL)`) grouped by track in
  syllabus order, then the Volta appendix and contacts. English field preferred
  (`title_en`/`result_en`), falling back to the RU one exactly like the cards.
- `profile.json` — JSON-LD `@graph`: one `Person` (`sameAs` to GitHub, LinkedIn,
  Linktree, Telegram; `knowsAbout` the method list) plus an `ItemList` of portfolio
  works and one of Volta cases. No timestamp, so a rebuild is a no-op.

Both are written by `build_profile.py` only when the registry loads; a registry
outage leaves the old files in place rather than shipping a half-empty index.

## Audit gate (`--audit`)

One local, token-free command, wired into `ci.yml` and into `profile.yml`'s
validate step. It fails on:

| Check | Claim it binds |
|---|---|
| an asset referenced from `README.md` is missing on disk | "self-hosted" means present |
| a committed root `*.svg` no surface references | no orphan art left by a rename |
| `metrics.svg` over the 80 KB budget | the size budget in `docs/prd-v2.md` REQ-018 |
| a `**N projects**` / `**N Volta case studies**` claim in README prose not equal to the generated `llms.txt` count | the hand-written header cannot outrun the work |
| `profile.json` missing, unparsable, or its `ItemList` count off | the machine layer is present and agrees |
| `llms.txt` / `profile.json` absent | GEO surface cannot be silently deleted |

Link liveness stays a separate CI job (`--print-project-links` + HTTP) because it
needs the network; the audit is deterministic, so it can run on every PR.

## Coverage

`scripts/build_profile.py` is covered by `tests/test_build_profile.py` at **~87%**
(network fetch, `main()`, and the CLI path are intentionally not covered — tests
must stay offline). CI runs the same suite with `pytest --cov=scripts`.

## Asset / link pinning policy

- **Self-hosted cards** (`stats`, `activity`, `metrics`, `contribution-types`, `monthly-activity`, `top-languages`, `projects`)
  are referenced from the repo's own `main` via `raw.githubusercontent.com` — no
  third-party render service, zero external requests at render time.
- **Contribution snake** is committed to `main` and referenced from `main`.
- **Project covers** are referenced from the portfolio site
  (`nikitaboyarkin.github.io/images/*`), not copied here: the site owns the art, so
  a renamed or redrawn cover cannot leave a stale copy in this repo. GitHub proxies
  each one through camo, so the rendered profile still issues no third-party request.

## Palette

Single brand palette — 60 / 30 / 10 by area:

| Token | Hex | Share | Role |
|---|---|---|---|
| `BG` / `SURFACE` | `#f8f2da` | 60% | background, card surfaces (cream) |
| `ACCENT` | `#fe4e02` | 30% | primary data, actions (orange) |
| `TEXT_MAIN` | `#1400c3` | 10% | text, highlights (deep blue) |

Defined once in `scripts/build_profile.py`. Secondary tones are **opacity on
these three tokens** — `MUTED_OP` (secondary text), `FAINT_OP` (gridlines,
baselines, empty bars/tiles), `GHOST_OP` (the `Other` language slice) — never
new hex values, so the rendered cards stay exactly 3 colors. One deliberate
exception is semantic and kept: GitHub linguist colors in `top-languages.svg`.

## All Projects cards

The catalogue is one raw-HTML `<table>`: two `<td width="50%" valign="top">` cards
per row, in registry track order (`experiments → analytics → product →
engineering`), padded with an empty cell when the count is odd so the last row does
not stretch to full width.

A card is assembled from the registry alone, in this order:

| Slot | Source | Why |
|---|---|---|
| cover | `COVER_BY_SLUG` → `<site>/images/<file>`, linked to the case study | the site's own 1200×600 diagram, so the profile and the portfolio show the same picture of a project; a slug with no registered cover renders without an image instead of an `<img>` that 404s |
| eyebrow | `track` via `TRACK_PLAIN_LABELS` | a card stays readable out of context — quoted, screenshotted, in a search result |
| title | `title_en`, else `title` | text, not the cream wordmark image the catalogue used before: a heading a screen reader can read beats a branded chip, and the cover above it already carries the brand |
| action badges | repo · **live star count** · demo · case study | raw `<a>`/`<img>`, because GitHub does not run the markdown parser inside a table cell; the star counter is shields' live endpoint, so it needs no rebuild; `flat-square` and a label-less counter keep all four on one line at half-column width; a private repo is not linked (its URL 404s) and gets a `repo-private` badge instead |
| stack badges | `tools`, capped at `TOOL_LIMIT` | flat-square brand badges, one row |

The card carries **no prose**: the case study one click away is where the claim and
its numbers live, and 31 two-sentence blurbs turned the catalogue into a wall of
text. Covers, track labels, titles and stacks all come from `public/projects.json`;
nothing on a card is authored by hand.

### Volta Neobank appendix

The 23 sub-cases use the same card, one level down, inside a collapsed `<details>`:
same `<table>` grid, same badges, no stack row (the registry gives them no `tools`
or `demo`) and **no cover** — the neobank has no per-case art, and the cream
wordmark that used to sit in the row repeats the heading at banner size once
stretched across a card. The eyebrow is the **layer** the case belongs to
(`core → extended → market jobs → RAT v2 → causal`), so a reader knows how far from
the product argument a case sits. Their case-study links keep the `volta` UTM
campaign rather than `featured`, so the appendix stays separable in PostHog.

They stay inside `<details>`: 23 more rows above the Activity section is length
nobody scrolls before deciding whether to keep reading.

## UTM scheme

All outbound section links use one scheme:

```
?utm_source=github&utm_medium=profile_readme&utm_campaign=<section>
```

`<section>` is one of `header`, `featured`, `building`, `notes`, `connect`,
`volta`.

| Section | Links it covers |
|---|---|
| `header` | Portfolio / Links plates and the KYC A/B line at the top |
| `featured` | the two-column card catalogue under **All Projects** (31 cards) |
| `volta` | the collapsed Volta appendix (23 sub-cases) |
| `notes` | the RSS-generated "Recent notes" list — scheme applied by the `template` input in `update-notes.yml` |
| `building` | the "Currently building" line |
| `connect` | the contact plates at the bottom |

Catalogue and appendix links also carry **`utm_content=<project slug>`**, so
per-project clicks are separable without inventing a campaign per project. Both
are emitted by `scripts/build_profile.py` (`_utm`), which tags the site host
only — repo links (github.com) and the raw asset host stay untagged, and a link
that already carries `utm_campaign` is left alone.

No PII in UTMs. UTM is deliberately **not** applied to `rss.xml`: feed readers
re-fetch and re-share the URL, so a tag there manufactures campaign hits that
never happened. Aggregation runs on the portfolio site's PostHog — dashboard
06 "UTM-кампании" in `NikitaBoyarkin.github.io/monitoring/dashboards/`; the
redirect-service plan in REQ-027 (`docs/prd-v2.md`) stays deferred.

## CI self-loop protection

The daily asset job writes files and commits them, so it must never trigger
itself:

- `concurrency` with `cancel-in-progress: true` on every workflow.
- autogenerated commits carry `[skip ci]`.
- `profile.yml`'s `on.push.paths` does **not** include `**.svg`.
- `build_profile.py` writes idempotently: an asset is left untouched if only its
  rendered timestamp differs, so a no-op day produces at most the meaningful
  "Last refreshed" README commit.
- `enable_keepalive: false` on the RSS workflow (no dummy empty commits).
- `projects.svg` is committed by `profile.yml` alongside the other generated assets.
- A project-links liveness job runs `build_profile.py --print-project-links` and
  checks every URL the block renders — repo, case study, cover and demo — so a
  stale registry, a renamed cover or a dead link surfaces in CI instead of
  silently dropping out of the README.
