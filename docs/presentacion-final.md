# Presentación Final: ECON Operations Hub
**Reto de Integración Operativa · Hackathon Grupo ECON**
*Equipo: Los Filósofos | Entrega: 13 de Septiembre de 2026*

---

## 🎙️ El Pitch Ejecutivo (3 minutos)
*Diseñado para convencer tanto al Director Financiero/Operaciones (Non-Tech) como al Arquitecto de Software/CTO (Tech).*

### Gancho (El dolor real):
> «Imaginen esto: en el ERP **Prisma**, un cargador frontal aparece como "OCUPADO" y asignado a un proyecto en La Unión. Pero en la plataforma GPS **Startrack**, el motorista completó la tarea hace dos días... y en la obra real, la máquina está parada en un rincón porque nadie confirmó la entrega, o peor: tiene una falla activa de motor que nadie reportó al sistema central.
> 
> Hoy en Grupo ECON, la Gerencia de Proyectos, Logística y Mantenimiento operan como tres islas ciegas. Cruzar una llamada para saber *"dónde diablos está la excavadora y si está produciendo"* toma horas de WhatsApp, suposiciones y fricción humana. El resultado: millones de dólares en maquinaria pesada subutilizada, disputas de horas-máquina y decisiones a ciegas.»

### La Solución (ECON Hub):
> «No venimos a reemplazar Prisma ni a reprogramar Startrack. Construimos **ECON Operations Hub**: una capa de interoperabilidad inteligente y gobernanza en tiempo real que **se come los datos de ambos mundos, los normaliza sin inventar verdades y los pone a trabajar juntos**.
> 
> Mientras otros sistemas cometen el error fatal de asumir que *"una visita GPS significa que la máquina ya está trabajando"* o que *"velocidad cero es tiempo muerto"*, ECON implementa un modelo estricto de evidencia:
> 1. **Grafo de Operaciones Unificado**: Ves en un solo lienzo interactivo dónde está asignada cada máquina, su estado administrativo en Prisma, la telemetría en Startrack y su constancia física de recepción en obra.
> 2. **Sugerencias Inteligentes de Asignación**: Cuando una obra pide maquinaria, el sistema evalúa compatibilidad de clase exacta, disponibilidad administrativa, ausencia de paros mecánicos y proximidad, recomendando la mejor unidad sin tocar la base de datos de origen a ciegas.
> 3. **8 Fichas de SLA y Control Operativo**: Tiempos de aprobación, detección de asignaciones vencidas, y traslados finalizados sin recepción formal en obra. Sin promedios engañosos: hechos por fila con responsable claro (RACI).»

### El Cierre de Negocio:
> «Para el equipo técnico: son 18 endpoints REST, un modelo determinista sin dependencias pesadas, arquitectura desacoplada, 616 pruebas automatizadas aprobadas y despliegue inmediato.
> Para la gerencia: visibilidad 100% auditable del activo más costoso de la empresa, cero horas perdidas en disputas y trazabilidad total desde que el ingeniero pide la máquina hasta que firma la recepción en el proyecto. 
> 
> **ECON Hub no es un parche: es el sistema nervioso operativo que Grupo ECON necesitaba.**»

---

## 📊 Estructura de Diapositivas (10 Slides Oficiales)

### Diapositiva 1: Portada y Visión
- **Título**: ECON Operations Hub — Trazabilidad, Gobernanza e Interoperabilidad Operativa
- **Subtítulo**: Conectando Prisma (ERP) y Startrack (Telemetría) en una única fuente de verdad
- **Equipo**: Los Filósofos (Hackathon Grupo ECON 2026)
- **Mensaje Clave**: De islas de información desconectadas a una operación sincronizada y auditable en tiempo real.

---

### Diapositiva 2: El Problema (Tres Gerencias, Cero Sincronía)
- **Mantenimiento**: Registra fallas y paros en Prisma, pero Logística sigue programando traslados sobre unidades dañadas.
- **Logística y Equipos**: Gestiona solicitudes y despachos en hojas o llamadas; desconoce si el transportista llegó realmente a la obra.
- **Técnica de Proyectos**: Pide equipos que tardan días en llegar; una vez en el sitio, nadie registra formalmente la recepción ni el fin de uso.
- **Impacto**: Costos ocultos de fletes innecesarios, máquinas paradas y falta de métricas confiables de utilización.

---

### Diapositiva 3: La Solución — ECON Operations Hub
- **Cero reemplazos destructivos**: Prisma sigue siendo el ERP financiero; Startrack sigue siendo el proveedor telemático.
- **Middleware inteligente de normalización**:
  - Homologa identidades (UUIDs vs Remote IDs).
  - Gestiona el ciclo de vida del traslado con un Libro Mayor inmutable (*Operations Ledger*).
  - Separa estrictamente hechos administrativos de observaciones físicas (GPS ≠ Disponibilidad, Tarea completada ≠ Recepción).

---

