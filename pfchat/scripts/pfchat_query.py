#!/usr/bin/env python3
"""CLI entry point for the PfChat skill.

Examples:
  python3 skills/pfchat/scripts/pfchat_query.py devices
  python3 skills/pfchat/scripts/pfchat_query.py connections --limit 200 --host 192.168.0.95
  python3 skills/pfchat/scripts/pfchat_query.py logs --limit 200 --contains block --interface vtnet1
  python3 skills/pfchat/scripts/pfchat_query.py snapshot --limit 150 --once compact
  python3 skills/pfchat/scripts/pfchat_query.py block-ip --target 1.2.3.4
  python3 skills/pfchat/scripts/pfchat_query.py block-device --target iphoneLeo
  python3 skills/pfchat/scripts/pfchat_query.py draft-show --draft-id <id>
  python3 skills/pfchat/scripts/pfchat_query.py apply-draft --draft-id <id>
"""

from __future__ import annotations

import argparse
import hashlib
import ipaddress
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

from pfsense_client import PfSenseClient
from ntopng_client import NtopngClient
from ntopng_adapter import NtopngAdapter
from ntopng_pyapi_backend import NtopngPyApiBackend


FILTERLOG_RE = re.compile(
    r"(?P<rule>\d*),(?P<subrule>[^,]*),(?P<anchor>[^,]*),(?P<tracker>[^,]*),(?P<interface>[^,]*),(?P<reason>[^,]*),(?P<action>[^,]*),(?P<direction>[^,]*),(?P<ipver>[^,]*),(?P<tos>[^,]*),(?P<ecn>[^,]*),(?P<ttl>[^,]*),(?P<protocol_text>[^,]*),(?P<protocol_id>[^,]*),(?P<length>[^,]*),(?P<src>[^,]*),(?P<dst>[^,]*)(?:,(?P<src_port>[^,]*),(?P<dst_port>[^,]*).*)?$"
)


ONCE_PRESETS = {
    'compact': {'command': 'snapshot', 'limit': 50, 'view': 'summary'},
    'triage': {'command': 'snapshot', 'limit': 150, 'view': 'summary'},
    'wan': {'command': 'health', 'limit': 20, 'view': 'wan'},
    'blocked': {'command': 'logs', 'limit': 100, 'action': 'block', 'view': 'logs'},
}


STATE_DIR = Path(__file__).resolve().parents[1] / '.state'
DRAFTS_DIR = STATE_DIR / 'drafts'
AUDIT_LOG = STATE_DIR / 'audit.log'


def ensure_state_dirs() -> None:
    DRAFTS_DIR.mkdir(parents=True, exist_ok=True)


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


def validate_url_base(url: str, env_name: str) -> str:
    url = url.strip().rstrip('/')
    if not url:
        raise SystemExit(f"Missing {env_name}. Set it in the environment or in a local .env file.")
    if not (url.startswith('http://') or url.startswith('https://')):
        raise SystemExit(f"Invalid {env_name} value: {url!r}. Provide a full http:// or https:// base URL.")
    return url


def load_ntopng_config() -> tuple[str, str, str, str, bool]:
    script_root = Path(__file__).resolve().parents[2]
    load_env_file(script_root / '.env')
    load_env_file(Path('.env'))

    base_url = validate_url_base(os.environ.get('NTOPNG_BASE_URL', ''), 'NTOPNG_BASE_URL')
    username = os.environ.get('NTOPNG_USERNAME', '').strip()
    password = os.environ.get('NTOPNG_PASSWORD', '').strip()
    auth_token = os.environ.get('NTOPNG_AUTH_TOKEN', '').strip()
    if not auth_token and not username:
        raise SystemExit('Missing NTOPNG_USERNAME. Set it in the environment or in a local .env file, or provide NTOPNG_AUTH_TOKEN.')
    if not auth_token and not password:
        raise SystemExit('Missing NTOPNG_PASSWORD. Set it in the environment or in a local .env file, or provide NTOPNG_AUTH_TOKEN.')
    verify_ssl = parse_bool_env('NTOPNG_VERIFY_SSL', 'false')
    return base_url, username, password, auth_token, verify_ssl


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
    return cleaned[:24] or 'target'


