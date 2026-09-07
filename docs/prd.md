# PRD: GitHub Profile README — лендинг аналитика на рынке труда

**Автор:** Nikita Boyarkin
**Дата:** 2026-09-07
**Статус:** In Review
**Версия:** 1.1

> **Статус реализации (2026-09-07):** 8 из 13 REQ уже реализованы (REQ-001, 003, 006, 009, 010, 011, 012, 013). Осталось: REQ-002 (трекинг), REQ-004, REQ-005, REQ-007, REQ-008 (TODO). См. пометки `[DONE]`/`[PARTIAL]` в секции 5.

---

## 1. Executive Summary

GitHub profile README (`NikitaBoyarkin/NikitaBoyarkin`) — это лендинг аналитика на рынке труда: первая точка контакта рекрутера, найм-менеджера или коллеги с кандидатом. Сейчас профиль силён по контенту (позиционирование, featured projects с метриками, 8 SVG-игр, self-hosted stats), но воронка «просмотр → контакт» не измеряется: нет UTM-агрегации, нет трекинга контактов и CV-загрузок, metrics.svg весит 367KB и тормозит загрузку. Решение — формализовать профиль как продукт: измерить воронку (PostHog), поднять конверсию (CV-CTA выше фолда, реордер секций, social proof), устранить технический долг (self-host top-langs, slim metrics, тесты build-скрипта). Ожидаемый эффект — измеримый рост контактов от рекрутеров и CV-загрузок при LCP < 2s.

## 2. Problem Statement

### Текущая ситуация
Профиль существует и наполнен, но работает «вслепую»:
- **Аналитика не измеряется.** Единственный трекер — hits.sh (счётчик просмотров). Воронка «profile view → scroll → click portfolio → case study → contact» не агрегируется, UTM-метки на ссылках не замыкаются на серверную аналитику.
- **Конверсия не оптимизирована.** CTA «Download CV» отсутствует выше фолда; featured projects расположены ниже игр; нет social proof.
- **Производительность деградирует.** `metrics.svg` весит 367KB (lowlighter/metrics), что замедляет LCP. 3 из 4 динамических карточек зависят от внешних сервисов (Vercel, lowlighter, snk).
- **Технический долг.** `build_profile.py` без тестов, ретраев и `--dry-run`; 5 daily workflows + keepalive 4×/день (риск TOS-бана GitHub).

### Влияние на пользователя
- **Кто затронут:** рекрутеры, найм-менеджеры, коллеги-аналитики, HR-боты.
- **Как затронут:** медленная загрузка (367KB SVG) → часть посетителей уходит до контента; отсутствие явного CTA → контакт требует лишнего клика; нет измеримого результата → кандидат не знает, что работает.
- **Серьёзность:** Medium. Профиль не сломан, но конверсия и измеримость — главные неиспользованные рычаги.

### Бизнес-влияние
- **Стоимость проблемы:** потерянные контакты от рекрутеров (не измеряется, но профиль — основной канал на рынке труда).
- **Стратегическая важность:** профиль — часть активного поиска работы (BI/product/data analyst, интервью в Авито/Яндекс/Т-банк). Измеримая воронка усиливает и портфель (PostHog-проект), и переговорную позицию.

### Почему решать сейчас
Кандидат активно интервьюируется (2026-08-08 старт цикла). Профиль — живой артефакт, который показывают рекрутерам. Каждая неделя без измерений — неделя без данных о том, что конвертит. Плюс PLAN.md уже содержит готовый аудит и бэклог — PRD формализует его в исполняемые требования.

## 3. Goals & Success Metrics

### Goal 1: Измерить воронку профиля
- **Описание:** UTM-атрибуция по секциям + агрегация в PostHog; ручной учёт контактов.
- **Метрика:** число контактов от рекрутеров/найм-менеджеров в месяц.
- **Baseline:** не измеряется (0 данных).
- **Target:** тренд ↑, измеримо ≥ 1 контакт/мес через PostHog + ручной учёт.
- **Срок:** 2 недели (после Phase 2).
- **Метод измерения:** PostHog events (UTM-клики), ручной учёт входящих контактов.

### Goal 2: Рост CV-загрузок
- **Описание:** CTA «Download CV» выше фолда + трекинг загрузок.
- **Метрика:** число загрузок CV/мес.
- **Baseline:** не измеряется.
- **Target:** ≥ 10 загрузок/мес.
- **Срок:** 2 недели.
- **Метод измерения:** PostHog event `cv_download` + UTM-метка на CV-ссылке.

