# PfChat

[![Release](https://img.shields.io/github/v/release/leonuz/pfchat)](https://github.com/leonuz/pfchat/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![OpenClaw](https://img.shields.io/badge/OpenClaw-skill-blue)](https://docs.openclaw.ai)

PfChat es una skill de OpenClaw para consultar y analizar un firewall pfSense en tiempo real a través de la REST API de pfSense.

Es agnóstica al modelo: la skill obtiene datos vivos desde pfSense y deja el análisis al agente actual de OpenClaw, sin amarrarse a un proveedor específico de LLM.

## Qué hace

- Consulta dispositivos conectados usando ARP/DHCP cuando la API los expone
- Hace fallback a hosts activos inferidos desde `firewall/states` cuando ARP/DHCP no está disponible
- Inspecciona estados activos del firewall y conexiones en vivo
- Revisa actividad reciente del firewall
- Verifica estado de interfaces, gateways y sistema
- Revisa reglas del firewall
- Genera un snapshot útil para triage de seguridad
- Descubre capacidades soportadas desde el OpenAPI schema en vivo

## Inicio rápido

### 1. Configura el acceso a pfSense

```bash
cp .env.example .env
```

Ejemplo:

```env
PFSENSE_HOST=192.168.0.254
PFSENSE_API_KEY=replace-me
PFSENSE_VERIFY_SSL=false
```

Notas:
- `PFSENSE_VERIFY_SSL=false` mantiene HTTPS activo; solo desactiva la validación de confianza del certificado.
- Esto es normal cuando pfSense usa certificado autofirmado o una CA interna que el host cliente no tiene instalada.
- El CLI hace fallback al archivo `pfchat/.env` según la ruta del script, lo cual ayuda cuando la skill se invoca desde otros canales o directorios de trabajo.
- No subas claves reales al repositorio.

### 2. Ejecuta consultas directas

```bash
python3 pfchat/scripts/pfchat_query.py capabilities
python3 pfchat/scripts/pfchat_query.py devices
python3 pfchat/scripts/pfchat_query.py health
python3 pfchat/scripts/pfchat_query.py snapshot --limit 150
```

### 3. Úsala desde OpenClaw

Prompts típicos:

- "revisa qué dispositivos están conectados al pfSense"
- "mira si hay algo sospechoso en mi firewall"
- "qué está haciendo iphoneLeo ahora mismo"
- "cuál es mi dirección WAN"
- "muéstrame reglas de firewall relacionadas con OpenVPN"

## Ejemplo de salida

### Capacidades

```json
{
  "openapi_available": true,
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

### Health / WAN

```json
{
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
      "descr": "WAN",
      "ipaddr": "142.197.33.220",
      "gateway": "142.197.33.1",
      "status": "up"
    }
  ]
}
```

## Estructura del repositorio

```text
pfchat/
├── README.md
├── README.es.md
├── TODO.md
├── TODO.es.md
├── CHANGELOG.md
├── CHANGELOG.es.md
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
        ├── upstream-notes.md
        └── investigation-patterns.md
```

## CLI auxiliar

Desde la raíz del repo:

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

## Uso desde Telegram

Si OpenClaw ya está conectado a Telegram, no necesitas un bot separado dentro de PfChat. Puedes hablarle a OpenClaw desde Telegram y dejar que use PfChat detrás para consultar pfSense.

Consulta `TELEGRAM.md` para prompts sugeridos, flujo recomendado y base de alertas/resúmenes.

## Resumen diario por email

PfChat puede generar un resumen diario del firewall y enviarlo por correo cuando OpenClaw tenga configurado Resend.

Script local incluido:
- `scripts/send_daily_summary.py`

En este host, la forma correcta de que cron jobs y sesiones aisladas hereden variables globales es cargarlas desde el servicio `openclaw-gateway.service` mediante `EnvironmentFile`.

Los reportes de PfChat deben preferir nombres de dispositivos tomados del inventario local (`TOOLS.md`). Si no existe mapping local, pueden usar reverse lookup y dejar la IP como respaldo.

## Estado actual

PfChat ya cubre el workflow de consulta en vivo por API. El foco actual es robustez, compatibilidad entre versiones y pulido operativo.

Consulta `TODO.es.md`, `CHANGELOG.es.md` y `TELEGRAM.md` para ver pendientes, cambios y uso por canal. Las versiones base `TODO.md` y `CHANGELOG.md` están en inglés para GitHub.

## Licencia

MIT
