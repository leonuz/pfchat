# PfChat

PfChat is an OpenClaw skill for querying and analyzing a pfSense firewall in real time through the pfSense REST API.

It is model-agnostic: the skill fetches live data from pfSense and lets the current OpenClaw agent analyze it, instead of locking the workflow to a specific LLM provider.

## What it does

- Query connected devices using ARP/DHCP when the API exposes them
- If ARP/DHCP is unavailable in that installation, infer active internal hosts from `firewall/states`
- Inspect active firewall states and live connections
- Review recent firewall activity
- Check interface, gateway, and system status
- Review firewall rules
- Build a broad live snapshot for security triage

## Repository layout

```text
pfchat/
├── README.md
├── README.en.md
├── TODO.md
├── TODO.en.md
├── CHANGELOG.md
├── CHANGELOG.en.md
├── LICENSE
├── .gitignore
├── .env.example
├── dist/
│   └── pfchat.skill
└── pfchat/
    ├── SKILL.md
    ├── scripts/
    │   ├── pfchat_query.py
    │   └── pfsense_client.py
    └── references/
        ├── endpoints.md
        └── investigation-patterns.md
```

## Requirements

- OpenClaw
- Access to a pfSense instance with the REST API package enabled
- A pfSense API key
- Python 3.10+

## Configuration

Create a local `.env` file from `.env.example`:

```bash
cp .env.example .env
```

Example:

```env
PFSENSE_HOST=192.168.0.254
PFSENSE_API_KEY=replace-me
PFSENSE_VERIFY_SSL=false
```

Notes:
- `PFSENSE_VERIFY_SSL=false` keeps HTTPS enabled; it only disables certificate trust validation.
- This is normal when pfSense uses a self-signed certificate or an internal CA that is not installed on the client host.
- The CLI falls back to the project-local `pfchat/.env` based on the script path, which helps when the skill is invoked from another channel or working directory.
- Do not commit real API keys.

## Use as an OpenClaw skill

Place the `pfchat/` skill folder where your OpenClaw skills live, or install the packaged artifact from `dist/pfchat.skill`.

The skill is intended to trigger for requests like:

- "check what devices are connected to pfSense"
- "see if there is anything suspicious on my firewall"
- "what is iphoneLeo doing right now?"
- "review recent blocked traffic"
- "check WAN health and gateways"
- "what is my WAN address?"
- "what is my firewall public IP?"
- "show me firewall rules related to this flow"

## Use the helper CLI directly

From the repository root:

```bash
python3 pfchat/scripts/pfchat_query.py capabilities
python3 pfchat/scripts/pfchat_query.py devices
python3 pfchat/scripts/pfchat_query.py connections --limit 200
python3 pfchat/scripts/pfchat_query.py connections --limit 100 --filter source__contains=192.168.0.95
python3 pfchat/scripts/pfchat_query.py logs --limit 200
python3 pfchat/scripts/pfchat_query.py interfaces
python3 pfchat/scripts/pfchat_query.py health
python3 pfchat/scripts/pfchat_query.py rules
python3 pfchat/scripts/pfchat_query.py rules --filter descr__contains=OpenVPN
python3 pfchat/scripts/pfchat_query.py snapshot --limit 150
```

## Observed real-world compatibility

During validation against a real pfSense installation in this environment:

- `firewall/states` responded correctly
- firewall log endpoints responded through fallback handling
- `firewall/rules` responded correctly
- `status/system`, `status/interfaces`, and `status/gateways` worked as the base for the health bundle
- `status/arp` and DHCP lease endpoints were not exposed, so device inventory falls back to a degraded mode inferred from active states

This means PfChat now tolerates real REST API package variation instead of relying on a single theoretical endpoint layout.

## Design goals

- Keep the workflow OpenClaw-native
- Keep the pfSense client reusable
- Avoid provider lock-in
- Prefer clean JSON fetches and agent-side reasoning
- Tolerate endpoint variation across pfSense REST API package versions

## Telegram usage

If OpenClaw is already connected to Telegram, you do not need a separate bot inside PfChat. You can talk to OpenClaw from Telegram and let it use PfChat behind the scenes to query pfSense.

See `TELEGRAM.md` for suggested prompts, recommended workflow, and the alerting baseline.

## Daily email summary

PfChat can also be used to generate a daily firewall summary and deliver it by email when OpenClaw has Resend configured.

Recommended case:
- daily summary at 9:00 AM local time
- compact snapshot
- top active devices
- notable blocked traffic
- gateway/system status

Included local script:
- `pfchat/scripts/send_daily_summary.py`

On this host, the correct way for cron jobs and isolated sessions to inherit global variables is to load them from the `openclaw-gateway.service` unit through `EnvironmentFile`.

PfChat reports should prefer device names from the local inventory (`TOOLS.md`). If no local mapping exists, they may use reverse lookup and keep the IP only as fallback detail.

## Current status

PfChat already covers the live API workflow. The current focus is robustness, version compatibility, and a better operational experience.

See `TODO.en.md`, `CHANGELOG.en.md`, and `TELEGRAM.md` for pending work, recent changes, and channel usage.

## License

MIT
