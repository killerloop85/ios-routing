# Clash Routing Spec

## Goal

Add Clash for Windows / mihomo as another thin export layer on top of the shared routing core.

The Clash layer must:

- reuse the same finalized routing lists as Shadowrocket, Streisand, Hiddify, and Happ;
- preserve the same buckets: `ru-direct`, `ru-blocked-core`, `foreign-services`, plus `local/private` and `final`;
- avoid introducing a second routing engine or a separate source of truth.

## Source of Truth

Clash exports are generated only from the finalized Shadowrocket lists:

- `shadowrocket/ru-direct.list`
- `shadowrocket/ru-blocked-core.list`
- `shadowrocket/foreign-services.list`

The policy itself still lives in:

- `data/manual_direct.json`
- `data/manual_blocked.json`
- `data/manual_foreign.json`
- `data/routing_settings.json`
- `scripts/update_routing_lists.py`

## Output Structure

Generated Clash artifacts live in `clash/`:

- `ru-direct.rules.yaml`
- `ru-blocked-core.rules.yaml`
- `foreign-services.rules.yaml`
- `routing-profile-full.yaml`
- `routing-profile-split.yaml`
- `routing-profile-split-direct-default.yaml`

## Rule Format

Bucket rule files are YAML wrappers around raw Clash rule strings:

```yaml
rules:
  - "DOMAIN-SUFFIX,gosuslugi.ru,DIRECT"
  - "DOMAIN-SUFFIX,nalog.ru,DIRECT"
```

Supported generated rule kinds:

- `DOMAIN-SUFFIX,...`
- `DOMAIN,...`
- `IP-CIDR,...,no-resolve`
- `GEOIP,...,no-resolve`
- `MATCH,...`

## Profile Semantics

### `routing-profile-full.yaml`

Status:

- stable
- production-ready as a routing profile template

Semantics:

- `local/private` stays `DIRECT`
- everything else falls through to `MATCH,PROXY`

### `routing-profile-split.yaml`

Status:

- experimental
- parity-oriented

Semantics:

- `local/private` -> `DIRECT`
- `ru-blocked-core` -> `PROXY`
- `ru-direct` -> `DIRECT`
- `foreign-services` -> `PROXY`
- `GEOIP,RU,DIRECT,no-resolve`
- final fallback -> `MATCH,PROXY`

### `routing-profile-split-direct-default.yaml`

Status:

- experimental
- Happ-style direct-default variant

Semantics:

- same ordered buckets as the parity split profile
- final fallback -> `MATCH,DIRECT`

## Proxy Groups

The Clash layer intentionally does not own real nodes.

Profiles therefore define only minimal routing groups:

- `PROXY`
- `DIRECT`

The expectation is that users merge these routing profiles with their existing Clash nodes or subscriptions.

## Validation

Clash exports participate in the same repository checks:

- `scripts/export_clash_rules.py --offline`
- `scripts/check_regression_domains.py`
- `scripts/smoke_check.py`

Smoke checks validate:

- generated YAML structure
- presence of `rules:`
- presence of final `MATCH`
- sync between bucket rule files and Shadowrocket lists
- parity of the split profile against the shared regression domain set

## Future Extensions

Possible later improvements:

- richer proxy-groups (`url-test`, `fallback`, providers)
- GEOIP or IP-specific policy layers beyond the current local/private block
- rule-provider output if a future Clash workflow benefits from it
