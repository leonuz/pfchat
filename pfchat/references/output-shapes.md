# PfChat output shapes

This file documents the high-level JSON shape returned by each CLI command.

These are not strict schemas. Fields may vary across pfSense versions and package builds, but these are the practical top-level shapes you should expect.

## `capabilities`

Purpose:
- show whether OpenAPI discovery worked
- expose supported paths
- summarize core feature availability

Top-level shape:

```json
{
  "openapi_available": true,
  "supported_paths": ["firewall/states", "status/system"],
  "capabilities": {
    "devices_arp": true,
    "devices_dhcp": true,
    "connections": true,
    "logs_firewall": true,
    "rules": true,
    "interfaces": true,
    "system_status": true,
    "gateways": true
  }
}
```

## `devices`

Purpose:
- inventory connected devices from ARP + DHCP
- or fall back to inferred hosts when needed

Top-level shape:

```json
{
  "total_devices": 34,
  "devices": [
    {
      "hostname": "iphoneLeo",
      "ip_address": "192.168.0.95",
      "mac_address": "80:96:98:58:4a:39",
      "interface": "LAN",
      "source": "arp_dhcp"
    }
  ],
  "dhcp_leases_total": 42,
  "degraded": false
}
```

Fallback/inferred mode may instead contain:
- `ip`
- `hostname`
- `seen_in_states`
- `seen_as_source`
- `seen_as_destination`
- `interfaces`
- `peer_count`
- `confidence`
- `degraded_reason`

## `connections`

Purpose:
- show active firewall states / live traffic

Top-level shape:

```json
{
  "total_active_connections": 20,
  "connections": [
    {
      "interface": "vtnet0",
      "protocol": "tcp",
      "source": "192.168.0.95:62042",
      "destination": "216.239.36.131:5223",
      "state": "ESTABLISHED:ESTABLISHED",
      "bytes_total": 17574
    }
  ],
  "applied_filters": {
    "source__contains": "192.168.0.95"
  }
}
```

## `logs`

Purpose:
- show recent firewall log entries
- optionally attach parsed filterlog fields when matching traffic lines

Top-level shape:

```json
{
  "total_entries": 5,
  "logs": [
    {
      "id": 1,
      "text": "Mar 13 ... filterlog...",
      "parsed": {
        "interface": "vtnet1",
        "action": "block",
        "src": "80.94.95.226",
        "dst": "142.197.33.220",
        "dst_port": "8443"
      }
    }
  ],
  "applied_filters": {
    "host": "80.94.95.226",
    "port": null,
    "interface": "vtnet1",
    "contains": null,
    "action": "block"
  }
}
```

If a line is not a filterlog traffic line, `parsed` may be absent.

## `interfaces`

Purpose:
- inspect pfSense interface status

Top-level shape:

```json
{
  "interfaces": [
    {
      "name": "wan",
      "descr": "WAN",
      "ipaddr": "142.197.33.220",
      "gateway": "142.197.33.1",
      "status": "up"
    }
  ]
}
```

## `health`

Purpose:
- combine system, gateway, and interface health in one response

Top-level shape:

```json
{
  "system": {
    "uptime": "12 Days 14 Hours",
    "cpu_usage": 28.5,
    "mem_usage": 13,
    "disk_usage": 5
  },
  "gateways": [
    {
      "name": "WAN_DHCP",
      "srcip": "142.197.33.220",
      "monitorip": "142.197.33.1",
      "status": "online"
    }
  ],
  "interfaces": [
    {
      "name": "wan",
      "ipaddr": "142.197.33.220",
      "status": "up"
    }
  ]
}
```

## `rules`

Purpose:
- inspect firewall rules
- optionally filter by query params

Top-level shape:

```json
{
  "total_rules": 12,
  "rules": [
    {
      "descr": "OpenVPN",
      "interface": "wan",
      "type": "pass"
    }
  ],
  "applied_filters": {
    "descr__contains": "OpenVPN"
  }
}
```

## `block-ip` / `block-device`

Purpose:
- create a persisted draft for a safe firewall block workflow

Top-level shape:

```json
{
  "mode": "draft",
  "command": "block-device",
  "apply_status": "draft-only",
  "draft_id": "12d4154718ac",
  "target": {
    "input": "192.168.0.81",
    "kind": "device",
    "resolution": "device-match",
    "hostname": "sniperhack",
    "ip": "192.168.0.81"
  },
  "proposal": {
    "alias_name": "pfb_sniperhack_192_168_0_81",
    "rule_interface": "lan",
    "rule_action": "block"
  },
  "schema_support": {
    "firewall_aliases_write": true,
    "firewall_apply": true
  }
}
```

## `apply-draft`

Purpose:
- preview or execute a saved firewall block draft

Preview shape:

```json
{
  "mode": "apply-preview",
  "draft_id": "12d4154718ac",
  "status": "ready-for-confirmation",
  "draft": { ... }
}
```

Confirmed apply shape:

```json
{
  "mode": "apply",
  "draft_id": "12d4154718ac",
  "status": "applied",
  "results": {
    "alias": {"id": 3, "name": "pfb_sniperhack_192_168_0_81"},
    "rule": {"id": 5, "descr": "PfChat draft block for sniperhack (192.168.0.81)"},
    "apply": {"applied": true}
  }
}
```

If the same draft is applied again, shape may instead be:
- `status: "already-applied"`

## `rollback-draft`

Purpose:
- preview or execute rollback for a previously applied draft

Confirmed rollback shape:

```json
{
  "mode": "rollback",
  "draft_id": "12d4154718ac",
  "status": "rolled-back",
  "results": {
    "rule_delete": {"id": 5},
    "alias_delete": {"id": 3},
    "apply": {"applied": true}
  }
}
```

## `snapshot`

Purpose:
- broad one-shot collection for investigation and reporting

Top-level shape:

```json
{
  "errors": {},
  "summary": {
    "wan": {"ipaddr": "142.197.33.220", "gateway": "142.197.33.1", "status": "up"},
    "gateway_status": {"online": ["WAN_DHCP"], "total": 1},
    "device_summary": {"total_devices": 34, "degraded": false, "top_active_devices": [ ... ]},
    "connection_summary": {"total_active_connections": 120, "top_flows": [ ... ]},
    "log_summary": {"total_entries": 150, "blocked_entries_in_sample": 24},
    "rule_summary": {"total_rules": 12},
    "highlights": ["WAN 142.197.33.220 via 142.197.33.1 is up"]
  },
  "capabilities": { ... },
  "devices": { ... },
  "connections": { ... },
  "logs": { ... },
  "health": { ... },
  "rules": { ... }
}
```

If one subsection fails, PfChat should keep the others when possible and record the failure under `errors`.
The `summary` block is meant to be the first compact layer for Telegram, email summaries, and fast triage.
