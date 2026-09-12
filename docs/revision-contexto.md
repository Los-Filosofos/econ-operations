# Revisión de contexto para iniciar el frontend y ampliar la API

> Continuar desde [contexto-vigente.md](contexto-vigente.md): incorpora los
> contratos nuevos, las capturas posteriores y la retirada de ejemplos inventados.

> Registro anterior a la migración solicitada a Dash. La arquitectura vigente
> está en [ADR 0003](adr/0003-python-dash-hub.md). Las observaciones de negocio
> y los límites de integración se conservan con su fecha original.

Fecha: **12 de septiembre de 2026**. Esta revisión registra la lectura del material entregado, el cotejo del ZIP y las decisiones de implementación de esta etapa. Las conversiones originales de `docs/onedrive` se conservan sin modificaciones.

## Cobertura y procedencia

Se revisaron los **21 Markdown** de `docs/onedrive`, incluidas las tablas, transcripciones visuales, ejemplos de código y los registros de las **338 celdas** del diccionario. También se leyeron el índice de documentación, la guía de navegación, la exploración de integraciones, las propuestas de KPIs/ISO y las decisiones anteriores de API y base de datos.

| Material revisado | Qué determina para el producto |
| --- | --- |
| Introducción, confidencialidad y brief | Asignación del equipo, procedencia del material, alcance y requisitos RF/RNF |
| Diagramas AS-IS, TO-BE y organigramas | Flujo de solicitudes, asignación, mantenimiento y responsabilidades por validar |
| Tres casos de uso | Consulta integrada, estados que describen objetos diferentes y riesgo por mantenimiento |
| Accesos y extracto del manual Nexus | Entornos entregados y significado de campos/pantallas; el extracto tiene 9 páginas, no las 44 del manual |
| Cuatro hojas del diccionario | 51 definiciones, ejemplos y problemas de formato; no constituye un contrato API ni una matriz de equivalencias |
| Propuesta, análisis y contexto de conversación | Separación entre código propuesto, hechos comprobados y decisiones posteriores |
| README, CONTEXTO-IA e INVENTARIO de OneDrive | Navegación, resumen y correspondencia de fuentes |

Se volvió a abrir `C:/Users/wilme/Downloads/OneDrive_1_9-12-2026.zip` en lectura. Sus **9,748,744 bytes**, sus **11 archivos** —7 DOCX, 1 XLSX, 1 PDF y 2 PNG—, nombres, tamaños y las once huellas individuales coinciden con [INVENTARIO.md](onedrive/INVENTARIO.md). El SHA-256 del archivo es `16518658282244a0d4f4eea3fafc354e78e9a29cf88da516975d237c3bc17924`.

Este cotejo acredita que el inventario corresponde a ese ZIP. La revisión actual utiliza las transcripciones ya preservadas; no repitió la conversión ni una auditoría visual de cada imagen. La ubicación bajo OneDrive no demuestra sincronización remota actual. Los originales y credenciales completas permanecen locales en `.context-work/`, excluida de Git; la copia compartida omite las contraseñas.

## Estado de acceso, con fecha

| Fuente | Evidencia anterior del 12/09 | Observación en esta nueva revisión | Límite vigente |
| --- | --- | --- | --- |
| Nexus / Prisma de MAIC | Login y lecturas HTTP autenticadas de equipos, solicitudes y operadores | La pestaña existente mostró login; después el nuevo conector confirmó login y dos lecturas HTTP pequeñas a las **19:05:50 UTC** | La prueba es una ventana acotada, no una sincronización completa; falta confirmar el contrato soportado |
| Startrack | Acceso web correcto; API pública requiere Basic; detalle de usuario propio devolvió `403` | La pestaña existente sigue autenticada y muestra navegación de la plataforma | No se obtuvo ni validó una API key en esta revisión |

La comprobación actual fue de lectura. No se regeneraron claves, no se repitió la vía rechazada por `403` y no se crearon ni modificaron registros operativos. La prueba histórica detallada continúa en [integraciones-reales.md](integraciones-reales.md). El formulario de login observado al inicio no demostraba que las credenciales fueran inválidas ni explicaba por qué faltaba una sesión de navegador.

**Nueva prueba del conector implementado:** el 12/09/2026 a las `19:05:50Z`, la cuenta asignada inició sesión mediante cookie. `GET /api/maquinaria/equipos?page=1&limit=1` devolvió un registro y total 15; `GET /api/maquinaria/requests?page=1&limit=1` devolvió un registro y total 2. La cobertura quedó expresamente parcial. La muestra mostró que `clave` puede ser `null` mientras `no_activo` contiene texto; el contrato conserva ahora `code` y `asset_number` por separado. Las credenciales se utilizaron solo en memoria para esta prueba, y la API de desarrollo conserva las lecturas reales deshabilitadas por defecto.

