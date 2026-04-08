#!/usr/bin/env python3
"""Update Shadowrocket routing lists from curated cores and external sources.

This script implements the repository spec from docs/routing-update-spec.md.
It favors conservative output and can run in offline mode using only the
manual core domains defined below.
"""

from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Set


ROOT = Path(__file__).resolve().parent.parent
SHADOWROCKET_DIR = ROOT / "shadowrocket"
DATA_DIR = ROOT / "data"

DIRECT_PATH = SHADOWROCKET_DIR / "ru-direct.list"
BLOCKED_PATH = SHADOWROCKET_DIR / "ru-blocked-core.list"
FOREIGN_PATH = SHADOWROCKET_DIR / "foreign-services.list"


@dataclass(frozen=True)
class Source:
    name: str
    url: str
    bucket: str
    kind: str = "text"
    priority: int = 50
    notes: str = ""
    exclude_domains: tuple[str, ...] = ()
    optional: bool = True


@dataclass
class Candidate:
    domain: str
    sources: Set[str] = field(default_factory=set)
    source_priorities: Dict[str, int] = field(default_factory=dict)
    manual: bool = False

    def total_priority(self) -> int:
        return sum(self.source_priorities.values())

    def score(self) -> tuple[int, int, int, str]:
        return (1 if self.manual else 0, self.total_priority(), len(self.sources), self.domain)


DOMAIN_RE = re.compile(r"\b(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-zа-я0-9-]{2,}\b", re.IGNORECASE)


@dataclass(frozen=True)
class ManualList:
    header: List[str]
    sections: Dict[str, List[str]]
    tail_comment: str | None = None
    tail_domains: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class RoutingConfig:
    direct_limit: int
    blocked_limit: int
    foreign_limit: int
    ru_tlds: tuple[str, ...]
    direct_always_keep: Set[str]
    direct_override: Set[str]
    sources: Sequence[Source]


def find_parent_conflicts(domains: Iterable[str]) -> list[tuple[str, str]]:
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


def flatten_sections(sections: Dict[str, List[str]]) -> Set[str]:
    values: Set[str] = set()
    for domains in sections.values():
        values.update(domains)
    return values


def load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def load_manual_list(path: Path) -> ManualList:
    raw = load_json(path)
    assert isinstance(raw, dict)
    header = [str(item) for item in raw.get("header", [])]
    raw_sections = raw.get("sections", {})
    if not isinstance(raw_sections, dict):
        raise ValueError(f"Invalid sections in {path}")
    sections = {
        str(section): [str(domain) for domain in domains]
        for section, domains in raw_sections.items()
    }
    conflicts = find_parent_conflicts(flatten_sections(sections))
    if conflicts:
        rendered = ", ".join(f"{parent} -> {child}" for parent, child in conflicts)
        raise ValueError(f"Manual list contains parent/subdomain conflicts in {path}: {rendered}")
    tail_comment = raw.get("tail_comment")
    tail_domains = [str(item) for item in raw.get("tail_domains", [])]
    return ManualList(
        header=header,
        sections=sections,
        tail_comment=str(tail_comment) if tail_comment is not None else None,
        tail_domains=tail_domains,
    )


def load_routing_config(path: Path) -> RoutingConfig:
    raw = load_json(path)
    assert isinstance(raw, dict)
    sources = tuple(
        Source(
            name=str(item["name"]),
            url=str(item["url"]),
            bucket=str(item["bucket"]),
            kind=str(item.get("kind", "text")),
            priority=int(item.get("priority", 50)),
            notes=str(item.get("notes", "")),
            exclude_domains=tuple(str(domain) for domain in item.get("exclude_domains", [])),
            optional=bool(item.get("optional", True)),
        )
        for item in raw.get("sources", [])
    )
    return RoutingConfig(
        direct_limit=int(raw["direct_limit"]),
        blocked_limit=int(raw["blocked_limit"]),
        foreign_limit=int(raw["foreign_limit"]),
        ru_tlds=tuple(str(item) for item in raw["ru_tlds"]),
        direct_always_keep={str(item) for item in raw.get("direct_always_keep", [])},
        direct_override={str(item) for item in raw.get("direct_override", [])},
        sources=sources,
    )


