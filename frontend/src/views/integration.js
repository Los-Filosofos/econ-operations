import { api } from '../api.js';
import { renderStatusBadge } from '../components/status-badge.js';

export async function renderIntegrationView(container) {
  container.innerHTML = `
    <div class="page-header fade-in">
      <div>
        <h1 class="page-header__title">Traza de Integración End-to-End</h1>
        <div class="page-header__subtitle">Trazabilidad de datos entre Prisma (ERP/Nexus), ECON (Normalización) y Startrack (Telemetría)</div>
      </div>
      <div style="display: flex; align-items: center; gap: 8px;">
        <label for="request-selector" style="font-size: 0.75rem; color: var(--text-secondary);">Solicitud:</label>
        <select id="request-selector" style="
          background: var(--bg-surface);
          border: 1px solid var(--border);
          border-radius: var(--radius-sm);
          color: var(--text-primary);
          padding: 6px 12px;
          font-family: var(--font-mono);
          font-size: 0.75rem;
          outline: none;
        "></select>
      </div>
    </div>

    <!-- Request Overview Card -->
    <div id="request-meta-card" class="fade-in stagger-1" style="
      background: var(--bg-surface);
      border: 1px solid var(--border);
      border-radius: var(--radius-lg);
      padding: var(--sp-4) var(--sp-5);
      margin-bottom: var(--sp-6);
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: space-between;
      gap: var(--sp-4);
    ">
      <div>Cargando datos de la solicitud...</div>
    </div>

    <!-- 4 Pipeline Stages -->
    <div class="fade-in stagger-2" style="
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: var(--sp-4);
      margin-bottom: var(--sp-6);
    " id="stages-container"></div>

    <!-- Timeline of the Transfer -->
    <div class="fade-in stagger-3" style="
      background: var(--bg-surface);
      border: 1px solid var(--border);
      border-radius: var(--radius-lg);
      padding: var(--sp-5);
      margin-bottom: var(--sp-6);
    " id="timeline-container">
      <div style="font-weight: 600; font-size: 0.875rem; margin-bottom: var(--sp-4);">Línea Temporal de Eventos del Traslado</div>
      <div id="timeline-steps" style="display: flex; flex-wrap: wrap; gap: var(--sp-4); align-items: flex-start;"></div>
      <div id="timeline-note" style="margin-top: var(--sp-4); font-size: 0.75rem; color: var(--text-tertiary);"></div>
    </div>

    <!-- Field Transformation Matrix -->
    <div class="fade-in stagger-4" style="
      background: var(--bg-surface);
      border: 1px solid var(--border);
      border-radius: var(--radius-lg);
      padding: var(--sp-5);
    ">
      <div style="font-weight: 600; font-size: 0.875rem; margin-bottom: var(--sp-4);">Tratamiento de Campos y Reglas de Normalización</div>
      <div style="overflow-x: auto;">
        <table class="data-table" id="field-matrix-table">
          <thead>
            <tr>
              <th>Concepto</th>
              <th>Prisma (Origen)</th>
              <th>ECON (Normalizado)</th>
              <th>Startrack (Destino)</th>
              <th>Tratamiento</th>
              <th>Nota</th>
            </tr>
          </thead>
          <tbody></tbody>
        </table>
      </div>
    </div>
  `;

  const selector = container.querySelector('#request-selector');

  try {
    // 1. Fetch hub requests to populate selector
    const hub = await api.getHub();
    const requests = hub.requests || [];

    if (requests.length === 0) {
      container.querySelector('#request-meta-card').innerHTML = '<div>No se encontraron solicitudes registradas.</div>';
      return;
    }

    selector.innerHTML = requests.map(r => `
      <option value="${r.id}">${r.label || r.id.split(':').pop()}</option>
    `).join('');

    async function loadTrace(requestId) {
      try {
        const trace = await api.getIntegration(requestId);
        renderTrace(trace);
      } catch (err) {
        container.querySelector('#request-meta-card').innerHTML = `<div style="color: #d03b3b;">Error al cargar traza: ${err.message}</div>`;
      }
    }

    selector.addEventListener('change', (e) => loadTrace(e.target.value));

    // Load initial trace
    await loadTrace(requests[0].id);

  } catch (err) {
    container.innerHTML += `<div style="color: #d03b3b; padding: 20px;">Error: ${err.message}</div>`;
  }

  function renderTrace(trace) {
    // 1. Header card
    container.querySelector('#request-meta-card').innerHTML = `
      <div style="display: flex; align-items: center; gap: 12px;">
        <div style="width: 32px; height: 32px; border-radius: 6px; background: rgba(90, 141, 188, 0.2); display: flex; align-items: center; justify-content: center; font-size: 16px;">⇄</div>
        <div>
          <div style="font-weight: 600; font-size: 0.9375rem;">${trace.request_label}</div>
          <div style="font-size: 0.75rem; color: var(--text-secondary);">${trace.project_label}</div>
        </div>
      </div>
      <div style="display: flex; align-items: center; gap: 12px;">
        <div>
          <div style="font-size: 0.6875rem; text-transform: uppercase; color: var(--text-tertiary);">Maquinaria Vinculada</div>
          <div style="font-size: 0.8125rem; font-weight: 500;">${trace.equipment_label || 'Sin asignar'}</div>
        </div>
        <div>
          <div style="font-size: 0.6875rem; text-transform: uppercase; color: var(--text-tertiary);">Movimiento Local</div>
          <div style="font-size: 0.8125rem; font-family: var(--font-mono);">${trace.movement_reference || '—'}</div>
        </div>
        <div>
          <div style="font-size: 0.6875rem; text-transform: uppercase; color: var(--text-tertiary);">Estado Traslado</div>
          <div>${renderStatusBadge(trace.movement_state || 'DRAFT')}</div>
        </div>
      </div>
    `;

    // 2. Stages
    const stagesContainer = container.querySelector('#stages-container');
    const stageIcons = {
      prisma: '📦',
      econ: '⚙',
      startrack_request: '🚀',
      startrack_response: '🛰',
    };

    stagesContainer.innerHTML = (trace.stages || []).map((stage, idx) => {
      const entriesHtml = (stage.entries || []).slice(0, 8).map(e => `
        <div style="display: flex; justify-content: space-between; gap: 8px; font-size: 0.75rem; padding: 3px 0; border-bottom: 1px solid var(--border-light);">
          <span style="color: var(--text-tertiary);">${e.label || e.field}</span>
          <span class="text-mono" style="color: var(--text-primary); text-align: right; max-width: 160px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
            ${e.value !== null ? e.value : '—'}
          </span>
        </div>
      `).join('');

      return `
        <div style="
          background: var(--bg-surface);
          border: 1px solid var(--border);
          border-radius: var(--radius-lg);
          padding: var(--sp-4);
          display: flex;
          flex-direction: column;
        ">
          <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px;">
            <div style="display: flex; align-items: center; gap: 8px;">
              <span style="font-size: 16px;">${stageIcons[stage.key] || '📋'}</span>
              <strong style="font-size: 0.875rem;">${stage.title}</strong>
            </div>
            ${renderStatusBadge(stage.state === 'done' ? 'APROBADA' : 'PENDIENTE', stage.state)}
          </div>
          <div style="font-size: 0.75rem; color: var(--text-secondary); margin-bottom: 12px; line-height: 1.4;">${stage.summary}</div>
          <div style="display: flex; flex-direction: column; gap: 2px;">
            ${entriesHtml || '<div style="font-size: 0.75rem; color: var(--text-tertiary); padding: 12px 0;">Sin campos recibidos aún</div>'}
          </div>
        </div>
      `;
    }).join('');

    // 3. Timeline
    const timelineSteps = container.querySelector('#timeline-steps');
    const instants = trace.timeline?.instants || [];

    timelineSteps.innerHTML = instants.map((inst, idx) => {
      const isDone = Boolean(inst.at);
      return `
        <div style="flex: 1; min-width: 140px; display: flex; flex-direction: column; gap: 6px;">
          <div style="display: flex; align-items: center; gap: 8px;">
            <div style="
              width: 24px;
              height: 24px;
              border-radius: 50%;
              background: ${isDone ? '#199e70' : '#30363d'};
              color: white;
              display: flex;
              align-items: center;
              justify-content: center;
              font-size: 11px;
              font-weight: 600;
            ">${isDone ? '✓' : idx + 1}</div>
            <strong style="font-size: 0.8125rem; color: ${isDone ? 'var(--text-primary)' : 'var(--text-secondary)'};">${inst.label}</strong>
          </div>
          <div class="text-mono" style="font-size: 0.6875rem; color: ${isDone ? 'var(--brand-light)' : 'var(--text-tertiary)'};">
            ${inst.at ? new Date(inst.at).toLocaleString('es-SV') : 'No observado'}
          </div>
          <div style="font-size: 0.6875rem; color: var(--text-tertiary); line-height: 1.3;">${inst.source}</div>
        </div>
      `;
    }).join('');

    container.querySelector('#timeline-note').textContent = trace.timeline?.note || '';

    // 4. Field matrix table
    const tableBody = container.querySelector('#field-matrix-table tbody');
    const fields = trace.field_map || [];

    tableBody.innerHTML = fields.map(f => {
      const treatmentBadges = {
        conserved: '<span style="color: #199e70;">✓ Conservado</span>',
        transformed: '<span style="color: #5a8dbc;">↻ Transformado</span>',
        manual: '<span style="color: #eb6834;">✎ Manual</span>',
        no_equivalent: '<span style="color: #8b949e;">— Sin equiv.</span>',
      };

      return `
        <tr>
          <td><strong>${f.concept}</strong></td>
          <td class="text-mono" style="font-size: 0.75rem;">${f.prisma?.value ?? '—'}</td>
          <td class="text-mono" style="font-size: 0.75rem;">${f.econ?.value ?? '—'}</td>
          <td class="text-mono" style="font-size: 0.75rem;">${f.startrack?.value ?? '—'}</td>
          <td>${treatmentBadges[f.treatment] || f.treatment}</td>
          <td style="font-size: 0.75rem; max-width: 280px; white-space: normal;">${f.note}</td>
        </tr>
      `;
    }).join('');
  }
}
