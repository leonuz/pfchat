# TODO — PfChat

Project backlog, organized by priority.

## High priority

- [x] Add safe administrative firewall actions for blocking an IP/device using `draft -> preview -> apply -> audit` workflow
- [x] Strengthen rollback using pfSense-native object identifiers where available instead of descriptive delete heuristics
- [x] Add live-fire validation against a controlled lab target before recommending production use
- [x] Load/configure `RESEND_API_KEY` in the environment to enable actual delivery of the daily email summary
- [ ] Add optional custom CA support (`PFSENSE_CA_FILE`) so certificates can be validated without relying on `PFSENSE_VERIFY_SSL=false`  ← requested, but do not implement yet
- [x] Add optional endpoint discovery from `/api/v2/schema/openapi` and cache supported capabilities
- [x] Add optional persistent caching of the OpenAPI schema to reduce repeated fetches
- [x] Refine device inference when ARP/DHCP endpoints are not exposed by the API
- [x] Add host/IP/port filters to reduce noise in `connections` and `logs`
- [x] Add unit tests for `pfsense_client.py` and `pfchat_query.py`
- [x] Add integration tests using mocked pfSense responses
- [x] Better document the output shape for each command

## Medium priority

- [ ] Add a documented and automatable Telegram summary/alert workflow on top of OpenClaw
- [x] Discover more real-world pfSense REST API endpoint variants
- [x] Add a `--once` mode or automation-oriented presets
- [x] Improve snapshot output to summarize findings more compactly
- [x] Add real investigation examples under `references/`
- [ ] Evaluate support for multiple LAN/VLAN segments in device inventory
- [x] Add stricter `.env` validation

## Low priority

- [ ] Support Markdown/HTML report export
- [ ] Consider additional packaging for distribution outside OpenClaw
- [ ] Optional external IP enrichment with GeoIP or ASN data
- [ ] Exploratory compatibility with pfSense Plus and OPNsense
- [ ] Templates for operational and security review reports
