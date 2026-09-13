# Entregable 1: Matriz de Mapeo de Campos (Prisma ↔ Startrack)
**Hackathon Grupo ECON 2026** · *Equipo: Los Filósofos*

Este documento establece la correspondencia estructurada entre los campos de **Prisma** (`/api/maquinaria/*`) y **Startrack** (`/api/job`), identificando de manera explícita aquellos que **no tienen un equivalente directo**.

---

## 1. Mapeo Consolidado de Correspondencia

| Campo Prisma (Origen) | Modelo ECON (Normalizado) | Campo Startrack (Destino) | Tratamiento | Equivalencia / Justificación Técnica |
| :--- | :--- | :--- | :--- | :--- |
| `Request.id` | `RequestRecord.id` | `job.description` | **Transformado** | Embebido en la descripción (`Solicitud Prisma: {id}`) para garantizar trazabilidad bidireccional sin colisionar con IDs numéricos de Startrack. |
| `Request.machinery_type` | `RequestRecord.machinery_type` | `job.objective` | **Transformado** | Concatenado en el título de la tarea: `"Traslado de {asset_number} a {project_name}"`. |
| `Request.starts_on` | `RequestRecord.starts_on` | `job.start_date` | **Manual / Derivado** | **Sin equivalente directo**: El inicio de uso solicitado no es la fecha de transporte; requiere programación logística. |
| `Request.ends_on` | `RequestRecord.ends_on` | *(Ninguno)* | **Sin equivalente** | Fecha de fin de uso en obra; no aplica a la tarea telemática de entrega de Startrack. |
| `Equipment.asset_number` | `EquipmentRecord.asset_number` | `job.objective` | **Transformado** | Código operativo visible para el motorista (ej. `CF-01`). |
| `Project.id` | `RequestRecord.project_id` | `job.poi_id` | **Mapeado** | Correspondencia a la geocerca de destino (`POI-PROY-014`). |
| `Equipment.worker_code` | `EquipmentRecord.operators[].worker_code` | `job.assigned_user_ids` | **Mapeado** | Solo cuando el código MOT de Prisma tiene usuario registrado en Startrack; nunca por coincidencia aproximada de nombres. |
| `Equipment.machinery_status` | `EquipmentRecord.machinery_status` | *(Ninguno)* | **Sin equivalente** | Estado administrativo de ERP (`DISPONIBLE`, `OCUPADA`, `OBSOLETA`); el transportista no administra inventario. |
| `Equipment.project_rate` | `EquipmentRecord.project_rate` | *(Ninguno)* | **Sin equivalente** | Dato económico confidencial de Grupo ECON; no se expone al proveedor telemático. |
| `Equipment.active_failure_id` | `EquipmentRecord.maintenance_failure_id` | *(Ninguno)* | **Sin equivalente** | Diagnóstico interno de Mantenimiento; se usa en ECON como regla de guardia (*guard*) para impedir traslados. |
| `Equipment.active_failure_is_paro` | `EquipmentRecord.maintenance_is_stopped` | *(Ninguno)* | **Sin equivalente** | Bandera de paro crítico; bloquea la creación de la tarea en ECON. |
| *(No provisto en Prisma)* | `TransferMapping.start_time` | `job.start_time` | **Manual** | Hora programada para el inicio del flete; definida por Logística. |
| *(No provisto en Prisma)* | `TransferMapping.remote_id` | `job.remote_id` | **Generado por ECON** | Identificador único del movimiento en el libro mayor local (`MOV-XXXX`). |
| *(No provisto en Prisma)* | *(Sin equivalente)* | `job.form_ids` | **Sin equivalente** | Formularios dinámicos en la app móvil de Startrack; opcionales en el prototipo. |

---

## 2. Archivos Relacionados
- **Libro Excel con 17 tablas estructuradas**: `1-Matriz-de-Mapeo-de-Campos.xlsx`
- **CSV para ingesta automatizada**: `1-Matriz-de-Mapeo-de-Campos.csv`
- **Diccionario de datos completo**: `docs/diccionario-modelo-econ.md`