def build_alias_name(hostname: str, ip_value: str) -> str:
    host_part = sanitize_alias_component(hostname).lower()[:12] or 'host'
    ip_part = sanitize_alias_component(ip_value).lower()[:12] or 'ip'
    alias = f"pfb_{host_part}_{ip_part}"
    return alias[:31]


def make_draft_id(command: str, target: str) -> str:
    seed = f'{command}|{target}|{time.time_ns()}'
    return hashlib.sha256(seed.encode()).hexdigest()[:12]


def draft_path(draft_id: str) -> Path:
    return DRAFTS_DIR / f'{draft_id}.json'


def append_audit(event: dict[str, Any]) -> None:
    ensure_state_dirs()
    with AUDIT_LOG.open('a', encoding='utf-8') as handle:
        handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + '\n')


def save_draft(draft: dict[str, Any]) -> dict[str, Any]:
    ensure_state_dirs()
    draft_id = draft.get('draft_id') or make_draft_id(str(draft.get('command', 'draft')), str(draft.get('target', {}).get('input', 'target')))
    draft['draft_id'] = draft_id
    draft['saved_at'] = int(time.time())
    draft['state_path'] = str(draft_path(draft_id))
    draft_path(draft_id).write_text(json.dumps(draft, indent=2, ensure_ascii=False), encoding='utf-8')
    append_audit({
        'ts': draft['saved_at'],
        'event': 'draft_saved',
        'draft_id': draft_id,
        'command': draft.get('command'),
        'target': draft.get('target', {}),
    })
    return draft


def load_draft(draft_id: str) -> dict[str, Any]:
    ensure_state_dirs()
    path = draft_path(draft_id)
    if not path.exists():
        raise SystemExit(f'Unknown draft id: {draft_id}')
    return json.loads(path.read_text(encoding='utf-8'))


def list_drafts() -> dict[str, Any]:
    ensure_state_dirs()
    drafts = []
    for path in sorted(DRAFTS_DIR.glob('*.json')):
        try:
            payload = json.loads(path.read_text(encoding='utf-8'))
        except Exception:
            continue
        drafts.append({
            'draft_id': payload.get('draft_id'),
            'saved_at': payload.get('saved_at'),
            'command': payload.get('command'),
            'target': payload.get('target', {}),
            'apply_status': payload.get('apply_status'),
        })
    return {'total_drafts': len(drafts), 'drafts': drafts}


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


def build_block_draft(client: PfSenseClient, target: str, command: str, port: str | None = None, proto: str = 'tcp') -> dict[str, Any]:
    resolved = resolve_block_target(client, target, command)
    ip_value = resolved.get('ip')
    if not ip_value or not is_ip_address(ip_value):
        raise SystemExit(f'Unable to resolve a valid IP address from target: {target!r}')

    try:
        parsed_ip = ipaddress.ip_address(ip_value)
    except ValueError as exc:
        raise SystemExit(f'Unable to resolve a valid IP address from target: {target!r}') from exc

    device = resolved.get('device') if isinstance(resolved.get('device'), dict) else {}
    interface = str(device.get('interface') or '').strip().lower() or None
    hostname = device.get('hostname') or device.get('dnsresolve') or ip_value
    caps = client.get_capabilities().get('capabilities', {})
    alias_name = build_alias_name(hostname, ip_value)
    private_target = parsed_ip.is_private
    is_egress_port_block = command == 'block-egress-port'
    is_egress_proto_block = command == 'block-egress-proto'

    warnings: list[str] = []
    if private_target:
        warnings.append('Target is RFC1918/private space. Review LAN impact carefully before any apply step.')
    if not interface:
        warnings.append('No interface could be resolved from device inventory. Preview cannot safely choose placement yet.')
    if not caps.get('firewall_aliases_write'):
        warnings.append('Live schema does not currently confirm firewall alias write endpoints.')
    if not caps.get('firewall_apply'):
        warnings.append('Live schema does not currently confirm firewall apply endpoint.')

    if is_egress_port_block:
        if not port or not str(port).isdigit():
            raise SystemExit('block-egress-port requires --port with a numeric destination port.')
        rule_description = f'PfChat draft egress block for {hostname} ({ip_value}) {proto}/{port}'
        proposal = {
            'strategy': 'alias_plus_rule_preview',
            'alias_name': alias_name,
            'alias_type': 'host',
            'alias_values': [ip_value],
            'rule_action': 'block',
            'rule_direction': 'in',
            'rule_interface': interface,
            'rule_protocol': proto.lower(),
            'destination_port': str(port),
            'rule_description': rule_description,
        }
    elif is_egress_proto_block:
        if proto.lower() != 'icmp':
            raise SystemExit('block-egress-proto currently supports only --proto icmp.')
        rule_description = f'PfChat draft egress block for {hostname} ({ip_value}) {proto}'
        proposal = {
            'strategy': 'alias_plus_rule_preview',
            'alias_name': alias_name,
            'alias_type': 'host',
            'alias_values': [ip_value],
            'rule_action': 'block',
            'rule_direction': 'in',
            'rule_interface': interface,
            'rule_protocol': 'icmp',
            'rule_description': rule_description,
        }
    else:
        rule_description = f'PfChat draft block for {hostname} ({ip_value})'
        proposal = {
            'strategy': 'alias_plus_rule_preview',
            'alias_name': alias_name,
            'alias_type': 'host',
            'alias_values': [ip_value],
            'rule_action': 'block',
            'rule_direction': 'in',
            'rule_interface': interface,
            'rule_description': rule_description,
        }

    return {
        'mode': 'draft',
        'command': command,
        'apply_supported_now': False,
        'apply_status': 'draft-only',
        'target': {
            'input': resolved['input'],
            'kind': resolved['kind'],
            'resolution': resolved['resolution'],
            'hostname': hostname,
            'ip': ip_value,
            'device': device or None,
        },
        'proposal': proposal,
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
            'Use draft-show with the returned draft_id to reload this proposal later.',
            'Apply remains blocked until the write phase is implemented.',
        ],
    }


