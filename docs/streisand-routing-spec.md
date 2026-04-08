# Streisand Routing Spec

## 1. Цель

Добавить в текущий проект второй потребитель routing-слоя — **Streisand** (Linux/macOS GUI-клиент с собственным форматом правил), используя те же источники и эвристики, что и для Shadowrocket.

Задачи:

- Генерировать Streisand-совместимые rule-файлы **из тех же `data/*.json` и внешних источников**, что и для Shadowrocket.
- Сохранить одну общую политику роутинга: `ru-direct`, `ru-blocked-core`, `foreign-services`.
- Обеспечить автоматический и регрессионно проверяемый экспорт в форматы Streisand.

## 2. Целевая структура для Streisand

Добавить каталог:

- `streisand/` — выходные файлы для Streisand.

Минимальный набор файлов:

- `streisand/ru-direct.streisand.json` — список правил для RU-direct.
- `streisand/ru-blocked-core.streisand.json` — правила для ядра блокировок.
- `streisand/foreign-services.streisand.json` — правила для foreign-сервисов.
- (опционально) `streisand/routing-profile-split.json` — готовый профиль split-routing.
- (опционально) `streisand/routing-profile-full.json` — профиль полного туннеля.

Streisand-формат фиксируем так:

```jsonc
{
  "name": "RU Direct",
  "description": "Russian and socially significant domains that should stay DIRECT.",
  "rules": [
    {
      "type": "domain_suffix",
      "value": "gosuslugi.ru",
      "action": "direct",
      "bucket": "ru-direct"
    },
    {
      "type": "domain_suffix",
      "value": "ru",
      "action": "direct",
      "bucket": "ru-direct",
      "note": "fallback .ru"
    }
  ]
}
```

Принципы:

- `type`: `"domain_suffix"` для доменов, `"ip_cidr"` для IP-сетей (на будущее).
- `value`: чистый суффикс без префикса `DOMAIN-SUFFIX,`.
- `action`: `"direct"` или `"proxy"`.
- `bucket`: логический слой (`"ru-direct"`, `"ru-blocked-core"`, `"foreign-services"`).
- Дополнительные поля (`note`, `source`) допускаются, но не обязательны.

## 3. Источники и связь с существующим слоем

**Source of truth не дублируется**:

- Используются те же файлы:
  - `data/manual_direct.json`
  - `data/manual_blocked.json`
  - `data/manual_foreign.json`
  - `data/routing_settings.json`
  - внешние источники из `sources` (как для Shadowrocket).

**Генерация Streisand-слоя происходит уже после** того, как:

- Собраны кандидаты из внешних источников.
- Применены лимиты, overrides и conflict-policy.
- Сгенерированы и стабилизированы итоговые `.list`:
  - `shadowrocket/ru-direct.list`
  - `shadowrocket/ru-blocked-core.list`
  - `shadowrocket/foreign-services.list`

Streisand-файлы должны опираться **на итоговые списки**, а не на сырые источники.

## 4. Правила генерации Streisand-файлов

### 4.1 Общие правила

1. Читать три итоговых списка из `shadowrocket/` и превращать каждую строку вида:

   ```text
   DOMAIN-SUFFIX,example.com
   ```

   в Streisand-правило:

   ```json
   {
     "type": "domain_suffix",
     "value": "example.com",
     "action": "direct",
     "bucket": "ru-direct"
   }
   ```

2. Маппинг action/bucket:

- `ru-direct.list` → `action: "direct"`, `bucket: "ru-direct"`.
- `ru-blocked-core.list` → `action: "proxy"`, `bucket: "ru-blocked-core"`.
- `foreign-services.list` → `action: "proxy"`, `bucket: "foreign-services"`.

3. Структура файлов:

- Один JSON-объект верхнего уровня: `{ name, description, rules }`.
- `rules` — массив однородных объектов.

4. Порядок правил должен соответствовать порядку доменов в `.list`, чтобы проще было eyeball-diff сопоставлять.

### 4.2 `ru-direct.streisand.json`

- Название: `"RU Direct"`.
- Описание: `"Russian and socially significant domains that should stay DIRECT."`.
- Все домены из `shadowrocket/ru-direct.list` преобразуются в правила с `action: "direct"`.
- Fallback-суффиксы `ru` и `su` сохраняются как отдельные правила с понятной `note`.

### 4.3 `ru-blocked-core.streisand.json`

- Название: `"RU Blocked Core"`.
- Описание: `"Compact core of domains that almost always require PROXY in Russia."`.
- Все домены из `shadowrocket/ru-blocked-core.list` → `action: "proxy"`, `bucket: "ru-blocked-core"`.

### 4.4 `foreign-services.streisand.json`

- Название: `"Foreign Services"`.
- Описание: `"Foreign services that are restricted in Russia or work better through PROXY."`.
- Все домены из `shadowrocket/foreign-services.list` → `action: "proxy"`, `bucket: "foreign-services"`.

### 4.5 Профили (`routing-profile-split.json`, `routing-profile-full.json`)

Опционально:

1. **Split-profile**:

```jsonc
{
  "name": "RU Split Routing",
  "description": "Direct RU and core domestic traffic, proxy blocked core and foreign services.",
  "priority": [
    "ru-blocked-core",
    "ru-direct",
    "foreign-services",
    "final"
  ],
  "sources": [
    "ru-blocked-core",
    "ru-direct",
    "foreign-services"
  ],
  "final_action": "proxy"
}
```

2. **Full-tunnel profile**:

```jsonc
{
  "name": "Full VPN",
  "description": "All non-local traffic through proxy, keeping LAN direct.",
  "priority": [
    "local",
    "final"
  ],
  "sources": [],
  "final_action": "proxy"
}
```

