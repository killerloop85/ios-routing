# Segment Gateway Rollout

Use this when the office is ready to move from per-machine clients to a dedicated VPN segment through Synology.

## Recommended pilot scope

Start with one separate office SSID or VLAN only.

Do not replace the main office LAN immediately.

## Suggested pilot segment

- Segment name: `Office-VPN`
- Subnet: `10.77.230.0/24`
- Router interface in that segment: `10.77.230.1`
- Synology gateway IP in that segment: `10.77.230.2`

## Router-side checklist

1. Create a new VLAN or dedicated SSID.
2. Assign a separate DHCP scope to it.
3. Keep the regular office LAN unchanged.
4. Route this segment through Synology:
   - either by setting Synology as the segment gateway;
   - or by policy-routing that segment through Synology.

## Synology-side checklist

1. Keep the current office VPN stack as the routing core baseline.
2. Add the VPN-segment IP or VLAN presence on Synology.
3. Enable IP forwarding.
4. Add source NAT / masquerade for the segment.
5. Keep local/private and office-internal destinations direct.
6. Keep upstream tunnel and split-routing policy as already defined in this repository.

## Pilot validation

For 2-3 pilot users on the segment, verify:

- `https://ifconfig.me/ip`
- `https://yandex.ru`
- `https://github.com`
- `https://chatgpt.com`
- `https://youtube.com`
- Telegram Desktop
- WhatsApp Desktop
- Bitrix24

## Success criteria

- users on the segment do not need PAC
- users on the segment do not need Hiddify
- Telegram and WhatsApp desktop work
- internal office services remain reachable
- users outside the segment are unaffected

## Rollback

1. Move users back to the normal office SSID or VLAN.
2. Disable the pilot segment route on the router/AP.
3. Leave the Synology stack running for diagnostics or future retries.
