# PRD v2: GitHub Profile README — credibility и техдолг

**Автор:** Nikita Boyarkin
**Дата:** 2026-09-18
**Статус:** Executed — P0/P1 закрыты (см. §11). Остаются только time-gated и внешние проверки: 7-дневный чекпойнт CI (REQ-014/019), Lighthouse/LCP (NFR), REQ-026/027/028.
**Версия:** 2.0
**Предшественник:** `docs/prd.md` (v1.1, 8 из 13 REQ закрыто)

> **Роль:** v1 строился вокруг измерения воронки (PostHog, UTM). v2 меняет приоритет: сначала **доверие** (найм зависит от проверяемости, а не от дашборда) и **технический долг** (CI-петля жжёт Actions и мусорит историю), затем — конверсия. Измерение воронки (PostHog + редирект-сервис) переведено в deferred (REQ-027).
>
> **Что НЕ дублируется из v1:** self-host top-langs (REQ-003), реордер секций (REQ-006), игры (REQ-001), ретраи/`--dry-run` (REQ-010), `preview.sh` (REQ-012), snake в main (REQ-013) — уже сделано, в v2 не переделывается.

---

## 1. Executive Summary

Профиль `NikitaBoyarkin/NikitaBoyarkin` — первая точка контакта рекрутера с кандидатом. Контент сильный (позиционирование, 3 featured-кейса с метриками, 8 SVG-игр, self-hosted stats), но вскрыты три системные проблемы, которых не было в v1:

1. **CI самовоспроизводится.** `profile.yml` триггерится на push изменённых `*.svg` и сам же коммитит `*.svg` с таймстампом через PAT → 7–8 коммитов за ~105 секунд, ежедневно, бесконечно. Нет `concurrency`, нет `[skip ci]`, запись не идемпотентна.
2. **Credibility-дыры.** Один из трёх featured-репозиториев **приватный** (`supabase-product-analytics` → 404 у рекрутера), счётчик просмотров **накручен** (`extra_count=124`), метрики (`€716K/yr`, `48× ROI`, `+6.24pp`) **не проверяемы** в один клик, а проверяемого опыта/отзывов нет вообще.
3. **Техдолг недозакрыт.** PRD v1 объявил REQ-011 и REQ-009 `[DONE]`, но empty-commits живы в трёх местах, а pytest не запускается в CI.

Решение v2 — закрыть доверие и долг до любой новой аналитики: разорвать CI-петлю, убрать накрутку, сделать метрики проверяемыми, self-host slim-метрики, удалить keepalive, поставить тесты в CI.

## 2. Context & Baseline

### Фактическое состояние (замер 2026-09-18)

| Область | Baseline | Источник |
|---|---|---|
| metrics.svg | **365 963 B (~357 KiB)**, цель ≤80 KB | `metrics.svg` |
| CI-петля | **7 коммитов за 105 сек** (09:01:53→09:03:38) | `git log origin/main` |
| `concurrency` в workflow | **отсутствует** во всех 5 workflow | `.github/workflows/` |
| Тесты в CI | **не запускаются** (pytest не упомянут в `.github/`) | `.github/workflows/` |
| Зависимости объявлены | **нет** `pyproject.toml` / `requirements.txt` | корень |
| keepalive empty-commit | **жив в 3 местах**: `keepalive.yml:31`, `scripts/keepalive.sh:16`, launchd plist (22:00) | файлы |
| Приватная ссылка | `supabase-product-analytics` → **404** для посетителя | `README.md:84-90` |
| Накрутка просмотров | `extra_count=124` | `README.md:67` |
| Метрики без источника | `+6.24pp`, `Z=6.35`, `€716K/yr`, `48× ROI`, `p=0.0034` | `README.md:77,86` |
| Проверяемый опыт/отзывы | **отсутствуют** (только TODO) | `README.md:73` (TODO P1.3) |
| Игры | **не играбельны на профиле** — статичные `<img>`; скрипт исполняется только после клика по jsDelivr | `README.md:105-201`, `*.svg` |
| a11y игровых SVG | `role`/`<title>`/`<desc>`/`aria-*` — **0 совпадений** | 8 игровых SVG |
| Пиннинг ассетов | гибрид: **5 pinned SHA + 3 `@main`**, политика не задокументирована | `README.md:108-195` |
| Footer credits | 3 из 7 кредитов ложные (указывают на снятые сервисы) | `README.md:285` |
| Дрейф документов | `PLAN.md` устарел (число игр, статусы), `docs/prd.md` завышает статусы | `PLAN.md`, `docs/prd.md` |
| Git-база | локальный `main` **на 72 коммита позади** `origin/main`; ветка `origin/output` жива | `git status` |
| `streak.svg` | дублировал 3 метрики из `stats.svg` → слит в stats, файл удалён | `build_profile.py` |

