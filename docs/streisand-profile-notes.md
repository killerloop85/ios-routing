# Streisand Profile Notes

Короткая заметка по четырём реальным Streisand-профилям, которые были декодированы из `streisand://` import-ссылок и использованы как референсы для проекта.

## Текущий статус

- Streisand-экспорт в этом репозитории пока считается experimental.
- JSON, URI и QR-артефакты проходят локальную валидацию и smoke-check, но это ещё не доказывает корректную работу маршрутизации внутри клиента Streisand.
- Есть уже подтверждённый полевой кейс, что split-routing в Streisand ведёт себя некорректно: `routing-profile-split-qr` на `ip.ru` показал NL вместо ожидаемого DIRECT/RU.
- Поэтому любой профиль Streisand нужно подтверждать ручным тестом на реальном клиенте.
- Тяжёлый `routing-profile-split.json` сохраняется как reference JSON, но больше не публикуется как import-ready URI: практический импортный контур сейчас ограничен `routing-profile-full.*` и `routing-profile-split-qr.*`.
- Default CLI/export path теперь должен генерировать только `routing-profile-full.*`; split-артефакты собираются только по явному experimental opt-in.
- Для повторяемых проверок использовать фиксированный чек-лист из `docs/streisand-field-test-matrix.md`.

## Что внутри этих ссылок

- Это не JSON, а сериализованный `route`-профиль Streisand в `bplist`-формате.
- После base64-декодирования внутри лежат:
  - `name`
  - `uuid`
  - `domainStrategy`
  - `domainMatcher`
  - `rules`
- Каждое правило обычно содержит:
  - `domain`
  - `ip`
  - `outboundTag`
  - иногда `port`

## Профиль 1: `Россия`

- `geosite:category-ads-all -> block`
- большой набор blocked/foreign-доменов и `geosite:* -> proxy`
- финальный fallback через `direct`

Практический вывод:

- полезен как референс реального пользовательского Streisand-профиля;
- полезен для понимания того, что Streisand вживую использует `geosite:*` и `outboundTag`;
- как source of truth для проекта не подходит, потому что в нём смешаны ручные выборки доменов и geosite-слои.

## Профиль 2: `Россия и Youtube`

- очень похож на первый профиль;
- дополнительно явно добавлены `youtube`, `whatsapp`, `dell`;
- внутри встречаются шумовые/пустые элементы.

Практический вывод:

- полезен как пример «ручного расширения» пользовательского профиля;
- в репозиторий как эталон его тащить не стоит;
- показывает, что живые импорт-профили могут быть не очень чистыми, поэтому наши генераторы должны оставаться более строгими и нормализованными.

## Профиль 3: `Заграница`

- `geoip:RU -> proxy`
- `domain:RU -> proxy`
- `final -> direct`

Практический вывод:

- это отдельный сценарий "я нахожусь за пределами РФ, а российский трафик хочу отправлять через proxy";
- для текущей архитектуры `ru-direct / ru-blocked-core / foreign-services` он не является базовым;
- при необходимости его можно позже оформить как отдельный optional-профиль, но не как дефолтный split/full режим.

## Профиль 4: `Все через VPN`

- локальные и private-IP сети идут `direct`;
- `localhost`, `local`, `captive.apple.com`, `geosite:private`, `geosite:apple`, `geosite:icloud` идут `direct`;
- весь остальной трафик — через `proxy`;
- есть отдельный proxy-IP блок для Google/Telegram.

Практический вывод:

- это самый полезный референс для нашего full-tunnel профиля;
- из него имеет смысл перенять именно `local/private` direct-блоки;
- Google/Telegram proxy-IP блоки пока не переносятся автоматически, потому что в текущем проекте source of truth строится вокруг доменных списков, а не отдельного ручного IP-core.

## Что уже перенесено в проект

- в `streisand/routing-profile-split.json` и `streisand/routing-profile-full.json` теперь есть явные `local/private` direct-блоки;
- они основаны на текущей политике проекта и идеях из профиля `Все через VPN`, но остаются чище и предсказуемее для сопровождения.
- поверх этих JSON-профилей теперь можно генерировать import-ready `streisand://...` URI без ручного редактирования.

## Compact QR profile

`routing-profile-split-qr.json` существует для отдельного операционного кейса: обычный split-URI слишком большой для одного практичного QR или сам клиент становится нестабилен при импорте.

Этот профиль намеренно компактнее основного split-профиля:

- сохраняет `local/private` direct-поведение;
- сохраняет `domain:ru`, `domain:su`, `geoip:ru` как direct-RU слой;
- использует небольшой curated `proxy-core` на основе `geosite:*` и короткого списка high-value `domain:*`;
- сохраняет `final -> proxy`.

То есть это policy-compatible профиль по смыслу, но оптимизированный под размер transport-артефакта и стабильность клиента, а не под полное 1:1 раскрытие всех routing buckets.

## Что сейчас считать безопасным набором

- `routing-profile-full.json` и `routing-profile-full.streisand-uri.txt` — основной рекомендуемый путь для реального клиента Streisand.
- `routing-profile-split-qr.json` и `routing-profile-split-qr.streisand-uri.txt` — диагностический split-вариант для ручного теста, но не рабочий production-профиль.
- `routing-profile-split.json` — reference-only JSON для сопровождения policy и диффов, но не для обычного import-flow.

## Как разбирать расхождения

- `mapping_bug` — когда export-layer, вероятно, собрал профиль не в той семантике, что ожидает routing core.
- `client_limitation` — когда профиль выглядит логично, но сам Streisand применяет правила по-другому.
- `transport_issue` — когда профиль не импортируется, клиент падает или импорт не сохраняется корректно.

## Что пока сознательно не делаем

- не экспортируем тяжёлый `routing-profile-split.json` как `streisand://` import-URI;
- не делаем эти четыре пользовательских профиля source of truth;
- не переносим в генератор случайные ручные домены или шумовые элементы из импортов;
- не строим отдельный IP-heavy профиль под Google/Telegram, пока это не закреплено в общей политике репозитория.
