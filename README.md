# ios-routing

Ready-to-use Shadowrocket routing presets and rule lists for split tunneling on iOS.

## Structure

- `shadowrocket/Universal-Routing.conf` - universal routing-only config without embedded servers
- `shadowrocket/Vaso-All-VPN-v2.conf` - universal full-tunnel profile without embedded servers
- `shadowrocket/ru-blocked-core.list` - domains that should always go through VPN
- `shadowrocket/ru-direct.list` - Russian domains that should stay direct
- `shadowrocket/foreign-services.list` - foreign services that are more stable through VPN
- `streisand/*.json` - generated Streisand exports built from the same finalized routing lists
- `streisand/*.streisand-uri.txt` - import-ready `streisand://...` links generated from the JSON profiles
- `streisand/routing-profile-split-qr.*` - compact split-profile artifacts optimized for QR and fragile import flows
- `hiddify/*.json` - generated Hiddify exports built from the same finalized routing lists
- `happ/*.json` - generated Happ routing exports built from the same finalized routing lists
- `happ/README.md` - short guide for mapping the exported Happ JSON into the client UI
- `docs/routing-update-spec.md` - technical spec for automated list updates
- `docs/streisand-routing-spec.md` - technical spec for exporting the same routing policy to Streisand JSON
- `docs/streisand-profile-notes.md` - decoded notes about real-world Streisand import profiles and what we adopted
- `docs/hiddify-routing-spec.md` - technical spec for exporting the same routing policy to Hiddify JSON
- `docs/hiddify-profile-notes.md` - notes on Hiddify as a thin export layer and what semantics are carried over
- `docs/happ-routing-spec.md` - technical spec for exporting the same routing policy to Happ JSON
- `docs/happ-profile-notes.md` - notes on Happ as a thin export layer and how to map it into the client UI
- `docs/routing-dev-heuristics.md` - short maintainer notes for manual core, source tuning, and regression checks
- `docs/ROADMAP.md` - short backlog for real-device validation and next routing improvements
- `WORKFLOW.md` - practical day-to-day workflow for updating lists and publishing changes
- `data/*.json` - manual core domains, overrides, headers, limits, and source definitions for the updater
- `data/regression_domains.json` - fixed regression domain set for route expectation checks
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

## User Setup

### Shadowrocket

1. Import your own node from x-ui, URI, or QR.
2. Import either `shadowrocket/Universal-Routing.conf` or `shadowrocket/Vaso-All-VPN-v2.conf`.
3. Make the chosen config active.
4. Test a few domains from the regression set before daily use.

### Streisand

1. Start with the full-tunnel profile first, not split.
2. Import the generated Streisand JSON or the full-tunnel `streisand://` artifact.
3. Confirm that the client imports cleanly and actually routes traffic.
4. Treat split-routing as experimental until the import and routing issues are fully verified.

### Hiddify

1. Import `hiddify/routing-profile-split.json` or `hiddify/routing-profile-full.json` according to your use case.
2. Keep using your own proxy/node configuration separately from the routing profile.
3. Verify a few direct and proxy domains after import.
4. If client-specific quirks appear, treat the JSON as the normalized reference and document the client behavior separately.

### Happ

1. Open `happ/routing-profile-split.json` or `happ/routing-profile-full.json`.
2. Copy the exported `direct` and `proxy` sections into the corresponding Happ UI fields.
3. Keep using the Happ profile only as a routing layer, not as a separate source of truth.
4. Verify a few direct and proxy domains after applying the rules.

## Notes

- `Universal-Routing.conf` is the recommended file for family, clients, and anyone who uses their own nodes.
- `Vaso-All-VPN-v2.conf` is the simpler option when you want all non-local traffic to go through VPN.
- Streisand routing is currently experimental and must be tested manually before real use. There is an open suspicion that import and/or routing behavior may still be broken on the client side.
- Hiddify artifacts are generated from the finalized Shadowrocket lists and are not a separate source of truth.
- Happ artifacts are generated from the finalized Shadowrocket lists and are also not a separate source of truth.
- Personal configs with embedded credentials are intentionally not stored in the shared repository.
- The rule lists are shared between both configs and can be extended over time.
- `FINAL,PROXY` is enabled, so all non-local traffic that does not match the direct rules will go through VPN.
- `GEOIP,RU,DIRECT` keeps Russian IP traffic direct as a fallback.
- Automated refresh logic for the three `.list` files is specified in `docs/routing-update-spec.md`.

## Maintenance

- Show available shortcuts: `make help`
- Run repository smoke checks: `make smoke`
- Run the fixed regression domain suite: `make regression`
- Write Streisand JSON and URI exports: `make streisand`
- Write only Streisand import URIs: `make streisand-uri`
- Write compact Streisand split QR artifacts: `make streisand-qr`
- Write Hiddify JSON exports: `make hiddify`
- Check Hiddify export sync without writing: `make hiddify-check`
- Write Happ routing exports: `make happ`
- Check Happ export sync without writing: `make happ-check`
- Treat Streisand exports as test artifacts until real client validation confirms that routing works as expected
- Preview list regeneration without changing files: `make offline`
- Fetch external sources and preview a diff: `make update`
- Write updated lists to disk: `make write`
- Emit a machine-readable report to stdout: `make report-json`
- Write a Markdown report to a file: `make report-md`
- Run repository smoke checks: `python3 scripts/smoke_check.py`
- Run the fixed regression domain suite: `python3 scripts/check_regression_domains.py`
- Write Streisand JSON exports: `python3 scripts/export_streisand_rules.py --write`
- Write Streisand import URIs: `python3 scripts/export_streisand_uri.py --write`
- Write Hiddify JSON exports: `python3 scripts/export_hiddify_rules.py --write`
- Check Hiddify export sync: `python3 scripts/export_hiddify_rules.py --offline`
- Write Happ routing exports: `python3 scripts/export_happ_routing.py --write`
- Check Happ export sync: `python3 scripts/export_happ_routing.py --offline`
- Check Streisand import URI sync: `python3 scripts/export_streisand_uri.py --offline`
- Check Streisand export sync: `python3 scripts/export_streisand_rules.py --offline`
- Preview list regeneration without changing files: `python3 scripts/update_routing_lists.py --offline`
- Fetch external sources and preview a diff: `python3 scripts/update_routing_lists.py`
- Write updated lists to disk: `python3 scripts/update_routing_lists.py --write`
- Emit a machine-readable report to stdout: `python3 scripts/update_routing_lists.py --offline --report-json -`
- Write a Markdown report to a file: `python3 scripts/update_routing_lists.py --report-md reports/routing-update.md`
- Edit `data/manual_*.json` to change the manual core domains and section order
- Edit `data/routing_settings.json` to change overrides, limits, TLD policy, source URLs, per-source priority, notes, and exclude rules
- Edit `data/regression_domains.json` when you want to extend the stable smoke-domain set
