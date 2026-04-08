# Routing List Update Spec

## 1. Goal

Keep these three Shadowrocket-compatible list files up to date:

- `shadowrocket/ru-direct.list` - Russian and socially significant domains that should go `DIRECT`
- `shadowrocket/ru-blocked-core.list` - compact core of domains that should always go through `PROXY`
- `shadowrocket/foreign-services.list` - foreign services that are blocked in Russia or work noticeably better through `PROXY`

The goal is a minimal but practical split-routing setup for Russia without bloated lists.

## 2. Inputs And Formats

### 2.1 Local Target Files

Repository:

- `https://github.com/killerloop85/ios-routing`

Files to update:

- `shadowrocket/ru-direct.list`
- `shadowrocket/ru-blocked-core.list`
- `shadowrocket/foreign-services.list`

Allowed line formats:

```text
# comments
DOMAIN-SUFFIX,example.com
```

Only `DOMAIN-SUFFIX,` entries and `#` comments are valid output.

### 2.2 External Sources

#### Russian whitelist sources

1. `hxehex/russia-mobile-internet-whitelist`
   - `https://github.com/hxehex/russia-mobile-internet-whitelist/raw/main/whitelist.txt`
   - `https://github.com/hxehex/russia-mobile-internet-whitelist/raw/main/cidrwhitelist.txt`
2. `kort0881/russia-whitelist`
3. Russia Routing Ruleset discussions for v2rayNG
   - `https://github.com/2dust/v2rayNG/issues/4217`
   - `https://github.com/2dust/v2rayNG/discussions/4761`
4. `igareck/vpn-configs-for-russia`

#### Russian blocked-domain sources

1. `runetfreedom/russia-blocked-geosite`
2. `1andrevich/Re-filter-lists`
3. `1andrevich/ooni-zapret-list`
4. OONI reports and related datasets
   - `https://ooni.org/post/2024-russia-blocked-ooni-explorer/`

#### Foreign-service sources

1. `igareck/vpn-configs-for-russia`
2. Russia Routing Ruleset discussions
3. Discussions or issue threads covering AI, cloud, developer, and social services with Russia restrictions

## 3. File-Specific Update Logic

### 3.1 `ru-direct.list`

Purpose:

- Keep a compact whitelist of domains that should almost always stay `DIRECT` for a normal Russian user experience and for mobile/operator whitelist compatibility.

Candidate collection:

1. Collect domains from `whitelist.txt` in `russia-mobile-internet-whitelist`.
2. Collect relevant domains from other RU whitelist projects and routing rulesets.
3. Collect domains marked as RU-direct or bypass in `vpn-configs-for-russia` and similar configs.
4. Always include a built-in manual core set of domains:
   - state services
   - banks and payment systems
   - operators and ISPs
   - top Russian services

Filtering:

1. Keep only domains whose TLD is one of:
   - `ru`
   - `su`
   - `rf`
   - `moscow`
   - `москва`
2. Also allow explicit Russian-brand domains from the built-in manual core.
3. Exclude domains that also appear in block sources such as:
   - `russia-blocked-geosite`
   - `Re-filter-lists`
   - `ooni-zapret-list`
   - OONI reports
4. Any conflict should be handled by moving the domain into `ru-blocked-core.list` unless it is explicitly overridden to stay direct.

Deduplication:

1. Normalize all domains to lowercase.
2. Remove exact duplicates.
3. Do not add a subdomain if its parent suffix is already present.
   - Example: keep `DOMAIN-SUFFIX,example.ru` and drop `DOMAIN-SUFFIX,sub.example.ru`

Output structure:

1. Preserve comment blocks with clear sections:
   - state services
   - banks and payments
   - Russian mail and social
   - marketplaces and large services
   - operators and providers
2. Always keep the final fallback:

```text
DOMAIN-SUFFIX,ru
DOMAIN-SUFFIX,su
```

Growth limits:

1. Target size: roughly 300 to 500 domains maximum.
2. If candidates exceed the cap, keep:
   - all manual core domains
   - top-ranked domains by frequency across independent sources
3. Drop low-signal bulk additions.

### 3.2 `ru-blocked-core.list`

