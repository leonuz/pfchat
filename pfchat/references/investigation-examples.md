# PfChat investigation examples

These examples are based on the real workflows validated during this project.

## Investigation logic by question type

Use this quick split before choosing commands:

- use **pfSense-first** for rules, enforcement, blocked events, interfaces, gateways, health, and live state-table visibility
- use **ntopng-first** for top talkers, host behavior, applications/protocols, and alert-heavy traffic analysis
- use **both** when the user asks what a host is doing, whether something is suspicious, or whether a containment action is justified

## 1. What is my WAN IP?

Use:

```bash
python3 pfchat/scripts/pfchat_query.py health
```

Look at:
- `interfaces[].name == "wan"`
- `interfaces[].ipaddr`
- `interfaces[].gateway`
- `gateways[].status`

Typical answer style:
- WAN IP: `142.197.33.220`
- WAN gateway: `142.197.33.1`
- gateway status: `online`

## 2. What device is generating the most traffic right now?

Use:

```bash
python3 pfchat/scripts/pfchat_query.py connections --limit 200
```

Then group by internal host and sort by:
- `bytes_total`
- or number of active states

Prefer local inventory names over raw IPs in the final report.

## 3. What is iphoneLeo doing?

Use:

```bash
python3 pfchat/scripts/pfchat_query.py connections --limit 100 --host 192.168.0.95
```

Look for:
- destination hosts
- ports like `443`, `5223`, `5228`
- QUIC/UDP over `443`
- large `bytes_total`

Example interpretation:
- many `443`/`5223` flows often means normal mobile app activity, push traffic, or streaming

## 4. Show me recent blocked traffic

Use:

```bash
python3 pfchat/scripts/pfchat_query.py logs --limit 200 --action block
```

To narrow by interface:

```bash
python3 pfchat/scripts/pfchat_query.py logs --limit 200 --action block --interface vtnet1
```

To narrow by remote host:

```bash
python3 pfchat/scripts/pfchat_query.py logs --limit 200 --host 80.94.95.226
```

Look for:
- repeated hits from the same external source
- repeated destination ports
- blocks against admin or VPN-related services

## 5. Review OpenVPN-related rules

Use:

```bash
python3 pfchat/scripts/pfchat_query.py rules --filter descr__contains=OpenVPN
```

Look for:
- pass vs block
- interface
- source/destination
- broad exposure patterns

## 6. Is anything suspicious?

Use:

```bash
python3 pfchat/scripts/pfchat_query.py snapshot --limit 150
```

Then review in this order:
1. `errors`
2. `devices`
3. `logs`
4. `connections`
5. `health`
6. `rules`

High-value findings to call out:
- unknown host on LAN
- repeated blocked hits from the same source
- large outbound flows from an unexpected device
- WAN gateway degradation
- overly broad firewall rules

## 7. Which devices are active now?

Use:

```bash
python3 pfchat/scripts/pfchat_query.py devices
```

If `degraded` is false:
- ARP + DHCP data is working
- use hostname/IP/MAC/interface as normal

If `degraded` is true:
- explain that device inventory was inferred from active firewall states
- use `confidence`, `seen_as_source`, `seen_as_destination`, `interfaces`, and `peer_count` to describe how strong the inference is
- avoid overclaiming hostname confidence

## 8. Focus on port 443 only

Use:

```bash
python3 pfchat/scripts/pfchat_query.py connections --limit 100 --port 443
```

This is useful to quickly inspect:
- HTTPS activity
- QUIC over UDP 443
- heavy streaming/app traffic patterns

## 9. Show ntopng active hosts

Use:

```bash
python3 pfchat/scripts/pfchat_query.py ntop-hosts --ifid 0 --limit 20
```

Natural-language equivalents:
- "show ntopng active hosts"
- "what hosts are active on ntopng right now?"
- "show ntopng active hosts on interface 0"

Look for:
- first/last seen timestamps
- bytes and flow counts
- whether the host is local, expected, or unusual

## 10. Show ntopng top talkers

Use:

```bash
python3 pfchat/scripts/pfchat_query.py ntop-top-talkers --ifid 0 --direction local
python3 pfchat/scripts/pfchat_query.py ntop-top-talkers --ifid 0 --direction remote
```

Natural-language equivalents:
- "show ntopng top talkers"
- "show ntopng top local talkers"
- "show ntopng top remote talkers"

Look for:
- the noisiest current hosts
- whether top talkers are expected local clients or external systems
- large byte deltas that deserve host-level follow-up with `ntop-host`

## 11. Show ntopng alerts

Use:

