# Workflow

Короткая инструкция по ежедневной работе с routing-репозиторием.

## Что где лежит

- `shadowrocket/` — готовые `.conf` и итоговые `.list` для Shadowrocket
- `data/` — source of truth для ручного ядра, source pool, приоритетов и override-правил
- `scripts/update_routing_lists.py` — генератор и апдейтер списков
- `docs/routing-update-spec.md` — техническая спецификация логики обновления

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
python3 scripts/update_routing_lists.py --report-json -
```

## Как публиковать изменения

1. Посмотреть статус:

```bash
git status --short
```

2. Добавить нужные файлы:

```bash
git add README.md WORKFLOW.md data scripts shadowrocket
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

## Быстрые команды

Проверка генерации:

```bash
python3 scripts/update_routing_lists.py --offline
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
