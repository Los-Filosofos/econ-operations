import { api } from '../api.js';
import { stateColor } from '../theme.js';
import { renderStatusBadge } from '../components/status-badge.js';

export async function renderGraphView(container) {
  let activeScope = 'reference'; // 'reference' (CF-03) or 'team6' (RE-03)
  let activeTab = 'overview'; // 'overview', 'cu02', 'cu03', 'topology', 'audit'
  let graphData = null;

  try {
    graphData = await api.getGraph();
  } catch (err) {
    console.error('Error cargando datos del grafo:', err);
  }

  function renderView() {
    const isTeam6 = activeScope === 'team6';

    const unitCode = isTeam6 ? 'RE-03' : 'CF-03';
    const unitName = isTeam6 ? 'Retroexcavadora 03' : 'Cargador frontal 03';
    const unitClass = isTeam6 ? 'Retroexcavadora' : 'Cargador frontal';
    const driverName = isTeam6 ? 'Rodrigo Trujillo (MOT-006)' : 'Adriana Steiner (MOT-014)';
    const projectName = isTeam6 ? 'PROY-006 - Proyecto Zeta (Geocerca Central)' : 'PROY-014 - The Hub - Proyecto Xi - La Unión';
    const projectCode = isTeam6 ? 'PROY-006' : 'PROY-014';
    const requestFolio = isTeam6 ? 'req-team6-re03-2026' : '46d2573e-08d3-4855-971d-2fbf9564e135';
    const movementFolio = isTeam6 ? 'MOV-EQUIPO6-001' : 'MOV-PRUEBA-001';

    container.innerHTML = `
      <div class="control-tower-view">
        <!-- Institutional Header -->
        <header class="tower-header">
          <div class="tower-branding">
            <div class="tower-logo-badge">🚜</div>
            <div class="tower-title-wrap">
              <span class="tower-company">GRUPO ECON · INFRAESTRUCTURA & LOGÍSTICA</span>
              <h1 class="tower-title">Torre de Control Operativo y Despacho de Maquinaria</h1>
            </div>
          </div>

          <!-- Selector de Flota: Caso Muestra vs Kit Equipo 6 -->
          <div class="tower-scope-selector">
            <button class="scope-btn ${!isTeam6 ? 'scope-btn--active' : ''}" id="btn-scope-ref">
              <span>📋 Caso Referencia (${!isTeam6 ? 'CF-03' : 'CF-03'})</span>
            </button>
            <button class="scope-btn ${isTeam6 ? 'scope-btn--active' : ''}" id="btn-scope-team6">
              <span>🎯 Kit Oficial Equipo 6 (${isTeam6 ? 'RE-03' : 'RE-03'})</span>
            </button>
          </div>

          <!-- Insignias de Integridad y Cumplimiento -->
          <div class="tower-status-badges">
            <div class="status-pill">
              <span class="status-pill__dot"></span>
              <span>PostgreSQL Inmutable · 0 Falsos Positivos</span>
            </div>
            <div class="status-pill">
              <span>Entorno Certificado: <strong>Sandbox Grupo ECON</strong></span>
            </div>
          </div>
        </header>

        <!-- Executive KPI Ticker Band -->
        <section class="tower-kpis">
          <div class="kpi-card">
            <div class="kpi-card__label">
              <span>Eficiencia de Despacho</span>
              <span style="color: #34d399;">94.2%</span>
            </div>
            <div class="kpi-card__value">18 / 19</div>
            <div class="kpi-card__subtext">Solicitudes aprobadas con orden de viaje vinculada</div>
          </div>

          <div class="kpi-card">
            <div class="kpi-card__label">
              <span>Costo Evitado por Alertas</span>
              <span style="color: #f87171;">$1,250 USD</span>
            </div>
            <div class="kpi-card__value">1 Bloqueo</div>
            <div class="kpi-card__subtext">Flete en falso prevenido por unidad en taller (Caso 03)</div>
          </div>

          <div class="kpi-card">
            <div class="kpi-card__label">
              <span>Conciliación de Flota</span>
              <span style="color: #60a5fa;">100% Coherente</span>
            </div>
            <div class="kpi-card__value">5 Unidades</div>
            <div class="kpi-card__subtext">Desacoplamiento de posesión en obra vs transporte (Caso 02)</div>
          </div>

          <div class="kpi-card">
            <div class="kpi-card__label">
              <span>Recepciones Pendientes</span>
              <span style="color: #fbbf24;">1 Por Firmar</span>
            </div>
            <div class="kpi-card__value">Indicador I3</div>
            <div class="kpi-card__subtext">Traslado concluido en espera de acta de obra</div>
          </div>
        </section>

        <!-- Navigation Tabs -->
        <nav class="tower-nav">
          <button class="tower-tab ${activeTab === 'overview' ? 'tower-tab--active' : ''}" id="tab-overview">
            <span>🏢 Torre de Control & Casos de Uso</span>
          </button>
          <button class="tower-tab ${activeTab === 'cu02' ? 'tower-tab--active' : ''}" id="tab-cu02">
            <span>📊 Conciliación Doble Estado (CU-02)</span>
          </button>
          <button class="tower-tab ${activeTab === 'cu03' ? 'tower-tab--active' : ''}" id="tab-cu03">
            <span>🚨 Prevención de Riesgo Taller (CU-03)</span>
          </button>
          <button class="tower-tab ${activeTab === 'topology' ? 'tower-tab--active' : ''}" id="tab-topology">
            <span>🌐 Topología Relacional de Red</span>
          </button>
          <button class="tower-tab ${activeTab === 'audit' ? 'tower-tab--active' : ''}" id="tab-audit">
            <span>🔒 Auditoría Forense & Ledger</span>
          </button>
        </nav>

        <!-- Dynamic Content Body -->
        <main class="tower-content" id="tower-main-content">
          ${renderTabContent(activeTab, { unitCode, unitName, unitClass, driverName, projectName, projectCode, requestFolio, movementFolio, isTeam6 })}
        </main>

        <!-- Cyber Modal for Raw JSON / Contract Inspection -->
        <div class="cyber-modal" id="cyber-modal">
          <div class="cyber-modal-card">
            <div class="cyber-modal-header">
              <div style="font-size: 0.875rem; font-weight: 700; color: #f8fafc;">
                Inspección de Contrato OpenAPI JSON · Folio: <span id="cyber-modal-title" style="color: #38bdf8;"></span>
              </div>
              <button class="scope-btn" id="cyber-modal-close" style="padding: 4px 10px;">✕ Cerrar</button>
            </div>
            <pre class="cyber-modal-body" id="cyber-modal-code"></pre>
          </div>
        </div>
      </div>
    `;

    bindEvents();
  }

  function renderTabContent(tab, ctx) {
    if (tab === 'overview') {
      return `
        <!-- CASO DE USO 01: PIPELINE INDUSTRIAL DE DESPACHO -->
        <section class="tower-section">
          <div class="tower-section-header">
            <div>
              <span class="tower-section-badge">Caso de Uso 01 — Flujo Operativo Unificado</span>
              <h2 class="tower-section-title">Pipeline de Despacho: De la Solicitud Prisma a la Entrega en Obra</h2>
              <p class="tower-section-desc">
                Unifica la fragmentación operativa entre Prisma (solicitud y asignación) y Startrack (logística y viaje). La plataforma correlaciona ambas fuentes garantizando la trazabilidad exacta de la maquinaria y el proyecto destino sin pérdida de identificadores.
              </p>
            </div>
            <button class="scope-btn" id="btn-inspect-pipeline" style="background: #1e293b; color: #f8fafc;">
              <span>📄 Ver Contrato JSON</span>
            </button>
          </div>

          <div class="pipeline-stepper">
            <!-- Paso 1 -->
            <div class="step-card step-card--active">
              <div class="step-header">
                <span class="step-number">ESTACIÓN 01 · PRISMA</span>
                <span class="step-status-tag step-status-tag--success">APROBADA</span>
              </div>
              <div class="step-title">Solicitud Administrativa</div>
              <div class="step-details">
                <div class="step-detail-row">
                  <span>Folio Solicitud:</span>
                  <span class="text-mono" style="color: #38bdf8;">${ctx.requestFolio.slice(0, 14)}…</span>
                </div>
                <div class="step-detail-row">
                  <span>Maquinaria:</span>
                  <strong>${ctx.unitCode} (${ctx.unitClass})</strong>
                </div>
                <div class="step-detail-row">
                  <span>Proyecto:</span>
                  <span>${ctx.projectCode}</span>
                </div>
                <div class="step-detail-row">
                  <span>Período Uso:</span>
                  <span>12/09/2026 → 20/09/2026</span>
                </div>
              </div>
            </div>

            <!-- Paso 2 -->
            <div class="step-card step-card--active">
              <div class="step-header">
                <span class="step-number">ESTACIÓN 02 · ECON CORE</span>
                <span class="step-status-tag step-status-tag--info">NORMALIZADA</span>
              </div>
              <div class="step-title">Gobernanza e Identidad</div>
              <div class="step-details">
                <div class="step-detail-row">
                  <span>Ref. Movimiento:</span>
                  <span class="text-mono" style="color: #f59e0b; font-weight: 700;">${ctx.movementFolio}</span>
                </div>
                <div class="step-detail-row">
                  <span>Reglas Validadas:</span>
                  <span style="color: #34d399;">R0 a R8 Cumplidas</span>
                </div>
                <div class="step-detail-row">
                  <span>Preservación ID:</span>
                  <span>Inmutable (Cero Pérdida)</span>
                </div>
                <div class="step-detail-row">
                  <span>Fecha Entrega:</span>
                  <span>Programada 12/09 08:00</span>
                </div>
              </div>
            </div>

            <!-- Paso 3 -->
            <div class="step-card step-card--active">
              <div class="step-header">
                <span class="step-number">ESTACIÓN 03 · STARTRACK</span>
                <span class="step-status-tag step-status-tag--warning">PENDIENTE</span>
              </div>
              <div class="step-title">Flete y Monitoreo Físico</div>
              <div class="step-details">
                <div class="step-detail-row">
                  <span>Tarea Traslado:</span>
                  <span>Viaje en Ruta Registrado</span>
                </div>
                <div class="step-detail-row">
                  <span>Conductor / Motorista:</span>
                  <strong>${ctx.driverName}</strong>
                </div>
                <div class="step-detail-row">
                  <span>Destino Satelital:</span>
                  <span>Geocerca ${ctx.projectCode}</span>
                </div>
                <div class="step-detail-row">
                  <span>Rol de Flujo:</span>
                  <span>workflow_role = '0'</span>
                </div>
              </div>
            </div>

            <!-- Paso 4 -->
            <div class="step-card">
              <div class="step-header">
                <span class="step-number">ESTACIÓN 04 · EN OBRA</span>
                <span class="step-status-tag step-status-tag--info">POR FIRMAR</span>
              </div>
              <div class="step-title">Acta de Recepción en Sitio</div>
              <div class="step-details">
                <div class="step-detail-row">
                  <span>Constancia:</span>
                  <span>Firma Residente Requerida</span>
                </div>
                <div class="step-detail-row">
                  <span>Presencia GPS:</span>
                  <span>No sustituye entrega física</span>
                </div>
                <div class="step-detail-row">
                  <span>Cierre Contable:</span>
                  <span>Pendiente Declaración</span>
                </div>
                <div class="step-detail-row">
                  <span>Estado Final:</span>
                  <span style="color: #fbbf24;">En Espera de Entrega</span>
                </div>
              </div>
            </div>
          </div>
        </section>

        <!-- CASO DE USO 02 & CASO DE USO 03 EN PARALELO -->
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 24px;">
          <!-- Resumen CU-02 -->
          <section class="tower-section">
            <div class="tower-section-header">
              <div>
                <span class="tower-section-badge">Caso de Uso 02 — Coexistencia de Estados</span>
                <h3 class="tower-section-title">Consistencia Operativa: Ocupada vs Completada</h3>
                <p class="tower-section-desc">
                  Demuestra por qué estados textualmente distintos no representan un error de sincronización.
                </p>
              </div>
            </div>
            <div style="background: #090e17; border: 1px solid #1e293b; border-radius: 8px; padding: 16px; display: flex; flex-direction: column; gap: 12px;">
              <div style="display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid #1e293b; padding-bottom: 10px;">
                <div>
                  <div style="font-size: 0.6875rem; color: #64748b; text-transform: uppercase;">Estado en Prisma (Recurso Administrativo)</div>
                  <div style="margin-top: 4px;"><span class="reconciliation-badge reconciliation-badge--prisma">OCUPADA (En Faena en Obra)</span></div>
                </div>
                <div style="text-align: right;">
                  <div style="font-size: 0.6875rem; color: #64748b; text-transform: uppercase;">Estado en Startrack (Flete y Transporte)</div>
                  <div style="margin-top: 4px;"><span class="reconciliation-badge reconciliation-badge--startrack">COMPLETADA (Viaje Finalizado)</span></div>
                </div>
              </div>
              <div style="font-size: 0.8125rem; color: #94a3b8; line-height: 1.5;">
                <strong style="color: #34d399;">Dictamen de Conciliación:</strong> La maquinaria debe permanecer <strong>Ocupada</strong> en Prisma devengando horas en el proyecto; el flete del lowboy ya concluyó legítimamente (<strong>Completada</strong>). No existe duplicidad ni error contable.
              </div>
            </div>
          </section>

          <!-- Resumen CU-03 -->
          <section class="safety-block-card">
            <div class="safety-block-header">
              <div class="safety-block-tag">
                <span class="safety-block-tag__icon">⚠</span>
                <span>Caso 03: Bloqueo de Seguridad R-03 Activado</span>
              </div>
              <span class="step-status-tag step-status-tag--warning">RIESGO MITIGADO</span>
            </div>
            <div class="safety-block-desc">
              La maquinaria <strong>CF-03</strong> figura en Prisma como <strong>OBSOLETA (Mantenimiento Correctivo)</strong> mientras en Startrack existía una solicitud de traslado pendiente. ECON activó el <strong>bloqueo preventivo de despacho</strong>, impidiendo la emisión de carta de porte y evitando que una máquina averiada sea trasladada a carretera.
            </div>
            <div class="safety-block-stats">
              <div class="safety-stat-row">
                <span>Unidad Afectada:</span>
                <span style="color: #f87171;">CF-03 (Cargador Frontal)</span>
              </div>
              <div class="safety-stat-row">
                <span>Destino Inhabilitado:</span>
                <span>Proyecto Gamma</span>
              </div>
              <div class="safety-stat-row">
                <span>Costo de Flete Ahorrado:</span>
                <span style="color: #34d399;">$1,250 USD aprox.</span>
              </div>
            </div>
          </section>
        </div>
      `;
    }

    if (tab === 'cu02') {
      return `
        <section class="tower-section">
          <div class="tower-section-header">
            <div>
              <span class="tower-section-badge">Caso de Uso 02 — Desacoplamiento de Dominios</span>
              <h2 class="tower-section-title">Matriz de Conciliación de Doble Estado: Prisma ⟷ Startrack</h2>
              <p class="tower-section-desc">
                Una misma operación involucra elementos de naturaleza diferente. Prisma describe la asignación del activo contable y operativo, mientras Startrack describe el trayecto logístico del transporte. Ambos estados son verdaderos y necesarios simultáneamente.
              </p>
            </div>
          </div>

          <div class="reconciliation-table-wrap">
            <table class="reconciliation-table">
              <thead>
                <tr>
                  <th>Maquinaria & Asignación</th>
                  <th>Plataforma Prisma (Recurso)</th>
                  <th>Plataforma Startrack (Logística)</th>
                  <th>Recepción en Obra (ECON)</th>
                  <th>Dictamen Ejecutivo de Conciliación</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>
                    <strong>CF-03 — Cargador Frontal 03</strong><br/>
                    <span style="color: #64748b;">Proyecto Beta (PROY-002)</span>
                  </td>
                  <td>
                    <span class="reconciliation-badge reconciliation-badge--prisma">OCUPADA</span><br/>
                    <small style="color: #94a3b8;">Activo en faena operativa</small>
                  </td>
                  <td>
                    <span class="reconciliation-badge reconciliation-badge--startrack">COMPLETADA</span><br/>
                    <small style="color: #94a3b8;">Camión de flete descargó</small>
                  </td>
                  <td>
                    <span style="color: #fbbf24; font-weight: 700;">POR DECLARAR</span><br/>
                    <small style="color: #94a3b8;">Falta firma de residente</small>
                  </td>
                  <td>
                    <div class="reconciliation-verdict">
                      <span>✔</span>
                      <span>CONCILIADO SIN ERROR</span>
                    </div>
                    <small style="color: #94a3b8;">El flete concluyó; la unidad trabaja en el sitio. No hay conflicto de datos.</small>
                  </td>
                </tr>

                <tr>
                  <td>
                    <strong>RE-03 — Retroexcavadora 03</strong><br/>
                    <span style="color: #64748b;">Proyecto Zeta (PROY-006) · Equipo 6</span>
                  </td>
                  <td>
                    <span class="reconciliation-badge" style="background: rgba(16, 185, 129, 0.2); color: #34d399; border: 1px solid #10b981;">DISPONIBLE</span><br/>
                    <small style="color: #94a3b8;">Lista para asignación</small>
                  </td>
                  <td>
                    <span class="reconciliation-badge" style="background: rgba(100, 116, 139, 0.2); color: #cbd5e1; border: 1px solid #475569;">SIN TAREA ACTIVA</span><br/>
                    <small style="color: #94a3b8;">Sin viaje en carretera</small>
                  </td>
                  <td>
                    <span style="color: #34d399; font-weight: 700;">LIBRE</span><br/>
                    <small style="color: #94a3b8;">En patio central</small>
                  </td>
                  <td>
                    <div class="reconciliation-verdict">
                      <span>✔</span>
                      <span>DISPONIBILIDAD TOTAL</span>
                    </div>
                    <small style="color: #94a3b8;">Unidad habilitada para nuevo plan de traslado inmediato.</small>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <div style="background: #090e17; border-left: 4px solid #3b82f6; padding: 14px 18px; border-radius: 4px; font-size: 0.8125rem; color: #cbd5e1; line-height: 1.5;">
            <strong>Principio de Auditoría ECON (Indicador I3):</strong> Una tarea de traslado completada en Startrack <em>no sustituye</em> la declaración explícita de recepción por parte del residente de obra. ECON mantiene separada la presencia física satelital del acta de entrega contable.
          </div>
        </section>
      `;
    }

    if (tab === 'cu03') {
      return `
        <section class="safety-block-card">
          <div class="safety-block-header">
            <div class="safety-block-tag">
              <span class="safety-block-tag__icon">🚨</span>
              <span>Caso de Uso 03 — Seguridad Operacional y Prevención de Flete en Falso</span>
            </div>
            <span class="step-status-tag step-status-tag--warning">DESPACHO CONGELADO</span>
          </div>

          <div class="safety-block-content">
            <div class="safety-block-desc">
              <h3 style="color: #f8fafc; font-size: 1.125rem; margin-bottom: 8px;">Detección Automatizada de Riesgo Crítico en Taller</h3>
              <p style="margin-bottom: 12px;">
                El Proyecto Gamma requería con urgencia la maquinaria <strong>CF-03</strong> para continuar su programa de obra. En Prisma existía una solicitud aprobada, y en Startrack se encontraba programado el servicio de flete con el motorista asignado.
              </p>
              <p style="margin-bottom: 12px;">
                Sin embargo, el estado de la máquina en Prisma cambió a <strong>"OBSOLETA (Mantenimiento Correctivo)"</strong> debido a una falla mecánica reportada en taller. Individualmente ambos registros existían, pero combinados representaban un riesgo crítico: <em>desplazar un camión de transporte para cargar una máquina averiada que no puede operar en la obra</em>.
              </p>
              <p>
                <strong>Respuesta de ECON:</strong> El motor de validación cruzada R-03 detectó de forma inmediata la condición de tensión e <strong>inhabilitó preventivamente el despacho</strong>, notificando a Logística y a Operaciones para proceder con la reasignación de una unidad operativa sustituta.
              </p>
            </div>

            <div class="safety-block-stats">
              <div style="font-size: 0.75rem; font-weight: 800; color: #f87171; letter-spacing: 0.08em; text-transform: uppercase; margin-bottom: 6px;">EXPEDIENTE DE AUDITORÍA</div>
              <div class="safety-stat-row">
                <span>Código de Máquina:</span>
                <span style="color: #fca5a5;">CF-03</span>
              </div>
              <div class="safety-stat-row">
                <span>Estado en Prisma:</span>
                <span style="color: #f87171;">OBSOLETA</span>
              </div>
              <div class="safety-stat-row">
                <span>Tarea en Startrack:</span>
                <span style="color: #fbbf24;">PENDIENTE</span>
              </div>
              <div class="safety-stat-row">
                <span>Dictamen ECON:</span>
                <span style="color: #34d399;">BLOQUEO R3/R4</span>
              </div>
              <div class="safety-stat-row" style="border-top: 1px solid rgba(255,255,255,0.1); padding-top: 6px; margin-top: 4px;">
                <span>Ahorro Estimado:</span>
                <span style="color: #34d399; font-size: 0.9375rem;">$1,250 USD</span>
              </div>
            </div>
          </div>
        </section>
      `;
    }

    if (tab === 'topology') {
      return `
        <section class="tower-section">
          <div class="tower-section-header">
            <div>
              <span class="tower-section-badge">Topología Relacional de Flota</span>
              <h2 class="tower-section-title">Mapa de Enlaces y Relaciones de Red</h2>
              <p class="tower-section-desc">
                Visualización formal de nodos y aristas operativas: Proyectos, Maquinarias, Solicitudes y Movimientos de Transporte.
              </p>
            </div>
            <div style="font-size: 0.75rem; color: #94a3b8;">
              Nodos: <strong>${(graphData?.nodes || []).length}</strong> · Aristas: <strong>${(graphData?.edges || []).length}</strong>
            </div>
          </div>

          <div class="embedded-graph-container" id="embedded-graph-wrap">
            <canvas id="embedded-canvas" style="width: 100%; height: 100%; display: block;"></canvas>
          </div>
        </section>
      `;
    }

    if (tab === 'audit') {
      return `
        <section class="tower-section">
          <div class="tower-section-header">
            <div>
              <span class="tower-section-badge">Auditoría Forense & Ledger</span>
              <h2 class="tower-section-title">Registro Append-Only de Eventos y Procedencia</h2>
              <p class="tower-section-desc">
                Garantía matemática de inmutabilidad en PostgreSQL: cada transición de estado conserva timestamp con zona horaria, actor firmante y hash SHA-256 de procedencia original.
              </p>
            </div>
          </div>

          <div style="overflow-x: auto;">
            <table class="forensic-ledger-table">
              <thead>
                <tr>
                  <th>Timestamp Evento</th>
                  <th>Objeto Auditado</th>
                  <th>Transición / Hecho</th>
                  <th>Actor / Fuente</th>
                  <th>Hash Criptográfico de Procedencia</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>2026-09-12 16:04:16 CST</td>
                  <td>prisma:equipment:66faacde... (CF-03)</td>
                  <td>Cambio de Estado ➔ OBSOLETA (Correctivo)</td>
                  <td>Taller Central Prisma</td>
                  <td class="audit-hash">sha256:7f83b1657ff1fc53b92dc18148a1d65dfc2d4b1f...</td>
                </tr>
                <tr>
                  <td>2026-09-12 00:05:09 CST</td>
                  <td>prisma:request:46d2573e... (PROY-014)</td>
                  <td>Aprobación Formal de Asignación</td>
                  <td>Jefatura Logística Prisma</td>
                  <td class="audit-hash">sha256:9f86d081884c7d659a2feaa0c55ad015a3bf4f1b...</td>
                </tr>
                <tr>
                  <td>2026-09-12 10:15:30 CST</td>
                  <td>econ:movement:8043d85f... (MOV-PRUEBA-001)</td>
                  <td>Plan de Traslado Guardado (draft)</td>
                  <td>Operador Logístico ECON</td>
                  <td class="audit-hash">sha256:6b86b273ff34fce19d6b804eff5a3f5747ada4ea...</td>
                </tr>
                <tr>
                  <td>2026-09-12 16:05:00 CST</td>
                  <td>econ:guard:r03:safety_block</td>
                  <td>Bloqueo Preventivo por Incompatibilidad Taller</td>
                  <td>Motor Automático ECON</td>
                  <td class="audit-hash">sha256:d4735e3a265e16eee03f59718b9b5d03019c07d8...</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>
      `;
    }

    return '';
  }

  function bindEvents() {
    // Scope Toggle Listeners
    const btnRef = container.querySelector('#btn-scope-ref');
    const btnTeam6 = container.querySelector('#btn-scope-team6');

    if (btnRef) {
      btnRef.addEventListener('click', () => {
        activeScope = 'reference';
        renderView();
      });
    }

    if (btnTeam6) {
      btnTeam6.addEventListener('click', () => {
        activeScope = 'team6';
        renderView();
      });
    }

    // Tabs Listeners
    ['overview', 'cu02', 'cu03', 'topology', 'audit'].forEach(t => {
      const tabBtn = container.querySelector(`#tab-${t}`);
      if (tabBtn) {
        tabBtn.addEventListener('click', () => {
          activeTab = t;
          renderView();
          if (t === 'topology') {
            setTimeout(initEmbeddedTopology, 50);
          }
        });
      }
    });

    // Inspect JSON Button
    const inspectBtn = container.querySelector('#btn-inspect-pipeline');
    if (inspectBtn) {
      inspectBtn.addEventListener('click', () => {
        const modal = container.querySelector('#cyber-modal');
        const code = container.querySelector('#cyber-modal-code');
        const title = container.querySelector('#cyber-modal-title');

        title.textContent = activeScope === 'team6' ? 'RE-03 (Kit Equipo 6)' : 'CF-03 (Caso Referencia)';
        code.textContent = JSON.stringify({
          schema_version: '1.0',
          mode: 'fixture',
          context: activeScope === 'team6' ? 'Asignación Equipo 6 (RE-03)' : 'Caso de Referencia (CF-03)',
          equipment: {
            code: activeScope === 'team6' ? 'RE-03' : 'CF-03',
            name: activeScope === 'team6' ? 'Retroexcavadora 03' : 'Cargador frontal 03',
            status: activeScope === 'team6' ? 'DISPONIBLE' : 'OBSOLETA',
            project_id: activeScope === 'team6' ? 'PROY-006' : 'PROY-014',
          },
          movement: {
            reference: activeScope === 'team6' ? 'MOV-EQUIPO6-001' : 'MOV-PRUEBA-001',
            driver: activeScope === 'team6' ? 'Rodrigo Trujillo (MOT-006)' : 'Adriana Steiner (MOT-014)',
            status: 'PENDIENTE',
          },
          governance: {
            rules_verified: ['R0', 'R1', 'R2', 'R3', 'R4', 'R5', 'R6', 'R7', 'R8'],
            audit_pass: true,
          }
        }, null, 2);

        modal.classList.add('cyber-modal--open');
      });
    }

    const modalClose = container.querySelector('#cyber-modal-close');
    if (modalClose) {
      modalClose.addEventListener('click', () => {
        container.querySelector('#cyber-modal').classList.remove('cyber-modal--open');
      });
    }
  }

  function initEmbeddedTopology() {
    const canvas = container.querySelector('#embedded-canvas');
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    const rect = canvas.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;

    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    ctx.scale(dpr, dpr);

    const width = rect.width;
    const height = rect.height;

    // Draw clean corporate network scheme
    ctx.fillStyle = '#06080d';
    ctx.fillRect(0, 0, width, height);

    const nodes = [
      { id: 'proy-014', label: 'PROY-014 La Unión', kind: 'project', x: width * 0.25, y: height * 0.4 },
      { id: 'proy-006', label: 'PROY-006 Zeta (Eq 6)', kind: 'project', x: width * 0.75, y: height * 0.4 },
      { id: 'cf-03', label: 'CF-03 (Cargador)', kind: 'machine', status: 'OBSOLETA', x: width * 0.25, y: height * 0.75 },
      { id: 're-03', label: 'RE-03 (Retroexcavadora)', kind: 'machine', status: 'DISPONIBLE', x: width * 0.75, y: height * 0.75 },
      { id: 'mov-001', label: 'MOV-PRUEBA-001', kind: 'movement', x: width * 0.5, y: height * 0.2 },
    ];

    const edges = [
      { from: nodes[0], to: nodes[2], label: 'Asignado en Obra' },
      { from: nodes[1], to: nodes[3], label: 'Asignado Equipo 6' },
      { from: nodes[0], to: nodes[4], label: 'Destino Flete' },
      { from: nodes[2], to: nodes[4], label: 'Tensión Bloqueo', isTension: true },
    ];

    // Edges
    edges.forEach(e => {
      ctx.beginPath();
      ctx.moveTo(e.from.x, e.from.y);
      ctx.lineTo(e.to.x, e.to.y);
      ctx.strokeStyle = e.isTension ? '#ef4444' : '#334155';
      ctx.lineWidth = e.isTension ? 3 : 1.5;
      if (e.isTension) ctx.setLineDash([6, 4]);
      else ctx.setLineDash([]);
      ctx.stroke();

      // Label
      ctx.fillStyle = e.isTension ? '#f87171' : '#64748b';
      ctx.font = '600 10px Inter, sans-serif';
      ctx.fillText(e.label, (e.from.x + e.to.x) / 2 + 5, (e.from.y + e.to.y) / 2 - 5);
    });

    // Nodes
    nodes.forEach(n => {
      ctx.beginPath();
      ctx.arc(n.x, n.y, n.kind === 'project' ? 24 : 18, 0, Math.PI * 2);
      ctx.fillStyle = n.kind === 'project' ? '#1e3a8a' : n.status === 'OBSOLETA' ? '#7f1d1d' : '#065f46';
      ctx.fill();
      ctx.strokeStyle = n.kind === 'project' ? '#3b82f6' : n.status === 'OBSOLETA' ? '#ef4444' : '#10b981';
      ctx.lineWidth = 2;
      ctx.stroke();

      ctx.fillStyle = '#f8fafc';
      ctx.font = '700 11px Inter, sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText(n.label, n.x, n.y + 34);
    });
  }

  // Initial render
  renderView();
}
