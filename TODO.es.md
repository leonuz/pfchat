# TODO — PfChat

Pendientes del proyecto, organizados por prioridad.

## Alta prioridad

- [x] Cargar/configurar `RESEND_API_KEY` en el entorno para activar el envío real del resumen diario por correo
- [ ] Añadir soporte opcional para CA custom (`PFSENSE_CA_FILE`) y así validar certificados sin usar `PFSENSE_VERIFY_SSL=false`  ← pendiente solicitado, no implementar todavía
- [x] Añadir descubrimiento opcional de endpoints desde `/api/v2/schema/openapi` y cachear capacidades soportadas
- [x] Añadir cache persistente opcional del schema OpenAPI para reducir fetches repetidos
- [ ] Afinar la inferencia de dispositivos cuando ARP/DHCP no estén expuestos por la API
- [x] Añadir filtros por host/IP/puerto para reducir ruido en `connections` y `logs`
- [x] Añadir pruebas unitarias para `pfsense_client.py` y `pfchat_query.py`
- [x] Añadir pruebas de integración con respuestas mockeadas de pfSense
- [x] Documentar mejor la estructura de salida de cada comando

## Prioridad media

- [ ] Añadir un workflow documentado y automatizable de resúmenes/alertas vía Telegram sobre OpenClaw
- [ ] Descubrir más variantes reales de endpoints del paquete REST API de pfSense
- [x] Añadir modo `--once` o presets orientados a automatización
- [x] Mejorar el snapshot para resumir hallazgos de forma más compacta
- [x] Añadir ejemplos reales de investigación en `references/`
- [ ] Evaluar soporte para múltiples LAN/VLAN en inventario de dispositivos
- [x] Añadir validación más estricta del archivo `.env`

## Prioridad baja

- [ ] Soporte para exportar reportes Markdown/HTML
- [ ] Posible empaquetado adicional para distribución fuera de OpenClaw
- [ ] Enriquecimiento opcional de IPs externas con GeoIP o ASN
- [ ] Compatibilidad exploratoria con pfSense Plus y OPNsense
- [ ] Plantillas de reportes operativos y de security review
