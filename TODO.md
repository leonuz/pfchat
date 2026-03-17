# TODO — PfChat

Project backlog, organized by priority.

## High priority

### ntopng integration architecture

- [x] Refactor the current ntopng support into a two-layer design: low-level transport/auth client plus a higher-level normalization/aggregation adapter
- [x] Add ntopng capability detection that distinguishes REST v1/v2, alerts, timeseries, and historical-flow support instead of assuming a uniform install
- [x] Add shared host identity resolution across pfSense + ntopng inputs (hostname, FQDN, IP, alias, VLAN-aware host key)
- [x] Keep ntopng commands returning PfChat-native normalized JSON instead of leaking raw endpoint-specific response shapes
- [x] Decide whether to replace the current custom ntopng transport path with the new lightweight Python-API-style backend for live queries
- [ ] Investigate whether the malformed `connect/test.lua` response body is a version-specific ntopng bug/proxy quirk worth working around more generally
- [x] Add richer parsing/normalization for alert-list records so conversational summaries can highlight hosts, severities, and alert families without exposing raw ntopng row structure
- [ ] Convert normalized ntopng alert epochs into ET in higher-level conversational summaries by default

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
- [x] Add ntopng top-talkers support backed by normalized adapter output rather than direct raw endpoint passthrough
- [x] Add ntopng alerts support (global + per-host) with severity normalization
- [x] Add ntopng host application/protocol summaries (L7) through a stable PfChat output model
- [x] Discover more real-world pfSense REST API endpoint variants
- [x] Add a `--once` mode or automation-oriented presets
- [x] Improve snapshot output to summarize findings more compactly
- [x] Add real investigation examples under `references/`
- [ ] Evaluate support for multiple LAN/VLAN segments in device inventory
- [ ] Extend ntopng integration beyond active hosts/host summary into historical flows, alerts, and top applications
- [x] Add immediate `quick-egress-block` / `quick-egress-unblock` operations for host-specific TCP/UDP port and ICMP toggles using temporary floating+quick rules plus state cleanup
- [ ] Extend host-specific egress blocking beyond the current single-port draft/apply/rollback path (multiple ports, richer protocol handling, target-aware unblock by port, and cleaner promotion from quick rules to permanent policy)
- [x] Add stricter `.env` validation

## Low priority

### Ideas to explore

- [ ] Evaluate whether real 72h-per-device historical activity can be exposed through ntopng, Insight, or another pfSense-adjacent source instead of only current states/logs
- [ ] Detect and use ntopng timeseries/history endpoints opportunistically, but degrade cleanly when ClickHouse/Pro-backed features are absent
- [ ] If no native historical API is available, design a lightweight OpenClaw snapshot/retention workflow to build short-term host activity history over time

- [ ] Support Markdown/HTML report export
- [ ] Consider additional packaging for distribution outside OpenClaw
- [ ] Optional external IP enrichment with GeoIP or ASN data
- [ ] Exploratory compatibility with pfSense Plus and OPNsense
- [ ] Templates for operational and security review reports
