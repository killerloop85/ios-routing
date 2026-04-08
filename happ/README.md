# Happ Routing

These files are a thin export layer over the shared routing policy in this repository.

Available profiles:

- `routing-profile-split.json`
- `routing-profile-full.json`

How to use with Happ:

1. Open the exported JSON profile.
2. Copy `direct.domains` into Happ `DirectSites`.
3. Copy `direct.ip_cidrs` into Happ `DirectIp`.
4. Copy `proxy.domains` into Happ `ProxySites`.
5. Copy `proxy.ip_cidrs` into Happ `ProxyIp`.
6. Leave `block` empty unless you explicitly want block-rules later.

Notes:

- The JSON files are not source of truth.
- The source of truth remains the shared routing policy and generated Shadowrocket lists.
- Split mode keeps a proxy-default fallback to stay aligned with the repository core routing semantics.
