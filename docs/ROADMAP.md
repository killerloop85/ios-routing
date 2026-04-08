# ROADMAP

## Near-Term

- Fix Streisand split-profile import instability and the suspected split URI crash path.
- Fix confirmed Streisand split-routing mismatch: `ip.ru` on `routing-profile-split-qr` resolves through NL instead of staying DIRECT/RU.
- Validate Streisand routing behavior on real devices before treating it as production-ready; until then, use only full-profile in practice.
- Validate Hiddify split/full profiles on real devices and document import caveats if any appear.
- Define the exit criteria for Streisand experimental status: field-test matrix across profile type, client version, and a fixed direct/proxy domain set must pass without routing mismatches.
- Keep `docs/streisand-field-test-matrix.md` current as the operational checklist for all future Streisand validation.

## Routing Extensions

- Evaluate optional IP-heavy layers for Google and Telegram where domain-only routing is not enough.
- Evaluate additional `geoip` and `geosite` expansions only if they improve real-world behavior without bloating the policy.
- Expand compact client-specific profiles only when size or import stability requires it.

## Regression Layer

- Add newly discovered real-world edge cases to `data/regression_domains.json`.
- Keep parity checks strict across Shadowrocket, Streisand, and Hiddify.
- Add client-specific regression notes when a backend behaves differently from the normalized policy layer.
- Record the Streisand `ip.ru -> NL on split-qr` case as a client-behavior exception until the export model or the client behavior is understood.

## Streisand Investigation

- Verify whether the mismatch comes from our export model: rule ordering, `domainMatcher`, `domainStrategy`, final fallback semantics, and `source:*` expansion vs compact `geosite/domain` rules.
- Verify whether the mismatch comes from the Streisand client itself: import parser behavior, precedence between `domain`, `geoip`, and final rules, and version-specific routing differences.
- Keep a small field-test matrix for Streisand split-routing: at minimum `ip.ru`, one bank/government domain, one Meta domain, YouTube, and OpenAI across multiple client versions.
- For every new mismatch, classify it as `mapping_bug`, `client_limitation`, or `transport_issue` before changing exporter logic.

## Operational

- Keep using routing reports as the first place to eyeball generated diffs.
- Treat generated client exports as thin artifacts, not independent policy engines.
- Revisit import/share layers only after the normalized JSON layers are stable in real usage.
