# DS920+ Two-Port Rollout

Use this when the office is ready to use the second Ethernet port of the Synology DS920+ for a dedicated VPN segment.

## Target layout

- `LAN1` on Synology:
  - existing office LAN
  - keep current Synology LAN IP `10.77.221.15`
- `LAN2` on Synology:
  - dedicated office VPN segment
  - set Synology IP to `10.77.230.1/24`

## What to connect physically

1. Keep `LAN1` as it is today.
2. Connect `LAN2` to one of:
   - a small unmanaged switch for pilot PCs;
   - or a dedicated Wi-Fi access point for `Office-VPN`.

## Synology configuration checklist

1. Assign static IP `10.77.230.1/24` to `LAN2`.
2. Enable DHCP Server for the `10.77.230.0/24` network on `LAN2`.
3. Suggested pool:
   - start: `10.77.230.50`
   - end: `10.77.230.199`
4. Gateway for clients:
   - `10.77.230.1`
5. DNS for clients:
   - `10.77.230.1`
6. Keep the office `sing-box` stack as the routing baseline.
7. Enable forwarding/NAT for the new segment.
8. Keep office LAN destinations direct.

## Pilot validation

For the first 1-2 machines connected to `LAN2`:

- confirm they get `10.77.230.x`
- confirm gateway is `10.77.230.1`
- confirm DNS is `10.77.230.1`
- check:
  - `https://ifconfig.me/ip`
  - `https://yandex.ru`
  - `https://github.com`
  - `https://chatgpt.com`
  - `https://youtube.com`
  - Telegram Desktop
  - WhatsApp Desktop
  - access to office-local resources

## Success criteria

- No PAC on pilot machines
- No Hiddify on pilot machines
- Telegram and WhatsApp desktop work
- Web traffic follows the office routing policy
- Office-local resources still open

## Rollback

1. Unplug pilot machines from the `LAN2` switch/AP.
2. Move them back to the normal office network.
3. If needed, disable DHCP on `LAN2`.
