#!/usr/bin/env python3
"""Export Streisand routing profiles as import-ready streisand:// URIs."""

from __future__ import annotations

import argparse
import base64
import difflib
import json
import plistlib
import sys
import uuid
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
STREISAND_DIR = ROOT / "streisand"

PROFILE_FILES = (
    STREISAND_DIR / "routing-profile-split.json",
    STREISAND_DIR / "routing-profile-full.json",
)
BUCKET_FILES = {
    "ru-direct": STREISAND_DIR / "ru-direct.streisand.json",
    "ru-blocked-core": STREISAND_DIR / "ru-blocked-core.streisand.json",
    "foreign-services": STREISAND_DIR / "foreign-services.streisand.json",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="write generated Streisand URI files to disk")
    parser.add_argument(
        "--offline",
        action="store_true",
        help="accepted for workflow parity; URI export only uses local generated JSON profiles",
    )
    parser.add_argument(
        "--report-json",
        nargs="?",
        const="-",
        help="write a structured JSON report to PATH or stdout with '-'",
    )
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: expected top-level JSON object")
    return payload


def load_bucket_source_domains() -> dict[str, list[str]]:
    bucket_domains: dict[str, list[str]] = {}
    for bucket, path in BUCKET_FILES.items():
        payload = load_json(path)
        rules = payload.get("rules")
        if not isinstance(rules, list):
            raise ValueError(f"{path}: expected 'rules' list")
        domains: list[str] = []
        for rule in rules:
            if not isinstance(rule, dict):
                raise ValueError(f"{path}: invalid rule entry: {rule!r}")
            value = str(rule.get("value", "")).strip().lower()
            if not value:
                raise ValueError(f"{path}: empty value in rule")
            domains.append(value)
        bucket_domains[bucket] = domains
    return bucket_domains


def split_entries(entries: list[str], bucket_domains: dict[str, list[str]]) -> tuple[list[str], list[str], bool]:
    domains: list[str] = []
    ips: list[str] = []
    saw_final = False
    for entry in entries:
        if entry == "final":
            saw_final = True
            continue
        if entry.startswith("source:"):
            bucket = entry.split(":", 1)[1]
            if bucket not in bucket_domains:
                raise ValueError(f"Unknown bucket source: {bucket}")
            domains.extend(f"domain:{domain}" for domain in bucket_domains[bucket])
            continue
        if entry.startswith("ipcidr:"):
            ips.append(entry.split(":", 1)[1])
            continue
        if entry.startswith("geoip:"):
            ips.append(entry)
            continue
        if entry.startswith("domain:") or entry.startswith("geosite:") or entry.startswith("full:"):
            domains.append(entry)
            continue
        raise ValueError(f"Unsupported Streisand profile entry: {entry}")
    return domains, ips, saw_final


def build_route_rule(rule: dict[str, Any], bucket_domains: dict[str, list[str]]) -> dict[str, Any]:
    name = str(rule.get("name", "")).strip()
    entries = rule.get("entries")
    action = str(rule.get("action", "")).strip()
    if not name:
        raise ValueError("Profile rule is missing name")
    if not isinstance(entries, list):
        raise ValueError(f"Profile rule '{name}' is missing entries list")
    if action not in {"direct", "proxy"}:
        raise ValueError(f"Profile rule '{name}' has unsupported action: {action}")

    domains, ips, saw_final = split_entries([str(item).strip() for item in entries], bucket_domains)
    outbound_tag = action
    route_rule: dict[str, Any] = {
        "domainMatcher": "hybrid",
        "domain": domains,
        "ip": ips,
        "outboundTag": outbound_tag,
    }
    if saw_final:
        route_rule["port"] = "0-65535"
        route_rule["domain"] = []
        route_rule["ip"] = []
    return route_rule


def build_plist_payload(profile_path: Path, bucket_domains: dict[str, list[str]]) -> dict[str, Any]:
    profile = load_json(profile_path)
    name = str(profile.get("name", "")).strip()
    rules = profile.get("rules")
    if not name:
        raise ValueError(f"{profile_path}: profile is missing name")
    if not isinstance(rules, list) or not rules:
        raise ValueError(f"{profile_path}: profile is missing rules list")

    return {
        "name": name,
        "uuid": str(uuid.uuid5(uuid.NAMESPACE_URL, f"https://killerloop85.github.io/ios-routing/{profile_path.name}")).upper(),
        "domainStrategy": "AsIs",
        "domainMatcher": "hybrid",
        "rules": [build_route_rule(rule, bucket_domains) for rule in rules],
    }


def encode_streisand_uri(payload: dict[str, Any]) -> str:
    plist_bytes = plistlib.dumps(payload, fmt=plistlib.FMT_BINARY, sort_keys=False)
    inner = base64.b64encode(plist_bytes).decode("ascii")
    wrapper = f"import/route://{inner}".encode("utf-8")
    outer = base64.b64encode(wrapper).decode("ascii")
    return f"streisand://{outer}\n"


def output_path_for_profile(profile_path: Path) -> Path:
    stem = profile_path.name.removesuffix(".json")
    return STREISAND_DIR / f"{stem}.streisand-uri.txt"


def build_outputs() -> dict[Path, str]:
    bucket_domains = load_bucket_source_domains()
    outputs: dict[Path, str] = {}
    for profile_path in PROFILE_FILES:
        payload = build_plist_payload(profile_path, bucket_domains)
        outputs[output_path_for_profile(profile_path)] = encode_streisand_uri(payload)
    return outputs


def build_report(outputs: dict[Path, str], changed_paths: list[Path]) -> dict[str, Any]:
    profile_names: dict[str, str] = {}
    for path, content in outputs.items():
        encoded = content.strip().removeprefix("streisand://")
        wrapper = base64.b64decode(encoded).decode("utf-8")
        plist_payload = plistlib.loads(base64.b64decode(wrapper.split("route://", 1)[1]))
        profile_names[path.name] = str(plist_payload["name"])
    return {
        "files": [path.name for path in sorted(outputs)],
        "changed_files": [path.name for path in changed_paths],
        "profiles": profile_names,
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
        STREISAND_DIR.mkdir(parents=True, exist_ok=True)
        for path, content in outputs.items():
            path.write_text(content, encoding="utf-8")
        if changed_paths:
            print(f"Updated {len(changed_paths)} Streisand URI file(s).", file=status_stream)
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