### Воронка

`profile view → scroll → click portfolio → case study → contact`

| Тип | Метрика | Сейчас | Цель |
|---|---|---|---|
| North Star | Контакты от рекрутеров / мес | не измеряется | тренд ↑ |
| Guardrail | Вес `metrics.svg` / LCP | не измеряется | ≤80 KB / <2s LCP |
| Secondary | CTR portfolio-ссылки | UTM без агрегации | дашборд |
| Counter | Время на играх vs конверсия | — | не каннибализует CTR кейсов |

Измерение воронки (PostHog + редирект-сервис) — deferred, REQ-027.

### Влияние на пользователя

- **Кто затронут:** рекрутеры, найм-менеджеры, коллеги-аналитики.
- **Как затронут:** клик по сильнейшему кейсу ведёт в 404 (теряется доверие), накрутка просмотров читается как нечестность, непроверяемые цифры обесценивают реальный аналитический навык, «играбельные» карточки вводят в заблуждение.
- **Серьёзность:** High для цели найма. Профиль не сломан технически, но работает против себя на доверии.

### Почему решать сейчас

Кандидат активно интервьюируется; профиль показывают рекрутерам прямо сейчас. CI-петля ежедневно жжёт Actions-минуты и засоряет историю, а credibility-дыры видны первым же кликом. Это дешевле всего починить до следующей волны откликов.

## 3. Goals & Non-goals

### Goals & Success Metrics

#### Goal 1: Credibility — профиль не ломает доверие
- **Метрика:** число «мёртвых»/вводящих в заблуждение элементов профиля.
- **Baseline:** 1 приватный 404 + 1 накрутка (`extra_count=124`) + 5 непроверяемых цифр.
- **Target:** **0**; каждая метрика проверяема в 1 клик.
- **Срок:** Phase 1.
- **Метод измерения:** ручной аудит ссылок (HTTP 200) + ревизия формулировок.

#### Goal 2: Технический долг — CI не работает против себя
- **Метрика:** число самовоспроизводящихся коммитов в сутки; прогон тестов в CI.
- **Baseline:** 7–8 loop-коммитов/сутки; тесты в CI — 0.
- **Target:** **0** loop-коммитов; pytest зелёный на каждый push.
- **Срок:** Phase 1.
- **Метод измерения:** `git log --oneline --since="1 day" | wc -l`, статус workflow.

#### Goal 3: Производительность профиля
- **Метрика:** вес `metrics.svg`; LCP; число внешних запросов при рендере карточек.
- **Baseline:** 357 KiB; LCP не измеряется; lowlighter — внешний.
- **Target:** ≤80 KB; LCP < 2s; **0** внешних запросов при рендере метрик.
- **Срок:** Phase 1.
- **Метод измерения:** размер файла, Lighthouse на `github.com/NikitaBoyarkin`.

#### Goal 4: Консистентность и гигиена репозитория
- **Метрика:** дрейф документов и политик; состояние git.
- **Baseline:** 72 коммита позади, ветка `output`, ложные credits, `USER`-баг, двойной GraphQL, гибридный пиннинг.
- **Target:** `main` синхронизирован; 0 известных дрейфов; единая политика пиннинга.
- **Срок:** Phase 1–2.
- **Метод измерения:** `git status`, чек-лист аудита.

### Non-goals (v2 не делает)

1. **Полный редизайн README** — точечные правки.
2. **Измерение воронки (PostHog + редирект-сервис)** — deferred до REQ-027.
3. **Правки сайта `Personal_Projects.github.io`** — внешняя зависимость (REQ-028).
4. **Новые игры / расширение игровой секции.**
5. **Платная аналитика.**

## 4. User Stories

### Story 1: Рекрутер проверяет кандидата
**As a** рекрутер, **I want to** открыть любой featured-кейс и увидеть проверяемые цифры, **So that I can** доверять профилю.

