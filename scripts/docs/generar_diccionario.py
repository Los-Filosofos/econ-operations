"""Generate the ECON model dictionary without settings, database or provider access."""

from __future__ import annotations

import argparse
import ast
import hashlib
import importlib
import inspect
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
API = ROOT / "apps" / "api"
sys.path.insert(0, str(API))

from app.integrations.fixtures import fixture_records
from app.integrations.startrack import Identifier, StartrackTaskDraft
from app.models.hub import DataMode
from app.services.transfers import TransferMapping, TransferPreparation
from pydantic import BaseModel, ConfigDict, Field

OUTPUT = ROOT / "docs" / "diccionario-modelo-econ.md"
MODULES = ("app.models.hub", "app.models.operations", "app.models.workflow")
TECH_TIME = "2000-01-01T00:00:00Z"
PRISMA_FIELDS = {
    "EquipmentRecord": {
        "id": "id + prefijo ECON",
        "code": "clave",
        "asset_number": "no_activo",
        "name": "nombre",
        "company": "empresa",
        "equipment_class": "clase_equipo",
        "project_id": "project_id",
        "project_name": "project_name",
        "machinery_status": "estado",
        "maintenance_failure_id": "active_failure_id",
        "maintenance_status": "active_failure_status",
        "maintenance_is_stopped": "active_failure_is_paro",
        "created_at": "created_at",
        "updated_at": "updated_at",
    },
    "RequestRecord": {
        "id": "id + prefijo ECON",
        "project_id": "project_id",
        "project_name": "project_name",
        "machinery_id": "maquinaria_id + prefijo ECON",
        "status": "status",
        "starts_on": "fecha_inicio",
        "ends_on": "fecha_fin",
        "machinery_type": "tipo",
        "requested_by": "requested_by_name",
        "requested_by_id": "requested_by_user_id",
        "comments": "comentarios",
        "created_at": "created_at",
        "updated_at": "updated_at",
        "approved_at": "approved_at",
    },
}

