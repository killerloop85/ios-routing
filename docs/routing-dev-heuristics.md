# Routing Dev Heuristics

Короткая памятка по поддержке routing-репозитория.

## Правила работы

1. Не редактировать `shadowrocket/*.list` вручную, если правка относится к manual core.
   Истина лежит в `data/manual_*.json`, а `.list` считаются сгенерированным артефактом.

2. Не раздувать `ru-blocked-core.list`.
   Туда идёт компактное ядро блокировок, а не весь реестр. Для новых доменов нужен либо явный high-value кейс, либо как минимум два независимых сигнала из внешних источников.

3. Сначала parent suffix, потом subdomain.
   Если уже есть `example.ru`, не нужно добавлять `www.example.ru` или `sub.example.ru`. Отдельный subdomain оправдан только когда у него реально другая политика, и это стоит зафиксировать в комментарии и в регрессионных тестах.

4. `exclude_domains` использовать как last resort.
   Это инструмент для чистки шумных community-источников, а не замена нормальной bucket-политики в manual core.

5. `--strict` включать осознанно.
   Падение в strict-режиме означает, что обязательный источник недоступен или существенно изменился. В таком случае нужно либо чинить источник, либо пересматривать его `optional`-статус и фильтры.

6. Любое изменение routing-логики нужно прогонять минимум в три шага.
   Сначала `python3 scripts/update_routing_lists.py --offline`, потом `python3 scripts/smoke_check.py`, затем `python3 scripts/check_regression_domains.py`.

## Регрессионный набор

- Машиночитаемый набор лежит в `data/regression_domains.json`.
- Он покрывает:
  - ожидаемые `DIRECT` домены;
  - ожидаемые `PROXY` домены из `ru-blocked-core`;
  - ожидаемые `PROXY` домены из `foreign-services`;
  - пограничные кейсы для `FINAL,PROXY`, parent-suffix inheritance и `.ru/.su` fallback.

## Что проверяет regression-check

- bucket `DIRECT` или `PROXY`;
- правило-источник: `ru-direct`, `ru-blocked-core`, `foreign-services` или `FINAL`;
- при необходимости точный suffix, который должен сработать.