### Diapositiva 4: Arquitectura del Sistema y Flujo de Datos
- **Diagrama de Componentes**:
  - *Capa de Ingesta*: Conectores desacoplados para Nexus/Prisma (OpenAPI) y Startrack (REST API).
  - *Capa de Dominio & Ledger*: Modelo unificado ECON (SQLModel + Alembic + SQLite/PostgreSQL) con control de concurrencia y roles (RACI).
  - *Capa de Entrega*: API REST documentada con OpenAPI/Swagger (18 endpoints) + Consola Analítica Unificada (Dash Mantine + AG Grid Community + Plotly).
- **Flujo de 4 Etapas**:
  1. Prisma Entrega (Solicitud aprobada).
  2. ECON Normaliza (Validación de reglas R0-R8 y preparación del plan).
  3. Startrack Recibe (Despacho telemático con POI y conductor).
  4. Startrack Devuelve & Proyecto Recibe (Telemetría + Firma manual de recepción).

---

### Diapositiva 5: Dónde Vive Cada Estado (Desacoplamiento Semántico)
- **Estado Administrativo** (`DISPONIBLE`, `OCUPADA`, `OBSOLETA`): Vive en **Prisma**.
- **Estado de Tarea y Movimiento** (`draft`, `queued`, `sending`, `sent`): Vive en **ECON Hub**.
- **Estado Telemático en Ruta** (`en camino`, `en geocerca`): Vive en **Startrack**.
- **Estado de Mantenimiento** (`falla activa`, `paro operativo`): Vive en **Prisma Mantenimiento**.
- **Estado de Entrega Física** (`recepción declarada`): Vive en **ECON Hub** avalado por el Ingeniero de Proyecto.
- *Principio clave*: "OCUPADA" y "COMPLETADA" no compiten; describen dimensiones distintas de la realidad operativa.

---

### Diapositiva 6: Matriz de Mapeo de Campos e Inconsistencias Resueltas
- **Campos Mapeados Directos**: Proyecto, Maquinaria, Tipo de Equipo, Fechas de Uso.
- **Campos Transformados**:
  - `RequestRecord.id` → Embebido en `description` de Startrack para asegurar trazabilidad bidireccional.
  - Formato de fechas: ISO 8601 UTC en ECON ↔ YYYY-MM-DD HH:mm:ss local en Startrack.
- **Campos Explícitamente Excluidos (Fuera de Alcance)**:
  - *Ventanas horarias y plazo límite*: No existen en el contrato público de Startrack (`/api/job`).
  - *Tarifas por hora*: Datos financieros confidenciales de Prisma que no deben exponerse al motorista.
  - *Presencia GPS del teléfono del transportista*: No acredita ubicación de la excavadora cuando el flete termina.

---

### Diapositiva 7: Matriz de Responsabilidades (RACI Operativa)
- **Gerencia Técnica de Proyectos**:
  - Responsable (R) y Aprobador (A) de: Solicitud de equipo y Recepción física en obra.
- **Gerencia de Logística y Equipos**:
  - Responsable (R) y Aprobador (A) de: Asignación de unidad en Prisma, Programación de traslado y Despacho en Startrack.
- **Gerencia de Mantenimiento**:
  - Responsable (R) y Aprobador (A) de: Diagnóstico de fallas y Orden de Paro operativo (bloquea traslados en ECON).
- **Control de Costos**:
  - Informado (I) y Consultor (C) en todo el ciclo; Responsable (R) de la liquidación económica posterior.

---

### Diapositiva 8: Demostración en Vivo del Prototipo
- **Grafo Operativo**: Navegación en Canvas 2D con visualización de nodos, aristas dirigidas y panel contextual de evidencia.
- **Dashboard de SLAs y KPIs**: 8 fichas operativas con métricas por fila (ej. Tiempo de aprobación de 42s, detección de asignación vencida al corte).
- **Recomendador de Candidatas**: Evaluación en vivo de solicitudes pendientes con reglas deterministas de disponibilidad y ausencia de paro.
- **Registro de Traslado y Recepción**: Despacho simulado y firma digital de recepción en destino.

---

### Diapositiva 9: Valor Generado para Grupo ECON
- **Eficiencia Operativa**: Reducción drástica del tiempo de coordinación entre obra y patio central.
- **Gobernanza y Cero Falsos Datos**: Nadie puede "adivinar" que una máquina llegó solo porque un celular pasó cerca de la geocerca.
- **Ahorro Financiero**: Eliminación de fletes a maquinaria con fallas no reportadas y control de máquinas con período de uso vencido.
- **Extensibilidad**: Preparado para entornos de producción mediante Docker, PostgreSQL y sincronización programable.

---

### Diapositiva 10: Reflexión y Aprendizaje del Equipo
- **Lección 1 (Semántica sobre Código)**: El mayor reto de la integración no fue conectar dos APIs, sino reconciliar dos vocabularios de negocio radicalmente distintos.
- **Lección 2 (La Tentación de "Completar Vacíos")**: Aprendimos que en sistemas industriales, inventar un dato faltante o promediar sin evidencia es peor que reportar "No Evaluable". La verdad documental es la base de la confianza gerencial.
- **Conclusión**: Construimos una solución sólida, testeada con 616 pruebas automáticas y lista para escalar con la visión de futuro de Grupo ECON.