Purpose:

- Maintain a compact list of domains that almost always require `PROXY` in Russia because they are blocked, degraded, or politically sensitive.

Candidate collection:

1. Collect domains marked as blocked in:
   - `Re-filter-lists`
   - `russia-blocked-geosite`
   - `ooni-zapret-list`
   - OONI reports and datasets
2. Collect domains explicitly routed through proxy in `vpn-configs-for-russia` and similar projects.

Core selection:

1. Prefer domains that appear in two or more independent sources.
2. Always include the manual core list, such as:
   - Meta properties
   - Twitter / X
   - Discord
   - LinkedIn
   - YouTube / Google video delivery
   - Meduza
   - Dozhd
   - OONI
   - Tor
3. Optionally exclude RU domains if project policy explicitly wants them to remain `DIRECT`, but that must be configurable.

Size limits:

1. Keep the file compact: hundreds of lines at most.
2. Do not expand it into a massive dump of every blocked domain.
3. The goal is strong coverage of common censorship cases, not exhaustive completeness.

Conflict resolution with `ru-direct.list`:

1. If a domain appears in both direct and blocked sources, default to `ru-blocked-core.list`.
2. Remove it from `ru-direct.list`.
3. Allow an override list for domains that must always remain `DIRECT`.

### 3.3 `foreign-services.list`

Purpose:

- Track foreign services that either restrict Russia or work noticeably better through `PROXY`, especially AI, SaaS, cloud, developer, media, and communications services.

Candidate collection:

1. Collect explicitly proxied foreign domains from `vpn-configs-for-russia` and similar configs.
2. Collect commonly cited domains from routing discussions and issues.
3. Always include a manual core list for important services such as:
   - OpenAI
   - Anthropic
   - GitHub
   - Google
   - Notion
   - Figma
   - Cloudflare
   - Vercel

Filtering:

1. Exclude Russian domains and Russian TLDs.
2. Allow overlap with `ru-blocked-core.list` for foreign domains.
   - If both lists route to `PROXY`, overlap is acceptable.
3. Exclude low-value noise and bulk domains that do not materially improve routing quality.

Output structure:

1. Group domains into logical blocks:
   - AI and dev tools
   - SaaS and collaboration
   - cloud and CDN
   - mail and security
   - VPN and circumvention
   - media and entertainment
2. Keep strict output format:

```text
DOMAIN-SUFFIX,example.com
```

Growth limits:

1. Keep the file in the hundreds of lines, not thousands.
2. Favor clearly important and frequently problematic services over exhaustive coverage.

## 4. Update Frequency And Workflow

Recommended cadence:

- every 1 to 2 weeks
- or on-demand via a manual refresh command

Per refresh, Codex should:

1. Fetch external sources.
2. Build candidate buckets for:
   - RU-direct
   - RU-blocked
   - foreign
3. Resolve conflicts and apply core rules and size caps.
4. Generate new versions of the three `.list` files.
5. Show a diff of added and removed domains before finalizing changes.

## 5. Conflict Priorities

1. If a domain appears in both whitelist and blocked sources:
   - default to `ru-blocked-core.list`
   - unless the domain is present in a manual direct-override set
2. If a non-RU domain appears both in foreign-services and RU-blocked sources:
   - keep it in both files if useful
   - both paths still route to `PROXY`

## 6. Output Guarantees

After a successful update:

1. All three files are valid for Shadowrocket:
   - only `DOMAIN-SUFFIX,` entries
   - only `#` comments
2. No duplicate entries exist.
3. `ru-direct.list` always keeps the direct-routing core:
   - state services
   - banks
   - operators
   - top Russian services
4. `ru-blocked-core.list` remains compact but useful.
5. `foreign-services.list` keeps a current set of critical foreign services.

## 7. Implementation Notes

Suggested future implementation details:

1. Store manual core lists and override rules as separate machine-readable files.
2. Track source attribution per domain during candidate collection.
3. Rank candidates by:
   - manual core membership
   - number of supporting sources
   - category priority
4. Treat CIDR whitelist sources as contextual inputs only unless separate IP-based outputs are introduced.
5. Keep the final emitted lists intentionally conservative.
