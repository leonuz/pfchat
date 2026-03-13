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
- `seen_in_states`
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

## `snapshot`

Purpose:
- broad one-shot collection for investigation and reporting

Top-level shape:

```json
{
  "errors": {},
  "capabilities": { ... },
  "devices": { ... },
  "connections": { ... },
  "logs": { ... },
  "health": { ... },
  "rules": { ... }
}
```

If one subsection fails, PfChat should keep the others when possible and record the failure under `errors`.
