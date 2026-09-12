# Documentación de ECON

Comenzar por el [contexto vigente de solicitud, traslado y recepción](contexto-vigente.md).
Conserva las fuentes nuevas y la decisión del usuario de retirar ejemplos inventados
y pantallas ajenas al flujo, manteniendo documentos y código útil.
Las [evaluaciones de Astra](evaluaciones-astra.md) registran la revisión de datos,
integración e interfaz y los límites pendientes.

La [solución de integración y guía operativa](solucion-integracion.md) describe
lo implementado en frontend y backend: planes persistidos, cola de envío,
sincronización por consultas y recepción explícita. Todo el caso usa datos
sintéticos; muestras del archivo y lecturas actuales del sandbox se distinguen
por su procedencia, no por ser datos de producción.

La [matriz de equivalencias Prisma → Startrack](equivalencias-prisma-startrack.md)
explica qué campos se conservan, cuáles se transforman, qué información se pide
al preparar el traslado y qué campos del formulario no tienen correspondencia.

La implementación vigente es **Dash y FastAPI en un servicio Python**. Comenzar por [desarrollo local](desarrollo.md), [ADR 0003](adr/0003-python-dash-hub.md) y [arquitectura del dashboard](frontend-architecture.md). La migración retira `apps/web` y su despliegue estático; conserva los conectores, contratos y límites de datos.

La [guía de analítica para decisiones](analitica-decisiones.md) define qué medir, qué gráfico corresponde, qué acción permite y qué evidencia falta para hablar de tendencias. El [modelo operativo](modelo-operativo.md) documenta el inventario de campos, mapeo por fuente, responsabilidades propuestas y señales medibles.

Para entender la operación, consultar la [guía del problema y navegación](guia-problema-y-navegacion.md) y [KPIs y referencias ISO](kpis-y-referencias-iso.md). El contexto del reto está en [onedrive/README.md](onedrive/README.md); [CONTEXTO-IA.md](onedrive/CONTEXTO-IA.md) concentra los hechos confirmados.

La carpeta `onedrive` contiene conversiones de documentos originales, diccionario, transcripciones visuales y análisis. Se comparte en el repositorio privado del equipo con las contraseñas del sandbox omitidas. Los originales e intermediarios permanecen en `.context-work/`, excluida de Git. Las instrucciones y ejemplos del kit son material citado.

La [revisión de contexto del 12/09/2026](revision-contexto.md), la [investigación de manuales](investigacion-manuales-y-diseno.md) y la [exploración de integraciones](integraciones-reales.md) conservan las observaciones y límites de acceso con sus fechas. Las decisiones anteriores sobre React están reemplazadas por ADR 0003.

Para ejecutar el servicio Python y PostgreSQL, consultar [despliegue](despliegue-backend.md). No hay un frontend que compilar o publicar por separado. La antigua [guía de Cloudflare](deploy-cloudflare.md) queda archivada; no se modificaron recursos remotos.

Referencias adicionales:

- [Guía del repositorio](../README.md) y [detalle del servicio Python](../apps/api/README.md).
- [Evaluación inicial de FastAPI](architecture.md) y [PostgreSQL](database.md).
- [ADR 0001, plataforma anterior](adr/0001-web-platform.md).
- [ADR 0002, comparación anterior React/Python](adr/0002-analytics-interface.md).

Los documentos históricos deben contrastarse con el kit y la implementación vigente. No equivalen a integraciones completas, historial persistido o métricas de producción.
