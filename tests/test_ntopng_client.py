#!/usr/bin/env python3

from __future__ import annotations

import unittest
from unittest.mock import patch

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / 'pfchat' / 'scripts'
sys.path.insert(0, str(SCRIPT_DIR))

from ntopng_client import NtopngClient  # noqa: E402


class NtopngClientTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = NtopngClient(base_url='https://ntop.local:3000', username='admin', password='secret', verify_ssl=False)

    def test_headers_use_token_when_configured(self) -> None:
        client = NtopngClient(base_url='https://ntop.local:3000', auth_token='abc123', verify_ssl=False)
        headers = client._headers()
        self.assertEqual(headers['Authorization'], 'Token abc123')

    def test_get_capabilities_reports_expected_flags(self) -> None:
        def fake_probe(method, path, params=None, body=None):
            mapping = {
                'lua/rest/v1/get/ntopng/interfaces.lua': {'ok': True, 'path': path, 'method': method, 'sample_type': 'list'},
                'lua/rest/v1/get/host/active.lua': {'ok': True, 'path': path, 'method': method, 'sample_type': 'dict'},
                'lua/rest/v1/get/host/data.lua': {'ok': True, 'path': path, 'method': method, 'sample_type': 'dict'},
                'lua/rest/v1/get/interface/data.lua': {'ok': True, 'path': path, 'method': method, 'sample_type': 'dict'},
                'lua/rest/v2/get/host/active': {'ok': False, 'path': path, 'method': method, 'error': '404'},
                'lua/rest/v2/get/alert/summary': {'ok': False, 'path': path, 'method': method, 'error': '404'},
                'lua/pro/rest/v2/get/flow/historical/top_talkers': {'ok': False, 'path': path, 'method': method, 'error': '404'},
            }
            return mapping[path]

        with patch.object(self.client, 'probe', side_effect=fake_probe), patch.object(self.client, 'get_interfaces', return_value=[{'ifid': 0}, {'ifid': 1}]):
            caps = self.client.get_capabilities()
        self.assertTrue(caps['ntopng_available'])
        self.assertEqual(caps['interface_count'], 2)
        self.assertTrue(caps['capabilities']['rest_v1'])
        self.assertFalse(caps['capabilities']['rest_v2'])
        self.assertTrue(caps['capabilities']['interfaces'])
        self.assertTrue(caps['capabilities']['active_hosts'])
        self.assertTrue(caps['capabilities']['host_data'])
        self.assertTrue(caps['capabilities']['timeseries'])
        self.assertFalse(caps['capabilities']['historical_flows'])


if __name__ == '__main__':
    unittest.main()