### Goal 3: Производительность
- **Описание:** убрать тяжёлые внешние карточки, self-host ключевые SVG.
- **Метрика:** LCP профиля.
- **Baseline:** не измеряется (metrics.svg 367KB).
- **Target:** < 2s LCP; metrics.svg ≤ 80KB.
- **Срок:** 1 неделя (Phase 1).
- **Метод измерения:** Lighthouse / WebPageTest на `github.com/NikitaBoyarkin`.

### Goal 4: Конверсия к кейсам
- **Описание:** featured projects выше игр + social proof.
- **Метрика:** CTR portfolio-ссылки (UTM-клики).
- **Baseline:** UTM без агрегации.
- **Target:** дашборд с CTR по секциям; рост CTR кейсов после реордера.
- **Срок:** 2 недели.
- **Метод измерения:** PostHog UTM-агрегация.

## 4. User Stories

### Story 1: Рекрутер оценивает кандидата
**As a** рекрутер, **I want to** за 30 секунд понять позиционирование и увидеть явный CTA, **So that I can** быстро решить, стоит ли контактировать.

**Acceptance Criteria:**
- [ ] Позиционирование («turn ambiguous product questions into clean experiments…») видно без скролла.
- [ ] CTA «Download CV» и ссылки на portfolio/LinkedIn доступны выше фолда.
- [ ] Профиль загружается < 2s LCP на мобильном и десктопе.

**Dependencies:** REQ-002, REQ-004

### Story 2: Найм-менеджер проверяет кейсы
**As a** найм-менеджер, **I want to** видеть featured projects с измеримыми результатами, **So that I can** оценить глубину аналитических навыков.

**Acceptance Criteria:**
- [ ] Featured projects (volta-banking, supabase-product-analytics, sql-analytics-case-study) расположены выше игр.
- [ ] Каждый кейс содержит метрику результата (+6.24pp, p=0.0034, 10 SQL-кейсов).
- [ ] Ссылка на case study открывается в 1 клик.

**Dependencies:** REQ-006

### Story 3: Коллега-аналитик запоминает профиль
**As a** коллега/аналитик, **I want to** поиграть в on-brand игры, **So that I can** запомнить профиль и вернуться.

**Acceptance Criteria:**
- [ ] Игровая секция содержит ≥ 6 игр, каждая с управлением и целью.
- [ ] Игры не каннибализируют CTR portfolio-ссылки (counter-метрика).
- [ ] Игры работают в fullscreen через jsDelivr.

**Dependencies:** REQ-001

## 5. Functional Requirements

### Must Have (P0) — критично для запуска

#### REQ-001: Игровая секция — 6+ on-brand игр `[DONE]`
**Описание:** Поддерживать и расширять секцию SVG-игр, каждая игра — on-brand (аналитика/метрики), с управлением и целью. Текущее состояние: 8 игр (Snake, A/B Test, Pong, 2048, Funnel Drop, Cohort Catch, SQL Query, Metric Match).

**Acceptance Criteria:**
- [ ] Секция содержит ≥ 6 игр, каждая с описанием управления и цели.
- [ ] Каждая игра доступна в fullscreen по прямой ссылке (jsDelivr).
- [ ] Новая игра добавляется в таблицу с on-brand темой (метрика/аналитика/воронка).
- [ ] Игры не ломают рендер README на мобильном (таблица адаптивна).

**Техническая спецификация:**
```
SVG-игра: интерактивный <svg> с <script>, self-contained, без внешних зависимостей.
Хостинг: jsDelivr (cdn.jsdelivr.net/gh/NikitaBoyarkin/NikitaBoyarkin@<ref>/<game>.svg).
```

**Task Breakdown:**
- [Игровая секция]: Medium (4-8h)
- [Новая игра]: Medium (4-8h)
- [Тесты рендера]: Small (2-4h)

**Dependencies:** None

#### REQ-002: CTA «Download CV» выше фолда `[PARTIAL]`
**Описание:** Добавить явный CTA загрузки CV в верхнюю часть профиля (рядом с portfolio/links), с UTM-меткой и трекингом. Ссылка с UTM уже есть в header; не хватает выделения как CTA и трекинга (зависит от REQ-005).