def build_apply_preview(draft: dict[str, Any]) -> dict[str, Any]:
    event = {
        'ts': int(time.time()),
        'event': 'apply_preview',
        'draft_id': draft.get('draft_id'),
        'command': draft.get('command'),
        'target': draft.get('target', {}),
    }
    append_audit(event)
    return {
        'mode': 'apply-preview',
        'draft_id': draft.get('draft_id'),
        'status': 'ready-for-confirmation',
        'draft': draft,
        'next_steps': [
            'Review the saved draft details.',
            'Re-run apply-draft with --confirm to execute alias/rule/apply writes.',
        ],
    }


def require_apply_readiness(draft: dict[str, Any]) -> None:
    target = draft.get('target', {}) if isinstance(draft, dict) else {}
    proposal = draft.get('proposal', {}) if isinstance(draft, dict) else {}
    schema_support = draft.get('schema_support', {}) if isinstance(draft, dict) else {}
    ip_value = str(target.get('ip') or '').strip()
    if not ip_value or not is_ip_address(ip_value):
        raise SystemExit('Draft is missing a valid resolved IP address.')
    if not proposal.get('rule_interface'):
        raise SystemExit('Draft is missing a resolved interface. Refusing to apply.')
    if not schema_support.get('firewall_aliases_write'):
        raise SystemExit('Live schema does not confirm firewall alias write support.')
    if not schema_support.get('firewall_apply'):
        raise SystemExit('Live schema does not confirm firewall apply support.')