MEANINGS = {
    "id": "Identificador del objeto; su ámbito depende del modelo, nunca de un nombre visible.",
    "source": "Fuente de la evidencia; en ReceiptRecord identifica declaración manual.",
    "source_id": "ID original del proveedor; conservar separado del ID local y de etiquetas.",
    "environment": "Entorno de la evidencia o movimiento; no acredita datos de producción.",
    "observed_at": "Instante de observación/lectura conocido; no sustituye la fecha del evento.",
    "is_synthetic": "Naturaleza sintética de los datos; independiente de fixture/live.",
    "evidence_kind": "Clase de evidencia: muestra proporcionada, lectura actual o caso interno de prueba.",
    "source_reference": "Referencia documental que permite localizar la muestra de origen.",
    "observed_on": "Día documentado sin inventar una hora de observación.",
    "label": "Etiqueta de presentación de la fuente o ubicación; no clave de unión.",
    "status": "Estado del objeto del modelo; ver separación semántica de estados.",
    "message": "Explicación legible de disponibilidad/cobertura, sin cuerpos privados ni secretos.",
    "code": "Código descriptivo de equipo/tarea o identificador de regla según el modelo.",
    "request_id": "Referencia a la solicitud en el contrato de lectura, normalmente con prefijo nexus:request:.",
    "destination_project_id": "Referencia de proyecto destino; no prueba presencia ni recepción.",
    "destination_project_name": "Nombre descriptivo del destino; no resuelve su identidad.",
    "driver": "Etiqueta de motorista, sin equivalencia automática a usuario o conductor Startrack.",
    "provenance": "Procedencia del objeto o evento; ver Provenance.",
    "asset_number": "Número de activo Prisma no_activo, separado de clave y UUID.",
    "name": "Nombre descriptivo de la maquinaria.",
    "company": "Valor original de empresa; no se interpreta como identidad legal.",
    "equipment_class": "Clase de maquinaria del origen, distinta del tipo de tarea.",
    "project_id": "UUID de proyecto Prisma asociado al objeto; no equivale a poi_id.",
    "project_name": "Nombre de proyecto del origen; solo presentación.",
    "machinery_status": "Estado administrativo de maquinaria Prisma, conservado literalmente.",
    "maintenance_failure_id": "Referencia de falla activa, si está disponible.",
    "maintenance_status": "Estado de falla/mantenimiento, separado del estado administrativo.",
    "maintenance_is_stopped": "Paro explícito: true/false; null significa desconocido.",
    "request_ids": "Solicitudes de la consulta vinculadas por maquinaria_id exacto.",
    "transfers": "Lista de traslados del contrato de lectura; no hay ejemplos Startrack en la muestra.",
    "location": "Observación de ubicación fechada; ausente en el dataset proporcionado.",
    "relation_status": "Calidad de relación: confirmada, candidata o sin vínculo; no equivalencia por nombre.",
    "relation_note": "Evidencia o límite de la relación con el traslado.",
    "created_at": "Creación en Prisma para equipo/solicitud; creación local para movimiento.",
    "updated_at": "Actualización en Prisma para equipo/solicitud; última actualización local del movimiento.",
    "machinery_id": "ID normalizado de maquinaria asignada; conserva prefijo del contrato del hub.",
    "starts_on": "Inicio del uso solicitado, conservado como texto; no ventana de entrega.",
    "ends_on": "Fin del uso solicitado, conservado como texto; no vencimiento del traslado.",
    "machinery_type": "Clase solicitada en Prisma; no identifica por sí sola una unidad.",
    "requested_by": "Nombre del solicitante Prisma; no receptor ni usuario Startrack asignado.",
    "requested_by_id": "UUID del solicitante Prisma; no se transforma en ID de otro proveedor.",
    "comments": "Comentarios de solicitud preservados; el borrador actual no los copia.",
    "approved_at": "Instante de aprobación informado por Prisma; no salida, llegada o recepción.",
    "severity": "Categoría propuesta de una regla de alerta; no SLA ni puntaje de riesgo.",
    "title": "Texto de la señal de revisión.",
    "description": "Explicación de alerta o contenido generado del borrador, según modelo.",
    "owner": "Área funcional propuesta para revisar la alerta; no asignación autenticada.",
    "equipment_id": "Referencia a maquinaria en el contrato normalizado de lectura.",
    "evidence": "Hechos que sostienen la regla de alerta, como lista de textos.",
    "search": "Búsqueda local sobre el conjunto acotado recibido.",
    "bounded": "Indica que la consulta tiene límites; no es censo irrestricto.",
    "equipment_total": "Total de equipos informado por el origen antes del filtro local.",
    "requests_total": "Total de solicitudes informado por el origen antes del filtro local.",
    "equipment_returned": "Equipos incluidos tras aplicar la búsqueda local.",
    "requests_returned": "Solicitudes incluidas tras aplicar la búsqueda local.",
    "complete": "Completitud del ámbito integrado/catálogos, no simple éxito de una llamada.",
    "equipment_count": "Conteo de equipos devueltos; null si no se obtuvo lectura evaluable.",
    "administratively_available": "Equipos devueltos cuyo estado administrativo es Disponible; no disponibilidad física.",
    "active_failures": "Equipos devueltos con referencia de falla activa.",
    "stopped_equipment": "Equipos devueltos con paro explícito true.",
    "unlinked_equipment": "Equipos devueltos cuya relación no es confirmed; incluye candidatos.",
    "alerts_count": "Alertas sobre los datos evaluados; cero no certifica ausencia global de riesgo.",
    "schema_version": "Versión del contrato de lectura de ECON.",
    "mode": "Mecanismo seleccionado: muestra de archivo o lectura actual del sandbox.",
    "generated_at": "Instante de ensamblaje de la respuesta; no antigüedad del dato de origen.",
    "data_as_of": "Corte de lectura, cuando existe; null en muestras sin instante común.",
    "sources": "Estados técnicos y cobertura de las fuentes.",
    "scope": "Población, filtros y límites de la respuesta; ver HubScope.",
    "summary": "Conteos sobre la población devuelta; ver HubSummary.",
    "equipment": "Equipos de la proyección de lectura; ver EquipmentRecord.",
    "requests": "Solicitudes de la proyección de lectura; ver RequestRecord.",
    "alerts": "Señales derivadas de hechos disponibles; ver AlertRecord.",
    "movement_reference": "Referencia de correlación creada en ECON; se envía como remote_id, sin unicidad remota garantizada.",
    "request_source_id": "UUID original de solicitud Prisma, sin prefijo local.",
    "machinery_source_id": "UUID original de maquinaria Prisma, sin prefijo local.",
    "project_source_id": "UUID original del proyecto Prisma.",
    "tracked_vehicle_id": "ID de activo rastreado elegido por separado; puede ser el transportador.",
    "mapping": "Correspondencias explícitas y programación; estructura de TransferMapping.",
    "source_request": "Copia normalizada de solicitud usada como evidencia del movimiento.",
    "source_equipment": "Copia normalizada de maquinaria usada como evidencia, si existe.",
    "source_request_hash": "SHA-256 de la copia normalizada de solicitud con JSON canónico local.",
    "source_equipment_hash": "SHA-256 de la copia normalizada de maquinaria, cuando existe.",
    "identity_hash": "SHA-256 de mapping, payload y tracked_vehicle_id; distingue contenido del plan bajo su referencia local.",
    "payload": "Cuerpo preparado para Job; null si no hay borrador válido. No acredita envío.",
    "preparation": "Resultado estructurado de preparación; ver TransferPreparation.",
    "state": "Estado local del envío; separado del estado remoto de tarea y de recepción.",
    "job_id": "ID de tarea confirmado por Startrack; ausente en muestras proporcionadas.",
    "workflow_role": "Rol remoto del catálogo de estado de tarea; no es rol de usuario.",
    "reason_code": "Código local de motivo/bloqueo/fallo; detalle en eventos y preparación.",
    "queued_at": "Instante local de ingreso en cola, si ocurrió.",
    "sending_at": "Instante local de reclamación/inicio de envío, si ocurrió.",
    "sent_at": "Instante local en que se confirmó asociación de tarea; no ejecución ni llegada.",
    "receipt": "Declaración explícita de recepción; nunca generada por GPS o cierre de tarea.",
    "movement_id": "ID local del movimiento al que pertenece el evento.",
    "kind": "Tipo de evento local: transición, observación, evidencia o recepción según el productor.",
    "evidence_hash": "SHA-256 de kind/source_id/event_time/data/provenance, sin provenance.observed_at; deduplica task_state/arrival.",
    "event_time": "Instante del hecho informado por el origen, si puede interpretarse con zona.",
    "recorded_at": "Instante en que ECON almacena la evidencia o declaración.",
    "data": "Contenido del evento local/observación; objeto JSON de estructura según kind.",
    "content_hash": "SHA-256 del HubResponse completo, incluidos tiempos/cobertura; no huella exclusiva de hechos de negocio.",
    "content": "Respuesta del hub serializada que se conserva como corte.",
    "receiver": "Nombre declarado del receptor; no acredita identidad autenticada.",
    "received_at": "Instante declarado de recepción; el servicio exige zona horaria.",
    "reference": "Referencia de constancia declarada; no adjunto ni comprobación automática del documento.",
    "note": "Nota opcional de la declaración de recepción.",
    "events": "Historial local de eventos; no copia completa de la actividad de los proveedores.",
    "available": "Disponibilidad de consulta del registro local de operaciones.",
    "management_enabled": "Capacidad de gestión habilitada por servidor y contexto local; no autorización desde navegador.",
    "sending_enabled": "Habilitación de envío evaluada por servidor; no demuestra conectividad ni permisos remotos.",
    "movements": "Movimientos locales de la consulta; cero solo es interpretable con available=true.",
    "last_sync_at": "recorded_at del último SourceSnapshot por modo; no acredita sincronización exitosa de todas las fuentes.",
    "pois": "Catálogo acotado de geocercas para elegir IDs; no maestro de equivalencias aprobado.",
    "users": "Catálogo acotado de usuarios Startrack asignables; separado de operadores Prisma.",
    "vehicles": "Catálogo acotado de activos rastreados.",
    "job_types": "Catálogo acotado de tipos de tarea; distinto de clase de maquinaria.",
    "poi_id": "ID Startrack de destino confirmado explícitamente; no inferido del nombre de proyecto.",
    "assigned_user_ids": "IDs de usuarios Startrack elegidos explícitamente, sin duplicados.",
    "scheduled_date": "Fecha explícita de programación del movimiento; no copia automática del inicio de uso.",
    "scheduled_time": "Hora explícita HH:MM:SS sin zona en payload; confirmar zona de la cuenta.",
    "job_type_id": "ID opcional del tipo de tarea Startrack.",
    "request_provenance": "Procedencia de la solicitud revisada para preparar el movimiento.",
    "equipment_provenance": "Procedencia de la maquinaria revisada, si existe.",
    "missing_fields": "Datos necesarios que faltan para preparar el borrador.",
    "blocking_reasons": "Razones que impiden preparar el borrador.",
    "notes": "Advertencias y límites de interpretación de la preparación.",
    "draft": "Propuesta local de tarea; ver StartrackTaskDraft.",
    "remote_writes": "Siempre false: preparar el borrador no escribe en los proveedores.",
    "objective": "Título generado con etiquetas de unidad/proyecto, hasta 255 caracteres; no clave de unión.",
    "start_date": "Fecha explícita del traslado en Job; diferente del período de uso Prisma.",
    "remote_id": "Referencia local de movimiento enviada para correlación; no idempotencia garantizada.",
    "start_time": "Hora programada HH:MM:SS del Job; el campo no contiene zona.",
    "form_ids": "IDs de formularios asociados al borrador; soporte SDK, no propagados por preparación actual.",
    "required_form_ids": "Subconjunto de formularios obligatorios; no define por sí solo recepción empresarial.",
    "notify_contact": "Siempre false en este borrador; no solicita avisos al contacto.",
}

