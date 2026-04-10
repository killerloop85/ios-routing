# Office Hiddify Rollout

This is the recommended office path when all employees use Telegram and WhatsApp desktop.

## Decision

Use per-machine Hiddify as the primary employee access model.

Keep the Synology PAC/proxy setup only as:

- a browser-only fallback;
- a temporary rollback path;
- a diagnostic tool for office web traffic.

## Why this is the preferred office model now

- PAC solved browser traffic, but not Telegram and WhatsApp desktop.
- Hiddify gives per-machine routing that also covers native desktop apps.
- The routing policy still stays centralized in this repository.
- This avoids a rushed move to VLAN or router-level routing before it is really needed.

## Recommended rollout order

1. Pick 2-3 pilot employees who actively use Telegram and WhatsApp desktop.
2. Install Hiddify on their Windows machines.
3. Import each employee's own VPN node or subscription.
4. Import the shared `hiddify/routing-profile-split.json`.
5. Verify:
   - web traffic;
   - Telegram Desktop;
   - WhatsApp Desktop;
   - rollback by disconnecting Hiddify.
6. If stable, expand to the rest of the office.

## What stays centralized

- shared routing policy:
  - `ru-direct`
  - `ru-blocked-core`
  - `foreign-services`
- regression and export checks in this repository

## What stays per employee

- node / subscription
- active Hiddify app session on the machine
- local OS-level app behavior

## When to revisit Synology gateway as the main office path

Revisit the network-level Synology or VLAN approach only if:

- you need zero-touch employee onboarding;
- you want all traffic types handled centrally without local clients;
- you are ready to change office router or VLAN policy.
