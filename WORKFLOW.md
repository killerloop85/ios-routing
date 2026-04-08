# Workflow

Короткая инструкция по ежедневной работе с routing-репозиторием.

## Что где лежит

- `shadowrocket/` — готовые `.conf` и итоговые `.list` для Shadowrocket
- `streisand/` — экспортированные JSON-правила и профили для Streisand
- `streisand/*.streisand-uri.txt` — готовые import-ready `streisand://...` ссылки
- `streisand/routing-profile-split-qr.*` — компактный split-профиль под QR и нестабильный импорт
- `data/` — source of truth для ручного ядра, source pool, приоритетов и override-правил
- `scripts/update_routing_lists.py` — генератор и апдейтер списков
- `scripts/export_streisand_rules.py` — экспорт итоговых `.list` в Streisand JSON
- `scripts/export_streisand_uri.py` — экспорт Streisand-профилей в import-ready URI
- `scripts/check_regression_domains.py` — фиксированный regression-check по доменам
- `docs/routing-update-spec.md` — техническая спецификация логики обновления
- `docs/streisand-routing-spec.md` — ТЗ на второй consumer того же routing-слоя для Streisand
- `docs/streisand-profile-notes.md` — заметки по реальным `streisand://` профилям и что из них перенесено в проект
- `docs/routing-dev-heuristics.md` — короткая памятка по эвристикам и правилам сопровождения
- `Makefile` — короткие алиасы для повседневных команд

## Базовый сценарий обновления списков

1. Перейти в рабочую папку проекта.

```bash
cd "/Users/vasiliizviadadze/Documents/New project"
```

2. Проверить, что оффлайн-генерация не ломает текущие списки.

```bash
python3 scripts/update_routing_lists.py --offline
```

Ожидаемый результат:

- `No changes.`

3. Подтянуть внешние источники и посмотреть diff без записи файлов.

```bash
python3 scripts/update_routing_lists.py
```

Если есть изменения, скрипт покажет unified diff по:

- `shadowrocket/ru-direct.list`
- `shadowrocket/ru-blocked-core.list`
- `shadowrocket/foreign-services.list`

4. Сохранить markdown-отчёт, если нужен читаемый summary.

```bash
python3 scripts/update_routing_lists.py --report-md reports/routing-update.md
```

5. Сгенерировать machine-readable отчёт, если нужен JSON для автоматизации.

```bash
python3 scripts/update_routing_lists.py --report-json -
```

6. Если diff устраивает, записать новые версии файлов.

```bash
python3 scripts/update_routing_lists.py --write
```

7. Прогнать общий smoke-check репозитория.

```bash
python3 scripts/smoke_check.py
```

8. Прогнать фиксированный набор регрессионных доменов.

```bash
python3 scripts/check_regression_domains.py
```

9. Проверить, что Streisand-экспорт синхронизирован с текущими `.list`.

```bash
python3 scripts/export_streisand_rules.py --offline
```

10. Проверить, что import-ready Streisand URI синхронизированы с профилями.

```bash
python3 scripts/export_streisand_uri.py --offline
```

То же самое короткими алиасами:

```bash
make offline
make update
make write
make streisand
make streisand-uri
make streisand-qr
make smoke
make regression
```

Если обычный split-URI слишком тяжёлый для QR или клиент нестабилен при импорте, использовать:

- `streisand/routing-profile-split-qr.json`
- `streisand/routing-profile-split-qr.streisand-uri.txt`

## Как менять списки вручную

### Добавить или убрать ручные домены

Редактировать:

- `data/manual_direct.json`
- `data/manual_blocked.json`
- `data/manual_foreign.json`

Там задаются:

- секции
- порядок доменов
- заголовки
- fallback-блоки

После правки прогнать:

```bash
python3 scripts/update_routing_lists.py --offline --write
```

### Изменить источники, приоритеты и фильтрацию

Редактировать:

- `data/routing_settings.json`

Там настраиваются:

- `sources`
- `priority`
- `notes`
- `exclude_domains`
- лимиты роста списков
- `direct_override`
- политика по TLD

После правки полезно проверить:

```bash
python3 -m json.tool data/routing_settings.json >/dev/null
python3 scripts/update_routing_lists.py --offline
python3 scripts/export_streisand_rules.py --offline
python3 scripts/export_streisand_uri.py --offline
python3 scripts/check_regression_domains.py
python3 scripts/update_routing_lists.py --report-json -
python3 scripts/smoke_check.py
```

## Как публиковать изменения

1. Посмотреть статус:

```bash
git status --short
```

2. Добавить нужные файлы:

```bash
git add .github README.md WORKFLOW.md Makefile data docs scripts shadowrocket streisand
```

3. Создать коммит:

```bash
git commit -m "Update routing lists"
```

4. Запушить:

```bash
git push
```

Если обычный SSH на `github.com:22` рвётся, рабочий fallback:

```bash
git push ssh://git@ssh.github.com:443/killerloop85/ios-routing.git HEAD:main
```

## GitHub Actions

В репозитории есть два workflow:

- `.github/workflows/smoke-check.yml` — CI smoke-check на `push`, `pull_request`, `workflow_dispatch`
- `.github/workflows/routing-report.yml` — weekly/manual запуск апдейтера с сохранением `json`, `md` и `diff` как artifact

## Быстрые команды

Показать все алиасы:

```bash
make help
```

Проверка генерации:

```bash
make offline
```

Smoke-check:

```bash
make smoke
```

Regression-check:

```bash
make regression
```

Запись Streisand-экспортов:

```bash
make streisand
```

Запись только Streisand URI:

```bash
make streisand-uri
```

Просмотр diff с сетью:

```bash
make update
```

Запись новых `.list`:

```bash
make write
```

JSON-отчёт:

```bash
make report-json
```

Markdown-отчёт:

```bash
make report-md
```

Проверка генерации:

```bash
python3 scripts/update_routing_lists.py --offline
```

Smoke-check:

```bash
python3 scripts/smoke_check.py
```

Regression-check:

```bash
python3 scripts/check_regression_domains.py
```

Проверка Streisand-синхронизации:

```bash
python3 scripts/export_streisand_rules.py --offline
```

Проверка Streisand URI-синхронизации:

```bash
python3 scripts/export_streisand_uri.py --offline
```

Просмотр diff с сетью:

```bash
python3 scripts/update_routing_lists.py
```

Запись новых `.list`:

```bash
python3 scripts/update_routing_lists.py --write
```

JSON-отчёт:

```bash
python3 scripts/update_routing_lists.py --report-json -
```

Markdown-отчёт:

```bash
python3 scripts/update_routing_lists.py --report-md reports/routing-update.md
```

## Что важно помнить

- Истина для ручных доменов теперь в `data/*.json`, а не в `shadowrocket/*.list`
- `shadowrocket/*.list` лучше не редактировать напрямую, если хочешь сохранить совместимость с генератором
- После любых ручных правок в `data/` лучше прогонять `--offline --write`
- Для community-источников шум лучше убирать через `exclude_domains`, а не точечными хаками в коде
- Регрессионный набор лежит в `data/regression_domains.json`, а правила сопровождения коротко зафиксированы в `docs/routing-dev-heuristics.md`
