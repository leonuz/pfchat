# PfChat

[![Release](https://img.shields.io/github/v/release/leonuz/pfchat)](https://github.com/leonuz/pfchat/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![OpenClaw](https://img.shields.io/badge/OpenClaw-skill-blue)](https://docs.openclaw.ai)

PfChat is an API-driven operational and security workflow for **pfSense** plus **ntopng**.

It talks directly to:

- the **pfSense REST API** for authoritative firewall state, rules, interfaces, gateways, logs, device inventory, and controlled administrative changes
- the **ntopng API** for host-level traffic visibility, top talkers, alerts, applications, and network-activity context

In practice, PfChat is meant to answer questions like:

- what is this client doing right now?
- what traffic is a host generating?
- what was blocked recently?
- what are the top talkers?
- what applications is this device using?
- is anything suspicious happening on the firewall?
- can I block this host or restrict its outbound traffic safely?

PfChat is model-agnostic: it fetches live data from pfSense and ntopng, then lets the current OpenClaw agent analyze it conversationally.

## What PfChat really is

PfChat is not just a pfSense reader and not just an ntopng wrapper.

It combines:

- **pfSense** for firewall truth and administration
- **ntopng** for network intelligence and host behavior
- **OpenClaw** for investigation workflows, summaries, and operator-friendly interactions

Think of it like this:

- **pfSense** tells you what the firewall knows and enforces
- **ntopng** tells you what hosts are doing on the network
- **PfChat** brings both together into one operational interface

## Architecture

```text
+---------------------------+
| OpenClaw / CLI / Operator |
+-------------+-------------+
              |
              v
+---------------------------+
|          PfChat           |
|  query / correlate / act  |
+-------------+-------------+
              |                          
      +-------+-------+         +--------+--------+
      | pfSense REST  |         |   ntopng API    |
      | API           |         |  (host traffic, |
      |               |         |   alerts, apps) |
      +-------+-------+         +--------+--------+
              |                          |
              v                          v
   firewall state / rules /      host activity / top talkers /
   logs / interfaces / apply     apps / alerts / traffic context
```

## Core capabilities

### 1. Visibility

Use PfChat to inspect live network and firewall state:

- connected devices
- active firewall states
- recent blocked or passed events
- interface and gateway health
- WAN/public IP visibility
- firewall rules
- top talkers
- active ntopng hosts
- per-host application/protocol summaries
- recent alerts and traffic summaries

### 2. Investigation

Use PfChat for security-focused questions such as:

- what is `iphoneLeo` doing right now?
- which client is generating the most traffic?
- what did the firewall block in the last hour?
- does ntopng show anything suspicious for this host?
- what apps is this client using?
- is this host talking to unusual destinations or ports?
- is the firewall healthy, overloaded, or dropping something important?

### 3. Administration

PfChat is also an operational control surface for pfSense.

It can perform controlled administrative actions such as:

- build block drafts for IPs or devices
- apply block drafts with confirmation
- roll back managed changes
- list and clean up PfChat-managed objects
- perform quick host-specific egress blocks/unblocks

Administrative actions are intentionally guarded through preview / confirm / rollback workflows instead of blind mutation.

## Why pfSense + ntopng together matters

pfSense and ntopng solve different parts of the problem.

### pfSense is best for

- rules
- enforcement
- interfaces and gateways
- firewall logs
- device discovery through ARP/DHCP when exposed
- controlled writes such as rule or alias changes

### ntopng is best for

- top talkers
- host traffic behavior
- host application/protocol summaries
- recent alerts and network-activity context
- answering “what is this client actually doing?”

### PfChat uses both

Typical workflow:

1. use **pfSense** to confirm the host, interface, rules, states, and blocked activity
2. use **ntopng** to understand traffic volume, applications, peer behavior, and alerts
3. use **PfChat** to summarize findings or perform a safe administrative action

## Security-focused workflows

### Investigate a client

Examples:

- identify the host in pfSense inventory
- inspect current firewall states for that host
- inspect recent firewall log entries
- pivot into ntopng host details
- review top applications and alerts
- decide whether to monitor, block, or constrain egress

### Find top talkers

Examples:

- use ntopng top-talker views when supported
- fall back cleanly when some ntopng endpoints are unavailable
- correlate top talkers with pfSense device identity and interface context

### Review blocked traffic

Examples:

- inspect recent filterlog activity from pfSense
- isolate repeated blocks from one source
- compare with ntopng alerts or host behavior
- determine whether it is noise, misconfiguration, or suspicious activity

### Apply a safe firewall action

Examples:

- draft a host block
- preview the rule/alias plan
- confirm the change
- verify impact
- roll back if needed

## Installing the pfSense REST API

This section matters because **the pfSense API is not native by default**.
PfChat depends on the upstream **pfSense-pkg-RESTAPI** package being installed on the firewall.

### 1. Install the package

Canonical upstream project:
- <https://github.com/pfrest/pfSense-pkg-RESTAPI>

Useful upstream docs:
- installation: <https://pfrest.org/INSTALL_AND_CONFIG/>
- authentication: <https://pfrest.org/AUTHENTICATION_AND_AUTHORIZATION/>
- Swagger/OpenAPI: <https://pfrest.org/SWAGGER_AND_OPENAPI/>

Practical walkthrough used during this project:
- <https://www.youtube.com/watch?v=inqMEOEVtao>

Typical install command for pfSense CE:

```bash
pkg-static add https://github.com/pfrest/pfSense-pkg-RESTAPI/releases/latest/download/pfSense-2.8.1-pkg-RESTAPI.pkg
```

Typical install command for pfSense Plus:

```bash
pkg-static -C /dev/null add https://github.com/pfrest/pfSense-pkg-RESTAPI/releases/latest/download/pfSense-25.11-pkg-RESTAPI.pkg
```

Important notes:

- use the package build that matches your pfSense version
- unofficial packages may disappear after pfSense upgrades, so you may need to reinstall it
- PfChat has been validated against a real pfSense instance exposing `/api/v2/schema/openapi`

### 2. Configure the API in pfSense

After installation, verify:

- `System -> REST API` exists in the webConfigurator
- the REST API is enabled/configured correctly
- the authentication method you plan to use is allowed
- the account behind the API key has the permissions you need

### 3. Create an API key

PfChat uses **API key authentication** for pfSense by default via the `X-API-Key` header.

According to upstream docs, keys are managed from:

- `System -> REST API -> Keys`

Important notes:

- the key inherits the privileges of the user that created it
- treat it as a secret
- if exposed, revoke it and create a new one

### 4. Validate the API before blaming PfChat

Useful checks:

- confirm the API responds at `https://<pfsense>/api/v2/...`
- confirm your API key works
- confirm the live OpenAPI schema responds at `/api/v2/schema/openapi`
- confirm the endpoints you care about exist in that schema

If `/api/v2/schema/openapi` works, PfChat can use schema-aware discovery and adapt to that installation much more reliably.

## ntopng expectations

PfChat expects a reachable ntopng instance that can be queried over HTTP(S).
In many environments this is the ntopng deployment integrated with or adjacent to pfSense.

PfChat uses ntopng for:

- active hosts
- top talkers
- host profiles
- host applications/protocols
- alerts
- network-activity summaries

Important notes:

- some ntopng endpoints vary by version, edition, or local install behavior
- some top-talker endpoints may be Pro-only
- PfChat includes fallbacks and normalization so operator output stays stable even when ntopng behavior varies
- if ntopng returns an HTML login page instead of JSON, enable API auth or use an auth token

## Configuration

PfChat uses this as the single project-local setup file:

- `/home/openclaw/.openclaw/workspace/pfchat/.env`

Create it from the example:

```bash
cp .env.example .env
```

Example:

```env
PFSENSE_HOST=192.168.0.254
PFSENSE_API_KEY=replace-me
PFSENSE_VERIFY_SSL=false

NTOPNG_BASE_URL=https://192.168.0.254:3000
NTOPNG_USERNAME=admin
NTOPNG_PASSWORD=replace-me
NTOPNG_AUTH_TOKEN=
NTOPNG_VERIFY_SSL=false
```

### pfSense variables

- `PFSENSE_HOST` — host or IP only, without `https://` or URL paths
- `PFSENSE_API_KEY` — real API key, not the placeholder
- `PFSENSE_VERIFY_SSL` — accepts `true/false`, `1/0`, `yes/no`, `on/off`

### ntopng variables

- `NTOPNG_BASE_URL` — full URL such as `https://192.168.0.254:3000`
- `NTOPNG_USERNAME` / `NTOPNG_PASSWORD` — used for Basic Auth when HTTP API auth is enabled
- `NTOPNG_AUTH_TOKEN` — optional alternative that takes precedence over username/password when present
- `NTOPNG_VERIFY_SSL` — accepts the same boolean forms as pfSense SSL verification

### TLS note

`PFSENSE_VERIFY_SSL=false` and `NTOPNG_VERIFY_SSL=false` still use HTTPS.
They only disable certificate trust validation, which is common with self-signed certs or internal CAs not installed on the client host.

### Important config note

PfChat now uses the same local setup for both surfaces:

- the repo CLI
- the active OpenClaw skill

There is no longer a split where ntopng support exists in one surface but not the other.

Do not commit real API keys, passwords, or tokens.

## Quick start

### Run direct CLI queries

```bash
python3 pfchat/scripts/pfchat_query.py capabilities
python3 pfchat/scripts/pfchat_query.py devices
python3 pfchat/scripts/pfchat_query.py health
python3 pfchat/scripts/pfchat_query.py snapshot --limit 150
python3 pfchat/scripts/pfchat_query.py ntop-capabilities
python3 pfchat/scripts/pfchat_query.py ntop-hosts --ifid 0 --limit 50
python3 pfchat/scripts/pfchat_query.py ntop-host --host 192.168.0.95 --ifid 0
python3 pfchat/scripts/pfchat_query.py ntop-top-talkers --ifid 0 --direction local
python3 pfchat/scripts/pfchat_query.py ntop-alerts --ifid 0 --hours 24
python3 pfchat/scripts/pfchat_query.py ntop-host-apps --host 192.168.0.95 --ifid 0
python3 pfchat/scripts/pfchat_query.py ntop-network-stats --ifid 0 --hours 24 --limit 10
```

### Use from OpenClaw

Examples:

- `check what devices are connected to pfSense`
- `see if there is anything suspicious on my firewall`
- `what is iphoneLeo doing right now?`
- `what is my WAN address?`
- `show me firewall rules related to OpenVPN`
- `show ntopng active hosts`
- `what does ntopng know about 192.168.0.160?`
- `show ntopng top talkers`
- `show ntopng alerts from the last 24 hours`
- `what applications is 192.168.0.95 using in ntopng?`

## Commands by category

### pfSense state and visibility

- `capabilities`
- `devices`
- `connections`
- `logs`
- `interfaces`
- `health`
- `rules`
- `snapshot`

### ntopng intelligence

- `ntop-capabilities`
- `ntop-hosts`
- `ntop-host`
- `ntop-top-talkers`
- `ntop-alerts`
- `ntop-host-apps`
- `ntop-network-stats`

### Safe administrative actions

- `block-ip`
- `block-device`
- `block-egress-port`
- `block-egress-proto`
- `apply-draft`
- `rollback-draft`
- `quick-egress-block`
- `quick-egress-unblock`
- `unblock-ip`
- `unblock-device`
- `pfchat-managed-list`
- `pfchat-managed-cleanup`

## Safe administration model

PfChat supports real administrative changes on pfSense, but it is designed around guardrails:

- draft first
- preview before apply
- explicit confirm for live changes
- rollback support where possible
- managed-object cleanup support
- schema-aware checks before write paths

This matters because PfChat is not just for observation. It is also meant to be useful during real firewall operations.

## Example workflows

### What is this host doing?

```bash
python3 pfchat/scripts/pfchat_query.py connections --host 192.168.0.95 --limit 100
python3 pfchat/scripts/pfchat_query.py logs --host 192.168.0.95 --limit 100
python3 pfchat/scripts/pfchat_query.py ntop-host --host 192.168.0.95 --ifid 0
python3 pfchat/scripts/pfchat_query.py ntop-host-apps --host 192.168.0.95 --ifid 0
```

### Show top talkers and recent alerts

```bash
python3 pfchat/scripts/pfchat_query.py ntop-top-talkers --ifid 0 --direction local
python3 pfchat/scripts/pfchat_query.py ntop-alerts --ifid 0 --hours 24
```

### Block a host safely

```bash
python3 pfchat/scripts/pfchat_query.py block-device --target sniperhack
python3 pfchat/scripts/pfchat_query.py apply-draft --draft-id <id>
python3 pfchat/scripts/pfchat_query.py apply-draft --draft-id <id> --confirm
python3 pfchat/scripts/pfchat_query.py rollback-draft --draft-id <id> --confirm
```

### Apply a quick host-specific egress block

```bash
python3 pfchat/scripts/pfchat_query.py quick-egress-block --target sniperhack --proto tcp --port 443
python3 pfchat/scripts/pfchat_query.py quick-egress-unblock --target sniperhack --proto tcp --port 443
```

## Repository layout

```text
pfchat/
├── README.md
├── README.en.md
├── README.es.md
├── CHANGELOG.md
├── CHANGELOG.en.md
├── CHANGELOG.es.md
├── TODO.md
├── TODO.en.md
├── TODO.es.md
├── ROADMAP.md
├── ROADMAP.es.md
├── docs/
│   └── unification-2026-03-19.md
├── .env.example
├── pfchat/
│   ├── SKILL.md
│   ├── scripts/
│   │   ├── pfchat_query.py
│   │   ├── pfsense_client.py
│   │   ├── ntopng_client.py
│   │   ├── ntopng_adapter.py
│   │   └── ntopng_pyapi_backend.py
│   └── references/
│       ├── endpoints.md
│       ├── output-shapes.md
│       ├── upstream-notes.md
│       ├── investigation-patterns.md
│       └── investigation-examples.md
└── tests/
```

## Notes

- PfChat prefers the live OpenAPI schema from pfSense when available
- PfChat caches capability/schema data to reduce repeated fetches
- ntopng output is normalized so the operator gets stable JSON even when the underlying install varies
- known local device names can be enriched from local inventory data so output is more readable than raw vendor strings

## Related docs

- `pfchat/SKILL.md`
- `docs/unification-2026-03-19.md`
- `pfchat/references/endpoints.md`
- `pfchat/references/output-shapes.md`
- `pfchat/references/investigation-patterns.md`
- `pfchat/references/investigation-examples.md`
