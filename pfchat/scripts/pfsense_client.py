#!/usr/bin/env python3
"""Reusable pfSense REST API client for the PfChat skill."""

from __future__ import annotations

import ipaddress
import json
import ssl
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


class PfSenseClient:
    """Thin wrapper around the pfSense REST API with endpoint fallbacks and schema-aware discovery."""

    def __init__(self, host: str, api_key: str, verify_ssl: bool = False):
        self.base_url = f"https://{host.rstrip('/')}/api/v2"
        self.api_key = api_key
        self.ssl_ctx = ssl.create_default_context()
        if not verify_ssl:
            self.ssl_ctx.check_hostname = False
            self.ssl_ctx.verify_mode = ssl.CERT_NONE
        self._openapi_schema: dict[str, Any] | None = None
        self._supported_paths: set[str] | None = None

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
            self._openapi_schema = self._unwrap(self._get("schema/openapi"))
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
            "status/arp",
            "status/arp-table",
            "diag/arp",
            "diagnostics/arp",
        ])

    def get_dhcp_leases(self) -> list[dict[str, Any]]:
        return self._get_first_supported([
            "status/dhcp_server/leases",
            "services/dhcpd/leases",
            "status/dhcp_leases",
            "status/dhcp/leases",
        ])

    def get_firewall_states(self, limit: int = 100, filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"limit": limit}
        if filters:
            params.update(filters)
        return self._unwrap(self._get("firewall/states", params))

    def get_firewall_logs(self, limit: int = 200) -> list[dict[str, Any]]:
        return self._get_first_supported([
            "status/logs/firewall",
            "status/log/firewall",
            "log/firewall",
        ], {"limit": limit})

    def get_interfaces(self) -> list[dict[str, Any]]:
        return self._get_first_supported([
            "status/interfaces",
        ])

    def get_system_stats(self) -> dict[str, Any]:
        return self._get_first_supported([
            "system/stats",
            "status/system",
        ])

    def get_gateways(self) -> list[dict[str, Any]]:
        return self._get_first_supported([
            "status/gateways",
            "routing/gateways",
            "status/gateway",
            "system/gateways",
        ])

    def get_firewall_rules(self, filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        if filters:
            return self._unwrap(self._get("firewall/rules", filters))
        return self._unwrap(self._get("firewall/rules"))

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

    def _infer_connected_devices_from_states(self, limit: int = 500) -> dict[str, Any]:
        """Build a lightweight device inventory from active firewall states when ARP/DHCP endpoints are unavailable."""
        states = self.get_firewall_states(limit=limit)
        devices: dict[str, dict[str, Any]] = {}

        for state in states:
            if not isinstance(state, dict):
                continue
            for field in ("source", "destination"):
                ip = self._extract_ip(state.get(field, ""))
                if not ip:
                    continue
                try:
                    parsed_ip = ipaddress.ip_address(ip)
                except ValueError:
                    continue
                if parsed_ip.is_private and not parsed_ip.is_loopback and not parsed_ip.is_multicast and not parsed_ip.is_unspecified:
                    if str(parsed_ip).endswith('.255'):
                        continue
                    row = devices.setdefault(ip, {
                        "ip": ip,
                        "hostname": "(inferred-from-states)",
                        "source": "firewall_states_fallback",
                        "seen_in_states": 0,
                    })
                    row["seen_in_states"] += 1

        inferred = sorted(devices.values(), key=lambda item: (-item["seen_in_states"], item["ip"]))
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
            arp_message = str(arp_error)
            if arp_message.startswith("HTTP 404 on "):
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
            "capabilities": {
                "devices_arp": any(path in supported for path in ["diagnostics/arp_table", "status/arp", "status/arp-table", "diag/arp", "diagnostics/arp"]),
                "devices_dhcp": any(path in supported for path in ["status/dhcp_server/leases", "services/dhcpd/leases", "status/dhcp_leases", "status/dhcp/leases"]),
                "connections": "firewall/states" in supported,
                "logs_firewall": any(path in supported for path in ["status/logs/firewall", "status/log/firewall", "log/firewall"]),
                "rules": "firewall/rules" in supported,
                "interfaces": "status/interfaces" in supported,
                "system_status": any(path in supported for path in ["status/system", "system/stats"]),
                "gateways": any(path in supported for path in ["status/gateways", "routing/gateways", "status/gateway", "system/gateways"]),
            },
        }

    def get_snapshot(self, limit: int = 150) -> dict[str, Any]:
        snapshot: dict[str, Any] = {"errors": {}}

        for key, func in {
            "capabilities": self.get_capabilities,
            "devices": self.get_connected_devices,
            "connections": lambda: {
                "total_active_connections": len(self.get_firewall_states(limit=limit)),
                "connections": self.get_firewall_states(limit=limit),
            },
            "logs": lambda: {
                "total_entries": len(self.get_firewall_logs(limit=limit)),
                "logs": self.get_firewall_logs(limit=limit),
            },
            "health": self.get_health_bundle,
            "rules": lambda: {
                "total_rules": len(self.get_firewall_rules()),
                "rules": self.get_firewall_rules(),
            },
        }.items():
            try:
                snapshot[key] = func()
            except Exception as exc:
                snapshot["errors"][key] = str(exc)

        return snapshot