def execute_apply_draft(client: PfSenseClient, draft: dict[str, Any], confirm: bool = False) -> dict[str, Any]:
    require_apply_readiness(draft)
    if draft.get('apply_status') == 'applied':
        return {
            'mode': 'apply',
            'draft_id': draft.get('draft_id'),
            'status': 'already-applied',
            'draft': draft,
            'next_steps': ['Use rollback-draft if you intend to undo this applied draft.'],
        }
    if not confirm:
        return build_apply_preview(draft)

    target = draft['target']
    proposal = draft['proposal']
    capabilities = client.get_capabilities().get('capabilities', {})
    if not capabilities.get('firewall_aliases_write'):
        raise SystemExit('Current live schema no longer confirms firewall alias write support.')
    if not capabilities.get('firewall_rule_write'):
        raise SystemExit('Current live schema does not confirm firewall rule write support.')
    if not capabilities.get('firewall_apply'):
        raise SystemExit('Current live schema no longer confirms firewall apply support.')

    alias_payload = {
        'name': proposal['alias_name'],
        'type': proposal['alias_type'],
        'address': proposal['alias_values'],
        'descr': proposal['rule_description'],
        'detail': [f"Created by PfChat draft {draft.get('draft_id')}"] * len(proposal['alias_values']),
    }
    rule_payload = {
        'interface': [proposal['rule_interface']],
        'type': proposal['rule_action'],
        'ipprotocol': 'inet',
        'protocol': proposal.get('rule_protocol', 'any'),
        'source': proposal['alias_values'][0],
        'destination': 'any',
        'descr': proposal['rule_description'],
        'log': True,
    }
    if proposal.get('destination_port'):
        rule_payload['destination_port'] = proposal['destination_port']

    alias_result = client.create_firewall_alias(alias_payload)
    rule_result = client.create_firewall_rule(rule_payload)
    apply_result = client.apply_firewall_changes({'async': False})

    applied = {
        'mode': 'apply',
        'draft_id': draft.get('draft_id'),
        'status': 'applied',
        'target': target,
        'proposal': proposal,
        'results': {
            'alias': alias_result,
            'rule': rule_result,
            'apply': apply_result,
        },
        'applied_at': int(time.time()),
    }
    draft['apply_status'] = 'applied'
    draft['applied_at'] = applied['applied_at']
    draft['last_apply_result'] = applied['results']
    draft['rollback'] = {
        'status': 'available',
        'alias_id': alias_result.get('id'),
        'rule_id': rule_result.get('id'),
        'alias_name': proposal['alias_name'],
        'rule_description': proposal['rule_description'],
    }
    draft_path(str(draft['draft_id'])).write_text(json.dumps(draft, indent=2, ensure_ascii=False), encoding='utf-8')
    append_audit({
        'ts': applied['applied_at'],
        'event': 'apply_executed',
        'draft_id': draft.get('draft_id'),
        'command': draft.get('command'),
        'target': target,
    })
    return applied


def is_pfchat_managed_alias(entry: dict[str, Any]) -> bool:
    name = str(entry.get('name') or '')
    descr = str(entry.get('descr') or '')
    details = entry.get('detail') or []
    detail_text = ' '.join(str(x) for x in details) if isinstance(details, list) else str(details)
    return name.startswith('pfb_') or 'PfChat draft block' in descr or 'Created by PfChat draft' in detail_text


def is_pfchat_managed_rule(entry: dict[str, Any]) -> bool:
    descr = str(entry.get('descr') or '')
    source = str(entry.get('source') or '')
    return 'PfChat draft block' in descr or source.startswith('pfb_')


def list_managed_objects(client: PfSenseClient) -> dict[str, Any]:
    aliases = [item for item in client.get_firewall_aliases() if isinstance(item, dict) and is_pfchat_managed_alias(item)]
    rules = [item for item in client.get_firewall_rules() if isinstance(item, dict) and is_pfchat_managed_rule(item)]
    return {
        'total_aliases': len(aliases),
        'total_rules': len(rules),
        'aliases': aliases,
        'rules': rules,
    }


def execute_managed_delete(client: PfSenseClient, managed: dict[str, Any], confirm: bool, event_prefix: str, mode_preview: str, mode_apply: str, next_step_text: str) -> dict[str, Any]:
    if not confirm:
        append_audit({'ts': int(time.time()), 'event': f'{event_prefix}_preview', 'counts': {'aliases': managed['total_aliases'], 'rules': managed['total_rules']}})
        return {
            'mode': mode_preview,
            'status': 'ready-for-confirmation',
            'managed': managed,
            'next_steps': [next_step_text],
        }

    capabilities = client.get_capabilities().get('capabilities', {})
    if not capabilities.get('firewall_apply'):
        raise SystemExit('Current live schema does not confirm firewall apply support for this cleanup action.')

    results = {'rule_delete': [], 'alias_delete': []}
    if capabilities.get('firewall_rule_delete'):
        for rule in managed['rules']:
            if rule.get('id') is not None:
                results['rule_delete'].append(client.delete_firewall_rule(rule['id']))
    if capabilities.get('firewall_aliases_delete'):
        for alias in managed['aliases']:
            if alias.get('id') is not None:
                results['alias_delete'].append(client.delete_firewall_alias(alias['id']))
    results['apply'] = client.apply_firewall_changes({'async': False})
    append_audit({'ts': int(time.time()), 'event': f'{event_prefix}_executed', 'counts': {'aliases': len(results['alias_delete']), 'rules': len(results['rule_delete'])}})
    return {
        'mode': mode_apply,
        'status': 'cleaned',
        'results': results,
    }


