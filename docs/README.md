# Documentación de ECON

La implementación actual se organiza como monorepo: `apps/web` y `apps/api`. Comenzar por [desarrollo local](desarrollo.md), [decisión de plataforma web](adr/0001-web-platform.md) y [preparación para Cloudflare](deploy-cloudflare.md). La [revisión de contexto del 12/09/2026](revision-contexto.md) registra la lectura completa del kit, el cotejo del ZIP y los límites actuales de acceso. Los documentos históricos siguientes conservan sus afirmaciones con la fecha y el alcance de cada revisión.

El [modelo operativo y sus matrices iniciales](modelo-operativo.md) documenta el contrato implementado, inventario de campos, mapeo por fuente, responsabilidades propuestas y señales medibles. Distingue las relaciones locales de demostración de las correspondencias externas todavía sin validar.

Para elegir dónde ejecutar FastAPI y PostgreSQL, consultar la [comparación de proveedores y configuración del backend](despliegue-backend.md). La web se prepara para Cloudflare y la API conserva su contenedor independiente.

Para entender la operación y recorrer las plataformas, comenzar por la [guía del problema y navegación](guia-problema-y-navegacion.md). Después consultar [qué revisar ahora, KPIs y referencias ISO](kpis-y-referencias-iso.md): decisiones pendientes, indicadores ligados a datos disponibles y normas como referencia de diseño.

El contexto completo del reto entregado por el usuario está en [onedrive/README.md](onedrive/README.md). Para incorporar rápidamente los hechos confirmados, comenzar por [CONTEXTO-IA.md](onedrive/CONTEXTO-IA.md).

La carpeta `onedrive` contiene conversiones de los documentos originales, el diccionario completo, transcripciones visuales, la propuesta del usuario y su análisis. Se comparte en el repositorio privado del equipo con las contraseñas del sandbox omitidas. Los originales completos y los intermediarios permanecen locales en `.context-work/`, excluida de Git.

La [exploración de las integraciones reales](integraciones-reales.md) registra el acceso por Chrome a Nexus y Startrack, las consultas HTTP probadas, autenticación, límites y la arquitectura recomendada. Distingue observaciones del entorno de contratos documentados y puntos pendientes.

Los documentos anteriores al kit siguen disponibles:

- [Evaluación inicial de FastAPI](architecture.md).
- [Elección y configuración de PostgreSQL](database.md).
- [Guía general del repositorio](../README.md) y [detalle de la API](../apps/api/README.md).

Las suposiciones previas sobre un reto todavía desconocido deben contrastarse con el kit recibido. El [contexto de la conversación](onedrive/09-contexto-conversacion.md) distingue lo implementado, lo propuesto y lo que falta verificar.
