# Gráficos y diagramas del reto ECON

Edición del 12 de septiembre de 2026. Este documento es el punto de entrada al
dossier visual. Las fuentes originales de `docs/onedrive` se conservan. Los
gráficos usan únicamente la muestra proporcionada; los diagramas distinguen
proceso documental, implementación actual y ampliación propuesta.

## Paquete para revisar

- [Trazabilidad de RF/RNF y entregables](matriz-requisitos-entregables.md).
- [Matriz completa de equivalencias y RACI propuesta](equivalencias-prisma-startrack.md).
- [Diccionario técnico y manual de operación](manual-mapeo-integracion.md).
- [Inventario de campos del modelo ECON](diccionario-modelo-econ.md).
- [Decisiones técnicas, resumen de dos páginas](decisiones-tecnicas.md).
- [Dossier visual en PDF](../output/pdf/ECON-entregables-visuales.pdf).
- [Decisiones técnicas en PDF](../output/pdf/ECON-decisiones-tecnicas.pdf).
- [Diccionario y mapeo completo en PDF](../output/pdf/ECON-diccionario-mapeo-y-manual-integracion.pdf).

El brief pide además una presentación de hasta diez diapositivas con reflexión;
este dossier no se presenta como una presentación terminada. La validación
combinada de un caso Prisma/Startrack sigue limitada por las evidencias disponibles.

## Gráficos con datos suministrados

El script [generar_graficos.py](../scripts/docs/generar_graficos.py) lee la muestra
Prisma sin modificarla. Sus resultados y huellas se conservan en
[el manifiesto](assets/entregables/manifest.json).

Los intervalos representan uso solicitado, no fechas de transporte o entrega.
Los estados de maquinaria son administrativos y no miden utilización ni
disponibilidad técnica. La cobertura corresponde al ejemplo del archivo, no al
estado actual del sandbox ni a toda la flota. Startrack carece de registros
operativos en esa muestra; no se dibuja un cero como si fuera un censo vacío.

![Períodos de uso solicitados](assets/entregables/grafico-periodos-uso.png)

![Estados administrativos de la muestra](assets/entregables/grafico-estados-administrativos.png)

![Cobertura documental por fuente](assets/entregables/grafico-cobertura.png)

## Diagrama 1: recorrido operativo sintetizado

![Solicitud, traslado y recepción](assets/entregables/diagrama-proceso.png)

Síntesis propia del [AS-IS](onedrive/03-as-is.md), [TO-BE](onedrive/03-to-be.md) y
[casos de uso](onedrive/04-casos-de-uso.md), centrada en el alcance del prototipo.
No reemplaza las imágenes originales ni incorpora como implementada la
automatización que propone el TO-BE.

```mermaid
flowchart LR
    P[Proyecto y necesidad en Prisma] --> S[Solicitud de maquinaria]
    S --> A[Aprobación y unidad asignada]
    A --> E[Plan y envío controlado en ECON]
    E --> T[Tarea de traslado Startrack]
    T --> R[Recepción declarada por el proyecto]
    M[Mantenimiento: restricción y liberación] -. revisión .-> A
    G[Observación GPS del activo vinculado] -. evidencia separada .-> R
```

## Diagrama 2: identidad y correspondencias

![Correspondencias entre fuentes](assets/entregables/diagrama-identidad.png)

Modelo conceptual; no es un esquema físico de tablas. Las correspondencias
se revisan por ID y entorno. Las vigencias maestras son una ampliación propuesta;
actualmente el movimiento guarda su mapeo. El GPS puede pertenecer al camión que
transporta la máquina.

```mermaid
flowchart LR
    P[Prisma proyecto UUID] --> C[Correspondencia de destino] --> POI[Startrack poi_id]
    S[Prisma solicitud UUID] --> N[Uno o varios movimientos ECON] --> J[Tarea con job_id confirmado]
    E[Prisma maquinaria UUID] --> V[Vínculo explícito del activo observado] --> G[Startrack vehicle_id]
    O[Prisma operador UUID] --> U[Correspondencia revisada de personas] --> US[Usuarios Startrack asignables]
```