def cleanup_managed_objects(client: PfSenseClient, confirm: bool = False) -> dict[str, Any]:
    managed = list_managed_objects(client)
    return execute_managed_delete(
        client,
        managed,
        confirm,
        event_prefix='managed_cleanup',
        mode_preview='managed-cleanup-preview',
        mode_apply='managed-cleanup',
        next_step_text='Re-run pfchat-managed-cleanup with --confirm to delete these PfChat-managed objects.',
    )


def select_managed_objects_by_target(client: PfSenseClient, target: str) -> dict[str, Any]:
    target = normalize_device_name(target)
    if not target:
        raise SystemExit('Missing --target for unblock workflow.')
    managed = list_managed_objects(client)
    aliases = []
    rules = []
    for alias in managed['aliases']:
        hay = ' '.join([
            str(alias.get('name') or ''),
            str(alias.get('descr') or ''),
            ' '.join(str(x) for x in (alias.get('address') or [])),
            ' '.join(str(x) for x in (alias.get('detail') or [])),
        ]).lower()
        if target in hay:
            aliases.append(alias)
    for rule in managed['rules']:
        hay = ' '.join([
            str(rule.get('descr') or ''),
            str(rule.get('source') or ''),
            str(rule.get('destination') or ''),
        ]).lower()
        if target in hay:
            rules.append(rule)
    return {
        'target': target,
        'total_aliases': len(aliases),
        'total_rules': len(rules),
        'aliases': aliases,
        'rules': rules,
    }


def cleanup_managed_target(client: PfSenseClient, target: str, confirm: bool = False) -> dict[str, Any]:
    managed = select_managed_objects_by_target(client, target)
    if managed['total_aliases'] == 0 and managed['total_rules'] == 0:
        raise SystemExit(f'No PfChat-managed objects matched target: {target!r}')
    result = execute_managed_delete(
        client,
        managed,
        confirm,
        event_prefix='managed_target_cleanup',
        mode_preview='managed-target-cleanup-preview',
        mode_apply='managed-target-cleanup',
        next_step_text='Re-run unblock command with --confirm to remove these PfChat-managed objects.',
    )
    result['target'] = managed['target']
    return result


def build_quick_rule_description(hostname: str, ip_value: str, proto: str, port: str | None = None) -> str:
    suffix = f' {proto}/{port}' if port else f' {proto}'
    return f'PfChat quick egress block for {hostname} ({ip_value}){suffix}'


def build_quick_rule_payload(interface: str, hostname: str, ip_value: str, proto: str, port: str | None = None) -> dict[str, Any]:
    proto_value = proto.lower()
    payload = {
        'interface': [interface],
        'floating': True,
        'quick': True,
        'direction': 'in',
        'type': 'block',
        'ipprotocol': 'inet',
        'protocol': proto_value,
        'source': ip_value,
        'destination': 'any',
        'descr': build_quick_rule_description(hostname, ip_value, proto_value, port),
        'log': True,
        'statetype': 'keep state',
    }
    if proto_value == 'icmp':
        payload['icmptype'] = ['any']
    elif port:
        payload['destination_port'] = str(port)
    return payload


def state_matches_target(state: dict[str, Any], ip_value: str, proto: str, port: str | None = None) -> bool:
    if not isinstance(state, dict):
        return False
    source = str(state.get('source') or '')
    if ip_value not in source:
        return False
    state_proto = str(state.get('protocol') or state.get('proto') or '').lower()
    proto_value = proto.lower()
    if proto_value == 'icmp':
        return state_proto in {'icmp', 'icmpv4', '1', ''}
    if state_proto != proto_value:
        return False
    if port:
        return str(state.get('destination') or '').endswith(f':{port}')
    return True


