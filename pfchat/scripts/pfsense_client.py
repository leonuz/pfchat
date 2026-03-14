#!/usr/bin/env python3
"""Reusable pfSense REST API client for the PfChat skill."""

from __future__ import annotations

import hashlib
import ipaddress
import json
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


class PfSenseClient:
    """Thin wrapper around the pfSense REST API with endpoint fallbacks and schema-aware discovery."""

    def __init__(self, host: str, api_key: str, verify_ssl: bool = False):
        self.host = host.rstrip('/')
        self.base_url = f"https://{self.host}/api/v2"
        self.api_key = api_key
        self.ssl_ctx = ssl.create_default_context()
        if not verify_ssl:
            self.ssl_ctx.check_hostname = False
            self.ssl_ctx.verify_mode = ssl.CERT_NONE
        self._openapi_schema: dict[str, Any] | None = None
        self._supported_paths: set[str] | None = None
        self._cache_ttl_seconds = 3600
        self._cache_dir = Path(__file__).resolve().parents[1] / '.cache'
        self._cache_dir.mkdir(parents=True, exist_ok=True)

    def _schema_cache_path(self) -> Path:
        digest = hashlib.sha256(f'{self.host}|{self.base_url}'.encode()).hexdigest()[:16]
        return self._cache_dir / f'openapi-schema-{digest}.json'

    def _read_cached_schema(self) -> dict[str, Any] | None:
        path = self._schema_cache_path()
        if not path.exists():
            return None
        try:
            payload = json.loads(path.read_text(encoding='utf-8'))
        except Exception:
            return None
        fetched_at = payload.get('fetched_at')
        schema = payload.get('schema')
        if not isinstance(fetched_at, (int, float)) or not isinstance(schema, dict):
            return None
        if time.time() - fetched_at > self._cache_ttl_seconds:
            return None
        return schema

    def _write_cached_schema(self, schema: dict[str, Any]) -> None:
        payload = {
            'fetched_at': time.time(),
            'host': self.host,
            'schema': schema,
        }
        self._schema_cache_path().write_text(json.dumps(payload, indent=2), encoding='utf-8')

    def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        url = f"{self.base_url}/{path.lstrip('/')}"
        if params:
            url = f"{url}?{urllib.parse.urlencode(params, doseq=True)}"

        req = urllib.request.Request(
            url,
            headers={
                "X-API-Key": self.api_key,
                "Accept": "application/json",
            },
        )

        try:
            with urllib.request.urlopen(req, context=self.ssl_ctx, timeout=20) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as exc:
            body = exc.read().decode(errors="replace")
            if exc.code in (401, 403):
                raise RuntimeError("Authentication failed against pfSense REST API") from exc
            raise RuntimeError(f"HTTP {exc.code} on {path}: {body[:400]}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Cannot connect to pfSense: {exc.reason}") from exc

    @staticmethod
    def _unwrap(data: Any) -> Any:
        return data.get("data", data) if isinstance(data, dict) else data

    def get_openapi_schema(self, force_refresh: bool = False) -> dict[str, Any]:
        """Fetch and cache the live OpenAPI schema when available."""
        if self._openapi_schema is None or force_refresh:
            schema: dict[str, Any] | None = None
            if not force_refresh:
                schema = self._read_cached_schema()
            if schema is None:
                schema = self._unwrap(self._get("schema/openapi"))
                if isinstance(schema, dict):
                    self._write_cached_schema(schema)
            self._openapi_schema = schema
            paths = self._openapi_schema.get("paths", {}) if isinstance(self._openapi_schema, dict) else {}
            self._supported_paths = {
                path.removeprefix("/api/v2/").lstrip("/")
                for path in paths.keys()
                if isinstance(path, str)
            }
        return self._openapi_schema

    def get_supported_paths(self, force_refresh: bool = False) -> set[str]:
        if self._supported_paths is None or force_refresh:
            self.get_openapi_schema(force_refresh=force_refresh)
        return self._supported_paths or set()

    def _filter_candidates_by_schema(self, paths: list[str]) -> list[str]:
        """Prefer paths confirmed by the live OpenAPI schema, but keep legacy fallbacks if schema is unavailable."""
        try:
            supported = self.get_supported_paths()
        except Exception:
            return paths
        matched = [path for path in paths if path in supported]
        return matched or paths

    def _get_first_supported(self, paths: list[str], params: dict[str, Any] | None = None) -> Any:
        """Try endpoint candidates in order and stop only on real not-found cases."""
        last_not_found: RuntimeError | None = None
        for path in self._filter_candidates_by_schema(paths):
            try:
                return self._unwrap(self._get(path, params))
            except RuntimeError as exc:
                message = str(exc)
                if message.startswith("HTTP 404 on "):
                    last_not_found = exc
                    continue
                raise
        if last_not_found is not None:
            raise last_not_found
        raise RuntimeError("No supported endpoint candidates were provided")

    def get_arp_table(self) -> list[dict[str, Any]]:
        return self._get_first_supported([
            "diagnostics/arp_table",
            "diagnostics/arp_table/entry",
            "status/arp",
            "status/arp-table",
            "diag/arp",
            "diagnostics/arp",
        ])

    def get_dhcp_leases(self) -> list[dict[str, Any]]:
        return self._get_first_supported([
            "status/dhcp_server/leases",
            "services/dhcp_server/leases",
            "services/dhcpd/leases",
            "status/dhcp_leases",
            "status/dhcp/leases",
        ])

    def get_firewall_states(self, limit: int = 100, filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"limit": limit}
        if filters:
            params.update(filters)
        return self._get_first_supported([
            "firewall/states",
            "firewall/state",
        ], params)

    def get_firewall_logs(self, limit: int = 200) -> list[dict[str, Any]]:
        return self._get_first_supported([
            "status/logs/firewall",
            "status/log/firewall",
            "log/firewall",
        ], {"limit": limit})

    def get_interfaces(self) -> list[dict[str, Any]]:
        return self._get_first_supported([
            "status/interfaces",
            "interfaces",
            "interface",
        ])

    def get_system_stats(self) -> dict[str, Any]:
        return self._get_first_supported([
            "status/system",
            "system/stats",
            "system/status",
        ])

    def get_gateways(self) -> list[dict[str, Any]]:
        return self._get_first_supported([
            "status/gateways",
            "routing/gateways",
            "routing/gateway",
            "status/gateway",
            "system/gateways",
        ])

    def get_firewall_rules(self, filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        return self._get_first_supported([
            "firewall/rules",
            "firewall/rule",
        ], filters)

    @staticmethod
    def _extract_ip(value: str) -> str:
        """Extract the IP portion from values like 192.168.0.91:443 or [IPv6]:443."""
        value = str(value or "").strip()
        if not value:
            return ""
        if value.startswith("[") and "]" in value:
            return value[1:].split("]", 1)[0]
        if value.count(":") == 1:
            return value.rsplit(":", 1)[0]
        return value

    @staticmethod
    def _normalize_hostname(value: Any) -> str:
        name = str(value or '').strip()
        if not name:
            return ''
        lowered = name.lower()
        if lowered in {'?', '(null)', 'unknown', '(unknown)', 'none'}:
            return ''
        return name

    def _infer_connected_devices_from_states(self, limit: int = 500) -> dict[str, Any]:
        states = self.get_firewall_states(limit=limit)
        devices: dict[str, dict[str, Any]] = {}

        for state in states:
            if not isinstance(state, dict):
                continue
            interface = state.get('interface') or state.get('if') or ''
            direction = str(state.get('direction') or '').lower()
            for field, peer_field in (("source", "destination"), ("destination", "source")):
                ip = self._extract_ip(state.get(field, ""))
                peer_ip = self._extract_ip(state.get(peer_field, ""))
                if not ip:
                    continue
                try:
                    parsed_ip = ipaddress.ip_address(ip)
                except ValueError:
                    continue
                if not parsed_ip.is_private or parsed_ip.is_loopback or parsed_ip.is_multicast or parsed_ip.is_unspecified:
                    continue
                if str(parsed_ip).endswith('.255'):
                    continue

                row = devices.setdefault(ip, {
                    "ip": ip,
                    "hostname": "",
                    "source": "firewall_states_fallback",
                    "seen_in_states": 0,
                    "seen_as_source": 0,
                    "seen_as_destination": 0,
                    "interfaces": set(),
                    "peers": set(),
                    "confidence": "low",
                })
                row["seen_in_states"] += 1
                row["interfaces"].add(str(interface))
                if peer_ip:
                    row["peers"].add(peer_ip)
                if field == 'source':
                    row["seen_as_source"] += 1
                else:
                    row["seen_as_destination"] += 1

                for candidate in (
                    state.get('source_host') if field == 'source' else state.get('destination_host'),
                    state.get('source_name') if field == 'source' else state.get('destination_name'),
                    state.get('host'),
                    state.get('hostname'),
                    state.get('dnsresolve'),
                ):
                    normalized = self._normalize_hostname(candidate)
                    if normalized:
                        row['hostname'] = normalized
                        break

                if row['seen_as_source'] > 0 and row['seen_as_destination'] > 0:
                    row['confidence'] = 'medium'
                if row['seen_in_states'] >= 3:
                    row['confidence'] = 'medium'

        inferred: list[dict[str, Any]] = []
        for item in devices.values():
            inferred.append({
                "ip": item["ip"],
                "hostname": item["hostname"] or "(inferred-from-states)",
                "source": item["source"],
                "seen_in_states": item["seen_in_states"],
                "seen_as_source": item["seen_as_source"],
                "seen_as_destination": item["seen_as_destination"],
                "interfaces": sorted(x for x in item["interfaces"] if x),
                "peer_count": len(item["peers"]),
                "confidence": item["confidence"],
            })

        inferred.sort(key=lambda item: (-item["seen_in_states"], -item["peer_count"], item["ip"]))
        return {
            "total_devices": len(inferred),
            "devices": inferred,
            "dhcp_leases_total": 0,
            "degraded": True,
            "degraded_reason": "ARP/DHCP endpoints are not exposed by this pfSense REST API installation; inventory inferred from active firewall states.",
        }

    def get_connected_devices(self) -> dict[str, Any]:
        try:
            arp = self.get_arp_table()
        except RuntimeError as arp_error:
            if str(arp_error).startswith("HTTP 404 on "):
                return self._infer_connected_devices_from_states()
            raise

        try:
            leases = self.get_dhcp_leases()
        except RuntimeError as leases_error:
            if not str(leases_error).startswith("HTTP 404 on "):
                raise
            leases = []

        lease_by_mac = {
            str(item.get("mac_address") or item.get("mac", "")).lower(): item
            for item in leases
            if isinstance(item, dict)
        }

        enriched: list[dict[str, Any]] = []
        for entry in arp:
            if not isinstance(entry, dict):
                continue
            row = dict(entry)
            mac = str(row.get("mac_address") or row.get("mac", "")).lower()
            lease = lease_by_mac.get(mac, {})
            row["hostname"] = (
                lease.get("hostname")
                or row.get("hostname")
                or row.get("dnsresolve")
                or "(unknown)"
            )
            row["lease_end"] = lease.get("end") or lease.get("lease_end", "")
            row["lease_type"] = lease.get("type", "")
            row["source"] = "arp_dhcp"
            enriched.append(row)

        return {
            "total_devices": len(enriched),
            "devices": enriched,
            "dhcp_leases_total": len(leases),
            "degraded": False,
        }

    def get_health_bundle(self) -> dict[str, Any]:
        return {
            "system": self.get_system_stats(),
            "gateways": self.get_gateways(),
            "interfaces": self.get_interfaces(),
        }

    def get_capabilities(self) -> dict[str, Any]:
        supported = sorted(self.get_supported_paths())
        return {
            "openapi_available": bool(supported),
            "supported_paths": supported,
            "schema_cache": {
                "path": str(self._schema_cache_path()),
                "ttl_seconds": self._cache_ttl_seconds,
                "exists": self._schema_cache_path().exists(),
            },
            "capabilities": {
                "devices_arp": any(path in supported for path in ["diagnostics/arp_table", "diagnostics/arp_table/entry", "status/arp", "status/arp-table", "diag/arp", "diagnostics/arp"]),
                "devices_dhcp": any(path in supported for path in ["status/dhcp_server/leases", "services/dhcp_server/leases", "services/dhcpd/leases", "status/dhcp_leases", "status/dhcp/leases"]),
                "connections": any(path in supported for path in ["firewall/states", "firewall/state"]),
                "logs_firewall": any(path in supported for path in ["status/logs/firewall", "status/log/firewall", "log/firewall"]),
                "rules": any(path in supported for path in ["firewall/rules", "firewall/rule"]),
                "interfaces": any(path in supported for path in ["status/interfaces", "interfaces", "interface"]),
                "system_status": any(path in supported for path in ["status/system", "system/stats", "system/status"]),
                "gateways": any(path in supported for path in ["status/gateways", "routing/gateways", "routing/gateway", "status/gateway", "system/gateways"]),
            },
        }

    def summarize_snapshot(self, snapshot: dict[str, Any], top_n: int = 5) -> dict[str, Any]:
        health = snapshot.get('health', {}) if isinstance(snapshot, dict) else {}
        gateways = health.get('gateways', []) if isinstance(health, dict) else []
        interfaces = health.get('interfaces', []) if isinstance(health, dict) else []
        devices = snapshot.get('devices', {}).get('devices', []) if isinstance(snapshot.get('devices', {}), dict) else []
        logs = snapshot.get('logs', {}).get('logs', []) if isinstance(snapshot.get('logs', {}), dict) else []
        connections = snapshot.get('connections', {}).get('connections', []) if isinstance(snapshot.get('connections', {}), dict) else []

        wan = next((item for item in interfaces if str(item.get('name', '')).lower() == 'wan'), None)
        online_gateways = [gw.get('name') for gw in gateways if str(gw.get('status', '')).lower() == 'online']
        blocked_logs = [item for item in logs if 'block' in str(item.get('text', '')).lower()]
        top_devices = sorted(
            devices,
            key=lambda d: int(d.get('seen_in_states', 0) or 0),
            reverse=True,
        )[:top_n]
        top_flows = sorted(
            connections,
            key=lambda c: int(c.get('bytes_total', 0) or 0),
            reverse=True,
        )[:top_n]

        highlights: list[str] = []
        if wan:
            highlights.append(
                f"WAN {wan.get('ipaddr')} via {wan.get('gateway')} is {wan.get('status')}"
            )
        if online_gateways:
            highlights.append(f"Online gateways: {', '.join(str(x) for x in online_gateways)}")
        if top_devices:
            device_names = [
                str(d.get('hostname') or d.get('ip') or d.get('ip_address') or '(unknown)')
                for d in top_devices[:3]
            ]
            highlights.append(f"Top active devices: {', '.join(device_names)}")
        if blocked_logs:
            highlights.append(f"Blocked log entries in sample: {len(blocked_logs)}")
        if snapshot.get('errors'):
            highlights.append(f"Partial data warnings: {len(snapshot['errors'])}")

        return {
            'wan': {
                'ipaddr': wan.get('ipaddr') if wan else None,
                'gateway': wan.get('gateway') if wan else None,
                'status': wan.get('status') if wan else None,
            },
            'gateway_status': {
                'online': online_gateways,
                'total': len(gateways),
            },
            'device_summary': {
                'total_devices': snapshot.get('devices', {}).get('total_devices') if isinstance(snapshot.get('devices', {}), dict) else None,
                'degraded': snapshot.get('devices', {}).get('degraded') if isinstance(snapshot.get('devices', {}), dict) else None,
                'top_active_devices': top_devices,
            },
            'connection_summary': {
                'total_active_connections': snapshot.get('connections', {}).get('total_active_connections') if isinstance(snapshot.get('connections', {}), dict) else None,
                'top_flows': top_flows,
            },
            'log_summary': {
                'total_entries': snapshot.get('logs', {}).get('total_entries') if isinstance(snapshot.get('logs', {}), dict) else None,
                'blocked_entries_in_sample': len(blocked_logs),
            },
            'rule_summary': {
                'total_rules': snapshot.get('rules', {}).get('total_rules') if isinstance(snapshot.get('rules', {}), dict) else None,
            },
            'highlights': highlights,
        }

    def get_snapshot(self, limit: int = 150) -> dict[str, Any]:
        snapshot: dict[str, Any] = {'errors': {}}

        for key, func in {
            'capabilities': self.get_capabilities,
            'devices': self.get_connected_devices,
            'connections': lambda: {
                'total_active_connections': len(self.get_firewall_states(limit=limit)),
                'connections': self.get_firewall_states(limit=limit),
            },
            'logs': lambda: {
                'total_entries': len(self.get_firewall_logs(limit=limit)),
                'logs': self.get_firewall_logs(limit=limit),
            },
            'health': self.get_health_bundle,
            'rules': lambda: {
                'total_rules': len(self.get_firewall_rules()),
                'rules': self.get_firewall_rules(),
            },
        }.items():
            try:
                snapshot[key] = func()
            except Exception as exc:
                snapshot['errors'][key] = str(exc)

        snapshot['summary'] = self.summarize_snapshot(snapshot)
        return snapshot
