# CHANGELOG — PfChat

All notable changes to this project will be documented in this file.

## [Unreleased]

## [0.3.0] - 2026-03-17

### Added

- Initial ntopng integration using project-local environment variables for `NTOPNG_BASE_URL`, `NTOPNG_USERNAME`, `NTOPNG_PASSWORD`, `NTOPNG_AUTH_TOKEN`, and `NTOPNG_VERIFY_SSL`.
- First-pass ntopng commands: `ntop-capabilities`, `ntop-hosts`, and `ntop-host`.
- Reusable `pfchat/scripts/ntopng_client.py` plus unit coverage for the initial ntopng transport layer.
- Documentation for ntopng-backed command output shapes and example invocation.
- Lightweight Python-API-style ntopng backend in `pfchat/scripts/ntopng_pyapi_backend.py` that follows the useful official object model (`Ntopng` / `Interface` / `Historical`) while keeping PfChat control over SSL verification and response parsing.
- Wired ntopng commands (`ntop-capabilities`, `ntop-hosts`, `ntop-host`, `ntop-top-talkers`, `ntop-alerts`, `ntop-host-apps`) to the new backend through the adapter layer.
- Clean degradation for ntopng features that are unavailable or too slow on this instance: top talkers fall back to active-host byte ranking, and ntop-alerts prefer alert-list endpoints over the slower top-alert summary path.
- Normalized flow/host alert records plus an alert summary block so ntopng alert results are easier to use conversationally.
- Eastern Time rendering for ntopng alert/host summary timestamps.
- Quiet handling of urllib3 TLS warnings when ntopng SSL verification is intentionally disabled.
- Daily summary filtering improvements based on real private-IP detection instead of a broad `172.*` prefix match.
- `delete_firewall_state()` support in `pfsense_client.py` plus test coverage for state deletion capability detection.

### Changed

- ntopng command handling now routes through an adapter layer that normalizes host output and shared identity resolution instead of returning raw endpoint-shaped payloads directly.
- ntopng transport now fails cleanly when the appliance returns the HTML login page, guiding the operator toward HTTP API auth or token-based auth instead of a JSON parse traceback.

### Validated

- Verified that the official ntopng Python API package can be installed and imported in a local virtualenv on this host.
- Verified that the official Python API self-test still fails against this ntopng instance because `connect/test.lua` returns an embedded raw HTTP response inside the body, which breaks normal JSON parsing.
- Verified that direct `curl` auth works and that the lightweight backend can successfully retrieve live ntopng data (`connect/test`, interfaces, active hosts, interface stats, L7 stats, alert lists, host apps, and host summaries) by sanitizing the malformed `connect/test.lua` body before JSON parsing.

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

- `TELEGRAM.md` documenting the recommended workflow for using PfChat through OpenClaw on Telegram
- Documentation for the daily email summary use case through OpenClaw + Resend
- `pfchat/scripts/send_daily_summary.py` to generate and send the daily summary email
- Operational support for OpenClaw Gateway-inherited global variables through `EnvironmentFile`
- Preference for device names over raw IPs in reports, using local inventory and reverse lookup as fallback
- Integration of upstream pfrest findings and the live OpenAPI schema exposed by the local instance
- Automatic discovery of supported capabilities from `/api/v2/schema/openapi`
- Initial query-filter support in `connections` and `rules`
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
- Live query support for connected devices, active connections, recent firewall logs, interfaces, system and gateway health, firewall rules, and combined snapshots
- Endpoint notes and investigation patterns under `pfchat/references/`
- Packaged `dist/pfchat.skill` artifact
- GitHub-ready repository structure
- Initial bilingual documentation
