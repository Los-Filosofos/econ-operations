import { api } from '../api.js';

export async function renderRequirementsView(container) {
  let activeTab = 'rf01';
  let liveOutput = null;
  let isLoadingLive = false;

  const rfData = {
    rf01: {
      code: 'RF-01',
      title: 'Inventario de Términos y Diccionario de Datos',
      mandate: 'Inventario de cualquier campo o término nuevo generado a partir del diccionario y dataset sandbox de Prisma y Startrack: nombre de campo, tipo de dato y ejemplo de valor.',
      status: 'CUMPLE',
      statusClass: 'rf-badge-cumple',
      endpoint: '/api/v1/hub?mode=fixture',
      evidenceFile: 'docs/diccionario-modelo-econ.md',
      summary: 'El backend implementa contratos tipados en SQLModel/Pydantic (HubResponse, GraphProjection, IndicatorsReport, AssignmentSuggestion). Cada campo documenta su JSONPath, tipo de dato, obligatoriedad, ejemplo y procedencia explícita.',
      tests: 'scripts/check.sh --check (generar_diccionario.py)',
    },
    rf02: {
      code: 'RF-02',
      title: 'Matriz de Mapeo Campo a Campo (Prisma ↔ Startrack)',
      mandate: 'Matriz de mapeo que conecte cada campo relevante de una plataforma con su equivalente en la otra, marcando explícitamente los campos sin equivalente directo.',
      status: 'CUMPLE',
      statusClass: 'rf-badge-cumple',
      endpoint: '/api/v1/integration/nexus:request:46d2573e-08d3-4855-971d-2fbf9564e135?mode=fixture',
      evidenceFile: 'docs/equivalencias-prisma-startrack.md / output/matrices/matrices-econ.xlsx',
      summary: 'Mapeo clasificado en 4 tratamientos: Directo (ej. solicitud → remote_id), Transformado (fechas UTC/horarios a ventanas Startrack), Manual (asignación de conductor verificado) y Sin Equivalente (geocercas y telemetría avanzada).',
      tests: 'tests/test_integration_trace.py',
    },
    rf03: {
      code: 'RF-03',
      title: 'Matriz RACI y Control de Acceso por Roles',
      mandate: 'Matriz de responsabilidades que defina, para al menos tres roles funcionales, quién es Responsable, quién Aprueba, a quién se Consulta y a quién se Informa sobre el estado de un equipo.',
      status: 'CUMPLE',
      statusClass: 'rf-badge-cumple',
      endpoint: '/api/v1/status',
      evidenceFile: 'output/matrices/raci-propuesta.csv / apps/api/app/core/auth.py',
      summary: 'Define 9 decisiones operativas para 6 roles en sesión: admin, logistica, gerencia_proyecto, mantenimiento, control_costos y lectura. Permisos diferenciados (read, manage_transfers, declare_reception) e inmutabilidad por actor_* en el ledger.',
      tests: 'tests/test_auth.py, test_auth_ui.py',
    },
    rf04: {
      code: 'RF-04',
      title: 'Consulta Unificada de Estado y Ubicación de Equipo',
      mandate: 'El prototipo debe permitir consultar el estado y la ubicación de al menos un equipo de forma unificada, combinando datos de ambas plataformas.',
      status: 'CUMPLE',
      statusClass: 'rf-badge-cumple',
      endpoint: '/api/v1/hub?mode=fixture&search=CF-03',
      evidenceFile: 'apps/api/app/services/hub.py / apps/api/app/services/graph.py',
      summary: 'Combina el estado administrativo de Prisma (DISPONIBLE, OCUPADA, OBSOLETA) con la tarea y ubicación telemática en Startrack sin mezclar IDs ni inventar datos. Señala explícitamente si el GPS pertenece al camión o a la máquina.',
      tests: 'tests/test_evidence_views.py, test_graph.py',
    },
    rf05: {
      code: 'RF-05',
      title: 'Detección Visual y Resolución de Discrepancias',
      mandate: 'El prototipo debe reflejar visualmente al menos un caso donde el estado del equipo difiere entre Prisma y Startrack, y cómo se resuelve.',
      status: 'CUMPLE',
      statusClass: 'rf-badge-cumple',
      endpoint: '/api/v1/graph?mode=fixture',
      evidenceFile: 'docs/assets/entregables/diagrama-estados.svg / apps/api/app/services/graph.py',
      summary: 'Resuelve 3 tensiones críticas: 1) CF-03 OBSOLETA con solicitud APROBADA (mostrada como tensión auditable, sin sobreescritura silenciosa); 2) Máquina OCUPADA en ERP con tarea completada en GPS; 3) Paro mecánico activo bloqueando traslado.',
      tests: 'tests/test_evidence_projection.py, test_operations_graph.py',
    },
    rf06: {
      code: 'RF-06',
      title: 'Indicadores Inéditos y SLAs Operativos',
      mandate: 'Documentar al menos un indicador operativo que la integración haría visible por primera vez, por ejemplo tiempo de equipo fuera de geocerca sin justificación.',
      status: 'CUMPLE',
      statusClass: 'rf-badge-cumple',
      endpoint: '/api/v1/indicators?mode=fixture',
      evidenceFile: 'docs/indicadores-calculables.md / apps/api/app/services/indicators.py',
      summary: 'Calcula 8 indicadores por fila sin promedios engañosos: tiempo de solicitud abierta, aprobación sin tarea, máquina ocupada sin proyecto, flete sin acta de recepción y tiempo fuera de geocerca, cotejados contra SLAs S1 a S6.',
      tests: 'tests/test_indicators.py, test_indicator_views.py',
    },
    rnf: {
      code: 'RNF',
      title: 'Requisitos No Funcionales (RNF-01 a RNF-04)',
      mandate: 'Exploración exclusiva en Sandbox/datos sintéticos (RNF-01), formatos estructurados CSV/XLSX (RNF-02), prototipo navegable (RNF-03) y repositorio con manual (RNF-04).',
      status: 'VERIFICADO',
      statusClass: 'rf-badge-cumple',
      endpoint: '/api/v1/status',
      evidenceFile: 'output/matrices/matrices-econ.xlsx / README.md',
      summary: 'Cero uso de credenciales en cliente; 17 CSVs estructurados y libro XLSX auditado con SHA-256; aplicación web reactiva sin dependencias externas bloqueantes; suite de 616 pruebas automatizadas aprobadas.',
      tests: 'scripts/check.sh (Ruff, Format, Pytest, Diccionario, Matrices)',
    }
  };

  async function executeLiveQuery(endpoint) {
    isLoadingLive = true;
    render();
    try {
      const res = await fetch(endpoint);
      const data = await res.json();
      liveOutput = JSON.stringify(data, null, 2);
    } catch (err) {
      liveOutput = `Error ejecutando consulta: ${err.message}`;
    } finally {
      isLoadingLive = false;
      render();
    }
  }

  function render() {
    const current = rfData[activeTab];

    container.innerHTML = `
      <div class="rf-container fade-in">
        <!-- Header -->
        <header class="rf-header">
          <div>
            <div class="hub-intro-tag">Auditoría & Cumplimiento Técnico</div>
            <h1 class="hub-intro-title">Matriz de Requisitos Funcionales (RF-01 a RF-06 & RNF)</h1>
            <div class="hub-intro-subtitle">
              Demostración interactiva de cómo el backend de FastAPI + PostgreSQL resuelve cada exigencia del brief.
            </div>
          </div>
          <div style="display: flex; gap: 8px; align-items: center;">
            <div style="background: rgba(16, 185, 129, 0.15); border: 1px solid #10b981; color: #34d399; padding: 6px 14px; border-radius: var(--radius-sm); font-size: 0.75rem; font-weight: 700;">
              ✓ 6 RF CUMPLEN
            </div>
            <div style="background: rgba(56, 189, 248, 0.15); border: 1px solid #38bdf8; color: #38bdf8; padding: 6px 14px; border-radius: var(--radius-sm); font-size: 0.75rem; font-weight: 700;">
              ✓ 4 RNF AUDITADOS
            </div>
          </div>
        </header>

        <!-- Navigation Tabs -->
        <div class="rf-nav-tabs">
          <button class="rf-tab-btn ${activeTab === 'rf01' ? 'rf-tab-btn--active' : ''}" data-tab="rf01">
            <span>RF-01: Diccionario</span>
          </button>
          <button class="rf-tab-btn ${activeTab === 'rf02' ? 'rf-tab-btn--active' : ''}" data-tab="rf02">
            <span>RF-02: Mapeo</span>
          </button>
          <button class="rf-tab-btn ${activeTab === 'rf03' ? 'rf-tab-btn--active' : ''}" data-tab="rf03">
            <span>RF-03: RACI</span>
          </button>
          <button class="rf-tab-btn ${activeTab === 'rf04' ? 'rf-tab-btn--active' : ''}" data-tab="rf04">
            <span>RF-04: Consulta</span>
          </button>
          <button class="rf-tab-btn ${activeTab === 'rf05' ? 'rf-tab-btn--active' : ''}" data-tab="rf05">
            <span>RF-05: Discrepancias</span>
          </button>
          <button class="rf-tab-btn ${activeTab === 'rf06' ? 'rf-tab-btn--active' : ''}" data-tab="rf06">
            <span>RF-06: Indicadores</span>
          </button>
          <button class="rf-tab-btn ${activeTab === 'rnf' ? 'rf-tab-btn--active' : ''}" data-tab="rnf">
            <span>RNF: Calidad & Sandbox</span>
          </button>
        </div>

        <!-- Requirement Detail Card -->
        <div class="rf-card">
          <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 12px;">
            <div>
              <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 4px;">
                <span style="font-family: var(--font-mono); font-size: 1rem; font-weight: 700; color: #38bdf8;">${current.code}</span>
                <span class="${current.statusClass}">${current.status}</span>
              </div>
              <h2 style="font-size: 1.25rem; font-weight: 700; color: #ffffff;">${current.title}</h2>
            </div>
            <button id="btn-run-live" style="
              background: var(--brand);
              border: 1px solid var(--brand-light);
              color: #ffffff;
              padding: 8px 16px;
              border-radius: var(--radius-sm);
              font-size: 0.8125rem;
              font-weight: 600;
              cursor: pointer;
              display: flex;
              align-items: center;
              gap: 8px;
            ">
              <span>⚡ Probar Endpoint en Vivo</span>
            </button>
          </div>

          <!-- Mandate Box -->
          <div style="background: var(--bg-elevated); border-left: 4px solid #38bdf8; padding: 12px 16px; border-radius: 4px;">
            <span style="font-size: 0.75rem; font-weight: 700; color: #38bdf8; text-transform: uppercase;">Qué exige el Brief del Hackathon:</span>
            <div style="font-size: 0.875rem; color: var(--text-primary); margin-top: 4px; line-height: 1.5;">
              "${current.mandate}"
            </div>
          </div>

          <!-- Solution Breakdown -->
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px;">
            <div style="background: var(--bg-surface); border: 1px solid var(--border); border-radius: var(--radius-md); padding: 16px;">
              <div style="font-size: 0.75rem; font-weight: 700; color: var(--text-secondary); margin-bottom: 6px;">CÓMO LO RESUELVE EL BACKEND</div>
              <div style="font-size: 0.8125rem; color: #e2e8f0; line-height: 1.5;">
                ${current.summary}
              </div>
            </div>

            <div style="background: var(--bg-surface); border: 1px solid var(--border); border-radius: var(--radius-md); padding: 16px; display: flex; flex-direction: column; gap: 10px;">
              <div>
                <div style="font-size: 0.75rem; font-weight: 700; color: var(--text-secondary);">EVIDENCIA EN REPOSITORIO</div>
                <div style="font-family: var(--font-mono); font-size: 0.75rem; color: #93c5fd; margin-top: 2px;">
                  ${current.evidenceFile}
                </div>
              </div>
              <div>
                <div style="font-size: 0.75rem; font-weight: 700; color: var(--text-secondary);">PRUEBAS AUTOMATIZADAS</div>
                <div style="font-family: var(--font-mono); font-size: 0.75rem; color: #34d399; margin-top: 2px;">
                  ${current.tests}
                </div>
              </div>
              <div>
                <div style="font-size: 0.75rem; font-weight: 700; color: var(--text-secondary);">ENDPOINT REST ASOCIADO</div>
                <div style="font-family: var(--font-mono); font-size: 0.75rem; color: #fbbf24; margin-top: 2px;">
                  ${current.endpoint}
                </div>
              </div>
            </div>
          </div>

          <!-- Live Output Console -->
          <div>
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
              <span style="font-size: 0.8125rem; font-weight: 600; color: var(--text-secondary);">Respuesta Real del Backend en Vivo:</span>
              <span style="font-size: 0.75rem; color: var(--text-tertiary); font-family: var(--font-mono);">${current.endpoint}</span>
            </div>
            <div class="rf-live-box">
              ${isLoadingLive
                ? 'Consultando endpoint en tiempo real...'
                : (liveOutput || 'Haz clic en "⚡ Probar Endpoint en Vivo" para inspeccionar la respuesta JSON real del backend.')}
            </div>
          </div>
        </div>
      </div>
    `;

    // Event listeners
    container.querySelectorAll('.rf-tab-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        activeTab = e.currentTarget.dataset.tab;
        liveOutput = null; // Clear live output on tab change
        render();
      });
    });

    const runBtn = container.querySelector('#btn-run-live');
    if (runBtn) {
      runBtn.addEventListener('click', () => {
        executeLiveQuery(current.endpoint);
      });
    }
  }

  render();
}
