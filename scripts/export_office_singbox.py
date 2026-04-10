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
    "10.77.221.0/24",
]
LOCAL_DOMAINS = ["localhost", "captive.apple.com"]
LOCAL_SUFFIXES = ["local", "lan"]


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
            "servers": [
                {
                    "tag": "local-dns",
                    "address": "local",
                    "detour": "direct",
                },
                {
                    "tag": "remote-dns",
                    "address": "https://1.1.1.1/dns-query",
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
            }
        ],
        "outbounds": [
            {
                "type": "selector",
                "tag": "proxy",
                "outbounds": [
                    "vless-reality-primary",
                ],
                "default": "vless-reality-primary",
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
                        "spider_x": "REPLACE_VLESS_SPIDER_X",
                    },
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
    blocked_domains = read_domain_suffix_list(SHADOWROCKET_DIR / "ru-blocked-core.list")
    foreign_domains = read_domain_suffix_list(SHADOWROCKET_DIR / "foreign-services.list")

    payload = base_config()
    payload["route"] = {
        "auto_detect_interface": True,
        "final": "proxy",
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
                "domain_suffix": LOCAL_SUFFIXES + direct_domains,
                "outbound": "direct",
            },
            {
                "domain_suffix": blocked_domains,
                "outbound": "proxy",
            },
            {
                "domain_suffix": foreign_domains,
                "outbound": "proxy",
            },
        ],
    }
    return payload


def build_full_config() -> dict[str, Any]:
    payload = base_config()
    payload["route"] = {
        "auto_detect_interface": True,
        "final": "proxy",
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
                "domain_suffix": LOCAL_SUFFIXES,
                "outbound": "direct",
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
