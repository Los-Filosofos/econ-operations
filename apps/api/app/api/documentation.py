"""OpenAPI guidance; examples are documentation and never seed runtime records."""

from pydantic import BaseModel, Field

MODE_DESCRIPTION = (
    "fixture: muestras sintéticas del archivo, sin llamadas a proveedores. "
    "live: lecturas actuales del sandbox sintético, habilitadas solo en el servidor. "
    "No hay fallback entre modos."
)

API_DESCRIPTION = """
API del hub ECON: **proyecto → solicitud → asignación → traslado → recepción**.
Dash y HTTP comparten servicios y reglas; este contrato describe las rutas del hub,
no todas las APIs de Prisma o Startrack.

### Empezar
1. Probar `GET /health/live` y `GET /api/v1/hub` con `mode=fixture`.
2. Revisar `sources`, `scope`, `provenance` y `operation_evidence` junto con los datos.
3. Consultar `GET /api/v1/operations` para los planes y el historial persistidos.

**Todo el caso es sintético.** `fixture` conserva muestras documentales;
`live` consulta el sandbox y permanece deshabilitado por defecto. Nunca se sustituye
una fuente fallida por fixtures. Un `200` de consulta puede describir una fuente
inaccesible: no equivale a cobertura completa ni a cero operaciones.

Las mutaciones requieren `ALLOW_LOCAL_MANAGEMENT=true`, conexión local y origen
coincidente. Envío remoto exige habilitaciones independientes del servidor.
No hay login de aplicación ni credenciales de proveedor que introducir en Swagger.
Los ejemplos no habilitan acceso ni se cargan como datos al abrir esta página.

El estado administrativo, mantenimiento, tarea, presencia GPS y recepción son
hechos diferentes. Una geocerca o tarea completada no acredita recepción.
`generated_at` indica generación de la respuesta; la vigencia depende de la
procedencia y las fechas de cada evidencia. Los filtros trabajan sobre lecturas
acotadas y no permiten inferir KPIs de toda la flota.
"""

OPENAPI_TAGS = [
    {
        "name": "Salud",
        "description": "Disponibilidad del proceso y conexión SQL; no verifican proveedores.",
    },
    {
        "name": "Consulta operativa",
        "description": "Maquinaria, solicitudes y evidencia relacionada por IDs explícitos.",
    },
    {
        "name": "Integración",
        "description": (
            "Recorrido de los datos de una solicitud: lo que entrega Prisma, cómo lo normaliza "
            "ECON, qué recibiría Startrack en POST /api/job y qué devuelve la tarea observada. "
            "Solo lectura: no crea ni modifica tareas."
        ),
    },
    {
        "name": "Traslados",
        "description": (
            "Planes locales, catálogos y seguimiento. Guardar un plan no crea una tarea. "
            "La sincronización live puede enviar tareas solo con habilitación del servidor."
        ),
    },
]


class ErrorResponse(BaseModel):
    detail: str = Field(description="Motivo público del rechazo, sin datos de credenciales.")


WORKFLOW_CONFLICT = {
    409: {
        "model": ErrorResponse,
        "description": (
            "Gestión o live deshabilitados, operación ausente, conflicto de identidad/estado, "
            "evidencia inválida o dependencia no disponible. Revisar detail; no reenviar a ciegas."
        ),
        "content": {
            "application/json": {
                "examples": {
                    "local_only": {
                        "summary": "Sesión sin permiso para gestionar",
                        "value": {
                            "detail": (
                                "La gestión requiere una sesión con permiso para esta operación."
                            )
                        },
                    },
                    "live_disabled": {
                        "summary": "Live deshabilitado",
                        "value": {
                            "detail": "Las lecturas en vivo están deshabilitadas en este servidor."
                        },
                    },
                }
            }
        },
    }
}

PLAN_EXAMPLES = {
    "local_sample": {
        "summary": "Ensayo local con la muestra proporcionada de PROY-014",
        "description": (
            "Los UUID de Prisma proceden del archivo. demo-poi y demo-user son IDs "
            "didácticos sin validación en Startrack. La fecha es una decisión del ejemplo, "
            "no una fecha de entrega inferida. No corresponde a RE-03/MOT-006/PROY-006. "
            "Ejecutar guarda un plan local; no envía tareas."
        ),
        "value": {
            "mode": "fixture",
            "mapping": {
                "request_source_id": "46d2573e-08d3-4855-971d-2fbf9564e135",
                "machinery_source_id": "66faacde-728c-4378-8b46-dbfb38254e03",
                "project_source_id": "39723f32-8bb5-4158-a415-2a3d49b0993b",
                "poi_id": "demo-poi",
                "assigned_user_ids": ["demo-user"],
                "movement_reference": "demo-swagger-fixture-001",
                "scheduled_date": "2026-09-14",
                "scheduled_time": "08:00:00",
            },
            "tracked_vehicle_id": None,
        },
    }
}