Nexus tiene lecturas comprobadas mediante cookie del backend web, sin contrato público de integración confirmado. Startrack publica una API separada que usa **API key del usuario y contraseña del sistema** mediante Basic. Poder navegar Startrack no basta para afirmar que esa API está conectada. El siguiente insumo externo sigue siendo una clave habilitada para la cuenta autorizada. [Evidencia y documentación consultada](integraciones-reales.md#startrack-api-oficial-y-sesión-web).

## Reglas de negocio preservadas

La asignación de Los Filósofos es **RE-03 / MOT-006 / PROY-006**. Los códigos **CF-03 / MOT-014** pertenecen al walkthrough. No se ha confirmado una cadena completa de solicitud, asignación y traslado para el equipo; la interfaz debe hacer visible esa ausencia.

| Evidencia | Regla de implementación |
| --- | --- |
| Aprobar una solicitud con unidad asignada cambia el inventario a Ocupada | Mostrar el estado administrativo separado de la ubicación y del estado del traslado |
| Ocupada y Completada describen objetos distintos | Explicar su compatibilidad semántica sin declarar verificada toda la operación |
| El GPS puede corresponder al vehículo transportador | No identificar automáticamente vehículo y maquinaria por nombre |
| `EQ142` se repite en capturas del manual | Conservar IDs de origen; no asumir unicidad global de `clave` |
| `Obsoletas`, `Mant. correctivo` y `Obsoleta (mantenimiento correctivo)` difieren entre fuentes | Mantener valores originales y la ambigüedad; confirmar el catálogo con Mantenimiento |
| El diccionario contiene coordenadas enteras sin escala documentada | No convertirlas en posición geográfica por una división supuesta |
| IDR de una tarea coincidió con una solicitud, pero el destino difería y la tarea estaba cancelada | Tratarlo como candidato, sin validar la relación por coincidencia de un solo campo |
| Datos sin fecha, relaciones faltantes o consultas incompletas | Mostrar ausencia de evidencia; no representarla como cero riesgo o información actual |

El diccionario conserva además tipos declarados que difieren del tipo físico de las celdas, un tipo de título malformado y una definición de servicio duplicada. Sus ejemplos no deben convertirse automáticamente en esquemas de los proveedores. [Observaciones detalladas](onedrive/06-diccionario-de-datos/README.md).

## Decisiones vigentes de esta etapa

Se adopta [React + Vite con TanStack Router/Query y shadcn `b0`](adr/0001-web-platform.md), manteniendo FastAPI separado. El monorepo organiza frontend y backend en `apps/web` y `apps/api`. El proyecto Compose y su volumen PostgreSQL se conservan al mover el código.

**No se implementa autenticación de usuarios de la aplicación**, según el alcance actual del usuario. La asignación funcional de responsabilidades continúa siendo necesaria para interpretar datos y atender alertas; no se convierte en pantallas de login o permisos ficticios. Las recomendaciones históricas de acceso por rol no describen funcionalidad presente.

La demostración utiliza casos locales identificados como `fixture`. Las lecturas `live` requieren habilitación expresa del backend y credenciales del proveedor; nunca se sustituyen por fixtures ante un fallo. La publicación del panel sin login debe mantener datos sintéticos. Un despliegue que habilite lecturas de información privada necesita un perímetro de acceso efectivo, incluido el origen API. CORS no impide que un cliente directo consulte una API pública.

## Requisitos y trabajo que permanece abierto

El [modelo operativo inicial](modelo-operativo.md) registra el inventario del contrato, mapeos implementados y ausentes, matriz funcional propuesta y reglas medibles. Es un punto de partida revisable, sin aprobación de los responsables de ECON ni cobertura de todos los campos del kit.

| Requisito del brief | Evidencia que debe conservarse o completarse |
| --- | --- |
| RF-01: campos nuevos | Contrato del hub e inventario con nombre, tipo, ejemplo, significado y procedencia de cada derivación |
| RF-02: mapeo | Matriz completa por objeto, transformación, cardinalidad, evidencia y campos sin equivalente; los tipos del frontend no reemplazan esa matriz |
| RF-03: responsabilidades | Matriz de Mantenimiento, Logística y Equipos, y Técnica de Proyectos; validar quién aprueba, revisa y recibe información |
| RF-04: consulta unificada | Panel navegable y seleccionable; distinguir datos de demostración, lectura parcial y vínculos faltantes |
| RF-05: diferencias de estado | Explicar el objeto descrito por cada estado y la evidencia que sostiene una alerta |
| RF-06: indicador | Fórmula, población, corte, cobertura y limitaciones; ver [KPIs](kpis-y-referencias-iso.md) |

El panel inicial y un conector de lectura no constituyen sincronización continua, historial persistente, conciliación validada de todas las entidades, ni prueba de capacidad productiva. Faltan la API key de Startrack, el contrato soportado de Nexus, las correspondencias del caso propio, recepción física/plazos acordados, catálogos de mantenimiento y cifras de carga. No hay metas ISO ni certificaciones de ECON confirmadas por estos documentos.

Los manuales y contratos históricos siguen accesibles desde el [índice](README.md). Para ejecutar la implementación actual usar [desarrollo](desarrollo.md); para preparar la publicación web usar [Cloudflare](deploy-cloudflare.md). Esta etapa prepara archivos y verificaciones locales de despliegue, sin publicar servicios en la cuenta del usuario.
