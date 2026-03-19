---
name: pfchat
description: Query, correlate, and safely administer a pfSense firewall plus its ntopng traffic-intelligence layer through APIs, using the current OpenClaw model instead of a hard-coded provider. Use when the user wants to inspect devices, active connections, firewall logs, WAN/interface/gateway/system status, firewall rules, top talkers, per-host traffic behavior, ntopng alerts, application/protocol usage, or to understand what a client is doing right now. Also use when the user wants controlled pfSense administrative actions such as drafting/applying/rolling back host blocks or quick egress controls. Also use for equivalent Spanish requests such as dirección WAN, tráfico sospechoso, top talkers, alertas de ntopng, qué está haciendo un host, bloquear un equipo, o resumen del firewall.
---

# PfChat

Use this skill to turn pfSense REST API data into a live conversational security workflow inside OpenClaw.

Keep the skill model-agnostic. Do not call Anthropic or any provider SDK directly. Fetch data from pfSense and ntopng, then analyze and explain it with the current agent.

## Quick workflow

1. Load connection details from inherited environment variables first, then portable local `.env` fallbacks.
2. Decide which backend is authoritative for the question:
   - pfSense for rules, states, logs, interfaces, gateways, and firewall administration
   - ntopng for top talkers, host behavior, apps/protocols, and alert context
3. Use `scripts/pfchat_query.py` to fetch only the data needed.
4. If the user asks a broad firewall question, start with `snapshot`.
5. If the user asks what a client is doing, combine pfSense state/log data with `ntop-*` host views.
6. If the user wants an administrative change, prefer draft/preview/confirm/rollback flows over direct mutation.
7. Summarize findings clearly, and flag anything risky or odd.
8. If the user wants a reusable artifact, produce a Markdown report from the fetched JSON.

## Configuration

Expect these variables in the environment or a local `.env` file discoverable from the current working directory or skill/project directory:

- `PFSENSE_HOST`
- `PFSENSE_API_KEY`
- `PFSENSE_VERIFY_SSL` (`true` or `false`)
- `NTOPNG_BASE_URL`
- `NTOPNG_USERNAME`
- `NTOPNG_PASSWORD`
- `NTOPNG_AUTH_TOKEN` (optional alternative to username/password)
- `NTOPNG_VERIFY_SSL` (`true` or `false`)

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

`PFSENSE_VERIFY_SSL=false` and `NTOPNG_VERIFY_SSL=false` still use HTTPS. They only disable certificate trust validation, which is common for pfSense/ntopng deployments using self-signed certificates or an internal CA not installed on the client host.

Prefer inherited environment variables first, then `.env` in the current working directory, then `.env` next to the skill/project when present. Do not print secrets back to the user.

## Entry points

### Live API queries

Use `scripts/pfchat_query.py` for direct pfSense and ntopng access.

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
python3 skills/pfchat/scripts/pfchat_query.py ntop-capabilities
python3 skills/pfchat/scripts/pfchat_query.py ntop-hosts --ifid 0 --limit 50
python3 skills/pfchat/scripts/pfchat_query.py ntop-host --host 192.168.0.95 --ifid 0
python3 skills/pfchat/scripts/pfchat_query.py ntop-top-talkers --ifid 0 --direction local
python3 skills/pfchat/scripts/pfchat_query.py ntop-alerts --ifid 0 --hours 24
python3 skills/pfchat/scripts/pfchat_query.py ntop-host-apps --host 192.168.0.95 --ifid 0
python3 skills/pfchat/scripts/pfchat_query.py ntop-network-stats --ifid 0 --hours 24 --limit 10
```

### Reusable Python module

If a task needs custom logic, import `scripts/pfsense_client.py` from a small one-off Python script instead of rewriting the HTTP client.

## Operating model

Use pfSense as the authoritative source for:

- firewall rules and enforcement
- live state-table traffic
- filterlog and recent firewall events
- interfaces, gateways, WAN status, and system health
- ARP/DHCP-backed device inventory
- administrative writes such as aliases, rules, apply, and state cleanup

Use ntopng as the authoritative source for:

- top talkers and traffic ranking
- per-host traffic profile
- application/protocol visibility
- network alerts and host alert context
- higher-level traffic summaries when firewall states are too low-level

When the user asks what a host is doing, correlate both sides instead of answering from only one backend.

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

### 6. Pivot into ntopng host intelligence

Use `ntop-hosts`, `ntop-host`, `ntop-top-talkers`, `ntop-alerts`, `ntop-host-apps`, and `ntop-network-stats` when the user asks:

- which hosts are most active right now
- what ntopng knows about a specific device
- which devices are top talkers
- whether ntopng has recent alerts for a host or interface
- what applications or protocols a host is using
- whether you can produce a network-activity summary beyond raw pfSense states

Prefer pfSense for authoritative firewall/rule/state answers. Prefer ntopng for richer host activity, applications, and alert visibility.

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
6. If the snapshot suggests a noisy or suspicious host, pivot into `ntop-top-talkers`, `ntop-host`, `ntop-host-apps`, or `ntop-alerts` for host-level explanation.
7. Return a compact assessment with:
   - key findings
   - evidence
   - confidence/uncertainty
   - next actions

For concrete multi-step examples, read `references/investigation-examples.md`.

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

- `scripts/pfchat_query.py` — main CLI entry point for live pfSense and ntopng queries
- `scripts/pfsense_client.py` — reusable pfSense REST API client
- `scripts/ntopng_client.py` — ntopng transport/auth client
- `scripts/ntopng_pyapi_backend.py` — lightweight ntopng backend with installation-aware fallbacks
- `scripts/ntopng_adapter.py` — normalized ntopng-to-PfChat adapter layer
- `references/output-shapes.md` — expected high-level JSON output by command, including visibility vs intelligence vs administrative responses
- `references/endpoints.md` — supported endpoints and fallback notes
- `references/upstream-notes.md` — upstream pfrest/OpenAPI notes for future releases
- `references/investigation-patterns.md` — practical investigation heuristics and reporting patterns
- `references/investigation-examples.md` — concrete technical playbooks for WAN, blocked traffic, top talkers, host triage, and administrative containment
