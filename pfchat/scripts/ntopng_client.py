#!/usr/bin/env python3
"""Reusable ntopng REST client for PfChat."""

from __future__ import annotations

import base64
import json
import ssl
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


class NtopngClient:
    """Thin wrapper around ntopng REST API endpoints used by PfChat."""

    def __init__(self, base_url: str, username: str, password: str, verify_ssl: bool = False):
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.password = password
        self.ssl_ctx = ssl.create_default_context()
        if not verify_ssl:
            self.ssl_ctx.check_hostname = False
            self.ssl_ctx.verify_mode = ssl.CERT_NONE

    def _headers(self) -> dict[str, str]:
        token = base64.b64encode(f'{self.username}:{self.password}'.encode()).decode()
        return {
            'Authorization': f'Basic {token}',
            'Accept': 'application/json',
            'Content-Type': 'application/json',
        }

    def _request(self, path: str, params: dict[str, Any] | None = None) -> Any:
        url = f"{self.base_url}/{path.lstrip('/')}"
        if params:
            url = f"{url}?{urllib.parse.urlencode(params, doseq=True)}"
        req = urllib.request.Request(url, headers=self._headers(), method='GET')
        try:
            with urllib.request.urlopen(req, context=self.ssl_ctx, timeout=20) as resp:
                raw = resp.read().decode()
                data = json.loads(raw) if raw else {}
        except urllib.error.HTTPError as exc:
            body_text = exc.read().decode(errors='replace')
            if exc.code in (401, 403):
                raise RuntimeError('Authentication failed against ntopng REST API') from exc
            raise RuntimeError(f'HTTP {exc.code} on ntopng path {path}: {body_text[:400]}') from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f'Cannot connect to ntopng: {exc.reason}') from exc

        if isinstance(data, dict) and 'rc' in data and data.get('rc') not in (0, '0', None):
            raise RuntimeError(f"ntopng API error on {path}: {data.get('rc_str') or data.get('error') or data.get('rc')}")
        return data

    @staticmethod
    def _unwrap(data: Any) -> Any:
        if isinstance(data, dict) and 'rsp' in data:
            return data['rsp']
        return data

    def get_interfaces(self) -> list[dict[str, Any]]:
        return self._unwrap(self._request('lua/rest/v1/get/ntopng/interfaces.lua'))

    def get_active_hosts(self, ifid: int = 0, per_page: int = 100) -> dict[str, Any]:
        return self._unwrap(self._request('lua/rest/v1/get/host/active.lua', {'ifid': ifid, 'perPage': per_page}))

    def get_host_data(self, host: str, ifid: int = 0) -> dict[str, Any]:
        return self._unwrap(self._request('lua/rest/v1/get/host/data.lua', {'ifid': ifid, 'host': host}))

    def get_capabilities(self) -> dict[str, Any]:
        interface_count = None
        try:
            interfaces = self.get_interfaces()
            interface_count = len(interfaces) if isinstance(interfaces, list) else None
        except Exception:
            interfaces = None
        return {
            'ntopng_available': True,
            'capabilities': {
                'interfaces': interfaces is not None,
                'active_hosts': True,
                'host_data': True,
                'historical_flows': False,
            },
            'interface_count': interface_count,
        }

    def summarize_host(self, host: str, ifid: int = 0) -> dict[str, Any]:
        payload = self.get_host_data(host=host, ifid=ifid)
        seen = payload.get('seen', {}) if isinstance(payload, dict) else {}
        bytes_block = payload.get('bytes', {}) if isinstance(payload, dict) else {}
        return {
            'host': payload.get('ip', host),
            'ifid': ifid,
            'name': payload.get('name') or payload.get('ip', host),
            'seen_first_epoch': seen.get('first'),
            'seen_last_epoch': seen.get('last'),
            'bytes': {
                'total': bytes_block.get('total'),
                'sent': bytes_block.get('sent'),
                'received': bytes_block.get('rcvd'),
            },
            'flows': {
                'as_client': payload.get('flows.as_client'),
                'as_server': payload.get('flows.as_server'),
                'total_server': payload.get('total_flows.as_server'),
            },
            'asn': payload.get('asn'),
            'asname': payload.get('asname'),
            'country': payload.get('country'),
            'is_blacklisted': payload.get('is_blacklisted'),
        }