**Acceptance Criteria:**
- [ ] CTA «Download CV» виден без скролла на десктопе и мобильном.
- [ ] Ссылка на CV содержит UTM-метку (`utm_campaign=cv`).
- [ ] Клик по CTA генерирует PostHog event `cv_download` (после REQ-005).
- [ ] CV-файл доступен по стабильному URL (GitHub Pages).

**Техническая спецификация:**
```
<a href="https://nikitaboyarkin.github.io/Personal_Projects.github.io/CV-Nikita-Boyarkin.pdf?utm_source=github&utm_medium=profile_readme&utm_campaign=cv">
  <img src="cv.svg" alt="Download CV" />
</a>
```

**Task Breakdown:**
- [README-правка]: Small (2-4h)
- [Трекинг]: Small (2-4h)

**Dependencies:** REQ-005 (трекинг)

#### REQ-003: Self-host top-languages SVG `[DONE]`
**Описание:** Заменить внешнюю карточку top-languages (Vercel) на self-hosted SVG, генерируемый `build_profile.py` через GitHub GraphQL. Реализовано: `build_top_languages_svg()` + `profile.yml` коммитит `top-languages.svg`.

**Acceptance Criteria:**
- [ ] `top-languages.svg` генерируется локально `build_profile.py` и коммитится в репозиторий.
- [ ] README ссылается на `raw.githubusercontent.com/NikitaBoyarkin/NikitaBoyarkin/main/top-languages.svg`.
- [ ] Внешняя Vercel-зависимость для top-langs удалена.
- [ ] Карточка рендерится без JS и без внешних запросов.

**Техническая спецификация:**
```
build_profile.py → GraphQL (user.repositories.primaryLanguage) → top-languages.svg
```

**Task Breakdown:**
- [build_profile.py]: Medium (4-8h)
- [README-правка]: Small (2-4h)
- [Тесты]: Small (2-4h)

**Dependencies:** REQ-009 (тесты)

#### REQ-004: Slim metrics.svg `[TODO]`
**Описание:** Уменьшить вес `metrics.svg` с 367KB до ≤ 80KB, убрав необязательные блоки (notable, metadata) и оптимизировав SVG. Правка: убрать тяжёлые плагины из `metrics.yml` (`plugin_commit`, `plugin_followup`, `plugin_isocalendar`).

**Acceptance Criteria:**
- [ ] `metrics.svg` весит ≤ 80KB.
- [ ] Ключевые метрики (contributions, streak, activity) сохранены.
- [ ] LCP профиля < 2s после оптимизации.
- [ ] Карточка рендерится корректно в light и dark theme.

**Task Breakdown:**
- [Оптимизация metrics]: Medium (4-8h)
- [Проверка LCP]: Small (2-4h)

**Dependencies:** None

### Should Have (P1) — важно, но не блокирует

#### REQ-005: UTM-атрибуция + PostHog дашборд `[TODO]`
**Описание:** Добавить UTM-метки по секциям (header, featured, games, connect) и агрегировать клики в PostHog. Портфельный проект: профиль как источник данных. UTM-метки уже есть на portfolio/links/CV; не хватает PostHog-агрегации (требует решения Q3).

**Acceptance Criteria:**
- [ ] Каждая секция README имеет уникальную UTM-метку (`utm_campaign=<section>`).
- [ ] PostHog-проект принимает события кликов по ссылкам профиля.
- [ ] Дашборд показывает CTR по секциям и конверсию в CV-загрузки.
- [ ] Данные доступны без ручной выгрузки (live-дашборд).

**Техническая спецификация:**
```
UTM: utm_source=github&utm_medium=profile_readme&utm_campaign=<section>
PostHog: posthog.capture('profile_link_click', {section, href})
```

**Task Breakdown:**
- [UTM-разметка]: Small (2-4h)
- [PostHog-проект]: Medium (4-8h)
- [Дашборд]: Medium (4-8h)

**Dependencies:** None

#### REQ-006: Featured projects выше игр `[DONE]`
**Описание:** Переместить секцию featured projects выше игровой секции, чтобы кейсы с метриками были видны раньше. Реализовано: порядок секций header → stats → featured → games.

**Acceptance Criteria:**
- [ ] Порядок секций: header → featured projects → games → recent notes.
- [ ] Все ссылки и UTM-метки сохранены при реордере.
- [ ] CTR кейсов (UTM-клики) растёт или не падает после реордера (эксперимент EXP-02).