**Acceptance Criteria:**
- [x] Ни одна featured-ссылка не ведёт в 404/приватную страницу. _(volta / sql — публичные репо HTTP 200; supabase — приватный репо заменён бейджем `Case study` → HTTP 200.)_
- [x] Каждая цифра-метрика имеет рабочую ссылку на источник (кейс на сайте). _(у каждого featured-проекта бейдж `Case study` → `/projects/<slug>/` HTTP 200; `€716K/yr` и `48× ROI` убраны вместо неподкреплённых.)_ 
- [x] Счётчик просмотров честный (без `extra_count`).
- [x] Позиционирование под Data/Product Analyst читается без скролла. _(H2 «Data / Product Analyst (Middle+)» — первая содержательная строка.)_

**Dependencies:** REQ-015, REQ-016, REQ-017, REQ-025

### Story 2: Найм-менеджер оценивает глубину
**As a** найм-менеджер, **I want to** видеть методологию за цифрами, **So that I can** оценить реальный уровень аналитика.

**Acceptance Criteria:**
- [x] ROI/lift-заявления подкреплены методологией или смягчены до доказанного. _(`€716K/yr` и `48× ROI` убраны; остались lift / p-value / конверсии, каждая карточка ссылается на кейс.)_
- [x] Featured-проекты ведут на публичный код или публичный кейс.

**Dependencies:** REQ-015, REQ-017

### Story 3: Коллега-аналитик смотрит игры
**As a** коллега, **I want to** понимать, что карточка ведёт в игру, **So that I can** сыграть без разочарования.

**Acceptance Criteria:**
- [x] Рядом с активными карточками явно сказано «открывается в новой вкладке». _(блокquote под игровой сеткой.)_
- [x] Игровые SVG имеют `<title>`/`<desc>`/`role="img"`. _(все 8 файлов: `snake, ab-test, pong, 2048, funnel-drop, cohort-catch, sql-query, metric-match`.)_
- [x] Политика ссылок на игры единообразна (`@main`).

**Dependencies:** REQ-022

## 5. Functional Requirements

### Must Have (P0) — критично

#### REQ-014: Разорвать CI-петлю самовоспроизведения `[P0]`
**Описание:** Автогенерация ассетов с таймстампом триггерит сама себя. Ввести `concurrency`, коммитить автогенерации с `[skip ci]`, сузить `on.push.paths` (не по `*.svg`), сделать запись идемпотентной (не коммитить, если контент не изменился).

**Acceptance Criteria:**
- [x] `concurrency` с `cancel-in-progress: true` добавлен в `profile.yml` (и остальные генераторы). _(все 4 workflow: `profile`, `ci`, `snake`, `update-notes`.)_
- [x] Автокоммит содержит `[skip ci]`. _(все автокоммит-шаги.)_
- [x] `on.push.paths` не включает `**.svg`. _(только `scripts/build_profile.py` и сам workflow.)_
- [x] `build_profile.py` не перезаписывает файл, если содержимое не изменилось (кроме штатного daily refresh). _(`write_asset` вырезает таймстамп перед сравнением; README refresh-блок намеренно обновляется раз в сутки — это и есть штатный meaningful refresh.)_
- [ ] За 7 дней наблюдения — 0 loop-коммитов (≤1/сутки штатный refresh). **[time-gated — проверить через 7 дней]**

**Техническая спецификация:**
```yaml
concurrency:
  group: profile-build
  cancel-in-progress: true
# commit message: "chore: update profile assets [skip ci]"
```

**Dependencies:** None

#### REQ-015: Приватный featured-репозиторий → Case study `[P0]`
**Описание:** `supabase-product-analytics` приватный (`README.md:88`) — бейдж `Repo` ведёт в 404. Заменить на бейдж `Case study`, ведущий на существующий публичный кейс `https://nikitaboyarkin.github.io/Personal_Projects.github.io/projects/supabase/` (HTTP 200).

**Acceptance Criteria:**
- [x] Для проекта Supabase бейдж `Repo` заменён на `Case study`.
- [x] Ссылка ведёт на `/Personal_Projects.github.io/projects/supabase/` (с base, не root-relative).
- [x] Бейдж `Case study` есть у **всех трёх** featured-проектов.
- [x] Все featured-ссылки возвращают HTTP 200 для анонимного посетителя. _(volta/supabase/sql case-study URL и public repos: 200; приватный supabase-repo отдаёт 404 и больше нигде не залинкован.)_

**Dependencies:** None. Внешняя зависимость: REQ-028 (кейс уже существует, ссылаемся).