def find_matching_quick_rules(client: PfSenseClient, ip_value: str, proto: str, port: str | None = None) -> list[dict[str, Any]]:
    matches = []
    expected_descr_suffix = f' {proto.lower()}/{port}' if port else f' {proto.lower()}'
    for rule in client.get_firewall_rules():
        if not isinstance(rule, dict):
            continue
        descr = str(rule.get('descr') or '')
        if not descr.startswith('PfChat quick egress block for '):
            continue
        if str(rule.get('source') or '') != ip_value:
            continue
        if str(rule.get('protocol') or '').lower() != proto.lower():
            continue
        if port and str(rule.get('destination_port') or '') != str(port):
            continue
        if not port and str(rule.get('destination_port') or '') not in {'', 'None', 'null'}:
            continue
        if not descr.endswith(expected_descr_suffix):
            continue
        matches.append(rule)
    return matches


def clear_matching_states(client: PfSenseClient, ip_value: str, proto: str, port: str | None = None) -> list[dict[str, Any]]:
    deleted = []
    for state in client.get_firewall_states(limit=500, filters={'source__contains': ip_value}):
        if not state_matches_target(state, ip_value, proto, port):
            continue
        state_id = state.get('id')
        if state_id is None:
            continue
        deleted.append({
            'id': state_id,
            'source': state.get('source'),
            'destination': state.get('destination'),
            'protocol': state.get('protocol'),
            'result': client.delete_firewall_state(state_id),
        })
    return deleted


def quick_egress_block(client: PfSenseClient, target: str, proto: str, port: str | None = None) -> dict[str, Any]:
    resolved = resolve_block_target(client, target, 'quick-egress-block')
    ip_value = str(resolved.get('ip') or '').strip()
    if not ip_value or not is_ip_address(ip_value):
        raise SystemExit(f'Unable to resolve a valid IP address from target: {target!r}')
    device = resolved.get('device') if isinstance(resolved.get('device'), dict) else {}
    interface = str(device.get('interface') or '').strip().lower()
    hostname = device.get('hostname') or device.get('dnsresolve') or ip_value
    if not interface:
        raise SystemExit('Quick egress block requires a resolved interface from device inventory.')
    proto_value = proto.lower()
    if proto_value not in {'tcp', 'udp', 'icmp'}:
        raise SystemExit('Quick egress block supports only tcp, udp, or icmp.')
    if proto_value in {'tcp', 'udp'} and (not port or not str(port).isdigit()):
        raise SystemExit('Quick egress block for tcp/udp requires --port with a numeric destination port.')
    if proto_value == 'icmp':
        port = None

    existing = find_matching_quick_rules(client, ip_value, proto_value, port)
    if existing:
        rule_result = {'status': 'exists', 'rules': existing}
    else:
        rule_result = client.create_firewall_rule(build_quick_rule_payload(interface, str(hostname), ip_value, proto_value, port))
    apply_result = client.apply_firewall_changes({'async': False})
    deleted_states = clear_matching_states(client, ip_value, proto_value, port)
    append_audit({'ts': int(time.time()), 'event': 'quick_egress_block', 'target': {'input': resolved['input'], 'hostname': hostname, 'ip': ip_value}, 'proto': proto_value, 'port': port})
    return {
        'mode': 'quick-egress-block',
        'status': 'blocked',
        'target': {'input': resolved['input'], 'hostname': hostname, 'ip': ip_value, 'interface': interface},
        'proto': proto_value,
        'port': port,
        'rule_result': rule_result,
        'apply_result': apply_result,
        'deleted_states': deleted_states,
    }


