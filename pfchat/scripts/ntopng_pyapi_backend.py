#!/usr/bin/env python3
"""Lightweight ntopng Python-API-style backend for PfChat.

Imitates the useful structure of the official ntopng Python API while keeping
control over SSL verification and avoiding heavyweight/reporting features.
"""

from __future__ import annotations

from typing import Any

import json
import requests
from requests.auth import HTTPBasicAuth


class NtopngPyApiBackend:
    def __init__(self, url: str, username: str | None = None, password: str | None = None, auth_token: str | None = None, verify_ssl: bool = False):
        self.url = url.rstrip('/')
        self.username = username or ''
        self.password = password or ''
        self.auth_token = auth_token or ''
        self.verify_ssl = verify_ssl
        self.rest_v2_url = '/lua/rest/v2'
        self.rest_pro_v2_url = '/lua/pro/rest/v2'

    def _headers(self) -> dict[str, str]:
        headers = {'Accept': 'application/json'}
        if self.auth_token:
            headers['Authorization'] = f'Token {self.auth_token}'
        return headers

    def _auth(self):
        if self.auth_token:
            return None
        return HTTPBasicAuth(self.username, self.password)

    @staticmethod
    def _extract_json_payload(text: str) -> dict[str, Any] | list[Any]:
        candidate = text.lstrip()
        if candidate.startswith('HTTP/1.1') or candidate.startswith('HTTP/1.0'):
            marker = candidate.find('\r\n\r\n')
            if marker != -1:
                candidate = candidate[marker + 4 :].lstrip()
        return json.loads(candidate)

    def _request(self, path: str, params: dict[str, Any] | None = None) -> Any:
        response = requests.get(
            self.url + path,
            params=params,
            auth=self._auth(),
            headers=self._headers(),
            verify=self.verify_ssl,
            timeout=20,
        )
        response.raise_for_status()
        ctype = response.headers.get('Content-Type', '')
        if 'application/json' not in ctype:
            raise RuntimeError(f'ntopng backend expected JSON on {path}, got {ctype}: {response.text[:160]}')
        try:
            payload = self._extract_json_payload(response.text)
        except Exception as exc:
            raise RuntimeError(f'ntopng backend could not parse JSON on {path}: {response.text[:200]}') from exc
        if isinstance(payload, dict) and payload.get('rc') not in (0, '0', None):
            raise RuntimeError(f"ntopng API error on {path}: {payload.get('rc_str') or payload.get('rc')}")
        return payload.get('rsp', payload)

    def self_test(self) -> Any:
        return self._request(self.rest_v2_url + '/connect/test.lua')

    def get_interfaces_list(self) -> list[dict[str, Any]]:
        return self._request(self.rest_v2_url + '/get/ntopng/interfaces.lua')

    def get_interface(self, ifid: int) -> 'PyApiInterface':
        return PyApiInterface(self, ifid)

    def get_historical_interface(self, ifid: int) -> 'PyApiHistorical':
        return PyApiHistorical(self, ifid)


