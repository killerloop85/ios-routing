# Happ Profile Notes

Короткие заметки по Happ-слою в этом репозитории.

## Что считаем Happ-слоем

Happ здесь представлен как нормализованный JSON export-layer, который удобно:

- читать глазами;
- диффить в git;
- использовать как источник для ручного ввода правил в клиенте;
- проверять в smoke/regression.

## Что переносим

- `local/private` direct-правила;
- `ru-direct` как direct bucket;
- `ru-blocked-core` и `foreign-services` как proxy buckets;
- `final` как proxy-default поведение для профиля split, чтобы сохранить parity с проектным routing-core.

## Что пока сознательно не делаем

- не генерируем import/share URI автоматически;
- не делаем отдельный Happ-specific source of truth;
- не добавляем IP-heavy policy без отдельного решения;
- не добавляем block-layer автоматически, пока он пустой по policy.

## Практический статус

- Happ-слой считается thin export layer.
- Он нужен для консистентного переноса общей routing-политики, а не как отдельный движок принятия решений.
- Если в живом клиенте Happ появятся особенности, их лучше документировать отдельно, не ломая общий policy-core.
