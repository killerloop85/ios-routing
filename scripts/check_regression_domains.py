#!/usr/bin/env python3
"""Validate expected routing outcomes for a fixed regression domain set."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "data" / "regression_domains.json"
SHADOWROCKET_DIR = ROOT / "shadowrocket"
STREISAND_DIR = ROOT / "streisand"

DIRECT_PATH = SHADOWROCKET_DIR / "ru-direct.list"
BLOCKED_PATH = SHADOWROCKET_DIR / "ru-blocked-core.list"
FOREIGN_PATH = SHADOWROCKET_DIR / "foreign-services.list"
STREISAND_DIRECT_PATH = STREISAND_DIR / "ru-direct.streisand.json"
STREISAND_BLOCKED_PATH = STREISAND_DIR / "ru-blocked-core.streisand.json"
STREISAND_FOREIGN_PATH = STREISAND_DIR / "foreign-services.streisand.json"


@dataclass(frozen=True)
class RoutingOutcome:
    bucket: str
    rule: str
    matched_suffix: str | None


def load_suffixes(path: Path) -> set[str]:
    suffixes: set[str] = set()
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        prefix = "DOMAIN-SUFFIX,"
        if not line.startswith(prefix):
            raise ValueError(f"{path}: unsupported line format: {raw_line}")
        suffix = line[len(prefix):].strip().lower()
        if not suffix:
            raise ValueError(f"{path}: empty suffix in line: {raw_line}")
        suffixes.add(suffix)
    return suffixes


def match_longest_suffix(domain: str, suffixes: Iterable[str]) -> str | None:
    matches = [suffix for suffix in suffixes if domain == suffix or domain.endswith("." + suffix)]
    if not matches:
        return None
    return max(matches, key=lambda suffix: (suffix.count("."), len(suffix), suffix))


def resolve_domain(domain: str, blocked: set[str], direct: set[str], foreign: set[str]) -> RoutingOutcome:
    blocked_match = match_longest_suffix(domain, blocked)
    if blocked_match:
        return RoutingOutcome(bucket="PROXY", rule="ru-blocked-core", matched_suffix=blocked_match)

    direct_match = match_longest_suffix(domain, direct)
    if direct_match:
        return RoutingOutcome(bucket="DIRECT", rule="ru-direct", matched_suffix=direct_match)

    foreign_match = match_longest_suffix(domain, foreign)
    if foreign_match:
        return RoutingOutcome(bucket="PROXY", rule="foreign-services", matched_suffix=foreign_match)

    return RoutingOutcome(bucket="PROXY", rule="FINAL", matched_suffix=None)


def load_streisand_suffixes(path: Path, expected_action: str, expected_bucket: str) -> set[str]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rules = payload.get("rules")
    if not isinstance(rules, list):
        raise ValueError(f"{path}: missing 'rules' list")

    suffixes: set[str] = set()
    for rule in rules:
        if not isinstance(rule, dict):
            raise ValueError(f"{path}: invalid rule entry: {rule!r}")
        rule_type = str(rule.get("type", "")).strip()
        value = str(rule.get("value", "")).strip().lower()
        action = str(rule.get("action", "")).strip()
        bucket = str(rule.get("bucket", "")).strip()
        if rule_type != "domain_suffix":
            raise ValueError(f"{path}: unsupported rule type: {rule_type}")
        if action != expected_action:
            raise ValueError(f"{path}: unexpected action for {value}: {action}")
        if bucket != expected_bucket:
            raise ValueError(f"{path}: unexpected bucket for {value}: {bucket}")
        if not value:
            raise ValueError(f"{path}: empty value in rule")
        suffixes.add(value)
    return suffixes


def main() -> int:
    payload = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    cases = payload.get("cases", [])
    if not isinstance(cases, list):
        raise ValueError(f"{DATA_PATH}: 'cases' must be a list")

    direct = load_suffixes(DIRECT_PATH)
    blocked = load_suffixes(BLOCKED_PATH)
    foreign = load_suffixes(FOREIGN_PATH)
    streisand_direct = load_streisand_suffixes(
        STREISAND_DIRECT_PATH,
        expected_action="direct",
        expected_bucket="ru-direct",
    )
    streisand_blocked = load_streisand_suffixes(
        STREISAND_BLOCKED_PATH,
        expected_action="proxy",
        expected_bucket="ru-blocked-core",
    )
    streisand_foreign = load_streisand_suffixes(
        STREISAND_FOREIGN_PATH,
        expected_action="proxy",
        expected_bucket="foreign-services",
    )

    failures: list[str] = []
    for item in cases:
        if not isinstance(item, dict):
            raise ValueError(f"{DATA_PATH}: invalid case: {item!r}")
        domain = str(item["domain"]).strip().lower()
        expected_bucket = str(item["expected_bucket"]).strip().upper()
        expected_rule = str(item["expected_rule"]).strip()
        expected_suffix = item.get("expected_suffix")
        expected_suffix = str(expected_suffix).strip().lower() if expected_suffix is not None else None
        actual = resolve_domain(domain, blocked=blocked, direct=direct, foreign=foreign)
        actual_streisand = resolve_domain(
            domain,
            blocked=streisand_blocked,
            direct=streisand_direct,
            foreign=streisand_foreign,
        )
        mismatches: list[str] = []
        if actual.bucket != expected_bucket:
            mismatches.append(f"bucket={actual.bucket} expected={expected_bucket}")
        if actual.rule != expected_rule:
            mismatches.append(f"rule={actual.rule} expected={expected_rule}")
        if expected_suffix is not None and actual.matched_suffix != expected_suffix:
            mismatches.append(
                f"suffix={actual.matched_suffix or '-'} expected={expected_suffix}"
            )
        if actual_streisand != actual:
            mismatches.append(
                "streisand="
                f"{actual_streisand.rule}/{actual_streisand.bucket}/{actual_streisand.matched_suffix or '-'} "
                "shadowrocket="
                f"{actual.rule}/{actual.bucket}/{actual.matched_suffix or '-'}"
            )
        if mismatches:
            failures.append(f"{domain}: " + ", ".join(mismatches))

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        print(f"Regression check failed: {len(failures)} case(s) mismatched.", file=sys.stderr)
        return 1

    print(f"Regression check passed: {len(cases)} case(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
