#!/usr/bin/env python3
"""Basic repository smoke checks for routing data and generated lists."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
SHADOWROCKET_DIR = ROOT / "shadowrocket"
STREISAND_DIR = ROOT / "streisand"
UPDATER = ROOT / "scripts" / "update_routing_lists.py"
STREISAND_EXPORTER = ROOT / "scripts" / "export_streisand_rules.py"
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
    STREISAND_DIR / "routing-profile-full.json",
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


def main() -> int:
    validate_json_files()
    validate_manual_core_conflicts()
    for path in LIST_FILES:
        validate_list_file(path)
    run_offline_updater()
    run_streisand_export_check()
    for path in STREISAND_FILES:
        validate_streisand_file(path)
    run_regression_check()
    print("Smoke check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
