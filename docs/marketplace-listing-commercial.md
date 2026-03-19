# PfChat marketplace listing — commercial version

## Name

PfChat

## Short description

Turn pfSense + ntopng into a live security operations assistant for visibility, investigation, and safe firewall actions.

## Tagline

See what hosts are doing, spot suspicious traffic, and act safely on pfSense from one skill.

## Long description

PfChat turns your pfSense firewall and ntopng traffic intelligence into one conversational security workflow inside OpenClaw.

Instead of jumping between firewall pages, traffic dashboards, and manual API calls, PfChat gives you one interface for understanding what is happening on your network and taking controlled action when needed.

With PfChat, you can:

- inspect connected devices and live traffic
- review blocked traffic and firewall behavior
- check WAN, interfaces, gateways, and system health
- identify top talkers and noisy clients
- understand what a host is doing right now
- review alerts and application/protocol activity from ntopng
- safely block hosts or constrain outbound traffic with preview / apply / rollback workflows

PfChat combines the strengths of both systems:

- pfSense provides authoritative firewall state, rules, logs, interfaces, and safe administrative control
- ntopng provides the traffic context pfSense alone does not fully explain, including host activity, top talkers, alerts, and app visibility

That makes PfChat especially useful for:

- homelab security operations
- network troubleshooting
- firewall investigations
- device behavior analysis
- fast containment during live incidents
- day-to-day pfSense administration with better traffic context

PfChat is designed for real questions operators ask every day:

- What is this client doing right now?
- Why is this device generating so much traffic?
- What did the firewall block recently?
- Is anything suspicious happening on the network?
- Should I block this host or just restrict one outbound dependency?
- What does ntopng know about this device?

If you run pfSense with ntopng and want a faster, more operational way to investigate and act, PfChat is built for exactly that.

## Key capabilities

- Live pfSense visibility for devices, states, logs, interfaces, gateways, health, and rules
- ntopng-powered host intelligence for top talkers, alerts, traffic behavior, and applications
- host-centric investigation workflows that combine firewall truth with traffic context
- safe firewall administration with draft / preview / confirm / rollback flows
- quick host-specific egress controls for live containment and testing
- English and Spanish operational support

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

## Why people will want it

- It reduces friction between visibility and action
- It makes pfSense + ntopng feel like one operational system
- It helps answer host behavior questions much faster
- It adds safer administrative workflows instead of raw one-shot firewall mutations
- It is useful for both daily operations and incident-driven investigation

## Requirements

- pfSense with the upstream `pfSense-pkg-RESTAPI` package installed and configured
- reachable pfSense API credentials
- reachable ntopng instance for traffic-intelligence features
- valid environment variables or local `.env` configuration

## Limitations / caveats

- pfSense REST API is not native by default; the upstream package must be installed first
- ntopng-backed features depend on the local ntopng version, edition, and exposed endpoints
- some ntopng views may degrade gracefully when certain endpoints are unavailable
- firewall changes should still be treated as operator-supervised actions

## Audience

- homelab operators
- security engineers
- firewall admins
- defenders
- OpenClaw users running pfSense + ntopng
