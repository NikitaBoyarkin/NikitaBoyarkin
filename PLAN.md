# Plan — NikitaBoyarkin/NikitaBoyarkin profile improvement

> **Статус (2026-09-18):** синхронизирован с фактом. P0 и P2 закрыты; измерение
> воронки (P1.1, PostHog) переведено в deferred. Актуальный трекер — `docs/prd-v2.md`,
> детали пайплайна — `docs/development.md`.

## 0. Что это за продукт
GitHub profile README = лендинг аналитика на рынке труда. Пользователи — рекрутеры, найм-менеджеры, коллеги. Цель — конверсия «просмотр профиля → контакт».

## 1. Аудит текущего состояния
| Слой | Что есть | Оценка |
|---|---|---|
| Позиционирование | «Data / Product Analyst (Middle+)…» | 🟢 |
| Self-hosted SVG | stats/streak/activity/metrics/top-langs через build_profile.py | 🟢 |
| Динамические карточки | snake (snk), RSS-заметки; hits.sh | 🟢 |
| Игры | 8 SVG-игр, role/title/desc, ссылки `@main` | 🟢 |
| Featured projects | +6.24pp, p<0.0001, p=0.0034; ROI-цифры убраны | 🟢 |
| Recent notes | RSS → blog-post-workflow (+UTM) | 🟢 |
| UTM-аттрибуция | согласованная схема; серверного замыкания нет (deferred) | 🟡 |
| Аналитика профиля | только hits.sh | 🔴 воронка не измерена (deferred) |
| Билд-скрипт | build_profile.py: тесты, ретраи, dry-run, идемпотентность | 🟢 |
| Workflows | 3 daily (profile/snake/notes), keepalive удалён | 🟢 |

## 2. Воронка и метрики
Profile view → scroll → click portfolio → case study view → contact

| Тип | Метрика | Сейчас | Цель |
|---|---|---|---|
| North Star | Контакты от рекрутеров / мес | не измерается | тренд ↑ |
| Guardrail | Время загрузки (metrics.svg 367KB) | не измерается | <2s LCP |
| Secondary | CTR portfolio-ссылки | UTM без агрегации | дашборд |
| Counter | Время на играх vs конверсия | — | не каннибализует CTR |

## 3. Бэклог

### P0 — Быстрые победы
- [x] P0.1 8-я on-brand игра (Cohort Catch / SQL Query / Metric Match) в таблице
- [x] P0.2 CTA «Download CV» выше фолда
- [x] P0.3 Self-host top-languages SVG в build_profile.py
- [x] P0.4 Slim metrics.svg — 357KB → ~44KB

### P1 — Измерение и конверсия
- [ ] P1.1 UTM по секциям + агрегация в PostHog (deferred) — схема готова, `docs/development.md`
  - [ ] Создать PostHog-проект `NikitaBoyarkin Profile` в NBxHive (UI) + взять `phc_...` ключ → гайд: `docs/posthog-setup.md`
- [x] P1.2 Featured projects ВЫШЕ игр
- [ ] P1.3 Social proof — 1–2 цитаты (ждёт реальных данных)
- [x] P1.4 «Currently building» — пинн активного проекта

### P2 — Технический долг
- [x] P2.1 Тесты для build_profile.py (compute_streaks, build_*_svg, extract, metrics)
- [x] P2.2 Ретраи + --dry-run в build_profile.py
- [x] P2.3 Консолидация workflows; keepalive удалён полностью
- [x] P2.4 Локальный превью README (scripts/preview.sh, задокументирован)
- [x] P2.5 Snake в main вместо ветки output

## 4. Эксперименты (before/after)
| EXP | Гипотеза | Метрика | Длительность |
|---|---|---|---|
| EXP-01 | CTA «Download CV» ↑ контакты | загрузки CV, LinkedIn-клики | 2 нед |
| EXP-02 | Featured projects выше игр ↑ CTR кейсов | UTM-клики | 2 нед |
| EXP-03 | 6-я игра ↑ время без каннибализации | views, portfolio CTR | 2 нед |
| EXP-04 | Self-host top-langs ↑ доступность | uptime карточки | 1 мес |

## 5. Риски
| Риск | Вер | Влияние | Митигация |
|---|---|---|---|
| Keepalive empty commits vs GitHub TOS | M | H | meaningful commit (auto-refresh block) |
| 3rd-party Vercel даун | M | M | P0.3 self-host |
| metrics.svg тормозит | M | M | P0.4 |
| Yandex-email для зарубежных ролей | L | L | LinkedIn первичный |

## 6. Roadmap (2 недели)
| Неделя | Что |
|---|---|
| W1 d1–2 | P0.1 6-я игра, P0.2 CV-CTA, P0.4 slim metrics |
| W1 d3–4 | P0.3 self-host top-langs + тесты |
| W1 d5 | P2.3 консолидация, P2.5 snake в main |
| W2 d1–2 | P1.1 UTM → PostHog дашборд |
| W2 d3–4 | P1.2 реордер, P1.3 social proof, P1.4 currently-building |
| W2 d5 | P2.1 тесты, P2.2 ретраи, P2.4 preview |

## 7. Главный совет
Keepalive — главный риск. Заменить empty-commits на meaningful: build_profile.py пишет «Last refreshed: <date>, <N> contributions this week» — коммит осмысленный, streak сохранён, риск TOS-бана падает.