```bash
python3 pfchat/scripts/pfchat_query.py ntop-alerts --ifid 0 --hours 24
python3 pfchat/scripts/pfchat_query.py ntop-alerts --ifid 0 --hours 24 --host 192.168.0.95
```

Natural-language equivalents:
- "show ntopng alerts from the last 24 hours"
- "show ntopng alerts for 192.168.0.95"
- "show me suspicious ntop alerts"
- "what host is generating the most alerts?"

Look for:
- severity counters
- alert type counters
- whether one host dominates the alert sample
- top alert names and top affected hosts from the normalized summary block

## 12. Show ntopng applications for one host

Use:

```bash
python3 pfchat/scripts/pfchat_query.py ntop-host-apps --host 192.168.0.95 --ifid 0
```

Natural-language equivalents:
- "what applications is 192.168.0.95 using in ntopng?"
- "show ntopng apps for ferpad.uzc"

Look for:
- dominant protocols like TLS, QUIC, HTTP, YouTube, DNS
- whether the app mix matches the device type and expected behavior

## 13. Safely block and then roll back a lab device

Draft first:

```bash
python3 pfchat/scripts/pfchat_query.py block-device --target 192.168.0.81
```

Preview the draft later if needed:

```bash
python3 pfchat/scripts/pfchat_query.py draft-show --draft-id <id>
python3 pfchat/scripts/pfchat_query.py apply-draft --draft-id <id>
```

Apply only with explicit confirmation:

```bash
python3 pfchat/scripts/pfchat_query.py apply-draft --draft-id <id> --confirm
```

Then roll back the change:

```bash
python3 pfchat/scripts/pfchat_query.py rollback-draft --draft-id <id>
python3 pfchat/scripts/pfchat_query.py rollback-draft --draft-id <id> --confirm
```

Real validation notes from this project:
- this workflow was validated against `sniperhack.uzc` (`192.168.0.81`)
- pfSense returned real object IDs for alias and rule creation
- rollback worked cleanly when those IDs were reused


## 14. Deep host triage with pfSense + ntopng

Use when the user asks a real operator question like:
- "what is this host doing?"
- "is this client suspicious?"
- "should I block this device?"

Suggested sequence:

```bash
python3 pfchat/scripts/pfchat_query.py devices
python3 pfchat/scripts/pfchat_query.py connections --host 192.168.0.95 --limit 100
python3 pfchat/scripts/pfchat_query.py logs --host 192.168.0.95 --limit 100
python3 pfchat/scripts/pfchat_query.py ntop-host --host 192.168.0.95 --ifid 0
python3 pfchat/scripts/pfchat_query.py ntop-host-apps --host 192.168.0.95 --ifid 0
python3 pfchat/scripts/pfchat_query.py ntop-alerts --host 192.168.0.95 --ifid 0 --hours 24
```

Use this to answer:
- is the host active right now?
- what destinations or ports is it using?
- what applications dominate its traffic?
- has it triggered recent alerts?
- does the observed traffic justify containment or just monitoring?

## 15. Decide between draft block vs quick egress block

Use **draft/apply/rollback** when:
- the goal is a managed firewall change
- the user may want rollback with stored metadata
- the change should look like a proper administrative action

Use **quick-egress-block** when:
- the user needs immediate temporary containment
- the goal is to test or interrupt a specific outbound dependency
- speed matters more than durable policy structure

Examples:

```bash
python3 pfchat/scripts/pfchat_query.py block-device --target sniperhack
python3 pfchat/scripts/pfchat_query.py draft-show --draft-id <id>
python3 pfchat/scripts/pfchat_query.py apply-draft --draft-id <id> --confirm
```

```bash
python3 pfchat/scripts/pfchat_query.py quick-egress-block --target sniperhack --proto tcp --port 443
python3 pfchat/scripts/pfchat_query.py quick-egress-unblock --target sniperhack --proto tcp --port 443
```

## 16. Explain whether a top talker is benign or worth containment

Use:

```bash
python3 pfchat/scripts/pfchat_query.py ntop-top-talkers --ifid 0 --direction local
python3 pfchat/scripts/pfchat_query.py ntop-host --host <host-or-ip> --ifid 0
python3 pfchat/scripts/pfchat_query.py ntop-host-apps --host <host-or-ip> --ifid 0
python3 pfchat/scripts/pfchat_query.py connections --host <host-or-ip> --limit 100
python3 pfchat/scripts/pfchat_query.py logs --host <host-or-ip> --limit 100
```

Interpretation model:
- heavy bytes + expected apps + no alerts often means normal noisy traffic
- heavy bytes + odd apps/protocols + repeated blocks/alerts deserves escalation
- repeated outbound attempts to constrained destinations may justify a temporary quick egress block during investigation