#### REQ-016: Убрать накрутку счётчика просмотров `[P0]`
**Описание:** `hits.sh` на `README.md:67` использует `extra_count=124` — искусственная надбавка. Убрать параметр; оставить честный счётчик либо отключить вовсе.

**Acceptance Criteria:**
- [x] Параметр `extra_count` удалён из URL счётчика.
- [x] Счётчик отображает реальное значение. _(URL счётчика без каких-либо надбавок.)_

**Dependencies:** None

#### REQ-017: Верифицируемость метрик `[P0]`
**Описание:** Цифры без источника подрывают доверие. Вариант Q13-A + Q21-B: метрики остаются, но каждая получает прямую ссылку на методологию/кейс; `€716K/yr` и `48× ROI` смягчаются до доказанного (lift, p-value, конверсии) до публикации ROI-методологии на сайте.

**Acceptance Criteria:**
- [x] У каждой заявленной метрики есть ссылка на источник (кейс/методология на сайте). _(бейдж `Case study` на каждой featured-карточке.)_
- [x] `48× ROI` и `€716K/yr` убраны либо подкреплены ссылкой на методологию — иначе смягчены до lift/p/конверсий. _(убраны из профиля; остались `+6.24pp (Z=6.35, p<0.0001)` и `p=0.0034`.)_
- [x] `p=0.0034` и `+5.1 пп` (Supabase) ведут на `/projects/supabase/`. _(карточка Supabase → `Case study`.)_
- [x] Терминология метрик согласована с сайтом (нет расхождений в цифрах). _(`+6.24pp` ↔ сайт `+6,24 пп`; `p=0.0034` ↔ сайт `p = 0.0034`.)_ **[manual]**

**Dependencies:** REQ-015; внешняя — REQ-028.

#### REQ-018: Slim self-hosted metrics + стрики без дублей `[P0]`
**Описание:** Выкинуть `lowlighter/metrics` из `metrics.yml` и self-host slim-карточку метрик в `build_profile.py`. Стрики (`Current/Longest`) оставить только в `stats.svg`: отдельная `streak.svg` дублировала те же числа, что уже были в stats, и удалена из пайплайна.

**Acceptance Criteria:**
- [x] `metrics.svg` весит ≤80 KB и генерируется `build_profile.py`. _(44 921 B ≈ 44 KB; `build_metrics_svg` в генераторе; headline-числа убраны — heatmap без дублей.)_
- [x] `metrics.yml` больше не тянет `lowlighter/metrics`. _(workflow удалён; `lowlighter` не встречается.)_
- [x] В рендере карточек метрик — **0 внешних запросов**. _(все карточки — `raw.githubusercontent.com/<repo>/main/*.svg`, self-hosted.)_
- [x] Стрики и суммарные числа не дублируются: живут только в `stats.svg`; отдельная `streak.svg` удалена из пайплайна и README (сирот нет). _(2026-09-18: `build_streak_svg` и `streak.svg` удалены.)_
- [x] Карточка корректна в light/dark-режимах GitHub. _(карточки с собственным непрозрачным фоном `#1400c3` — тема GitHub не влияет.)_ **[manual]**

**Dependencies:** REQ-014 (стабильный CI), REQ-020 (тесты).

#### REQ-019: Полное удаление keepalive `[P0]`
**Описание:** Пустой коммит жив в трёх местах (`keepalive.yml:31`, `scripts/keepalive.sh:16`, launchd plist 22:00) — TOS-риск и мусор истории; при daily build-коммите не нужен. Удалить всё трое.

**Acceptance Criteria:**
- [x] `keepalive.yml` удалён.
- [x] `scripts/keepalive.sh` удалён.
- [ ] launchd plist (`com.nikitaboyarkin.keepalive.plist`) удалён/выгружен. **[вне репо — проверить у владельца]**
- [x] `--allow-empty` не встречается в репозитории. _(только текст этого критерия в PRD.)_
- [ ] Репозиторий остаётся активным за счёт daily build-коммита (проверка 7 дней). **[time-gated — проверить через 7 дней]**

**Dependencies:** REQ-014 (стабильный meaningful refresh).

### Should Have (P1) — важно

#### REQ-020: Тесты в CI + pyproject/ruff `[P1]`
**Описание:** PRD v1 объявил тесты `[DONE]`, но CI их не запускает, а зависимости не объявлены. Добавить `pyproject.toml` (pytest/ruff) и шаг прогона в workflow.

