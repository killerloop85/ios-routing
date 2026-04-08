#!/usr/bin/env python3
"""Export generated Shadowrocket lists into Happ-compatible routing JSON."""

from __future__ import annotations

import argparse
import difflib
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
SHADOWROCKET_DIR = ROOT / "shadowrocket"
HAPP_DIR = ROOT / "happ"

DIRECT_PATH = SHADOWROCKET_DIR / "ru-direct.list"
BLOCKED_PATH = SHADOWROCKET_DIR / "ru-blocked-core.list"
FOREIGN_PATH = SHADOWROCKET_DIR / "foreign-services.list"

LOCAL_DOMAINS = [
    "localhost",
    "local",
    "captive.apple.com",
]

LOCAL_IP_CIDRS = [
    "127.0.0.0/8",
    "10.0.0.0/8",
    "172.16.0.0/12",
    "192.168.0.0/16",
    "100.64.0.0/10",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="write generated Happ files to disk")
    parser.add_argument(
        "--offline",
        action="store_true",
        help="accepted for workflow parity; export only uses local generated lists",
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


def unique_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def render_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def build_split_profile() -> dict[str, Any]:
    direct_domains = read_domain_suffix_list(DIRECT_PATH)
    blocked_domains = read_domain_suffix_list(BLOCKED_PATH)
    foreign_domains = read_domain_suffix_list(FOREIGN_PATH)

    return {
        "name": "RU Split Routing",
        "description": "Direct local and Russian traffic, proxy blocked core and foreign services.",
        "platform": "happ",
        "globalProxy": True,
        "routeOrder": "direct-block-proxy",
        "direct": {
            "domains": unique_preserve_order(LOCAL_DOMAINS + direct_domains),
            "ip_cidrs": list(LOCAL_IP_CIDRS),
        },
        "proxy": {
            "domains": unique_preserve_order(blocked_domains + foreign_domains),
            "ip_cidrs": [],
        },
        "block": {
            "domains": [],
            "ip_cidrs": [],
        },
        "bucket_domains": {
            "ru-direct": list(direct_domains),
            "ru-blocked-core": list(blocked_domains),
            "foreign-services": list(foreign_domains),
            "local": list(LOCAL_DOMAINS),
        },
    }


def build_split_direct_default_profile() -> dict[str, Any]:
    direct_domains = read_domain_suffix_list(DIRECT_PATH)
    blocked_domains = read_domain_suffix_list(BLOCKED_PATH)
    foreign_domains = read_domain_suffix_list(FOREIGN_PATH)

    return {
        "name": "RU Split Routing (Direct Default)",
        "description": "Direct local and Russian traffic, proxy blocked core and foreign services, direct default fallback for Happ-style routing.",
        "platform": "happ",
        "globalProxy": False,
        "routeOrder": "direct-block-proxy",
        "direct": {
            "domains": unique_preserve_order(LOCAL_DOMAINS + direct_domains),
            "ip_cidrs": list(LOCAL_IP_CIDRS),
        },
        "proxy": {
            "domains": unique_preserve_order(blocked_domains + foreign_domains),
            "ip_cidrs": [],
        },
        "block": {
            "domains": [],
            "ip_cidrs": [],
        },
        "bucket_domains": {
            "ru-direct": list(direct_domains),
            "ru-blocked-core": list(blocked_domains),
            "foreign-services": list(foreign_domains),
            "local": list(LOCAL_DOMAINS),
        },
    }


def build_full_profile() -> dict[str, Any]:
    return {
        "name": "Full VPN",
        "description": "All non-local traffic through proxy, keeping LAN and service traffic direct.",
        "platform": "happ",
        "globalProxy": True,
        "routeOrder": "direct-block-proxy",
        "direct": {
            "domains": list(LOCAL_DOMAINS),
            "ip_cidrs": list(LOCAL_IP_CIDRS),
        },
        "proxy": {
            "domains": [],
            "ip_cidrs": [],
        },
        "block": {
            "domains": [],
            "ip_cidrs": [],
        },
        "bucket_domains": {
            "local": list(LOCAL_DOMAINS),
        },
    }


def build_outputs() -> dict[Path, str]:
    outputs = {
        HAPP_DIR / "routing-profile-split.json": render_json(build_split_profile()),
        HAPP_DIR / "routing-profile-split-direct-default.json": render_json(build_split_direct_default_profile()),
        HAPP_DIR / "routing-profile-full.json": render_json(build_full_profile()),
    }
    return outputs


def build_report(outputs: dict[Path, str], changed_paths: list[Path]) -> dict[str, Any]:
    profiles: dict[str, dict[str, Any]] = {}
    for path, content in outputs.items():
        payload = json.loads(content)
        direct = payload.get("direct", {})
        proxy = payload.get("proxy", {})
        block = payload.get("block", {})
        profiles[path.name] = {
            "globalProxy": payload.get("globalProxy"),
            "routeOrder": payload.get("routeOrder"),
            "direct_domains": len(direct.get("domains", [])) if isinstance(direct, dict) else 0,
            "direct_ip_cidrs": len(direct.get("ip_cidrs", [])) if isinstance(direct, dict) else 0,
            "proxy_domains": len(proxy.get("domains", [])) if isinstance(proxy, dict) else 0,
            "proxy_ip_cidrs": len(proxy.get("ip_cidrs", [])) if isinstance(proxy, dict) else 0,
            "block_domains": len(block.get("domains", [])) if isinstance(block, dict) else 0,
            "block_ip_cidrs": len(block.get("ip_cidrs", [])) if isinstance(block, dict) else 0,
        }
    return {
        "files": [path.name for path in sorted(outputs)],
        "changed_files": [path.name for path in changed_paths],
        "profiles": profiles,
    }


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
        HAPP_DIR.mkdir(parents=True, exist_ok=True)
        for path, content in outputs.items():
            path.write_text(content, encoding="utf-8")
        if changed_paths:
            print(f"Updated {len(changed_paths)} Happ file(s).", file=status_stream)
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
