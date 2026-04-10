# ios-routing

Ready-to-use Shadowrocket routing presets and rule lists for split tunneling on iOS.

## Structure

- `shadowrocket/Universal-Routing.conf` - universal routing-only config without embedded servers
- `shadowrocket/Vaso-All-VPN-v2.conf` - universal full-tunnel profile without embedded servers
- `shadowrocket/ru-blocked-core.list` - domains that should always go through VPN
- `shadowrocket/ru-direct.list` - Russian domains that should stay direct
- `shadowrocket/foreign-services.list` - foreign services that are more stable through VPN
- `streisand/*.json` - generated Streisand exports built from the same finalized routing lists
- `streisand/*.streisand-uri.txt` - safe import-ready `streisand://...` links generated from the supported Streisand profiles
- `streisand/routing-profile-split-qr.*` - compact split-profile artifacts optimized for QR and fragile import flows
- `hiddify/*.json` - generated Hiddify exports built from the same finalized routing lists
- `happ/*.json` - generated Happ routing exports built from the same finalized routing lists
- `happ/README.md` - short guide for mapping the exported Happ JSON into the client UI
- `clash/*.yaml` - generated Clash for Windows / mihomo routing exports built from the same finalized routing lists
- `office/` - Synology office gateway templates, PAC example, and sing-box deployment skeleton
- `office/sing-box/generated/*.json` - generated Synology sing-box configs built from the same finalized routing lists
- `office/windows-pilot-setup.md` - short first-machine checklist for testing the Synology office gateway on Windows
- `office/windows-hiddify-setup.md` - primary Windows setup when employees need Telegram and WhatsApp desktop
- `office/hiddify-office-rollout.md` - short office rollout plan for Hiddify-first deployment
- `docs/routing-update-spec.md` - technical spec for automated list updates
- `docs/streisand-routing-spec.md` - technical spec for exporting the same routing policy to Streisand JSON
- `docs/streisand-profile-notes.md` - decoded notes about real-world Streisand import profiles and what we adopted
- `docs/streisand-field-test-matrix.md` - fixed field checklist for validating Streisand full vs split behavior on real clients
- `docs/streisand-10min-checklist.md` - short human-friendly manual test flow for Streisand on a real device
- `docs/hiddify-routing-spec.md` - technical spec for exporting the same routing policy to Hiddify JSON
- `docs/hiddify-profile-notes.md` - notes on Hiddify as a thin export layer and what semantics are carried over
- `docs/happ-routing-spec.md` - technical spec for exporting the same routing policy to Happ JSON
- `docs/happ-profile-notes.md` - notes on Happ as a thin export layer and how to map it into the client UI
- `docs/clash-routing-spec.md` - technical spec for exporting the same routing policy to Clash YAML
- `docs/office-synology-vpn-architecture.md` - recommended office architecture for running Synology as a split-routing VPN gateway
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
5. Keep Tailscale and tailnet access direct: `100.64.0.0/10` and `*.ts.net` must not go through the proxy.

### Streisand

1. Start with the full-tunnel profile first, not split.
2. Import the generated full-tunnel `streisand://` artifact.
3. Confirm that the client imports cleanly and actually routes traffic.
4. Treat `routing-profile-split.json` and `routing-profile-split-qr.*` as diagnostic artifacts until repeated field tests prove split-routing is stable on real clients.

### Hiddify

1. Import `hiddify/routing-profile-split.json` or `hiddify/routing-profile-full.json` according to your use case.
2. Keep using your own proxy/node configuration separately from the routing profile.
3. Verify a few direct and proxy domains after import.
4. If client-specific quirks appear, treat the JSON as the normalized reference and document the client behavior separately.

For office machines that need Telegram and WhatsApp desktop, prefer Hiddify over PAC as the main per-machine setup.

### Happ

1. Open `happ/routing-profile-split.json`, `happ/routing-profile-split-direct-default.json`, or `happ/routing-profile-full.json`.
2. Copy the exported `direct` and `proxy` sections into the corresponding Happ UI fields.
3. Keep using the Happ profile only as a routing layer, not as a separate source of truth.
4. Verify a few direct and proxy domains after applying the rules.

### Clash for Windows

1. Import or merge `clash/routing-profile-full.yaml`, `clash/routing-profile-split.yaml`, or `clash/routing-profile-split-direct-default.yaml` into your Clash for Windows / mihomo setup.
2. Keep using your own nodes or subscription separately; the Clash YAML here is only the routing layer.
3. Start with `routing-profile-full.yaml` if you want the least surprising behavior.
4. Verify a few direct and proxy domains after import.

### Office Synology Gateway

1. Generate the office sing-box configs with `python3 scripts/export_office_singbox.py --write`.
2. Copy `office/` to Synology, for example under `/volume1/docker/office-vpn`.
3. Use `office/sing-box/generated/config.split.generated.json` as the preferred baseline, then replace placeholders locally.
4. Serve `office/proxy.pac` from Synology and use `http://10.77.221.15:8088/proxy.pac` for the first Windows pilot machine.
5. Start with 1-2 pilot machines through explicit proxy or PAC before wider office rollout.

