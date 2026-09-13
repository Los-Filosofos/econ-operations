# Entregable 2: Matriz de Responsabilidades (RACI)
**Hackathon Grupo ECON 2026** · *Equipo: Los Filósofos*

Matriz estructurada que define quién es **Responsable (R)**, quién **Aprueba (A)**, a quién se **Consulta (C)** y a quién se **Informa (I)** sobre el estado de un equipo a lo largo de su ciclo de vida, cubriendo las tres gerencias involucradas (**Mantenimiento**, **Logística y Equipos**, y **Técnica de Proyectos**) más **Control de Costos**.

---

## 1. Tabla Estructurada RACI

| Decisión o Evento Operativo | Gerencia Técnica de Proyectos | Gerencia de Logística y Equipos | Gerencia de Mantenimiento | Control de Costos / Finanzas |
| :--- | :---: | :---: | :---: | :---: |
| **1. Solicitud de Maquinaria**<br>Definición del tipo de equipo, obra destino y ventana de uso requerida. | **R / A** | C | I | I |
| **2. Aprobación y Asignación de Unidad**<br>Selección de unidad en Prisma, asignación de operador y fijación de tarifa. | C | **R / A** | C | I |
| **3. Consulta de Sugerencias ECON**<br>Evaluación de unidades candidatas mediante reglas R0-R8 (sin paro, clase exacta). | C | **R / A** | C | I |
| **4. Programación del Traslado**<br>Asignación de geocerca de destino (POI), vehículo flete y fecha/hora de despacho. | I | **R / A** | C | I |
| **5. Habilitación Técnica y Envío a Startrack**<br>Validación de contratos y guardias de mantenimiento previas al despacho. | I | **R / A** | C | I |
| **6. Ejecución y Telemetría en Ruta**<br>Seguimiento GPS del trayecto y detección telemática de arribo a geocerca. | I | **R / A** | I | I |
| **7. Paro Operativo y Diagnóstico Mecánico**<br>Registro de falla en Prisma y emisión de orden de paro que inhabilita traslados. | I | C | **R / A** | I |
| **8. Recepción Física en Obra**<br>Inspección física en sitio y declaración formal de entrega (`receipt`) en ECON. | **R / A** | C | I | I |
| **9. Liquidación Económica Posterior**<br>Auditoría de horas reales trabajadas vs períodos solicitados y conciliación. | C | C | I | **R / A** |

---

## 2. Definiciones de Roles
- **Responsable (R)**: El rol que ejecuta materialmente la actividad o captura el dato en el sistema.
- **Aprueba (A)**: El rol directivo que tiene la autoridad final de decisión y asume la rendición de cuentas.
- **Consultado (C)**: El área que debe ser escuchada antes de tomar la decisión por aportar insumos críticos.
- **Informado (I)**: El área que recibe notificación formal del resultado para fines de coordinación o costeo.

---

## 3. Archivos Relacionados
- **Archivo CSV**: `2-Matriz-de-Responsabilidades-RACI.csv`
- **Libro Excel**: `1-Matriz-de-Mapeo-de-Campos.xlsx` (Pestaña *raci-propuesta*)
