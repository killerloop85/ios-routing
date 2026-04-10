function FindProxyForURL(url, host) {
  if (isPlainHostName(host)) {
    return "DIRECT";
  }

  if (dnsDomainIs(host, ".local") || dnsDomainIs(host, ".lan")) {
    return "DIRECT";
  }

  if (host === "localhost" || host === "captive.apple.com") {
    return "DIRECT";
  }

  return "PROXY 10.77.221.15:1080; SOCKS5 10.77.221.15:1080; DIRECT";
}
