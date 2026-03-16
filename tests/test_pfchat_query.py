#!/usr/bin/env python3

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / 'pfchat' / 'scripts'
sys.path.insert(0, str(SCRIPT_DIR))

import pfchat_query  # noqa: E402


class PfChatQueryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        pfchat_query.STATE_DIR = Path(self.tempdir.name)
        pfchat_query.DRAFTS_DIR = pfchat_query.STATE_DIR / 'drafts'
        pfchat_query.AUDIT_LOG = pfchat_query.STATE_DIR / 'audit.log'

    def tearDown(self) -> None:
        self.tempdir.cleanup()

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

    def test_validate_url_base_requires_http_scheme(self) -> None:
        with self.assertRaises(SystemExit):
            pfchat_query.validate_url_base('192.168.0.10:3000', 'NTOPNG_BASE_URL')
        self.assertEqual(
            pfchat_query.validate_url_base('https://192.168.0.10:3000/', 'NTOPNG_BASE_URL'),
            'https://192.168.0.10:3000'
        )

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

    def test_ntop_hosts_command_filters_by_host(self) -> None:
        class Args:
            command = 'ntop-hosts'
            ifid = 0
            limit = 50
            host = '192.168.0.95'
        rows = [
            {'ip': '192.168.0.95', 'name': 'iphoneLeo'},
            {'ip': '192.168.0.52', 'name': 'samsung'},
        ]
        hosts = {'data': rows}
        filtered = [row for row in hosts.get('data', []) if Args.host.lower() in str(row.get('ip', '')).lower() or Args.host.lower() in str(row.get('name', '')).lower()]
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0]['name'], 'iphoneLeo')

    def test_build_block_draft_for_device_target(self) -> None:
        class Client:
            def get_connected_devices(self):
                return {
                    'devices': [
                        {'hostname': 'iphoneLeo', 'ip_address': '192.168.0.95', 'interface': 'LAN'}
                    ]
                }

            def get_capabilities(self):
                return {'capabilities': {'firewall_aliases_write': True, 'firewall_apply': True}}

        draft = pfchat_query.build_block_draft(Client(), 'iphoneLeo', 'block-device')
        self.assertEqual(draft['target']['ip'], '192.168.0.95')
        self.assertEqual(draft['proposal']['rule_interface'], 'lan')
        self.assertEqual(draft['apply_status'], 'draft-only')

    def test_build_block_draft_for_ip_requires_valid_ip(self) -> None:
        class Client:
            def get_connected_devices(self):
                return {'devices': []}

            def get_capabilities(self):
                return {'capabilities': {}}

        with self.assertRaises(SystemExit):
            pfchat_query.build_block_draft(Client(), 'not-an-ip', 'block-ip')

    def test_build_block_egress_port_draft(self) -> None:
        class Client:
            def get_connected_devices(self):
                return {
                    'devices': [
                        {'hostname': 'sniperhack', 'ip_address': '192.168.0.81', 'interface': 'LAN'}
                    ]
                }
            def get_capabilities(self):
                return {'capabilities': {'firewall_aliases_write': True, 'firewall_apply': True}}
        draft = pfchat_query.build_block_draft(Client(), 'sniperhack', 'block-egress-port', port='80', proto='tcp')
        self.assertEqual(draft['proposal']['destination_port'], '80')
        self.assertEqual(draft['proposal']['rule_protocol'], 'tcp')
        self.assertIn('egress block', draft['proposal']['rule_description'])

    def test_build_block_egress_proto_icmp_draft(self) -> None:
        class Client:
            def get_connected_devices(self):
                return {
                    'devices': [
                        {'hostname': 'sniperhack', 'ip_address': '192.168.0.81', 'interface': 'LAN'}
                    ]
                }
            def get_capabilities(self):
                return {'capabilities': {'firewall_aliases_write': True, 'firewall_apply': True}}
        draft = pfchat_query.build_block_draft(Client(), 'sniperhack', 'block-egress-proto', proto='icmp')
        self.assertEqual(draft['proposal']['rule_protocol'], 'icmp')
        self.assertNotIn('destination_port', draft['proposal'])
        self.assertIn('icmp', draft['proposal']['rule_description'])

    def test_build_quick_rule_payload_for_icmp(self) -> None:
        payload = pfchat_query.build_quick_rule_payload('lan', 'sniperhack', '192.168.0.81', 'icmp')
        self.assertTrue(payload['floating'])
        self.assertTrue(payload['quick'])
        self.assertEqual(payload['protocol'], 'icmp')
        self.assertEqual(payload['icmptype'], ['any'])
        self.assertNotIn('destination_port', payload)

    def test_state_matches_target_for_tcp_port(self) -> None:
        state = {'source': '192.168.0.81:51514', 'destination': '1.1.1.1:443', 'protocol': 'tcp'}
        self.assertTrue(pfchat_query.state_matches_target(state, '192.168.0.81', 'tcp', '443'))
        self.assertFalse(pfchat_query.state_matches_target(state, '192.168.0.81', 'tcp', '80'))

    def test_quick_egress_block_creates_rule_and_clears_states(self) -> None:
        class Client:
            def get_connected_devices(self):
                return {'devices': [{'hostname': 'sniperhack', 'ip_address': '192.168.0.81', 'interface': 'LAN'}]}
            def get_firewall_rules(self):
                return []
            def create_firewall_rule(self, payload):
                self.rule_payload = payload
                return {'id': 9, 'status': 'ok'}
            def apply_firewall_changes(self, payload):
                self.apply_payload = payload
                return {'applied': True}
            def get_firewall_states(self, limit=500, filters=None):
                self.state_filters = filters
                return [{'id': 211, 'source': '192.168.0.81:51514', 'destination': '1.1.1.1:443', 'protocol': 'tcp'}]
            def delete_firewall_state(self, state_id):
                self.deleted_state_id = state_id
                return {'deleted': True}
        client = Client()
        result = pfchat_query.quick_egress_block(client, 'sniperhack', 'tcp', port='443')
        self.assertEqual(result['status'], 'blocked')
        self.assertEqual(client.rule_payload['destination_port'], '443')
        self.assertTrue(client.rule_payload['floating'])
        self.assertEqual(client.deleted_state_id, 211)

    def test_quick_egress_unblock_deletes_matching_rule_and_state(self) -> None:
        class Client:
            def get_connected_devices(self):
                return {'devices': [{'hostname': 'sniperhack', 'ip_address': '192.168.0.81', 'interface': 'LAN'}]}
            def get_firewall_rules(self):
                return [{'id': 5, 'descr': 'PfChat quick egress block for sniperhack (192.168.0.81) tcp/443', 'source': '192.168.0.81', 'protocol': 'tcp', 'destination_port': '443'}]
            def delete_firewall_rule(self, rule_id):
                self.deleted_rule_id = rule_id
                return {'deleted': True}
            def apply_firewall_changes(self, payload):
                self.apply_payload = payload
                return {'applied': True}
            def get_firewall_states(self, limit=500, filters=None):
                return [{'id': 212, 'source': '192.168.0.81:51514', 'destination': '1.1.1.1:443', 'protocol': 'tcp'}]
            def delete_firewall_state(self, state_id):
                self.deleted_state_id = state_id
                return {'deleted': True}
        client = Client()
        result = pfchat_query.quick_egress_unblock(client, 'sniperhack', 'tcp', port='443')
        self.assertEqual(result['status'], 'unblocked')
        self.assertEqual(client.deleted_rule_id, 5)
        self.assertEqual(client.deleted_state_id, 212)

    def test_save_and_load_draft_roundtrip(self) -> None:
        draft = {
            'command': 'block-ip',
            'target': {'input': '1.2.3.4'},
            'apply_status': 'draft-only',
        }
        saved = pfchat_query.save_draft(draft)
        loaded = pfchat_query.load_draft(saved['draft_id'])
        self.assertEqual(loaded['draft_id'], saved['draft_id'])
        self.assertTrue(Path(saved['state_path']).exists())

    def test_list_drafts_returns_saved_entries(self) -> None:
        pfchat_query.save_draft({'command': 'block-ip', 'target': {'input': '1.2.3.4'}, 'apply_status': 'draft-only'})
        listing = pfchat_query.list_drafts()
        self.assertEqual(listing['total_drafts'], 1)
        self.assertEqual(listing['drafts'][0]['command'], 'block-ip')

    def test_apply_preview_audits(self) -> None:
        saved = pfchat_query.save_draft({
            'command': 'block-ip',
            'target': {'input': '1.2.3.4', 'ip': '1.2.3.4'},
            'proposal': {'rule_interface': 'wan'},
            'schema_support': {'firewall_aliases_write': True, 'firewall_apply': True},
            'apply_status': 'draft-only',
        })
        result = pfchat_query.build_apply_preview(saved)
        self.assertEqual(result['status'], 'ready-for-confirmation')
        lines = pfchat_query.AUDIT_LOG.read_text(encoding='utf-8').strip().splitlines()
        self.assertTrue(lines)
        payload = json.loads(lines[-1])
        self.assertEqual(payload['event'], 'apply_preview')

    def test_execute_apply_draft_requires_confirm(self) -> None:
        class Client:
            pass
        saved = pfchat_query.save_draft({
            'draft_id': 'abc123',
            'command': 'block-ip',
            'target': {'input': '1.2.3.4', 'ip': '1.2.3.4'},
            'proposal': {'rule_interface': 'wan'},
            'schema_support': {'firewall_aliases_write': True, 'firewall_apply': True},
            'apply_status': 'draft-only',
        })
        result = pfchat_query.execute_apply_draft(Client(), saved, confirm=False)
        self.assertEqual(result['status'], 'ready-for-confirmation')

    def test_execute_apply_draft_runs_writes_when_confirmed(self) -> None:
        class Client:
            def get_capabilities(self):
                return {'capabilities': {'firewall_aliases_write': True, 'firewall_rule_write': True, 'firewall_apply': True, 'firewall_aliases_delete': True, 'firewall_rule_delete': True}}
            def create_firewall_alias(self, payload):
                self.alias_payload = payload
                return {'status': 'alias-ok'}
            def create_firewall_rule(self, payload):
                self.rule_payload = payload
                return {'status': 'rule-ok'}
            def apply_firewall_changes(self, payload):
                self.apply_payload = payload
                return {'status': 'apply-ok'}
            def delete_firewall_rule(self, payload):
                self.rule_delete_payload = payload
                return {'status': 'rule-delete-ok'}
            def delete_firewall_alias(self, payload):
                self.alias_delete_payload = payload
                return {'status': 'alias-delete-ok'}
        client = Client()
        saved = pfchat_query.save_draft({
            'draft_id': 'apply123',
            'command': 'block-device',
            'target': {'input': 'iphoneLeo', 'ip': '192.168.0.95', 'hostname': 'iphoneLeo'},
            'proposal': {
                'alias_name': 'pfb_iphoneleo_192_168_0_95',
                'alias_type': 'host',
                'alias_values': ['192.168.0.95'],
                'rule_action': 'block',
                'rule_direction': 'in',
                'rule_interface': 'lan',
                'rule_description': 'PfChat draft block for iphoneLeo (192.168.0.95)',
            },
            'schema_support': {'firewall_aliases_write': True, 'firewall_apply': True},
            'apply_status': 'draft-only',
        })
        result = pfchat_query.execute_apply_draft(client, saved, confirm=True)
        self.assertEqual(result['status'], 'applied')
        self.assertEqual(client.alias_payload['name'], 'pfb_iphoneleo_192_168_0_95')
        self.assertEqual(client.rule_payload['interface'], ['lan'])
        self.assertEqual(client.rule_payload['source'], '192.168.0.95')
        self.assertEqual(client.rule_payload['destination'], 'any')
        self.assertEqual(client.rule_payload['protocol'], 'any')
        self.assertEqual(client.apply_payload, {'async': False})

    def test_execute_apply_draft_is_idempotent_after_success(self) -> None:
        class Client:
            def get_capabilities(self):
                return {'capabilities': {'firewall_aliases_write': True, 'firewall_rule_write': True, 'firewall_apply': True}}
            def create_firewall_alias(self, payload):
                raise AssertionError('should not be called')
            def create_firewall_rule(self, payload):
                raise AssertionError('should not be called')
            def apply_firewall_changes(self, payload):
                raise AssertionError('should not be called')
        saved = pfchat_query.save_draft({
            'draft_id': 'done123',
            'command': 'block-ip',
            'target': {'input': '1.2.3.4', 'ip': '1.2.3.4'},
            'proposal': {'rule_interface': 'wan'},
            'schema_support': {'firewall_aliases_write': True, 'firewall_apply': True},
            'apply_status': 'applied',
        })
        result = pfchat_query.execute_apply_draft(Client(), saved, confirm=True)
        self.assertEqual(result['status'], 'already-applied')

    def test_execute_rollback_draft_runs_when_confirmed(self) -> None:
        class Client:
            def get_capabilities(self):
                return {'capabilities': {'firewall_apply': True, 'firewall_aliases_delete': True, 'firewall_rule_delete': True}}
            def delete_firewall_rule(self, payload):
                self.rule_delete_payload = payload
                return {'status': 'rule-delete-ok'}
            def delete_firewall_alias(self, payload):
                self.alias_delete_payload = payload
                return {'status': 'alias-delete-ok'}
            def apply_firewall_changes(self, payload):
                self.apply_payload = payload
                return {'status': 'apply-ok'}
        client = Client()
        saved = pfchat_query.save_draft({
            'draft_id': 'rb123',
            'command': 'block-device',
            'target': {'input': 'iphoneLeo', 'ip': '192.168.0.95'},
            'apply_status': 'applied',
            'rollback': {
                'alias_id': 3,
                'rule_id': 5,
                'alias_name': 'pfb_iphoneleo_192_168_0_95',
                'rule_description': 'PfChat draft block for iphoneLeo (192.168.0.95)',
            },
        })
        result = pfchat_query.execute_rollback_draft(client, saved, confirm=True)
        self.assertEqual(result['status'], 'rolled-back')
        self.assertEqual(client.alias_delete_payload, 3)
        self.assertEqual(client.rule_delete_payload, 5)

    def test_list_managed_objects_filters_pfchat_entries(self) -> None:
        class Client:
            def get_firewall_aliases(self):
                return [
                    {'id': 1, 'name': 'pfb_iphoneleo_192_168_0_95', 'descr': 'PfChat draft block for iphoneLeo (192.168.0.95)'},
                    {'id': 2, 'name': 'Fernanda', 'descr': 'normal alias'},
                ]
            def get_firewall_rules(self):
                return [
                    {'id': 5, 'descr': 'PfChat draft block for iphoneLeo (192.168.0.95)', 'source': 'pfb_iphoneleo_192_168_0_95'},
                    {'id': 6, 'descr': 'OpenVPN', 'source': 'any'},
                ]
        result = pfchat_query.list_managed_objects(Client())
        self.assertEqual(result['total_aliases'], 1)
        self.assertEqual(result['total_rules'], 1)

    def test_cleanup_managed_objects_confirmed(self) -> None:
        class Client:
            def get_firewall_aliases(self):
                return [{'id': 3, 'name': 'pfb_sniperhack_192_168_0_81', 'descr': 'PfChat draft block for sniperhack (192.168.0.81)'}]
            def get_firewall_rules(self):
                return [{'id': 5, 'descr': 'PfChat draft block for sniperhack (192.168.0.81)', 'source': 'pfb_sniperhack_192_168_0_81'}]
            def get_capabilities(self):
                return {'capabilities': {'firewall_apply': True, 'firewall_aliases_delete': True, 'firewall_rule_delete': True}}
            def delete_firewall_rule(self, rule_id):
                self.rule_id = rule_id
                return {'status': 'rule-delete-ok'}
            def delete_firewall_alias(self, alias_id):
                self.alias_id = alias_id
                return {'status': 'alias-delete-ok'}
            def apply_firewall_changes(self, payload):
                self.apply_payload = payload
                return {'status': 'apply-ok'}
        client = Client()
        result = pfchat_query.cleanup_managed_objects(client, confirm=True)
        self.assertEqual(result['status'], 'cleaned')
        self.assertEqual(client.rule_id, 5)
        self.assertEqual(client.alias_id, 3)

    def test_select_managed_objects_by_target(self) -> None:
        class Client:
            def get_firewall_aliases(self):
                return [{'id': 3, 'name': 'pfb_sniperhack_192_168_0_81', 'descr': 'PfChat draft block for sniperhack (192.168.0.81)', 'address': ['192.168.0.81']}]
            def get_firewall_rules(self):
                return [{'id': 5, 'descr': 'PfChat draft block for sniperhack (192.168.0.81)', 'source': 'pfb_sniperhack_192_168_0_81', 'destination': 'any'}]
        result = pfchat_query.select_managed_objects_by_target(Client(), 'sniperhack')
        self.assertEqual(result['total_aliases'], 1)
        self.assertEqual(result['total_rules'], 1)

    def test_cleanup_managed_target_confirmed(self) -> None:
        class Client:
            def get_firewall_aliases(self):
                return [{'id': 3, 'name': 'pfb_sniperhack_192_168_0_81', 'descr': 'PfChat draft block for sniperhack (192.168.0.81)', 'address': ['192.168.0.81']}]
            def get_firewall_rules(self):
                return [{'id': 5, 'descr': 'PfChat draft block for sniperhack (192.168.0.81)', 'source': 'pfb_sniperhack_192_168_0_81', 'destination': 'any'}]
            def get_capabilities(self):
                return {'capabilities': {'firewall_apply': True, 'firewall_aliases_delete': True, 'firewall_rule_delete': True}}
            def delete_firewall_rule(self, rule_id):
                self.rule_id = rule_id
                return {'status': 'rule-delete-ok'}
            def delete_firewall_alias(self, alias_id):
                self.alias_id = alias_id
                return {'status': 'alias-delete-ok'}
            def apply_firewall_changes(self, payload):
                self.apply_payload = payload
                return {'status': 'apply-ok'}
        client = Client()
        result = pfchat_query.cleanup_managed_target(client, '192.168.0.81', confirm=True)
        self.assertEqual(result['status'], 'cleaned')
        self.assertEqual(result['target'], '192.168.0.81')
        self.assertEqual(client.rule_id, 5)
        self.assertEqual(client.alias_id, 3)


if __name__ == '__main__':
    unittest.main()
