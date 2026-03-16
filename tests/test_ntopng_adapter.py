#!/usr/bin/env python3

from __future__ import annotations

import unittest

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / 'pfchat' / 'scripts'
sys.path.insert(0, str(SCRIPT_DIR))

from ntopng_adapter import NtopngAdapter  # noqa: E402


class NtopngAdapterTests(unittest.TestCase):
    def test_get_active_hosts_normalizes_rows(self) -> None:
        class Interface:
            def get_active_hosts_paginated(self, current_page, per_page):
                return {
                    'data': [
                        {
                            'ip': '192.168.0.95',
                            'name': 'iphoneLeo',
                            'vlan': 0,
                            'key': '192.168.0.95@0',
                            'first_seen': 1710600000,
                            'last_seen': 1710600300,
                            'bytes': {'total': 100, 'sent': 60, 'rcvd': 40},
                            'num_flows': {'total': 3, 'as_client': 2, 'as_server': 1},
                        }
                    ]
                }
        class NtopClient:
            def get_interface(self, ifid=0):
                return Interface()
            def get_interfaces_list(self):
                return [{'ifid': 0}]
            def get_historical_interface(self, ifid=0):
                class H:
                    def get_alert_severity_counters(self, epoch_begin, epoch_end):
                        return {'ok': True}
                return H()

        adapter = NtopngAdapter(NtopClient())
        data = adapter.get_active_hosts(ifid=0, limit=10)
        self.assertEqual(data['total_active_hosts'], 1)
        self.assertEqual(data['hosts'][0]['ip'], '192.168.0.95')
        self.assertEqual(data['hosts'][0]['hostname'], 'iphoneLeo')
        self.assertEqual(data['hosts'][0]['bytes']['received'], 40)

    def test_resolve_host_identity_uses_pfsense_and_ntop(self) -> None:
        class Interface:
            def get_active_hosts_paginated(self, current_page, per_page):
                return {'data': [{'ip': '192.168.0.160', 'name': 'ferpad', 'vlan': 0, 'key': '192.168.0.160@0'}]}
        class NtopClient:
            def get_interface(self, ifid=0):
                return Interface()

        class PfSenseClient:
            def get_connected_devices(self):
                return {'devices': [{'hostname': 'ferpad', 'dnsresolve': 'ferpad.uzc', 'ip_address': '192.168.0.160'}]}

        adapter = NtopngAdapter(NtopClient(), PfSenseClient())
        resolved = adapter.resolve_host_identity('ferpad', ifid=0)
        self.assertEqual(resolved['resolved_ip'], '192.168.0.160')
        self.assertEqual(resolved['resolved_hostname'], 'ferpad')
        self.assertEqual(resolved['confidence'], 'high')
        self.assertIn('pfsense_devices', resolved['sources'])
        self.assertIn('ntopng_active_hosts', resolved['sources'])

    def test_get_host_summary_returns_pfchat_native_shape(self) -> None:
        class Interface:
            def get_active_hosts_paginated(self, current_page, per_page):
                return {'data': [{'ip': '192.168.0.95', 'name': 'iphoneLeo', 'vlan': 0, 'key': '192.168.0.95@0'}]}
            def get_host_data(self, host):
                return {
                    'ip': '192.168.0.95',
                    'name': 'iphoneLeo',
                    'seen': {'first': 1710600000, 'last': 1710600300},
                    'bytes': {'total': 123456, 'sent': 45678, 'rcvd': 77778},
                    'flows.as_client': 4,
                    'flows.as_server': 1,
                    'active_alerted_flows': 0,
                    'asn': 714,
                    'asname': 'APPLE',
                    'country': 'US',
                    'is_blacklisted': False,
                }
        class NtopClient:
            def get_interface(self, ifid=0):
                return Interface()

        adapter = NtopngAdapter(NtopClient())
        summary = adapter.get_host_summary('192.168.0.95', ifid=0)
        self.assertEqual(summary['host']['ip'], '192.168.0.95')
        self.assertEqual(summary['host']['hostname'], 'iphoneLeo')
        self.assertEqual(summary['activity']['bytes_received'], 77778)
        self.assertEqual(summary['network']['asname'], 'APPLE')

    def test_get_capabilities_with_pyapi_backend_shape(self) -> None:
        class Interface:
            def get_active_hosts_paginated(self, current_page, per_page):
                return {'data': []}
            def get_top_local_talkers(self):
                return [{'host': 'a'}]
        class Historical:
            def get_alert_severity_counters(self, epoch_begin, epoch_end):
                return {'critical': 1}
        class NtopClient:
            def get_interfaces_list(self):
                return [{'ifid': 0}]
            def get_interface(self, ifid=0):
                return Interface()
            def get_historical_interface(self, ifid=0):
                return Historical()

        adapter = NtopngAdapter(NtopClient())
        caps = adapter.get_capabilities()
        self.assertTrue(caps['capabilities']['rest_v2'])
        self.assertTrue(caps['capabilities']['interfaces'])
        self.assertTrue(caps['capabilities']['active_hosts'])
        self.assertTrue(caps['capabilities']['alerts'])
        self.assertTrue(caps['capabilities']['historical_flows'])


if __name__ == '__main__':
    unittest.main()
