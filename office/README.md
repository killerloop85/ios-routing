# Office VPN on Synology

This directory contains the practical deployment skeleton for running an office VPN gateway on Synology Container Manager.

## Design Summary

- Synology acts as a LAN-only split-routing gateway.
- Office clients use the Synology node as an explicit proxy first.
- Upstream tunnel is `VLESS/Reality` today.
- `Hysteria2` can be added later without redesigning the office side.
- The routing policy follows the shared repository core:
  - `ru-direct` -> direct
  - `ru-blocked-core` -> proxy
  - `foreign-services` -> proxy

## Files

- `docker-compose.synology.yml` - Synology Container Manager compose skeleton
- `env.example` - example environment variables for local-only secrets
- `proxy.pac.example.js` - browser/system PAC example for office rollout
- `sing-box/config.split.template.jsonc` - split-routing template
- `sing-box/config.full.template.jsonc` - full-tunnel template
- `sing-box/generated/config.split.generated.json` - generated split config built from the current routing core
- `sing-box/generated/config.full.generated.json` - generated full config built from the current routing core

## Generated baseline

Use the generated configs as the office source of routing truth:

```bash
python3 scripts/export_office_singbox.py --write
```

They are exported from the finalized `shadowrocket/*.list` files, so office routing stays aligned with the same repository core as the other clients.

## Recommended Rollout

1. Copy this directory to Synology, for example:
   - `/volume1/docker/office-vpn`
2. Copy `env.example` to `.env` and fill real secrets locally on Synology.
3. Run `python3 scripts/export_office_singbox.py --write`.
4. Choose `sing-box/generated/config.split.generated.json` first.
5. Copy it to the Synology-local `config/config.json`.
6. Replace proxy auth and upstream placeholders locally on Synology.
7. Start the stack in Container Manager.
8. Point 1-2 office pilot machines to the mixed proxy listener.
9. Verify direct/proxy behavior before wider rollout.

## Do not commit

- real upstream subscription URLs
- UUIDs / passwords / auth secrets
- Synology-local `.env`
- final `config.json` with real credentials

## Remote Users

If remote access to office LAN is needed later:

- keep it as a separate Synology VPN access layer;
- do not mix that with the primary office LAN egress design.

For office LAN machines already inside the office, explicit proxy is the preferred first deployment model.