MANUAL_DIRECT = load_manual_list(DATA_DIR / "manual_direct.json")
MANUAL_BLOCKED = load_manual_list(DATA_DIR / "manual_blocked.json")
MANUAL_FOREIGN = load_manual_list(DATA_DIR / "manual_foreign.json")
ROUTING_CONFIG = load_routing_config(DATA_DIR / "routing_settings.json")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="write updated files to disk")
    parser.add_argument("--offline", action="store_true", help="skip network fetches and use only manual core data")
    parser.add_argument("--timeout", type=float, default=20.0, help="per-request timeout in seconds")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="fail if any non-optional source cannot be fetched",
    )
    parser.add_argument(
        "--report-json",
        nargs="?",
        const="-",
        help="write a structured JSON report to PATH or stdout with '-'",
    )
    parser.add_argument(
        "--report-md",
        nargs="?",
        const="-",
        help="write a Markdown report to PATH or stdout with '-'",
    )
    return parser.parse_args()


def normalize_domain(value: str) -> str | None:
    value = value.strip().lower().strip(".")
    if not value or value.startswith("#"):
        return None
    if value.startswith("domain-suffix,"):
        value = value.split(",", 1)[1].strip()
    if value.startswith("full:"):
        value = value.split(":", 1)[1].strip()
    if value.startswith("domain:"):
        value = value.split(":", 1)[1].strip()
    if value.startswith("http://") or value.startswith("https://"):
        return None
    if "/" in value or ":" in value or "*" in value or " " in value:
        return None
    if not DOMAIN_RE.fullmatch(value):
        return None
    return value


def extract_domains(text: str) -> Set[str]:
    domains = set()
    for line in text.splitlines():
        if line.lstrip().startswith("#"):
            continue
        for match in DOMAIN_RE.findall(line):
            domain = normalize_domain(match)
            if domain:
                domains.add(domain)
    return domains


