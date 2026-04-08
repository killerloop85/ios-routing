# Streisand 10-Minute Checklist

Короткий practical-checklist для ручной проверки Streisand на реальном устройстве.

Основная идея:

- `full` — это единственный практический профиль Streisand на сейчас;
- `split-qr` — только диагностический профиль для расследования, не для постоянного использования.

Если времени мало, сначала прогоняй только блок `full`. Блок `split-qr` нужен только если ты специально проверяешь known issue или пытаешься локализовать проблему.

Подробная матрица ожиданий лежит в:

- `docs/streisand-field-test-matrix.md`

## Что заранее подготовить

- Версию клиента Streisand.
- Устройство, на котором тестируешь.
- Какой профиль проверяешь:
  - `routing-profile-full.*`
  - `routing-profile-split-qr.*`
- Любой удобный способ фиксировать результат:
  - заметка
  - скрин
  - короткая таблица

Минимальные поля заметки:

- `date`
- `device`
- `client_version`
- `profile`
- `target`
- `expected`
- `actual`
- `notes`

## Full Checklist

Цель: подтвердить, что full-profile реально ведёт весь внешний трафик через proxy, а локалку оставляет direct.

1. Импортируй `routing-profile-full.*`.
2. Убедись, что профиль импортировался без ошибки и применился.
3. Открой `ip.ru`.
   Ожидание: `PROXY`, внешний IP не российский.
4. Открой `gosuslugi.ru`.
   Ожидание: `PROXY`.
5. Открой `sberbank.ru`.
   Ожидание: `PROXY`.
6. Открой `youtube.com`.
   Ожидание: `PROXY`.
7. Открой `openai.com` или `chatgpt.com`.
   Ожидание: `PROXY`.
8. Открой `github.com`.
   Ожидание: `PROXY`.
9. Если можно проверить локальный адрес, проверь `localhost` или локальный сервис.
   Ожидание: `DIRECT`.
10. Если можно проверить captive/service-исключения, проверь `captive.apple.com`.
    Ожидание: `DIRECT`.

Если все шаги выглядят логично, full-profile можно считать practically usable на этом устройстве.

## Split-QR Diagnostic Checklist

Цель: понять, насколько split-routing в Streisand расходится с общим routing core.

1. Импортируй `routing-profile-split-qr.*`.
2. Убедись, что профиль импортировался и не крашит клиент.
3. Открой `ip.ru`.
   Ожидание: `DIRECT/RU`.
   Если видишь NL/proxy, зафиксируй это как mismatch и сразу сравни с `sweb.ru` или `yandex.ru` в том же прогоне.
4. Открой `gosuslugi.ru`.
   Ожидание: `DIRECT`.
5. Открой `nalog.ru`.
   Ожидание: `DIRECT`.
6. Открой `sberbank.ru`.
   Ожидание: `DIRECT`.
7. Открой `yandex.ru`.
   Ожидание: `DIRECT`.
8. Открой `bitrix24.ru` или `confael.ru`.
   Ожидание: `DIRECT`.
9. Открой `instagram.com`.
   Ожидание: `PROXY`.
10. Открой `youtube.com`.
    Ожидание: `PROXY`.
11. Открой `openai.com`.
    Ожидание: `PROXY`.
12. Открой `github.com`.
    Ожидание: `PROXY`.
13. Открой `yandex.com`.
    Ожидание: `PROXY`.

Если direct-кейсы уходят в proxy или в иностранный IP, split в Streisand на этом устройстве считать ненадёжным в этом конкретном прогоне и записывать это как наблюдение, а не как окончательный вердикт по клиенту.

## Как записывать расхождения

Используй три короткие категории:

- `mapping_bug`
  Похоже, наш export-layer собрал профиль не в той логике.

- `client_limitation`
  Профиль выглядит разумно, но Streisand применяет правила иначе.

- `transport_issue`
  Импорт ломается, профиль не сохраняется или клиент падает.

Пример записи:

```text
date: 2026-04-08
device: iPhone 15 Pro
client_version: Streisand x.y.z
profile: routing-profile-split-qr
target: ip.ru
expected: DIRECT/RU
actual: PROXY/NL
notes: client_limitation
```

## Когда тест считается достаточным

Минимально достаточно:

1. Прогнать `full` по 5-6 внешним целям и 1-2 local/service-кейсам.
2. Если нужен split-анализ, прогнать `split-qr` по `ip.ru`, одному гос-домену, одному банковскому, одному blocked-core и одному foreign-service.
3. Любое ключевое расхождение сразу фиксировать со скрином и категорией.
