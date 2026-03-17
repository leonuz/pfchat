#!/usr/bin/env python3

from __future__ import annotations

import unittest

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / 'pfchat' / 'scripts'
sys.path.insert(0, str(SCRIPT_DIR))

from ntopng_pyapi_backend import NtopngPyApiBackend  # noqa: E402


class NtopngPyApiBackendTests(unittest.TestCase):
    def test_extract_json_payload_handles_embedded_http_response(self) -> None:
        raw = (
            'HTTP/1.1 200 OK\r\n'
            'Content-Type: application/json\r\n\r\n'
            '{"rc":0,"rsp":[1,2],"rc_str":"OK"}'
        )
        payload = NtopngPyApiBackend._extract_json_payload(raw)
        self.assertEqual(payload['rc'], 0)
        self.assertEqual(payload['rsp'], [1, 2])

    def test_init_keeps_verify_ssl_flag(self) -> None:
        client = NtopngPyApiBackend(url='https://ntop.local:3000', verify_ssl=False)
        self.assertFalse(client.verify_ssl)


if __name__ == '__main__':
    unittest.main()