def quick_egress_unblock(client: PfSenseClient, target: str, proto: str, port: str | None = None) -> dict[str, Any]:
    resolved = resolve_block_target(client, target, 'quick-egress-unblock')
    ip_value = str(resolved.get('ip') or '').strip()
    if not ip_value or not is_ip_address(ip_value):
        raise SystemExit(f'Unable to resolve a valid IP address from target: {target!r}')
    device = resolved.get('device') if isinstance(resolved.get('device'), dict) else {}
    hostname = device.get('hostname') or device.get('dnsresolve') or ip_value
    proto_value = proto.lower()
    if proto_value == 'icmp':
        port = None
    rules = find_matching_quick_rules(client, ip_value, proto_value, port)
    deleted_rules = []
    for rule in rules:
        if rule.get('id') is None:
            continue
        deleted_rules.append({'id': rule['id'], 'descr': rule.get('descr'), 'result': client.delete_firewall_rule(rule['id'])})
    apply_result = client.apply_firewall_changes({'async': False}) if deleted_rules else None
    deleted_states = clear_matching_states(client, ip_value, proto_value, port)
    append_audit({'ts': int(time.time()), 'event': 'quick_egress_unblock', 'target': {'input': resolved['input'], 'hostname': hostname, 'ip': ip_value}, 'proto': proto_value, 'port': port})
    return {
        'mode': 'quick-egress-unblock',
        'status': 'unblocked',
        'target': {'input': resolved['input'], 'hostname': hostname, 'ip': ip_value},
        'proto': proto_value,
        'port': port,
        'deleted_rules': deleted_rules,
        'apply_result': apply_result,
        'deleted_states': deleted_states,
    }


