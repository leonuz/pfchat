# TODO — PfChat

Pendientes del proyecto, organizados por prioridad.

## Alta prioridad

### Arquitectura de integración con ntopng

- [x] Refactorizar el soporte de ntopng a un diseño de dos capas: cliente de transporte/auth de bajo nivel más un adapter de normalización/agregación
- [x] Añadir detección de capacidades de ntopng que distinga REST v1/v2, alerts, timeseries y soporte de historical flows en vez de asumir una instalación uniforme
- [x] Añadir resolución compartida de identidad de host entre entradas de pfSense + ntopng (hostname, FQDN, IP, alias y host key con VLAN)
- [x] Mantener que los comandos de ntopng devuelvan JSON normalizado nativo de PfChat en vez de exponer respuestas crudas específicas del endpoint
- [x] Decidir reemplazar la ruta actual de transporte custom de ntopng por el backend ligero estilo Python API para consultas live
- [ ] Investigar si la respuesta malformada de `connect/test.lua` es un bug específico de versión de ntopng o una rareza de proxy que convenga tratar más generalmente
- [x] Convertir epochs normalizados de alertas ntopng a hora del este (ET) en resúmenes conversacionales de alto nivel por defecto
- [ ] Añadir render ET/hora local a otras superficies de resumen de ntopng como top talkers y active-host summaries cuando se muestren timestamps

- [x] Añadir acciones administrativas seguras de firewall para bloquear una IP/dispositivo usando flujo `draft -> preview -> apply -> audit`
- [x] Fortalecer rollback usando identificadores nativos de objetos pfSense cuando existan en lugar de heurísticas por descripción
- [x] Añadir validación real en un lab controlado antes de recomendar uso en producción
- [x] Cargar/configurar `RESEND_API_KEY` en el entorno para activar el envío real del resumen diario por correo
- [ ] Añadir soporte opcional para CA custom (`PFSENSE_CA_FILE`) y así validar certificados sin usar `PFSENSE_VERIFY_SSL=false`  ← pendiente solicitado, no implementar todavía
- [x] Añadir descubrimiento opcional de endpoints desde `/api/v2/schema/openapi` y cachear capacidades soportadas
- [x] Añadir cache persistente opcional del schema OpenAPI para reducir fetches repetidos
- [x] Afinar la inferencia de dispositivos cuando ARP/DHCP no estén expuestos por la API
- [x] Añadir filtros por host/IP/puerto para reducir ruido en `connections` y `logs`
- [x] Añadir pruebas unitarias para `pfsense_client.py` y `pfchat_query.py`
- [x] Añadir pruebas de integración con respuestas mockeadas de pfSense
- [x] Documentar mejor la estructura de salida de cada comando

## Prioridad media

- [ ] Añadir un workflow documentado y automatizable de resúmenes/alertas vía Telegram sobre OpenClaw
- [x] Descubrir más variantes reales de endpoints del paquete REST API de pfSense
- [x] Añadir modo `--once` o presets orientados a automatización
- [x] Mejorar el snapshot para resumir hallazgos de forma más compacta
- [x] Añadir ejemplos reales de investigación en `references/`
- [ ] Evaluar soporte para múltiples LAN/VLAN en inventario de dispositivos
- [ ] Extender el bloqueo de salida por host más allá del flujo actual single-port draft/apply/rollback (múltiples puertos, protocolos más ricos y unblock por target+puerto)
- [x] Añadir validación más estricta del archivo `.env`
- [x] Añadir soporte para top-talkers de ntopng basado en salida normalizada del adapter en vez de passthrough crudo del endpoint
- [x] Añadir soporte de alertas ntopng (globales + por host) con normalización de severidad
- [x] Añadir resúmenes de aplicaciones/protocolos de host ntopng (L7) mediante un modelo de salida estable de PfChat
- [x] Añadir parsing/normalización más rico para registros de alert-list y así resaltar hosts, severidades y familias de alertas sin exponer solo la estructura cruda de ntopng

## Prioridad baja

- [ ] Soporte para exportar reportes Markdown/HTML
- [ ] Posible empaquetado adicional para distribución fuera de OpenClaw
- [ ] Enriquecimiento opcional de IPs externas con GeoIP o ASN
- [ ] Compatibilidad exploratoria con pfSense Plus y OPNsense
- [ ] Plantillas de reportes operativos y de security review
