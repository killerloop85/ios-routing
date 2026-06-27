#!/usr/bin/env python3
"""Export the finalized routing core into Synology sing-box office configs."""

from __future__ import annotations

import argparse
import difflib
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
SHADOWROCKET_DIR = ROOT / "shadowrocket"
OFFICE_SINGBOX_DIR = ROOT / "office" / "sing-box"
GENERATED_DIR = OFFICE_SINGBOX_DIR / "generated"

LOCAL_IP_CIDRS = [
    "127.0.0.0/8",
    "10.0.0.0/8",
    "172.16.0.0/12",
    "192.168.0.0/16",
    "100.64.0.0/10",
    "17.0.0.0/8",
    "10.77.216.0/21",
    "10.77.221.0/24",
    "10.77.230.0/24",
]
LOCAL_DOMAINS = ["localhost", "captive.apple.com"]
LOCAL_SUFFIXES = ["local", "lan"]
TPROXY_INBOUND_PORT = 12346

# Keep the office VPN route intentionally narrow.  The broad finalized
# blocked/foreign lists are useful for per-device clients, but on the NAS they
# can fan out into hundreds of background office connections and overload a
# single Reality upstream.  The office gateway should default to direct and
# only send explicitly blocked/user-facing families through VLESS.
TELEGRAM_SUFFIXES = [
    "api.telegram.org",
    "telegram.org",
    "t.me",
    "telegram.me",
    "telegra.ph",
    "telesco.pe",
]
TELEGRAM_IP_CIDRS = [
    "91.108.4.0/22",
    "91.108.56.0/22",
    "149.154.160.0/20",
]
SOCIAL_VPN_SUFFIXES = [
    "api.whatsapp.com",
    "web.whatsapp.com",
    "whatsapp.com",
    "whatsapp.net",
    "wa.me",
    "instagram.com",
    "cdninstagram.com",
    "facebook.com",
    "fbcdn.net",
    "messenger.com",
    "threads.net",
    "twitter.com",
    "x.com",
    "t.co",
    "discord.com",
    "discord.gg",
    "discordapp.com",
    "linkedin.com",
    "licdn.com",
    "meduza.io",
    "svoboda.org",
    "currenttime.tv",
    "dozhd.ru",
    "tvrain.tv",
]
AI_VPN_SUFFIXES = [
    "openai.com",
    "chatgpt.com",
    "api.openai.com",
    "anthropic.com",
    "claude.ai",
    "claude.com",
    "perplexity.ai",
    "deepl.com",
    "huggingface.co",
    "hf.co",
    "replicate.com",
    "cursor.com",
    "cursor.sh",
]
FOREIGN_IP_BLOCKING_SUFFIXES = [
    "canva.com",
    "figma.com",
    "github.com",
    "githubusercontent.com",
    "githubassets.com",
    "gitlab.com",
    "docker.com",
    "docker.io",
    "registry-1.docker.io",
    "auth.docker.io",
    "npmjs.com",
    "npmjs.org",
    "registry.npmjs.org",
    "pypi.org",
    "pythonhosted.org",
    "supabase.com",
    "vercel.com",
    "netlify.app",
    "render.com",
    "fly.io",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="write generated office sing-box configs to disk")
    parser.add_argument(
        "--offline",
        action="store_true",
        help="accepted for parity with other exporters; office export only uses local finalized lists",
    )
    parser.add_argument(
        "--report-json",
        nargs="?",
        const="-",
        help="write a structured JSON report to PATH or stdout with '-'",
    )
    return parser.parse_args()


def read_domain_suffix_list(path: Path) -> list[str]:
    domains: list[str] = []
    prefix = "DOMAIN-SUFFIX,"
    for lineno, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if not line.startswith(prefix):
            raise ValueError(f"{path}:{lineno}: unsupported list line: {raw_line}")
        suffix = line[len(prefix):].strip().lower()
        if not suffix:
            raise ValueError(f"{path}:{lineno}: empty domain suffix")
        domains.append(suffix)
    return domains


