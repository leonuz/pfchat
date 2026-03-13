#!/usr/bin/env python3

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import sys

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / 'pfchat' / 'scripts'
sys.path.insert(0, str(SCRIPT_DIR))

from pfsense_client import PfSenseClient  # noqa: E402


class PfSenseIntegrationMockTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = PfSenseClient(host='192.168.0.254', api_key='test-key', verify_ssl=False)
        self.tempdir = tempfile.TemporaryDirectory()
        self.client._cache_dir = Path(self.tempdir.name)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_devices_flow_uses_schema_confirmed_arp_and_dhcp_endpoints(self) -> None:
        responses = {
            'schema/openapi': {
                'paths': {
                    '/api/v2/diagnostics/arp_table': {},
                    '/api/v2/status/dhcp_server/leases': {},
                }
            },
            'diagnostics/arp_table': [
                {'ip_address': '192.168.0.95', 'mac_address': '80:96:98:58:4a:39', 'hostname': 'iphoneLeo'}
            ],
            'status/dhcp_server/leases': [
                {'mac_address': '80:96:98:58:4a:39', 'hostname': 'iphoneLeo', 'lease_end': 'never'}
            ],
        }

        def fake_get(path, params=None):
            return responses[path]

        with patch.object(self.client, '_get', side_effect=fake_get) as mock_get:
            devices = self.client.get_connected_devices()

        self.assertFalse(devices['degraded'])
        self.assertEqual(devices['total_devices'], 1)
        self.assertEqual(devices['devices'][0]['hostname'], 'iphoneLeo')
        requested_paths = [call.args[0] for call in mock_get.call_args_list]
        self.assertIn('schema/openapi', requested_paths)
        self.assertIn('diagnostics/arp_table', requested_paths)
        self.assertIn('status/dhcp_server/leases', requested_paths)

    def test_snapshot_flow_builds_summary_from_mocked_responses(self) -> None:
        responses = {
            'schema/openapi': {
                'paths': {
                    '/api/v2/diagnostics/arp_table': {},
                    '/api/v2/status/dhcp_server/leases': {},
                    '/api/v2/firewall/states': {},
                    '/api/v2/status/logs/firewall': {},
                    '/api/v2/status/interfaces': {},
                    '/api/v2/status/system': {},
                    '/api/v2/status/gateways': {},
                    '/api/v2/firewall/rules': {},
                }
            },
            'diagnostics/arp_table': [
                {'ip_address': '192.168.0.95', 'mac_address': '80:96:98:58:4a:39', 'hostname': 'iphoneLeo'}
            ],
            'status/dhcp_server/leases': [
                {'mac_address': '80:96:98:58:4a:39', 'hostname': 'iphoneLeo'}
            ],
            'firewall/states': [
                {'source': '192.168.0.95:62042', 'destination': '17.253.13.141:443', 'bytes_total': 120000, 'state': 'ESTABLISHED:ESTABLISHED'}
            ],
            'status/logs/firewall': [
                {'text': 'Mar 13 15:22:00 fw filterlog[1]: 4,,,1000000003,vtnet1,match,block,in,6,0xe0,0x00000,255,TCP,6,60,80.94.95.226,142.197.33.220,44321,8443,60'}
            ],
            'status/interfaces': [
                {'name': 'wan', 'ipaddr': '142.197.33.220', 'gateway': '142.197.33.1', 'status': 'up'}
            ],
            'status/system': {
                'uptime': '1 Day', 'cpu_usage': 10, 'mem_usage': 20, 'disk_usage': 5
            },
            'status/gateways': [
                {'name': 'WAN_DHCP', 'status': 'online'}
            ],
            'firewall/rules': [
                {'descr': 'Allow LAN to any'}
            ],
        }

        def fake_get(path, params=None):
            return responses[path]

        with patch.object(self.client, '_get', side_effect=fake_get):
            snapshot = self.client.get_snapshot(limit=10)

        self.assertIn('summary', snapshot)
        self.assertEqual(snapshot['summary']['wan']['ipaddr'], '142.197.33.220')
        self.assertEqual(snapshot['summary']['device_summary']['total_devices'], 1)
        self.assertEqual(snapshot['summary']['log_summary']['blocked_entries_in_sample'], 1)
        self.assertTrue(snapshot['summary']['highlights'])
        self.assertEqual(snapshot['rules']['total_rules'], 1)


if __name__ == '__main__':
    unittest.main()
