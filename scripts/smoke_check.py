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
UPDATER = ROOT / "scripts" / "update_routing_lists.py"
REGRESSION_CHECK = ROOT / "scripts" / "check_regression_domains.py"

LIST_FILES = (
    SHADOWROCKET_DIR / "ru-direct.list",
    SHADOWROCKET_DIR / "ru-blocked-core.list",
    SHADOWROCKET_DIR / "foreign-services.list",
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


def main() -> int:
    validate_json_files()
    validate_manual_core_conflicts()
    for path in LIST_FILES:
        validate_list_file(path)
    run_offline_updater()
    run_regression_check()
    print("Smoke check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
