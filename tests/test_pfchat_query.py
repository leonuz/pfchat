#!/usr/bin/env python3

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / 'pfchat' / 'scripts'
sys.path.insert(0, str(SCRIPT_DIR))

import pfchat_query  # noqa: E402


class PfChatQueryTests(unittest.TestCase):
    def test_parse_bool_env_accepts_common_values(self) -> None:
        import os
        os.environ['PFSENSE_VERIFY_SSL'] = 'yes'
        self.assertTrue(pfchat_query.parse_bool_env('PFSENSE_VERIFY_SSL'))
        os.environ['PFSENSE_VERIFY_SSL'] = 'off'
        self.assertFalse(pfchat_query.parse_bool_env('PFSENSE_VERIFY_SSL'))

    def test_parse_bool_env_rejects_invalid_values(self) -> None:
        import os
        os.environ['PFSENSE_VERIFY_SSL'] = 'maybe'
        with self.assertRaises(SystemExit):
            pfchat_query.parse_bool_env('PFSENSE_VERIFY_SSL')

    def test_validate_host_rejects_urls(self) -> None:
        with self.assertRaises(SystemExit):
            pfchat_query.validate_host('https://192.168.0.254')

    def test_validate_api_key_rejects_placeholder(self) -> None:
        with self.assertRaises(SystemExit):
            pfchat_query.validate_api_key('replace-me')

    def test_parse_filters_supports_scalar_and_array(self) -> None:
        parsed = pfchat_query.parse_filters([
            'descr__contains=OpenVPN',
            'tag[]=blue',
            'tag[]=green',
        ])
        self.assertEqual(parsed['descr__contains'], 'OpenVPN')
        self.assertEqual(parsed['tag'], ['blue', 'green'])

    def test_build_connection_filters_from_helper_args(self) -> None:
        class Args:
            host = '192.168.0.95'
            port = '443'
            interface = 'vtnet0'
            contains = 'apple'

        filters = pfchat_query.build_connection_filters(Args(), {})
        self.assertEqual(filters['source__contains'], '192.168.0.95')
        self.assertEqual(filters['destination__contains'], ':443')
        self.assertEqual(filters['interface__contains'], 'vtnet0')
        self.assertEqual(filters['search'], 'apple')

    def test_parse_filterlog_entry_extracts_core_fields(self) -> None:
        text = 'Mar 13 15:22:00 sniperfw filterlog[46930]: 4,,,1000000003,vtnet1,match,block,in,6,0xe0,0x00000,255,ICMPv6,58,32,80.94.95.226,142.197.33.220,44321,8443,32'
        parsed = pfchat_query.parse_filterlog_entry(text)
        self.assertEqual(parsed['interface'], 'vtnet1')
        self.assertEqual(parsed['action'], 'block')
        self.assertEqual(parsed['src'], '80.94.95.226')
        self.assertEqual(parsed['dst'], '142.197.33.220')
        self.assertEqual(parsed['dst_port'], '8443')

    def test_filter_logs_matches_host_and_action(self) -> None:
        logs = [
            {'id': 1, 'text': 'Mar 13 15:22:00 sniperfw filterlog[1]: 4,,,1000000003,vtnet1,match,block,in,6,0xe0,0x00000,255,TCP,6,60,80.94.95.226,142.197.33.220,44321,8443,60'},
            {'id': 2, 'text': 'Mar 13 15:22:01 sniperfw filterlog[1]: 4,,,1000000003,vtnet0,match,pass,in,6,0xe0,0x00000,255,TCP,6,60,192.168.0.95,17.253.13.141,62042,443,60'},
        ]
        filtered = pfchat_query.filter_logs(logs, host='80.94.95.226', action='block')
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0]['id'], 1)
        self.assertIn('parsed', filtered[0])

    def test_apply_once_preset_sets_expected_values(self) -> None:
        import argparse
        args = argparse.Namespace(command='snapshot', once='wan', view='full', limit=100, action=None)
        updated = pfchat_query.apply_once_preset(args)
        self.assertEqual(updated.command, 'health')
        self.assertEqual(updated.view, 'wan')

    def test_render_view_summary_extracts_summary_block(self) -> None:
        data = {'summary': {'highlights': ['ok']}, 'other': 1}
        rendered = pfchat_query.render_view(data, 'summary')
        self.assertEqual(rendered, {'highlights': ['ok']})


if __name__ == '__main__':
    unittest.main()
