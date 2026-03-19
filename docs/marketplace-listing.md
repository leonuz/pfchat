# PfChat marketplace listing draft

## Name

PfChat

## Short description

API-driven pfSense + ntopng security operations skill for live visibility, investigation, and safe firewall administration.

## Tagline

Understand what hosts are doing, investigate suspicious traffic, and apply controlled pfSense actions through one skill.

## Long description

PfChat is an OpenClaw skill for operating and investigating a pfSense firewall together with its ntopng traffic-intelligence layer.

It talks directly to the pfSense REST API for authoritative firewall state, rules, interfaces, gateways, logs, device inventory, and controlled administrative changes. It also talks to ntopng for host-level traffic visibility, top talkers, alerts, applications/protocols, and higher-level network activity context.

PfChat is designed for real operator questions such as:

- what is this client doing right now?
- what traffic is a host generating?
- what did the firewall block recently?
- which systems are the top talkers?
- what applications is this device using?
- is anything suspicious happening on the network?
- should I block this host or constrain its outbound traffic?

The skill supports both observational and administrative workflows:

- inspect devices, connections, logs, interfaces, gateways, and rules
- pivot into ntopng host behavior, top talkers, alerts, and app visibility
- create draft firewall actions
- preview before apply
- confirm live changes explicitly
- roll back managed changes when needed
- apply quick host-specific egress controls during live investigation

PfChat is especially useful for security-focused pfSense environments where ntopng adds the traffic context that raw firewall states and logs do not fully explain.

## Key capabilities

- pfSense API visibility for devices, states, logs, interfaces, health, gateways, and rules
- ntopng-backed visibility for top talkers, host traffic behavior, apps/protocols, and alerts
- correlation across pfSense inventory and ntopng host intelligence
- schema-aware pfSense endpoint discovery
- safe draft/apply/rollback administrative workflows
- quick host-specific egress blocking/unblocking
- English and Spanish operational coverage

## Example prompts

- check what devices are connected to pfSense
- what is this client doing right now?
- show me recent blocked traffic
- show ntopng top talkers
- show ntopng alerts from the last 24 hours
- what applications is this host using?
- what is my WAN address?
- block this device safely
- rollback the last PfChat firewall change
- show me anything suspicious on the firewall
- muéstrame los top talkers de ntopng
- qué está haciendo este host ahora mismo
- bloquea este equipo de forma segura
- revisa si hay algo sospechoso en mi firewall

## Requirements

- pfSense with the upstream `pfSense-pkg-RESTAPI` package installed and configured
- reachable pfSense API credentials
- reachable ntopng instance for traffic-intelligence features
- valid environment variables or local `.env` configuration

## Limitations / caveats

- pfSense REST API is not native by default; the upstream package must be installed first
- ntopng-backed features depend on the local ntopng version, edition, and available endpoints
- some ntopng views may degrade gracefully when endpoints are unavailable
- administrative actions should still be treated as operator-supervised changes

## Audience

- homelab operators
- network defenders
- security engineers
- firewall administrators
- OpenClaw users running pfSense with ntopng
