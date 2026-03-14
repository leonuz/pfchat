# ROADMAP — PfChat

Plan de trabajo hacia las próximas releases relevantes de PfChat.

## Próximo tramo

### Acciones administrativas seguras sobre el firewall

Conjunto de features planeado:
- bloquear una dirección IP
- bloquear un dispositivo conocido
- eventualmente soportar bloqueo de un puerto o servicio expuesto en WAN

Modelo de seguridad:
- draft primero
- preview antes de aplicar
- paso explícito de apply
- auditoría de quién pidió el cambio y qué se envió
- preferir patrones reversibles con alias/regla sobre ediciones directas opacas
- no hacer writes ciegos cuando el schema vivo no confirme soporte de endpoints

Despliegue propuesto:
1. discovery schema-aware de endpoints de escritura del firewall  ✅
2. modelo local de draft para acciones de bloqueo propuestas  ✅
3. preview con target resuelto, interfaz, dirección, plan de regla/alias e impacto esperado  ✅
4. flujo explícito de apply  ✅
5. auditoría y rollback básico  ✅
6. integration tests mockeados para flujos administrativos  ✅

Estado actual:
- implementado para flujos de bloqueo de IP/dispositivo
- usa drafts guardados, confirmación explícita, auditoría, idempotencia en apply y base de rollback
- todavía necesita rollback más fuerte basado en identificadores nativos de objetos pfSense y validación real controlada antes de dar confianza de producción

Scope inicial:
- `block-ip --draft <ip>`
- `block-device --draft <nombre|ip>`
- primero solo preview, luego apply controlado

## Mediano plazo

- workflow de resúmenes y alertas por Telegram sobre OpenClaw
- mejor soporte para múltiples segmentos LAN/VLAN en el inventario
- compatibilidad más amplia con variantes reales de rutas del REST API de pfSense

## Largo plazo

- exportación de reportes Markdown/HTML
- enriquecimiento opcional de IP externa con GeoIP/ASN
- compatibilidad exploratoria con pfSense Plus / OPNsense
- templates para reportes operativos/de seguridad
