#!/usr/bin/env python3
"""Update Shadowrocket routing lists from curated cores and external sources.

This script implements the repository spec from docs/routing-update-spec.md.
It favors conservative output and can run in offline mode using only the
manual core domains defined below.
"""

from __future__ import annotations

import argparse
import difflib
import re
import sys
import urllib.error
import urllib.request
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Set


ROOT = Path(__file__).resolve().parent.parent
SHADOWROCKET_DIR = ROOT / "shadowrocket"

DIRECT_PATH = SHADOWROCKET_DIR / "ru-direct.list"
BLOCKED_PATH = SHADOWROCKET_DIR / "ru-blocked-core.list"
FOREIGN_PATH = SHADOWROCKET_DIR / "foreign-services.list"

DIRECT_LIMIT = 500
BLOCKED_LIMIT = 250
FOREIGN_LIMIT = 250

RU_TLDS = ("ru", "su", "rf", "moscow", "москва")
DIRECT_ALWAYS_KEEP = {"ru", "su"}


@dataclass(frozen=True)
class Source:
    name: str
    url: str
    bucket: str
    kind: str = "text"
    optional: bool = True


@dataclass
class Candidate:
    domain: str
    sources: Set[str] = field(default_factory=set)
    manual: bool = False

    def score(self) -> tuple[int, int, str]:
        return (1 if self.manual else 0, len(self.sources), self.domain)


MANUAL_DIRECT: Dict[str, List[str]] = {
    "Госуслуги и госорганы": [
        "gosuslugi.ru",
        "esia.gosuslugi.ru",
        "nalog.ru",
        "nalog.gov.ru",
        "mos.ru",
        "mosreg.ru",
        "government.ru",
        "kremlin.ru",
        "pfr.gov.ru",
    ],
    "Банки и платежи": [
        "sberbank.ru",
        "sber.ru",
        "online.sberbank.ru",
        "vtb.ru",
        "alfabank.ru",
        "tbank.ru",
        "tinkoff.ru",
        "open.ru",
        "raiffeisen.ru",
        "gazprombank.ru",
        "psbank.ru",
        "mironline.ru",
        "sbp.nspk.ru",
    ],
    "Почта и соцсети Рунета": [
        "yandex.ru",
        "yandex.net",
        "ya.ru",
        "yastatic.net",
        "mail.ru",
        "vk.com",
        "ok.ru",
    ],
    "Крупные сервисы и маркетплейсы": [
        "ozon.ru",
        "wildberries.ru",
        "avito.ru",
        "cian.ru",
        "2gis.ru",
        "pochta.ru",
        "cdek.ru",
        "rzd.ru",
    ],
    "Операторы связи и провайдеры": [
        "mts.ru",
        "tele2.ru",
        "beeline.ru",
        "megafon.ru",
        "rostelecom.ru",
        "yota.ru",
        "domru.ru",
        "ertelecom.ru",
    ],
}

MANUAL_BLOCKED: Dict[str, List[str]] = {
    "Meta / соцсети": [
        "instagram.com",
        "cdninstagram.com",
        "threads.net",
        "facebook.com",
        "fbcdn.net",
        "messenger.com",
    ],
    "Twitter / X": [
        "twitter.com",
        "x.com",
        "t.co",
    ],
    "Discord": [
        "discord.com",
        "discord.gg",
        "discordapp.com",
    ],
    "LinkedIn": [
        "linkedin.com",
        "licdn.com",
    ],
    "YouTube / Google-видео": [
        "youtube.com",
        "youtu.be",
        "googlevideo.com",
        "ytimg.com",
    ],
    "Независимые медиа / чувствительные ресурсы (ядро)": [
        "meduza.io",
        "svoboda.org",
        "currenttime.tv",
        "dozhd.ru",
        "tvrain.tv",
    ],
    "OONI / цензурные исследования": [
        "ooni.org",
        "explorer.ooni.org",
        "torproject.org",
    ],
}

