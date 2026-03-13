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
- Cache the OpenAPI schema locally to reduce repeated fetches

## Prerequisites on pfSense

Before PfChat can work, the pfSense REST API package must already be installed and accessible on the firewall.

### 1. Install the pfSense REST API package

PfChat depends on the upstream **pfSense-pkg-RESTAPI** package.

Reference hierarchy:
- official upstream project (canonical source): <https://github.com/pfrest/pfSense-pkg-RESTAPI>
- published installation guide: <https://pfrest.org/INSTALL_AND_CONFIG/>
- published authentication guide: <https://pfrest.org/AUTHENTICATION_AND_AUTHORIZATION/>
- published Swagger/OpenAPI guide: <https://pfrest.org/SWAGGER_AND_OPENAPI/>
- practical installation walkthrough used during this project: <https://www.youtube.com/watch?v=inqMEOEVtao>

Typical install commands from the upstream docs:

Install on pfSense CE:

```bash
pkg-static add https://github.com/pfrest/pfSense-pkg-RESTAPI/releases/latest/download/pfSense-2.8.1-pkg-RESTAPI.pkg
```

Install on pfSense Plus:

```bash
pkg-static -C /dev/null add https://github.com/pfrest/pfSense-pkg-RESTAPI/releases/latest/download/pfSense-25.11-pkg-RESTAPI.pkg
```

Important notes:
- Choose the package build that matches your pfSense version.
- After pfSense upgrades, unofficial packages may be removed, so the REST API package may need to be reinstalled.
- PfChat has been validated in this project against a real pfSense installation exposing `/api/v2/schema/openapi`.

### 2. Configure the REST API in pfSense

After installation, verify these items in pfSense:

- `System -> REST API` is present in the webConfigurator
- the REST API is enabled/configured as needed
- your chosen authentication method is allowed
- the account used for the API key has the privileges needed for the endpoints you want to query

### 3. Create an API key

PfChat uses **API key authentication** by default through the `X-API-Key` header.

According to upstream docs, API keys can be created from:
- `System -> REST API -> Keys`

Important notes:
- API keys inherit the privileges of the user that created them.
- Treat the API key like a secret.
- If the key is ever exposed, revoke it and create a new one.

### 4. Verify the API before using PfChat

Useful checks before blaming PfChat:

- confirm the API responds at `https://<pfsense>/api/v2/...`
- confirm your API key works
- confirm the live OpenAPI schema is reachable:
  - `/api/v2/schema/openapi`
- confirm the endpoints you care about exist in that schema

If `/api/v2/schema/openapi` works, PfChat can use schema-aware discovery and adapt better to that installation.

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
- `PFSENSE_HOST` must be only the hostname or IP. Do not include `https://` or URL paths.
- `PFSENSE_API_KEY` must be a real key, not the example placeholder.
- `PFSENSE_VERIFY_SSL` accepts `true/false`, `1/0`, `yes/no`, or `on/off`.
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
├── README.es.md
├── TODO.md
├── TODO.es.md
├── CHANGELOG.md
├── CHANGELOG.es.md
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
python3 pfchat/scripts/pfchat_query.py connections --limit 100 --host 192.168.0.95
python3 pfchat/scripts/pfchat_query.py connections --limit 100 --port 443
python3 pfchat/scripts/pfchat_query.py logs --limit 200 --action block --interface vtnet1
python3 pfchat/scripts/pfchat_query.py logs --limit 200 --host 80.94.95.226
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

## Tests

Run the current test suite with the Python standard library:

```bash
python3 -m unittest discover -s tests -v
```

## Reference docs

Additional reference material:
- `pfchat/references/output-shapes.md` — high-level JSON output shape per command
- `pfchat/references/investigation-examples.md` — practical investigation workflows and example commands
- `pfchat/references/endpoints.md` — endpoint and fallback notes
- `pfchat/references/upstream-notes.md` — upstream pfrest/OpenAPI notes

## Current status

PfChat already covers the live API workflow. The current focus is robustness, version compatibility, and operational polish.

See `TODO.md`, `TODO.es.md`, `CHANGELOG.md`, `CHANGELOG.es.md`, `TELEGRAM.md`, and the reference docs for pending work, recent changes, and usage patterns.

## License

MIT
