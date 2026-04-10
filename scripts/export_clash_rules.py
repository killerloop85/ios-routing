#!/usr/bin/env python3
"""Export generated Shadowrocket lists into Clash for Windows (mihomo) YAML."""

from __future__ import annotations

import argparse
import difflib
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
SHADOWROCKET_DIR = ROOT / "shadowrocket"
CLASH_DIR = ROOT / "clash"

DIRECT_PATH = SHADOWROCKET_DIR / "ru-direct.list"
BLOCKED_PATH = SHADOWROCKET_DIR / "ru-blocked-core.list"
FOREIGN_PATH = SHADOWROCKET_DIR / "foreign-services.list"

LOCAL_DOMAIN_RULES = [
    "DOMAIN,localhost,DIRECT",
    "DOMAIN-SUFFIX,local,DIRECT",
    "DOMAIN,captive.apple.com,DIRECT",
]

LOCAL_IP_RULES = [
    "IP-CIDR,127.0.0.0/8,DIRECT,no-resolve",
    "IP-CIDR,10.0.0.0/8,DIRECT,no-resolve",
    "IP-CIDR,172.16.0.0/12,DIRECT,no-resolve",
    "IP-CIDR,192.168.0.0/16,DIRECT,no-resolve",
    "IP-CIDR,100.64.0.0/10,DIRECT,no-resolve",
]

