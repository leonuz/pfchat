# PfChat investigation examples

These examples are based on the real workflows validated during this project.

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