**Acceptance Criteria:**
- [x] Есть `pyproject.toml` с pytest (и ruff).
- [x] Шаг `pytest` есть в CI и зелёный на каждый push. _(`.github/workflows/ci.yml`: `ruff check` + `pytest --cov`; локально 19 passed.)_
- [x] Покрытие `build_profile.py` измерено и задокументировано. _(~68%, `docs/development.md` §Coverage.)_
- [x] Тесты не делают сетевых вызовов (моки GraphQL). _(`tests/test_build_profile.py` — только чистые функции.)_

**Dependencies:** None

#### REQ-021: Гигиена и устранение дрейфа `[P1]`
**Описание:** Пакет мелких дефектов: ложные footer-credits (`README.md:285` — 3 из 7 указывают на снятые сервисы), `USER`-env-баг (`build_profile.py:28`), двойной GraphQL-запрос (`main()` + `fetch_contributions()`), устаревший `PLAN.md`, завышенные статусы `docs/prd.md`, недокументированный `preview.sh`, ветка `origin/output`, гибридный пиннинг ассетов.

**Acceptance Criteria:**
- [x] Footer credits перечисляют только реально используемые сервисы. _(snk, blog-post-workflow, skill-icons, shields.io, jsDelivr — все используются.)_
- [x] `USER` берётся из GitHub-контекста/аргумента, а не из lowercase `$USER`. _(`GH_USER` env → `DEFAULT_USER`, плюс `--user`.)_
- [x] Двойной GraphQL-запрос устранён (один fetch за прогон). _(`extract_contributions` принимает уже полученные данные.)_
- [x] `PLAN.md` синхронизирован с фактом (игры, статусы P0–P2). _(стал навигационным указателем на prd-v2 / development.)_
- [x] `docs/prd.md` статусы приведены к факту. _(свёрнут в исторический индекс, полный текст — в git-истории.)_
- [x] `preview.sh` задокументирован в README репозитория. _(`docs/development.md` §Layout/Commands.)_
- [x] Ветка `origin/output` удалена. _(осталась только `main`.)_
- [x] Единая политика пиннинга ассетов задокументирована. _(`docs/development.md` §Asset / link pinning policy.)_

**Dependencies:** None

#### REQ-022: Игры — честный label + a11y + единый пиннинг `[P1]`
**Описание:** Игры не играбельны на профиле (статические `<img>`; интерактив только после клика по jsDelivr). Сделать это честным и доступным: явный label «открывается в новой вкладке», `<title>`/`<desc>`/`role="img"`, понизить визуальный вес, унифицировать ссылки на `@main`.

**Acceptance Criteria:**
- [x] Рядом с игровой сеткой явно указано, что игра открывается в новой вкладке (не создаёт впечатления инлайн-игры).
- [x] В каждом игровом SVG есть `<title>`/`<desc>`/`role="img"` или эквивалент. _(8/8 файлов.)_
- [x] Все игровые ссылки ассетов указывают на `@main` (гибрид устранён).
- [ ] Игровая секция не доминирует над featured-проектами (визуальный вес). **[manual — относится к open Q9: урезать игры до 4]**
- [ ] README рендерится корректно на мобильном. **[manual — визуальная проверка]**

**Dependencies:** REQ-021 (политика пиннинга).

#### REQ-023: UTM-консистентность `[P1]`
**Описание:** Часть секций без UTM (Recent Notes, Games, Tech Stack, Stats/Activity). Без редирект-сервиса (deferred) закрываем консистентность меток на оставшихся секциях, чтобы при включении аналитики данные были готовы.

**Acceptance Criteria:**
- [x] Все исходящие ссылки разделов имеют согласованную UTM-схему (`utm_source=github&utm_medium=profile_readme&utm_campaign=<section>`). _(header, cv, featured, building, notes, connect; notes — через `template` в `update-notes.yml`.)_
- [x] Нет UTM с PII.
- [x] Схема задокументирована. _(`docs/development.md` §UTM scheme.)_

**Dependencies:** None (REQ-027 deferred).

#### REQ-024: «Currently building» — рабочая ссылка `[P1]`
**Описание:** Строка «Building: interactive analyst portfolio» (`README.md:24`) без ссылки. Добавить рабочую ссылку на активный проект.

**Acceptance Criteria:**
- [x] «Currently building» указывает на реальный активный проект ссылкой. _(портфолио, UTM `building`.)_
- [x] Ссылка возвращает HTTP 200.

**Dependencies:** None

