#!/usr/bin/env python3
"""CLI entry point for the PfChat skill.

Examples:
  python3 skills/pfchat/scripts/pfchat_query.py devices
  python3 skills/pfchat/scripts/pfchat_query.py connections --limit 200 --host 192.168.0.95
  python3 skills/pfchat/scripts/pfchat_query.py logs --limit 200 --contains block --interface vtnet1
  python3 skills/pfchat/scripts/pfchat_query.py snapshot --limit 150 --once compact
  python3 skills/pfchat/scripts/pfchat_query.py block-ip --target 1.2.3.4
  python3 skills/pfchat/scripts/pfchat_query.py block-device --target iphoneLeo
"""

from __future__ import annotations

import argparse
import ipaddress
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


ONCE_PRESETS = {
    'compact': {'command': 'snapshot', 'limit': 50, 'view': 'summary'},
    'triage': {'command': 'snapshot', 'limit': 150, 'view': 'summary'},
    'wan': {'command': 'health', 'limit': 20, 'view': 'wan'},
    'blocked': {'command': 'logs', 'limit': 100, 'action': 'block', 'view': 'logs'},
}


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def parse_bool_env(name: str, default: str = "false") -> bool:
    raw = os.environ.get(name, default).strip().lower()
    if raw in {"true", "1", "yes", "y", "on"}:
        return True
    if raw in {"false", "0", "no", "n", "off"}:
        return False
    raise SystemExit(
        f"Invalid {name} value: {raw!r}. Expected one of true/false, 1/0, yes/no, on/off."
    )


def validate_host(host: str) -> str:
    host = host.strip().rstrip('/')
    if not host:
        raise SystemExit("Missing PFSENSE_HOST. Set it in the environment or in a local .env file.")
    if '://' in host:
        raise SystemExit(
            f"Invalid PFSENSE_HOST value: {host!r}. Provide only the host or IP, without http:// or https://."
        )
    if '/' in host:
        raise SystemExit(
            f"Invalid PFSENSE_HOST value: {host!r}. Provide only the host or IP, without URL paths."
        )
    return host


def validate_api_key(api_key: str) -> str:
    api_key = api_key.strip()
    if not api_key:
        raise SystemExit("Missing PFSENSE_API_KEY. Set it in the environment or in a local .env file.")
    if any(ch.isspace() for ch in api_key):
        raise SystemExit("Invalid PFSENSE_API_KEY. It must not contain whitespace.")
    if api_key == 'replace-me':
        raise SystemExit("Invalid PFSENSE_API_KEY. Replace the example placeholder with a real API key.")
    return api_key


def load_config() -> tuple[str, str, bool]:
    script_root = Path(__file__).resolve().parents[2]
    load_env_file(script_root / ".env")
    load_env_file(Path(".env"))

    host = validate_host(os.environ.get("PFSENSE_HOST", ""))
    api_key = validate_api_key(os.environ.get("PFSENSE_API_KEY", ""))
    verify_ssl = parse_bool_env("PFSENSE_VERIFY_SSL", "false")

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


def apply_once_preset(args: argparse.Namespace) -> argparse.Namespace:
    if not args.once:
        return args
    preset = ONCE_PRESETS[args.once]
    args.command = preset['command']
    args.limit = preset.get('limit', args.limit)
    args.view = preset.get('view', args.view)
    if preset.get('action') and not args.action:
        args.action = preset['action']
    return args


def normalize_device_name(value: Any) -> str:
    return str(value or '').strip().lower()


def is_ip_address(value: str) -> bool:
    try:
        ipaddress.ip_address(value)
        return True
    except ValueError:
        return False


def sanitize_alias_component(value: str) -> str:
    cleaned = re.sub(r'[^a-zA-Z0-9]+', '_', value).strip('_')
    return cleaned[:40] or 'target'


def resolve_block_target(client: PfSenseClient, target: str, command: str) -> dict[str, Any]:
    target = str(target or '').strip()
    if not target:
        raise SystemExit('Missing --target. Provide an IP, hostname, or device name to draft a block action.')

    devices = client.get_connected_devices()
    candidates = devices.get('devices', []) if isinstance(devices, dict) else []

    if command == 'block-ip':
        if not is_ip_address(target):
            raise SystemExit('block-ip requires --target to be a valid IP address.')
        matched = next(
            (
                item for item in candidates
                if str(item.get('ip') or item.get('ip_address') or '').strip() == target
            ),
            None,
        )
        return {
            'kind': 'ip',
            'input': target,
            'ip': target,
            'device': matched,
            'resolution': 'exact-ip',
        }

    normalized_target = normalize_device_name(target)
    matches = []
    for item in candidates:
        hostname = normalize_device_name(item.get('hostname'))
        ip_value = str(item.get('ip') or item.get('ip_address') or '').strip()
        if normalized_target in {hostname, normalize_device_name(ip_value)}:
            matches.append(item)

    if is_ip_address(target) and not matches:
        return {
            'kind': 'device',
            'input': target,
            'ip': target,
            'device': None,
            'resolution': 'ip-without-device-match',
        }

    if not matches:
        raise SystemExit(f'No device matched target: {target!r}')
    if len(matches) > 1:
        raise SystemExit(f'Ambiguous device target: {target!r}. Narrow it to an IP or exact hostname.')

    device = matches[0]
    return {
        'kind': 'device',
        'input': target,
        'ip': str(device.get('ip') or device.get('ip_address') or '').strip(),
        'device': device,
        'resolution': 'device-match',
    }