RU_GEOIP_RULE = "GEOIP,RU,DIRECT,no-resolve"
PROXY_GROUP_NAME = "PROXY"
DIRECT_GROUP_NAME = "DIRECT"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="write generated Clash files to disk")
    parser.add_argument(
        "--offline",
        action="store_true",
        help="accepted for workflow parity; export only uses local generated lists",
    )
    parser.add_argument(
        "--profile",
        action="append",
        choices=["full", "split", "split-direct-default"],
        help="additional profile(s) to generate; defaults to only the stable full profile",
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


def yaml_quote(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def render_rule_layer(
    *,
    title: str,
    description: str,
    rules: list[str],
) -> str:
    lines = [
        f"# {title}",
        f"# {description}",
        "rules:",
    ]
    lines.extend(f"  - {yaml_quote(rule)}" for rule in rules)
    lines.append("")
    return "\n".join(lines)


def render_profile(
    *,
    title: str,
    description: str,
    status: str,
    intended_use: str,
    rules: list[str],
) -> str:
    lines = [
        f"# {title}",
        f"# {description}",
        f"# status: {status}",
        f"# intended-use: {intended_use}",
        "port: 7890",
        "socks-port: 7891",
        "mode: Rule",
        "allow-lan: true",
        "log-level: info",
        "proxies: []",
        "proxy-groups:",
        f"  - name: {yaml_quote(PROXY_GROUP_NAME)}",
        "    type: select",
        "    include-all: true",
        "    proxies:",
        f"      - {yaml_quote(DIRECT_GROUP_NAME)}",
        f"  - name: {yaml_quote(DIRECT_GROUP_NAME)}",
        "    type: select",
        "    proxies:",
        f"      - {yaml_quote(DIRECT_GROUP_NAME)}",
        "rules:",
    ]
    lines.extend(f"  - {yaml_quote(rule)}" for rule in rules)
    lines.append("")
    return "\n".join(lines)


def build_domain_rules(domains: list[str], target: str) -> list[str]:
    return [f"DOMAIN-SUFFIX,{domain},{target}" for domain in domains]


def build_full_profile_rules() -> list[str]:
    return list(LOCAL_DOMAIN_RULES) + list(LOCAL_IP_RULES) + [f"MATCH,{PROXY_GROUP_NAME}"]


def build_split_profile_rules(
    direct_domains: list[str],
    blocked_domains: list[str],
    foreign_domains: list[str],
    *,
    final_action: str,
) -> list[str]:
    rules = list(LOCAL_DOMAIN_RULES)
    rules.extend(LOCAL_IP_RULES)
    rules.extend(build_domain_rules(blocked_domains, PROXY_GROUP_NAME))
    rules.extend(build_domain_rules(direct_domains, DIRECT_GROUP_NAME))
    rules.extend(build_domain_rules(foreign_domains, PROXY_GROUP_NAME))
    rules.append(RU_GEOIP_RULE)
    rules.append(f"MATCH,{final_action}")
    return rules


def build_outputs(profiles: list[str]) -> dict[Path, str]:
    direct_domains = read_domain_suffix_list(DIRECT_PATH)
    blocked_domains = read_domain_suffix_list(BLOCKED_PATH)
    foreign_domains = read_domain_suffix_list(FOREIGN_PATH)

    outputs: dict[Path, str] = {
        CLASH_DIR / "ru-direct.rules.yaml": render_rule_layer(
            title="RU Direct",
            description="Russian and socially significant domains that should stay DIRECT.",
            rules=build_domain_rules(direct_domains, DIRECT_GROUP_NAME),
        ),
        CLASH_DIR / "ru-blocked-core.rules.yaml": render_rule_layer(
            title="RU Blocked Core",
            description="Compact core of domains that almost always require PROXY in Russia.",
            rules=build_domain_rules(blocked_domains, PROXY_GROUP_NAME),
        ),
        CLASH_DIR / "foreign-services.rules.yaml": render_rule_layer(
            title="Foreign Services",
            description="Foreign services that are restricted in Russia or work better through PROXY.",
            rules=build_domain_rules(foreign_domains, PROXY_GROUP_NAME),
        ),
    }

    for profile in profiles:
        if profile == "full":
            outputs[CLASH_DIR / "routing-profile-full.yaml"] = render_profile(
                title="Full VPN",
                description="All non-local traffic through proxy, keeping LAN and service traffic direct.",
                status="stable",
                intended_use="production",
                rules=build_full_profile_rules(),
            )
        elif profile == "split":
            outputs[CLASH_DIR / "routing-profile-split.yaml"] = render_profile(
                title="RU Split Routing",
                description="Parity-oriented split profile: local and RU direct, blocked core and foreign services via proxy.",
                status="experimental",
                intended_use="parity",
                rules=build_split_profile_rules(
                    direct_domains,
                    blocked_domains,
                    foreign_domains,
                    final_action=PROXY_GROUP_NAME,
                ),
            )
        elif profile == "split-direct-default":
            outputs[CLASH_DIR / "routing-profile-split-direct-default.yaml"] = render_profile(
                title="RU Split Routing (Direct Default)",
                description="Happ-style split profile: local and RU direct, blocked core and foreign services via proxy, direct default fallback.",
                status="experimental",
                intended_use="direct-default",
                rules=build_split_profile_rules(
                    direct_domains,
                    blocked_domains,
                    foreign_domains,
                    final_action=DIRECT_GROUP_NAME,
                ),
            )
    return outputs


def extract_rendered_rules(content: str) -> list[str]:
    rules: list[str] = []
    in_rules = False
    for raw_line in content.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped:
            continue
        if not in_rules:
            if stripped == "rules:":
                in_rules = True
            continue
        if line.startswith("  - "):
            rules.append(line.split("- ", 1)[1].strip().strip('"'))
    return rules


def build_report(outputs: dict[Path, str], changed_paths: list[Path]) -> dict[str, Any]:
    bucket_counts: dict[str, int] = {}
    profiles: dict[str, dict[str, Any]] = {}
    for path, content in outputs.items():
        rule_lines = extract_rendered_rules(content)
        if path.name.endswith(".rules.yaml"):
            bucket_counts[path.name] = len(rule_lines)
        else:
            final_rule = next((rule for rule in reversed(rule_lines) if rule.startswith("MATCH,")), "")
            profiles[path.name] = {
                "rules": len(rule_lines),
                "final_rule": final_rule,
            }
    return {
        "files": [path.name for path in sorted(outputs)],
        "changed_files": [path.name for path in changed_paths],
        "bucket_rule_counts": bucket_counts,
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
    requested_profiles = args.profile or ["full"]
    outputs = build_outputs(requested_profiles)
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
        CLASH_DIR.mkdir(parents=True, exist_ok=True)
        for path, content in outputs.items():
            path.write_text(content, encoding="utf-8")
        if changed_paths:
            print(f"Updated {len(changed_paths)} Clash file(s).", file=status_stream)
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
