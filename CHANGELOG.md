# CHANGELOG — PfChat

All notable changes to this project will be documented in this file.

## [0.1.1] - 2026-03-13

### Added

- English-first repository document layout: `README.md`, `TODO.md`, and `CHANGELOG.md` are now the canonical English docs, with Spanish variants in `README.es.md`, `TODO.es.md`, and `CHANGELOG.es.md`
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