OVERRIDES = {
    (
        "EquipmentRecord",
        "code",
    ): "Prisma clave; conservar null aunque exista no_activo.",
    ("SourceStatus", "id"): "Identidad lógica nexus/startrack del proveedor.",
    (
        "SourceStatus",
        "status",
    ): "Estado técnico de fuente, distinto del estado de maquinaria o traslado.",
    ("RequestRecord", "status"): "Estado original del flujo de solicitud en Prisma.",
    (
        "TransferRecord",
        "status",
    ): "Estado del traslado en la proyección de lectura, separado de maquinaria.",
    (
        "TransferPreparation",
        "status",
    ): "Resultado local: faltan datos, requiere revisión o borrador preparado.",
    (
        "Movement",
        "status",
    ): "ID/texto de estado remoto de la tarea Startrack; no estado de envío local.",
    (
        "MovementRecord",
        "status",
    ): "ID/texto de estado remoto de la tarea Startrack; no estado de envío local.",
    (
        "LocationObservation",
        "observed_at",
    ): "Instante de la posición; puede ser anterior a provenance.observed_at.",
    (
        "HubScope",
        "description",
    ): "Explicación de la población y límites de cobertura de la consulta.",
    (
        "StartrackTaskDraft",
        "description",
    ): "Texto generado con UUID de solicitud, maquinaria, proyecto y referencia; no copia comentarios.",
}