#### REQ-025: Позиционирование под Data/Product Analyst `[P1]`
**Описание:** Целевая роль — Data/Product Analyst, Middle/Middle+. Выровнять заголовок/терминологию и порядок верхнего блока так, чтобы роль и доказательства читались без скролла.

**Acceptance Criteria:**
- [x] Заголовок и первая строка явно называют роль (Data/Product Analyst). _(H2 «Data / Product Analyst» + строка «(Middle+)».)_
- [x] Featured-кейсы и CTA доступны выше секции игр.
- [x] Терминология согласована с сайтом. _(роль и метрики совпадают с кейсами.)_ **[manual]**

**Dependencies:** REQ-017

#### REQ-026: Experience / recommendations `[P1] [PENDING INPUT]`
**Описание:** Проверяемого опыта/отзывов нет. Требование заведено с явным статусом *blocked pending input*; добавляем только настоящие данные (без выдуманных отзывов). После получения фактов — отдельная секция.

**Acceptance Criteria:**
- [ ] Получены реальные данные (роли/компании/даты и/или отзыв с разрешением автора). **[PENDING INPUT]**
- [ ] Секция добавлена только при наличии проверяемого источника. **[PENDING INPUT]**
- [x] Выдуманные отзывы отсутствуют (placeholder TODO удалён либо заменён реальным). _(TODO P1.3 удалён из README; пустой секции нет.)_

**Dependencies:** внешний ввод (не блокирует P0).

### Nice to Have (P2) / Deferred

#### REQ-027: PostHog + редирект-сервис (deferred) `[P2]`
**Описание:** Измерение исходящих кликов требует внешнего редирект-сервиса (Cloudflare Worker) + PostHog-проекта. Для цели найма ROI низкий, инфраструктура дорогая → **deferred** из v1 до появления свободного ресурса. Гайд: [`docs/posthog-setup.md`](posthog-setup.md).

**Acceptance Criteria (когда будет разблокировано):**
- [ ] Редирект-сервис разворачивается и трекает клики.
- [ ] PostHog-проект принимает события.
- [ ] Дашборд CTR по секциям.

**Dependencies:** REQ-023 (UTM готовы).

#### REQ-028: Внешняя зависимость — дополнение сайт-кейсов `[P2] [EXTERNAL]`
**Описание:** Часть правок требует соседнего репозитория `Personal_Projects.github.io`: добавить `n=8000` в кейс Supabase (сейчас только профиль), опубликовать ROI-методологию Volta для восстановления `€716K/yr`/`48× ROI`. **Вне скоупа исполнения этого PRD** — фиксируется как зависимость.

**Acceptance Criteria (в соседнем репо):**
- [ ] Кейс Supabase содержит размер выборки.
- [ ] Кейс Volta содержит методологию ROI.

**Dependencies:** управляется отдельно.

## 5.1 Итерация v2.1 — новые self-hosted графики

#### REQ-029: Contribution types + Monthly activity `[P2] [DONE]`
**Описание:** Добавить два self-hosted графика, дающих **новую** информацию (без дублей уже показанных чисел): разбивка вклада по типам (`Commits / Pull Requests / Issues / Code Reviews`) и помесячная динамика за 12 месяцев. Оба — из GitHub GraphQL, в палитре профиля, 0 внешних запросов.

**Acceptance Criteria:**
- [x] `contribution-types.svg` — горизонтальные бары, данные из `contributionsCollection` (`build_contribution_types_svg`).
- [x] `monthly-activity.svg` — вертикальные бары по месяцам из того же calendar (`build_monthly_activity_svg`).
- [x] Оба — self-hosted через `raw.githubusercontent.com/<repo>/main/*.svg`, 0 внешних запросов.
- [x] Новые поля добавлены в единственный GraphQL-запрос (`totalCommit/PR/Issue/ReviewContributions`) — по-прежнему 1 запрос за прогон.
- [x] Оба подключены в README (секция ⚡ Activity), в `profile.yml` `file_pattern` и покрыты тестами.
- [x] Числа не дублируют stats/metrics (types — декомпозиция, monthly — временной ряд).

**Dependencies:** REQ-014 (стабильный CI), REQ-029 наследует бюджет REQ-018.

## 6. Non-Functional Requirements

