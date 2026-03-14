#!/usr/bin/env python3

from __future__ import annotations

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
            'diagnostics/arp_table/entry',
            'services/dhcp_server/leases',
            'firewall/state',
            'status/logs/firewall',
            'firewall/rule',
            'interfaces',
            'system/status',
            'routing/gateway',
        }
        caps = self.client.get_capabilities()
        self.assertTrue(caps['openapi_available'])
        self.assertIn('schema_cache', caps)
        self.assertTrue(caps['capabilities']['devices_arp'])
        self.assertTrue(caps['capabilities']['devices_dhcp'])
        self.assertTrue(caps['capabilities']['connections'])
        self.assertTrue(caps['capabilities']['rules'])
        self.assertTrue(caps['capabilities']['interfaces'])
        self.assertTrue(caps['capabilities']['gateways'])
        self.assertFalse(caps['capabilities']['firewall_aliases_write'])
        self.assertFalse(caps['capabilities']['firewall_apply'])
        self.assertTrue(caps['capabilities']['firewall_rule_write'])

    def test_summarize_snapshot_builds_highlights(self) -> None:
        snapshot = {
            'errors': {},
            'devices': {
                'total_devices': 2,
                'degraded': False,
                'devices': [
                    {'hostname': 'iphoneLeo', 'seen_in_states': 8},
                    {'hostname': 'tvsala', 'seen_in_states': 5},
                ],
            },
            'connections': {
                'total_active_connections': 2,
                'connections': [
                    {'source': '192.168.0.95:1234', 'destination': '17.1.1.1:443', 'bytes_total': 5000},
                    {'source': '192.168.0.52:1234', 'destination': '3.3.3.3:443', 'bytes_total': 3000},
                ],
            },
            'logs': {
                'total_entries': 2,
                'logs': [
                    {'text': '... block ...'},
                    {'text': '... pass ...'},
                ],
            },
            'health': {
                'gateways': [{'name': 'WAN_DHCP', 'status': 'online'}],
                'interfaces': [{'name': 'wan', 'ipaddr': '142.197.33.220', 'gateway': '142.197.33.1', 'status': 'up'}],
            },
            'rules': {'total_rules': 10, 'rules': []},
        }
        summary = self.client.summarize_snapshot(snapshot)
        self.assertEqual(summary['wan']['ipaddr'], '142.197.33.220')
        self.assertEqual(summary['gateway_status']['online'], ['WAN_DHCP'])
        self.assertEqual(summary['log_summary']['blocked_entries_in_sample'], 1)
        self.assertTrue(summary['highlights'])

    def test_get_first_supported_uses_variant_confirmed_by_schema(self) -> None:
        self.client._supported_paths = {'routing/gateway'}
        with patch.object(self.client, '_get', return_value=[{'name': 'WAN_DHCP'}]) as mock_get:
            gateways = self.client.get_gateways()
        self.assertEqual(gateways, [{'name': 'WAN_DHCP'}])
        mock_get.assert_called_once_with('routing/gateway', None)

    def test_get_capabilities_detects_write_related_paths(self) -> None:
        self.client._supported_paths = {'firewall/aliases', 'firewall/apply', 'firewall/rule', 'firewall/alias/delete', 'firewall/rule/delete'}
        caps = self.client.get_capabilities()
        self.assertTrue(caps['capabilities']['firewall_aliases_write'])
        self.assertTrue(caps['capabilities']['firewall_aliases_delete'])
        self.assertTrue(caps['capabilities']['firewall_apply'])
        self.assertTrue(caps['capabilities']['firewall_rule_write'])
        self.assertTrue(caps['capabilities']['firewall_rule_delete'])

    def test_create_firewall_alias_uses_supported_write_path(self) -> None:
        self.client._supported_paths = {'firewall/alias'}
        with patch.object(self.client, '_post', return_value={'status': 'ok'}) as mock_post:
            result = self.client.create_firewall_alias({'name': 'test_alias'})
        self.assertEqual(result, {'status': 'ok'})
        mock_post.assert_called_once_with('firewall/alias', body={'name': 'test_alias'})

    def test_create_firewall_rule_uses_supported_write_path(self) -> None:
        self.client._supported_paths = {'firewall/rule'}
        with patch.object(self.client, '_post', return_value={'status': 'ok'}) as mock_post:
            result = self.client.create_firewall_rule({'descr': 'block thing'})
        self.assertEqual(result, {'status': 'ok'})
        mock_post.assert_called_once_with('firewall/rule', body={'descr': 'block thing'})

    def test_apply_firewall_changes_uses_apply_endpoint(self) -> None:
        self.client._supported_paths = {'firewall/apply'}
        with patch.object(self.client, '_post', return_value={'applied': True}) as mock_post:
            result = self.client.apply_firewall_changes({'async': False})
        self.assertEqual(result, {'applied': True})
        mock_post.assert_called_once_with('firewall/apply', body={'async': False})

    def test_delete_firewall_alias_uses_supported_delete_path(self) -> None:
        self.client._supported_paths = {'firewall/alias/delete'}
        with patch.object(self.client, '_post', return_value={'deleted': True}) as mock_post:
            result = self.client.delete_firewall_alias({'name': 'test_alias'})
        self.assertEqual(result, {'deleted': True})
        mock_post.assert_called_once_with('firewall/alias/delete', body={'name': 'test_alias'})

    def test_delete_firewall_rule_uses_supported_delete_path(self) -> None:
        self.client._supported_paths = {'firewall/rule/delete'}
        with patch.object(self.client, '_post', return_value={'deleted': True}) as mock_post:
            result = self.client.delete_firewall_rule({'descr': 'rule'})
        self.assertEqual(result, {'deleted': True})
        mock_post.assert_called_once_with('firewall/rule/delete', body={'descr': 'rule'})

    @patch.object(PfSenseClient, 'get_firewall_states')
    def test_infer_connected_devices_from_states(self, mock_states: MagicMock) -> None:
        mock_states.return_value = [
            {'source': '192.168.0.95:443', 'destination': '34.1.2.3:443', 'interface': 'vtnet0', 'source_host': 'iphoneLeo'},
            {'source': '10.0.0.8:5555', 'destination': '192.168.0.50:53', 'interface': 'vtnet2'},
            {'source': '127.0.0.1:1234', 'destination': '8.8.8.8:53', 'interface': 'lo0'},
            {'source': '192.168.0.255:9999', 'destination': '1.1.1.1:443', 'interface': 'vtnet0'},
            {'source': '17.1.1.1:443', 'destination': '192.168.0.95:53000', 'interface': 'vtnet0'},
        ]
        result = self.client._infer_connected_devices_from_states(limit=10)
        rows = {entry['ip']: entry for entry in result['devices']}
        self.assertIn('192.168.0.95', rows)
        self.assertIn('10.0.0.8', rows)
        self.assertIn('192.168.0.50', rows)
        self.assertNotIn('127.0.0.1', rows)
        self.assertNotIn('192.168.0.255', rows)
        self.assertEqual(rows['192.168.0.95']['hostname'], 'iphoneLeo')
        self.assertEqual(rows['192.168.0.95']['confidence'], 'medium')
        self.assertEqual(rows['192.168.0.95']['interfaces'], ['vtnet0'])
        self.assertTrue(result['degraded'])


if __name__ == '__main__':
    unittest.main()
