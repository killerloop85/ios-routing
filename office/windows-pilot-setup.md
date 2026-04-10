# Windows Pilot Setup

Use this for the first office test machine.

## Ready values

- Proxy host: `10.77.221.15`
- Proxy port: `1080`
- PAC URL: `http://10.77.221.15:8088/proxy.pac`
- Proxy username: `officeproxy`
- Proxy password: keep it local and rotate after the pilot

## Recommended setup

1. Open `Settings -> Network & Internet -> Proxy`.
2. Enable `Use setup script`.
3. Set `Script address` to:

   `http://10.77.221.15:8088/proxy.pac`

4. Save settings.
5. Open a browser.
6. The first request through the proxy should ask for proxy credentials.
7. Enter the office proxy username and password.
8. Test:
   - `https://ifconfig.me/ip`
   - `https://yandex.ru`
   - `https://github.com`
   - `https://chatgpt.com`
   - `https://youtube.com`

## Fallback manual setup

If PAC auto-config is not applied correctly:

1. In the same Proxy settings page, disable `Use setup script`.
2. Enable manual proxy.
3. Set address `10.77.221.15` and port `1080`.
4. Save and retest.

## Success criteria

- `ifconfig.me/ip` shows the VPN egress IP, not the office WAN IP.
- `yandex.ru` opens normally.
- `github.com`, `chatgpt.com`, and `youtube.com` open through the office gateway.
- Disabling proxy settings returns the machine to direct internet immediately.

## Rollback

1. Open `Settings -> Network & Internet -> Proxy`.
2. Disable `Use setup script`.
3. Disable manual proxy if it was enabled.
4. Close and reopen the browser.
