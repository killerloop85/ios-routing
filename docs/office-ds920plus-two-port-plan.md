# DS920+ Two-Port Office Segment Plan

## Goal

Use the second Ethernet port of Synology DS920+ to build a dedicated office VPN segment without changing the main office LAN first.

This is the cleanest near-term production path when:

- the NAS already has a free second LAN port;
- all employees need Telegram and WhatsApp desktop;
- PAC and per-machine clients are no longer the desired steady-state.

## Recommended physical layout

```text
[Main office LAN / internet]
        |
        |  existing office network
        v
[Synology DS920+ LAN1]
        |
        |  internal routing + sing-box + VPN upstream
        |
[Synology DS920+ LAN2]
        |
        |  dedicated office VPN segment
        v
[Small switch or dedicated Wi-Fi AP]
        |
        +---- office pilot machines
        +---- later: all intended users
```

## Recommended addressing

Keep the current office LAN unchanged on `LAN1`.

Use `LAN2` as the new office VPN segment:

- `LAN1`:
  - existing office LAN
  - current Synology address remains `10.77.221.15`
- `LAN2`:
  - dedicated VPN segment subnet: `10.77.230.0/24`
  - Synology `LAN2` IP: `10.77.230.1`
  - suggested DHCP range: `10.77.230.50-10.77.230.199`
  - DNS for clients: `10.77.230.1`

## Why this is the best immediate office option

- No need to redesign the main office router first.
- No dependency on PAC support in desktop apps.
- No per-machine Hiddify requirement for steady-state office use.
- Rollback is physical and simple:
  - unplug users from the VPN segment switch/AP;
  - move them back to the regular office LAN.

## Synology role on each interface

### LAN1

- stays connected to the current office LAN and internet path;
- keeps access to office resources and NAS administration;
- carries the existing upstream path for the `sing-box` office stack.

### LAN2

- becomes the gateway for the dedicated office VPN segment;
- serves DHCP for that segment;
- is the default route for connected office devices.

## Required Synology behavior

On the DS920+ we need:

1. Static IP on `LAN2`: `10.77.230.1/24`
2. DHCP server enabled for `10.77.230.0/24`
3. IP forwarding between `LAN2` and the office/VPN egress path
4. NAT / masquerade for the VPN segment where needed
5. Office routing policy from this repository:
   - `local/private` -> `DIRECT`
   - office LAN `10.77.221.0/24` -> `DIRECT`
   - `ru-direct` -> `DIRECT`
   - `ru-blocked-core` -> `PROXY`
   - `foreign-services` -> `PROXY`
   - final fallback -> `PROXY`

## Office resources

The VPN segment should still be able to reach office-local resources on the main LAN where needed, for example:

- NAS services on `10.77.221.15`
- printers
- Bitrix24-related local integrations if any
- other office-local systems

That means office LAN destinations should be routed direct, not sent into the upstream VPN tunnel.

## Pilot rollout

Start small:

1. Connect a small unmanaged switch or separate Wi-Fi AP to `LAN2`.
2. Put 1-2 office machines onto that segment only.
3. Confirm they receive:
   - IP from `10.77.230.0/24`
   - gateway `10.77.230.1`
   - DNS `10.77.230.1`
4. Verify:
   - `ifconfig.me/ip`
   - `yandex.ru`
   - `github.com`
   - `chatgpt.com`
   - `youtube.com`
   - Telegram Desktop
   - WhatsApp Desktop
   - office-local resources

## Rollback

Rollback should stay simple:

1. Move pilot machines back to the main office LAN or Wi-Fi.
2. Disable DHCP on `LAN2` if needed.
3. Leave the `sing-box` office stack running for diagnostics.

## Decision

For your current hardware, this is the preferred office target:

- `DS920+ LAN1` -> existing office LAN
- `DS920+ LAN2` -> dedicated office VPN segment

This is better than PAC for employees, and simpler than redesigning the whole office router first.