def fetch_text(source: Source, timeout: float) -> str:
    request = urllib.request.Request(
        source.url,
        headers={"User-Agent": "ios-routing-updater/1.0"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


def matches_exclude(domain: str, patterns: Sequence[str]) -> bool:
    for pattern in patterns:
        value = pattern.strip().lower()
        if not value:
            continue
        if "*" in value:
            regex = "^" + re.escape(value).replace(r"\*", ".*") + "$"
            if re.fullmatch(regex, domain):
                return True
            continue
        if value.startswith("."):
            suffix = value[1:]
            if domain == suffix or domain.endswith("." + suffix):
                return True
            continue
        if domain == value or domain.endswith("." + value):
            return True
    return False


def add_candidates(
    store: Dict[str, Candidate],
    domains: Iterable[str],
    source_name: str,
    manual: bool = False,
    priority: int = 0,
) -> None:
    for domain in domains:
        candidate = store.setdefault(domain, Candidate(domain=domain))
        candidate.sources.add(source_name)
        existing_priority = candidate.source_priorities.get(source_name, 0)
        candidate.source_priorities[source_name] = max(existing_priority, priority)
        if manual:
            candidate.manual = True


def is_ru_domain(domain: str, manual_direct_domains: Set[str]) -> bool:
    if domain in manual_direct_domains:
        return True
    return any(domain == tld or domain.endswith("." + tld) for tld in ROUTING_CONFIG.ru_tlds)


def compact_domains(domains: Iterable[str], always_keep: Set[str] | None = None) -> List[str]:
    always_keep = always_keep or set()
    ordered = sorted(set(domains), key=lambda item: (item.count("."), item))
    selected: List[str] = []
    for domain in ordered:
        if domain in always_keep:
            selected.append(domain)
            continue
        if any(domain == keep or domain.endswith("." + keep) for keep in selected):
            continue
        selected.append(domain)
    return sorted(set(selected), key=lambda item: (item.count("."), item))


def select_top(candidates: Dict[str, Candidate], limit: int, always_keep: Set[str]) -> List[str]:
    ranked = sorted(
        candidates.values(),
        key=lambda item: (-item.score()[0], -item.score()[1], -item.score()[2], item.domain),
    )
    chosen: List[str] = []
    chosen_set: Set[str] = set()
    for candidate in ranked:
        if candidate.domain in always_keep:
            continue
        chosen.append(candidate.domain)
        chosen_set.add(candidate.domain)
        if len(chosen_set) >= max(0, limit - len(always_keep)):
            break
    return compact_domains(always_keep | set(chosen), always_keep=always_keep)


def unique_preserve_order(domains: Iterable[str]) -> List[str]:
    seen: Set[str] = set()
    ordered: List[str] = []
    for domain in domains:
        if domain not in seen:
            seen.add(domain)
            ordered.append(domain)
    return ordered


def render_list(
    header_lines: Sequence[str],
    manual_sections: Dict[str, List[str]],
    extra_sections: Dict[str, List[str]] | None = None,
    tail_comment: str | None = None,
    tail_domains: Sequence[str] = (),
) -> str:
    lines = list(header_lines) + [""]
    first = True
    combined_sections: List[tuple[str, List[str]]] = []
    for section_name, domains in manual_sections.items():
        combined_sections.append((section_name, unique_preserve_order(domains)))
    for section_name, domains in (extra_sections or {}).items():
        combined_sections.append((section_name, compact_domains(domains)))

    for section_name, domains in combined_sections:
        if not domains:
            continue
        if not first:
            lines.append("")
        first = False
        lines.append(f"# {section_name}")
        lines.extend(f"DOMAIN-SUFFIX,{domain}" for domain in domains)
    if tail_domains:
        lines.append("")
        if tail_comment:
            lines.append(f"# {tail_comment}")
        lines.extend(f"DOMAIN-SUFFIX,{domain}" for domain in tail_domains)
    lines.append("")
    return "\n".join(lines)


def build_direct_list(
    direct_candidates: Dict[str, Candidate],
    blocked_domains: Set[str],
) -> str:
    manual_core = flatten_sections(MANUAL_DIRECT.sections)
    filtered: Dict[str, Candidate] = {}
    for domain, candidate in direct_candidates.items():
        if domain in ROUTING_CONFIG.direct_override:
            filtered[domain] = candidate
            continue
        if domain in blocked_domains:
            continue
        if not is_ru_domain(domain, manual_core):
            continue
        filtered[domain] = candidate

    always_keep = manual_core | ROUTING_CONFIG.direct_always_keep | ROUTING_CONFIG.direct_override
    selected = select_top(filtered, ROUTING_CONFIG.direct_limit, always_keep)
    extra = [domain for domain in selected if domain not in always_keep]

    return render_list(
        header_lines=MANUAL_DIRECT.header,
        manual_sections={name: list(domains) for name, domains in MANUAL_DIRECT.sections.items()},
        extra_sections={"Автодобавленные кандидаты": extra} if extra else None,
        tail_comment=MANUAL_DIRECT.tail_comment,
        tail_domains=MANUAL_DIRECT.tail_domains,
    )


def build_blocked_list(blocked_candidates: Dict[str, Candidate], direct_override: Set[str]) -> str:
    manual_core = flatten_sections(MANUAL_BLOCKED.sections)
    filtered: Dict[str, Candidate] = {}
    for domain, candidate in blocked_candidates.items():
        if domain in direct_override:
            continue
        if candidate.manual or len(candidate.sources) >= 2:
            filtered[domain] = candidate

    always_keep = manual_core
    selected = select_top(filtered, ROUTING_CONFIG.blocked_limit, always_keep)
    extra = [domain for domain in selected if domain not in always_keep]

    return render_list(
        header_lines=MANUAL_BLOCKED.header,
        manual_sections={name: list(domains) for name, domains in MANUAL_BLOCKED.sections.items()},
        extra_sections={"Автодобавленные кандидаты": extra} if extra else None,
    )


def build_foreign_list(foreign_candidates: Dict[str, Candidate]) -> str:
    manual_core = flatten_sections(MANUAL_FOREIGN.sections)
    filtered: Dict[str, Candidate] = {}
    for domain, candidate in foreign_candidates.items():
        if is_ru_domain(domain, set()):
            continue
        filtered[domain] = candidate

    always_keep = manual_core
    selected = select_top(filtered, ROUTING_CONFIG.foreign_limit, always_keep)
    extra = [domain for domain in selected if domain not in always_keep]

    return render_list(
        header_lines=MANUAL_FOREIGN.header,
        manual_sections={name: list(domains) for name, domains in MANUAL_FOREIGN.sections.items()},
        extra_sections={"Автодобавленные кандидаты": extra} if extra else None,
    )


def diff_text(path: Path, new_text: str) -> str:
    old_text = path.read_text(encoding="utf-8") if path.exists() else ""
    return "".join(
        difflib.unified_diff(
            old_text.splitlines(keepends=True),
            new_text.splitlines(keepends=True),
            fromfile=str(path),
            tofile=str(path),
        )
    )


def parse_list_domains(text: str) -> Set[str]:
    domains: Set[str] = set()
    for line in text.splitlines():
        domain = normalize_domain(line)
        if domain:
            domains.add(domain)
    return domains


def build_report_item(path: Path, new_text: str) -> dict[str, object]:
    old_text = path.read_text(encoding="utf-8") if path.exists() else ""
    old_domains = parse_list_domains(old_text)
    new_domains = parse_list_domains(new_text)
    added = sorted(new_domains - old_domains)
    removed = sorted(old_domains - new_domains)
    return {
        "path": str(path.relative_to(ROOT)),
        "changed": bool(added or removed),
        "current_count": len(old_domains),
        "new_count": len(new_domains),
        "added": added,
        "removed": removed,
    }


def build_sources_report() -> list[dict[str, object]]:
    sources = []
    for source in ROUTING_CONFIG.sources:
        sources.append(
            {
                "name": source.name,
                "bucket": source.bucket,
                "priority": source.priority,
                "optional": source.optional,
                "notes": source.notes,
                "exclude_domains": list(source.exclude_domains),
                "url": source.url,
            }
        )
    return sources


def build_report(
    outputs: Sequence[tuple[Path, str]],
    warnings: Sequence[str],
    args: argparse.Namespace,
    filtered_domains: dict[str, list[str]],
) -> dict[str, object]:
    files = [build_report_item(path, text) for path, text in outputs]
    changed_files = sum(1 for item in files if item["changed"])
    total_added = sum(len(item["added"]) for item in files)
    total_removed = sum(len(item["removed"]) for item in files)
    return {
        "offline": args.offline,
        "write": args.write,
        "warnings": list(warnings),
        "summary": {
            "files": len(files),
            "changed_files": changed_files,
            "total_added": total_added,
            "total_removed": total_removed,
        },
        "sources": build_sources_report(),
        "filtered_domains": filtered_domains,
        "files": files,
    }


def render_markdown_report(report: dict[str, object]) -> str:
    summary = report["summary"]
    assert isinstance(summary, dict)
    files = report["files"]
    assert isinstance(files, list)
    lines = [
        "# Routing Update Report",
        "",
        f"- Offline: `{report['offline']}`",
        f"- Write mode: `{report['write']}`",
        f"- Files checked: `{summary['files']}`",
        f"- Changed files: `{summary['changed_files']}`",
        f"- Total added: `{summary['total_added']}`",
        f"- Total removed: `{summary['total_removed']}`",
    ]

    warnings = report["warnings"]
    assert isinstance(warnings, list)
    if warnings:
        lines.extend(["", "## Warnings"])
        lines.extend(f"- {warning}" for warning in warnings)

    sources = report["sources"]
    assert isinstance(sources, list)
    if sources:
        lines.extend(["", "## Sources"])
        for source in sources:
            assert isinstance(source, dict)
            lines.append(
                f"- `{source['name']}`: bucket=`{source['bucket']}`, priority=`{source['priority']}`, optional=`{source['optional']}`"
            )
            if source["notes"]:
                lines.append(f"  notes: {source['notes']}")

    filtered_domains = report["filtered_domains"]
    assert isinstance(filtered_domains, dict)
    if filtered_domains:
        lines.extend(["", "## Filtered Domains"])
        for source_name, domains in filtered_domains.items():
            lines.append(f"- `{source_name}`: {len(domains)} filtered")
            if domains:
                lines.append(f"  domains: {', '.join(f'`{domain}`' for domain in domains)}")

    for item in files:
        assert isinstance(item, dict)
        lines.extend(
            [
                "",
                f"## `{item['path']}`",
                "",
                f"- Changed: `{item['changed']}`",
                f"- Current count: `{item['current_count']}`",
                f"- New count: `{item['new_count']}`",
                f"- Added: `{len(item['added'])}`",
                f"- Removed: `{len(item['removed'])}`",
            ]
        )
        added = item["added"]
        removed = item["removed"]
        assert isinstance(added, list)
        assert isinstance(removed, list)
        if added:
            lines.append("")
            lines.append("Added:")
            lines.extend(f"- `{domain}`" for domain in added)
        if removed:
            lines.append("")
            lines.append("Removed:")
            lines.extend(f"- `{domain}`" for domain in removed)

    lines.append("")
    return "\n".join(lines)


def emit_report(path_arg: str | None, payload: str) -> None:
    if not path_arg:
        return
    if path_arg == "-":
        sys.stdout.write(payload)
        if not payload.endswith("\n"):
            sys.stdout.write("\n")
        return
    path = Path(path_arg)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="utf-8")


def gather_candidates(
    args: argparse.Namespace,
) -> tuple[Dict[str, Candidate], Dict[str, Candidate], Dict[str, Candidate], List[str], dict[str, list[str]]]:
    direct_candidates: Dict[str, Candidate] = {}
    blocked_candidates: Dict[str, Candidate] = {}
    foreign_candidates: Dict[str, Candidate] = {}
    warnings: List[str] = []
    filtered_domains: dict[str, list[str]] = {}

    add_candidates(direct_candidates, flatten_sections(MANUAL_DIRECT.sections), "manual-core", manual=True, priority=1000)
    add_candidates(blocked_candidates, flatten_sections(MANUAL_BLOCKED.sections), "manual-core", manual=True, priority=1000)
    add_candidates(foreign_candidates, flatten_sections(MANUAL_FOREIGN.sections), "manual-core", manual=True, priority=1000)

    if args.offline:
        return direct_candidates, blocked_candidates, foreign_candidates, warnings, filtered_domains

    for source in ROUTING_CONFIG.sources:
        try:
            text = fetch_text(source, timeout=args.timeout)
        except (urllib.error.URLError, TimeoutError, ValueError) as exc:
            message = f"{source.name}: {exc}"
            if args.strict and not source.optional:
                raise RuntimeError(message) from exc
            warnings.append(message)
            continue

        domains = extract_domains(text)
        excluded = sorted(domain for domain in domains if matches_exclude(domain, source.exclude_domains))
        if excluded:
            filtered_domains[source.name] = excluded
        domains = {domain for domain in domains if not matches_exclude(domain, source.exclude_domains)}
        if source.bucket == "direct":
            add_candidates(direct_candidates, domains, source.name, priority=source.priority)
        elif source.bucket == "blocked":
            add_candidates(blocked_candidates, domains, source.name, priority=source.priority)
        elif source.bucket == "foreign":
            add_candidates(foreign_candidates, domains, source.name, priority=source.priority)

    return direct_candidates, blocked_candidates, foreign_candidates, warnings, filtered_domains


def write_if_requested(path: Path, text: str, write: bool) -> None:
    if write:
        path.write_text(text, encoding="utf-8")


def main() -> int:
    args = parse_args()
    if args.report_json == "-" and args.report_md == "-":
        raise SystemExit("Only one stdout report can be requested at a time.")

    direct_candidates, blocked_candidates, foreign_candidates, warnings, filtered_domains = gather_candidates(args)

    blocked_domains_for_direct = set(blocked_candidates) - ROUTING_CONFIG.direct_override
    direct_text = build_direct_list(direct_candidates, blocked_domains_for_direct)
    blocked_text = build_blocked_list(blocked_candidates, ROUTING_CONFIG.direct_override)
    foreign_text = build_foreign_list(foreign_candidates)

    outputs = (
        (DIRECT_PATH, direct_text),
        (BLOCKED_PATH, blocked_text),
        (FOREIGN_PATH, foreign_text),
    )
    report = build_report(outputs, warnings, args, filtered_domains)

    diff_stream = sys.stderr if args.report_json == "-" or args.report_md == "-" else sys.stdout

    any_changes = False
    for path, text in outputs:
        diff = diff_text(path, text)
        if diff:
            any_changes = True
            diff_stream.write(diff)
        write_if_requested(path, text, args.write)

    if not any_changes:
        print("No changes.", file=diff_stream)

    if warnings:
        warning_stream = sys.stderr
        print("\nWarnings:", file=warning_stream)
        for warning in warnings:
            print(f"- {warning}", file=warning_stream)

    if args.report_json:
        emit_report(args.report_json, json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    if args.report_md:
        emit_report(args.report_md, render_markdown_report(report))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
