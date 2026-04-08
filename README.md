# ios-routing

Ready-to-use Shadowrocket routing presets and rule lists for split tunneling on iOS.

## Structure

- `shadowrocket/Universal-Routing.conf` - universal routing-only config without embedded servers
- `shadowrocket/Vaso-All-VPN-v2.conf` - universal full-tunnel profile without embedded servers
- `shadowrocket/ru-blocked-core.list` - domains that should always go through VPN
- `shadowrocket/ru-direct.list` - Russian domains that should stay direct
- `shadowrocket/foreign-services.list` - foreign services that are more stable through VPN
- `docs/routing-update-spec.md` - technical spec for automated list updates
- `WORKFLOW.md` - practical day-to-day workflow for updating lists and publishing changes
- `data/*.json` - manual core domains, overrides, headers, limits, and source definitions for the updater
- `.github/workflows/*.yml` - CI smoke checks and scheduled routing reports
- `Makefile` - short aliases for the most common local maintenance commands

## Usage

### Universal routing

1. Import your own server into Shadowrocket from x-ui, URI, or QR.
2. Import `shadowrocket/Universal-Routing.conf`.
3. Make `Universal-Routing.conf` the active config.
4. Leave your preferred imported server selected as the active proxy.

### Universal full tunnel

1. Import your own server into Shadowrocket from x-ui, URI, or QR.
2. Import `shadowrocket/Vaso-All-VPN-v2.conf`.
3. Make `Vaso-All-VPN-v2.conf` the active config.
4. Leave your preferred imported server selected as the active proxy.

## Notes

- `Universal-Routing.conf` is the recommended file for family, clients, and anyone who uses their own nodes.
- `Vaso-All-VPN-v2.conf` is the simpler option when you want all non-local traffic to go through VPN.
- Personal configs with embedded credentials are intentionally not stored in the shared repository.
- The rule lists are shared between both configs and can be extended over time.
- `FINAL,PROXY` is enabled, so all non-local traffic that does not match the direct rules will go through VPN.
- `GEOIP,RU,DIRECT` keeps Russian IP traffic direct as a fallback.
- Automated refresh logic for the three `.list` files is specified in `docs/routing-update-spec.md`.

## Maintenance

- Show available shortcuts: `make help`
- Run repository smoke checks: `make smoke`
- Preview list regeneration without changing files: `make offline`
- Fetch external sources and preview a diff: `make update`
- Write updated lists to disk: `make write`
- Emit a machine-readable report to stdout: `make report-json`
- Write a Markdown report to a file: `make report-md`
- Run repository smoke checks: `python3 scripts/smoke_check.py`
- Preview list regeneration without changing files: `python3 scripts/update_routing_lists.py --offline`
- Fetch external sources and preview a diff: `python3 scripts/update_routing_lists.py`
- Write updated lists to disk: `python3 scripts/update_routing_lists.py --write`
- Emit a machine-readable report to stdout: `python3 scripts/update_routing_lists.py --offline --report-json -`
- Write a Markdown report to a file: `python3 scripts/update_routing_lists.py --report-md reports/routing-update.md`
- Edit `data/manual_*.json` to change the manual core domains and section order
- Edit `data/routing_settings.json` to change overrides, limits, TLD policy, source URLs, per-source priority, notes, and exclude rules
