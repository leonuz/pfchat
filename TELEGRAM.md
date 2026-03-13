# PfChat via Telegram

Use OpenClaw as the Telegram-facing interface and PfChat as the pfSense capability behind it.

## Model

- Telegram = chat channel
- OpenClaw = agent runtime and routing
- PfChat = pfSense live inspection capability

You do not need a separate Telegram bot inside PfChat.
If OpenClaw is already connected to Telegram, you can ask pfSense questions directly from Telegram and let OpenClaw use the PfChat skill behind the scenes.

## Example prompts to send from Telegram

- Check my pfSense and tell me if anything looks suspicious.
- What devices are generating traffic right now?
- What is host 192.168.0.95 doing?
- Show me recent blocked traffic.
- Check WAN health and gateways.
- Review firewall rules related to OpenVPN.

## Recommended Telegram workflows

### 1. On-demand questions

Best for interactive use.

Examples:
- What devices are active right now?
- Any suspicious traffic?
- Why is the network slow?

### 2. Daily summary

Use a scheduled run that gathers:
- snapshot
- notable blocked traffic
- gateway status
- top active internal hosts

Deliver the summary back to Telegram.

### 3. Alerting

Use a scheduled run for lightweight checks such as:
- gateway offline or packet loss
- unusual spike in blocked traffic
- unexpected active internal host
- WAN-exposed rule review reminders

Keep alerts compact. Only push when something changed or looks worth attention.

## Suggested alert strategy

Start simple:

- Morning summary once per day
- One lightweight anomaly check every few hours
- No noisy per-event spam

## Operational notes

- PfChat currently depends on live pfSense API access.
- In this environment, device inventory may run in degraded mode when ARP/DHCP endpoints are not exposed by the pfSense REST API package.
- That is still useful for Telegram queries, but answers should say when device inventory was inferred from active states.

## Email delivery option

PfChat summaries can also be delivered by email instead of chat delivery when the environment has Resend configured.

Recommended use case:
- daily morning summary email
- compact security snapshot
- notable active devices
- blocked traffic highlights
- gateway/system status

## Next step to fully automate Telegram delivery

To enable automatic Telegram push alerts, OpenClaw needs the destination chat/session target for delivery.
Once that target is known, schedule isolated jobs that run PfChat checks and announce results to the Telegram destination.