MODEL_ORIGINS = {
    "Provenance": "ECON añade metadatos al dato Prisma/Startrack",
    "SourceStatus": "ECON: disponibilidad y cobertura del conector",
    "TransferRecord": "Proyección prevista de traslado; sin muestra proporcionada",
    "LocationObservation": "Proyección de ubicación; sin muestra proporcionada",
    "EquipmentRecord": "Prisma → normalización ECON; fixtures.py / hub.py",
    "RequestRecord": "Prisma → normalización ECON; fixtures.py / hub.py",
    "AlertRecord": "ECON: services/hub.py evaluate_alerts",
    "HubScope": "ECON: límites de lectura y filtrado local",
    "HubSummary": "ECON: conteos sobre registros devueltos",
    "HubResponse": "ECON: ensamblaje del contrato de consulta",
    "Movement": "ECON: registro SQLModel de plan/envío/evidencia",
    "OperationEvent": "ECON: services/ledger.py y services/workflow.py",
    "SourceSnapshot": "ECON: conservación explícita de cortes",
    "ReceiptRecord": "Declaración manual → registro local ECON",
    "MovementEventRecord": "Proyección de OperationEvent para consumo",
    "MovementRecord": "Proyección de Movement y su historial local",
    "SnapshotRecord": "Proyección de SourceSnapshot",
    "WorkflowOverview": "ECON: resumen de operaciones consultadas",
    "MappingCatalogs": "Startrack SDK → catálogos acotados de ECON",
    "TransferMapping": "Correspondencias y programación proporcionadas explícitamente",
    "TransferPreparation": "ECON: services/transfers.py prepare_transfer",
    "StartrackTaskDraft": "ECON prepara campos del contrato Job; no acredita aceptación",
    "PlanInput": "Entrada de gestión local → TransferMapping",
    "SyncInput": "Entrada de gestión local para seleccionar modo",
    "ReceiptInput": "Entrada de declaración manual de recepción",
}


def api_inputs() -> list[type[BaseModel]]:
    """Extract only DTO declarations; never import routes/dependencies/settings."""
    path = API / "app" / "api" / "workflow.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names = {"PlanInput", "SyncInput", "ReceiptInput"}
    declarations = [
        n for n in tree.body if isinstance(n, ast.ClassDef) and n.name in names
    ]
    namespace = {
        "__name__": "econ_dictionary_inputs",
        "BaseModel": BaseModel,
        "ConfigDict": ConfigDict,
        "Field": Field,
        "DataMode": DataMode,
        "Identifier": Identifier,
        "TransferMapping": TransferMapping,
        "datetime": datetime,
    }
    # Only three reviewed, repository-owned DTO declarations; no source documents or input text.
    exec(  # noqa: S102
        compile(ast.Module(body=declarations, type_ignores=[]), str(path), "exec"),
        namespace,
    )
    for node in declarations:
        namespace[node.name].model_rebuild(_types_namespace=namespace)
    return [namespace[node.name] for node in declarations]


