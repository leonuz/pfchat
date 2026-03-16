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

    def test_get_capabilities_reports_expected_flags(self) -> None:
        with patch.object(self.client, 'get_interfaces', return_value=[{'ifid': 0}, {'ifid': 1}]):
            caps = self.client.get_capabilities()
        self.assertTrue(caps['ntopng_available'])
        self.assertEqual(caps['interface_count'], 2)
        self.assertTrue(caps['capabilities']['interfaces'])
        self.assertTrue(caps['capabilities']['active_hosts'])
        self.assertTrue(caps['capabilities']['host_data'])
        self.assertFalse(caps['capabilities']['historical_flows'])

    def test_summarize_host_extracts_core_fields(self) -> None:
        payload = {
            'ip': '192.168.0.95',
            'name': 'iphoneLeo',
            'seen': {'first': 1710600000, 'last': 1710600300},
            'bytes': {'total': 123456, 'sent': 45678, 'rcvd': 77778},
            'flows.as_client': 4,
            'flows.as_server': 1,
            'total_flows.as_server': 1,
            'asn': 714,
            'asname': 'APPLE',
            'country': 'US',
            'is_blacklisted': False,
        }
        with patch.object(self.client, 'get_host_data', return_value=payload):
            summary = self.client.summarize_host('192.168.0.95', ifid=0)
        self.assertEqual(summary['host'], '192.168.0.95')
        self.assertEqual(summary['name'], 'iphoneLeo')
        self.assertEqual(summary['seen_first_epoch'], 1710600000)
        self.assertEqual(summary['bytes']['received'], 77778)
        self.assertEqual(summary['flows']['as_client'], 4)
        self.assertEqual(summary['asname'], 'APPLE')


if __name__ == '__main__':
    unittest.main()
