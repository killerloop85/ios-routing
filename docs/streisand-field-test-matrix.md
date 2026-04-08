# Streisand Field Test Matrix

Фиксированный чек-лист для ручной проверки поведения Streisand на реальном клиенте. Это не source of truth для policy, а operational-слой поверх общего routing core.

## Как использовать

1. Выбрать профиль Streisand:
   - stable: `routing-profile-full.*`
   - diagnostic: `routing-profile-split-qr.*`
2. Импортировать профиль в реальный клиент.
3. Открыть домен или сервис.
4. Зафиксировать фактический результат:
   - `DIRECT/RU`
   - `PROXY/NL`
   - не открылось / крэш / импорт не применился
5. Если есть расхождение, приложить:
   - скрин результата
   - версию клиента Streisand
   - какой профиль использовался
   - краткую заметку, какой outbound ожидался по routing core

## Поля для заметки

- `date`
- `device`
- `client_version`
- `profile`
- `domain_or_ip`
- `expected_outbound`
- `actual_outbound`
- `notes`

## Split Expectations

Для `routing-profile-split-qr.*` ожидаемое поведение считается только диагностическим: оно показывает, как export-layer должен работать по смыслу, но не считается production-гарантией.

| Case | Target | Expected | Why |
| --- | --- | --- | --- |
| 1 | `ip.ru` | `DIRECT` | fallback `domain:ru` / `geoip:ru` |
| 2 | `gosuslugi.ru` | `DIRECT` | `ru-direct` |
| 3 | `nalog.ru` | `DIRECT` | `ru-direct` |
| 4 | `mos.ru` | `DIRECT` | `ru-direct` |
| 5 | `sberbank.ru` | `DIRECT` | `ru-direct` |
| 6 | `tinkoff.ru` | `DIRECT` | `ru-direct` |
| 7 | `sbp.nspk.ru` | `DIRECT` | `ru-direct` |
| 8 | `yandex.ru` | `DIRECT` | `ru-direct` |
| 9 | `mail.ru` | `DIRECT` | `ru-direct` |
| 10 | `vk.com` | `DIRECT` | `ru-direct` |
| 11 | `confael.ru` | `DIRECT` | manual direct override |
| 12 | `bitrix24.ru` | `DIRECT` | manual direct override |
| 13 | `instagram.com` | `PROXY` | blocked core |
| 14 | `facebook.com` | `PROXY` | blocked core |
| 15 | `discord.com` | `PROXY` | blocked core / compact proxy-core |
| 16 | `youtube.com` | `PROXY` | blocked core / compact proxy-core |
| 17 | `meduza.io` | `PROXY` | blocked core / compact proxy-core |
| 18 | `torproject.org` | `PROXY` | blocked core / compact proxy-core |
| 19 | `openai.com` | `PROXY` | foreign-services / compact proxy-core |
| 20 | `chatgpt.com` | `PROXY` | foreign-services |
| 21 | `claude.ai` | `PROXY` | foreign-services / compact proxy-core |
| 22 | `github.com` | `PROXY` | foreign-services / compact proxy-core |
| 23 | `cloudflare.com` | `PROXY` | foreign-services / compact proxy-core |
| 24 | `google.com` | `PROXY` | foreign-services / compact proxy-core |
| 25 | `proton.me` | `PROXY` | foreign-services / compact proxy-core |
| 26 | `yandex.com` | `PROXY` | falls through to final proxy in normalized core |

## Full Expectations

Для `routing-profile-full.*` почти весь нелокальный трафик должен идти через `PROXY`; direct остаются только локальные/служебные правила.

| Case | Target | Expected | Why |
| --- | --- | --- | --- |
| 1 | `localhost` | `DIRECT` | local rule |
| 2 | `captive.apple.com` | `DIRECT` | service direct rule |
| 3 | `ip.ru` | `PROXY` | full tunnel final proxy |
| 4 | `gosuslugi.ru` | `PROXY` | full tunnel final proxy |
| 5 | `sberbank.ru` | `PROXY` | full tunnel final proxy |
| 6 | `instagram.com` | `PROXY` | full tunnel final proxy |
| 7 | `youtube.com` | `PROXY` | full tunnel final proxy |
| 8 | `openai.com` | `PROXY` | full tunnel final proxy |
| 9 | `github.com` | `PROXY` | full tunnel final proxy |
| 10 | `8.8.8.8` | `PROXY` | full tunnel final proxy |

## IP Scenarios

Минимальные IP-проверки, если клиент позволяет проверить IP-адрес или IP-only ресурс:

| Case | Target | Profile | Expected |
| --- | --- | --- | --- |
| 1 | `127.0.0.1` | full / split | `DIRECT` |
| 2 | `192.168.1.1` | full / split | `DIRECT` |
| 3 | `100.64.0.1` | full / split | `DIRECT` |
| 4 | `8.8.8.8` | full | `PROXY` |
| 5 | public RU IP test if available | split | `DIRECT` |

## Как классифицировать расхождение

- `mapping_bug`
  - JSON/URI профиль собран не так, как предполагает общий routing core.
  - Подозревать: порядок правил, `domainMatcher`, `domainStrategy`, `final`, `geoip`, `source:*` expansion.

- `client_limitation`
  - Экспорт выглядит логично, но клиент Streisand применяет правила иначе.
  - Подозревать: import parser, precedence между `domain`/`geoip`, игнор части полей, версия клиента.

- `transport_issue`
  - Профиль не импортируется, импорт крашится или клиент не сохраняет его корректно.

## Exit Criteria

Streisand можно считать вышедшим из experimental-статуса только если:

1. Full-profile стабильно проходит базовый checklist на нескольких устройствах/версиях клиента.
2. Split diagnostic profile проходит матрицу direct/proxy кейсов без ключевых расхождений вроде `ip.ru -> NL`.
3. Все зафиксированные расхождения либо исправлены в export-layer, либо документированы как ограничение клиента.
