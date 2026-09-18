# PRD v1: GitHub Profile README — лендинг аналитика на рынке труда (historical)

**Автор:** Nikita Boyarkin · **Дата:** 2026-09-07 · **Версия:** 1.1 · **Статус:** superseded

> **Это архив.** Полный текст v1 (489 строк) доступен в истории git
> (`git show <sha>:docs/prd.md`). Актуальная версия — [`docs/prd-v2.md`](prd-v2.md);
> операционные детали — [`docs/development.md`](development.md).
> Здесь сохранено только то, что не продублировано в v2.

## Роль v1

v1 формализовал профиль как продукт и ставил во главу угла **измерение воронки**:
UTM-атрибуция по секциям → PostHog → дашборд CTR → рост контактов и CV-загрузок.
13 требований (REQ-001…REQ-013), 4 цели, воронка «view → scroll → click portfolio →
case study → contact».

## Что реально закрыто

REQ-001 (игры), REQ-003 (self-host top-langs), REQ-006 (featured выше игр),
REQ-009/010/012/013 (тесты, ретраи, preview, snake в main) — **done**.

## Что изменил v2

1. **Статусы v1 были завышены.** REQ-009 (тесты) и REQ-011 (keepalive) значились
   `[DONE]`, но pytest не запускался в CI, а empty-commits жили в трёх местах.
2. **Приоритет смещён:** сначала credibility и техдолг, потом измерение воронки.
3. **Воронка (PostHog + редирект-сервис) переведена в deferred** — REQ-027 в v2.
   Как её включать, если понадобится: [`docs/posthog-setup.md`](posthog-setup.md).

Остаток v1 (уточнённые требования REQ-014…REQ-028) ведётся в [`docs/prd-v2.md`](prd-v2.md).
