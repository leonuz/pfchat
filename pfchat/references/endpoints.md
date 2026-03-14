# PfChat endpoint notes

Use these endpoint groups when querying pfSense through `scripts/pfchat_query.py` or `scripts/pfsense_client.py`.

## Core endpoint mapping

- `devices`
  - preferred candidates:
    - `diagnostics/arp_table`
    - `status/arp`
    - `status/arp-table`
    - `diag/arp`
    - `diagnostics/arp`
  - DHCP lease candidates:
    - `status/dhcp_server/leases`
    - `services/dhcpd/leases`
    - `status/dhcp_leases`
    - `status/dhcp/leases`
  - degraded fallback:
    - infer internal hosts from `firewall/states`
- `connections`
  - preferred candidates:
    - `firewall/states`
    - `firewall/state`
- `logs`
  - fallback sequence:
    1. `status/logs/firewall`
    2. `status/log/firewall`
    3. `log/firewall`
- `interfaces`
  - preferred candidates:
    - `status/interfaces`
    - `interfaces`
    - `interface`
- `health`
  - preferred candidates:
    - `system/stats`
    - `status/system`
  - gateway candidates:
    - `status/gateways`
    - `status/gateway`
    - `system/gateways`
  - also includes:
    - `status/interfaces`
- `rules`
  - preferred candidates:
    - `firewall/rules`
    - `firewall/rule`

## Notes

- Different pfSense REST API package versions expose different route sets.
- Many resources have both singular and plural route variants (for example `firewall/rule` and `firewall/rules`). PfChat should prefer the plural read endpoints for inspection workflows.
- Status endpoints and config endpoints are different things. For inspection, prefer `status/*` routes when available.
- Self-signed certificates are common on pfSense. `PFSENSE_VERIFY_SSL=false` keeps HTTPS enabled and only skips certificate trust validation.
- Do not assume every field is present in every response. Some endpoints differ across versions and packages.
- If one endpoint fails during `snapshot`, continue with the others and report partial results.
- Fallback should only continue on real not-found cases. Do not hide TLS, auth, or network failures.

## Real validation notes from this environment

Validated working:

- `firewall/states`
- `status/logs/firewall` / log fallback group
- `firewall/rules`
- `status/interfaces`
- `status/system`
- `status/gateways`
- `schema/openapi`

The live OpenAPI schema in this environment also shows these relevant paths:

- `diagnostics/arp_table`
- `status/dhcp_server/leases`
- `routing/gateways`
- `system/restapi/settings`
- `status/logs/packages/restapi`

Previously observed as not exposed by direct guessed paths:

- `status/arp`
- `system/stats`

The practical lesson: prefer schema-confirmed paths over guessed legacy route names when possible.

## Common investigation mapping

- "What devices are connected?" → `devices`
- "What is this host doing right now?" → `connections`, then optionally `logs`
- "Anything suspicious?" → `snapshot`
- "Why is WAN acting weird?" → `health`
- "Why is traffic blocked?" → `logs` and `rules`
