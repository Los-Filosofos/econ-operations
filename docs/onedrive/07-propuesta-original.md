# Propuesta original del usuario

> Fuente: texto adjunto `pasted-text.txt`. Se conserva la propuesta sin corregir sus afirmaciones o ejemplos; solo se agregan estructura Markdown y bloques de código. No es un contrato técnico confirmado de las plataformas.

> El análisis y los ajustes sugeridos están en [08-analisis-propuesta.md](08-analisis-propuesta.md). Ningún fragmento de esta propuesta fue ejecutado durante la conversión.

Para romper la brecha entre el estado administrativo de Prisma y el estado logístico/satelital de Startrack, la solución óptima es un Protocolo de Sincronización Basado en Eventos (Webhooks/API Rest).

A continuación, se detalla la arquitectura del protocolo, la estructura de los payloads esenciales, la implementación técnica en FastAPI y la estrategia de pruebas para asegurar los 20 puntos de viabilidad técnica en el hackathon.

## 1. ¿Qué va a llevar el Protocolo? (Estructura y Payloads)

El protocolo funcionará bajo una arquitectura dirigida por eventos (Event-Driven). Cuando ocurra un cambio en Startrack o Prisma, se disparará un evento hacia nuestro hub intermedio en FastAPI, el cual unificará la semántica.

### A. Evento de Startrack: Actualización de Ubicación/Geocerca

Este payload notifica si la maquinaria entró o salió del proyecto asignado.
```json
{
  "event_id": "evt_st_98765",
  "timestamp": "2026-09-12T11:05:22Z",
  "source": "startrack",
  "event_type": "vehicle.geofence_update",
  "data": {
    "vehicle_id": "CF-03",
    "driver_id": "MOT-014",
    "geofence_id": "GEO-014",
    "geofence_name": "PROY-014 - The Hub - Proyecto Xi - La Unión",
    "status": "INSIDE",
    "horometro": 257748.0
  }
}
```


### B. Evento de Prisma: Cambio de Estado Operativo (Mantenimiento)

Este payload intercepta cuando la Gerencia de Mantenimiento reporta un fallo crítico.
```json
{
  "event_id": "evt_pr_12345",
  "timestamp": "2026-09-12T11:06:00Z",
  "source": "prisma",
  "event_type": "machinery.status_change",
  "data": {
    "activo_id": "CF-03",
    "nuevo_estado": "Obsoleta (mantenimiento correctivo)",
    "motivo": "Emergencia - Falla de sistema hidráulico",
    "solicitud_id": "PROY-003-REQ"
  }
}
```


## 2. Implementación en FastAPI

Este código levanta el servidor intermedio, define los esquemas de validación con Pydantic para evitar datos corruptos (cumpliendo el requerimiento RF-01) y procesa las reglas de negocio para resolver discrepancias de estados (RF-05).
```python
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

app = FastAPI(title="Hub de Operaciones - ECON Integration", version="1.0")

# --- ESQUEMAS DE DATOS (Pydantic) ---
class EventData(BaseModel):
    vehicle_id: Optional[str] = None
    activo_id: Optional[str] = None
    status: Optional[str] = None
    nuevo_estado: Optional[str] = None
    geofence_name: Optional[str] = None
    motivo: Optional[str] = None
    horometro: Optional[float] = None

class ProtocolEvent(BaseModel):
    event_id: str
    timestamp: datetime
    source: str
    event_type: str
    data: EventData

# --- BASE DE DATOS EN MEMORIA (Para simulación del Sandbox) ---
# Estado unificado del activo CF-03
db_estado_unificado = {
    "CF-03": {
        "codigo_activo": "CF-03",
        "prisma_estado": "Ocupada",
        "startrack_estado": "Pendiente",
        "ubicacion_actual": "PLANTA ORIGEN",
        "alerta_mantenimiento": False,
        "indicador_riesgo": "Normal"
    }
}

# --- ENDPOINTS DEL PROTOCOLO ---
@app.post("/api/v1/protocol/webhook", status_code=status.HTTP_202_ACCEPTED)
async def procesar_evento_protocolo(event: ProtocolEvent):
    # Identificar el ID del activo de forma cruzada
    activo_id = event.data.vehicle_id or event.data.activo_id

    if not activo_id or activo_id not in db_estado_unificado:
        raise HTTPException(status_code=404, detail="Activo no registrado en el Sandbox")

    registro = db_estado_unificado[activo_id]

    # REGLA DE NEGOCIO 1: Procesar traslado desde Startrack
    if event.event_type == "vehicle.geofence_update":
        registro["ubicacion_actual"] = event.data.geofence_name
        if event.data.status == "INSIDE":
            registro["startrack_estado"] = "Completada"
            # Si en Prisma está ocupada y en Startrack completada, es consistente (Caso de Uso 02)
            registro["indicador_riesgo"] = "Operación Consistente"

    # REGLA DE NEGOCIO 2: Procesar Alerta de Mantenimiento desde Prisma (Caso de Uso 03)
    elif event.event_type == "machinery.status_change":
        registro["prisma_estado"] = event.data.nuevo_estado
        if "correctivo" in event.data.nuevo_estado.lower():
            registro["alerta_mantenimiento"] = True
            registro["indicador_riesgo"] = "ALERTA: Traslado pendiente con equipo en falla"

            # Aquí se dispararía la alerta al usuario (Requerimiento RF-05)
            return {
                "status": "alert_triggered",
                "message": f"Alerta crítica para {activo_id}: El traslado sigue activo pero el equipo entró en mantenimiento correctivo.",
                "snapshot": registro
            }

    return {"status": "processed", "snapshot": registro}

@app.get("/api/v1/protocol/unified-view/{activo_id}")
async def obtener_vista_unificada(activo_id: str):
    if activo_id not in db_estado_unificado:
        raise HTTPException(status_code=404, detail="Activo no encontrado")
    return db_estado_unificado[activo_id]
```


