import unittest

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / 'scripts'
sys.path.insert(0, str(SCRIPT_DIR))

import send_daily_summary


class SendDailySummaryTests(unittest.TestCase):
    def test_is_internal_ip_uses_real_private_ranges(self) -> None:
        self.assertTrue(send_daily_summary.is_internal_ip('10.1.2.3'))
        self.assertTrue(send_daily_summary.is_internal_ip('172.16.5.4'))
        self.assertTrue(send_daily_summary.is_internal_ip('172.31.255.254'))
        self.assertTrue(send_daily_summary.is_internal_ip('192.168.0.50'))
        self.assertFalse(send_daily_summary.is_internal_ip('172.1.2.3'))
        self.assertFalse(send_daily_summary.is_internal_ip('8.8.8.8'))

    def test_should_include_connection_not_tied_to_vtnet0(self) -> None:
        conn = {
            'interface': 'lan',
            'source': '192.168.0.81:51514',
            'destination': '1.1.1.1:443',
            'protocol': 'tcp',
            'bytes_total': 1000,
        }
        self.assertTrue(send_daily_summary.should_include_connection(conn))

    def test_should_exclude_noise_destinations(self) -> None:
        multicast = {
            'source': '192.168.0.81:5353',
            'destination': '224.0.0.251:5353',
        }
        broadcast = {
            'source': '192.168.0.80:53320',
            'destination': '192.168.0.255:10001',
        }
        firewall = {
            'source': '192.168.0.81:53000',
            'destination': '192.168.0.254:443',
        }
        self.assertFalse(send_daily_summary.should_include_connection(multicast))
        self.assertFalse(send_daily_summary.should_include_connection(broadcast))
        self.assertFalse(send_daily_summary.should_include_connection(firewall))

    def test_aggregate_client_usage_sums_matching_flows(self) -> None:
        snapshot = {
            'connections': {
                'connections': [
                    {'interface': 'lan', 'source': '192.168.0.81:50000', 'destination': '1.1.1.1:443', 'bytes_total': 100, 'bytes_in': 40, 'bytes_out': 60},
                    {'interface': 'em1', 'source': '192.168.0.81:50001', 'destination': '8.8.8.8:53', 'bytes_total': 50, 'bytes_in': 10, 'bytes_out': 40},
                    {'interface': 'wan', 'source': '8.8.8.8:443', 'destination': '192.168.0.81:50002', 'bytes_total': 999},
                ]
            }
        }
        rows = send_daily_summary.aggregate_client_usage(snapshot)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['ip'], '192.168.0.81')
        self.assertEqual(rows[0]['bytes_total'], 150)
        self.assertEqual(rows[0]['flows'], 2)


if __name__ == '__main__':
    unittest.main()
