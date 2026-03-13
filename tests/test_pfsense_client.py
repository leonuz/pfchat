#!/usr/bin/env python3

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import sys

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / 'pfchat' / 'scripts'
sys.path.insert(0, str(SCRIPT_DIR))

from pfsense_client import PfSenseClient  # noqa: E402


class PfSenseClientTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = PfSenseClient(host='192.168.0.254', api_key='test-key', verify_ssl=False)
        self.tempdir = tempfile.TemporaryDirectory()
        self.client._cache_dir = Path(self.tempdir.name)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_schema_cache_roundtrip(self) -> None:
        schema = {'paths': {'/api/v2/firewall/states': {}}}
        self.client._write_cached_schema(schema)
        loaded = self.client._read_cached_schema()
        self.assertEqual(loaded, schema)

    def test_filter_candidates_by_schema_prefers_supported_paths(self) -> None:
        self.client._supported_paths = {'firewall/states', 'status/system'}
        result = self.client._filter_candidates_by_schema(['status/arp', 'firewall/states'])
        self.assertEqual(result, ['firewall/states'])

    def test_filter_candidates_by_schema_falls_back_when_no_match(self) -> None:
        self.client._supported_paths = {'status/system'}
        result = self.client._filter_candidates_by_schema(['status/arp', 'diag/arp'])
        self.assertEqual(result, ['status/arp', 'diag/arp'])

    def test_get_capabilities_includes_cache_metadata(self) -> None:
        self.client._supported_paths = {
            'diagnostics/arp_table',
            'status/dhcp_server/leases',
            'firewall/states',
            'status/logs/firewall',
            'firewall/rules',
            'status/interfaces',
            'status/system',
            'status/gateways',
        }
        caps = self.client.get_capabilities()
        self.assertTrue(caps['openapi_available'])
        self.assertIn('schema_cache', caps)
        self.assertTrue(caps['capabilities']['devices_arp'])
        self.assertTrue(caps['capabilities']['devices_dhcp'])

    @patch.object(PfSenseClient, 'get_firewall_states')
    def test_infer_connected_devices_from_states(self, mock_states: MagicMock) -> None:
        mock_states.return_value = [
            {'source': '192.168.0.95:443', 'destination': '34.1.2.3:443'},
            {'source': '10.0.0.8:5555', 'destination': '192.168.0.50:53'},
            {'source': '127.0.0.1:1234', 'destination': '8.8.8.8:53'},
            {'source': '192.168.0.255:9999', 'destination': '1.1.1.1:443'},
        ]
        result = self.client._infer_connected_devices_from_states(limit=10)
        ips = {entry['ip'] for entry in result['devices']}
        self.assertIn('192.168.0.95', ips)
        self.assertIn('10.0.0.8', ips)
        self.assertIn('192.168.0.50', ips)
        self.assertNotIn('127.0.0.1', ips)
        self.assertNotIn('192.168.0.255', ips)
        self.assertTrue(result['degraded'])


if __name__ == '__main__':
    unittest.main()
