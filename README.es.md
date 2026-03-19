# PfChat

[![Release](https://img.shields.io/github/v/release/leonuz/pfchat)](https://github.com/leonuz/pfchat/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![OpenClaw](https://img.shields.io/badge/OpenClaw-skill-blue)](https://docs.openclaw.ai)

PfChat es un flujo operacional y de seguridad, guiado por API, para **pfSense** más **ntopng**.

Habla directamente con:

- la **REST API de pfSense** para estado autoritativo del firewall, reglas, interfaces, gateways, logs, inventario de dispositivos y cambios administrativos controlados
- la **API de ntopng** para visibilidad de tráfico por host, top talkers, alertas, aplicaciones y contexto de actividad de red

En la práctica, PfChat está pensado para responder preguntas como:

- ¿qué está haciendo este cliente ahora mismo?
- ¿qué tráfico está generando un host?
- ¿qué fue bloqueado recientemente?
- ¿cuáles son los top talkers?
- ¿qué aplicaciones está usando este dispositivo?
- ¿está ocurriendo algo sospechoso en el firewall?
- ¿puedo bloquear este host o restringir su tráfico saliente de forma segura?

PfChat es agnóstico al modelo: obtiene datos vivos desde pfSense y ntopng, y luego deja el análisis conversacional al agente actual de OpenClaw.

## Qué es realmente PfChat

PfChat no es solo un lector de pfSense ni solo un wrapper de ntopng.

Combina:

- **pfSense** para verdad autoritativa del firewall y administración
- **ntopng** para inteligencia de red y comportamiento por host
- **OpenClaw** para workflows de investigación, resúmenes e interacción orientada al operador

Piénsalo así:

- **pfSense** te dice qué sabe y qué está aplicando el firewall
- **ntopng** te dice qué están haciendo los hosts en la red
- **PfChat** junta ambas cosas en una sola interfaz operacional

## Arquitectura

```text
+-----------------------------+
| OpenClaw / CLI / Operador   |
+-------------+---------------+
              |
              v
+-----------------------------+
|           PfChat            |
| consultar / correlacionar / |
| actuar                      |
+-------------+---------------+
              |
      +-------+-------+         +--------+--------+
      | pfSense REST  |         |   API de ntopng |
      | API           |         | (tráfico, hosts,|
      |               |         | alertas, apps)  |
      +-------+-------+         +--------+--------+
              |                          |
              v                          v
 estado firewall / reglas /     actividad por host / top talkers /
 logs / interfaces / apply      apps / alertas / contexto de tráfico
```

## Capacidades principales

### 1. Visibilidad

Usa PfChat para inspeccionar estado vivo de red y firewall:

- dispositivos conectados
- estados activos del firewall
- eventos recientes bloqueados o permitidos
- salud de interfaces y gateways
- visibilidad de WAN / IP pública
- reglas del firewall
- top talkers
- hosts activos en ntopng
- resúmenes de apps/protocolos por host
- alertas recientes y resúmenes de actividad

### 2. Investigación

Usa PfChat para preguntas orientadas a seguridad como:

- ¿qué está haciendo `iphoneLeo` ahora mismo?
- ¿qué cliente está generando más tráfico?
- ¿qué bloqueó el firewall en la última hora?
- ¿ntopng muestra algo sospechoso para este host?
- ¿qué apps está usando este cliente?
- ¿este host habla con destinos o puertos raros?
- ¿el firewall está sano, sobrecargado o bloqueando algo importante?

### 3. Administración

PfChat también es una superficie operacional de control para pfSense.

Puede realizar acciones administrativas controladas como:

- crear drafts de bloqueo para IPs o dispositivos
- aplicar drafts con confirmación
- revertir cambios gestionados
- listar y limpiar objetos creados por PfChat
- ejecutar bloqueos/desbloqueos rápidos de egress por host

Las acciones administrativas están deliberadamente protegidas mediante flujos de preview / confirm / rollback en vez de mutaciones ciegas.

## Por qué importa juntar pfSense + ntopng

pfSense y ntopng resuelven partes distintas del problema.

### pfSense es mejor para

- reglas
- enforcement
- interfaces y gateways
- logs del firewall
- descubrimiento de dispositivos vía ARP/DHCP cuando está expuesto
- escrituras controladas como cambios de reglas o aliases

### ntopng es mejor para

- top talkers
- comportamiento de tráfico por host
- resúmenes de aplicaciones/protocolos por host
- alertas recientes y contexto de actividad de red
- responder “¿qué está haciendo realmente este cliente?”

### PfChat usa ambos

Workflow típico:

1. usa **pfSense** para confirmar host, interfaz, reglas, estados y actividad bloqueada
2. usa **ntopng** para entender volumen de tráfico, aplicaciones, comportamiento y alertas
3. usa **PfChat** para resumir hallazgos o ejecutar una acción administrativa segura

## Workflows enfocados en seguridad

### Investigar un cliente

Ejemplos:

- identificar el host en el inventario de pfSense
- inspeccionar estados actuales del firewall para ese host
- revisar logs recientes del firewall
- pivotar a detalles del host en ntopng
- revisar aplicaciones principales y alertas
- decidir si conviene monitorear, bloquear o limitar egress

### Encontrar top talkers

Ejemplos:

- usar vistas de top talkers de ntopng cuando estén soportadas
- degradar limpiamente cuando algunos endpoints de ntopng no estén disponibles
- correlacionar top talkers con identidad del dispositivo en pfSense y contexto de interfaz

### Revisar tráfico bloqueado

Ejemplos:

- inspeccionar actividad reciente de filterlog en pfSense
- aislar bloqueos repetidos de una misma fuente
- compararlo con alertas de ntopng o comportamiento por host
- decidir si es ruido, mala configuración o actividad sospechosa

### Aplicar una acción segura de firewall

Ejemplos:

- crear draft de bloqueo de un host
- previsualizar el plan de rule/alias
- confirmar el cambio
- verificar impacto
- hacer rollback si hace falta

## Instalación de la REST API de pfSense

Esta sección importa porque **la API de pfSense no viene nativa por defecto**.
PfChat depende del paquete upstream **pfSense-pkg-RESTAPI** instalado en el firewall.

### 1. Instalar el paquete

Proyecto upstream canónico:
- <https://github.com/pfrest/pfSense-pkg-RESTAPI>

Documentación útil upstream:
- instalación: <https://pfrest.org/INSTALL_AND_CONFIG/>
- autenticación: <https://pfrest.org/AUTHENTICATION_AND_AUTHORIZATION/>
- Swagger/OpenAPI: <https://pfrest.org/SWAGGER_AND_OPENAPI/>

Walkthrough práctico usado durante este proyecto:
- <https://www.youtube.com/watch?v=inqMEOEVtao>

Comando típico de instalación para pfSense CE:

```bash
pkg-static add https://github.com/pfrest/pfSense-pkg-RESTAPI/releases/latest/download/pfSense-2.8.1-pkg-RESTAPI.pkg
```

Comando típico de instalación para pfSense Plus:

```bash
pkg-static -C /dev/null add https://github.com/pfrest/pfSense-pkg-RESTAPI/releases/latest/download/pfSense-25.11-pkg-RESTAPI.pkg
```

Notas importantes:

- usa el paquete que corresponda a tu versión exacta de pfSense
- los paquetes no oficiales pueden desaparecer después de upgrades de pfSense, así que puede tocar reinstalarlo
- PfChat fue validado contra una instancia real de pfSense que expone `/api/v2/schema/openapi`

### 2. Configurar la API en pfSense

Después de instalar, verifica:

- que exista `System -> REST API` en el webConfigurator
- que la REST API esté habilitada/configurada correctamente
- que el método de autenticación que vas a usar esté permitido
- que la cuenta detrás de la API key tenga los permisos que necesitas

### 3. Crear una API key

PfChat usa por defecto **autenticación por API key** para pfSense mediante el header `X-API-Key`.

Según la documentación upstream, las claves se gestionan desde:

- `System -> REST API -> Keys`

Notas importantes:

- la clave hereda los privilegios del usuario que la creó
- trátala como un secreto
- si se expone, revócala y genera una nueva

### 4. Validar la API antes de culpar a PfChat

Chequeos útiles:

- confirma que la API responde en `https://<pfsense>/api/v2/...`
- confirma que tu API key funciona
- confirma que el OpenAPI schema en vivo responde en `/api/v2/schema/openapi`
- confirma que los endpoints que te importan existen en ese schema

Si `/api/v2/schema/openapi` responde, PfChat puede usar descubrimiento basado en schema y adaptarse mucho mejor a esa instalación.

## Qué espera PfChat de ntopng

PfChat espera una instancia accesible de ntopng consultable por HTTP(S).
En muchos entornos esa será la instancia de ntopng integrada con o adyacente a pfSense.

PfChat usa ntopng para:

- hosts activos
- top talkers
- perfiles de host
- aplicaciones/protocolos por host
- alertas
- resúmenes de actividad de red

Notas importantes:

- algunos endpoints de ntopng varían según versión, edición o comportamiento local
- algunos endpoints de top talkers pueden ser Pro-only
- PfChat incluye fallbacks y normalización para mantener una salida estable aunque el comportamiento de ntopng varíe
- si ntopng devuelve HTML de login en vez de JSON, habilita API auth o usa un token de auth

## Configuración

PfChat usa este archivo como setup local único del proyecto:

- `/home/openclaw/.openclaw/workspace/pfchat/.env`

Créalo desde el ejemplo:

```bash
cp .env.example .env
```

Ejemplo:

```env
PFSENSE_HOST=192.168.0.254
PFSENSE_API_KEY=replace-me
PFSENSE_VERIFY_SSL=false

NTOPNG_BASE_URL=https://192.168.0.254:3000
NTOPNG_USERNAME=admin
NTOPNG_PASSWORD=replace-me
NTOPNG_AUTH_TOKEN=
NTOPNG_VERIFY_SSL=false
```

### Variables de pfSense

- `PFSENSE_HOST` — solo host o IP, sin `https://` ni paths
- `PFSENSE_API_KEY` — API key real, no el placeholder
- `PFSENSE_VERIFY_SSL` — acepta `true/false`, `1/0`, `yes/no`, `on/off`

### Variables de ntopng

- `NTOPNG_BASE_URL` — URL completa como `https://192.168.0.254:3000`
- `NTOPNG_USERNAME` / `NTOPNG_PASSWORD` — usados para Basic Auth cuando HTTP API auth está habilitado
- `NTOPNG_AUTH_TOKEN` — alternativa opcional con prioridad sobre usuario/contraseña si está presente
- `NTOPNG_VERIFY_SSL` — acepta las mismas formas booleanas que pfSense

### Nota TLS

`PFSENSE_VERIFY_SSL=false` y `NTOPNG_VERIFY_SSL=false` siguen usando HTTPS.
Solo desactivan la validación de confianza del certificado, algo común con certificados autofirmados o CAs internas no instaladas en el cliente.

### Nota importante de configuración

PfChat ahora usa la misma setup local en ambas superficies:

- el CLI del repo
- la skill activa de OpenClaw

Ya no existe la separación donde ntopng vivía en una superficie y no en la otra.

No subas API keys, passwords ni tokens reales al repositorio.

## Inicio rápido

### Ejecutar consultas directas por CLI

```bash
python3 pfchat/scripts/pfchat_query.py capabilities
python3 pfchat/scripts/pfchat_query.py devices
python3 pfchat/scripts/pfchat_query.py health
python3 pfchat/scripts/pfchat_query.py snapshot --limit 150
python3 pfchat/scripts/pfchat_query.py ntop-capabilities
python3 pfchat/scripts/pfchat_query.py ntop-hosts --ifid 0 --limit 50
python3 pfchat/scripts/pfchat_query.py ntop-host --host 192.168.0.95 --ifid 0
python3 pfchat/scripts/pfchat_query.py ntop-top-talkers --ifid 0 --direction local
python3 pfchat/scripts/pfchat_query.py ntop-alerts --ifid 0 --hours 24
python3 pfchat/scripts/pfchat_query.py ntop-host-apps --host 192.168.0.95 --ifid 0
python3 pfchat/scripts/pfchat_query.py ntop-network-stats --ifid 0 --hours 24 --limit 10
```

### Usarlo desde OpenClaw

Ejemplos:

- `revisa qué dispositivos están conectados al pfSense`
- `mira si hay algo sospechoso en mi firewall`
- `qué está haciendo iphoneLeo ahora mismo`
- `cuál es mi dirección WAN`
- `muéstrame reglas de firewall relacionadas con OpenVPN`
- `muéstrame hosts activos en ntopng`
- `qué sabe ntopng sobre 192.168.0.160`
- `muéstrame los top talkers de ntopng`
- `muéstrame alertas de ntopng de las últimas 24 horas`
- `qué aplicaciones está usando 192.168.0.95 en ntopng`

## Comandos por categoría

### Estado y visibilidad de pfSense

- `capabilities`
- `devices`
- `connections`
- `logs`
- `interfaces`
- `health`
- `rules`
- `snapshot`

### Inteligencia con ntopng

- `ntop-capabilities`
- `ntop-hosts`
- `ntop-host`
- `ntop-top-talkers`
- `ntop-alerts`
- `ntop-host-apps`
- `ntop-network-stats`

### Acciones administrativas seguras

- `block-ip`
- `block-device`
- `block-egress-port`
- `block-egress-proto`
- `apply-draft`
- `rollback-draft`
- `quick-egress-block`
- `quick-egress-unblock`
- `unblock-ip`
- `unblock-device`
- `pfchat-managed-list`
- `pfchat-managed-cleanup`

## Modelo de administración segura

PfChat soporta cambios administrativos reales sobre pfSense, pero está diseñado alrededor de guardrails:

- draft primero
- preview antes del apply
- confirm explícito para cambios live
- soporte de rollback cuando aplica
- soporte de cleanup de objetos gestionados
- validaciones basadas en schema antes de usar rutas de escritura

Esto importa porque PfChat no es solo para observar. También está pensado para ser útil durante operaciones reales de firewall.

## Workflows de ejemplo

### ¿Qué está haciendo este host?

```bash
python3 pfchat/scripts/pfchat_query.py connections --host 192.168.0.95 --limit 100
python3 pfchat/scripts/pfchat_query.py logs --host 192.168.0.95 --limit 100
python3 pfchat/scripts/pfchat_query.py ntop-host --host 192.168.0.95 --ifid 0
python3 pfchat/scripts/pfchat_query.py ntop-host-apps --host 192.168.0.95 --ifid 0
```

### Mostrar top talkers y alertas recientes

```bash
python3 pfchat/scripts/pfchat_query.py ntop-top-talkers --ifid 0 --direction local
python3 pfchat/scripts/pfchat_query.py ntop-alerts --ifid 0 --hours 24
```

### Bloquear un host de forma segura

```bash
python3 pfchat/scripts/pfchat_query.py block-device --target sniperhack
python3 pfchat/scripts/pfchat_query.py apply-draft --draft-id <id>
python3 pfchat/scripts/pfchat_query.py apply-draft --draft-id <id> --confirm
python3 pfchat/scripts/pfchat_query.py rollback-draft --draft-id <id> --confirm
```

### Aplicar un bloqueo rápido de egress por host

```bash
python3 pfchat/scripts/pfchat_query.py quick-egress-block --target sniperhack --proto tcp --port 443
python3 pfchat/scripts/pfchat_query.py quick-egress-unblock --target sniperhack --proto tcp --port 443
```

## Estructura del repositorio

```text
pfchat/
├── README.md
├── README.en.md
├── README.es.md
├── CHANGELOG.md
├── CHANGELOG.en.md
├── CHANGELOG.es.md
├── TODO.md
├── TODO.en.md
├── TODO.es.md
├── ROADMAP.md
├── ROADMAP.es.md
├── docs/
│   └── unification-2026-03-19.md
├── .env.example
├── pfchat/
│   ├── SKILL.md
│   ├── scripts/
│   │   ├── pfchat_query.py
│   │   ├── pfsense_client.py
│   │   ├── ntopng_client.py
│   │   ├── ntopng_adapter.py
│   │   └── ntopng_pyapi_backend.py
│   └── references/
│       ├── endpoints.md
│       ├── output-shapes.md
│       ├── upstream-notes.md
│       ├── investigation-patterns.md
│       └── investigation-examples.md
└── tests/
```

## Notas

- PfChat prefiere el OpenAPI schema live de pfSense cuando está disponible
- PfChat cachea datos de capacidades/schema para reducir fetches repetidos
- la salida de ntopng se normaliza para que el operador reciba JSON estable aunque cambie la instalación subyacente
- los nombres conocidos de dispositivos locales pueden enriquecerse desde inventario local para que la salida sea más legible que simples strings del vendor

## Documentos relacionados

- `pfchat/SKILL.md`
- `docs/unification-2026-03-19.md`
- `pfchat/references/endpoints.md`
- `pfchat/references/output-shapes.md`
- `pfchat/references/investigation-patterns.md`
- `pfchat/references/investigation-examples.md`