def base_config() -> dict[str, Any]:
    return {
        "log": {
            "level": "info",
            "timestamp": True,
        },
        "dns": {
            "strategy": "ipv4_only",
            "servers": [
                {
                    "tag": "local-dns",
                    "type": "local",
                },
                {
                    "tag": "remote-dns",
                    "type": "https",
                    "server": "1.1.1.1",
                    "server_port": 443,
                    "path": "/dns-query",
                    "detour": "proxy",
                },
            ],
            "rules": [
                {
                    "domain": LOCAL_DOMAINS,
                    "server": "local-dns",
                },
                {
                    "domain_suffix": LOCAL_SUFFIXES,
                    "server": "local-dns",
                },
            ],
            "final": "remote-dns",
        },
        "inbounds": [
            {
                "type": "mixed",
                "tag": "office-mixed",
                "listen": "0.0.0.0",
                "listen_port": 1080,
                "sniff": True,
                "sniff_override_destination": True,
                "users": [
                    {
                        "username": "REPLACE_PROXY_USERNAME",
                        "password": "REPLACE_PROXY_PASSWORD",
                    }
                ],
            },
            {
                "type": "tproxy",
                "tag": "office-tproxy",
                "listen": "0.0.0.0",
                "listen_port": TPROXY_INBOUND_PORT,
                "network": "tcp,udp",
                "sniff": True,
                "sniff_override_destination": True,
            },
        ],
        "outbounds": [
            {
                "type": "selector",
                "tag": "proxy",
                "outbounds": [
                    "direct",
                    "proxy-auto",
                    "vless-reality-primary",
                ],
                "default": "direct",
            },
            {
                "type": "urltest",
                "tag": "proxy-auto",
                "outbounds": [
                    "vless-reality-primary",
                ],
                "url": "https://www.gstatic.com/generate_204",
                "interval": "3m",
                "tolerance": 50,
            },
            {
                "type": "vless",
                "tag": "vless-reality-primary",
                "server": "REPLACE_VLESS_SERVER",
                "server_port": "REPLACE_VLESS_PORT",
                "uuid": "REPLACE_VLESS_UUID",
                "flow": "REPLACE_VLESS_FLOW",
                "tls": {
                    "enabled": True,
                    "server_name": "REPLACE_VLESS_SERVER_NAME",
                    "utls": {
                        "enabled": True,
                        "fingerprint": "REPLACE_VLESS_FINGERPRINT",
                    },
                    "reality": {
                        "enabled": True,
                        "public_key": "REPLACE_VLESS_PUBLIC_KEY",
                        "short_id": "REPLACE_VLESS_SHORT_ID",
                    },
                },
            },
            {
                "type": "hysteria2",
                "tag": "hysteria2-fallback",
                "server": "REPLACE_HY2_SERVER",
                "server_port": "REPLACE_HY2_PORT",
                "password": "REPLACE_HY2_PASSWORD",
                "tls": {
                    "enabled": True,
                    "server_name": "REPLACE_HY2_SNI",
                    "alpn": [
                        "h3",
                    ],
                },
            },
            {
                "type": "direct",
                "tag": "direct",
            },
            {
                "type": "block",
                "tag": "block",
            },
            {
                "type": "dns",
                "tag": "dns-out",
            },
        ],
    }


def build_split_config() -> dict[str, Any]:
    direct_domains = read_domain_suffix_list(SHADOWROCKET_DIR / "ru-direct.list")

    payload = base_config()
    payload["route"] = {
        "auto_detect_interface": True,
        "default_domain_resolver": "local-dns",
        "final": "direct",
        "rules": [
            {
                "ip_cidr": LOCAL_IP_CIDRS,
                "outbound": "direct",
            },
            {
                "domain": LOCAL_DOMAINS,
                "outbound": "direct",
            },
            {
                "protocol": [
                    "bittorrent",
                ],
                "outbound": "direct",
            },
            {
                "domain_suffix": LOCAL_SUFFIXES + direct_domains,
                "outbound": "direct",
            },
            {
                "domain_suffix": TELEGRAM_SUFFIXES,
                "outbound": "vless-reality-primary",
            },
            {
                "ip_cidr": TELEGRAM_IP_CIDRS,
                "outbound": "vless-reality-primary",
            },
            {
                "domain_suffix": SOCIAL_VPN_SUFFIXES,
                "outbound": "vless-reality-primary",
            },
            {
                "domain_suffix": AI_VPN_SUFFIXES,
                "outbound": "vless-reality-primary",
            },
            {
                "domain_suffix": FOREIGN_IP_BLOCKING_SUFFIXES,
                "outbound": "vless-reality-primary",
            },
        ],
    }
    return payload