**Task Breakdown:**
- [README-правка]: Small (2-4h)
- [Эксперимент]: Small (2-4h)

**Dependencies:** REQ-005

#### REQ-007: Social proof — цитаты `[TODO]`
**Описание:** Добавить 1-2 цитаты от коллег/рекрутеров в секцию featured projects. Блокируется получением реальных цитат (Q2).

**Acceptance Criteria:**
- [ ] ≥ 1 цитата с именем и ролью автора.
- [ ] Цитата связана с конкретным проектом/навыком.
- [ ] Нет выдуманных отзывов — только реальные (с разрешения автора).

**Task Breakdown:**
- [Сбор цитат]: Small (2-4h)
- [README-правка]: Small (2-4h)

**Dependencies:** None

#### REQ-008: «Currently building» — пинн активного проекта `[PARTIAL]`
**Описание:** Заменить TODO-строку «Currently building» на актуальный активный проект с ссылкой. Строка уже заполнена («interactive analyst portfolio»); осталось убрать TODO-комментарий P1.4.

**Acceptance Criteria:**
- [ ] Строка «Currently building» указывает на реальный активный проект.
- [ ] Проект имеет ссылку на репозиторий.
- [ ] TODO-комментарий P1.4 удалён после подтверждения.

**Task Breakdown:**
- [README-правка]: Small (2-4h)

**Dependencies:** None

### Nice to Have (P2) — будущее улучшение

#### REQ-009: Тесты для build_profile.py `[DONE]`
**Описание:** Добавить pytest-тесты для `compute_streaks`, `build_*_svg` и других функций build-скрипта. Реализовано: `tests/test_build_profile.py`.

**Acceptance Criteria:**
- [ ] Покрытие ≥ 80% для `build_profile.py`.
- [ ] Тесты запускаются `uv run pytest` без внешних сетевых вызовов (моки GraphQL).
- [ ] CI-шаг прогоняет тесты при каждом push.

**Task Breakdown:**
- [Тесты]: Medium (4-8h)
- [CI]: Small (2-4h)

**Dependencies:** None

#### REQ-010: Ретраи + --dry-run в build_profile.py `[DONE]`
**Описание:** Добавить ретраи на сетевые вызовы GraphQL и флаг `--dry-run` для безопасного запуска. Реализовано: `graphql(retries=3, backoff)`, `--dry-run` в `main()`.

**Acceptance Criteria:**
- [ ] Сетевые вызовы имеют ретраи (≥ 2 попытки с backoff).
- [ ] `--dry-run` показывает diff без записи файлов.
- [ ] Скрипт завершается с ненулевым кодом при недоступности API.

**Task Breakdown:**
- [build_profile.py]: Medium (4-8h)
- [Тесты]: Small (2-4h)

**Dependencies:** REQ-009

#### REQ-011: Консолидация workflows `[DONE]`
**Описание:** Сократить 5 daily workflows и keepalive 4×/день до минимального набора; заменить empty-commits на meaningful. Реализовано: keepalive 1×/день, `update_readme_refresh_block()` даёт meaningful-коммит (TOS-риск митигирован).

**Acceptance Criteria:**
- [ ] Keepalive 4×/день → 1×/день.
- [ ] Empty-commits заменены на meaningful (build_profile.py пишет «Last refreshed: <date>, <N> contributions»).
- [ ] Все workflows проходят без ошибок 7 дней подряд.

**Task Breakdown:**
- [Workflows]: Medium (4-8h)

**Dependencies:** None

#### REQ-012: Локальный превью README `[DONE]`
**Описание:** Добавить `scripts/preview.sh` для локального рендера README. Реализовано: `scripts/preview.sh`.

**Acceptance Criteria:**
- [ ] `scripts/preview.sh` открывает локальный превью README.
- [ ] Скрипт документирован в README проекта.
- [ ] Превью не требует внешних сервисов.

**Task Breakdown:**
- [preview.sh]: Small (2-4h)

**Dependencies:** None

#### REQ-013: Snake в main вместо ветки output `[DONE]`
**Описание:** Перенести snake.svg в ветку main, убрав зависимость от отдельной ветки. Реализовано: `snake.yml` коммитит в main.

**Acceptance Criteria:**
- [ ] `snake.svg` доступен в main.
- [ ] README ссылается на main-версию snake.
- [ ] Ветка output больше не нужна для рендера.