def execute_rollback_draft(client: PfSenseClient, draft: dict[str, Any], confirm: bool = False) -> dict[str, Any]:
    if draft.get('apply_status') != 'applied':
        raise SystemExit('Rollback requires a previously applied draft.')
    rollback = draft.get('rollback', {}) if isinstance(draft, dict) else {}
    if not rollback:
        raise SystemExit('Draft does not contain rollback metadata.')
    if not confirm:
        append_audit({
            'ts': int(time.time()),
            'event': 'rollback_preview',
            'draft_id': draft.get('draft_id'),
            'command': draft.get('command'),
        })
        return {
            'mode': 'rollback-preview',
            'draft_id': draft.get('draft_id'),
            'status': 'ready-for-confirmation',
            'rollback': rollback,
            'next_steps': ['Re-run rollback-draft with --confirm to execute the rollback.'],
        }

    capabilities = client.get_capabilities().get('capabilities', {})
    if not capabilities.get('firewall_apply'):
        raise SystemExit('Current live schema does not confirm firewall apply support for rollback.')

    results: dict[str, Any] = {}
    if rollback.get('rule_id') is not None and capabilities.get('firewall_rule_delete'):
        results['rule_delete'] = client.delete_firewall_rule(rollback['rule_id'])
    if rollback.get('alias_id') is not None and capabilities.get('firewall_aliases_delete'):
        results['alias_delete'] = client.delete_firewall_alias(rollback['alias_id'])
    results['apply'] = client.apply_firewall_changes({'async': False})

    draft['apply_status'] = 'rolled-back'
    draft['rolled_back_at'] = int(time.time())
    draft['last_rollback_result'] = results
    draft_path(str(draft['draft_id'])).write_text(json.dumps(draft, indent=2, ensure_ascii=False), encoding='utf-8')
    append_audit({
        'ts': draft['rolled_back_at'],
        'event': 'rollback_executed',
        'draft_id': draft.get('draft_id'),
        'command': draft.get('command'),
    })
    return {
        'mode': 'rollback',
        'draft_id': draft.get('draft_id'),
        'status': 'rolled-back',
        'results': results,
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
        choices=[
            "capabilities", "devices", "connections", "logs", "interfaces", "health", "rules", "snapshot",
            "ntop-capabilities", "ntop-hosts", "ntop-host", "ntop-top-talkers",
            "block-ip", "block-device", "block-egress-port", "block-egress-proto", "unblock-ip", "unblock-device", "draft-show", "draft-list", "apply-draft", "rollback-draft", "pfchat-managed-list", "pfchat-managed-cleanup",
            "quick-egress-block", "quick-egress-unblock"
        ],
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
    parser.add_argument("--proto", choices=['tcp', 'udp', 'icmp'], default='tcp', help="Protocol for egress block workflows")
    parser.add_argument("--draft-id", help="Saved draft identifier for draft-show or apply-draft")
    parser.add_argument("--confirm", action="store_true", help="Explicitly confirm a state-changing apply-draft execution")
    parser.add_argument("--ifid", type=int, default=0, help="ntopng interface id for ntop-* commands")
    parser.add_argument("--direction", choices=['local', 'remote'], default='local', help="Direction for ntop-top-talkers")
    args = parser.parse_args()
    args = apply_once_preset(args)

    base_filters = parse_filters(args.filter)
    pf_commands = {
        'capabilities', 'devices', 'connections', 'logs', 'interfaces', 'health', 'rules', 'snapshot',
        'block-ip', 'block-device', 'block-egress-port', 'block-egress-proto', 'unblock-ip', 'unblock-device',
        'apply-draft', 'rollback-draft', 'pfchat-managed-list', 'pfchat-managed-cleanup', 'quick-egress-block', 'quick-egress-unblock'
    }
    ntop_commands = {'ntop-capabilities', 'ntop-hosts', 'ntop-host', 'ntop-top-talkers'}

    if args.command in pf_commands:
        host, api_key, verify_ssl = load_config()
        client = PfSenseClient(host=host, api_key=api_key, verify_ssl=verify_ssl)
    else:
        client = None

    if args.command in ntop_commands:
        base_url, username, password, auth_token, ntop_verify_ssl = load_ntopng_config()
        ntop_client = NtopngClient(base_url=base_url, username=username, password=password, auth_token=auth_token, verify_ssl=ntop_verify_ssl)
        ntop_backend = NtopngPyApiBackend(url=base_url, username=username, password=password, auth_token=auth_token, verify_ssl=ntop_verify_ssl)
        ntop_adapter = NtopngAdapter(ntop_client=ntop_backend, pfsense_client=client)
    else:
        ntop_client = None
        ntop_backend = None
        ntop_adapter = None

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
        data = {"interfaces": client.get_interfaces()}
    elif args.command == "health":
        data = client.get_health_bundle()
    elif args.command == "rules":
        rules = client.get_firewall_rules(filters=base_filters or None)
        data = {"total_rules": len(rules), "rules": rules, "applied_filters": base_filters}
    elif args.command == 'ntop-capabilities':
        data = ntop_adapter.get_capabilities()
    elif args.command == 'ntop-hosts':
        data = ntop_adapter.get_active_hosts(ifid=args.ifid, limit=args.limit, host_filter=args.host)
    elif args.command == 'ntop-host':
        target_host = args.host or args.target
        if not target_host:
            raise SystemExit('Missing --host or --target for ntop-host.')
        data = ntop_adapter.get_host_summary(target=target_host, ifid=args.ifid)
    elif args.command == 'ntop-top-talkers':
        data = ntop_adapter.get_top_talkers(ifid=args.ifid, direction=args.direction)
    elif args.command in {"block-ip", "block-device"}:
        data = save_draft(build_block_draft(client, args.target or '', args.command))
    elif args.command == 'block-egress-port':
        data = save_draft(build_block_draft(client, args.target or '', args.command, port=args.port, proto=args.proto))
    elif args.command == 'block-egress-proto':
        data = save_draft(build_block_draft(client, args.target or '', args.command, proto=args.proto))
    elif args.command in {'unblock-ip', 'unblock-device'}:
        if not args.target:
            raise SystemExit('Missing --target for unblock workflow.')
        data = cleanup_managed_target(client, args.target, confirm=args.confirm)
    elif args.command == 'draft-show':
        if not args.draft_id:
            raise SystemExit('Missing --draft-id for draft-show.')
        data = load_draft(args.draft_id)
    elif args.command == 'draft-list':
        data = list_drafts()
    elif args.command == 'apply-draft':
        if not args.draft_id:
            raise SystemExit('Missing --draft-id for apply-draft.')
        data = execute_apply_draft(client, load_draft(args.draft_id), confirm=args.confirm)
    elif args.command == 'rollback-draft':
        if not args.draft_id:
            raise SystemExit('Missing --draft-id for rollback-draft.')
        data = execute_rollback_draft(client, load_draft(args.draft_id), confirm=args.confirm)
    elif args.command == 'pfchat-managed-list':
        data = list_managed_objects(client)
    elif args.command == 'pfchat-managed-cleanup':
        data = cleanup_managed_objects(client, confirm=args.confirm)
    elif args.command == 'quick-egress-block':
        data = quick_egress_block(client, args.target or '', args.proto, port=args.port)
    elif args.command == 'quick-egress-unblock':
        data = quick_egress_unblock(client, args.target or '', args.proto, port=args.port)
    else:
        data = client.get_snapshot(limit=args.limit)

    print_json(render_view(data, args.view))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
