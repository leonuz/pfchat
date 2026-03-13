# PfChat

PfChat es una skill de OpenClaw para consultar y analizar un firewall pfSense en tiempo real a través de la REST API de pfSense.

Es agnóstica al modelo: la skill obtiene datos vivos desde pfSense y deja el análisis al agente actual de OpenClaw, sin amarrarse a un proveedor específico de LLM.

## Qué hace

- Consulta dispositivos conectados usando ARP/DHCP cuando la API los expone
- Si ARP/DHCP no existen en esa instalación, infiere hosts internos activos desde `firewall/states`
- Inspecciona estados activos del firewall y conexiones en vivo
- Revisa actividad reciente del firewall
- Verifica estado de interfaces, gateways y sistema
- Revisa reglas del firewall
- Genera un snapshot general para triage de seguridad

## Estructura del repositorio

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

## Requisitos

- OpenClaw
- Acceso a una instancia de pfSense con el paquete REST API habilitado
- Una API key de pfSense
- Python 3.10+

## Configuración

Crea un archivo local `.env` a partir de `.env.example`:

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

## Uso como skill de OpenClaw

Coloca la carpeta `pfchat/` donde vivan tus skills de OpenClaw o instala el artefacto empaquetado `dist/pfchat.skill`.

La skill está pensada para activarse con peticiones como:

- "revisa qué dispositivos están conectados al pfSense"
- "mira si hay algo sospechoso en mi firewall"
- "qué está haciendo iphoneLeo ahora mismo"
- "revisa tráfico bloqueado reciente"
- "verifica salud WAN y gateways"
- "cuál es mi dirección WAN"
- "cuál es mi IP pública del firewall"
- "enséñame las reglas de firewall relacionadas con este flujo"

## Uso directo del CLI auxiliar

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

## Compatibilidad real observada

En la validación contra una instalación real de pfSense en este entorno:

- `firewall/states` respondió correctamente
- endpoints de logs del firewall respondieron mediante fallback
- `firewall/rules` respondió correctamente
- `status/system`, `status/interfaces` y `status/gateways` funcionaron como base del bundle de health
- `status/arp` y leases DHCP no estaban expuestos; por eso el inventario de dispositivos cae a un modo degradado basado en estados activos

Esto significa que PfChat ya tolera variaciones reales del paquete REST API en lugar de depender de una única ruta teórica.

## Objetivos de diseño

- Mantener el workflow nativo de OpenClaw
- Mantener reutilizable el cliente de pfSense
- Evitar lock-in con proveedores
- Preferir fetches JSON limpios y razonamiento del agente
- Tolerar variaciones de endpoints entre versiones del paquete REST API de pfSense

## Uso desde Telegram

Si OpenClaw ya está conectado a Telegram, no necesitas un bot separado dentro de PfChat. Puedes hablarle a OpenClaw desde Telegram y dejar que use PfChat detrás para consultar pfSense.

Consulta `TELEGRAM.md` para prompts sugeridos, flujo recomendado y base de alertas/resúmenes.

## Resumen diario por email

PfChat también puede usarse para generar un resumen diario del firewall y enviarlo por correo cuando OpenClaw tenga configurado Resend.

Caso recomendado:
- resumen diario a las 9:00 AM hora local
- snapshot compacto
- dispositivos más activos
- tráfico bloqueado relevante
- estado de gateway/sistema

Script local incluido:
- `pfchat/scripts/send_daily_summary.py`

En este host, la forma correcta de que cron jobs y sesiones aisladas hereden variables globales es cargarlas desde el servicio `openclaw-gateway.service` mediante `EnvironmentFile`.

Los reportes de PfChat deben preferir nombres de dispositivos tomados del inventario local (`TOOLS.md`). Si no existe mapping local, pueden usar reverse lookup y dejar la IP como respaldo.

## Estado actual

PfChat ya cubre el workflow de consulta en vivo por API. El foco actual es robustez, compatibilidad entre versiones y mejor experiencia operativa.

Consulta `TODO.md`, `CHANGELOG.md` y `TELEGRAM.md` para ver pendientes, cambios y uso por canal.

## Licencia

MIT
