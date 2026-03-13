# TODO — PfChat

Project backlog, organized by priority.

## High priority

- [x] Load/configure `RESEND_API_KEY` in the environment to enable actual delivery of the daily email summary
- [ ] Add optional custom CA support (`PFSENSE_CA_FILE`) so certificates can be validated without relying on `PFSENSE_VERIFY_SSL=false`  ← requested, but do not implement yet
- [x] Add optional endpoint discovery from `/api/v2/schema/openapi` and cache supported capabilities
- [x] Add optional persistent caching of the OpenAPI schema to reduce repeated fetches
- [ ] Refine device inference when ARP/DHCP endpoints are not exposed by the API
- [x] Add host/IP/port filters to reduce noise in `connections` and `logs`
- [x] Add unit tests for `pfsense_client.py` and `pfchat_query.py`
- [ ] Add integration tests using mocked pfSense responses
- [x] Better document the output shape for each command

## Medium priority

- [ ] Add a documented and automatable Telegram summary/alert workflow on top of OpenClaw
- [ ] Discover more real-world pfSense REST API endpoint variants
- [ ] Add a `--once` mode or automation-oriented presets
- [ ] Improve snapshot output to summarize findings more compactly
- [ ] Add real investigation examples under `references/`
- [ ] Evaluate support for multiple LAN/VLAN segments in device inventory
- [ ] Add stricter `.env` validation

## Low priority

- [ ] Support Markdown/HTML report export
- [ ] Consider additional packaging for distribution outside OpenClaw
- [ ] Optional external IP enrichment with GeoIP or ASN data
- [ ] Exploratory compatibility with pfSense Plus and OPNsense
- [ ] Templates for operational and security review reports
