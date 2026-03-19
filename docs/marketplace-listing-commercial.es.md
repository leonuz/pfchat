# PfChat marketplace listing — versión comercial en español

## Nombre

PfChat

## Descripción corta

Convierte pfSense + ntopng en un asistente de operaciones de seguridad para visibilidad, investigación y acciones seguras de firewall.

## Tagline

Mira qué están haciendo los hosts, detecta tráfico sospechoso y actúa de forma segura en pfSense desde una sola skill.

## Descripción larga

PfChat convierte tu firewall pfSense y la inteligencia de tráfico de ntopng en un solo flujo conversacional de operaciones de seguridad dentro de OpenClaw.

En vez de saltar entre páginas del firewall, dashboards de tráfico y llamadas manuales a APIs, PfChat te da una sola interfaz para entender qué está pasando en tu red y tomar acciones controladas cuando haga falta.

Con PfChat puedes:

- inspeccionar dispositivos conectados y tráfico en vivo
- revisar tráfico bloqueado y comportamiento del firewall
- comprobar WAN, interfaces, gateways y salud del sistema
- identificar top talkers y clientes ruidosos
- entender qué está haciendo un host ahora mismo
- revisar alertas y actividad de aplicaciones/protocolos desde ntopng
- bloquear hosts o restringir tráfico saliente de forma segura con flujos de preview / apply / rollback

PfChat combina lo mejor de ambos sistemas:

- pfSense aporta el estado autoritativo del firewall, reglas, logs, interfaces y control administrativo seguro
- ntopng aporta el contexto de tráfico que pfSense por sí sola no explica completamente, incluyendo actividad por host, top talkers, alertas y visibilidad de aplicaciones

Eso hace que PfChat sea especialmente útil para:

- operaciones de seguridad en homelab
- troubleshooting de red
- investigaciones sobre el firewall
- análisis de comportamiento de dispositivos
- contención rápida durante incidentes en vivo
- administración diaria de pfSense con mejor contexto de tráfico

PfChat está pensado para preguntas reales que un operador hace todos los días:

- ¿Qué está haciendo este cliente ahora mismo?
- ¿Por qué este dispositivo está generando tanto tráfico?
- ¿Qué bloqueó el firewall recientemente?
- ¿Está ocurriendo algo sospechoso en la red?
- ¿Debería bloquear este host o solo restringir una dependencia saliente?
- ¿Qué sabe ntopng sobre este dispositivo?

Si usas pfSense con ntopng y quieres una forma más rápida y operacional de investigar y actuar, PfChat está hecho exactamente para eso.

## Capacidades principales

- visibilidad live de pfSense para dispositivos, estados, logs, interfaces, gateways, salud y reglas
- inteligencia basada en ntopng para top talkers, alertas, comportamiento de tráfico y aplicaciones
- workflows de investigación centrados en hosts, combinando la verdad del firewall con contexto de tráfico
- administración segura del firewall con flujos draft / preview / confirm / rollback
- controles rápidos de egress por host para contención y pruebas en vivo
- soporte operativo en inglés y español

## Prompts de ejemplo

- check what devices are connected to pfSense
- what is this client doing right now?
- show me recent blocked traffic
- show ntopng top talkers
- show ntopng alerts from the last 24 hours
- what applications is this host using?
- what is my WAN address?
- block this device safely
- rollback the last PfChat firewall change
- show me anything suspicious on the firewall
- muéstrame los top talkers de ntopng
- qué está haciendo este host ahora mismo
- bloquea este equipo de forma segura
- revisa si hay algo sospechoso en mi firewall

## Por qué la gente la va a querer

- Reduce la fricción entre visibilidad y acción
- Hace que pfSense + ntopng se sientan como un solo sistema operacional
- Ayuda a responder mucho más rápido preguntas sobre comportamiento por host
- Añade workflows administrativos más seguros en vez de mutaciones crudas de firewall en un solo paso
- Sirve tanto para operación diaria como para investigación durante incidentes

## Requisitos

- pfSense con el paquete upstream `pfSense-pkg-RESTAPI` instalado y configurado
- credenciales válidas y accesibles para la API de pfSense
- una instancia alcanzable de ntopng para las capacidades de inteligencia de tráfico
- variables de entorno válidas o configuración local en `.env`

## Limitaciones / caveats

- la REST API de pfSense no viene nativa por defecto; primero hay que instalar el paquete upstream
- las capacidades apoyadas en ntopng dependen de la versión, edición y endpoints expuestos localmente
- algunas vistas de ntopng pueden degradar limpiamente cuando ciertos endpoints no están disponibles
- los cambios de firewall siguen debiendo tratarse como acciones supervisadas por el operador

## Audiencia

- operadores de homelab
- ingenieros de seguridad
- administradores de firewall
- defensores
- usuarios de OpenClaw que corren pfSense + ntopng
