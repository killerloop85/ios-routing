# Hiddify Routing Spec

## 1. Goal

Add Hiddify as the third routing consumer in this repository while reusing the same routing policy as Shadowrocket and Streisand.

The Hiddify layer must stay a thin export layer:

- it reads finalized Shadowrocket `.list` files;
- it does not reimplement candidate collection or source heuristics;
- it mirrors the same routing buckets:
  - `ru-direct`
  - `ru-blocked-core`
  - `foreign-services`

## 2. Source Of Truth

Hiddify does not introduce a separate routing engine.

The authoritative policy remains:

- `data/manual_direct.json`
- `data/manual_blocked.json`
- `data/manual_foreign.json`
- `data/routing_settings.json`

The actual export input remains:

- `shadowrocket/ru-direct.list`
- `shadowrocket/ru-blocked-core.list`
- `shadowrocket/foreign-services.list`

## 3. Output Structure

Generated artifacts live in `hiddify/`:

- `hiddify/ru-direct.hiddify.json`
- `hiddify/ru-blocked-core.hiddify.json`
- `hiddify/foreign-services.hiddify.json`
- `hiddify/routing-profile-split.json`
- `hiddify/routing-profile-full.json`

Import/share URI generation is intentionally out of scope for the first pass.

## 4. Bucket Files

Each bucket file is a normalized JSON document:

```json
{
  "name": "RU Direct",
  "description": "Russian and socially significant domains that should stay DIRECT.",
  "platform": "hiddify",
  "rules": [
    {
      "type": "domain_suffix",
      "value": "gosuslugi.ru",
      "outbound": "direct",
      "bucket": "ru-direct"
    }
  ]
}
```

Supported first-pass rule types:

- `domain_suffix`
- `domain`
- `ip_cidr`
- `geoip`
- `geosite`
- `final`

Supported outbounds:

- `direct`
- `proxy`
- `block`

## 5. Profiles

### Split Profile

`routing-profile-split.json` must describe these layers in order:

1. `local`
2. `ru-blocked-core`
3. `ru-direct`
4. `foreign-services`
5. `final`

It includes:

- explicit `local/private` direct rules;
- `source` references to generated Hiddify bucket files;
- explicit `geoip:ru` in the RU-direct layer;
- `final -> proxy`.

### Full Profile

`routing-profile-full.json` keeps:

- `local/private -> direct`
- `final -> proxy`

## 6. Validation Guarantees

The repository must guarantee that:

1. Hiddify bucket files are synchronized with Shadowrocket `.list` files.
2. Hiddify routing semantics match Shadowrocket and Streisand on the fixed regression set.
3. Smoke checks validate both structure and sync counts.
4. Hiddify remains a thin export layer and not a second source of truth.
