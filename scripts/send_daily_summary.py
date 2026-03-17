#!/usr/bin/env python3
"""Generate and email a daily PfChat summary."""

from __future__ import annotations

import ipaddress
import json
import os
import re
import socket
import subprocess
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path('/home/openclaw/.openclaw/workspace')
PFCHAT_DIR = ROOT / 'pfchat'
PFCHAT_QUERY = PFCHAT_DIR / 'pfchat' / 'scripts' / 'pfchat_query.py'
RESEND_PY = ROOT / 'skills' / 'resend-email' / '.venv' / 'bin' / 'python'
RESEND_SCRIPT = ROOT / 'skills' / 'resend-email' / 'scripts' / 'send_resend_email.py'
TOOLS_MD = ROOT / 'TOOLS.md'
IP_LINE_RE = re.compile(r"- `(?P<ip>[^`]+)` — `(?P<name>[^`]+)`")
NOISE_PATTERNS = (
    'ff02::',
    '224.0.0.',
    '239.255.255.',
    'mdns',
    'igmp',
    'fe80::',
)


def load_inventory() -> dict[str, str]:
    mapping: dict[str, str] = {}
    if not TOOLS_MD.exists():
        return mapping
    for line in TOOLS_MD.read_text(encoding='utf-8').splitlines():
        match = IP_LINE_RE.search(line)
        if match:
            mapping[match.group('ip')] = match.group('name')
    return mapping


def reverse_lookup(ip: str) -> str | None:
    try:
        host, _, _ = socket.gethostbyaddr(ip)
        return host
    except Exception:
        return None


def best_name(ip: str, inventory: dict[str, str]) -> str:
    if ip in inventory and inventory[ip] and inventory[ip] != 'no hostname':
        return inventory[ip]
    resolved = reverse_lookup(ip)
    if resolved:
        return resolved
    return ip


def label_for_ip(ip: str, inventory: dict[str, str]) -> str:
    name = best_name(ip, inventory)
    if name == ip:
        return ip
    return f"{name} ({ip})"


def split_ip_port(value: str) -> tuple[str, str]:
    value = str(value or '').strip()
    if not value:
        return '', ''
    if value.startswith('[') and ']' in value:
        ip = value[1:].split(']', 1)[0]
        rest = value.split(']:', 1)
        return (ip, rest[1] if len(rest) == 2 else '')
    if value.count(':') == 1:
        return tuple(value.rsplit(':', 1))
    return value, ''


def pretty_endpoint(value: str, inventory: dict[str, str]) -> str:
    ip, port = split_ip_port(value)
    if not ip:
        return value
    label = label_for_ip(ip, inventory)
    return f"{label}:{port}" if port else label


def parse_ip(ip: str) -> ipaddress._BaseAddress | None:
    try:
        return ipaddress.ip_address(str(ip).strip())
    except ValueError:
        return None


def is_internal_ip(ip: str) -> bool:
    parsed = parse_ip(ip)
    return bool(parsed and parsed.is_private and not parsed.is_loopback and not parsed.is_multicast and not parsed.is_unspecified)


def is_loopback_ip(ip: str) -> bool:
    parsed = parse_ip(ip)
    return bool(parsed and parsed.is_loopback)


def is_multicast_or_broadcast_ip(ip: str) -> bool:
    parsed = parse_ip(ip)
    if not parsed:
        return False
    if parsed.version == 4:
        text = str(parsed)
        if text == '255.255.255.255' or text.endswith('.255'):
            return True
    return bool(parsed.is_multicast)


def should_include_connection(conn: dict[str, Any]) -> bool:
    source_ip, _ = split_ip_port(conn.get('source'))
    dest_ip, _ = split_ip_port(conn.get('destination'))
    if not source_ip or not is_internal_ip(source_ip) or is_loopback_ip(source_ip):
        return False
    if dest_ip and (
        is_loopback_ip(dest_ip)
        or is_multicast_or_broadcast_ip(dest_ip)
        or dest_ip == '192.168.0.254'
    ):
        return False
    return True


def is_noise_log(text: str) -> bool:
    lowered = text.lower()
    return any(pattern in lowered for pattern in NOISE_PATTERNS)


