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
CLASH_DIR = ROOT / "clash"
OFFICE_DIR = ROOT / "office"
OFFICE_SINGBOX_DIR = OFFICE_DIR / "sing-box" / "generated"
UPDATER = ROOT / "scripts" / "update_routing_lists.py"
STREISAND_EXPORTER = ROOT / "scripts" / "export_streisand_rules.py"
STREISAND_URI_EXPORTER = ROOT / "scripts" / "export_streisand_uri.py"
HIDDIFY_EXPORTER = ROOT / "scripts" / "export_hiddify_rules.py"
HAPP_EXPORTER = ROOT / "scripts" / "export_happ_routing.py"
CLASH_EXPORTER = ROOT / "scripts" / "export_clash_rules.py"
OFFICE_EXPORTER = ROOT / "scripts" / "export_office_singbox.py"
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
CLASH_FILES = (
    CLASH_DIR / "ru-direct.rules.yaml",
    CLASH_DIR / "ru-blocked-core.rules.yaml",
    CLASH_DIR / "foreign-services.rules.yaml",
    CLASH_DIR / "routing-profile-full.yaml",
    CLASH_DIR / "routing-profile-split.yaml",
    CLASH_DIR / "routing-profile-split-direct-default.yaml",
)
OFFICE_FILES = (
    OFFICE_SINGBOX_DIR / "config.split.generated.json",
    OFFICE_SINGBOX_DIR / "config.full.generated.json",
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
        stability = str(payload.get("stability", "")).strip()
        intended_use = str(payload.get("intended_use", "")).strip()
        if not isinstance(priority, list) or not priority:
            raise ValueError(f"{path}: profile is missing non-empty 'priority'")
        if not isinstance(sources, list):
            raise ValueError(f"{path}: profile is missing 'sources' list")
        if final_action != "proxy":
            raise ValueError(f"{path}: profile has unexpected final_action: {final_action}")
        if path.name == "routing-profile-full.json":
            if stability != "stable" or intended_use != "production":
                raise ValueError(f"{path}: full profile must be marked stable/production")
        elif path.name in {"routing-profile-split.json", "routing-profile-split-qr.json"}:
            if stability != "experimental":
                raise ValueError(f"{path}: split profile must be marked experimental")
            if path.name == "routing-profile-split.json" and intended_use != "reference-only":
                raise ValueError(f"{path}: heavy split profile must be marked reference-only")
            if path.name == "routing-profile-split-qr.json" and intended_use != "diagnostic":
                raise ValueError(f"{path}: compact split profile must be marked diagnostic")
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


def unquote_yaml_scalar(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        if value[0] == '"':
            return str(json.loads(value))
        return value[1:-1]
    return value


def parse_clash_yaml(path: Path) -> tuple[dict[str, str], list[str]]:
    scalars: dict[str, str] = {}
    rules: list[str] = []
    in_rules = False
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if not in_rules:
            if stripped == "rules:":
                in_rules = True
                continue
            if ":" in stripped and not line.startswith("  - ") and not line.startswith("    "):
                key, value = stripped.split(":", 1)
                scalars[key.strip()] = unquote_yaml_scalar(value)
            continue
        if line.startswith("  - "):
            rules.append(unquote_yaml_scalar(line.split("- ", 1)[1]))
    if not rules:
        raise ValueError(f"{path}: missing rules list")
    return scalars, rules


def validate_clash_file(path: Path) -> None:
    scalars, rules = parse_clash_yaml(path)
    if path.name.endswith(".rules.yaml"):
        if "rules" in scalars:
            raise ValueError(f"{path}: unexpected scalar 'rules'")
        for rule in rules:
            if not rule.startswith("DOMAIN-SUFFIX,"):
                raise ValueError(f"{path}: unsupported bucket rule: {rule}")
            parts = [part.strip() for part in rule.split(",")]
            if len(parts) != 3:
                raise ValueError(f"{path}: malformed bucket rule: {rule}")
            if parts[2] not in {"DIRECT", "PROXY"}:
                raise ValueError(f"{path}: unsupported action in bucket rule: {rule}")
        return

    required_scalars = {
        "port",
        "socks-port",
        "mode",
        "allow-lan",
        "log-level",
        "proxies",
        "proxy-groups",
    }
    missing = sorted(key for key in required_scalars if key not in scalars)
    if missing:
        raise ValueError(f"{path}: missing profile keys: {missing}")
    if scalars["mode"] != "Rule":
        raise ValueError(f"{path}: unexpected mode {scalars['mode']}")
    if scalars["allow-lan"] != "true":
        raise ValueError(f"{path}: allow-lan must be true")
    if not any(rule == "MATCH,PROXY" or rule == "MATCH,DIRECT" for rule in rules):
        raise ValueError(f"{path}: missing MATCH fallback")
    if not any(rule.startswith("DOMAIN,localhost,DIRECT") for rule in rules):
        raise ValueError(f"{path}: missing localhost direct rule")
    if not any(rule.startswith("IP-CIDR,10.0.0.0/8,DIRECT") for rule in rules):
        raise ValueError(f"{path}: missing local/private IP rule")
    if path.name == "routing-profile-full.yaml" and rules[-1] != "MATCH,PROXY":
        raise ValueError(f"{path}: full profile must end with MATCH,PROXY")
    if path.name == "routing-profile-split.yaml":
        if rules[-1] != "MATCH,PROXY":
            raise ValueError(f"{path}: parity split profile must end with MATCH,PROXY")
        if not any(rule == "GEOIP,RU,DIRECT,no-resolve" for rule in rules):
            raise ValueError(f"{path}: split profile is missing GEOIP,RU,DIRECT,no-resolve")
    if path.name == "routing-profile-split-direct-default.yaml":
        if rules[-1] != "MATCH,DIRECT":
            raise ValueError(f"{path}: direct-default split profile must end with MATCH,DIRECT")
        if not any(rule == "GEOIP,RU,DIRECT,no-resolve" for rule in rules):
            raise ValueError(f"{path}: direct-default split profile is missing GEOIP,RU,DIRECT,no-resolve")


def validate_clash_sync() -> None:
    expected_counts = {
        CLASH_DIR / "ru-direct.rules.yaml": sum(
            1 for line in (SHADOWROCKET_DIR / "ru-direct.list").read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.strip().startswith("#")
        ),
        CLASH_DIR / "ru-blocked-core.rules.yaml": sum(
            1 for line in (SHADOWROCKET_DIR / "ru-blocked-core.list").read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.strip().startswith("#")
        ),
        CLASH_DIR / "foreign-services.rules.yaml": sum(
            1 for line in (SHADOWROCKET_DIR / "foreign-services.list").read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.strip().startswith("#")
        ),
    }
    for path, expected_count in expected_counts.items():
        _, rules = parse_clash_yaml(path)
        if len(rules) != expected_count:
            raise ValueError(f"{path}: rules count {len(rules)} does not match source count {expected_count}")


def validate_office_file(path: Path) -> None:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: top-level object must be a JSON object")
    for key in ("dns", "inbounds", "outbounds", "route"):
        if key not in payload:
            raise ValueError(f"{path}: missing {key}")
    route = payload.get("route")
    if not isinstance(route, dict):
        raise ValueError(f"{path}: route must be an object")
    if route.get("final") != "proxy":
        raise ValueError(f"{path}: route.final must be proxy")
    rules = route.get("rules")
    if not isinstance(rules, list) or not rules:
        raise ValueError(f"{path}: missing non-empty route.rules")
    saw_local_ip_rule = False
    saw_local_domain_rule = False
    saw_direct_suffixes = False
    saw_proxy_suffixes = False
    for rule in rules:
        if not isinstance(rule, dict):
            raise ValueError(f"{path}: invalid route rule: {rule!r}")
        ip_cidr = rule.get("ip_cidr")
        domain = rule.get("domain")
        domain_suffix = rule.get("domain_suffix")
        outbound = str(rule.get("outbound", "")).strip()
        if outbound not in {"direct", "proxy", "block"}:
            raise ValueError(f"{path}: unsupported outbound in route rule: {outbound}")
        if ip_cidr is not None:
            if not isinstance(ip_cidr, list) or not all(isinstance(item, str) and item.strip() for item in ip_cidr):
                raise ValueError(f"{path}: ip_cidr rule must be a list of non-empty strings")
            if "10.77.221.0/24" in ip_cidr and outbound == "direct":
                saw_local_ip_rule = True
        if domain is not None:
            if not isinstance(domain, list) or not all(isinstance(item, str) and item.strip() for item in domain):
                raise ValueError(f"{path}: domain rule must be a list of non-empty strings")
            if "localhost" in domain and outbound == "direct":
                saw_local_domain_rule = True
        if domain_suffix is not None:
            if not isinstance(domain_suffix, list) or not all(isinstance(item, str) and item.strip() for item in domain_suffix):
                raise ValueError(f"{path}: domain_suffix rule must be a list of non-empty strings")
            if outbound == "direct":
                saw_direct_suffixes = True
            if outbound == "proxy":
                saw_proxy_suffixes = True
    if not saw_local_ip_rule:
        raise ValueError(f"{path}: missing office LAN direct IP rule")
    if not saw_local_domain_rule:
        raise ValueError(f"{path}: missing localhost direct rule")
    if not saw_direct_suffixes:
        raise ValueError(f"{path}: missing direct domain_suffix rule")
    if path.name == "config.split.generated.json" and not saw_proxy_suffixes:
        raise ValueError(f"{path}: split config must include proxy domain_suffix rules")


def validate_office_sync() -> None:
    split_payload = json.loads((OFFICE_SINGBOX_DIR / "config.split.generated.json").read_text(encoding="utf-8"))
    rules = split_payload["route"]["rules"]
    direct_suffixes: set[str] = set()
    proxy_suffixes: set[str] = set()
    for rule in rules:
        suffixes = rule.get("domain_suffix")
        if not isinstance(suffixes, list):
            continue
        if rule.get("outbound") == "direct":
            direct_suffixes.update(str(item).strip().lower() for item in suffixes)
        if rule.get("outbound") == "proxy":
            proxy_suffixes.update(str(item).strip().lower() for item in suffixes)
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
    if not source_direct.issubset(direct_suffixes):
        missing = sorted(source_direct - direct_suffixes)[:10]
        raise ValueError(f"office/sing-box/generated/config.split.generated.json: missing direct suffixes: {missing}")
    if not source_proxy.issubset(proxy_suffixes):
        missing = sorted(source_proxy - proxy_suffixes)[:10]
        raise ValueError(f"office/sing-box/generated/config.split.generated.json: missing proxy suffixes: {missing}")


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
    for command in (
        [sys.executable, str(STREISAND_EXPORTER), "--offline"],
        [sys.executable, str(STREISAND_EXPORTER), "--offline", "--experimental-split"],
    ):
        result = subprocess.run(
            command,
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
    for command in (
        [sys.executable, str(STREISAND_URI_EXPORTER), "--offline"],
        [sys.executable, str(STREISAND_URI_EXPORTER), "--offline", "--experimental-split"],
    ):
        result = subprocess.run(
            command,
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


def run_clash_export_check() -> None:
    for command in (
        [sys.executable, str(CLASH_EXPORTER), "--offline"],
        [sys.executable, str(CLASH_EXPORTER), "--offline", "--profile", "split", "--profile", "split-direct-default"],
    ):
        result = subprocess.run(
            command,
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr or result.stdout or "clash export failed")
        if result.stdout.strip() != "No changes.":
            raise RuntimeError(f"clash export is not stable:\n{result.stdout}")


def run_office_export_check() -> None:
    result = subprocess.run(
        [sys.executable, str(OFFICE_EXPORTER), "--offline"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr or result.stdout or "office export failed")
    if result.stdout.strip() != "No changes.":
        raise RuntimeError(f"office export is not stable:\n{result.stdout}")


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
    run_clash_export_check()
    run_office_export_check()
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
    for path in CLASH_FILES:
        validate_clash_file(path)
    validate_clash_sync()
    for path in OFFICE_FILES:
        validate_office_file(path)
    validate_office_sync()
    run_regression_check()
    print("Smoke check passed.")
    print("Note: Streisand split artifacts are validated only as experimental local exports; real client behavior is not guaranteed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
