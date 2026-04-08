# ios-routing

Ready-to-use Shadowrocket routing presets and rule lists for split tunneling on iOS.

## Structure

- `shadowrocket/Universal-Routing.conf` - universal routing-only config without embedded servers
- `shadowrocket/Vaso-RU-Split-v2.conf` - personal split-routing config with embedded proxy definitions
- `shadowrocket/ru-blocked-core.list` - domains that should always go through VPN
- `shadowrocket/ru-direct.list` - Russian domains that should stay direct
- `shadowrocket/foreign-services.list` - foreign services that are more stable through VPN

## Usage

### Universal routing

1. Import your own server into Shadowrocket from x-ui, URI, or QR.
2. Import `shadowrocket/Universal-Routing.conf`.
3. Make `Universal-Routing.conf` the active config.
4. Leave your preferred imported server selected as the active proxy.

### Personal config

1. Import `shadowrocket/Vaso-RU-Split-v2.conf`.
2. Select it as the active config.
3. In the `PROXY` group choose `NL-VLESS`.
4. If you add a US backup node later, uncomment `US-VLESS` in the config and add its real credentials.

## Notes

- `Universal-Routing.conf` is the recommended file for family, clients, and anyone who uses their own nodes.
- The rule lists are shared between both configs and can be extended over time.
- `FINAL,PROXY` is enabled, so all non-local traffic that does not match the direct rules will go through VPN.
- `GEOIP,RU,DIRECT` keeps Russian IP traffic direct as a fallback.
