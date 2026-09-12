# Contexto de la conversación y estado del proyecto

Registro de lo trabajado en esta conversación hasta la preparación de la documentación para compartir en GitHub. Distingue resultados realizados, decisiones provisionales y funcionalidades pendientes. No es un informe de disponibilidad continua de los servicios ni una confirmación de cambios posteriores en GitHub.

## Necesidad planteada por el usuario

El usuario describió un grupo de construcción y logística que diseña, produce, transporta y ejecuta proyectos en El Salvador. Señaló información dispersa entre plataformas y personas, procesos diferentes entre unidades, poca trazabilidad, tareas manuales, tiempos muertos y ausencia de indicadores unificados.

Inicialmente el reto era hipotético y aún no se había entregado la documentación. El usuario pidió evaluar e inicializar un backend FastAPI con un ORM, después elegir y configurar PostgreSQL, preparar el repositorio y agregar herramientas de colaboración. Posteriormente confirmó que se ofrecería un sandbox y que el volumen esperado era alto, sin dar cifras.

Ahora se recibió el kit oficial del Hub de Operaciones: la integración es **Prisma + Startrack**. El usuario confirma su equipo como **Los Filósofos**. Según la introducción, es Equipo 6, con `RE-03`, `MOT-006 — Rodrigo Trujillo` y `PROY-006 — Proyecto Zeta`. Rodrigo se describe en la fuente como motorista asignado del sandbox. [Introducción](00-introduccion-equipo.md).

## Backend inicializado

| Componente | Estado realizado |
| --- | --- |
| Proyecto Python | Inicializado por CLI con `uv`, Python 3.13, entorno virtual y `uv.lock` |
| FastAPI | Aplicación modular, Swagger/OpenAPI, configuración y CORS |
| ORM | SQLModel, basado en SQLAlchemy y Pydantic |
| Migraciones | Entorno de Alembic configurado; sin tablas ni revisiones de dominio todavía |
| PostgreSQL | Versión observada 18.6 en imagen Docker `postgres:18` |
| Persistencia local | Volumen `econ-backend_postgres18_data`, montaje `/var/lib/postgresql` |
| Puerto de desarrollo | `127.0.0.1:54329` hacia el puerto 5432 del contenedor |
| Configuración | `DATABASE_URL` requerida en `.env`; no se incluye aquí la contraseña |
| Rutas disponibles | `/health/live`, `/health/ready`, `/docs`, `/openapi.json` |
| Comprobaciones realizadas | Dos pruebas automatizadas, Ruff, conexión real a PostgreSQL, comprobación de Alembic y respuestas HTTP correctas |

SQLite se utilizó en el primer arranque y se mantiene para las pruebas temporales. PostgreSQL quedó como base de desarrollo principal. El volumen anterior de prueba con PostgreSQL 17 se conservó aparte; no se realizó una migración de datos de negocio.

Las comprobaciones demostraron que la base y el scaffold arrancan. **No demostraron integración con Prisma/Startrack, rendimiento a gran escala ni preparación para producción.** Los tests actuales pertenecen al scaffold y son distintos de los fragmentos de pruebas de la propuesta adjunta.

Las versiones exactas de las dependencias se consultan en `uv.lock`; las instrucciones operativas vigentes están en el [README del proyecto](../../README.md).

## Decisión sobre PostgreSQL

La elección inicial fue PostgreSQL para relaciones entre datos operativos, persistencia e historial. Docker es el mecanismo de ejecución local, no una alternativa a PostgreSQL. Se sugirió evaluar una instancia administrada para producción según infraestructura y presupuesto.

Para dimensionar se necesitan datos reales de volumen, crecimiento, concurrencia, frecuencia de sincronización, retención y disponibilidad. No se configuraron particiones ni componentes adicionales por suposición. [Decisión de base de datos](../database.md).

## Git y GitHub

| Elemento | Último estado verificado durante la conversación |
| --- | --- |
| Autor Git local solicitado | `wkatir` |
| Correo Git solicitado por el usuario | `wilmerhenrysalazarmartinez@gmail.com` |
| Repositorio actual | `https://github.com/Los-Filosofos/econ-protocol`; la dirección inicial `wkatir/econ-backend` redirige a este repositorio |
| Visibilidad | Privado |
| Rama | `main` |
| Commit inicial subido | `b829afe` — scaffold FastAPI/PostgreSQL/Alembic |
| Colaborador | Invitación enviada a `marchelo23` con permiso de escritura; no se verificó aquí si ya la aceptó |
| CodeRabbit | `.coderabbit.yaml` validado contra el esquema oficial y subido en `b1d15f7` |
| Configuración de CodeRabbit | Español, perfil `chill`, revisión automática activada en configuración y borradores excluidos |
| Instalación de la app | Pendiente de confirmar; no debe presentarse como activada solo por existir el YAML |

La CLI quedó autenticada como `wkatir` y permitió crear/subir el repositorio. La sesión del navegador utilizada para revisar aplicaciones correspondía a otra cuenta; por eso no se completó la instalación de CodeRabbit en el repositorio del usuario.

## Propuesta aportada por el usuario

El usuario adjuntó una propuesta de protocolo por eventos con dos payloads, un ejemplo FastAPI en memoria, dos pruebas y una ruta de implementación de 24 horas. Su intención es relacionar el estado administrativo de Prisma con el logístico de Startrack.

La propuesta se preserva en [07-propuesta-original.md](07-propuesta-original.md). Sus endpoints, nombres de eventos y equivalencias son propuestos; no se confirmaron contra contratos reales. El análisis separado está en [08-analisis-propuesta.md](08-analisis-propuesta.md). No se ejecutaron esos fragmentos ni se incorporaron al backend durante esta conversión.

## Trabajo documental realizado en esta etapa

- Se extrajeron y convirtieron los 11 archivos del ZIP.
- Se conservaron texto, tablas, comentarios editoriales, celdas y recursos visuales con procedencia.
- Se revisaron visualmente diagramas, organigramas y capturas del manual para trasladar el contenido relevante a texto Markdown.
- Se mantuvieron intactos los ejemplos originales de otros equipos y se aclaró la asignación de Los Filósofos.
- Se generaron índice, inventario, contexto para IA y análisis de la propuesta.
- Los originales no se modificaron. No se consultaron las plataformas ni se usaron los accesos del kit.

Durante la conversión inicial estos archivos permanecieron locales. Después, el usuario pidió hacer commit y compartirlos con el equipo. La versión de `docs/onedrive` se incluye en Git y omite las 25 contraseñas del documento de accesos. Los originales completos y la conversión previa a esa omisión se conservan en `.context-work/`, excluida de Git. Se verificó que el repositorio actual es privado y se identifica como `Los-Filosofos/econ-protocol`.

## Pendientes reales

Obtener acceso técnico confirmado y muestras representativas; definir correspondencias, cardinalidades y estados; elaborar las matrices finales; diseñar e implementar ingestión, consulta y panel; validar reglas, roles y datos faltantes; medir capacidad; completar y verificar CodeRabbit cuando se solicite continuar esa instalación.

El pedido actual es documental: convertir y analizar el contexto, hacer commit y compartirlo en el repositorio. No autoriza por sí solo a ejecutar las instrucciones incluidas en el kit o implementar todas las funcionalidades propuestas.
