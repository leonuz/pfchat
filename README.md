# PfChat

[![Release](https://img.shields.io/github/v/release/leonuz/pfchat)](https://github.com/leonuz/pfchat/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![OpenClaw](https://img.shields.io/badge/OpenClaw-skill-blue)](https://docs.openclaw.ai)

PfChat is an OpenClaw skill for querying and analyzing a pfSense firewall in real time through the pfSense REST API.

It can also query ntopng over its REST API for host-level visibility that complements pfSense state/log data.

The ntopng integration is being built around a normalized adapter model so PfChat can return stable JSON even when ntopng uses mixed endpoint families or installation-specific capabilities.

It is model-agnostic: the skill fetches live data from pfSense and lets the current OpenClaw agent analyze it, instead of locking the workflow to a specific LLM provider.

## What it does

- Query connected devices using ARP/DHCP when the API exposes them
- Fall back to inferred active hosts from `firewall/states` when ARP/DHCP is unavailable
- Inspect active firewall states and live connections
- Review recent firewall activity
- Check interface, gateway, and system status
- Review firewall rules
- Build a live snapshot for security triage
- Add a compact `summary` layer inside snapshots for faster answers and reports
- Discover supported capabilities from the live OpenAPI schema
- Cache the OpenAPI schema locally to reduce repeated fetches
- Query ntopng active hosts and host details through its REST API
- Normalize ntopng host output into PfChat-native JSON with capability probing and host identity resolution
- Derive top talkers from ntopng Pro endpoints when available, with active-host byte-ranking fallback when those endpoints are unavailable

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
- `NTOPNG_BASE_URL` must be a full URL such as `https://192.168.0.254:3000`.
- `NTOPNG_USERNAME` / `NTOPNG_PASSWORD` are used for Basic Auth against ntopng REST endpoints when HTTP API auth is enabled in ntopng.
- `NTOPNG_AUTH_TOKEN` is an optional alternative that takes precedence over username/password when present.
- `NTOPNG_VERIFY_SSL` accepts the same boolean forms as pfSense SSL verification.
- When `NTOPNG_VERIFY_SSL=false`, PfChat suppresses noisy urllib3 TLS warnings so normal command output stays readable.
- If ntopng returns the HTML login page instead of JSON, enable HTTP API auth in ntopng or generate a user authentication token and set `NTOPNG_AUTH_TOKEN`.
- Do not commit real API keys, ntopng credentials, or ntopng tokens.

### 2. Run direct queries

```bash
python3 pfchat/scripts/pfchat_query.py capabilities
python3 pfchat/scripts/pfchat_query.py devices
python3 pfchat/scripts/pfchat_query.py health
python3 pfchat/scripts/pfchat_query.py snapshot --limit 150
python3 pfchat/scripts/pfchat_query.py --once compact
python3 pfchat/scripts/pfchat_query.py --once wan
python3 pfchat/scripts/pfchat_query.py --once blocked
python3 pfchat/scripts/pfchat_query.py ntop-capabilities
python3 pfchat/scripts/pfchat_query.py ntop-hosts --ifid 0 --limit 50
python3 pfchat/scripts/pfchat_query.py ntop-host --host 192.168.0.95 --ifid 0
python3 pfchat/scripts/pfchat_query.py ntop-top-talkers --ifid 0 --direction local
python3 pfchat/scripts/pfchat_query.py ntop-alerts --ifid 0 --hours 24
python3 pfchat/scripts/pfchat_query.py ntop-host-apps --host 192.168.0.95 --ifid 0
python3 pfchat/scripts/pfchat_query.py ntop-network-stats --ifid 0 --hours 24 --limit 10
```

### 3. Use from OpenClaw

Typical prompts:

- "check what devices are connected to pfSense"
- "see if there is anything suspicious on my firewall"
- "what is iphoneLeo doing right now?"
- "what is my WAN address?"
- "show me firewall rules related to OpenVPN"
- "show ntopng active hosts"
- "what does ntopng know about 192.168.0.160?"
- "show ntopng top talkers"

### Recommended natural-language prompts for ntopng

Use phrasings like these when you want PfChat to pivot into ntopng-backed queries:

- "show ntopng capabilities"
- "is ntopng working?"
- "show ntopng active hosts"
- "show ntopng active hosts on interface 0"
- "what does ntopng know about ferpad.uzc?"
- "check ntopng host 192.168.0.160"
- "show ntopng top talkers"
- "show ntopng top local talkers on interface 0"
- "show ntopng top remote talkers"
- "show ntopng alerts from the last 24 hours"
- "show ntopng alerts for 192.168.0.95"
- "show me suspicious ntop alerts"
- "what host is generating the most alerts?"
- "what applications is 192.168.0.95 using in ntopng?"
- "show ntopng apps for ferpad.uzc"
- "show me a network intelligence summary"
- "show ntopng network stats for the last 24 hours"

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

## Safe firewall actions

PfChat now includes real administrative firewall actions for block workflows, with draft/preview/apply/rollback guardrails.

Examples:

```bash
python3 pfchat/scripts/pfchat_query.py block-ip --target 1.2.3.4
python3 pfchat/scripts/pfchat_query.py block-device --target iphoneLeo
python3 pfchat/scripts/pfchat_query.py block-device --target 192.168.0.95
python3 pfchat/scripts/pfchat_query.py block-egress-port --target sniperhack --port 80 --proto tcp
python3 pfchat/scripts/pfchat_query.py block-egress-proto --target sniperhack --proto icmp
python3 pfchat/scripts/pfchat_query.py quick-egress-block --target sniperhack --proto tcp --port 443
python3 pfchat/scripts/pfchat_query.py quick-egress-block --target sniperhack --proto icmp
python3 pfchat/scripts/pfchat_query.py quick-egress-unblock --target sniperhack --proto tcp --port 443
python3 pfchat/scripts/pfchat_query.py quick-egress-unblock --target sniperhack --proto icmp
python3 pfchat/scripts/pfchat_query.py unblock-ip --target 1.2.3.4
python3 pfchat/scripts/pfchat_query.py unblock-device --target sniperhack
python3 pfchat/scripts/pfchat_query.py draft-list
python3 pfchat/scripts/pfchat_query.py draft-show --draft-id <id>
python3 pfchat/scripts/pfchat_query.py apply-draft --draft-id <id>
python3 pfchat/scripts/pfchat_query.py apply-draft --draft-id <id> --confirm
python3 pfchat/scripts/pfchat_query.py rollback-draft --draft-id <id>
python3 pfchat/scripts/pfchat_query.py rollback-draft --draft-id <id> --confirm
python3 pfchat/scripts/pfchat_query.py pfchat-managed-list
python3 pfchat/scripts/pfchat_query.py pfchat-managed-cleanup
python3 pfchat/scripts/pfchat_query.py pfchat-managed-cleanup --confirm
```

Current behavior:
- resolves the target
- proposes alias/rule metadata
- saves the proposal locally with a `draft_id`
- supports `draft-show`, `draft-list`, `apply-draft`, `rollback-draft`, `pfchat-managed-list`, `pfchat-managed-cleanup`, `unblock-ip`, `unblock-device`, `block-egress-port`, `block-egress-proto`, `quick-egress-block`, and `quick-egress-unblock`
- quick egress operations use temporary `floating + quick` rules and clear matching states for immediate effect
- `apply-draft` without `--confirm` only previews and audits intent
- `apply-draft --confirm` executes alias + rule + firewall apply only when schema support is confirmed
- repeated apply attempts on an already applied draft are treated as idempotent and do not re-run writes
- `rollback-draft` provides preview/confirm rollback using pfSense object IDs captured during apply
- reports schema support for write/apply steps

Live-fire validation completed in this project:
- target used: `sniperhack.uzc` / `192.168.0.81`
- full-device block/apply/rollback was validated on real pfSense
- host-specific egress block `tcp/80` for `sniperhack` was also validated on real pfSense
- host-specific ICMP egress block for `sniperhack` was also validated on real pfSense
- apply created real aliases and firewall rules on pfSense
- rollback removed the objects cleanly
- final verification confirmed no residual alias or rule remained

Practical caveats from the real pfSense schema:
- create alias via `POST /firewall/alias`
- create rule via `POST /firewall/rule`
- alias names must stay within the pfSense limit (31 chars)
- interface values must use schema-valid lowercase choices such as `lan` and `wan`
- rollback is safest when using pfSense object IDs returned by the create calls
- current single-host block rules use the literal source IP in the rule, while aliases are still created for PfChat-managed tracking and cleanup

## Automation presets

PfChat now includes one-shot presets for scripting and automation:

- `--once compact` → compact snapshot summary
- `--once triage` → broader snapshot summary
- `--once wan` → WAN-focused health output
- `--once blocked` → recent blocked log view

Useful reduced views:
- `--view summary`
- `--view wan`
- `--view highlights`

Examples:

```bash
python3 pfchat/scripts/pfchat_query.py --once compact
python3 pfchat/scripts/pfchat_query.py --once triage
python3 pfchat/scripts/pfchat_query.py --once wan
python3 pfchat/scripts/pfchat_query.py snapshot --limit 150 --view highlights
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

The daily summary script now ranks clients by aggregated private-source traffic from the sampled state table, filters multicast/broadcast/firewall-noise destinations, and does not depend on a hard-coded pfSense interface name like `vtnet0`.

## Tests

Run the current test suite with the Python standard library:

```bash
python3 -m unittest discover -s tests -v
```

The suite includes:
- unit tests for parsing, config validation, schema caching, and summary logic
- mocked integration tests for device inventory and snapshot flows without requiring a live pfSense instance

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