MANUAL_FOREIGN: Dict[str, List[str]] = {
    "Dev / AI / Tools": [
        "openai.com",
        "chatgpt.com",
        "anthropic.com",
        "claude.ai",
        "perplexity.ai",
        "deepl.com",
    ],
    "Prod / Collaboration": [
        "notion.so",
        "notion.site",
        "figma.com",
        "linear.app",
        "slack.com",
        "atlassian.com",
        "trello.com",
        "asana.com",
        "zoom.us",
    ],
    "Dev / Cloud / CDN": [
        "github.com",
        "githubusercontent.com",
        "githubassets.com",
        "gitlab.com",
        "bitbucket.org",
        "docker.com",
        "docker.io",
        "hub.docker.com",
        "cloudflare.com",
        "workers.dev",
        "vercel.com",
        "netlify.app",
        "herokuapp.com",
    ],
    "Google / YouTube": [
        "google.com",
        "googleapis.com",
        "gstatic.com",
        "youtube.com",
        "ytimg.com",
        "googlevideo.com",
    ],
    "Соцсети / медиа (но здесь — именно как зарубежные сервисы)": [
        "reddit.com",
        "redd.it",
        "redditmedia.com",
        "medium.com",
        "substack.com",
        "linkedin.com",
    ],
    "Почта / безопасность": [
        "proton.me",
        "protonmail.com",
        "protonvpn.com",
        "tutanota.com",
    ],
    "VPN / обход": [
        "openvpn.net",
        "wireguard.com",
        "psiphon.ca",
        "lantern.io",
    ],
    "Развлечения": [
        "netflix.com",
        "spotify.com",
    ],
}

DIRECT_OVERRIDE: Set[str] = set()

DIRECT_HEADER = ["# Russian and local services that should stay DIRECT."]
BLOCKED_HEADER = [
    "# Core services that are commonly blocked or heavily degraded in Russia.",
    "# Весь этот трафик нужно строго гнать через VPN.",
]
FOREIGN_HEADER = [
    "# Foreign services that are typically more reliable over VPN from Russia.",
    "# Здесь — сервисы и компании, которые часто режут РФ или работают нестабильно без VPN.",
]

SOURCES: Sequence[Source] = (
    Source(
        "russia-mobile-internet-whitelist",
        "https://github.com/hxehex/russia-mobile-internet-whitelist/raw/main/whitelist.txt",
        "direct",
    ),
    Source(
        "russia-mobile-internet-cidrwhitelist",
        "https://github.com/hxehex/russia-mobile-internet-whitelist/raw/main/cidrwhitelist.txt",
        "direct",
    ),
    Source(
        "ooni-zapret-list",
        "https://raw.githubusercontent.com/1andrevich/ooni-zapret-list/master/resolvers-hosts.txt",
        "blocked",
    ),
    Source(
        "re-filter-lists",
        "https://raw.githubusercontent.com/1andrevich/Re-filter-lists/main/community.lst",
        "blocked",
    ),
    Source(
        "vpn-configs-for-russia-bypass",
        "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/main/README.md",
        "direct",
    ),
    Source(
        "vpn-configs-for-russia",
        "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/main/README.md",
        "foreign",
    ),
)


DOMAIN_RE = re.compile(r"\b(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-zа-я0-9-]{2,}\b", re.IGNORECASE)


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


def add_candidates(store: Dict[str, Candidate], domains: Iterable[str], source_name: str, manual: bool = False) -> None:
    for domain in domains:
        candidate = store.setdefault(domain, Candidate(domain=domain))
        candidate.sources.add(source_name)
        if manual:
            candidate.manual = True


def flatten_sections(sections: Dict[str, List[str]]) -> Set[str]:
    values: Set[str] = set()
    for domains in sections.values():
        values.update(domains)
    return values


def is_ru_domain(domain: str, manual_direct_domains: Set[str]) -> bool:
    if domain in manual_direct_domains:
        return True
    return any(domain == tld or domain.endswith("." + tld) for tld in RU_TLDS)


def compact_domains(domains: Iterable[str], always_keep: Set[str] | None = None) -> List[str]:
    always_keep = always_keep or set()
    ordered = sorted(set(domains), key=lambda item: (item.count("."), item))
    selected: List[str] = []
    for domain in ordered:
        if domain in always_keep:
            selected.append(domain)
            continue
        if any(domain == keep or domain.endswith("." + keep) for keep in selected if keep not in always_keep):
            continue
        selected.append(domain)
    return sorted(set(selected), key=lambda item: (item.count("."), item))


def select_top(candidates: Dict[str, Candidate], limit: int, always_keep: Set[str]) -> List[str]:
    ranked = sorted(candidates.values(), key=lambda item: (-item.score()[0], -item.score()[1], item.domain))
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
    manual_core = flatten_sections(MANUAL_DIRECT)
    filtered: Dict[str, Candidate] = {}
    for domain, candidate in direct_candidates.items():
        if domain in DIRECT_OVERRIDE:
            filtered[domain] = candidate
            continue
        if domain in blocked_domains:
            continue
        if not is_ru_domain(domain, manual_core):
            continue
        filtered[domain] = candidate

    always_keep = manual_core | DIRECT_ALWAYS_KEEP | DIRECT_OVERRIDE
    selected = select_top(filtered, DIRECT_LIMIT, always_keep)
    extra = [domain for domain in selected if domain not in always_keep]

    return render_list(
        header_lines=DIRECT_HEADER,
        manual_sections={name: list(domains) for name, domains in MANUAL_DIRECT.items()},
        extra_sections={"Автодобавленные кандидаты": extra} if extra else None,
        tail_comment="Общий fallback для .ru / .su",
        tail_domains=["ru", "su"],
    )


