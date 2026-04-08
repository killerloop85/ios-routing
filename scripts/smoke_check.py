#!/usr/bin/env python3
"""Basic repository smoke checks for routing data and generated lists."""

from __future__ import annotations

import json
import plistlib
import re
import subprocess
import sys
import base64
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
SHADOWROCKET_DIR = ROOT / "shadowrocket"
STREISAND_DIR = ROOT / "streisand"
HIDDIFY_DIR = ROOT / "hiddify"
HAPP_DIR = ROOT / "happ"
UPDATER = ROOT / "scripts" / "update_routing_lists.py"
STREISAND_EXPORTER = ROOT / "scripts" / "export_streisand_rules.py"
STREISAND_URI_EXPORTER = ROOT / "scripts" / "export_streisand_uri.py"
HIDDIFY_EXPORTER = ROOT / "scripts" / "export_hiddify_rules.py"
HAPP_EXPORTER = ROOT / "scripts" / "export_happ_routing.py"
REGRESSION_CHECK = ROOT / "scripts" / "check_regression_domains.py"

LIST_FILES = (
    SHADOWROCKET_DIR / "ru-direct.list",
    SHADOWROCKET_DIR / "ru-blocked-core.list",
    SHADOWROCKET_DIR / "foreign-services.list",
)
STREISAND_FILES = (
    STREISAND_DIR / "ru-direct.streisand.json",
    STREISAND_DIR / "ru-blocked-core.streisand.json",
    STREISAND_DIR / "foreign-services.streisand.json",
    STREISAND_DIR / "routing-profile-split.json",
    STREISAND_DIR / "routing-profile-split-qr.json",
    STREISAND_DIR / "routing-profile-full.json",
)
STREISAND_URI_FILES = (
    STREISAND_DIR / "routing-profile-split-qr.streisand-uri.txt",
    STREISAND_DIR / "routing-profile-full.streisand-uri.txt",
)
HIDDIFY_FILES = (
    HIDDIFY_DIR / "ru-direct.hiddify.json",
    HIDDIFY_DIR / "ru-blocked-core.hiddify.json",
    HIDDIFY_DIR / "foreign-services.hiddify.json",
    HIDDIFY_DIR / "routing-profile-split.json",
    HIDDIFY_DIR / "routing-profile-full.json",
)
HAPP_FILES = (
    HAPP_DIR / "routing-profile-split.json",
    HAPP_DIR / "routing-profile-split-direct-default.json",
    HAPP_DIR / "routing-profile-full.json",
)

LIST_LINE_RE = re.compile(
    r"^DOMAIN-SUFFIX,([a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?(?:\.[a-zа-я0-9-]{2,})*)$",
    re.IGNORECASE,
)


def find_parent_conflicts(domains: list[str]) -> list[tuple[str, str]]:
    ordered = sorted(set(domains), key=lambda item: (item.count("."), item))
    conflicts: list[tuple[str, str]] = []
    parents: list[str] = []
    for domain in ordered:
        for parent in parents:
            if domain.endswith("." + parent):
                conflicts.append((parent, domain))
                break
        parents.append(domain)
    return conflicts


def validate_json_files() -> None:
    for path in sorted(DATA_DIR.glob("*.json")):
        with path.open("r", encoding="utf-8") as handle:
            json.load(handle)


