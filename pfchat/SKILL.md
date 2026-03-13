---
name: pfchat
description: Query and analyze a pfSense firewall in real time through the pfSense REST API, using the current OpenClaw model instead of a hard-coded provider. Use when the user wants to inspect connected devices, active connections, firewall logs, interface status, WAN status, WAN/public IP address, system health, gateway status, or firewall rules from pfSense; investigate suspicious activity; explain what a host is doing; or generate a live security snapshot/report from pfSense API data. Also use for equivalent Spanish requests such as asking for the dirección WAN, IP WAN, IP pública del firewall, dispositivos activos, tráfico sospechoso, gateways, reglas, or a resumen del firewall.
---

# PfChat

Use this skill to turn pfSense REST API data into a live conversational security workflow inside OpenClaw.

Keep the skill model-agnostic. Do not call Anthropic or any provider SDK directly. Fetch data from pfSense, then analyze and explain it with the current agent.

## Quick workflow

1. Load connection details from environment variables or a local `.env` file.
2. Use `scripts/pfchat_query.py` to fetch only the data needed.
3. If the user asks a broad question, start with `snapshot`.
4. Summarize findings clearly, and flag anything risky or odd.
5. If the user wants a reusable artifact, produce a Markdown report from the fetched JSON.

## Configuration

Expect these variables in the environment or a `.env` file:

- `PFSENSE_HOST`
- `PFSENSE_API_KEY`
- `PFSENSE_VERIFY_SSL` (`true` or `false`)

Example:

```env
PFSENSE_HOST=192.168.0.254
PFSENSE_API_KEY=replace-me
PFSENSE_VERIFY_SSL=false
```

`PFSENSE_VERIFY_SSL=false` still uses HTTPS. It only disables certificate trust validation, which is common for pfSense deployments using self-signed certificates or an internal CA not installed on the client host.

Prefer `.env` in the current working directory when the user is working inside a repo. Do not print secrets back to the user.

## Entry points

### Live API queries

Use `scripts/pfchat_query.py` for direct pfSense access.

Common commands:

```bash
python3 skills/pfchat/scripts/pfchat_query.py capabilities
python3 skills/pfchat/scripts/pfchat_query.py devices
python3 skills/pfchat/scripts/pfchat_query.py connections --limit 200
python3 skills/pfchat/scripts/pfchat_query.py connections --limit 100 --filter source__contains=192.168.0.95
python3 skills/pfchat/scripts/pfchat_query.py logs --limit 200
python3 skills/pfchat/scripts/pfchat_query.py health
python3 skills/pfchat/scripts/pfchat_query.py rules
python3 skills/pfchat/scripts/pfchat_query.py rules --filter descr__contains=OpenVPN
python3 skills/pfchat/scripts/pfchat_query.py snapshot --limit 150
```

### Reusable Python module

If a task needs custom logic, import `scripts/pfsense_client.py` from a small one-off Python script instead of rewriting the HTTP client.

## Capability map

### 1. Inventory devices

Use `devices` when the user asks:

- what devices are connected
- how many devices are online
- which MAC belongs to an IP
- whether an unknown device is present

Prefer ARP + DHCP when the API exposes those routes. If the installation does not expose them, the client falls back to a degraded inventory inferred from `firewall/states`. In that mode, hostnames and MAC details may be unavailable.

### 2. Inspect live traffic

Use `connections` when the user asks:

- what traffic is happening now
- what a specific host is connecting to
- whether there are suspicious outbound connections
- whether a host is talking to unusual ports

Filter or post-process results locally if the raw state table is large.

### 3. Review recent firewall activity

Use `logs` when the user asks:

- what was blocked recently
- whether there is port scanning or brute force behavior
- whether a source IP looks abusive
- whether the firewall is dropping something important

For larger investigations, read `references/investigation-patterns.md`.

### 4. Check firewall and network health

Use `interfaces` and `health` when the user asks:

- whether WAN/LAN is up
- what the WAN address is
- what the public/WAN IP of the firewall is
- whether there is unusual traffic volume
- whether CPU, memory, uptime, or gateway health look bad
- whether packet loss or latency is visible

For WAN/public IP questions, inspect interface and gateway data first and answer directly.

The current client tries `system/stats` first and falls back to `status/system` when needed.

### 5. Explain rule behavior

Use `rules` when the user asks:

- what rules exist
- why something is blocked or allowed
- whether a dangerous rule may exist

Do not guess rule intent from name alone. Quote the relevant rule fields from the returned data.

## Schema-aware behavior

PfChat should prefer the live OpenAPI schema at `/api/v2/schema/openapi` when available.

Use schema discovery to:

- confirm which endpoints really exist on this installation
- prefer schema-confirmed routes over guessed legacy fallbacks
- expose a quick `capabilities` view for troubleshooting and release validation
- safely use query filters on plural GET endpoints when appropriate

If the schema is unavailable, fall back to the current hard-coded candidate list.

## Investigation defaults

When the user asks a vague security question like “anything suspicious?” or “check my firewall”, do this:

1. Run `snapshot`.
2. Inspect device inventory for unknown hosts.
3. Inspect recent logs for repeated blocked attempts from the same source.
4. Inspect active connections for unusual destinations or high-volume patterns.
5. Inspect health/gateway data for overload or WAN issues.
6. Return a compact assessment with:
   - key findings
   - evidence
   - confidence/uncertainty
   - next actions

## Output guidance

Prefer compact bullets over giant tables unless the user explicitly wants full data.

Flag notable conditions clearly, for example:

- unknown device on LAN
- many blocked hits from one source
- traffic to unusual external ports
- gateway packet loss
- high CPU or memory pressure
- unexpectedly permissive firewall rule

Separate facts from inference. If data is incomplete because an endpoint failed or the client had to use degraded mode, say so.

## Failure handling

If pfSense API calls fail:

1. Check whether `PFSENSE_HOST` and `PFSENSE_API_KEY` are present.
2. Check TLS verification mode.
3. Report HTTP/auth errors cleanly.
4. If one endpoint fails, continue with the others when possible.
5. Only treat 404 responses as endpoint-candidate fallbacks. Do not hide TLS, auth, or network failures.

Read `references/endpoints.md` for endpoint fallback behavior and version notes.

## Resources

- `scripts/pfchat_query.py` — main CLI entry point for live queries and snapshots
- `scripts/pfsense_client.py` — reusable pfSense REST API client
- `references/endpoints.md` — supported endpoints and fallback notes
- `references/investigation-patterns.md` — practical investigation heuristics and reporting patterns
