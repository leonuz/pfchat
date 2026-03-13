# PfChat

[![Release](https://img.shields.io/github/v/release/leonuz/pfchat)](https://github.com/leonuz/pfchat/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![OpenClaw](https://img.shields.io/badge/OpenClaw-skill-blue)](https://docs.openclaw.ai)

PfChat is an OpenClaw skill for querying and analyzing a pfSense firewall in real time through the pfSense REST API.

It is model-agnostic: the skill fetches live data from pfSense and lets the current OpenClaw agent analyze it, instead of locking the workflow to a specific LLM provider.

## What it does

- Query connected devices using ARP/DHCP when the API exposes them
- Fall back to inferred active hosts from `firewall/states` when ARP/DHCP is unavailable
- Inspect active firewall states and live connections
- Review recent firewall activity
- Check interface, gateway, and system status
- Review firewall rules
- Build a live snapshot for security triage
- Discover supported capabilities from the live OpenAPI schema

## Quick start

### 1. Configure pfSense access

```bash
cp .env.example .env
```

Example:

```env
PFSENSE_HOST=192.168.0.254
PFSENSE_API_KEY=replace-me
PFSENSE_VERIFY_SSL=false
```

Notes:
- `PFSENSE_VERIFY_SSL=false` keeps HTTPS enabled; it only disables certificate trust validation.
- This is normal when pfSense uses a self-signed certificate or an internal CA that is not installed on the client host.
- The CLI falls back to the project-local `pfchat/.env` based on the script path, which helps when the skill is invoked from another channel or working directory.
- Do not commit real API keys.

### 2. Run direct queries

```bash
python3 pfchat/scripts/pfchat_query.py capabilities
python3 pfchat/scripts/pfchat_query.py devices
python3 pfchat/scripts/pfchat_query.py health
python3 pfchat/scripts/pfchat_query.py snapshot --limit 150
```

### 3. Use from OpenClaw

Typical prompts:

- "check what devices are connected to pfSense"
- "see if there is anything suspicious on my firewall"
- "what is iphoneLeo doing right now?"
- "what is my WAN address?"
- "show me firewall rules related to OpenVPN"

## Example output

### Capabilities

```json
{
  "openapi_available": true,
  "capabilities": {
    "devices_arp": true,
    "devices_dhcp": true,
    "connections": true,
    "logs_firewall": true,
    "rules": true,
    "interfaces": true,
    "system_status": true,
    "gateways": true
  }
}
```

### Health / WAN

```json
{
  "gateways": [
    {
      "name": "WAN_DHCP",
      "srcip": "142.197.33.220",
      "monitorip": "142.197.33.1",
      "status": "online"
    }
  ],
  "interfaces": [
    {
      "name": "wan",
      "descr": "WAN",
      "ipaddr": "142.197.33.220",
      "gateway": "142.197.33.1",
      "status": "up"
    }
  ]
}
```

## Repository layout

```text
pfchat/
├── README.md
├── README.en.md
├── TODO.md
├── TODO.en.md
├── CHANGELOG.md
├── CHANGELOG.en.md
├── LICENSE
├── .gitignore
├── .env.example
├── dist/
│   └── pfchat.skill
└── pfchat/
    ├── SKILL.md
    ├── scripts/
    │   ├── pfchat_query.py
    │   └── pfsense_client.py
    └── references/
        ├── endpoints.md
        ├── upstream-notes.md
        └── investigation-patterns.md
```

## Helper CLI

From the repository root:

```bash
python3 pfchat/scripts/pfchat_query.py capabilities
python3 pfchat/scripts/pfchat_query.py devices
python3 pfchat/scripts/pfchat_query.py connections --limit 200
python3 pfchat/scripts/pfchat_query.py connections --limit 100 --filter source__contains=192.168.0.95
python3 pfchat/scripts/pfchat_query.py logs --limit 200
python3 pfchat/scripts/pfchat_query.py interfaces
python3 pfchat/scripts/pfchat_query.py health
python3 pfchat/scripts/pfchat_query.py rules
python3 pfchat/scripts/pfchat_query.py rules --filter descr__contains=OpenVPN
python3 pfchat/scripts/pfchat_query.py snapshot --limit 150
```

## Telegram usage

If OpenClaw is already connected to Telegram, you do not need a separate bot inside PfChat. You can talk to OpenClaw from Telegram and let it use PfChat behind the scenes to query pfSense.

See `TELEGRAM.md` for suggested prompts, recommended workflow, and the alerting baseline.

## Daily email summary

PfChat can generate a daily firewall summary and deliver it by email when OpenClaw has Resend configured.

Included local script:
- `scripts/send_daily_summary.py`

On this host, the correct way for cron jobs and isolated sessions to inherit global variables is to load them from the `openclaw-gateway.service` unit through `EnvironmentFile`.

PfChat reports should prefer device names from the local inventory (`TOOLS.md`). If no local mapping exists, they may use reverse lookup and keep the IP only as fallback detail.

## Current status

PfChat already covers the live API workflow. The current focus is robustness, version compatibility, and operational polish.

See `TODO.en.md`, `CHANGELOG.en.md`, and `TELEGRAM.md` for pending work, recent changes, and channel usage.

## License

MIT
