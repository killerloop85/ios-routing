#!/usr/bin/env python3
"""Render a Synology office sing-box config from a generated baseline and a VLESS URI."""

from __future__ import annotations

import argparse
import json
import secrets
import sys
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse


ROOT = Path(__file__).resolve().parent.parent
GENERATED_DIR = ROOT / "office" / "sing-box" / "generated"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=("split", "full"), default="split")
    parser.add_argument("--uri", required=True, help="single VLESS URI")
    parser.add_argument("--output", required=True, help="output path for rendered config")
    parser.add_argument("--proxy-username", default="officeproxy")
    parser.add_argument("--proxy-password", default=None)
    return parser.parse_args()


def load_baseline(profile: str) -> dict:
    name = f"config.{profile}.generated.json"
    path = GENERATED_DIR / name
    return json.loads(path.read_text(encoding="utf-8"))


def parse_vless_uri(uri: str) -> dict[str, str]:
    parsed = urlparse(uri.strip())
    if parsed.scheme != "vless":
        raise ValueError("expected vless:// URI")
    if not parsed.hostname or not parsed.port or not parsed.username:
        raise ValueError("URI is missing hostname, port, or uuid")
    params = parse_qs(parsed.query)

    def one(key: str, default: str = "") -> str:
        values = params.get(key)
        return values[0] if values else default

    return {
        "server": parsed.hostname,
        "server_port": str(parsed.port),
        "uuid": unquote(parsed.username),
        "flow": one("flow"),
        "server_name": one("sni"),
        "fingerprint": one("fp", "chrome"),
        "public_key": one("pbk"),
        "short_id": one("sid"),
        "spider_x": unquote(one("spx", "/")),
    }


def replace_placeholders(payload: object, values: dict[str, str]) -> object:
    if isinstance(payload, dict):
        return {key: replace_placeholders(value, values) for key, value in payload.items()}
    if isinstance(payload, list):
        return [replace_placeholders(item, values) for item in payload]
    if isinstance(payload, str):
        return values.get(payload, payload)
    return payload


def main() -> int:
    args = parse_args()
    config = load_baseline(args.profile)
    uri_values = parse_vless_uri(args.uri)
    proxy_password = args.proxy_password or secrets.token_urlsafe(18)
    replacements = {
        "REPLACE_PROXY_USERNAME": args.proxy_username,
        "REPLACE_PROXY_PASSWORD": proxy_password,
        "REPLACE_VLESS_SERVER": uri_values["server"],
        "REPLACE_VLESS_PORT": int(uri_values["server_port"]),
        "REPLACE_VLESS_UUID": uri_values["uuid"],
        "REPLACE_VLESS_FLOW": uri_values["flow"],
        "REPLACE_VLESS_SERVER_NAME": uri_values["server_name"],
        "REPLACE_VLESS_FINGERPRINT": uri_values["fingerprint"],
        "REPLACE_VLESS_PUBLIC_KEY": uri_values["public_key"],
        "REPLACE_VLESS_SHORT_ID": uri_values["short_id"],
        "REPLACE_VLESS_SPIDER_X": uri_values["spider_x"],
    }
    rendered = replace_placeholders(config, replacements)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(rendered, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    summary = {
        "profile": args.profile,
        "output": str(output_path),
        "proxy_username": args.proxy_username,
        "proxy_password": proxy_password,
        "server": uri_values["server"],
        "server_port": uri_values["server_port"],
        "server_name": uri_values["server_name"],
        "flow": uri_values["flow"],
    }
    json.dump(summary, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
