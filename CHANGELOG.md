# CHANGELOG — PfChat

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added

- Migrated the active OpenClaw `skills/pfchat` copy to include ntopng support (`ntop-capabilities`, `ntop-hosts`, `ntop-host`, `ntop-top-talkers`, `ntop-alerts`, `ntop-host-apps`, `ntop-network-stats`) so the active skill and the repo CLI expose the same capability surface.

### Changed

- PfChat now treats `/home/openclaw/.openclaw/workspace/pfchat/.env` as the single project-local setup for both pfSense and ntopng credentials.
- Both the repo CLI and the active OpenClaw skill now resolve PfChat configuration from the same shared `.env` path instead of relying on split per-location fallbacks.
- Updated bilingual documentation and skill instructions to document the unified setup and ntopng parity in the active skill.

### Validated

- Revalidated the unified setup live: the shared `pfchat/.env` works for pfSense API access and ntopng API access.

## [0.3.0] - 2026-03-17

### Added

- Added initial ntopng REST API integration with project-local environment variables for `NTOPNG_BASE_URL`, `NTOPNG_USERNAME`, `NTOPNG_PASSWORD`, `NTOPNG_AUTH_TOKEN`, and `NTOPNG_VERIFY_SSL`.
- Added first-pass ntopng commands: `ntop-capabilities`, `ntop-hosts`, and `ntop-host`.
- Added reusable `pfchat/scripts/ntopng_client.py` plus unit coverage for the initial ntopng transport layer.
- Added documentation for ntopng-backed command output shapes and example invocation.
- Added `quick-egress-block` and `quick-egress-unblock` for immediate host-specific outbound TCP/UDP port or ICMP toggles using temporary floating+quick rules on the resolved interface.
- Quick egress operations now clear matching firewall states after apply so the effect is immediate during live testing.

### Changed

- ntopng command handling now routes through an adapter layer that normalizes host output and shared identity resolution instead of returning raw endpoint-shaped payloads directly.
- ntopng transport now fails cleanly when the appliance returns the HTML login page, guiding the operator toward HTTP API auth or token-based auth instead of a JSON parse traceback.

### Added

- Added a lightweight Python-API-style ntopng backend in `pfchat/scripts/ntopng_pyapi_backend.py` that follows the official object model (`Ntopng` / `Interface` / `Historical`) while keeping PfChat control over SSL verification and response parsing.
- Wired PfChat ntopng commands (`ntop-capabilities`, `ntop-hosts`, `ntop-host`, `ntop-top-talkers`, `ntop-alerts`, `ntop-host-apps`) to the new backend through the adapter layer.
- Added clean degradation for ntopng features that are unavailable or too slow on this instance: top talkers fall back to active-host byte ranking, and ntop-alerts now prefer alert-list endpoints over the slower top-alert summary path.
- Added normalized flow/host alert records plus an alert summary block so ntopng alert results are easier to use conversationally.
- Added Eastern Time rendering for ntopng alert/host summary timestamps and suppressed noisy urllib3 TLS warnings when ntopng SSL verification is intentionally disabled.
- Added local inventory enrichment from `TOOLS.md` so ntopng host outputs can prefer stable known hostnames/descriptions over generic vendor labels.

### Validated

- Verified that the official ntopng Python API package can be installed and imported in a local virtualenv on this host.
- Verified that the official Python API self-test still fails against this ntopng instance because `connect/test.lua` returns an embedded raw HTTP response inside the body, which breaks normal JSON parsing.
- Verified that direct `curl` auth works and that the new lightweight backend can successfully retrieve live ntopng data (`connect/test`, interfaces, active hosts, interface stats, and L7 stats) by sanitizing the malformed `connect/test.lua` body before JSON parsing.

### Planned

- Next ntopng work will expand the adapter architecture into alerts, applications, top talkers, and history after the capability detection and host identity groundwork.
- Before depending on the official Python API for live ntopng data, fix ntopng-side API authentication so `/lua/rest/v2/connect/test.lua` returns JSON under the configured credentials.

### Validated

- Real pfSense validation for `quick-egress-block` / `quick-egress-unblock` against `sniperhack.uzc` for outbound ICMP and `tcp/443`, with final verification confirming no residual quick rules remained.

### Fixed

- Daily summary email now ranks internal clients by aggregated LAN traffic instead of nonexistent device fields
- Daily summary email now excludes loopback and WAN-duplicate state entries from top-flow reporting
- Daily summary email blocked-log highlights now prefer meaningful block events over noisy multicast/mDNS/IGMP chatter
- Daily summary traffic selection now uses real private-IP detection instead of a broad `172.*` prefix match
- Daily summary flow ranking no longer depends on a hard-coded pfSense interface name like `vtnet0`

## [0.2.0] - 2026-03-14

### Added

- Safe administrative firewall actions for blocking an IP/device through a `draft -> preview -> apply -> audit` workflow
- Local draft persistence, audit logging, and guarded `apply-draft --confirm`
- Rollback support using pfSense object IDs returned by real create calls
- Managed-object operations with `pfchat-managed-list`, `pfchat-managed-cleanup`, `unblock-ip`, and `unblock-device`
- Host-specific egress blocking for `tcp/udp` destination ports via `block-egress-port`
- Host-specific ICMP egress blocking via `block-egress-proto --proto icmp`
- Mocked integration coverage for the administrative apply/rollback lifecycle

