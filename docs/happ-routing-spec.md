# Happ Routing Spec

## Goal

Happ is the fourth consumer of the shared routing core in this repository.

It must:

- reuse the same routing buckets as Shadowrocket, Streisand, and Hiddify;
- stay a thin export layer over finalized `.list` files;
- avoid duplicating domain-collection heuristics.

## Output

Generated artifacts live in `happ/`:

- `routing-profile-split.json`
- `routing-profile-full.json`

An optional human-oriented helper file also exists:

- `happ/README.md`

## Source Of Truth

Happ does not introduce a new policy engine.

Authoritative routing logic still lives in:

- `data/manual_direct.json`
- `data/manual_blocked.json`
- `data/manual_foreign.json`
- `data/routing_settings.json`

The actual export input is:

- `shadowrocket/ru-direct.list`
- `shadowrocket/ru-blocked-core.list`
- `shadowrocket/foreign-services.list`

## Mapping

### Split

- local/private domains and CIDRs -> `direct`
- `ru-direct.list` -> `direct.domains`
- `ru-blocked-core.list` + `foreign-services.list` -> `proxy.domains`
- `block` stays empty

### Full

- local/private domains and CIDRs -> `direct`
- everything else is handled by the proxy-default fallback

## Format

The JSON layer is normalized for diffs and later client-specific conversion.

Core fields:

- `name`
- `description`
- `platform`
- `globalProxy`
- `routeOrder`
- `direct`
- `proxy`
- `block`

Additional metadata is allowed when useful for parity checks, such as `bucket_domains`.

## Parity

Regression checks must confirm that Happ stays semantically aligned with:

- Shadowrocket
- Streisand
- Hiddify

on the shared domain regression suite.