### Performance
- `metrics.svg` ≤80 KB; карточки метрик — 0 внешних запросов при рендере.
- **LCP профиля < 2s — недостижимо из этого репо.** Замер 2026-09-18 (Lighthouse 12):
  desktop `LCP 4.2s`, `FCP 1.4s`, `TBT 0ms`, `CLS 0.001`, perf 0.70; mobile-sim `LCP 10.2s`,
  perf 0.45. Все opportunities — ресурсы github.com (`unused-css 134 KiB`, `unused-js 313 KiB`),
  не наши карточки. Наш вклад — векторные SVG ≤44 KB, часть лениво. Реальный repo-контролируемый
  бюджет: суммарный вес self-hosted карточек ≤ 80 KB на карточку.

### Reliability
- Ни один workflow не запускает сам себя (0 loop-коммитов).
- Все featured-ссылки → HTTP 200 для анонимного посетителя.

### Security
- Секретов нет в README/SVG (токены — в GitHub Secrets).
- Только `https`; UTM без PII.

### Accessibility
- Игровые SVG имеют `<title>`/`<desc>`/`role="img"`.
- Alt-тексты осмысленны (не пустые для контентных изображений).

## 7. Implementation Roadmap

### Phase 1: Доверие и разрыв петли (Week 1)
**Goal:** убрать вред и долг.
- [x] REQ-014 CI-петля — Medium (4–6h) _(остаётся 7-дневный чекпойнт)_
- [x] REQ-015 Приватный репо → Case study — Small (1–2h)
- [x] REQ-016 Убрать накрутку — XS (0.5h)
- [x] REQ-017 Верифицируемость метрик — Small (3–4h)
- [x] REQ-018 Slim metrics + стрики без дублей — Medium (5–6h)
- [x] REQ-019 Удалить keepalive — Small (1–2h) _(plist вне репо — у владельца)_
**Validation Checkpoint:** 7 дней 0 loop-коммитов; metrics ≤80 KB; 0 мёртвых featured-ссылок; 0 накрутки.

### Phase 2: Гигиена и CI (Week 2)
- [x] REQ-020 Тесты в CI + pyproject — Medium (4–6h)
- [x] REQ-021 Гигиена/дрейф — Medium (4–6h)
- [x] REQ-022 Игры: label + a11y + пиннинг — Medium (4–6h) _(визуальный вес/мобайл — manual)_
- [x] REQ-023 UTM-консистентность — Small (2–3h)
- [x] REQ-024 Ссылка «Currently building» — XS (0.5h)
- [x] REQ-025 Позиционирование — Small (2–3h)
**Validation Checkpoint:** pytest зелёный на push; 0 известных дрейфов; a11y игр закрыт.

### Phase 3: Отложенное / внешнее
- [ ] REQ-026 Experience — ждёт ввода
- [ ] REQ-027 PostHog + Worker — deferred
- [ ] REQ-028 Сайт-кейсы — внешняя зависимость

### Оценка усилий
- Phase 1: ~15–20h
- Phase 2: ~16–24h
- **Итого:** ~31–44h (~2 недели, solo)
- **Риск-буфер:** +20%

## 8. Out of Scope

1. Полный редизайн README.
2. PostHog/редирект-инфраструктура в этой итерации (REQ-027 deferred).
3. Правки сайта `Personal_Projects.github.io` (REQ-028 — внешняя зависимость).
4. Новые игры и расширение игровой секции.
5. Платная аналитика; CRM-автоматизация контактов.
6. Генерация выдуманных отзывов (Q14/Q18).

## 9. Risks & Mitigation

| Риск | Вероятность | Влияние | Severity | Митигация | Контингенция |
|------|-------------|---------|----------|-----------|--------------|
| `[skip ci]` подавит нужный workflow | Low | Medium | Medium | узкие `paths` + отдельный триггер для генератора | вернуть paths-триггер |
| Self-host metrics ≠ паритет с lowlighter | Medium | Medium | High | сравнить карточки до/после | откат коммита |
| Приватность Supabase-репо нельзя раскрыть | Low | Medium | Medium | вариант B: Case study-ссылка (выбран) | — |
| Смягчение ROI снизит «вау»-эффект | Medium | Low | Medium | сохранить lift/p/конверсии + вернуть ROI после REQ-028 | — |
| a11y-правка ломает рендер SVG на GitHub | Low | Medium | Medium | тест рендера в PR до merge | откат |
| Дрейф вернётся после правок | Medium | Low | Low | синк `PLAN/prd` в Definition of Done | регулярный аудит |

## 10. Open Questions