### Validated

- Real pfSense validation for full-device block/apply/rollback against `sniperhack.uzc` (`192.168.0.81`)
- Real pfSense validation for host-specific `tcp/80` egress block/apply/rollback against `sniperhack.uzc`
- Real pfSense validation for host-specific ICMP egress block/apply/rollback against `sniperhack.uzc`

## [0.1.1] - 2026-03-13

### Added

- Preview-only `block-ip` and `block-device` draft workflows that resolve targets, propose alias/rule metadata, save local draft state, and report schema support without applying firewall changes
- Local draft persistence plus audit logging with `draft-list`, `draft-show`, and `apply-draft`
- Confirmed `apply-draft --confirm` path that writes alias + rule + firewall apply when the live schema confirms the required endpoints
- Draft idempotence and rollback scaffolding with `rollback-draft`, stored rollback metadata, and delete/apply support paths
- Mocked integration coverage for the end-to-end apply/rollback administrative flow
- Real pfSense validation for block/apply/rollback against a controlled lab target, plus rollback by pfSense object IDs
- Managed-object operations with `pfchat-managed-list` and `pfchat-managed-cleanup` for PfChat-created aliases and rules
- Target-based unblock flows with `unblock-ip` and `unblock-device` built on managed-object discovery
- Draft/apply support for host-specific egress port blocks such as `block-egress-port --target sniperhack --port 80 --proto tcp`
- Real pfSense validation of host-specific egress block/apply/rollback for `sniperhack` on `tcp/80`
- ICMP-capable host-specific egress drafts via `block-egress-proto --target <host> --proto icmp`
- Real pfSense validation of ICMP egress block/apply/rollback for `sniperhack`
- Single-host block rules now use the literal source IP in pfSense rule payloads instead of the generated alias name
- English-first repository document layout: `README.md`, `TODO.md`, and `CHANGELOG.md` are now the canonical English docs, with Spanish variants in `README.es.md`, `TODO.es.md`, and `CHANGELOG.es.md`
- `TELEGRAM.md` documenting the recommended workflow for using PfChat through OpenClaw on Telegram
- Documentation for the daily email summary use case through OpenClaw + Resend
- `pfchat/scripts/send_daily_summary.py` to generate and send the daily summary email
- Operational support for OpenClaw Gateway-inherited global variables through `EnvironmentFile`
- Preference for device names over raw IPs in reports, using local inventory and reverse lookup as fallback
- Integration of upstream pfrest findings and the live OpenAPI schema exposed by the local instance
- Automatic discovery of supported capabilities from `/api/v2/schema/openapi`
- Initial query-filter support in `connections` and `rules`
- Practical helper filters for `connections` and `logs` (`--host`, `--port`, `--interface`, `--contains`, `--action`)
- `references/output-shapes.md` documenting the returned JSON shape of each command
- `references/investigation-examples.md` with concrete workflows for WAN, blocked traffic, top talkers, and rule review
- Persistent local caching of the OpenAPI schema to reduce repeated discovery fetches
- Initial `unittest` suite for `pfsense_client.py` and `pfchat_query.py`
- Stricter `.env` validation for host, API key, and boolean SSL settings
- Compact snapshot `summary` section for WAN, gateways, top devices, top flows, blocked log counts, and highlights
- Mocked integration tests covering device inventory and snapshot flows without requiring a live pfSense instance
- `--once` automation presets and reduced `--view` rendering for compact workflows
- Better degraded device inference from firewall states, including interfaces, peer counts, and confidence hints
- Broader endpoint compatibility for singular/plural variants such as `firewall/state`, `firewall/rule`, `interfaces`, and `interface`
- Additional conservative endpoint fallbacks for ARP, DHCP leases, system status, and gateways based on upstream/schema patterns
- Expanded endpoint-variant notes from the live schema, including singular/plural, status/config, and service/status route families
- Explicit skill coverage for WAN address / firewall public IP questions, including Spanish phrasing
- Config fallback to the project-local `pfchat/.env` based on script path for invocations from other channels/contexts
- Real-world compatibility adjustments validated against a pfSense installation in this environment
- `health` fallback to `status/system` when `system/stats` is unavailable
- Degraded `devices` mode when ARP/DHCP endpoints are not exposed, inferring internal hosts from `firewall/states`
- Updated bilingual documentation with real compatibility findings

### Fixed

- `total_active_connections` now reflects the actual returned count
- Log endpoint fallback no longer hides real TLS, auth, or connectivity failures behind a false "endpoint not found"
- Snapshot output now returns consistent counts for connections, logs, and rules

## [0.1.0] - 2026-03-13

### Added

- Initial `PfChat` skill for OpenClaw
- Reusable pfSense REST API client in `pfchat/scripts/pfsense_client.py`
- Helper CLI in `pfchat/scripts/pfchat_query.py`
- Live query support for:
  - connected devices
  - active connections
  - recent firewall logs
  - interfaces
  - system and gateway health
  - firewall rules
  - combined snapshot output
- Endpoint notes and investigation patterns under `pfchat/references/`
- Packaged `dist/pfchat.skill` artifact
- GitHub-ready repository structure
- Initial bilingual documentation

### Changed

- The original project was adapted for OpenClaw
- The workflow is now model-agnostic and no longer depends on a provider-specific SDK for the main path

### Notes

- This release focuses on the live/API workflow
- Offline log analysis is not included in this skill