**Task Breakdown:**
- [Git-операции]: Small (2-4h)

**Dependencies:** None

## 6. Non-Functional Requirements

### Performance
- LCP профиля: < 2s (десктоп и мобильный).
- metrics.svg: ≤ 80KB (сейчас 367KB).
- Динамические карточки: self-hosted, без внешних запросов при рендере.

### Security
- Никаких секретов в README/SVG (токены GraphQL — в GitHub Secrets).
- Внешние ссылки: только https.
- UTM-ссылки не содержат PII.

### Scalability
- Профиль — статический контент, масштабируется автоматически.
- PostHog-события: < 1k/мес (низкий объём).

### Reliability
- Self-hosted карточки: uptime = uptime GitHub Pages (≈ 100%).
- Внешние сервисы (Vercel, lowlighter): fallback на self-hosted (REQ-003, REQ-004).
- Build-скрипт: ретраи + `--dry-run` (REQ-010).

## 7. Technical Considerations

### Архитектура
```
GitHub Actions (daily) → build_profile.py (GraphQL) → *.svg → commit → README
        ↓
PostHog (UTM-клики, cv_download) → дашборд
```

### Технологический стек
- **Frontend:** Markdown README + self-contained SVG (интерактивные игры).
- **Backend:** Python `build_profile.py` (GraphQL), GitHub Actions.
- **Database:** PostHog (события), GitHub (артефакты).
- **Infrastructure:** GitHub Pages (CV, portfolio), jsDelivr (игры), raw.githubusercontent (SVG).

### Внешние зависимости
1. **GitHub GraphQL API:** данные stats/streak/top-langs. Rate limit ~5000 req/h. Fallback: кэш последнего успешного билда.
2. **jsDelivr:** хостинг SVG-игр. Fallback: raw.githubusercontent.
3. **PostHog:** аналитика кликов. Fallback: hits.sh (счётчик просмотров).
4. **lowlighter/metrics:** metrics.svg. Fallback: self-host (REQ-004).

### Миграция (для существующих систем)
1. Self-host top-langs (REQ-003) — feature flag: README ссылается на новый SVG, старый удаляется после проверки.
2. Slim metrics (REQ-004) — бета: новый metrics.svg коммитится, LCP проверяется, откат = revert коммита.
3. Реордер секций (REQ-006) — эксперимент EXP-02: before/after по UTM-кликам.

### Тестирование
- Unit: build_profile.py (compute_streaks, build_*_svg) — ≥ 80% (REQ-009).
- Integration: GitHub Actions workflow проходит end-to-end.
- E2E: README рендерится на github.com, игры кликабельны.
- Performance: Lighthouse LCP < 2s.
- Security: нет секретов в коммитах.

## 8. Implementation Roadmap

### Phase 1: Быстрые победы (Week 1) — 3/5 done
**Goal:** Производительность + явный CTA + консолидация.
**Tasks:**
- [x] Task 1.3: Self-host top-languages (REQ-003) — done
- [x] Task 1.4: Консолидация workflows, keepalive 1×/день (REQ-011) — done
- [x] Task 1.5: Snake в main (REQ-013) — done
- [ ] Task 1.1: CTA «Download CV» выше фолда (REQ-002) — Small (3h)
- [ ] Task 1.2: Slim metrics.svg 367KB → 80KB (REQ-004) — Medium (5h)
**Validation Checkpoint:** LCP < 2s; metrics.svg ≤ 80KB; keepalive 1×/день; CTA виден выше фолда.

### Phase 2: Измерение и конверсия (Week 2) — 4/7 done
**Goal:** Измерить воронку, поднять конверсию к кейсам.
**Tasks:**
- [x] Task 2.2: Featured projects выше игр (REQ-006) — done
- [x] Task 2.5: Тесты build_profile.py (REQ-009) — done
- [x] Task 2.6: Ретраи + --dry-run (REQ-010) — done
- [x] Task 2.7: Локальный превью (REQ-012) — done
- [ ] Task 2.1: UTM-атрибуция + PostHog дашборд (REQ-005) — Medium (8h)
- [ ] Task 2.3: Social proof — цитаты (REQ-007) — Small (3h)
- [ ] Task 2.4: «Currently building» — пинн проекта (REQ-008) — Small (2h)
**Validation Checkpoint:** PostHog дашборд показывает CTR по секциям; CV-загрузки трекаются; тесты ≥ 80% покрытия.