If all employees need Telegram and WhatsApp desktop, prefer the Hiddify path for each machine and keep the Synology PAC/proxy stack as a browser fallback and rollback tool.

## Notes

- `Universal-Routing.conf` is the recommended file for family, clients, and anyone who uses their own nodes.
- Shadowrocket must keep Tailscale addresses direct. If `https://100.x.y.z:5001/` or other tailnet endpoints fail while Tailscale is connected, the usual cause is proxying `100.64.0.0/10` instead of bypassing it.
- `Vaso-All-VPN-v2.conf` is the simpler option when you want all non-local traffic to go through VPN.
- Streisand routing is currently experimental and must be tested manually before real use. One earlier real-device run showed `ip.ru -> NL` on `routing-profile-split-qr`, but newer tests on April 9, 2026 showed `split-qr` and `full` working, so the current status is inconsistent rather than conclusively broken.
- Only the Streisand `full` import artifact should be treated as the practical path for now; both split variants remain diagnostic/reference artifacts.
- The default Streisand export commands generate only the stable full-profile path. Split artifacts require an explicit experimental opt-in.
- Hiddify artifacts are generated from the finalized Shadowrocket lists and are not a separate source of truth.
- Happ artifacts are generated from the finalized Shadowrocket lists and are also not a separate source of truth.
- Clash artifacts are generated from the finalized Shadowrocket lists and are also not a separate source of truth.
- The office Synology stack should be treated as another deployment target that consumes the same routing policy, not as a separate routing policy source.
- For office employees with native desktop messengers, Hiddify is now the preferred rollout path; Synology PAC remains useful as browser fallback and rollback.
- `happ/routing-profile-split.json` is the parity-safe variant; `happ/routing-profile-split-direct-default.json` is the Happ-style direct-default variant.
- `clash/routing-profile-full.yaml` is the stable Clash profile; both split Clash profiles should be treated as experimental until real Windows client checks confirm parity.
- The office Synology layer should consume generated sing-box configs from this repo, not its own hand-maintained routing policy.
- Personal configs with embedded credentials are intentionally not stored in the shared repository.
- The rule lists are shared between both configs and can be extended over time.
- `FINAL,PROXY` is enabled, so all non-local traffic that does not match the direct rules will go through VPN.
- `GEOIP,RU,DIRECT` keeps Russian IP traffic direct as a fallback.
- Automated refresh logic for the three `.list` files is specified in `docs/routing-update-spec.md`.

## Maintenance

- Show available shortcuts: `make help`
- Run repository smoke checks: `make smoke`
- Run the fixed regression domain suite: `make regression`
- Write stable Streisand JSON and URI exports: `make streisand`
- Write only the stable Streisand import URI export: `make streisand-uri`
- Write experimental Streisand split artifacts too: `make streisand-experimental`
- Write compact diagnostic Streisand split artifacts: `make streisand-qr`
- Write Hiddify JSON exports: `make hiddify`
- Check Hiddify export sync without writing: `make hiddify-check`
- Write Happ routing exports: `make happ`
- Check Happ export sync without writing: `make happ-check`
- Write Clash YAML exports: `make clash`
- Check Clash export sync without writing: `make clash-check`
- Write office Synology sing-box exports: `make office`
- Check office Synology sing-box export sync without writing: `make office-check`
- Treat Streisand exports as test artifacts until real client validation confirms that routing works as expected
- Preview list regeneration without changing files: `make offline`
- Fetch external sources and preview a diff: `make update`
- Write updated lists to disk: `make write`
- Emit a machine-readable report to stdout: `make report-json`
- Write a Markdown report to a file: `make report-md`
- Run repository smoke checks: `python3 scripts/smoke_check.py`
- Run the fixed regression domain suite: `python3 scripts/check_regression_domains.py`
- Write Streisand JSON exports: `python3 scripts/export_streisand_rules.py --write`
- Write experimental Streisand split JSON too: `python3 scripts/export_streisand_rules.py --write --experimental-split`
- Write the stable Streisand import URI: `python3 scripts/export_streisand_uri.py --write`
- Write experimental Streisand split URIs too: `python3 scripts/export_streisand_uri.py --write --experimental-split`
- Write Hiddify JSON exports: `python3 scripts/export_hiddify_rules.py --write`
- Check Hiddify export sync: `python3 scripts/export_hiddify_rules.py --offline`
- Write Happ routing exports: `python3 scripts/export_happ_routing.py --write`
- Check Happ export sync: `python3 scripts/export_happ_routing.py --offline`
- Write Clash YAML exports: `python3 scripts/export_clash_rules.py --write --profile full --profile split --profile split-direct-default`
- Check Clash export sync: `python3 scripts/export_clash_rules.py --offline --profile full --profile split --profile split-direct-default`
- Write office Synology sing-box exports: `python3 scripts/export_office_singbox.py --write`
- Check office Synology sing-box export sync: `python3 scripts/export_office_singbox.py --offline`
- Render a Synology-local office config from a real VLESS URI: `python3 scripts/render_office_config_from_vless_uri.py --profile split --uri 'vless://...' --output /tmp/office-config.json`
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
