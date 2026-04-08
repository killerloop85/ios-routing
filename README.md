# ios-routing

Ready-to-use Shadowrocket routing presets and rule lists for split tunneling on iOS.

## Structure

- `shadowrocket/Vaso-RU-Split-v2.conf` - main split-routing config
- `shadowrocket/ru-blocked-core.list` - domains that should always go through VPN
- `shadowrocket/ru-direct.list` - Russian domains that should stay direct
- `shadowrocket/foreign-services.list` - foreign services that are more stable through VPN

## Usage

1. Open `shadowrocket/Vaso-RU-Split-v2.conf` in Shadowrocket and import it.
2. Select the config as active.
3. In the `PROXY` group choose `NL-VLESS`.
4. If you add a US backup node later, uncomment `US-VLESS` in the config and add its real credentials.

## Notes

- The rule lists are starter sets and can be extended over time.
- `FINAL,PROXY` is enabled, so all non-local traffic that does not match the direct rules will go through VPN.
- `GEOIP,RU,DIRECT` keeps Russian IP traffic direct as a fallback.
