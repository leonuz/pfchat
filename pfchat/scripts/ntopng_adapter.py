#!/usr/bin/env python3
"""PfChat normalization/aggregation layer for ntopng."""

from __future__ import annotations

import ipaddress
from typing import Any

from pfsense_client import PfSenseClient


class NtopngAdapter:
    """Normalize ntopng responses into stable PfChat-native shapes."""

    def __init__(self, ntop_client: object, pfsense_client: PfSenseClient | None = None):
        self.ntop_client = ntop_client
        self.pfsense_client = pfsense_client

    @staticmethod
    def _extract_vlan(value: Any) -> int:
        try:
            return int(value)
        except Exception:
            return 0

    @staticmethod
    def _host_key(ip_value: str, vlan: int) -> str:
        return f'{ip_value}@{vlan}'

    @staticmethod
    def _normalize_host_row(row: dict[str, Any]) -> dict[str, Any]:
        ip_value = str(row.get('ip') or '').strip()
        vlan = NtopngAdapter._extract_vlan(row.get('vlan', 0))
        bytes_block = row.get('bytes', {}) if isinstance(row.get('bytes'), dict) else {}
        flows_block = row.get('num_flows', {}) if isinstance(row.get('num_flows'), dict) else {}
        return {
            'ip': ip_value,
            'hostname': row.get('name') if row.get('name') not in (0, '0', None, '') else None,
            'vlan': vlan,
            'ntop_host_key': row.get('key') or NtopngAdapter._host_key(ip_value, vlan),
            'first_seen_epoch': row.get('first_seen'),
            'last_seen_epoch': row.get('last_seen'),
            'bytes': {
                'total': bytes_block.get('total'),
                'sent': bytes_block.get('sent'),
                'received': bytes_block.get('rcvd') if 'rcvd' in bytes_block else bytes_block.get('received'),
            },
            'flows': {
                'total': flows_block.get('total'),
                'as_client': flows_block.get('as_client'),
                'as_server': flows_block.get('as_server'),
            },
            'country': row.get('country') or None,
            'os': row.get('os') if row.get('os') not in (0, '0', None, '') else None,
            'is_blacklisted': bool(row.get('is_blacklisted', False)),
            'raw': row,
        }

    def get_capabilities(self) -> dict[str, Any]:
        capabilities: dict[str, Any] = {
            'ntopng_available': True,
            'capabilities': {
                'rest_v1': hasattr(self.ntop_client, 'get_active_hosts'),
                'rest_v2': hasattr(self.ntop_client, 'get_interface'),
                'interfaces': False,
                'active_hosts': False,
                'host_data': False,
                'alerts': False,
                'timeseries': False,
                'historical_flows': False,
            },
        }
        try:
            interfaces = self.ntop_client.get_interfaces_list()
            capabilities['interface_count'] = len(interfaces) if isinstance(interfaces, list) else None
            capabilities['capabilities']['interfaces'] = True
        except Exception as exc:
            capabilities['interface_count'] = None
            capabilities.setdefault('errors', {})['interfaces'] = str(exc)

        try:
            iface = self.ntop_client.get_interface(0)
            iface.get_active_hosts_paginated(1, 1)
            capabilities['capabilities']['active_hosts'] = True
            capabilities['capabilities']['host_data'] = True
            capabilities['capabilities']['timeseries'] = True
        except Exception as exc:
            capabilities.setdefault('errors', {})['interface_probe'] = str(exc)

        try:
            hist = self.ntop_client.get_historical_interface(0)
            now = int(__import__('time').time())
            hist.get_alert_severity_counters(now - 3600, now)
            capabilities['capabilities']['alerts'] = True
        except Exception as exc:
            capabilities.setdefault('errors', {})['alerts_probe'] = str(exc)

        try:
            iface = self.ntop_client.get_interface(0)
            iface.get_top_local_talkers()
            capabilities['capabilities']['historical_flows'] = True
        except Exception:
            pass

        return capabilities

    def get_active_hosts(self, ifid: int = 0, limit: int = 100, host_filter: str | None = None) -> dict[str, Any]:
        if hasattr(self.ntop_client, 'get_interface'):
            payload = self.ntop_client.get_interface(ifid).get_active_hosts_paginated(1, limit)
        else:
            payload = self.ntop_client.get_active_hosts(ifid=ifid, per_page=limit)
        raw_rows = payload.get('data', []) if isinstance(payload, dict) else []
        rows = [self._normalize_host_row(row) for row in raw_rows if isinstance(row, dict)]
        if host_filter:
            host_filter = host_filter.lower()
            rows = [
                row for row in rows
                if host_filter in str(row.get('ip', '')).lower()
                or host_filter in str(row.get('hostname', '')).lower()
                or host_filter in str(row.get('ntop_host_key', '')).lower()
            ]
        return {
            'ifid': ifid,
            'total_active_hosts': len(rows),
            'hosts': rows,
            'applied_filters': {'host': host_filter},
        }

    def resolve_host_identity(self, target: str, ifid: int = 0, limit: int = 200) -> dict[str, Any]:
        target = (target or '').strip()
        if not target:
            raise RuntimeError('Missing host target for ntopng resolution')

        matches: list[dict[str, Any]] = []
        sources: list[str] = []
        normalized_target = target.lower()
        target_ip: str | None = None
        try:
            target_ip = str(ipaddress.ip_address(target))
        except ValueError:
            target_ip = None

        if self.pfsense_client is not None:
            try:
                pf_devices = self.pfsense_client.get_connected_devices().get('devices', [])
                for device in pf_devices:
                    hostname = str(device.get('hostname') or device.get('dnsresolve') or '').lower()
                    ip_value = str(device.get('ip_address') or device.get('ip') or '').strip()
                    if normalized_target in {hostname, ip_value.lower(), str(device.get('dnsresolve', '')).lower()}:
                        sources.append('pfsense_devices')
                        matches.append({
                            'ip': ip_value,
                            'hostname': device.get('hostname') or device.get('dnsresolve'),
                            'vlan': 0,
                            'ntop_host_key': self._host_key(ip_value, 0),
                        })
            except Exception:
                pass

        ntop_hosts = self.get_active_hosts(ifid=ifid, limit=limit).get('hosts', [])
        for row in ntop_hosts:
            if normalized_target in {
                str(row.get('ip', '')).lower(),
                str(row.get('hostname', '')).lower(),
                str(row.get('ntop_host_key', '')).lower(),
            }:
                sources.append('ntopng_active_hosts')
                matches.append(row)
            elif target_ip and row.get('ip') == target_ip:
                sources.append('ntopng_active_hosts')
                matches.append(row)

        dedup: dict[tuple[str, int], dict[str, Any]] = {}
        for match in matches:
            ip_value = str(match.get('ip') or '').strip()
            vlan = self._extract_vlan(match.get('vlan', 0))
            if ip_value:
                dedup[(ip_value, vlan)] = match

        if dedup:
            best = next(iter(dedup.values()))
            return {
                'input': target,
                'resolved_ip': best.get('ip'),
                'resolved_hostname': best.get('hostname'),
                'resolved_vlan': best.get('vlan', 0),
                'ntop_host_key': best.get('ntop_host_key') or self._host_key(str(best.get('ip')), self._extract_vlan(best.get('vlan', 0))),
                'sources': sorted(set(sources)),
                'confidence': 'high' if len(set(sources)) > 1 else 'medium',
                'candidates': list(dedup.values()),
            }

        if target_ip:
            return {
                'input': target,
                'resolved_ip': target_ip,
                'resolved_hostname': None,
                'resolved_vlan': 0,
                'ntop_host_key': self._host_key(target_ip, 0),
                'sources': [],
                'confidence': 'low',
                'candidates': [],
            }

        raise RuntimeError(f'Unable to resolve host identity for {target!r}')

    def get_host_summary(self, target: str, ifid: int = 0) -> dict[str, Any]:
        identity = self.resolve_host_identity(target=target, ifid=ifid)
        host_param = identity.get('resolved_ip') or target
        if hasattr(self.ntop_client, 'get_interface'):
            payload = self.ntop_client.get_interface(ifid).get_host_data(host_param)
        else:
            payload = self.ntop_client.get_host_data(host=host_param, ifid=ifid)
        seen = payload.get('seen', {}) if isinstance(payload, dict) else {}
        seen_first = seen.get('first') if isinstance(seen, dict) else None
        seen_last = seen.get('last') if isinstance(seen, dict) else None
        if seen_first is None:
            seen_first = payload.get('seen.first')
        if seen_last is None:
            seen_last = payload.get('seen.last')

        bytes_block = payload.get('bytes', {}) if isinstance(payload.get('bytes'), dict) else {}
        bytes_total = bytes_block.get('total', payload.get('bytes.total'))
        bytes_sent = bytes_block.get('sent', payload.get('bytes.sent'))
        bytes_received = bytes_block.get('rcvd') if 'rcvd' in bytes_block else bytes_block.get('received', payload.get('bytes.rcvd'))
        host_name = payload.get('name')
        if host_name in (0, '0', None, ''):
            host_name = None
        return {
            'host': {
                'input': target,
                'ip': payload.get('ip') or identity.get('resolved_ip') or target,
                'hostname': identity.get('resolved_hostname') or host_name or payload.get('ip') or target,
                'vlan': identity.get('resolved_vlan', 0),
                'ntop_host_key': identity.get('ntop_host_key'),
                'status': 'active' if seen_last else 'unknown',
            },
            'activity': {
                'first_seen_epoch': seen_first,
                'last_seen_epoch': seen_last,
                'bytes_total': bytes_total,
                'bytes_sent': bytes_sent,
                'bytes_received': bytes_received,
                'flows_as_client': payload.get('flows.as_client'),
                'flows_as_server': payload.get('flows.as_server'),
                'active_alerted_flows': payload.get('active_alerted_flows'),
            },
            'network': {
                'asn': payload.get('asn'),
                'asname': payload.get('asname'),
                'country': payload.get('country'),
                'blacklisted': payload.get('is_blacklisted'),
            },
            'resolution': identity,
            'confidence': identity.get('confidence', 'medium'),
        }
