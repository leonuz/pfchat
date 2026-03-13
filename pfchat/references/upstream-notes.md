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

### REST API self-management
- `/api/v2/system/restapi/settings`
- `/api/v2/system/restapi/version`
- `/api/v2/status/logs/packages/restapi`

## Recommended PfChat follow-up work

- Prefer schema-discovered endpoints over guessed legacy fallback paths.
- Add an optional schema discovery mode that reads `/api/v2/schema/openapi` once and caches supported paths.
- Add filtered requests for plural endpoints using upstream query filters.
- Consider GraphQL support only if a real use case appears; REST is enough for current PfChat scope.
