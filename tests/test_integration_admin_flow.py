#!/usr/bin/env python3

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import sys

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / 'pfchat' / 'scripts'
sys.path.insert(0, str(SCRIPT_DIR))

import pfchat_query  # noqa: E402
from pfsense_client import PfSenseClient  # noqa: E402


class PfChatAdminIntegrationMockTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        pfchat_query.STATE_DIR = Path(self.tempdir.name)
        pfchat_query.DRAFTS_DIR = pfchat_query.STATE_DIR / 'drafts'
        pfchat_query.AUDIT_LOG = pfchat_query.STATE_DIR / 'audit.log'

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_apply_and_rollback_cycle_uses_mocked_client(self) -> None:
        class Client:
            def __init__(self):
                self.calls = []

            def get_capabilities(self):
                return {
                    'capabilities': {
                        'firewall_aliases_write': True,
                        'firewall_rule_write': True,
                        'firewall_apply': True,
                        'firewall_aliases_delete': True,
                        'firewall_rule_delete': True,
                    }
                }

            def create_firewall_alias(self, payload):
                self.calls.append(('alias-create', payload))
                return {'status': 'ok', 'id': 3, 'name': payload['name']}

            def create_firewall_rule(self, payload):
                self.calls.append(('rule-create', payload))
                return {'status': 'ok', 'id': 5, 'descr': payload['descr']}

            def apply_firewall_changes(self, payload):
                self.calls.append(('apply', payload))
                return {'status': 'ok'}

            def delete_firewall_rule(self, payload):
                self.calls.append(('rule-delete', payload))
                return {'status': 'ok'}

            def delete_firewall_alias(self, payload):
                self.calls.append(('alias-delete', payload))
                return {'status': 'ok'}

        client = Client()
        draft = pfchat_query.save_draft({
            'draft_id': 'flow123',
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

        applied = pfchat_query.execute_apply_draft(client, draft, confirm=True)
        self.assertEqual(applied['status'], 'applied')
        self.assertEqual(client.calls[0][0], 'alias-create')
        self.assertEqual(client.calls[1][0], 'rule-create')
        self.assertEqual(client.calls[2][0], 'apply')

        reloaded = pfchat_query.load_draft('flow123')
        self.assertEqual(reloaded['apply_status'], 'applied')
        self.assertEqual(reloaded['rollback']['status'], 'available')

        rolled_back = pfchat_query.execute_rollback_draft(client, reloaded, confirm=True)
        self.assertEqual(rolled_back['status'], 'rolled-back')
        self.assertEqual(client.calls[3][0], 'rule-delete')
        self.assertEqual(client.calls[4][0], 'alias-delete')
        self.assertEqual(client.calls[5][0], 'apply')

    def test_apply_preview_then_confirm_flow_keeps_audit(self) -> None:
        class Client:
            def get_capabilities(self):
                return {
                    'capabilities': {
                        'firewall_aliases_write': True,
                        'firewall_rule_write': True,
                        'firewall_apply': True,
                        'firewall_aliases_delete': True,
                        'firewall_rule_delete': True,
                    }
                }

            def create_firewall_alias(self, payload):
                return {'status': 'ok'}

            def create_firewall_rule(self, payload):
                return {'status': 'ok'}

            def apply_firewall_changes(self, payload):
                return {'status': 'ok'}

            def delete_firewall_rule(self, payload):
                return {'status': 'ok'}

            def delete_firewall_alias(self, payload):
                return {'status': 'ok'}

        draft = pfchat_query.save_draft({
            'draft_id': 'audit123',
            'command': 'block-ip',
            'target': {'input': '1.2.3.4', 'ip': '1.2.3.4'},
            'proposal': {
                'alias_name': 'pfb_1_2_3_4',
                'alias_type': 'host',
                'alias_values': ['1.2.3.4'],
                'rule_action': 'block',
                'rule_direction': 'in',
                'rule_interface': 'wan',
                'rule_description': 'PfChat draft block for 1.2.3.4',
            },
            'schema_support': {'firewall_aliases_write': True, 'firewall_apply': True},
            'apply_status': 'draft-only',
        })

        preview = pfchat_query.execute_apply_draft(Client(), draft, confirm=False)
        self.assertEqual(preview['status'], 'ready-for-confirmation')
        lines = pfchat_query.AUDIT_LOG.read_text(encoding='utf-8').strip().splitlines()
        self.assertTrue(any('apply_preview' in line for line in lines))


if __name__ == '__main__':
    unittest.main()
