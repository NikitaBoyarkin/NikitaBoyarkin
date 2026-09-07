# PostHog Setup — NikitaBoyarkin Profile

> Гайд по созданию PostHog-проекта для трекинга GitHub profile README.
> Связан с PRD: REQ-005 (UTM-атрибуция + PostHog дашборд), Q1 (ручной учёт контактов), Q3 (проект в NBxHive).

## 1. Создание проекта (UI, ~1 мин)

1. Открыть [app.posthog.com](https://app.posthog.com) — залогинен в организации **NBxHive**.
2. Слева внизу: **Settings** (шестерёнка) → **Projects**.
3. **New project** → название: `NikitaBoyarkin Profile`.
4. **Timezone:** `Europe/Moscow`.
5. **Create project**.

После создания — взять API key:
- **Settings → Project settings → API keys** → `project_api_key` (формат `phc_...`).
- Этот ключ нужен для отправки событий (capture).

## 2. Структура событий

| Событие | Триггер | Properties |
|---|---|---|
| `profile_link_click` | Клик по ссылке README (через редирект-сервис) | `{section, href, utm_campaign}` |
| `cv_download` | Загрузка CV | `{utm_campaign: "cv"}` |
| `recruiter_contact` | Ручной учёт входящего контакта | `{source, date, company, role}` |

## 3. Отправка событий

### 3.1 Ручной учёт контактов (Q1)

Раз в неделю логировать входящие контакты от рекрутеров/найм-менеджеров:

```python
from posthog import Posthog

posthog = Posthog(project_api_key="phc_...", host="https://us.i.posthog.com")

posthog.capture(
    distinct_id="nikita",
    event="recruiter_contact",
    properties={
        "source": "linkedin",      # linkedin | email | telegram | other
        "date": "2026-09-07",
        "company": "Acme Corp",
        "role": "Product Analyst",
    },
)
```

### 3.2 Автоматический трекинг кликов (редирект-сервис)

GitHub README не выполняет JS → клики трекаются через редирект-сервис.
Шаблон Cloudflare Worker (бесплатный, 100k req/день):

```js
// worker.js — Cloudflare Worker: логирует клик в PostHog и редиректит
export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const target = url.searchParams.get("to");       // целевой URL
    const section = url.searchParams.get("section"); // секция README

    if (target) {
      // Отправить событие в PostHog (capture API)
      await fetch("https://us.i.posthog.com/capture/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          api_key: env.POSTHOG_KEY,
          event: "profile_link_click",
          distinct_id: "github-profile",
          properties: { section, href: target },
        }),
      });
      return Response.redirect(target, 302);
    }
    return new Response("Missing ?to= param", { status: 400 });
  },
};
```

Ссылки в README заменяются на `https://<worker>.workers.dev/?to=<url>&section=<section>`.

### 3.3 Аналитика приёмника (уже работает)

Portfolio-сайт (Astro) уже имеет PostHog и видит `utm_source=github` на входящих кликах.
Это даёт CTR portfolio-ссылок без редирект-сервиса — первый дашборд можно построить сразу.

## 4. Дашборд (после создания проекта)

| Панель | Запрос |
|---|---|
| Контакты/мес (North Star) | `recruiter_contact` по месяцам, breakdown по source |
| CV-загрузки/мес | `cv_download` по месяцам |
| CTR по секциям | `profile_link_click` breakdown по section |
| Источники трафика portfolio | UTM-клики на portfolio-сайте (существующий PostHog) |

## 5. Чек-лист

- [ ] Проект `NikitaBoyarkin Profile` создан в NBxHive
- [ ] `project_api_key` получен (phc_...)
- [ ] Ручной учёт контактов запущен (еженедельно)
- [ ] Редирект-сервис развёрнут (Cloudflare Worker) — опционально, для CTR по секциям
- [ ] Дашборд построен (4 панели)
