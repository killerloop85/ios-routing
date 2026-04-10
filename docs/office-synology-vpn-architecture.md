# Office VPN via Synology

## Goal

Use the office Synology NAS as a local VPN gateway and routing node, while keeping the existing repository as the single source of truth for split-routing policy.

The office design should:

- keep office LAN and local/private traffic direct;
- send blocked and foreign services through the upstream tunnel;
- avoid per-device full-tunnel complexity where possible;
- stay compatible with the existing routing core in this repository.

## Recommended Architecture

### Primary design

```text
[Office Windows/macOS clients]
          |
          |  explicit proxy (PAC / GPO / OS proxy)
          v
[Synology NAS 10.77.221.15]
  - Container Manager / Docker
  - sing-box client/gateway
  - LAN-only mixed proxy (HTTP + SOCKS)
  - split routing using this repository's policy
          |
          |  VLESS/Reality now
          |  Hysteria2 later as optional higher-priority outbound
          v
[VPS / x-ui upstream]
          |
          v
       Internet
```

### Why this is the preferred office design

- It keeps the office rollout reversible.
- It avoids making every office workstation maintain its own VPN client state.
- It allows gradual rollout through PAC / proxy settings / GPO.
- It lets Synology become a routing node, not just a dumb full-tunnel box.
- It fits the current upstream reality: only VLESS/Reality exists now, but Hysteria2 can be added later without redesigning the office side.

## What not to make the default

### Do not make local office machines use L2TP to Synology as the main office path

L2TP/IPsec to Synology is acceptable only as a separate remote-access scenario.

It is not the ideal primary architecture for office machines that are already inside the office LAN because it adds:

- extra per-device setup and maintenance;
- more MTU / IPsec / Windows-specific fragility;
- harder rollback;
- worse split-routing control than a local proxy or policy-gateway model.

Recommended interpretation:

- `L2TP/IPsec on Synology` -> only for remote users who need to reach office resources;
- `LAN office clients -> Synology mixed proxy` -> primary office internet routing model.

## Routing Policy

The Synology gateway should follow the same buckets already maintained in this repository:

- `local/private` -> `DIRECT`
- office LAN and internal services -> `DIRECT`
- `ru-direct` -> `DIRECT`
- `ru-blocked-core` -> `PROXY`
- `foreign-services` -> `PROXY`
- `17.0.0.0/8` -> `DIRECT` while the VDSina/Apple issue remains relevant
- final fallback:
  - parity-safe mode -> `PROXY`
  - optional direct-default mode only if a future office use case really needs it

This means the Synology node should behave closer to the repository's split-routing clients, not like a global VPN switch.

## Export Layer

The office deployment should consume the same finalized routing core as the other clients, not a separate hand-maintained rule set.

Recommended command:

```bash
python3 scripts/export_office_singbox.py --write
```

This generates:

- `office/sing-box/generated/config.split.generated.json`
- `office/sing-box/generated/config.full.generated.json`

Those generated configs should be treated as the authoritative office baseline. Any Synology-local edits should be limited to:

- proxy listener credentials;
- upstream server, UUID, Reality keys, and future Hysteria2 fields;
- Synology-local bind or subnet values if the office LAN changes.

## Rollout Strategy

### Phase 1: Safe pilot

- Deploy `sing-box` in Container Manager on Synology.
- Generate the office config from the current routing core first.
- Bind the proxy listener only to the office LAN IP.
- Require proxy authentication.
- Expose a single mixed proxy port for Windows/macOS browsers and system proxy.
- Start with 1-2 pilot machines.

### Phase 2: Controlled office adoption

- Add a PAC file or GPO-based proxy settings for selected machines.
- Verify business-critical paths:
  - Bitrix24
  - office services
  - Russian banking/government sites if used
  - GitHub / OpenAI / YouTube
- Keep a fast rollback path: remove proxy settings and the machine returns to direct internet.

### Phase 3: Optional network-level routing

Only if the explicit-proxy model proves too limited:

- move selected devices or a dedicated VLAN/SSID through Synology as a policy gateway;
- keep that isolated from the default office LAN until proven stable.

## Recommended Synology Layout

Use a neutral deployment path instead of project-specific application directories:

- base path: `/volume1/docker/office-vpn`

Suggested structure:

```text
/volume1/docker/office-vpn/
  docker-compose.yml
  .env
  config/
  logs/
  data/
  pac/
```

Recommended service account:

- use the existing privileged Synology admin context that actually owns Container Manager access;
- do not tie the VPN stack to `/volume1/Contracts Saas`.

## Upstream Design

### Current state

- primary upstream: `VLESS/Reality`
- current validated Synology runtime pin: `ghcr.io/sagernet/sing-box:v1.12.0`
- current compatibility flag: `ENABLE_DEPRECATED_SPECIAL_OUTBOUNDS=true`

### Future state

- add `Hysteria2` as an additional outbound
- optionally prefer it through a selector / urltest group if it proves faster and stable

### Design principle

The office side should not depend on a single protocol forever.

Synology should be built around:

- one stable routing engine (`sing-box`)
- multiple upstream outbounds
- one local office-facing proxy interface

## DNS

Recommended office gateway DNS behavior:

- internal office names and LAN resources -> local resolver / direct path
- public internet resolution -> DoH/DoT through the proxy path
- avoid plain DNS leakage where possible

If needed later:

- add `smartdns` or `dnsmasq`
- keep that separate from the first deployment unless there is a proven DNS issue

## Security Requirements

- Proxy listener must be LAN-only.
- Proxy listener must require authentication.
- Synology firewall must only allow office subnet(s) to the proxy port.
- No proxy port should be published on the public WAN.
- No secrets should live in tracked repository files.
- x-ui subscription links and outbound credentials should live in Synology-local config files or `.env`, not in committed docs.

## Operational Model

- office routing policy still lives in this repository;
- Synology deployment files are templates and runbooks;
- sensitive credentials stay outside git;
- rollback should be possible in under 5 minutes by:
  - disabling the Container Manager stack, or
  - removing proxy settings / PAC / GPO from clients

## Synology-specific note

In the current office environment, the Docker socket on Synology is owned by group `synopkgs`.

Practical implication:

- file deployment to `/volume1/docker/office-vpn` can be done with the normal admin account;
- but CLI lifecycle actions such as `docker run` or `docker compose up` may still require either:
  - DSM Container Manager UI,
  - a one-time privilege/group adjustment,
  - or a root-capable shell.

## Exit Criteria for "Good enough"

The office design can be considered ready when:

- pilot clients can reach `Bitrix24`, `Yandex`, `GitHub`, `OpenAI`, and `YouTube` with expected routing;
- office LAN resources remain direct and fast;
- Synology survives a container restart without manual intervention;
- rollback is documented and tested;
- adding Hysteria2 later does not require rebuilding the office-side topology.
