# PfChat upstream notes

This file captures upstream facts from the pfrest project that are directly useful for PfChat releases.

## Upstream sources

Primary canonical source:
- GitHub repository: <https://github.com/pfrest/pfSense-pkg-RESTAPI>

Published guides:
- Docs home: <https://pfrest.org>
- Installation guide: <https://pfrest.org/INSTALL_AND_CONFIG/>
- Swagger/OpenAPI guide: <https://pfrest.org/SWAGGER_AND_OPENAPI/>
- Auth guide: <https://pfrest.org/AUTHENTICATION_AND_AUTHORIZATION/>
- Query/filter guide: <https://pfrest.org/QUERIES_FILTERS_AND_SORTING/>

## High-value upstream facts

- The package exposes **200+ REST endpoints** plus **GraphQL**.
- Built-in Swagger documentation exists in the pfSense UI.
- The full OpenAPI schema is available at:
  - `/api/v2/schema/openapi`
- API key authentication via `X-API-Key` is officially supported.
- Query filters, sorting, and pagination are first-class features on plural GET endpoints.

## Real schema findings from this environment

The local pfSense instance exposes a live OpenAPI schema and reports:

- API version in schema info: `v2.7.3`
- OpenAPI schema endpoint works:
  - `/api/v2/schema/openapi`

Relevant paths discovered for PfChat:

### Devices / inventory candidates
- `/api/v2/diagnostics/arp_table`
- `/api/v2/diagnostics/arp_table/entry`
- `/api/v2/status/dhcp_server/leases`
- `/api/v2/services/dhcp_server/leases` (variant worth tolerating if exposed elsewhere)

### Traffic / rules
- `/api/v2/firewall/states`
- `/api/v2/firewall/state`
- `/api/v2/firewall/rules`
- `/api/v2/status/logs/firewall`

### Health / interfaces / gateways
- `/api/v2/status/system`
- `/api/v2/status/interfaces`
- `/api/v2/status/gateways`
- `/api/v2/routing/gateways`
- `/api/v2/interface`
- `/api/v2/interfaces`

### Logs / focused status endpoints
- `/api/v2/status/logs/firewall`
- `/api/v2/status/logs/system`
- `/api/v2/status/logs/auth`
- `/api/v2/status/logs/dhcp`
- `/api/v2/status/logs/openvpn`
- `/api/v2/status/logs/packages/restapi`

### Routing / network config endpoints worth tracking
- `/api/v2/routing/gateway`
- `/api/v2/routing/gateway/group`
- `/api/v2/routing/static_route`
- `/api/v2/interface/vlan`
- `/api/v2/interface/group`
- `/api/v2/interface/bridge`

### REST API self-management
- `/api/v2/system/restapi/settings`
- `/api/v2/system/restapi/version`
- `/api/v2/status/logs/packages/restapi`

## Real schema compatibility notes

The local schema shows a useful pattern for future compatibility work:

- many resources expose both singular and plural endpoints
  - examples: `firewall/rule` + `firewall/rules`, `routing/gateway` + `routing/gateways`, `interface` + `interfaces`
- status endpoints and config endpoints are distinct
  - examples: `status/gateways` vs `routing/gateways`, `status/interfaces` vs `interfaces`
- service configuration and service status are also distinct
  - examples: `services/dhcp_server/*` vs `status/dhcp_server/leases`

For future releases, PfChat should keep preferring read-only status endpoints for live inspection, while documenting config endpoints separately for administrative write actions.

Applied compatibility rule in PfChat:
- prefer plural read/status endpoints first
- allow singular/plural fallback variants when the live schema confirms a different shape on another installation

## Recommended PfChat follow-up work

- Prefer schema-discovered endpoints over guessed legacy fallback paths.
- Add an optional schema discovery mode that reads `/api/v2/schema/openapi` once and caches supported paths.
- Add filtered requests for plural endpoints using upstream query filters.
- Consider GraphQL support only if a real use case appears; REST is enough for current PfChat scope.
