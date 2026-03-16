# ROADMAP — PfChat

Forward-looking plan for the next meaningful PfChat releases.

## Near term

### Safe administrative firewall actions

Planned feature set:
- block an IP address
- block a known device
- eventually support blocking a WAN-exposed port or service

Safety model:
- draft first
- preview before apply
- explicit apply step
- audit trail for who requested the change and what was sent
- prefer reversible alias/rule patterns over opaque direct edits
- no blind writes when endpoint support cannot be confirmed from the live schema

Proposed rollout:
1. schema-aware discovery of write-capable firewall endpoints  ✅
2. local draft model for proposed block actions  ✅
3. preview output showing resolved target, interface, direction, rule/alias plan, and expected impact  ✅
4. explicit apply flow  ✅
5. audit logging and basic rollback support  ✅
6. mocked integration tests for administrative flows  ✅

Current status:
- implemented for IP/device block flows
- uses saved drafts, explicit confirmation, audit logging, idempotent apply handling, and rollback scaffolding
- validated against a real pfSense lab target, including apply and rollback by pfSense object IDs
- remaining work is now operational polish, broader admin actions, and productization rather than core block/apply/rollback viability

Initial scope:
- `block-ip --draft <ip>`
- `block-device --draft <name|ip>`
- preview only first, then controlled apply

## Medium term

- ntopng adapter layer that normalizes REST v1/v2, alerts, timeseries, and historical-flow responses into PfChat-native JSON
- shared host identity resolution across pfSense inventory + ntopng host keys (`ip`, `hostname`, `FQDN`, `ip@vlan`)
- ntopng-backed top talkers, alerts, and host application summaries built on the adapter instead of raw endpoint passthrough
- Telegram summary and alert workflow on top of OpenClaw
- better support for multiple LAN/VLAN segments in inventory output
- broader compatibility with real-world pfSense REST API route variants

## Longer term

- Markdown/HTML report export
- optional external IP enrichment with GeoIP/ASN
- exploratory pfSense Plus / OPNsense compatibility
- operational/security review report templates
