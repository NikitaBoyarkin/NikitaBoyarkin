# Plan — NikitaBoyarkin/NikitaBoyarkin profile improvement

## 0. Что это за продукт
GitHub profile README = лендинг аналитика на рынке труда. Пользователи — рекрутеры, найм-менеджеры, коллеги. Цель — конверсия «просмотр профиля → контакт».

## 1. Аудит текущего состояния
| Слой | Что есть | Оценка |
|---|---|---|
| Позиционирование | «turn ambiguous product questions into clean experiments…» | 🟢 |
| Self-hosted SVG | stats/streak/activity через build_profile.py (GraphQL) | 🟢 |
| Динамические карточки | top-langs (Vercel), metrics (lowlighter), snake (snk), hits.sh | 🟡 3/4 внешние |
| Игры | 5 SVG-игр, A/B Test on-brand | 🟢 |
| Featured projects | +6.24pp, p<0.0001, €716K/yr, 48× ROI | 🟢 |
| Recent notes | RSS → blog-post-workflow | 🟢 |
| UTM-аттрибуция | на portfolio/links | 🟡 без серверного замыкания |
| Аналитика профиля | только hits.sh | 🔴 воронка не измерена |
| Билд-скрипт | build_profile.py, без тестов/ретраев/dry-run | 🟡 |
| Workflows | 5 daily, keepalive 4×/день | 🟡 избыточно |

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
- P0.1 6-я on-brand игра (Cohort Catch / SQL Query) в пустую ячейку таблицы
- P0.2 CTA «Download CV» выше фолда
- P0.3 Self-host top-languages SVG в build_profile.py
- P0.4 Slim metrics.svg (убрать notable, metadata) — 367KB → ~80KB

### P1 — Измерение и конверсия
- P1.1 UTM по секциям + агрегация в PostHog (портфельный проект)
- P1.2 Featured projects ВЫШЕ игр
- P1.3 Social proof — 1–2 цитаты
- P1.4 «Currently building» — пинн активного проекта

### P2 — Технический долг
- P2.1 Тесты для build_profile.py (compute_streaks, build_*_svg)
- P2.2 Ретраи + --dry-run в build_profile.py
- P2.3 Консолидация workflows; keepalive 4×/день → 1×
- P2.4 Локальный превью README (scripts/preview.sh)
- P2.5 Snake в main вместо ветки output

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