- **Q14 (личное):** какие реальные данные по опыту/рекомендациям можно добавить? Статус: ожидается ввод. Влияние: Medium (REQ-026).
- **Q16-продолжение:** делать ли репозиторий Supabase публичным вместо Case study-ссылки? Статус: решено B (Case study). Влияние: Low.
- **Q9-объём:** урезать ли игры до 4 лучших дополнительно к REQ-022? Статус: отложено до визуальной оценки. Влияние: Low.

---

## 11. Execution log (2026-09-18)

Все P0/P1-требования реализованы. Ниже — что именно изменено и чем проверено.

| REQ | Артефакт / изменение |
|---|---|
| REQ-014 | `concurrency` (`cancel-in-progress: true`) во всех 4 workflow; автокоммиты с `[skip ci]`; `profile.yml` `paths` без `**.svg`; `write_asset()` вырезает таймстамп перед сравнением — идемпотентная запись. |
| REQ-015 | У приватного `supabase-product-analytics` бейдж `Repo` заменён на `Case study` → `/projects/supabase/`; `Case study` есть у всех трёх featured. |
| REQ-016 | `extra_count=124` удалён из URL `hits.sh`. |
| REQ-017 | `€716K/yr` и `48× ROI` убраны из профиля; каждая метрика подкреплена бейджем `Case study`. |
| REQ-018 | `metrics.yml` (lowlighter) удалён; `metrics.svg` self-hosted (`build_metrics_svg`, heatmap без totals) — **44 921 B**; `streak.svg` слит в `stats.svg` и удалён (числа без дублей). |
| REQ-019 | `keepalive.yml`, `scripts/keepalive.sh` удалены; `enable_keepalive: false` в `update-notes.yml`; `--allow-empty` отсутствует. |
| REQ-020 | `pyproject.toml` (pytest/ruff); `.github/workflows/ci.yml` — `ruff check` + `pytest --cov`; покрытие ~68% в `docs/development.md`. |
| REQ-021 | Footer credits — только живые сервисы; `GH_USER`/`--user` вместо shell `$USER`; один GraphQL-запрос за прогон; `PLAN.md` → навигатор; `docs/prd.md` → исторический архив; `preview.sh` и политика пиннинга в `docs/development.md`; ветка `output` удалена. |
| REQ-022 | Явный label «opens in a new tab»; `<title>`/`<desc>`/`role="img"` в 8/8 игровых SVG; все игровые ссылки → `@main`. |
| REQ-023 | Единая UTM-схема на header/cv/featured/building/notes/connect; схема задокументирована. |
| REQ-024 | «Building» ведёт на портфолио (HTTP 200). |
| REQ-025 | H2 «Data / Product Analyst (Middle+)»; featured выше игр. |
| REQ-026 | Placeholder TODO P1.3 удалён; секция не добавлена (ждёт реальных данных). |
| REQ-029 | `contribution-types.svg` + `monthly-activity.svg` — новые self-hosted графики (`build_contribution_types_svg` / `build_monthly_activity_svg`); поля типов добавлены в единственный GraphQL-запрос; подключены в README/`profile.yml`/тестах. |

**Верификация:** `pytest` — 23 passed; `ruff check scripts tests` — All checks passed;
`python3 scripts/build_profile.py --dry-run` — генератор отрабатывает, ассеты собираются
(в dry-run README-блок пропускается); featured case-study URL volta/supabase/sql — HTTP 200;
`metrics.svg` — 44 KB (цель ≤80 KB); карточки отрендерены в PNG и проверены визуально
(непрозрачный фон → light/dark не влияет).

**Lighthouse (2026-09-18, github.com/NikitaBoyarkin):** desktop perf 0.70, `LCP 4.2s`,
`FCP 1.4s`, `TBT 0ms`, `CLS 0.001`; mobile-sim perf 0.45, `LCP 10.2s`. Все opportunities —
ресурсы github.com; наш вклад мал. **Вывод: NFR «LCP < 2s» не достижим силами репо**
(см. §6 Performance — бюджет переформулирован на вес карточек).

**Документы:** `docs/development.md` (пайплайн, покрытие, пиннинг, UTM, CI-защита),
`docs/posthog-setup.md` (гайд для deferred REQ-027), `PLAN.md` (навигатор),
`docs/prd.md` (архив v1).

**Не закрыто (вне кода):** 7-дневные чекпойнты REQ-014/019; launchd plist вне репо;
REQ-026 (ввод), REQ-027 (deferred), REQ-028 (внешний репозиторий сайта);
Q9 (игры → 4 — ждёт решения владельца, impact Low).

---

**Конец PRD v2**