## Diagrama 3: arquitectura implementada

![Arquitectura Python actual](assets/entregables/diagrama-actual.png)

Implementación según [ADR 0004](adr/0004-persistent-transfer-workflow.md). Los
conectores están escritos; la creación autenticada en Startrack sigue pendiente
de validación. El trabajador no arranca automáticamente con el servidor.

```mermaid
flowchart LR
    D[Dash] --> S[Servicios compartidos Python]
    A[FastAPI] --> S
    W[CLI de sincronización] --> S
    S --> N[SDK Prisma: lectura]
    S --> T[SDK Startrack: tareas y seguimiento]
    S --> L[Ledger, eventos y cola transaccional]
    L --> P[PostgreSQL]
```

## Diagrama 4: detección de cambios y discrepancias

![Sincronización propuesta](assets/entregables/diagrama-sincronizacion.png)

Ampliación propuesta. La recepción de webhooks depende del contrato que habilite
cada proveedor. Las consultas de conciliación siguen siendo necesarias. Esta
secuencia no promete reconstruir eventos intermedios si la fuente solo entrega
su estado actual.

```mermaid
flowchart LR
    P[Cambio Prisma] --> I[Evento recibido o cambio detectado por consulta]
    S[Cambio Startrack] --> I
    I --> V[Validar ID, entorno y fecha]
    V --> H[Persistir historia y controlar duplicados]
    H --> C[Comparar con asignación y movimiento]
    C --> R[Actualizar seguimiento o abrir incidencia]
    R --> D[Responsable revisa evidencia y decide]
```

## Diagrama 5: arquitectura objetivo para miles de vehículos

![Arquitectura escalable propuesta](assets/entregables/diagrama-escala.png)

Propuesta, no despliegue. La [arquitectura de flota](arquitectura-escalable-flota.md)
contiene hipótesis de carga, retención, límites de API y pruebas pendientes.

```mermaid
flowchart LR
    P[Prisma y Startrack] --> I[Recepción FastAPI con réplicas]
    I --> K[Kafka gestionado]
    K --> W[Trabajadores paralelos por entidad]
    W --> B[PostgreSQL: operación y estado actual]
    K --> H[Histórico analítico y archivo]
    B --> D[API de lectura y Dash]
    H --> D
```

## RF-06: indicador definido, sin valor inventado

**Tiempo fuera de geocerca sin justificación**, por equipo y período acordado.
Unidad: horas. Cálculo: duración de la unión de intervalos válidos fuera de la
geocerca asignada, dentro del horario en que se exige presencia, excluyendo los
intervalos de salida autorizada o justificada. Unir intervalos evita doble conteo.

Se requieren identidad y vigencia del dispositivo, geocerca y asignación;
eventos fechados y válidos; horario exigible; justificaciones con vigencia y
criterio acordado para interpolar y cortar intervalos. Los huecos de señal
permanecen sin clasificar. Reportar horas evaluables y desconocidas junto al
indicador. Si faltan esos datos, el resultado es **no evaluable**, no cero.

Decisión: Logística y Técnica de Proyectos revisan el destino y la autorización;
Mantenimiento participa cuando hay una restricción. Estar fuera de geocerca no
equivale automáticamente a tiempo muerto, pérdida económica o uso indebido.

Fuente del requisito: [RF-06 del brief](onedrive/02-brief-del-reto.md#7-requerimientos).
Para otros indicadores consultar [analítica de decisiones](analitica-decisiones.md).

## Reproducción y revisión

Desde la raíz, sin cambiar el lockfile de la aplicación:

```powershell
uv run --no-project --with matplotlib python scripts/docs/generar_graficos.py
uv run --no-project --with matplotlib --with reportlab --with pypdf --with markdown-it-py python scripts/docs/generar_dossier.py
```

Los PNG/SVG y PDFs se generan localmente. Antes de entregar una nueva edición,
renderizar los PDFs, revisar páginas y verificar la matriz contra las fuentes.
La generación no consulta ni modifica Prisma o Startrack.