def run_pfchat_snapshot(limit: int = 150) -> dict[str, Any]:
    proc = subprocess.run(
        ['python3', str(PFCHAT_QUERY), 'snapshot', '--limit', str(limit)],
        cwd=str(PFCHAT_DIR),
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(proc.stdout)


def aggregate_client_usage(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    connections = snapshot.get('connections', {}).get('connections', [])
    per_client: dict[str, dict[str, Any]] = defaultdict(lambda: {
        'ip': '',
        'bytes_total': 0,
        'bytes_in': 0,
        'bytes_out': 0,
        'flows': 0,
    })

    for conn in connections:
        if not should_include_connection(conn):
            continue
        source_ip, _ = split_ip_port(conn.get('source'))

        item = per_client[source_ip]
        item['ip'] = source_ip
        item['bytes_total'] += int(conn.get('bytes_total', 0) or 0)
        item['bytes_in'] += int(conn.get('bytes_in', 0) or 0)
        item['bytes_out'] += int(conn.get('bytes_out', 0) or 0)
        item['flows'] += 1

    return sorted(per_client.values(), key=lambda d: d['bytes_total'], reverse=True)


def top_devices(snapshot: dict[str, Any], limit: int = 8) -> list[dict[str, Any]]:
    devices = snapshot.get('devices', {}).get('devices', [])
    usage = {item['ip']: item for item in aggregate_client_usage(snapshot)}
    enriched: list[dict[str, Any]] = []

    for dev in devices:
        ip = str(dev.get('ip_address') or dev.get('ip') or '').strip()
        if not ip:
            continue
        stats = usage.get(ip, {})
        enriched.append({
            'ip': ip,
            'hostname': dev.get('hostname') or dev.get('dnsresolve') or dev.get('mac_address') or '?',
            'source': dev.get('source') or 'unknown',
            'bytes_total': int(stats.get('bytes_total', 0) or 0),
            'bytes_in': int(stats.get('bytes_in', 0) or 0),
            'bytes_out': int(stats.get('bytes_out', 0) or 0),
            'flows': int(stats.get('flows', 0) or 0),
        })

    active = [item for item in enriched if item['bytes_total'] > 0]
    return sorted(active, key=lambda d: d['bytes_total'], reverse=True)[:limit]


def top_connections(snapshot: dict[str, Any], limit: int = 8) -> list[dict[str, Any]]:
    connections = snapshot.get('connections', {}).get('connections', [])
    filtered = [conn for conn in connections if should_include_connection(conn)]
    return sorted(filtered, key=lambda c: int(c.get('bytes_total', 0) or 0), reverse=True)[:limit]


def blocked_log_lines(snapshot: dict[str, Any], limit: int = 8) -> list[str]:
    lines: list[str] = []
    noisy: list[str] = []
    for item in snapshot.get('logs', {}).get('logs', []):
        text = str(item.get('text', ''))
        if 'block' not in text.lower():
            continue
        if is_noise_log(text):
            noisy.append(text)
            continue
        lines.append(text)
        if len(lines) >= limit:
            break
    return lines if lines else noisy[:limit]


def format_bytes(num: int) -> str:
    value = float(num)
    for unit in ('B', 'KB', 'MB', 'GB', 'TB'):
        if value < 1024 or unit == 'TB':
            return f'{value:.1f} {unit}'
        value /= 1024
    return f'{num} B'


def build_text(snapshot: dict[str, Any]) -> str:
    inventory = load_inventory()
    lines: list[str] = []
    errors = snapshot.get('errors', {})
    devices_meta = snapshot.get('devices', {})
    health = snapshot.get('health', {})
    gateways = health.get('gateways', [])
    system = health.get('system', {})

    lines.append('PfChat daily firewall summary')
    lines.append('')

    if errors:
        lines.append('Partial data warnings:')
        for key, value in errors.items():
            lines.append(f'- {key}: {value}')
        lines.append('')

    lines.append('Top internal clients by active traffic:')
    top_clients = top_devices(snapshot)
    if top_clients:
        for dev in top_clients:
            lines.append(
                f"- {label_for_ip(dev['ip'], inventory)} — total={format_bytes(dev['bytes_total'])} down={format_bytes(dev['bytes_in'])} up={format_bytes(dev['bytes_out'])} flows={dev['flows']}"
            )
    else:
        lines.append('- No active LAN client traffic found in the sampled state table')
    lines.append('')

    if devices_meta.get('degraded'):
        lines.append('Device inventory note: running in degraded mode inferred from firewall states because ARP/DHCP endpoints are not exposed by this pfSense REST API installation.')
        lines.append('')

    lines.append('Top LAN flows by bytes:')
    top_flows = top_connections(snapshot)
    if top_flows:
        for conn in top_flows:
            lines.append(
                f"- {pretty_endpoint(conn.get('source'), inventory)} -> {pretty_endpoint(conn.get('destination'), inventory)} | {conn.get('protocol')} | {conn.get('state')} | total={format_bytes(int(conn.get('bytes_total', 0) or 0))}"
            )
    else:
        lines.append('- No qualifying LAN flows found in the sampled state table')
    lines.append('')

    lines.append('Recent blocked log highlights:')
    blocked = blocked_log_lines(snapshot)
    if blocked:
        for line in blocked:
            lines.append(f'- {line}')
    else:
        lines.append('- No blocked entries found in the sampled logs')
    lines.append('')

    lines.append('Gateway/system status:')
    if gateways:
        for gw in gateways:
            src = gw.get('srcip')
            monitor = gw.get('monitorip')
            gw_label = gw.get('name')
            extra = []
            if src:
                extra.append(f"src={label_for_ip(str(src), inventory)}")
            if monitor:
                extra.append(f"monitor={label_for_ip(str(monitor), inventory)}")
            suffix = f" ({', '.join(extra)})" if extra else ''
            lines.append(
                f"- {gw_label}: status={gw.get('status')} loss={gw.get('loss')} delay={gw.get('delay')}ms stddev={gw.get('stddev')}{suffix}"
            )
    if system:
        lines.append(
            f"- system: uptime={system.get('uptime')} cpu_usage={system.get('cpu_usage')} mem_usage={system.get('mem_usage')} disk_usage={system.get('disk_usage')}"
        )

    lines.append('')
    lines.append('Generated by OpenClaw + PfChat.')
    return '\n'.join(lines)


def send_email(to_addr: str, subject: str, body: str) -> None:
    subprocess.run(
        [
            str(RESEND_PY),
            str(RESEND_SCRIPT),
            '--to',
            to_addr,
            '--subject',
            subject,
            '--text',
            body,
        ],
        cwd=str(ROOT),
        check=True,
    )


def main() -> int:
    to_addr = os.environ.get('PFCHAT_DAILY_EMAIL_TO', 'uzcategui@gmail.com').strip()
    subject = os.environ.get('PFCHAT_DAILY_EMAIL_SUBJECT', 'PfChat daily firewall summary')

    snapshot = run_pfchat_snapshot(limit=150)
    body = build_text(snapshot)
    send_email(to_addr, subject, body)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