def build_block_draft(client: PfSenseClient, target: str, command: str) -> dict[str, Any]:
    resolved = resolve_block_target(client, target, command)
    ip_value = resolved.get('ip')
    if not ip_value or not is_ip_address(ip_value):
        raise SystemExit(f'Unable to resolve a valid IP address from target: {target!r}')

    try:
        parsed_ip = ipaddress.ip_address(ip_value)
    except ValueError as exc:
        raise SystemExit(f'Unable to resolve a valid IP address from target: {target!r}') from exc

    device = resolved.get('device') if isinstance(resolved.get('device'), dict) else {}
    interface = device.get('interface') or None
    hostname = device.get('hostname') or device.get('dnsresolve') or ip_value
    caps = client.get_capabilities().get('capabilities', {})
    alias_name = f"pfchat_block_{sanitize_alias_component(hostname)}_{sanitize_alias_component(ip_value)}"
    private_target = parsed_ip.is_private

    warnings: list[str] = []
    if private_target:
        warnings.append('Target is RFC1918/private space. Review LAN impact carefully before any apply step.')
    if not interface:
        warnings.append('No interface could be resolved from device inventory. Preview cannot safely choose placement yet.')
    if not caps.get('firewall_aliases_write'):
        warnings.append('Live schema does not currently confirm firewall alias write endpoints.')
    if not caps.get('firewall_apply'):
        warnings.append('Live schema does not currently confirm firewall apply endpoint.')

    return {
        'mode': 'draft',
        'command': command,
        'apply_supported_now': False,
        'apply_status': 'not-implemented',
        'target': {
            'input': resolved['input'],
            'kind': resolved['kind'],
            'resolution': resolved['resolution'],
            'hostname': hostname,
            'ip': ip_value,
            'device': device or None,
        },
        'proposal': {
            'strategy': 'alias_plus_rule_preview',
            'alias_name': alias_name,
            'alias_type': 'host',
            'alias_values': [ip_value],
            'rule_action': 'block',
            'rule_direction': 'in',
            'rule_interface': interface,
            'rule_description': f'PfChat draft block for {hostname} ({ip_value})',
        },
        'schema_support': {
            'firewall_aliases_write': bool(caps.get('firewall_aliases_write')),
            'firewall_apply': bool(caps.get('firewall_apply')),
        },
        'risk': {
            'private_target': private_target,
            'warnings': warnings,
        },
        'next_steps': [
            'Review this draft and confirm the target, interface, and expected impact.',
            'Apply is intentionally not implemented yet in this phase.',
        ],
    }


def render_view(data: Any, view: str | None) -> Any:
    if not view or view == 'full':
        return data
    if view == 'summary':
        if isinstance(data, dict) and 'summary' in data:
            return data['summary']
        raise SystemExit('The selected command does not provide a summary view.')
    if view == 'wan':
        if isinstance(data, dict) and 'interfaces' in data:
            wan = next((item for item in data.get('interfaces', []) if str(item.get('name', '')).lower() == 'wan'), None)
            return {'wan': wan}
        if isinstance(data, dict) and 'summary' in data:
            return {'wan': data['summary'].get('wan')}
        raise SystemExit('The selected command does not provide a WAN view.')
    if view == 'highlights':
        if isinstance(data, dict) and 'summary' in data:
            return {'highlights': data['summary'].get('highlights', [])}
        raise SystemExit('The selected command does not provide highlights.')
    raise SystemExit(f'Unknown --view value: {view}')


def print_json(data: Any) -> None:
    json.dump(data, sys.stdout, indent=2, ensure_ascii=False, default=str)
    sys.stdout.write("\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Query pfSense API for the PfChat skill")
    parser.add_argument(
        "command",
        nargs='?',
        default='snapshot',
        choices=["capabilities", "devices", "connections", "logs", "interfaces", "health", "rules", "snapshot", "block-ip", "block-device"],
        help="Dataset to fetch from pfSense",
    )
    parser.add_argument("--once", choices=sorted(ONCE_PRESETS.keys()), help="Run an automation-oriented preset in one shot")
    parser.add_argument("--view", choices=["full", "summary", "wan", "highlights"], default='full', help="Render a reduced view when supported")
    parser.add_argument("--limit", type=int, default=100, help="Entry limit for large endpoints")
    parser.add_argument("--filter", action="append", default=[], help="Query filter in key=value form; repeatable")
    parser.add_argument("--host", help="Host/IP filter helper for connections or logs")
    parser.add_argument("--port", help="Port filter helper for connections or logs")
    parser.add_argument("--interface", help="Interface filter helper for connections or logs")
    parser.add_argument("--contains", help="Free-text contains helper for connections or logs")
    parser.add_argument("--action", choices=["block", "pass", "match"], help="Log action filter helper")
    parser.add_argument("--target", help="Target IP or device identifier for draft block workflows")
    args = parser.parse_args()
    args = apply_once_preset(args)

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
    elif args.command in {"block-ip", "block-device"}:
        data = build_block_draft(client, args.target or '', args.command)
    else:
        data = client.get_snapshot(limit=args.limit)

    print_json(render_view(data, args.view))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