def build_full_config() -> dict[str, Any]:
    payload = base_config()
    payload["route"] = {
        "auto_detect_interface": True,
        "default_domain_resolver": "local-dns",
        "final": "direct",
        "rules": [
            {
                "ip_cidr": LOCAL_IP_CIDRS,
                "outbound": "direct",
            },
            {
                "domain": LOCAL_DOMAINS,
                "outbound": "direct",
            },
            {
                "protocol": [
                    "bittorrent",
                ],
                "outbound": "direct",
            },
            {
                "domain_suffix": LOCAL_SUFFIXES,
                "outbound": "direct",
            },
            {
                "domain_suffix": TELEGRAM_SUFFIXES,
                "outbound": "vless-reality-primary",
            },
            {
                "ip_cidr": TELEGRAM_IP_CIDRS,
                "outbound": "vless-reality-primary",
            },
            {
                "domain_suffix": SOCIAL_VPN_SUFFIXES,
                "outbound": "vless-reality-primary",
            },
            {
                "domain_suffix": AI_VPN_SUFFIXES,
                "outbound": "vless-reality-primary",
            },
            {
                "domain_suffix": FOREIGN_IP_BLOCKING_SUFFIXES,
                "outbound": "vless-reality-primary",
            },
        ],
    }
    return payload


def render_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def build_outputs() -> dict[Path, str]:
    payloads = {
        GENERATED_DIR / "config.split.generated.json": build_split_config(),
        GENERATED_DIR / "config.full.generated.json": build_full_config(),
    }
    return {path: render_json(payload) for path, payload in payloads.items()}


def build_report(outputs: dict[Path, str], changed_paths: list[Path]) -> dict[str, Any]:
    summary: dict[str, Any] = {"files": [], "changed_files": []}
    for path, content in sorted(outputs.items()):
        payload = json.loads(content)
        route = payload.get("route", {})
        rules = route.get("rules", [])
        summary["files"].append(
            {
                "name": path.name,
                "route_rule_count": len(rules) if isinstance(rules, list) else 0,
                "final": route.get("final"),
            }
        )
    summary["changed_files"] = [path.name for path in changed_paths]
    return summary


def write_report(path_value: str, report: dict[str, Any]) -> None:
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if path_value == "-":
        sys.stdout.write(rendered)
        return
    path = Path(path_value)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(rendered, encoding="utf-8")


def main() -> int:
    args = parse_args()
    outputs = build_outputs()
    status_stream = sys.stderr if args.report_json == "-" else sys.stdout

    changed_paths: list[Path] = []
    diff_chunks: list[str] = []
    for path, content in outputs.items():
        existing = path.read_text(encoding="utf-8") if path.exists() else ""
        if existing == content:
            continue
        changed_paths.append(path)
        diff_chunks.append(
            "".join(
                difflib.unified_diff(
                    existing.splitlines(keepends=True),
                    content.splitlines(keepends=True),
                    fromfile=str(path),
                    tofile=str(path),
                )
            )
        )

    if args.write:
        GENERATED_DIR.mkdir(parents=True, exist_ok=True)
        for path, content in outputs.items():
            path.write_text(content, encoding="utf-8")
        if changed_paths:
            print(f"Updated {len(changed_paths)} office sing-box file(s).", file=status_stream)
        else:
            print("No changes.", file=status_stream)
    else:
        if diff_chunks:
            status_stream.write("".join(diff_chunks))
        else:
            print("No changes.", file=status_stream)

    if args.report_json:
        write_report(args.report_json, build_report(outputs, changed_paths))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