def models() -> list[tuple[type[BaseModel], str]]:
    result = []
    for name in MODULES:
        module = importlib.import_module(name)
        for value in vars(module).values():
            if (
                inspect.isclass(value)
                and issubclass(value, BaseModel)
                and value.__module__ == name
            ):
                result.append((value, f"apps/api/{name.replace('.', '/')}.py"))
    result.extend(
        [
            (TransferMapping, "apps/api/app/services/transfers.py"),
            (TransferPreparation, "apps/api/app/services/transfers.py"),
            (StartrackTaskDraft, "apps/api/app/integrations/startrack.py"),
        ]
    )
    result.extend((model, "apps/api/app/api/workflow.py") for model in api_inputs())
    return result


def json_type(schema: dict[str, Any]) -> str:
    if "$ref" in schema:
        return schema["$ref"].rsplit("/", 1)[-1]
    if "anyOf" in schema:
        return " / ".join(json_type(item) for item in schema["anyOf"])
    if "const" in schema:
        return json.dumps(schema["const"])
    if "enum" in schema:
        return "enum(" + ", ".join(map(str, schema["enum"])) + ")"
    kind = schema.get("type", "JSON")
    if kind == "array":
        return f"lista<{json_type(schema.get('items', {}))}>"
    if kind == "string" and schema.get("format"):
        return schema["format"]
    return {
        "string": "texto",
        "integer": "entero",
        "boolean": "booleano",
        "object": "objeto JSON",
    }.get(kind, kind)


def sample_values() -> dict[str, dict[str, Any]]:
    equipment, requests = fixture_records()
    machine = next(row for row in equipment if row.asset_number == "CF-03")
    request = next(row for row in requests if row.machinery_id == machine.id)
    return {
        "EquipmentRecord": machine.model_dump(mode="json"),
        "RequestRecord": request.model_dump(mode="json"),
        "Provenance": request.provenance.model_dump(mode="json"),
        "HubScope": {
            "search": "",
            "bounded": True,
            "equipment_total": 15,
            "requests_total": 2,
            "equipment_returned": len(equipment),
            "requests_returned": len(requests),
            "complete": False,
        },
        "HubSummary": {
            "equipment_count": len(equipment),
            "administratively_available": sum(
                row.machinery_status.upper() == "DISPONIBLE" for row in equipment
            ),
            "active_failures": sum(
                row.maintenance_failure_id is not None for row in equipment
            ),
            "stopped_equipment": sum(
                row.maintenance_is_stopped is True for row in equipment
            ),
            "unlinked_equipment": sum(
                row.relation_status != "confirmed" for row in equipment
            ),
        },
        "HubResponse": {"data_as_of": None, "mode": "fixture"},
    }


def example(schema: dict[str, Any], field: str) -> tuple[Any, str]:
    if "default" in schema:
        return schema["default"], "valor por defecto del modelo"
    if "anyOf" in schema and any(
        item.get("type") == "null" for item in schema["anyOf"]
    ):
        return None, "sin muestra; null permitido"
    if "const" in schema:
        return schema["const"], "constante del contrato"
    if "$ref" in schema:
        return {}, "estructura técnica; campos en la tabla del modelo referenciado"
    if "enum" in schema:
        return schema["enum"][0], "ejemplo técnico de catálogo, no observación"
    kind = schema.get("type")
    if kind == "array":
        if schema.get("minItems", 0) > 0:
            return [
                "<id-tecnico-por-confirmar>"
            ], "ejemplo técnico de estructura, no ID operativo"
        return [], "ejemplo técnico de lista; no conteo operativo"
    if kind == "object":
        return {}, "ejemplo técnico de objeto; ver significado y modelo anidado"
    if kind == "boolean":
        return False, "ejemplo técnico de tipo, no observación"
    if kind in {"integer", "number"}:
        return 0, "ejemplo técnico de tipo, no medición"
    if schema.get("format") == "date-time":
        return TECH_TIME, "instante técnico ilustrativo, no evento del sandbox"
    if schema.get("format") == "date":
        return "2000-01-01", "fecha técnica ilustrativa, no programación"
    if field.endswith("hash"):
        return "0" * 64, "estructura técnica SHA-256, no huella calculada"
    return f"<{field}-tecnico>", "ejemplo técnico de texto; no hecho operativo"


def cell(value: str) -> str:
    return value.replace("|", "&#124;").replace("\n", "<br>")