def build_blocked_list(blocked_candidates: Dict[str, Candidate], direct_override: Set[str]) -> str:
    manual_core = flatten_sections(MANUAL_BLOCKED)
    filtered: Dict[str, Candidate] = {}
    for domain, candidate in blocked_candidates.items():
        if domain in direct_override:
            continue
        if candidate.manual or len(candidate.sources) >= 2:
            filtered[domain] = candidate

    always_keep = manual_core
    selected = select_top(filtered, BLOCKED_LIMIT, always_keep)
    extra = [domain for domain in selected if domain not in always_keep]

    return render_list(
        header_lines=BLOCKED_HEADER,
        manual_sections={name: list(domains) for name, domains in MANUAL_BLOCKED.items()},
        extra_sections={"Автодобавленные кандидаты": extra} if extra else None,
    )


def build_foreign_list(foreign_candidates: Dict[str, Candidate]) -> str:
    manual_core = flatten_sections(MANUAL_FOREIGN)
    filtered: Dict[str, Candidate] = {}
    for domain, candidate in foreign_candidates.items():
        if is_ru_domain(domain, set()):
            continue
        filtered[domain] = candidate

    always_keep = manual_core
    selected = select_top(filtered, FOREIGN_LIMIT, always_keep)
    extra = [domain for domain in selected if domain not in always_keep]

    return render_list(
        header_lines=FOREIGN_HEADER,
        manual_sections={name: list(domains) for name, domains in MANUAL_FOREIGN.items()},
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


def gather_candidates(args: argparse.Namespace) -> tuple[Dict[str, Candidate], Dict[str, Candidate], Dict[str, Candidate], List[str]]:
    direct_candidates: Dict[str, Candidate] = {}
    blocked_candidates: Dict[str, Candidate] = {}
    foreign_candidates: Dict[str, Candidate] = {}
    warnings: List[str] = []

    add_candidates(direct_candidates, flatten_sections(MANUAL_DIRECT), "manual-core", manual=True)
    add_candidates(blocked_candidates, flatten_sections(MANUAL_BLOCKED), "manual-core", manual=True)
    add_candidates(foreign_candidates, flatten_sections(MANUAL_FOREIGN), "manual-core", manual=True)

    if args.offline:
        return direct_candidates, blocked_candidates, foreign_candidates, warnings

    for source in SOURCES:
        try:
            text = fetch_text(source, timeout=args.timeout)
        except (urllib.error.URLError, TimeoutError, ValueError) as exc:
            message = f"{source.name}: {exc}"
            if args.strict and not source.optional:
                raise RuntimeError(message) from exc
            warnings.append(message)
            continue

        domains = extract_domains(text)
        if source.bucket == "direct":
            add_candidates(direct_candidates, domains, source.name)
        elif source.bucket == "blocked":
            add_candidates(blocked_candidates, domains, source.name)
        elif source.bucket == "foreign":
            add_candidates(foreign_candidates, domains, source.name)

    return direct_candidates, blocked_candidates, foreign_candidates, warnings


def write_if_requested(path: Path, text: str, write: bool) -> None:
    if write:
        path.write_text(text, encoding="utf-8")


def main() -> int:
    args = parse_args()
    direct_candidates, blocked_candidates, foreign_candidates, warnings = gather_candidates(args)

    blocked_domains_for_direct = set(blocked_candidates) - DIRECT_OVERRIDE
    direct_text = build_direct_list(direct_candidates, blocked_domains_for_direct)
    blocked_text = build_blocked_list(blocked_candidates, DIRECT_OVERRIDE)
    foreign_text = build_foreign_list(foreign_candidates)

    outputs = (
        (DIRECT_PATH, direct_text),
        (BLOCKED_PATH, blocked_text),
        (FOREIGN_PATH, foreign_text),
    )

    any_changes = False
    for path, text in outputs:
        diff = diff_text(path, text)
        if diff:
            any_changes = True
            sys.stdout.write(diff)
        write_if_requested(path, text, args.write)

    if not any_changes:
        print("No changes.")

    if warnings:
        print("\nWarnings:", file=sys.stderr)
        for warning in warnings:
            print(f"- {warning}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