class PyApiInterface:
    def __init__(self, backend: NtopngPyApiBackend, ifid: int):
        self.backend = backend
        self.ifid = ifid

    def get_data(self) -> dict[str, Any]:
        return self.backend._request(self.backend.rest_v2_url + '/get/interface/data.lua', {'ifid': self.ifid})

    def get_active_hosts(self) -> list[dict[str, Any]]:
        rsp = self.backend._request(self.backend.rest_v2_url + '/get/host/active.lua', {'ifid': self.ifid, 'all': 'true'})
        return rsp.get('data', []) if isinstance(rsp, dict) else []

    def get_active_hosts_paginated(self, current_page: int, per_page: int) -> dict[str, Any]:
        return self.backend._request(self.backend.rest_v2_url + '/get/host/active.lua', {'ifid': self.ifid, 'currentPage': current_page, 'perPage': per_page})

    def get_active_flows_paginated(self, current_page: int, per_page: int) -> dict[str, Any]:
        return self.backend._request(self.backend.rest_v2_url + '/get/flow/active.lua', {'ifid': self.ifid, 'currentPage': current_page, 'perPage': per_page})

    def get_l7_stats(self, max_num_results: int = 20) -> Any:
        return self.backend._request(self.backend.rest_v2_url + '/get/interface/l7/stats.lua', {
            'ifid': self.ifid,
            'ndpistats_mode': 'count',
            'breed': True,
            'ndpi_category': True,
            'all_values': True,
            'max_values': max_num_results,
            'collapse_stats': False,
        })

    def get_host_data(self, host_ip: str) -> dict[str, Any]:
        return self.backend._request(self.backend.rest_v2_url + '/get/host/data.lua', {'ifid': self.ifid, 'host': host_ip})

    def get_host_l7_stats(self, host_ip: str, vlan: int | None = None) -> Any:
        params: dict[str, Any] = {'ifid': self.ifid, 'host': host_ip, 'breed': True, 'ndpi_category': True}
        if vlan is not None:
            params['vlan'] = vlan
        return self.backend._request(self.backend.rest_v2_url + '/get/host/l7/stats.lua', params)

    def get_top_local_talkers(self) -> Any:
        return self.backend._request(self.backend.rest_pro_v2_url + '/get/interface/top/local/talkers.lua', {'ifid': self.ifid})

    def get_top_remote_talkers(self) -> Any:
        return self.backend._request(self.backend.rest_pro_v2_url + '/get/interface/top/remote/talkers.lua', {'ifid': self.ifid})

    def get_top_local_talkers_v1(self) -> Any:
        return self.backend._request('/lua/pro/rest/v1/get/interface/top/local/talkers.lua', {'ifid': self.ifid})

    def get_top_remote_talkers_v1(self) -> Any:
        return self.backend._request('/lua/pro/rest/v1/get/interface/top/remote/talkers.lua', {'ifid': self.ifid})


class PyApiHistorical:
    def __init__(self, backend: NtopngPyApiBackend, ifid: int):
        self.backend = backend
        self.ifid = ifid

    def get_alerts_stats(self, epoch_begin: int, epoch_end: int, host: str | None = None) -> Any:
        params = {'ifid': self.ifid, 'epoch_begin': epoch_begin, 'epoch_end': epoch_end}
        if host:
            params['ip'] = f'{host};eq'
        return self.backend._request(self.backend.rest_v2_url + '/get/alert/top.lua', params)

    def get_alert_type_counters(self, epoch_begin: int, epoch_end: int) -> Any:
        return self.backend._request(self.backend.rest_v2_url + '/get/alert/type/counters.lua', {'ifid': self.ifid, 'status': 'historical', 'epoch_begin': epoch_begin, 'epoch_end': epoch_end})

    def get_alert_severity_counters(self, epoch_begin: int, epoch_end: int) -> Any:
        return self.backend._request(self.backend.rest_v2_url + '/get/alert/severity/counters.lua', {'ifid': self.ifid, 'status': 'historical', 'epoch_begin': epoch_begin, 'epoch_end': epoch_end})

    def get_alert_list(self, alert_family: str, epoch_begin: int, epoch_end: int, maxhits: int = 20, where_clause: str | None = None, select_clause: str | None = None, order_by: str | None = None, group_by: str | None = None) -> Any:
        params: dict[str, Any] = {
            'ifid': self.ifid,
            'alert_family': alert_family,
            'epoch_begin': epoch_begin,
            'epoch_end': epoch_end,
            'maxhits_clause': maxhits,
        }
        if where_clause:
            params['where_clause'] = where_clause
        if select_clause:
            params['select_clause'] = select_clause
        if order_by:
            params['order_by'] = order_by
        if group_by:
            params['group_by'] = group_by
        return self.backend._request(self.backend.rest_v2_url + '/get/alert/list/alerts.lua', params)

    def get_flow_alert_list(self, epoch_begin: int, epoch_end: int, length: int = 20, host: str | None = None) -> Any:
        params: dict[str, Any] = {
            'ifid': self.ifid,
            'epoch_begin': epoch_begin,
            'epoch_end': epoch_end,
            'length': length,
            'start': 0,
            'alert_id': '0;gte',
        }
        if host:
            params['ip'] = f'{host};eq'
        return self.backend._request(self.backend.rest_v2_url + '/get/flow/alert/list.lua', params)

    def get_host_alert_list(self, epoch_begin: int, epoch_end: int, length: int = 20, host: str | None = None) -> Any:
        params: dict[str, Any] = {
            'ifid': self.ifid,
            'epoch_begin': epoch_begin,
            'epoch_end': epoch_end,
            'length': length,
            'start': 0,
            'alert_id': '0;gte',
        }
        if host:
            params['ip'] = f'{host};eq'
        return self.backend._request(self.backend.rest_v2_url + '/get/host/alert/list.lua', params)
