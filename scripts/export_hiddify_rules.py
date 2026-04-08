#!/usr/bin/env python3
"""Export generated Shadowrocket lists into Hiddify-compatible JSON files."""

from __future__ import annotations

import argparse
import difflib
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
SHADOWROCKET_DIR = ROOT / "shadowrocket"
HIDDIFY_DIR = ROOT / "hiddify"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="write generated Hiddify files to disk")
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


def build_bucket_rules(domains: list[str], outbound: str, bucket: str) -> list[dict[str, str]]:
    rules: list[dict[str, str]] = []
    for domain in domains:
        rule: dict[str, str] = {
            "type": "domain_suffix",
            "value": domain,
            "outbound": outbound,
            "bucket": bucket,
        }
        if bucket == "ru-direct" and domain in {"ru", "su"}:
            rule["note"] = f"fallback .{domain}"
        rules.append(rule)
    return rules


def local_private_entries() -> list[dict[str, str]]:
    return [
        {"type": "ip_cidr", "value": "127.0.0.0/8"},
        {"type": "ip_cidr", "value": "10.0.0.0/8"},
        {"type": "ip_cidr", "value": "172.16.0.0/12"},
        {"type": "ip_cidr", "value": "192.168.0.0/16"},
        {"type": "ip_cidr", "value": "100.64.0.0/10"},
        {"type": "geoip", "value": "private"},
        {"type": "domain", "value": "localhost"},
        {"type": "domain_suffix", "value": "local"},
        {"type": "domain", "value": "captive.apple.com"},
        {"type": "geosite", "value": "private"},
        {"type": "geosite", "value": "apple"},
        {"type": "geosite", "value": "icloud"},
    ]


def render_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def build_bucket_payload(
    name: str,
    description: str,
    domains: list[str],
    outbound: str,
    bucket: str,
) -> dict[str, Any]:
    return {
        "name": name,
        "description": description,
        "platform": "hiddify",
        "rules": build_bucket_rules(domains, outbound=outbound, bucket=bucket),
    }


def build_profile_payloads() -> dict[Path, dict[str, Any]]:
    local_entries = local_private_entries()
    return {
        HIDDIFY_DIR / "routing-profile-split.json": {
            "name": "RU Split Routing",
            "description": "Direct local and Russian traffic, proxy blocked core and foreign services.",
            "platform": "hiddify",
            "priority": [
                "local",
                "ru-blocked-core",
                "ru-direct",
                "foreign-services",
                "final",
            ],
            "rules": [
                {
                    "name": "Local and private",
                    "bucket": "local",
                    "outbound": "direct",
                    "entries": local_entries,
                },
                {
                    "name": "RU direct",
                    "bucket": "ru-direct",
                    "outbound": "direct",
                    "entries": [
                        {"type": "source", "value": "ru-direct"},
                        {"type": "geoip", "value": "ru"},
                    ],
                },
                {
                    "name": "RU blocked core",
                    "bucket": "ru-blocked-core",
                    "outbound": "proxy",
                    "entries": [
                        {"type": "source", "value": "ru-blocked-core"},
                    ],
                },
                {
                    "name": "Foreign services",
                    "bucket": "foreign-services",
                    "outbound": "proxy",
                    "entries": [
                        {"type": "source", "value": "foreign-services"},
                    ],
                },
                {
                    "name": "Final fallback",
                    "bucket": "final",
                    "outbound": "proxy",
                    "entries": [
                        {"type": "final", "value": "final"},
                    ],
                },
            ],
        },
        HIDDIFY_DIR / "routing-profile-full.json": {
            "name": "Full VPN",
            "description": "All non-local traffic through proxy, keeping LAN and service traffic direct.",
            "platform": "hiddify",
            "priority": [
                "local",
                "final",
            ],
            "rules": [
                {
                    "name": "Local and private",
                    "bucket": "local",
                    "outbound": "direct",
                    "entries": local_entries,
                },
                {
                    "name": "Final fallback",
                    "bucket": "final",
                    "outbound": "proxy",
                    "entries": [
                        {"type": "final", "value": "final"},
                    ],
                },
            ],
        },
    }


def build_outputs() -> dict[Path, str]:
    direct_domains = read_domain_suffix_list(SHADOWROCKET_DIR / "ru-direct.list")
    blocked_domains = read_domain_suffix_list(SHADOWROCKET_DIR / "ru-blocked-core.list")
    foreign_domains = read_domain_suffix_list(SHADOWROCKET_DIR / "foreign-services.list")

    payloads: dict[Path, dict[str, Any]] = {
        HIDDIFY_DIR / "ru-direct.hiddify.json": build_bucket_payload(
            name="RU Direct",
            description="Russian and socially significant domains that should stay DIRECT.",
            domains=direct_domains,
            outbound="direct",
            bucket="ru-direct",
        ),
        HIDDIFY_DIR / "ru-blocked-core.hiddify.json": build_bucket_payload(
            name="RU Blocked Core",
            description="Compact core of domains that almost always require PROXY in Russia.",
            domains=blocked_domains,
            outbound="proxy",
            bucket="ru-blocked-core",
        ),
        HIDDIFY_DIR / "foreign-services.hiddify.json": build_bucket_payload(
            name="Foreign Services",
            description="Foreign services that are restricted in Russia or work better through PROXY.",
            domains=foreign_domains,
            outbound="proxy",
            bucket="foreign-services",
        ),
    }
    payloads.update(build_profile_payloads())
    return {path: render_json(payload) for path, payload in payloads.items()}


def build_report(outputs: dict[Path, str], changed_paths: list[Path]) -> dict[str, Any]:
    rule_counts: dict[str, int] = {}
    profiles: list[str] = []
    for path, content in outputs.items():
        payload = json.loads(content)
        rules = payload.get("rules")
        if isinstance(rules, list):
            if path.name.endswith(".hiddify.json"):
                rule_counts[path.name] = len(rules)
            else:
                profiles.append(path.name)
    return {
        "files": [path.name for path in sorted(outputs)],
        "changed_files": [path.name for path in changed_paths],
        "rule_counts": rule_counts,
        "profiles": sorted(profiles),
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
        HIDDIFY_DIR.mkdir(parents=True, exist_ok=True)
        for path, content in outputs.items():
            path.write_text(content, encoding="utf-8")
        if changed_paths:
            print(f"Updated {len(changed_paths)} Hiddify file(s).", file=status_stream)
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
