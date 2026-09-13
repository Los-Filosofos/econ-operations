# Entregable 3: Prototipo Navegable & Guía de Demostración en Vivo
**Hackathon Grupo ECON 2026** · *Equipo: Los Filósofos*

Este documento describe el prototipo funcional desarrollado para resolver la integración entre **Prisma (ERP)** y **Startrack (GPS)**, incluyendo instrucciones de acceso y los pasos para ejecutar la **consulta unificada** (estado y ubicación de un equipo combinando ambas plataformas).

---

## 1. Repositorio Oficial & Enlaces de Acceso
- **Repositorio Git**: [https://github.com/Los-Filosofos/econ-operations](https://github.com/Los-Filosofos/econ-operations)
- **Consola Analítica Unificada**: `http://localhost:8050/` (Dash Mantine + AG Grid + Plotly)
- **API REST & Documentación Swagger**: `http://localhost:8050/docs` (18 endpoints operativos)
- **Tablero de KPIs e Indicadores**: `http://localhost:8050/indicadores?mode=fixture`
- **Traza de Integración**: `http://localhost:8050/integracion?mode=fixture`

---

## 2. Instrucciones de Despliegue Local

### Requisitos Previos
- Python 3.11+ con `uv` instalado.
- Servidor PostgreSQL (opcional en desarrollo; por defecto SQLite en memoria/fichero).

### Pasos de Ejecución
```bash
# 1. Clonar el repositorio oficial
git clone https://github.com/Los-Filosofos/econ-operations.git
cd econ-operations

# 2. Instalar dependencias bloqueadas
uv sync --project apps/api --locked

# 3. Iniciar el servidor único (Dash + FastAPI en puerto 8050)
DATABASE_URL=sqlite:///apps/api/econ.db AUTH_REQUIRED=false uv run --directory apps/api uvicorn app.main:app --host 127.0.0.1 --port 8050
```

---

## 3. Demostración en Vivo: Consulta Unificada
La consulta unificada permite inspeccionar en un solo punto el **estado administrativo (Prisma)** junto con el **estado telemático y de traslado (Startrack)** de cualquier equipo.

### Opción A: A través de la Interfaz Gráfica (Dash Mantine)
1. Abrir el navegador en `http://localhost:8050/maquinaria/cf-03?mode=fixture`.
2. La vista de detalle despliega simultáneamente:
   - **Estado administrativo en Prisma**: `OBSOLETA` (con interpretación de evidencia: revisar antes de continuar).
   - **Mantenimiento**: Sin falla activa ni paro registrado.
   - **Ventana de asignación**: Período 11–14/09 en proyecto activo.
   - **Traslado y ubicación en Startrack**: Seguimiento de traslado, tarea telemática y recepción física.
   - **Trazabilidad de fuentes**: Referencias de integración y origen auditables.

### Opción B: A través de la API REST (Línea de Comandos)
```bash
# 1. Consulta unificada de todos los equipos con identidades combinadas:
curl -s "http://localhost:8050/api/v1/graph?mode=fixture" | jq '.nodes[] | select(.kind=="machine")'

# 2. Traza unificada de 4 etapas para una solicitud:
curl -s "http://localhost:8050/api/v1/integration/nexus:request:46d2573e-08d3-4855-971d-2fbf9564e135?mode=fixture" | jq '{solicitud: .request_label, maquinaria: .equipment_label, etapas: [.stages[] | {etapa: .title, estado: .state}]}'
```

---

## 4. Guion Rápido de Validación para el Jurado
1. **Grafo Operativo (`#/`)**: Explorar la topología con zoom y paneo.
2. **Indicadores & SLAs (`#/indicadores`)**: Visualizar los 8 SLAs sin promedios falsos y las tarjetas por gerencia.
3. **Traza de Integración (`#/integracion`)**: Inspeccionar la cadena Prisma → ECON → Startrack.
4. **Gestión de Traslados (`#/operaciones`)**: Ver los movimientos registrados y probar el botón de *Declarar Recepción*.
5. **Recomendador de Candidatas (`#/solicitudes`)**: Abrir una solicitud pendiente y ver las máquinas elegibles calculadas con las reglas R0-R8.
