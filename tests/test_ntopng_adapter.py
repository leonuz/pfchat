#!/usr/bin/env python3

from __future__ import annotations

import tempfile
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
        self.assertEqual(data['hosts'][0]['hostname'], 'iphoneLeo.uzc')
        self.assertEqual(data['hosts'][0]['bytes']['received'], 40)

    def test_get_active_hosts_prefers_inventory_hostname(self) -> None:
        class Interface:
            def get_active_hosts_paginated(self, current_page, per_page):
                return {'data': [{'ip': '192.168.0.52', 'name': 'Samsung', 'vlan': 0, 'bytes': {'total': 100}, 'num_flows': {'total': 1}}]}
        class NtopClient:
            def get_interface(self, ifid=0):
                return Interface()

        with tempfile.NamedTemporaryFile('w+', delete=False) as tmp:
            tmp.write("- `192.168.0.52` — `tvsala.uzc` — `wifi` / `endpoint` — `TV 65 Samsung`\n")
            tmp.flush()
            original = NtopngAdapter.TOOLS_PATH
            NtopngAdapter.TOOLS_PATH = Path(tmp.name)
            try:
                adapter = NtopngAdapter(NtopClient())
                data = adapter.get_active_hosts(ifid=0, limit=10)
            finally:
                NtopngAdapter.TOOLS_PATH = original
        self.assertEqual(data['hosts'][0]['hostname'], 'tvsala.uzc')
        self.assertEqual(data['hosts'][0]['display_name'], 'tvsala.uzc')
        self.assertEqual(data['hosts'][0]['inventory']['description'], 'TV 65 Samsung')

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
        self.assertEqual(summary['host']['hostname'], 'iphoneLeo.uzc')
        self.assertEqual(summary['activity']['bytes_received'], 77778)
        self.assertTrue(summary['activity']['first_seen_et'].endswith('ET'))
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

    def test_get_top_talkers_normalizes_rows(self) -> None:
        class Interface:
            def get_top_local_talkers(self):
                return [
                    {'host': '192.168.0.95', 'bytes': 12345, 'flows': 4, 'country': 'US', 'vlan': 0}
                ]
        class NtopClient:
            def get_interface(self, ifid=0):
                return Interface()

        adapter = NtopngAdapter(NtopClient())
        data = adapter.get_top_talkers(ifid=0, direction='local')
        self.assertEqual(data['total_talkers'], 1)
        self.assertEqual(data['talkers'][0]['host'], '192.168.0.95')
        self.assertEqual(data['talkers'][0]['bytes'], 12345)
        self.assertEqual(data['source'], 'ntopng_top_talkers_endpoint')

    def test_get_top_talkers_falls_back_to_active_hosts(self) -> None:
        class Interface:
            def get_top_local_talkers(self):
                raise RuntimeError('403 pro_only')
            def get_top_local_talkers_v1(self):
                raise RuntimeError('403 pro_only')
            def get_active_hosts_paginated(self, current_page, per_page):
                return {
                    'data': [
                        {'ip': 'a', 'name': 'a', 'vlan': 0, 'bytes': {'total': 10}, 'num_flows': {'total': 1}},
                        {'ip': 'b', 'name': 'b', 'vlan': 0, 'bytes': {'total': 50}, 'num_flows': {'total': 2}},
                    ]
                }
        class NtopClient:
            def get_interface(self, ifid=0):
                return Interface()

        adapter = NtopngAdapter(NtopClient())
        data = adapter.get_top_talkers(ifid=0, direction='local')
        self.assertEqual(data['source'], 'active_hosts_fallback')
        self.assertEqual(data['talkers'][0]['host'], 'b')
        self.assertIn('fallback', data['note'].lower())

    def test_get_alerts_aggregates_historical_calls(self) -> None:
        class Historical:
            def get_alert_severity_counters(self, epoch_begin, epoch_end):
                return {'critical': 1}
            def get_alert_type_counters(self, epoch_begin, epoch_end):
                return {'dns': 2}
            def get_flow_alert_list(self, epoch_begin, epoch_end, length=20, host=None):
                return {'records': [{'host': host or 'all'}]}
            def get_host_alert_list(self, epoch_begin, epoch_end, length=20, host=None):
                return {'records': [{'host': host or 'all'}]}
            def get_alert_list(self, alert_family, epoch_begin, epoch_end, maxhits=20, where_clause=None, order_by=None, group_by=None, select_clause=None):
                return [{'family': alert_family, 'where': where_clause}]
        class NtopClient:
            def get_historical_interface(self, ifid=0):
                return Historical()

        adapter = NtopngAdapter(NtopClient())
        data = adapter.get_alerts(ifid=0, hours=24, host='192.168.0.95')
        self.assertEqual(data['severity_counters']['critical'], 1)
        self.assertEqual(data['type_counters']['dns'], 2)
        self.assertEqual(data['flow_alerts']['records'][0]['host'], '192.168.0.95')
        self.assertEqual(data['host_alerts']['records'][0]['host'], '192.168.0.95')
        self.assertEqual(data['generic_alerts'][0]['family'], 'flow')
        self.assertEqual(data['normalized_flow_alerts'][0]['client'], None)
        self.assertEqual(data['summary']['total_flow_records'], 1)

    def test_get_alerts_handles_list_errors_cleanly(self) -> None:
        class Historical:
            def get_alert_severity_counters(self, epoch_begin, epoch_end):
                return {'critical': 1}
            def get_alert_type_counters(self, epoch_begin, epoch_end):
                return {'dns': 2}
            def get_flow_alert_list(self, epoch_begin, epoch_end, length=20, host=None):
                raise RuntimeError('timeout')
            def get_host_alert_list(self, epoch_begin, epoch_end, length=20, host=None):
                raise RuntimeError('timeout')
            def get_alert_list(self, alert_family, epoch_begin, epoch_end, maxhits=20, where_clause=None, order_by=None, group_by=None, select_clause=None):
                raise RuntimeError('timeout')
        class NtopClient:
            def get_historical_interface(self, ifid=0):
                return Historical()

        adapter = NtopngAdapter(NtopClient())
        data = adapter.get_alerts(ifid=0, hours=24)
        self.assertIsNone(data['flow_alerts'])
        self.assertIsNone(data['host_alerts'])
        self.assertIsNone(data['generic_alerts'])
        self.assertIn('unavailable', data['note'])

    def test_get_host_apps_normalizes_l7_stats(self) -> None:
        class Interface:
            def get_active_hosts_paginated(self, current_page, per_page):
                return {'data': [{'ip': '192.168.0.95', 'name': 'iphoneLeo', 'vlan': 0, 'key': '192.168.0.95@0'}]}
            def get_host_l7_stats(self, host_ip, vlan=None):
                return [{'label': 'TLS', 'value': 90, 'url': '/lua/flows_stats.lua?application=TLS'}]
        class NtopClient:
            def get_interface(self, ifid=0):
                return Interface()

        adapter = NtopngAdapter(NtopClient())
        data = adapter.get_host_apps(target='192.168.0.95', ifid=0)
        self.assertEqual(data['total_applications'], 1)
        self.assertEqual(data['applications'][0]['label'], 'TLS')
        self.assertEqual(data['host']['resolved_ip'], '192.168.0.95')

    def test_get_network_stats_aggregates_existing_views(self) -> None:
        class Interface:
            def get_active_hosts_paginated(self, current_page, per_page):
                return {
                    'data': [
                        {'ip': '192.168.0.95', 'name': 'iphoneLeo', 'vlan': 0, 'bytes': {'total': 100}, 'num_flows': {'total': 1}},
                        {'ip': '8.8.8.8', 'name': '8.8.8.8', 'vlan': 0, 'bytes': {'total': 50}, 'num_flows': {'total': 1}, 'country': 'US'},
                    ]
                }
            def get_top_local_talkers(self):
                return [{'host': '192.168.0.95', 'bytes': 100, 'flows': 1}]
        class Historical:
            def get_alert_severity_counters(self, epoch_begin, epoch_end):
                return {'critical': 1}
            def get_alert_type_counters(self, epoch_begin, epoch_end):
                return {'dns': 2}
            def get_flow_alert_list(self, epoch_begin, epoch_end, length=20, host=None):
                return {'records': []}
            def get_host_alert_list(self, epoch_begin, epoch_end, length=20, host=None):
                return {'records': []}
            def get_alert_list(self, alert_family, epoch_begin, epoch_end, maxhits=20, where_clause=None, order_by=None, group_by=None, select_clause=None):
                return []
        class NtopClient:
            def get_interface(self, ifid=0):
                return Interface()
            def get_historical_interface(self, ifid=0):
                return Historical()

        adapter = NtopngAdapter(NtopClient())
        data = adapter.get_network_stats(ifid=0, hours=24, limit=5)
        self.assertEqual(data['summary']['most_active_host'], 'iphoneLeo.uzc')
        self.assertEqual(data['summary']['active_host_count'], 2)
        self.assertEqual(data['summary']['external_peer_count'], 1)


if __name__ == '__main__':
    unittest.main()
