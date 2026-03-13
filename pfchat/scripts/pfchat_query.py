#!/usr/bin/env python3
"""CLI entry point for the PfChat skill.

Examples:
  python3 skills/pfchat/scripts/pfchat_query.py devices
  python3 skills/pfchat/scripts/pfchat_query.py connections --limit 200 --filter source__contains=192.168.0.95
  python3 skills/pfchat/scripts/pfchat_query.py snapshot --limit 150
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from pfsense_client import PfSenseClient


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
    args = parser.parse_args()

    host, api_key, verify_ssl = load_config()
    client = PfSenseClient(host=host, api_key=api_key, verify_ssl=verify_ssl)
    filters = parse_filters(args.filter)

    if args.command == "capabilities":
        data = client.get_capabilities()
    elif args.command == "devices":
        data = client.get_connected_devices()
    elif args.command == "connections":
        connections = client.get_firewall_states(limit=args.limit, filters=filters or None)
        data = {
            "total_active_connections": len(connections),
            "connections": connections,
        }
    elif args.command == "logs":
        logs = client.get_firewall_logs(limit=args.limit)
        data = {"total_entries": len(logs), "logs": logs}
    elif args.command == "interfaces":
        interfaces = client.get_interfaces()
        data = {"interfaces": interfaces}
    elif args.command == "health":
        data = client.get_health_bundle()
    elif args.command == "rules":
        rules = client.get_firewall_rules(filters=filters or None)
        data = {"total_rules": len(rules), "rules": rules}
    else:
        data = client.get_snapshot(limit=args.limit)

    print_json(data)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