def validate_manual_core_conflicts() -> None:
    for path in sorted(DATA_DIR.glob("manual_*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        sections = payload.get("sections", {})
        domains: list[str] = []
        if isinstance(sections, dict):
            for section_domains in sections.values():
                if isinstance(section_domains, list):
                    domains.extend(str(domain) for domain in section_domains)
        conflicts = find_parent_conflicts(domains)
        if conflicts:
            rendered = ", ".join(f"{parent} -> {child}" for parent, child in conflicts)
            raise ValueError(f"{path}: manual core parent/subdomain conflicts: {rendered}")


def validate_list_file(path: Path) -> None:
    seen: set[str] = set()
    for lineno, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        match = LIST_LINE_RE.fullmatch(line)
        if not match:
            raise ValueError(f"{path}:{lineno}: invalid list line: {raw_line}")
        domain = match.group(1).lower()
        if domain in seen:
            raise ValueError(f"{path}:{lineno}: duplicate domain: {domain}")
        seen.add(domain)


def validate_streisand_file(path: Path) -> None:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: top-level object must be a JSON object")
    if not isinstance(payload.get("name"), str) or not payload["name"].strip():
        raise ValueError(f"{path}: missing or empty 'name'")
    if not isinstance(payload.get("description"), str) or not payload["description"].strip():
        raise ValueError(f"{path}: missing or empty 'description'")

    rules = payload.get("rules")
    if rules is None:
        priority = payload.get("priority")
        sources = payload.get("sources")
        final_action = payload.get("final_action")
        if not isinstance(priority, list) or not priority:
            raise ValueError(f"{path}: profile is missing non-empty 'priority'")
        if not isinstance(sources, list):
            raise ValueError(f"{path}: profile is missing 'sources' list")
        if final_action != "proxy":
            raise ValueError(f"{path}: profile has unexpected final_action: {final_action}")
        return
    if not isinstance(rules, list):
        raise ValueError(f"{path}: 'rules' must be a list")

    if "routing-profile-" in path.name:
        priority = payload.get("priority")
        sources = payload.get("sources")
        final_action = payload.get("final_action")
        if not isinstance(priority, list) or not priority:
            raise ValueError(f"{path}: profile is missing non-empty 'priority'")
        if not isinstance(sources, list):
            raise ValueError(f"{path}: profile is missing 'sources' list")
        if final_action != "proxy":
            raise ValueError(f"{path}: profile has unexpected final_action: {final_action}")
        for rule in rules:
            if not isinstance(rule, dict):
                raise ValueError(f"{path}: invalid profile rule entry: {rule!r}")
            name = str(rule.get("name", "")).strip()
            entries = rule.get("entries")
            action = str(rule.get("action", "")).strip()
            bucket = str(rule.get("bucket", "")).strip()
            if not name:
                raise ValueError(f"{path}: profile rule is missing 'name'")
            if not isinstance(entries, list) or not entries:
                raise ValueError(f"{path}: profile rule '{name}' is missing non-empty 'entries'")
            if action not in {"direct", "proxy"}:
                raise ValueError(f"{path}: profile rule '{name}' has unsupported action: {action}")
            if not bucket:
                raise ValueError(f"{path}: profile rule '{name}' is missing bucket")
        return

    seen: set[str] = set()
    for rule in rules:
        if not isinstance(rule, dict):
            raise ValueError(f"{path}: invalid rule entry: {rule!r}")
        rule_type = str(rule.get("type", "")).strip()
        value = str(rule.get("value", "")).strip().lower()
        action = str(rule.get("action", "")).strip()
        bucket = str(rule.get("bucket", "")).strip()
        if rule_type != "domain_suffix":
            raise ValueError(f"{path}: unsupported rule type: {rule_type}")
        if action not in {"direct", "proxy"}:
            raise ValueError(f"{path}: unsupported action: {action}")
        if not bucket:
            raise ValueError(f"{path}: missing bucket for {value or '<empty>'}")
        if not value:
            raise ValueError(f"{path}: empty value in rule")
        if value in seen:
            raise ValueError(f"{path}: duplicate rule value: {value}")
        seen.add(value)


def validate_streisand_uri_file(path: Path) -> None:
    raw = path.read_text(encoding="utf-8").strip()
    if not raw.startswith("streisand://"):
        raise ValueError(f"{path}: missing streisand:// prefix")
    wrapper_bytes = base64.b64decode(raw.removeprefix("streisand://"))
    wrapper = wrapper_bytes.decode("utf-8")
    if not wrapper.startswith("import/route://"):
        raise ValueError(f"{path}: missing import/route:// wrapper")
    plist_payload = plistlib.loads(base64.b64decode(wrapper.split("route://", 1)[1]))
    if not isinstance(plist_payload, dict):
        raise ValueError(f"{path}: decoded payload is not a plist dict")
    if not str(plist_payload.get("name", "")).strip():
        raise ValueError(f"{path}: decoded payload is missing name")
    if not str(plist_payload.get("uuid", "")).strip():
        raise ValueError(f"{path}: decoded payload is missing uuid")
    if str(plist_payload.get("domainStrategy", "")) != "AsIs":
        raise ValueError(f"{path}: unexpected domainStrategy")
    if str(plist_payload.get("domainMatcher", "")) != "hybrid":
        raise ValueError(f"{path}: unexpected domainMatcher")
    rules = plist_payload.get("rules")
    if not isinstance(rules, list) or not rules:
        raise ValueError(f"{path}: decoded payload is missing rules")
    for rule in rules:
        if not isinstance(rule, dict):
            raise ValueError(f"{path}: invalid plist rule entry: {rule!r}")
        if str(rule.get("outboundTag", "")).strip() not in {"direct", "proxy", "block"}:
            raise ValueError(f"{path}: invalid outboundTag in decoded rule")
        domain = rule.get("domain")
        ip = rule.get("ip")
        if domain is not None and not isinstance(domain, list):
            raise ValueError(f"{path}: decoded rule domain must be a list")
        if ip is not None and not isinstance(ip, list):
            raise ValueError(f"{path}: decoded rule ip must be a list")
        if not domain and not ip and str(rule.get("port", "")).strip() != "0-65535":
            raise ValueError(f"{path}: decoded final rule is missing 0-65535 port")
    if path.name == "routing-profile-split-qr.streisand-uri.txt" and path.stat().st_size >= 2953:
        raise ValueError(f"{path}: compact QR URI is too large for a practical single QR")


def validate_hiddify_file(path: Path) -> None:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: top-level object must be a JSON object")
    if not isinstance(payload.get("name"), str) or not payload["name"].strip():
        raise ValueError(f"{path}: missing or empty 'name'")
    if not isinstance(payload.get("description"), str) or not payload["description"].strip():
        raise ValueError(f"{path}: missing or empty 'description'")
    if payload.get("platform") != "hiddify":
        raise ValueError(f"{path}: unexpected platform: {payload.get('platform')!r}")
    rules = payload.get("rules")
    if not isinstance(rules, list) or not rules:
        raise ValueError(f"{path}: 'rules' must be a non-empty list")

    if path.name.endswith(".hiddify.json"):
        seen: set[str] = set()
        for rule in rules:
            if not isinstance(rule, dict):
                raise ValueError(f"{path}: invalid rule entry: {rule!r}")
            rule_type = str(rule.get("type", "")).strip()
            value = str(rule.get("value", "")).strip().lower()
            outbound = str(rule.get("outbound", "")).strip()
            bucket = str(rule.get("bucket", "")).strip()
            if rule_type != "domain_suffix":
                raise ValueError(f"{path}: unsupported rule type: {rule_type}")
            if not value:
                raise ValueError(f"{path}: empty value in rule")
            if outbound not in {"direct", "proxy", "block"}:
                raise ValueError(f"{path}: unsupported outbound: {outbound}")
            if not bucket:
                raise ValueError(f"{path}: missing bucket for {value or '<empty>'}")
            if value in seen:
                raise ValueError(f"{path}: duplicate rule value: {value}")
            seen.add(value)
        return

    saw_local_direct = False
    saw_final_proxy = False
    for rule in rules:
        if not isinstance(rule, dict):
            raise ValueError(f"{path}: invalid profile rule entry: {rule!r}")
        name = str(rule.get("name", "")).strip()
        bucket = str(rule.get("bucket", "")).strip()
        outbound = str(rule.get("outbound", "")).strip()
        entries = rule.get("entries")
        if not name:
            raise ValueError(f"{path}: profile rule is missing 'name'")
        if not bucket:
            raise ValueError(f"{path}: profile rule '{name}' is missing bucket")
        if outbound not in {"direct", "proxy", "block"}:
            raise ValueError(f"{path}: profile rule '{name}' has unsupported outbound: {outbound}")
        if not isinstance(entries, list) or not entries:
            raise ValueError(f"{path}: profile rule '{name}' is missing non-empty 'entries'")
        if bucket == "local" and outbound == "direct":
            saw_local_direct = True
        if bucket == "final" and outbound == "proxy":
            saw_final_proxy = True
        for entry in entries:
            if not isinstance(entry, dict):
                raise ValueError(f"{path}: profile rule '{name}' has invalid entry: {entry!r}")
            entry_type = str(entry.get("type", "")).strip()
            value = str(entry.get("value", "")).strip()
            if entry_type not in {"domain_suffix", "domain", "ip_cidr", "geoip", "geosite", "final", "source"}:
                raise ValueError(f"{path}: profile rule '{name}' has unsupported entry type: {entry_type}")
            if not value:
                raise ValueError(f"{path}: profile rule '{name}' has empty entry value")
    if not saw_local_direct:
        raise ValueError(f"{path}: missing local/private direct block")
    if not saw_final_proxy:
        raise ValueError(f"{path}: missing final proxy block")


def validate_hiddify_sync() -> None:
    expected_counts = {
        HIDDIFY_DIR / "ru-direct.hiddify.json": sum(
            1 for line in (SHADOWROCKET_DIR / "ru-direct.list").read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.strip().startswith("#")
        ),
        HIDDIFY_DIR / "ru-blocked-core.hiddify.json": sum(
            1 for line in (SHADOWROCKET_DIR / "ru-blocked-core.list").read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.strip().startswith("#")
        ),
        HIDDIFY_DIR / "foreign-services.hiddify.json": sum(
            1 for line in (SHADOWROCKET_DIR / "foreign-services.list").read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.strip().startswith("#")
        ),
    }
    for path, expected_count in expected_counts.items():
        payload = json.loads(path.read_text(encoding="utf-8"))
        rules = payload.get("rules")
        if not isinstance(rules, list):
            raise ValueError(f"{path}: missing rules list for sync check")
        if len(rules) != expected_count:
            raise ValueError(f"{path}: rules count {len(rules)} does not match source count {expected_count}")


def validate_happ_file(path: Path) -> None:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: top-level object must be a JSON object")
    if not isinstance(payload.get("name"), str) or not payload["name"].strip():
        raise ValueError(f"{path}: missing or empty 'name'")
    if not isinstance(payload.get("description"), str) or not payload["description"].strip():
        raise ValueError(f"{path}: missing or empty 'description'")
    if payload.get("platform") != "happ":
        raise ValueError(f"{path}: unexpected platform: {payload.get('platform')!r}")
    if not isinstance(payload.get("globalProxy"), bool):
        raise ValueError(f"{path}: missing boolean globalProxy")
    if not isinstance(payload.get("routeOrder"), str) or not payload["routeOrder"].strip():
        raise ValueError(f"{path}: missing routeOrder")
    for block_name in ("direct", "proxy", "block"):
        block = payload.get(block_name)
        if not isinstance(block, dict):
            raise ValueError(f"{path}: missing {block_name} block")
        domains = block.get("domains")
        ip_cidrs = block.get("ip_cidrs")
        if not isinstance(domains, list) or not all(isinstance(item, str) and item.strip() for item in domains):
            raise ValueError(f"{path}: {block_name}.domains must be a list of non-empty strings")
        if not isinstance(ip_cidrs, list) or not all(isinstance(item, str) and item.strip() for item in ip_cidrs):
            raise ValueError(f"{path}: {block_name}.ip_cidrs must be a list of non-empty strings")
    if path.name == "routing-profile-split.json":
        direct_domains = set(payload["direct"]["domains"])
        proxy_domains = set(payload["proxy"]["domains"])
        for required in {"localhost", "local", "captive.apple.com"}:
            if required not in direct_domains:
                raise ValueError(f"{path}: missing local direct domain {required}")
        if not payload["globalProxy"]:
            raise ValueError(f"{path}: split profile must keep proxy-default fallback for parity with routing core")
        if not proxy_domains:
            raise ValueError(f"{path}: split profile has empty proxy.domains")
    if path.name == "routing-profile-split-direct-default.json":
        direct_domains = set(payload["direct"]["domains"])
        proxy_domains = set(payload["proxy"]["domains"])
        for required in {"localhost", "local", "captive.apple.com"}:
            if required not in direct_domains:
                raise ValueError(f"{path}: missing local direct domain {required}")
        if payload["globalProxy"]:
            raise ValueError(f"{path}: direct-default split profile must keep globalProxy=false")
        if not proxy_domains:
            raise ValueError(f"{path}: direct-default split profile has empty proxy.domains")
    if path.name == "routing-profile-full.json":
        if not payload["globalProxy"]:
            raise ValueError(f"{path}: full profile must keep globalProxy=true")
        if payload["proxy"]["domains"]:
            raise ValueError(f"{path}: full profile should not need explicit proxy domains")


def validate_happ_sync() -> None:
    split_payload = json.loads((HAPP_DIR / "routing-profile-split.json").read_text(encoding="utf-8"))
    direct_domains = {str(item).strip().lower() for item in split_payload["direct"]["domains"]}
    proxy_domains = {str(item).strip().lower() for item in split_payload["proxy"]["domains"]}
    source_direct = {
        line.split(",", 1)[1].strip().lower()
        for line in (SHADOWROCKET_DIR / "ru-direct.list").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    }
    source_proxy = {
        line.split(",", 1)[1].strip().lower()
        for source_path in (
            SHADOWROCKET_DIR / "ru-blocked-core.list",
            SHADOWROCKET_DIR / "foreign-services.list",
        )
        for line in source_path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    }
    if not source_direct.issubset(direct_domains):
        missing = sorted(source_direct - direct_domains)[:10]
        raise ValueError(f"happ/routing-profile-split.json: missing direct domains from source lists: {missing}")
    if not source_proxy.issubset(proxy_domains):
        missing = sorted(source_proxy - proxy_domains)[:10]
        raise ValueError(f"happ/routing-profile-split.json: missing proxy domains from source lists: {missing}")


def run_offline_updater() -> None:
    result = subprocess.run(
        [sys.executable, str(UPDATER), "--offline"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr or result.stdout or "offline updater failed")
    if result.stdout.strip() != "No changes.":
        raise RuntimeError(f"offline updater is not stable:\n{result.stdout}")


def run_regression_check() -> None:
    result = subprocess.run(
        [sys.executable, str(REGRESSION_CHECK)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr or result.stdout or "regression check failed")


def run_streisand_export_check() -> None:
    result = subprocess.run(
        [sys.executable, str(STREISAND_EXPORTER), "--offline"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr or result.stdout or "streisand export failed")
    if result.stdout.strip() != "No changes.":
        raise RuntimeError(f"streisand export is not stable:\n{result.stdout}")


def run_streisand_uri_export_check() -> None:
    result = subprocess.run(
        [sys.executable, str(STREISAND_URI_EXPORTER), "--offline"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr or result.stdout or "streisand URI export failed")
    if result.stdout.strip() != "No changes.":
        raise RuntimeError(f"streisand URI export is not stable:\n{result.stdout}")


def run_hiddify_export_check() -> None:
    result = subprocess.run(
        [sys.executable, str(HIDDIFY_EXPORTER), "--offline"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr or result.stdout or "hiddify export failed")
    if result.stdout.strip() != "No changes.":
        raise RuntimeError(f"hiddify export is not stable:\n{result.stdout}")


def run_happ_export_check() -> None:
    result = subprocess.run(
        [sys.executable, str(HAPP_EXPORTER), "--offline"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr or result.stdout or "happ export failed")
    if result.stdout.strip() != "No changes.":
        raise RuntimeError(f"happ export is not stable:\n{result.stdout}")


def main() -> int:
    validate_json_files()
    validate_manual_core_conflicts()
    for path in LIST_FILES:
        validate_list_file(path)
    run_offline_updater()
    run_streisand_export_check()
    run_streisand_uri_export_check()
    run_hiddify_export_check()
    run_happ_export_check()
    for path in STREISAND_FILES:
        validate_streisand_file(path)
    for path in STREISAND_URI_FILES:
        validate_streisand_uri_file(path)
    for path in HIDDIFY_FILES:
        validate_hiddify_file(path)
    validate_hiddify_sync()
    for path in HAPP_FILES:
        validate_happ_file(path)
    validate_happ_sync()
    run_regression_check()
    print("Smoke check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