## 3. Estrategia de Pruebas (Validación del MVP)

Para demostrarle al jurado (especialmente a Rafael Torres, evaluador de arquitectura técnica) que el protocolo funciona en vivo, utilizaremos la suite de pruebas nativa de FastAPI con pytest.

Crea un archivo llamado test_protocol.py:
```python
from fastapi.testclient import TestClient
from main import app  # Asumiendo que tu archivo principal se llama main.py

client = TestClient(app)

def test_caso_uso_02_consistencia_estados():
    """Prueba que el protocolo maneja estados nominalmente distintos pero operacionalmente correctos."""
    payload = {
        "event_id": "evt_st_002",
        "timestamp": "2026-09-12T11:05:22Z",
        "source": "startrack",
        "event_type": "vehicle.geofence_update",
        "data": {
            "vehicle_id": "CF-03",
            "status": "INSIDE",
            "geofence_name": "PROY-002 – Proyecto Beta"
        }
    }
    response = client.post("/api/v1/protocol/webhook", json=payload)
    assert response.status_code == 202
    json_data = response.json()
    assert json_data["snapshot"]["startrack_estado"] == "Completada"
    assert json_data["snapshot"]["indicador_riesgo"] == "Operación Consistente"

def test_caso_uso_03_alerta_mantenimiento():
    """Prueba que el protocolo detecta el riesgo de un traslado programado para un equipo dañado."""
    payload = {
        "event_id": "evt_pr_003",
        "timestamp": "2026-09-12T11:06:00Z",
        "source": "prisma",
        "event_type": "machinery.status_change",
        "data": {
            "activo_id": "CF-03",
            "nuevo_estado": "Obsoleta (mantenimiento correctivo)"
        }
    }
    response = client.post("/api/v1/protocol/webhook", json=payload)
    assert response.status_code == 202
    json_data = response.json()
    assert json_data["status"] == "alert_triggered"
    assert json_data["snapshot"]["alerta_mantenimiento"] is True
    assert "ALERTA" in json_data["snapshot"]["indicador_riesgo"]
```


## 4. Ruta de Implementación en las 24 horas del Hackathon

Para ejecutar esto de forma eficiente en las mesas de trabajo en Antiguo Cuscatlán, sigan este orden de despliegue:
Montar la Estructura: Un desarrollador clona el repositorio, instala FastAPI y uvicorn (pip install fastapi uvicorn pytest httpx), y pega la estructura base.
Mapear el Diccionario: Mientras tanto, el Arquitecto de Datos valida que las llaves del JSON de EventData correspondan exactamente a los campos del Excel (ej. horometro mapeado a las columnas de Startrack).
Correr los Tests locales: Ejecutar pytest test_protocol.py en la terminal. Al ver los checks en verde, garantizan que la lógica de reconciliación de estados funciona antes del congelamiento de código (Code Freeze) del domingo a las 10:00 AM.
Conexión al Frontend (Opcional/Deseable): Desde el Dashboard (Mockup/Streamlit/PowerBI), hagan peticiones HTTP GET al endpoint /api/v1/protocol/unified-view/CF-03 para pintar en la pantalla del jurado los datos unificados en tiempo real durante el Pitch.
¿Deseas que elaboremos el JSON de datos sintéticos completo para inyectar en el Sandbox durante la simulación de la defensa en vivo?
