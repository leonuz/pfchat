# CHANGELOG — PfChat

Todos los cambios relevantes de este proyecto se documentan aquí.

## [0.1.1] - 2026-03-13

### Añadido

- Convención de documentos orientada a GitHub: `README.md`, `TODO.md` y `CHANGELOG.md` quedan como originales en inglés, y las variantes en español pasan a `README.es.md`, `TODO.es.md` y `CHANGELOG.es.md`
- Documento `TELEGRAM.md` con el flujo recomendado para usar PfChat a través de OpenClaw en Telegram
- Documentación del caso de uso de resumen diario por email mediante OpenClaw + Resend
- Script `pfchat/scripts/send_daily_summary.py` para generar y enviar el resumen diario por correo
- Soporte operativo para variables globales heredadas por OpenClaw Gateway vía `EnvironmentFile`
- Preferencia de nombres de dispositivos sobre IPs en reportes, usando inventario local y reverse lookup como fallback
- Integración de hallazgos upstream del proyecto pfrest y del schema OpenAPI real expuesto por la instancia local
- Descubrimiento automático de capacidades soportadas desde `/api/v2/schema/openapi`
- Soporte inicial para filtros de consulta en `connections` y `rules`
- Filtros prácticos para `connections` y `logs` (`--host`, `--port`, `--interface`, `--contains`, `--action`)
- `references/output-shapes.md` documentando la forma del JSON devuelto por cada comando
- `references/investigation-examples.md` con workflows concretos para WAN, tráfico bloqueado, top talkers y revisión de reglas
- Cache persistente local del OpenAPI schema para reducir fetches repetidos de descubrimiento
- Suite inicial de `unittest` para `pfsense_client.py` y `pfchat_query.py`
- Validación más estricta del `.env` para host, API key y settings booleanos de SSL
- Sección compacta `summary` dentro del snapshot para WAN, gateways, top devices, top flows, conteo de bloqueos y highlights
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
- CLI auxiliar `pfchat/scripts/pfchat_query.py`
- Soporte para consultas en vivo de:
  - dispositivos conectados
  - conexiones activas
  - logs recientes del firewall
  - interfaces
  - salud del sistema y gateways
  - reglas del firewall
  - snapshot combinado
- Referencias de endpoints y patrones de investigación en `pfchat/references/`
- Artefacto empaquetado `dist/pfchat.skill`
- Estructura de repositorio lista para GitHub
- Documentación bilingüe inicial

### Cambiado

- El proyecto original fue adaptado para OpenClaw
- El workflow quedó agnóstico al modelo y ya no depende de un SDK de proveedor específico para el flujo principal

### Notas

- El foco de esta versión es el workflow live/API
- El análisis offline de logs no está incluido en esta skill
