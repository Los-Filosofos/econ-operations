# Entregable 3: Prototipo Navegable & Guía de Demostración en Vivo
**Hackathon Grupo ECON 2026** · *Equipo: Los Filósofos*

Este documento describe el prototipo funcional desarrollado para resolver la integración entre **Prisma (ERP)** y **Startrack (GPS)**, incluyendo instrucciones de acceso y los pasos para ejecutar la **consulta unificada** (estado y ubicación de un equipo combinando ambas plataformas).

---

## 1. Repositorio Oficial & Enlaces de Acceso
- **Repositorio Git**: [https://github.com/Los-Filosofos/econ-operations](https://github.com/Los-Filosofos/econ-operations)
- **Frontend SPA Web (Recomendado)**: `http://localhost:5173/` (Vite + Canvas 2D + Chart.js)
- **API REST & Documentación Swagger**: `http://localhost:8050/docs` (18 endpoints operativos)
- **Consola Analítica Unificada**: `http://localhost:8050/` (FastAPI + Dash Mantine)

---

## 2. Instrucciones de Despliegue Local

### Requisitos Previos
- Python 3.11+ con `uv` instalado.
- Node.js 18+ con `npm`.

### Pasos de Ejecución
```bash
# 1. Clonar el repositorio oficial
git clone https://github.com/Los-Filosofos/econ-operations.git
cd econ-operations

# 2. Iniciar el Backend (FastAPI en puerto 8050)
uv run --directory apps/api uvicorn app.main:app --host 127.0.0.1 --port 8050

# 3. En otra terminal, iniciar el Frontend Web (Vite en puerto 5173)
cd frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

---

## 3. Demostración en Vivo: Consulta Unificada
La consulta unificada permite inspeccionar en un solo punto el **estado administrativo (Prisma)** junto con el **estado telemático y de traslado (Startrack)** de cualquier equipo.

### Opción A: A través de la Interfaz Gráfica (SPA Web)
1. Abrir el navegador en `http://localhost:5173/`.
2. En el **Grafo Operativo** (`#/`), hacer click sobre cualquier nodo de maquinaria (ej. `CF-03`).
3. El panel contextual derecho desplegará simultáneamente:
   - **Estado administrativo en Prisma**: `OBSOLETA` / `DISPONIBLE`.
   - **Proyecto y período asignado**: `PROY-014 - The Hub`.
   - **Traslado telemático en Startrack**: Destino `POI-PROY-014`, hora y fecha programada.
   - **Evidencia documental**: Fuente original, entorno sandbox y referencia OpenAPI.
   - **Faltantes u observaciones de seguridad**: Advertencia explícita si la posición GPS pertenece al camión de transporte y no a la máquina.

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
