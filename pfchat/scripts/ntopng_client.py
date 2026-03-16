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

    def __init__(self, base_url: str, username: str | None = None, password: str | None = None, auth_token: str | None = None, verify_ssl: bool = False):
        self.base_url = base_url.rstrip('/')
        self.username = username or ''
        self.password = password or ''
        self.auth_token = auth_token or ''
        self.ssl_ctx = ssl.create_default_context()
        if not verify_ssl:
            self.ssl_ctx.check_hostname = False
            self.ssl_ctx.verify_mode = ssl.CERT_NONE

    def _headers(self) -> dict[str, str]:
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
        }
        if self.auth_token:
            headers['Authorization'] = f'Token {self.auth_token}'
            return headers
        token = base64.b64encode(f'{self.username}:{self.password}'.encode()).decode()
        headers['Authorization'] = f'Basic {token}'
        return headers

    def _request(self, method: str, path: str, params: dict[str, Any] | None = None, body: Any = None) -> Any:
        url = f"{self.base_url}/{path.lstrip('/')}"
        if params:
            url = f"{url}?{urllib.parse.urlencode(params, doseq=True)}"
        data = None
        if body is not None:
            data = json.dumps(body).encode()
        req = urllib.request.Request(url, headers=self._headers(), method=method.upper(), data=data)
        try:
            with urllib.request.urlopen(req, context=self.ssl_ctx, timeout=20) as resp:
                raw = resp.read().decode(errors='replace')
                raw_stripped = raw.lstrip()
                if raw_stripped.startswith('<!DOCTYPE html') or raw_stripped.startswith('<html'):
                    raise RuntimeError(
                        'ntopng returned an HTML login page instead of JSON. Enable HTTP API auth on ntopng or configure NTOPNG_AUTH_TOKEN.'
                    )
                try:
                    data = json.loads(raw) if raw else {}
                except json.JSONDecodeError as exc:
                    preview = raw_stripped[:160].replace('\n', ' ')
                    raise RuntimeError(f'ntopng returned non-JSON content on {path}: {preview}') from exc
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

    def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        return self._request('GET', path, params=params)

    def _post(self, path: str, params: dict[str, Any] | None = None, body: Any = None) -> Any:
        return self._request('POST', path, params=params, body=body)

    @staticmethod
    def _unwrap(data: Any) -> Any:
        if isinstance(data, dict) and 'rsp' in data:
            return data['rsp']
        return data

    def probe(self, method: str, path: str, params: dict[str, Any] | None = None, body: Any = None) -> dict[str, Any]:
        try:
            data = self._request(method, path, params=params, body=body)
            return {'ok': True, 'path': path, 'method': method.upper(), 'sample_type': type(self._unwrap(data)).__name__}
        except Exception as exc:
            return {'ok': False, 'path': path, 'method': method.upper(), 'error': str(exc)}

    def get_interfaces(self) -> list[dict[str, Any]]:
        return self._unwrap(self._get('lua/rest/v1/get/ntopng/interfaces.lua'))

    def get_active_hosts(self, ifid: int = 0, per_page: int = 100) -> dict[str, Any]:
        return self._unwrap(self._get('lua/rest/v1/get/host/active.lua', {'ifid': ifid, 'perPage': per_page}))

    def get_host_data(self, host: str, ifid: int = 0) -> dict[str, Any]:
        return self._unwrap(self._get('lua/rest/v1/get/host/data.lua', {'ifid': ifid, 'host': host}))

    def get_timeseries_probe(self, ifid: int = 0) -> Any:
        return self._unwrap(self._get('lua/rest/v1/get/interface/data.lua', {'ifid': ifid}))

    def get_capabilities(self) -> dict[str, Any]:
        interface_probe = self.probe('GET', 'lua/rest/v1/get/ntopng/interfaces.lua')
        active_hosts_probe = self.probe('GET', 'lua/rest/v1/get/host/active.lua', {'ifid': 0, 'perPage': 1})
        host_data_probe = self.probe('GET', 'lua/rest/v1/get/host/data.lua', {'ifid': 0, 'host': '127.0.0.1'})
        timeseries_probe = self.probe('GET', 'lua/rest/v1/get/interface/data.lua', {'ifid': 0})
        rest_v2_probe = self.probe('GET', 'lua/rest/v2/get/host/active')
        alerts_probe = self.probe('GET', 'lua/rest/v2/get/alert/summary')
        historical_probe = self.probe('GET', 'lua/pro/rest/v2/get/flow/historical/top_talkers')

        interface_count = None
        if interface_probe.get('ok'):
            try:
                interfaces = self.get_interfaces()
                interface_count = len(interfaces) if isinstance(interfaces, list) else None
            except Exception:
                interface_count = None

        return {
            'ntopng_available': True,
            'capabilities': {
                'rest_v1': any(p.get('ok') for p in [interface_probe, active_hosts_probe, host_data_probe]),
                'rest_v2': rest_v2_probe.get('ok', False),
                'interfaces': interface_probe.get('ok', False),
                'active_hosts': active_hosts_probe.get('ok', False),
                'host_data': host_data_probe.get('ok', False),
                'alerts': alerts_probe.get('ok', False),
                'timeseries': timeseries_probe.get('ok', False),
                'historical_flows': historical_probe.get('ok', False),
            },
            'interface_count': interface_count,
            'probes': {
                'interfaces_v1': interface_probe,
                'active_hosts_v1': active_hosts_probe,
                'host_data_v1': host_data_probe,
                'interface_data_v1': timeseries_probe,
                'active_hosts_v2': rest_v2_probe,
                'alerts_v2': alerts_probe,
                'historical_flows_pro_v2': historical_probe,
            },
        }