def field_origin(model: str, field: str) -> str:
    if field in PRISMA_FIELDS.get(model, {}):
        return f"Prisma: {PRISMA_FIELDS[model][field]}"
    if model in {
        "TransferMapping",
        "PlanInput",
        "SyncInput",
        "ReceiptInput",
        "ReceiptRecord",
    }:
        return "Entrada explícita; metadatos de registro en ECON"
    if model in {
        "Movement",
        "MovementRecord",
        "OperationEvent",
        "MovementEventRecord",
        "SourceSnapshot",
        "SnapshotRecord",
    }:
        if field in {"job_id", "status", "workflow_role"}:
            return "Startrack → registro ECON"
        return "Registro local ECON; significado según campo"
    if model == "MappingCatalogs":
        return "Startrack SDK; metadatos de consulta ECON"
    if model in {"TransferRecord", "LocationObservation"}:
        return "Proyección de Startrack prevista; sin muestra"
    if model == "StartrackTaskDraft":
        return "Borrador ECON para contrato Job"
    return "Derivación o metadato ECON"


def render() -> str:
    model_list = models()
    samples = sample_values()
    paths = sorted({source for _, source in model_list})
    count = sum(len(model.model_fields) for model, _ in model_list)
    lines = [
        "# Diccionario del modelo vigente de ECON",
        "",
        "Inventario generado del código local para **RF-01**, con revisión semántica del flujo.",
        f"Cubre **{len(model_list)} modelos y {count} campos declarados** (incluidos campos heredados de entradas).",
        "No representa las 51 definiciones del diccionario de proveedores ni acredita un mapeo completo.",
        "",
        "Las tablas usan JSONPath relativo a cada modelo (`$` es su raíz). Los objetos anidados",
        "se describen en su propia tabla; no se repiten todos los caminos posibles. Los modelos",
        "SQLModel incluyen columnas internas que no se exponen en sus proyecciones públicas.",
        "",
        "**Ejemplos:** los campos de CF-03 y de su solicitud provienen de las muestras proporcionadas",
        "del OpenAPI. Los conteos se derivan de cinco equipos y dos solicitudes, sin filtro.",
        "Los demás valores están rotulados como estructura técnica, defecto o constante; no son",
        "movimientos, tareas, ubicaciones, recepciones ni IDs del sandbox. `null` conserva lo desconocido",
        "cuando el contrato lo admite. `{}` y `[]` ilustran contenedores; no son objetos completos",
        "válidos si un modelo anidado exige campos. Una fila no constituye un payload listo para enviar.",
        "",
        "La muestra no tiene un instante de corte común. El ejemplo técnico `2000-01-01T00:00:00Z`",
        "solo ilustra una fecha con zona y nunca se usa para evaluar la operación.",
        "",
        "## Alcance y reproducción",
        "",
        "Se incluyen todos los modelos propios de `models/hub.py`, `models/operations.py` y",
        "`models/workflow.py`, además de `TransferMapping`, `TransferPreparation`,",
        "`StartrackTaskDraft` y las entradas de la API de operaciones. Se enumeran sus campos",
        "públicos/declarados; propiedades, validadores y restricciones de servicio se explican abajo.",
        "Se excluyen configuración/secretos, modelos genéricos del transporte y DTO de proveedores",
        "que no crean vocabulario del hub; su correspondencia está en la matriz de equivalencias.",
        "",
        "Desde la raíz, con las dependencias ya instaladas:",
        "",
        "```powershell",
        "uv run --project apps/api python scripts/docs/generar_diccionario.py",
        "uv run --project apps/api python scripts/docs/generar_diccionario.py --check",
        "```",
        "",
        "El generador importa únicamente declaraciones de modelos y el lector de muestras locales.",
        "Extrae las tres entradas HTTP por AST sin importar rutas ni dependencias. No carga settings,",
        "no abre la base, no inicia clientes y no consulta proveedores. `--check` verifica que este",
        "archivo coincida con las declaraciones y anotaciones del generador.",
        "",
        "| Fuente del código | SHA-256 |",
        "| --- | --- |",
    ]
    for path in paths:
        digest = hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
        lines.append(f"| [{path}](../{path}) | `{digest}` |")
    lines.extend(["", "## Inventario estructurado", ""])
    for model, source in model_list:
        name = model.__name__
        schema = model.model_json_schema()
        lines.extend(
            [
                f"### {name}",
                "",
                f"Procedencia: {MODEL_ORIGINS[name]}. [Código](../{source}).",
                "",
                "| Campo / JSONPath | Tipo JSON | Obligatorio | Ejemplo y clase de evidencia | Significado | Procedencia |",
                "| --- | --- | --- | --- | --- | --- |",
            ]
        )
        required = set(schema.get("required", []))
        for field, definition in schema["properties"].items():
            meaning = OVERRIDES.get((name, field), MEANINGS.get(field))
            if meaning is None:
                raise ValueError(f"Falta significado para {name}.{field}")
            if field in samples.get(name, {}):
                value = samples[name][field]
                label = (
                    "muestra normalizada"
                    if name not in {"HubScope", "HubSummary", "HubResponse"}
                    else "derivado de muestra / alcance"
                )
                if isinstance(value, (dict, list)) and value:
                    value = {} if isinstance(value, dict) else value
                    if field == "provenance":
                        label = "ver Provenance; muestra normalizada"
            else:
                value, label = example(definition, field)
            rendered = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
            lines.append(
                f"| `$.{field}` | {cell(json_type(definition))} | {'Sí' if field in required else 'No'} "
                f"| `{cell(rendered)}` — {label} | {cell(meaning)} | {cell(field_origin(name, field))} |"
            )
        lines.append("")
    lines.extend(SEMANTICS.strip().splitlines())
    return "\n".join(lines).rstrip() + "\n"


