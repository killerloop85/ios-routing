# Workflow

Короткая инструкция по ежедневной работе с routing-репозиторием.

## Что где лежит

- `shadowrocket/` — готовые `.conf` и итоговые `.list` для Shadowrocket
- `streisand/` — экспортированные JSON-правила и профили для Streisand
- `streisand/*.streisand-uri.txt` — готовые import-ready `streisand://...` ссылки только для safe-профилей
- `streisand/routing-profile-split-qr.*` — компактный split-профиль под QR и нестабильный импорт
- `hiddify/` — экспортированные JSON-правила и профили для Hiddify
- `happ/` — экспортированные routing-профили для Happ
- `data/` — source of truth для ручного ядра, source pool, приоритетов и override-правил
- `scripts/update_routing_lists.py` — генератор и апдейтер списков
- `scripts/export_streisand_rules.py` — экспорт итоговых `.list` в Streisand JSON
- `scripts/export_streisand_uri.py` — экспорт стабильного Streisand full-профиля в import-ready URI; split-артефакты требуют явный experimental opt-in
- `scripts/export_hiddify_rules.py` — экспорт итоговых `.list` в Hiddify JSON
- `scripts/export_happ_routing.py` — экспорт итоговых `.list` в Happ JSON
- `scripts/check_regression_domains.py` — фиксированный regression-check по доменам
- `docs/routing-update-spec.md` — техническая спецификация логики обновления
- `docs/streisand-routing-spec.md` — ТЗ на второй consumer того же routing-слоя для Streisand
- `docs/streisand-profile-notes.md` — заметки по реальным `streisand://` профилям и что из них перенесено в проект
- `docs/streisand-field-test-matrix.md` — фиксированная матрица полевых проверок для Streisand
- `docs/streisand-10min-checklist.md` — короткий human-friendly сценарий ручной проверки Streisand
- `docs/hiddify-routing-spec.md` — ТЗ на thin export-layer для Hiddify
- `docs/hiddify-profile-notes.md` — заметки по Hiddify-слою и его границам
- `docs/happ-routing-spec.md` — ТЗ на thin export-layer для Happ
- `docs/happ-profile-notes.md` — заметки по Happ-слою и его ограничениями
- `docs/routing-dev-heuristics.md` — короткая памятка по эвристикам и правилам сопровождения
- `docs/ROADMAP.md` — короткий backlog по полевым проверкам и следующим улучшениям
- `Makefile` — короткие алиасы для повседневных команд

## Важная пометка по Streisand

- Streisand-слой пока считать experimental.
- Есть уже наблюдавшийся кейс, что routing в самом клиенте Streisand может работать неконсистентно даже при валидных JSON/URI-артефактах: в одном прогоне `ip.ru` на `routing-profile-split-qr` показывал NL вместо DIRECT/RU, но более поздние тесты дали рабочий `split-qr` и рабочий `full`.
- Любой Streisand-профиль перед практическим использованием нужно проверять вручную на реальном клиенте.
- До отдельного подтверждения не считать Streisand-экспорт production-ready наравне с Shadowrocket.
- Тяжёлый `routing-profile-split.json` считать reference-only и не использовать как обычный import-flow.
- `routing-profile-split-qr.*` тоже считать только диагностическим артефактом, а не рабочим split-профилем.
- Для практического импорта сейчас держать только `routing-profile-full.*`.
- Default-команды Streisand должны генерировать только stable full-path; split-профили разрешены только через явный experimental opt-in.
- Hiddify-слой считать thin export-layer: он должен быть семантически синхронизирован с Shadowrocket и не заменяет основной source of truth в `data/`.
- Happ-слой считать thin export-layer: он нужен как нормализованный routing JSON для Happ UI и не заменяет общий source of truth.
- `happ/routing-profile-split.json` считать parity-safe профилем.
- `happ/routing-profile-split-direct-default.json` считать Happ-специфичным direct-default профилем.

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

10. При необходимости отдельно проверить experimental split-артефакты Streisand.

```bash
python3 scripts/export_streisand_rules.py --offline --experimental-split
python3 scripts/export_streisand_uri.py --offline --experimental-split
```

11. Проверить, что safe Streisand URI синхронизированы с профилями.

```bash
python3 scripts/export_streisand_uri.py --offline
```

12. Проверить, что Hiddify-экспорт синхронизирован с текущими `.list`.

```bash
python3 scripts/export_hiddify_rules.py --offline
```

13. Проверить, что Happ-экспорт синхронизирован с текущими `.list`.

```bash
python3 scripts/export_happ_routing.py --offline
```

То же самое короткими алиасами:

```bash
make offline
make update
make write
make streisand
make streisand-uri
make streisand-experimental
make streisand-qr
make hiddify
make hiddify-check
make happ
make happ-check
make smoke
make regression
```

Если нужен split-режим в Streisand, помнить, что компактный вариант сейчас годится только для диагностики, а не для production-использования:

- `streisand/routing-profile-split-qr.json`
- `streisand/routing-profile-split-qr.streisand-uri.txt`

После этого всё равно обязательно проверить routing вручную в самом Streisand. Пока матрица полевых тестов не пройдена повторяемо, в реальной работе считать full предпочтительным, а split — только диагностическим.

Для ручной проверки в живом клиенте использовать checklist из:

- `docs/streisand-field-test-matrix.md`
- `docs/streisand-10min-checklist.md`

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
python3 scripts/export_hiddify_rules.py --offline
python3 scripts/export_happ_routing.py --offline
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