### Зависимости задач
```
Phase 1 → Phase 2
Critical Path: REQ-005 (UTM) → REQ-002 (CV-CTA трекинг) → REQ-006 (реордер)
```

### Оценка усилий
- Phase 1: ~21h
- Phase 2: ~30h
- **Итого:** ~51h (~2 недели, solo)
- **Риск-буфер:** +20% → ~61h

## 9. Out of Scope

1. **Полный редизайн README** — текущая структура работает, меняем точечно. Будущее: A/B-тест макетов.
2. **Блог-платформа в профиле** — блог уже живёт на отдельном Astro-сайте (Personal_Projects.github.io), профиль только линкует RSS.
3. **Платная аналитика** — PostHog free tier достаточно (< 1k событий/мес).
4. **Мобильное приложение / PWA** — профиль статический, не требуется.
5. **Автоматизация контактов (CRM)** — ручной учёт входящих контактов достаточен на этом этапе.

## 10. Open Questions & Risks

### Open Questions
#### Q1: Как трекать контакты от рекрутеров?
- **Статус:** рекомендация — вариант (C) оба
- **Варианты:** (A) ручной учёт в PostHog (событие `recruiter_contact`), (B) UTM на LinkedIn/email, (C) оба.
- **Рекомендация:** (C) — UTM-метки на LinkedIn/email дают автоматический трекинг источника, ручной учёт в PostHog закрывает контакты без клика (прямые сообщения). Оба канала в одном дашборде.
- **Владелец:** Nikita
- **Дедлайн:** конец Phase 2
- **Влияние:** High (North Star метрика)

#### Q2: Social proof — откуда цитаты?
- **Статус:** открыт
- **Варианты:** (A) коллеги по прошлым проектам, (B) рекрутеры из интервью, (C) отложить до получения.
- **Владелец:** Nikita
- **Дедлайн:** конец Phase 2
- **Влияние:** Medium

#### Q3: PostHog-проект — отдельный или в существующий?
- **Статус:** рекомендация — вариант (A)
- **Варианты:** (A) новый проект в существующей организации NBxHive, (B) отдельная организация.
- **Рекомендация:** (A) — новый проект в NBxHive: организация уже настроена, free tier достаточно (< 1k событий/мес), дашборды в одном месте с остальными портфельными проектами.
- **Владелец:** Nikita
- **Дедлайн:** начало Phase 2
- **Влияние:** Low

### Risks & Mitigation

| Риск | Вероятность | Влияние | Severity | Митигация | Контингенция |
|------|-------------|---------|----------|-----------|--------------|
| Keepalive empty commits vs GitHub TOS | Medium | High | **Critical** | meaningful commits (build_profile.py пишет «Last refreshed») | отключить keepalive, полагаться на daily build |
| 3rd-party Vercel даун (top-langs) | Medium | Medium | High | self-host (REQ-003) | fallback на кэш последнего билда |
| metrics.svg тормозит LCP | Medium | Medium | High | slim до 80KB (REQ-004) | убрать metrics.svg, оставить stats/streak |
| Yandex-email для зарубежных ролей | Low | Low | Medium | LinkedIn первичный контакт | добавить email-алиас |
| Игры каннибализируют CTR кейсов | Low | Medium | Medium | counter-метрика (время на играх vs CTR) | реордер секций (REQ-006) |

## 11. Validation Checkpoints

### Checkpoint 1: Конец Phase 1
**Критерии:**
- [ ] LCP профиля < 2s (Lighthouse).
- [ ] metrics.svg ≤ 80KB.
- [ ] CTA «Download CV» виден выше фолда.
- [ ] Keepalive 1×/день, workflows зелёные 7 дней.
**Если провален:** вернуть metrics.svg, откатить CTA, продлить Phase 1 на 2-3 дня.

### Checkpoint 2: Конец Phase 2
**Критерии:**
- [ ] PostHog дашборд показывает CTR по секциям и cv_download.
- [ ] Тесты build_profile.py ≥ 80% покрытия.
- [ ] Featured projects выше игр, social proof добавлен.
- [ ] North Star метрика (контакты + CV-загрузки) трекается.
**Если провален:** сузить scope до UTM + CV-трекинг, остальное перенести в следующую итерацию.

---

**Конец PRD**