SEMANTICS = """
## Reglas que el tipo por sí solo no expresa

| Concepto | Regla implementada y límite | Evidencia de código |
| --- | --- | --- |
| Identidad de lectura | `nexus:request:` y `nexus:equipment:` distinguen objetos internos. El UUID original permanece en procedencia; código, activo y nombre no reemplazan la clave. | [fixtures.py](../apps/api/app/integrations/fixtures.py), [hub.py](../apps/api/app/services/hub.py) |
| Identidad de movimiento | `Movement.id` es local; `movement_reference` correlaciona el plan y Job.remote_id. La unicidad local es modo + entorno + referencia. No se atribuye unicidad de remote_id al proveedor. | [operations.py](../apps/api/app/models/operations.py), [ledger.py](../apps/api/app/services/ledger.py) |
| Estado por objeto | `RequestRecord.status` describe solicitud; `machinery_status`, máquina; `maintenance_*`, falla/paro; `Movement.state`, envío; `status`/`workflow_role`, tarea. Presencia y recepción siguen independientes. | [transfers.py](../apps/api/app/services/transfers.py), [workflow.py](../apps/api/app/services/workflow.py) |
| Envío incierto | `unknown` necesita conciliación por lectura. `sent` acredita una tarea vinculada, no ejecución o recepción. La recepción no se deriva automáticamente de una tarea completada. | [workflow.py](../apps/api/app/services/workflow.py) |
| Fechas | `created_at`/`updated_at` del origen, `approved_at`, `event_time`, `observed_at`, `recorded_at` y `generated_at` son hechos distintos. Una fecha sin hora sigue siendo fecha; no adquiere una zona o plazo inventado. | [hub.py](../apps/api/app/services/hub.py), [ledger.py](../apps/api/app/services/ledger.py) |
| Corte de muestra | `data_as_of=null` y `observed_at=null`; `observed_on=2026-09-12` conserva el día documental. El reloj actual no permite clasificar atraso con estas muestras. | [fixtures.py](../apps/api/app/integrations/fixtures.py) |
| Última sincronización | `last_sync_at` usa la última instantánea por modo. Se guarda antes del seguimiento Startrack; puede coexistir con errores parciales y no certifica la vigencia de cada tarea. | [workflow.py](../apps/api/app/services/workflow.py), [ledger.py](../apps/api/app/services/ledger.py) |
| Huellas internas | `identity_hash` y `evidence_hash` no salen en las proyecciones públicas; `source_request_hash` y `source_equipment_hash` sí. Se calculan sobre JSON normalizado, no sobre cuerpos HTTP originales. | [ledger.py](../apps/api/app/services/ledger.py) |
| Eventos repetidos o tardíos | Repetir una observación equivalente conserva su primera lectura. Se registran hechos tardíos, pero no reemplazan una proyección de tarea más reciente. Los eventos públicos se ordenan por recorded_at e ID. | [ledger.py](../apps/api/app/services/ledger.py) |
| Recepción | El servicio exige receptor y referencia no vacíos e instante con zona. El nombre declarado no es identidad autenticada; la referencia no carga ni valida un archivo de constancia. | [api/workflow.py](../apps/api/app/api/workflow.py), [workflow.py](../apps/api/app/services/workflow.py) |
| Correspondencias | Los identificadores deben ser cadenas no vacías sin espacios; los asignados no se repiten. POI, usuarios y activo rastreado se eligen explícitamente; proyecto, solicitante y motorista no se unen por nombres. | [transfers.py](../apps/api/app/services/transfers.py), [startrack.py](../apps/api/app/integrations/startrack.py) |
| Borrador | Fecha explícita YYYY-MM-DD; hora HH:MM:SS; objetivo no vacío y máximo 255 caracteres. Formularios obligatorios son subconjunto de formularios asociados. `notify_contact=false`. Preparación no certifica aceptación remota. | [startrack.py](../apps/api/app/integrations/startrack.py) |
| JSON interno | `mapping`, `source_request`, `source_equipment`, `preparation`, `payload`, `receipt`, `content` y `data` se tipan como JSON en persistencia. Sus estructuras operativas se revisan contra los modelos y productores; el esquema SQL no valida por sí solo toda su semántica. | [ledger.py](../apps/api/app/services/ledger.py) |

## Derivaciones de presentación vigentes

Estas estructuras pertenecen a Dash y no se agregan como campos de los proveedores.
Los ejemplos numéricos usan exclusivamente la muestra sin filtros; los textos de
decisión son resultados de reglas locales y no acontecimientos externos nuevos.

| Campo o término | Tipo | Ejemplo / evidencia | Significado y procedencia |
| --- | --- | --- | --- |
| `QueryContext.mode` | fixture/live | `fixture` · selección técnica | Origen escogido en URL; no habilita proveedores. |
| `QueryContext.query` | texto | `""` · selección técnica | Búsqueda; máximo 100 caracteres, bajo `q` en URL. |
| `QueryContext.filter` | catálogo de filtros | `all` · selección técnica | Filtro visible validado; no autorización. |
| `QueryContext.read_key` | lista de textos | `["fixture", ""]` · selección técnica | Clave derivada de modo y búsqueda para asociar la lectura. |
| `RequestCounts.total` | entero/null | `2` · derivado de muestra | Solicitudes de la población filtrada. |
| `RequestCounts.unassigned` | entero/null | `1` · derivado de muestra | Solicitudes sin ID de maquinaria; no unidades ausentes por paginación. |
| `RequestCounts.without_confirmed_task` | entero/null | `null` · registro de operaciones sin consultar | Solo calcula ausencia de vínculo si el registro local está disponible; requiere tarea enviada con ID confirmado. |
| `UsagePeriod.request` | RequestRecord | ver solicitud CF-03 | Registro original para preservar identidad. |
| `UsagePeriod.starts_on`, `ends_on` | fecha | `2026-09-11`, `2026-09-14` · muestra | Fechas de uso válidas; no fechas del traslado. |
| `UsagePeriod.calendar_days` | entero | `4` · derivado de muestra | Diferencia de días + 1; longitud del intervalo dibujado, no utilización. |
| `ExcludedPeriod.request`, `reason` | RequestRecord, texto | sin ejemplo excluido en la muestra | Registro y motivo de exclusión por fechas faltantes, inválidas o invertidas. |
| `UsageTimeline.periods`, `excluded` | tuplas de períodos/exclusiones | 2 períodos, 0 exclusiones · muestra | Resultado de validar y ordenar intervalos. |
| `request_states`: estado, cantidad | texto, entero | `APROBADA: 1`, `PENDIENTE: 1` · muestra | Conteo por categoría original en la misma población filtrada. |
| `DecisionItem.request`, `equipment` | RequestRecord, EquipmentRecord/null | solicitud aprobada y CF-03 · muestra | Registros enlazados por ID y procedencia compatible. |
| `DecisionItem.title` | texto | `Revisar la asignación` · regla sobre muestra | Acción de revisión porque CF-03 figura OBSOLETA; no declara avería. |
| `DecisionItem.evidence` | texto | estado administrativo OBSOLETA · regla sobre muestra | Explica los hechos disponibles y los faltantes del registro de movimientos. |
| `DecisionItem.action`, `href` | textos | `Revisar solicitud` y ruta derivada del ID | Etiqueta y navegación al registro; no ejecución automática de la acción. |

Fuentes: [context.py](../apps/api/app/dashboard/context.py),
[decision_analytics.py](../apps/api/app/dashboard/decision_analytics.py),
[decision_priorities.py](../apps/api/app/dashboard/decision_priorities.py).
Este apartado cubre las derivaciones de decisión y calendario vigentes; no enumera
cada propiedad visual de Plotly, AG Grid, HTML ni utilidades de presentación históricas.

## Uso con las matrices del reto

Este inventario reemplaza el vocabulario de la primera versión del modelo operativo.
La [matriz de equivalencias](equivalencias-prisma-startrack.md) explica el mapeo por
fuente, las cardinalidades y lo no soportado; la
[matriz de requisitos](matriz-requisitos-entregables.md) conserva brechas de la entrega.
Un inventario de tipos no acredita API autenticada, identidad entre plataformas,
recepción física, cobertura total de la flota ni cumplimiento ISO.
"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check", action="store_true", help="Check the checked-in dictionary"
    )
    args = parser.parse_args()
    rendered = render()
    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_text(encoding="utf-8") != rendered:
            raise SystemExit(
                "El diccionario no coincide con el código; volver a generarlo."
            )
        print("Diccionario vigente: modelos, campos y anotaciones coinciden.")
        return
    OUTPUT.write_text(rendered, encoding="utf-8", newline="\n")
    print(f"Generado: {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
