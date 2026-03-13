#!/usr/bin/env python3
"""Generate and email a daily PfChat summary."""

from __future__ import annotations

import json
import os
import re
import socket
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path('/home/openclaw/.openclaw/workspace')
PFCHAT_DIR = ROOT / 'pfchat'
PFCHAT_QUERY = PFCHAT_DIR / 'pfchat' / 'scripts' / 'pfchat_query.py'
RESEND_PY = ROOT / 'skills' / 'resend-email' / '.venv' / 'bin' / 'python'
RESEND_SCRIPT = ROOT / 'skills' / 'resend-email' / 'scripts' / 'send_resend_email.py'
TOOLS_MD = ROOT / 'TOOLS.md'
IP_LINE_RE = re.compile(r"- `(?P<ip>[^`]+)` — `(?P<name>[^`]+)`")


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


def run_pfchat_snapshot(limit: int = 150) -> dict[str, Any]:
    proc = subprocess.run(
        ['python3', str(PFCHAT_QUERY), 'snapshot', '--limit', str(limit)],
        cwd=str(PFCHAT_DIR),
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(proc.stdout)


def top_devices(snapshot: dict[str, Any], limit: int = 8) -> list[dict[str, Any]]:
    devices = snapshot.get('devices', {}).get('devices', [])
    return sorted(devices, key=lambda d: int(d.get('seen_in_states', 0) or 0), reverse=True)[:limit]


def top_connections(snapshot: dict[str, Any], limit: int = 8) -> list[dict[str, Any]]:
    connections = snapshot.get('connections', {}).get('connections', [])
    return sorted(connections, key=lambda c: int(c.get('bytes_total', 0) or 0), reverse=True)[:limit]


def blocked_log_lines(snapshot: dict[str, Any], limit: int = 8) -> list[str]:
    lines: list[str] = []
    for item in snapshot.get('logs', {}).get('logs', []):
        text = str(item.get('text', ''))
        if 'block' in text.lower():
            lines.append(text)
        if len(lines) >= limit:
            break
    return lines


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

    lines.append('Top active internal devices:')
    for dev in top_devices(snapshot):
        ip = dev.get('ip') or dev.get('ipaddr') or '(no-ip)'
        seen = dev.get('seen_in_states', 'n/a')
        lines.append(f'- {label_for_ip(ip, inventory)} — seen in {seen} active states')
    lines.append('')

    if devices_meta.get('degraded'):
        lines.append('Device inventory note: running in degraded mode inferred from firewall states because ARP/DHCP endpoints are not exposed by this pfSense REST API installation.')
        lines.append('')

    lines.append('Top active flows by bytes:')
    for conn in top_connections(snapshot):
        lines.append(
            f"- {pretty_endpoint(conn.get('source'), inventory)} -> {pretty_endpoint(conn.get('destination'), inventory)} | {conn.get('protocol')} | {conn.get('state')} | bytes={conn.get('bytes_total')}"
        )
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
