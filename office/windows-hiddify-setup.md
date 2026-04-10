# Windows Hiddify Setup

Use this as the primary office setup for employees who need Telegram and WhatsApp desktop.

## What the employee needs

- Hiddify installed on Windows
- their own VPN node or subscription from the admin
- the shared routing profile from this repository:
  - `hiddify/routing-profile-split.json`

## Recommended office flow

1. Install Hiddify on Windows.
2. Import the employee's VPN node or subscription into Hiddify.
3. Import the shared routing profile:
   - `hiddify/routing-profile-split.json`
4. In Hiddify, keep the employee's own node selected as the active proxy.
5. Enable the routing profile.
6. Test:
   - `https://ifconfig.me/ip`
   - `https://yandex.ru`
   - `https://github.com`
   - `https://chatgpt.com`
   - `https://youtube.com`
   - Telegram Desktop
   - WhatsApp Desktop

## Why this is now preferred

- Telegram and WhatsApp desktop do not reliably follow PAC on Windows.
- Hiddify applies routing at the client level, so desktop apps behave more consistently than browser-only PAC routing.
- The routing logic still comes from the same repository core.

## Success criteria

- Browser traffic follows the same expected split-routing behavior.
- Telegram Desktop connects and sends messages.
- WhatsApp Desktop connects and syncs.
- Disabling Hiddify returns the machine to direct office internet.

## Rollback

1. Disconnect in Hiddify.
2. Disable or remove the routing profile if needed.
3. Keep Windows proxy settings off unless PAC is being used as a temporary browser fallback.
