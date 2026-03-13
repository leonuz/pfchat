#!/usr/bin/env python3
"""CLI entry point for the PfChat skill.

Examples:
  python3 skills/pfchat/scripts/pfchat_query.py devices
  python3 skills/pfchat/scripts/pfchat_query.py connections --limit 200 --host 192.168.0.95
  python3 skills/pfchat/scripts/pfchat_query.py logs --limit 200 --contains block --interface vtnet1
  python3 skills/pfchat/scripts/pfchat_query.py snapshot --limit 150
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

from pfsense_client import PfSenseClient


FILTERLOG_RE = re.compile(
    r"(?P<rule>\d*),(?P<subrule>[^,]*),(?P<anchor>[^,]*),(?P<tracker>[^,]*),(?P<interface>[^,]*),(?P<reason>[^,]*),(?P<action>[^,]*),(?P<direction>[^,]*),(?P<ipver>[^,]*),(?P<tos>[^,]*),(?P<ecn>[^,]*),(?P<ttl>[^,]*),(?P<protocol_text>[^,]*),(?P<protocol_id>[^,]*),(?P<length>[^,]*),(?P<src>[^,]*),(?P<dst>[^,]*)(?:,(?P<src_port>[^,]*),(?P<dst_port>[^,]*).*)?$"
)


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def load_config() -> tuple[str, str, bool]:
    script_root = Path(__file__).resolve().parents[2]
    load_env_file(script_root / ".env")
    load_env_file(Path(".env"))

    host = os.environ.get("PFSENSE_HOST", "").strip()
    api_key = os.environ.get("PFSENSE_API_KEY", "").strip()
    verify_ssl = os.environ.get("PFSENSE_VERIFY_SSL", "false").strip().lower() == "true"

    if not host or not api_key:
        raise SystemExit(
            "Missing PFSENSE_HOST or PFSENSE_API_KEY. Set them in the environment or in a local .env file."
        )

    return host, api_key, verify_ssl


def parse_filters(values: list[str]) -> dict[str, Any]:
    filters: dict[str, Any] = {}
    for item in values:
        if "=" not in item:
            raise SystemExit(f"Invalid --filter value: {item}. Expected key=value")
        key, value = item.split("=", 1)
        if key.endswith("[]"):
            filters.setdefault(key[:-2], []).append(value)
        else:
            filters[key] = value
    return filters


def build_connection_filters(args: argparse.Namespace, base_filters: dict[str, Any]) -> dict[str, Any]:
    filters = dict(base_filters)
    if args.host:
        filters.setdefault("source__contains", args.host)
    if args.port:
        filters.setdefault("destination__contains", f":{args.port}")
    if args.interface:
        filters.setdefault("interface__contains", args.interface)
    if args.contains:
        filters.setdefault("search", args.contains)
    return filters


def parse_filterlog_entry(text: str) -> dict[str, str]:
    marker = 'filterlog['
    if marker not in text or ': ' not in text:
        return {}
    payload = text.split(': ', 1)[1]
    match = FILTERLOG_RE.search(payload)
    if not match:
        return {}
    parsed = {key: (value or "") for key, value in match.groupdict().items()}
    parsed["text"] = text
    return parsed


def filter_logs(
    logs: list[dict[str, Any]],
    host: str | None = None,
    port: str | None = None,
    interface: str | None = None,
    contains: str | None = None,
    action: str | None = None,
) -> list[dict[str, Any]]:
    filtered: list[dict[str, Any]] = []
    needle = (contains or "").lower()
    action = (action or "").lower()

    for item in logs:
        text = str(item.get("text", ""))
        parsed = parse_filterlog_entry(text)
        haystacks = [text.lower()]
        if parsed:
            haystacks.extend([
                parsed.get("src", "").lower(),
                parsed.get("dst", "").lower(),
                parsed.get("src_port", "").lower(),
                parsed.get("dst_port", "").lower(),
                parsed.get("interface", "").lower(),
                parsed.get("action", "").lower(),
                parsed.get("direction", "").lower(),
                parsed.get("protocol_text", "").lower(),
            ])

        if host and not any(host.lower() in field for field in haystacks):
            continue
        if port and not any(str(port).lower() == field for field in [parsed.get("src_port", "").lower(), parsed.get("dst_port", "").lower()] if parsed):
            continue
        if interface and interface.lower() != parsed.get("interface", "").lower():
            continue
        if needle and not any(needle in field for field in haystacks):
            continue
        if action and action != parsed.get("action", "").lower():
            continue

        enriched = dict(item)
        if parsed:
            enriched["parsed"] = parsed
        filtered.append(enriched)

    return filtered


def print_json(data: Any) -> None:
    json.dump(data, sys.stdout, indent=2, ensure_ascii=False, default=str)
    sys.stdout.write("\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Query pfSense API for the PfChat skill")
    parser.add_argument(
        "command",
        choices=["capabilities", "devices", "connections", "logs", "interfaces", "health", "rules", "snapshot"],
        help="Dataset to fetch from pfSense",
    )
    parser.add_argument("--limit", type=int, default=100, help="Entry limit for large endpoints")
    parser.add_argument("--filter", action="append", default=[], help="Query filter in key=value form; repeatable")
    parser.add_argument("--host", help="Host/IP filter helper for connections or logs")
    parser.add_argument("--port", help="Port filter helper for connections or logs")
    parser.add_argument("--interface", help="Interface filter helper for connections or logs")
    parser.add_argument("--contains", help="Free-text contains helper for connections or logs")
    parser.add_argument("--action", choices=["block", "pass", "match"], help="Log action filter helper")
    args = parser.parse_args()

    host, api_key, verify_ssl = load_config()
    client = PfSenseClient(host=host, api_key=api_key, verify_ssl=verify_ssl)
    base_filters = parse_filters(args.filter)

    if args.command == "capabilities":
        data = client.get_capabilities()
    elif args.command == "devices":
        data = client.get_connected_devices()
    elif args.command == "connections":
        filters = build_connection_filters(args, base_filters)
        connections = client.get_firewall_states(limit=args.limit, filters=filters or None)
        data = {
            "total_active_connections": len(connections),
            "connections": connections,
            "applied_filters": filters,
        }
    elif args.command == "logs":
        logs = client.get_firewall_logs(limit=args.limit)
        filtered_logs = filter_logs(
            logs,
            host=args.host,
            port=args.port,
            interface=args.interface,
            contains=args.contains,
            action=args.action,
        )
        data = {
            "total_entries": len(filtered_logs),
            "logs": filtered_logs,
            "applied_filters": {
                "host": args.host,
                "port": args.port,
                "interface": args.interface,
                "contains": args.contains,
                "action": args.action,
            },
        }
    elif args.command == "interfaces":
        interfaces = client.get_interfaces()
        data = {"interfaces": interfaces}
    elif args.command == "health":
        data = client.get_health_bundle()
    elif args.command == "rules":
        rules = client.get_firewall_rules(filters=base_filters or None)
        data = {"total_rules": len(rules), "rules": rules, "applied_filters": base_filters}
    else:
        data = client.get_snapshot(limit=args.limit)

    print_json(data)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