Здесь `sources` и `priority` — Streisand-специфичная логика (можно донастроить после первой интеграции).

## 5. Интеграция в скрипты и workflow

### 5.1 Новый скрипт генерации

Добавить:

- `scripts/export_streisand_rules.py`

Требования:

- Работает **после** `update_routing_lists.py`, использует только итоговые `.list`.
- Параметры:
  - `--write` — записать Streisand-файлы в `streisand/`.
  - `--offline` — не ходить в сеть, просто пересобрать из локальных `.list`.
  - `--report-json` — опционально выводить JSON-сводку (количество правил, diff по buckets).

### 5.2 Интеграция в `Makefile`

Добавить цели:

```make
streisand:
	python3 scripts/export_streisand_rules.py --write

smoke:
	python3 scripts/update_routing_lists.py --offline
	python3 scripts/check_regression_domains.py
	python3 scripts/export_streisand_rules.py --offline
	python3 scripts/smoke_check.py
```

Главное, чтобы streisand-экспорт входил в smoke-цепочку хотя бы в offline-режиме.

### 5.3 Интеграция в CI

В `.github/workflows/smoke-check.yml`:

- После шага `Run smoke check` можно добавить отдельный шаг:

```yaml
- name: Export Streisand rules (offline)
  run: python3 scripts/export_streisand_rules.py --offline
```

В `routing-report.yml`:

- Для полноты можно добавлять размеры/статистику Streisand-файлов в отчёт, но это опционально.

## 6. Регрессионные проверки для Streisand

Так как Streisand-файлы генерируются строго из `shadowrocket/*.list`, **отдельный Streisand-specific regression-набор не обязателен**. Достаточно:

- существующего `data/regression_domains.json`;
- проверки того, что каждый домен из `cases` резолвится в тот же `bucket`/`rule` при парсинге Streisand-JSON, как и при парсинге Shadowrocket-lists.

Можно добавить в `check_regression_domains.py` второй backend-резолвер:

- один резолвит по `.list`;
- другой — по Streisand-JSON;
- и убедиться, что для всех кейсов bucket/rule совпадают.

## 7. Выходные гарантии

После интеграции Codex должен обеспечивать:

1. `streisand/*.json` всегда синхронизированы с `shadowrocket/*.list` (без ручного редактирования).
2. Формат Streisand-файлов стабильный: валидный JSON, только `domain_suffix`-правила, только `direct/proxy`.
3. Любые изменения в эвристиках и источниках автоматически отражаются в обоих потребителях (Shadowrocket и Streisand) через общие `data/` и `update_routing_lists.py`.

## 8. Пример Streisand-профиля под Россию

Ниже референсный профиль, который использует ту же архитектуру bucket-ов:

```jsonc
{
  "name": "Russia Split Routing (ru-blocked)",
  "description": "RU domains and IPs direct, ru-blocked core and foreign services via proxy.",
  "priority": [
    "local",
    "ru-direct",
    "ru-blocked-core",
    "foreign-services",
    "final"
  ],
  "rules": [
    {
      "name": "Local networks",
      "entries": [
        "ipcidr:127.0.0.0/8",
        "ipcidr:10.0.0.0/8",
        "ipcidr:172.16.0.0/12",
        "ipcidr:192.168.0.0/16",
        "ipcidr:100.64.0.0/10"
      ],
      "action": "direct",
      "bucket": "local"
    },
    {
      "name": "RU direct (TLD + GeoIP)",
      "entries": [
        "domain:ru",
        "domain:su",
        "geoip:ru"
      ],
      "action": "direct",
      "bucket": "ru-direct"
    },
    {
      "name": "RU blocked core",
      "entries": [
        "geosite:ru-blocked",
        "geosite:ru-blocked-all"
      ],
      "action": "proxy",
      "bucket": "ru-blocked-core"
    },
    {
      "name": "Foreign services (manual core)",
      "entries": [
        "domain:openai.com",
        "domain:chatgpt.com",
        "domain:anthropic.com",
        "domain:claude.ai",
        "domain:perplexity.ai",
        "domain:notion.so",
        "domain:figma.com",
        "domain:github.com",
        "domain:cloudflare.com",
        "domain:google.com",
        "domain:googleapis.com"
      ],
      "action": "proxy",
      "bucket": "foreign-services"
    },
    {
      "name": "Final fallback",
      "entries": [
        "final"
      ],
      "action": "proxy",
      "bucket": "final"
    }
  ]
}
```

## 9. Re-filter и ru-blocked для Streisand

Для Streisand не нужны отдельные "streisand-версии" Re-filter. Используются готовые релизы и текстовые списки из **1andrevich/Re-filter-lists**:

- Репозиторий: `https://github.com/1andrevich/Re-filter-lists`
- Базовый доменный список: `domains_all.lst`
- Дополнительный community-слой: `community.lst`
- При необходимости в будущем можно использовать `.srs` ruleset-релизы, если Streisand научится читать их напрямую.

Для текущего проекта приоритетный путь такой:

- качать `domains_all.lst` и/или `community.lst`;
- парсить домены;
- фильтровать их текущими эвристиками (`ru-blocked-core` vs bulk);
- уже потом экспортировать выбранное ядро в Streisand-JSON с `action: "proxy"`.

## 10. Как добавлять новый blocked-домен

Если нужно добавить новый явно заблокированный сайт:

1. Открыть `data/manual_blocked.json`.
2. Добавить домен в нужную секцию.
3. Перегенерировать списки:

```bash
python3 scripts/update_routing_lists.py --offline --write
python3 scripts/check_regression_domains.py
python3 scripts/smoke_check.py
```

После этого:

- домен попадёт в `shadowrocket/ru-blocked-core.list`;
- а после будущего экспорта Streisand — и в `streisand/ru-blocked-core.streisand.json`.
