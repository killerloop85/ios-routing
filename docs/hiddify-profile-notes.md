# Hiddify Profile Notes

Короткие заметки по Hiddify-слою в этом репозитории.

## Что считаем референсом

На этом этапе Hiddify-поддержка опирается не на один конкретный import-формат клиента, а на нормализованный JSON routing-layer, который:

- стабилен для diff'ов;
- легко проверяется в CI;
- отражает ту же policy-модель, что Shadowrocket и Streisand.

То есть референсом является не отдельная share-ссылка, а согласованная routing-семантика проекта.

## Что переносим в Hiddify

- `local/private` direct-слой;
- `geosite:private`, `geosite:apple`, `geosite:icloud`;
- `geoip:private`;
- `geoip:ru` в split-профиле;
- explicit `final -> proxy`;
- bucket-модель:
  - `ru-direct`
  - `ru-blocked-core`
  - `foreign-services`

## Что сознательно не переносим автоматически

- нестабильные import/share URI;
- клиент-специфичные undocumented поля;
- отдельный второй source of truth;
- ручную логику сбора доменов в обход `update_routing_lists.py`.

## Текущий статус

- Hiddify-слой в репозитории считается thin export layer.
- Он должен быть semantic-parity слоем по отношению к Shadowrocket и Streisand.
- При необходимости import-format можно будет добавить поверх этих JSON-артефактов позже, не ломая policy-модель.
