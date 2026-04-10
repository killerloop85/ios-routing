# Office Segment via Synology Gateway

## Goal

Move from per-machine office access to a dedicated office network segment that exits to the internet through the Synology VPN gateway.

This is the long-term office architecture when:

- all employees need Telegram and WhatsApp desktop;
- browser-only PAC routing is no longer enough;
- the office wants one managed network path instead of per-machine client setup.

## Recommended topology

```text
[Office core LAN]
        |
        |  unchanged default office network
        |
[Router / Firewall / Managed AP]
        |
        |  dedicated VLAN / SSID / subnet
        v
[Office VPN Segment 10.77.230.0/24]
        |
        |  default gateway for this segment
        v
[Synology NAS]
  - split-routing VPN gateway
  - VLESS/Reality now
  - Hysteria2 later
        |
        v
[VPS / x-ui upstream]
        |
        v
     Internet
```

## Recommended network design

Use a separate office segment instead of changing the whole office LAN at once.

Suggested pilot layout:

- VPN segment subnet: `10.77.230.0/24`
- Synology gateway IP in that segment: `10.77.230.2`
- Router / VLAN interface: `10.77.230.1`
- Dedicated SSID example: `Office-VPN`

## Why this is better than PAC

- Telegram Desktop and WhatsApp Desktop no longer depend on app-specific proxy support.
- Routing becomes consistent for browsers and native desktop apps.
- User onboarding becomes simpler once the segment exists.
- The current repository routing policy can still be reused.

## Why this is better than immediate whole-office cutover

- Lower blast radius.
- Easy rollback: move devices back to the regular office SSID or VLAN.
- Allows a clean pilot with selected users first.

## Synology role

Synology remains the VPN egress node, but now also becomes the routed gateway for the dedicated segment.

It must provide:

- upstream tunnel via sing-box;
- split-routing policy from this repository;
- IP forwarding;
- source NAT / masquerade for the VPN segment;
- direct handling of local/private and office resources.

## Routing policy for the segment

Keep the same routing semantics:

- `local/private` -> `DIRECT`
- office LAN and internal services -> `DIRECT`
- `ru-direct` -> `DIRECT`
- `ru-blocked-core` -> `PROXY`
- `foreign-services` -> `PROXY`
- `17.0.0.0/8` -> `DIRECT` while the Apple/VDSina caveat exists
- final fallback -> `PROXY`

## Router / AP requirements

The router or managed AP must be able to do at least one of these cleanly:

1. Create a dedicated VLAN / SSID and point that segment at Synology as its gateway.
2. Or create a dedicated VLAN / SSID and use policy-based routing so that this subnet exits through Synology.

Minimum practical requirements:

- dedicated SSID or VLAN
- separate DHCP scope or DHCP options for that segment
- ability to keep the main office LAN unchanged

## Synology requirements

The Synology side must support:

- Docker / Container Manager
- stable sing-box runtime
- root-capable shell or equivalent admin control for gateway/NAT changes
- either:
  - a secondary IP / VLAN presence for the VPN segment, or
  - a router design where the router policy-forwards the segment through Synology

## Rollout stages

### Stage 1: keep current working paths

- Synology explicit proxy remains available
- PAC remains available for browser fallback
- Hiddify remains valid for early employee access

### Stage 2: pilot VLAN / SSID

- create one dedicated office VPN segment
- move 2-3 pilot users onto it
- verify:
  - Telegram Desktop
  - WhatsApp Desktop
  - browser traffic
  - internal office services

### Stage 3: wider rollout

- move the rest of the intended users
- keep the main office LAN unchanged until the segment is stable

## Rollback

Fast rollback should be network-only:

- move devices back to the normal office SSID / VLAN
- or disable the VPN segment on the router/AP
- leave the main office LAN untouched

## Decision boundary

Choose this architecture when:

- Telegram and WhatsApp desktop are mandatory for most employees;
- you want consistent behavior across apps;
- you can change router/AP configuration.

Stay with Hiddify-first when:

- router/AP access is limited;
- you need fast user rollout before touching office network topology;
- you want per-user subscriptions to remain the main operating model.
