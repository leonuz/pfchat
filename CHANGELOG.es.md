# CHANGELOG — PfChat

Todos los cambios relevantes de este proyecto se documentan aquí.

## [Unreleased]

## [0.3.0] - 2026-03-17

### Añadido

- Integración inicial con ntopng usando variables de entorno locales del proyecto para `NTOPNG_BASE_URL`, `NTOPNG_USERNAME`, `NTOPNG_PASSWORD`, `NTOPNG_AUTH_TOKEN` y `NTOPNG_VERIFY_SSL`.
- Primera tanda de comandos ntopng: `ntop-capabilities`, `ntop-hosts` y `ntop-host`.
- `pfchat/scripts/ntopng_client.py` reutilizable más cobertura unitaria para la capa inicial de transporte de ntopng.
- Documentación de formas de salida y ejemplos de invocación para comandos soportados por ntopng.
- Backend ligero de ntopng estilo Python API en `pfchat/scripts/ntopng_pyapi_backend.py`, siguiendo el modelo oficial útil (`Ntopng` / `Interface` / `Historical`) pero manteniendo control sobre SSL y parseo de respuestas.
- Conexión de los comandos ntopng (`ntop-capabilities`, `ntop-hosts`, `ntop-host`, `ntop-top-talkers`, `ntop-alerts`, `ntop-host-apps`) al backend nuevo a través del adapter.
- Degradación limpia para features de ntopng no disponibles o lentas en esta instancia: top talkers cae a ranking por bytes de active hosts y `ntop-alerts` prefiere endpoints `alert/list` sobre el resumen lento `alert/top`.
- Registros de alertas flow/host normalizados y bloque `summary` de alertas para que los resultados de ntopng sean más útiles conversacionalmente.
- Render de hora del este (ET) para timestamps de alertas y resúmenes de host en ntopng.
- Supresión de warnings ruidosos de urllib3 cuando la verificación SSL de ntopng se deshabilita de forma intencional.
- Mejoras en el filtrado del resumen diario usando detección real de IP privada en vez de un prefijo amplio `172.*`.
- Soporte `delete_firewall_state()` en `pfsense_client.py` y cobertura de tests para detectar capacidad de borrado de estados.

### Cambiado

- El manejo de comandos ntopng ahora pasa por una capa adapter que normaliza la salida de hosts y la resolución compartida de identidad en vez de devolver payloads crudos específicos de cada endpoint.
- El transporte ntopng ahora falla de forma limpia cuando el appliance devuelve la página HTML de login, guiando al operador hacia auth HTTP API o token en vez de un traceback de JSON parse.

### Validado

- Verificado que el paquete oficial de Python API de ntopng puede instalarse e importarse en un virtualenv local de este host.
- Verificado que el self-test de la Python API oficial sigue fallando contra esta instancia de ntopng porque `connect/test.lua` devuelve una respuesta HTTP completa embebida dentro del body, rompiendo el parseo JSON normal.
- Verificado que la auth directa con `curl` funciona y que el backend ligero puede recuperar datos live de ntopng (`connect/test`, interfaces, hosts activos, interface stats, L7 stats, alert lists, host apps y host summaries) saneando el body malformado de `connect/test.lua` antes de parsear JSON.

## [0.2.0] - 2026-03-14

### Añadido

- Acciones administrativas seguras de firewall para bloquear una IP/dispositivo mediante flujo `draft -> preview -> apply -> audit`
- Persistencia local de drafts, auditoría y `apply-draft --confirm` con guardrails
- Rollback usando IDs de objetos pfSense devueltos por llamadas reales de creación
- Operaciones de objetos gestionados con `pfchat-managed-list`, `pfchat-managed-cleanup`, `unblock-ip` y `unblock-device`
- Bloqueo de salida específico por host para puertos `tcp/udp` mediante `block-egress-port`
- Bloqueo de salida ICMP por host mediante `block-egress-proto --proto icmp`
- Cobertura de integración mockeada para el ciclo administrativo de apply/rollback

### Validado

- Validación real en pfSense para block/apply/rollback de host completo sobre `sniperhack.uzc` (`192.168.0.81`)
- Validación real en pfSense para bloqueo de salida `tcp/80` por host sobre `sniperhack.uzc`
- Validación real en pfSense para bloqueo de salida ICMP por host sobre `sniperhack.uzc`

## [0.1.1] - 2026-03-13

### Añadido

- Documento `TELEGRAM.md` con el flujo recomendado para usar PfChat a través de OpenClaw en Telegram
- Documentación del caso de uso de resumen diario por email mediante OpenClaw + Resend
- Script `pfchat/scripts/send_daily_summary.py` para generar y enviar el resumen diario por correo
- Soporte operativo para variables globales heredadas por OpenClaw Gateway vía `EnvironmentFile`
- Preferencia de nombres de dispositivos sobre IPs en reportes, usando inventario local y reverse lookup como fallback
- Integración de hallazgos upstream del proyecto pfrest y del schema OpenAPI real expuesto por la instancia local
- Descubrimiento automático de capacidades soportadas desde `/api/v2/schema/openapi`
- Soporte inicial para filtros de consulta en `connections` y `rules`
- Cobertura explícita en la skill para preguntas sobre dirección WAN / IP pública del firewall, también en español
- Fallback de configuración al archivo `pfchat/.env` basado en la ruta del script, para invocaciones desde otros canales/contextos
- Compatibilidad real con una instalación de pfSense validada en este entorno
- Fallback de `health` hacia `status/system` cuando `system/stats` no existe
- Modo degradado para `devices` cuando ARP/DHCP no están expuestos, infiriendo hosts internos desde `firewall/states`
- Documentación bilingüe actualizada con hallazgos de compatibilidad reales

### Corregido

- `total_active_connections` ahora refleja la cantidad real devuelta
- El fallback de logs ya no oculta errores reales de TLS, auth o conectividad detrás de un falso "endpoint not found"
- El snapshot ahora devuelve conteos consistentes para conexiones, logs y reglas

## [0.1.0] - 2026-03-13

### Añadido

- Primera versión de la skill `PfChat` para OpenClaw
- Cliente reutilizable de pfSense REST API en `pfchat/scripts/pfsense_client.py`
- CLI auxiliar en `pfchat/scripts/pfchat_query.py`
- Soporte live para dispositivos conectados, conexiones activas, logs recientes del firewall, interfaces, salud del sistema y gateways, reglas del firewall y snapshots combinados
- Referencias de endpoints y patrones de investigación en `pfchat/references/`
- Artefacto empaquetado `dist/pfchat.skill`
- Estructura de repositorio lista para GitHub
- Documentación bilingüe inicial
