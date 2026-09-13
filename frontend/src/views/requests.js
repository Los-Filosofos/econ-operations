import { api } from '../api.js';
import { renderStatusBadge } from '../components/status-badge.js';
import { renderDataTable } from '../components/data-table.js';

export async function renderRequestsView(container) {
  container.innerHTML = `
    <div class="page-header fade-in">
      <div>
        <h1 class="page-header__title">Solicitudes de Maquinaria</h1>
        <div class="page-header__subtitle">Requerimientos registrados en Prisma / Nexus y recomendación de unidades candidatas</div>
      </div>
    </div>

    <div class="fade-in stagger-1" id="requests-table-container">
      <div style="color: var(--text-secondary); padding: 20px;">Cargando solicitudes...</div>
    </div>

    <!-- Modals container -->
    <div id="request-modals"></div>
  `;

  try {
    const hub = await api.getHub();
    const requests = hub.requests || [];

    const tableEl = renderDataTable({
      title: 'Registro de Requerimientos de Proyecto',
      columns: [
        {
          header: 'ID Solicitud',
          accessor: (r) => r.provenance?.source_id || r.id.split(':').pop(),
          render: (r) => `<strong class="text-mono" style="color: var(--brand-light);">${r.provenance?.source_id || r.id.split(':').pop()}</strong>`,
        },
        { header: 'Proyecto', accessor: 'project_name' },
        { header: 'Tipo Maquinaria', accessor: 'machinery_type' },
        {
          header: 'Período',
          accessor: (r) => `${r.starts_on || '—'} → ${r.ends_on || '—'}`,
        },
        {
          header: 'Estado',
          accessor: 'status',
          render: (r) => renderStatusBadge(r.status),
        },
        {
          header: 'Unidad Asignada',
          accessor: (r) => r.machinery_asset_number || r.machinery_name || 'Sin asignar',
          render: (r) => r.machinery_asset_number ? `<span class="text-mono" style="color: var(--text-primary); font-weight: 500;">${r.machinery_asset_number}</span>` : '<span style="color: var(--state-pending);">Sin asignar</span>',
        },
        { header: 'Solicitado Por', accessor: 'requested_by' },
      ],
      data: requests,
      rowClick: (r) => openRequestModal(r),
      emptyMessage: 'No hay solicitudes encontradas.',
    });

    const tableContainer = container.querySelector('#requests-table-container');
    tableContainer.innerHTML = '';
    tableContainer.appendChild(tableEl);

  } catch (err) {
    container.querySelector('#requests-table-container').innerHTML = `
      <div style="color: #d03b3b; padding: 20px;">Error al cargar solicitudes: ${err.message}</div>
    `;
  }

  async function openRequestModal(r) {
    const modalRoot = container.querySelector('#request-modals');
    modalRoot.innerHTML = `
      <div class="modal-overlay" id="req-modal-overlay">
        <div class="modal-card">
          <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 16px;">
            <div>
              <div style="font-size: 0.6875rem; text-transform: uppercase; color: var(--text-tertiary);">Solicitud de Obra</div>
              <h2 style="font-size: 1.125rem;">${r.machinery_type} · ${r.project_name}</h2>
            </div>
            <button id="req-close-btn" style="background: none; border: none; font-size: 20px; color: var(--text-secondary); cursor: pointer;">&times;</button>
          </div>

          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 16px; background: var(--bg-elevated); padding: 12px; border-radius: 8px;">
            <div>
              <div style="font-size: 0.6875rem; color: var(--text-tertiary);">ESTADO</div>
              <div style="margin-top: 4px;">${renderStatusBadge(r.status)}</div>
            </div>
            <div>
              <div style="font-size: 0.6875rem; color: var(--text-tertiary);">PERÍODO SOLICITADO</div>
              <div class="text-mono" style="font-size: 0.8125rem; margin-top: 4px;">${r.starts_on} → ${r.ends_on}</div>
            </div>
            <div>
              <div style="font-size: 0.6875rem; color: var(--text-tertiary);">SOLICITANTE</div>
              <div style="font-size: 0.8125rem; font-weight: 500; margin-top: 4px;">${r.requested_by || '—'}</div>
            </div>
            <div>
              <div style="font-size: 0.6875rem; color: var(--text-tertiary);">ID ORIGEN (PRISMA)</div>
              <div class="text-mono" style="font-size: 0.75rem; margin-top: 4px;">${r.provenance?.source_id}</div>
            </div>
          </div>

          <div id="suggestions-area">
            <div style="text-align: center; padding: 20px; color: var(--text-secondary);">Consultando sugerencias de unidades...</div>
          </div>

          <div style="display: flex; justify-content: flex-end; gap: 8px; margin-top: 16px; border-top: 1px solid var(--border); padding-top: 12px;">
            <a href="#/integracion" style="padding: 8px 14px; background: var(--bg-elevated); border: 1px solid var(--border); border-radius: 4px; font-size: 0.8125rem; color: var(--text-link);">
              Ver Traza de Integración →
            </a>
          </div>
        </div>
      </div>
    `;

    modalRoot.querySelector('#req-close-btn').addEventListener('click', () => {
      modalRoot.innerHTML = '';
    });

    // Check suggestions
    const suggestionsArea = modalRoot.querySelector('#suggestions-area');
    try {
      const sugg = await api.getSuggestions(r.id);
      if (!sugg.applicable) {
        suggestionsArea.innerHTML = `
          <div style="padding: 12px; background: rgba(255,255,255,0.02); border-radius: 6px; border: 1px solid var(--border); font-size: 0.8125rem; color: var(--text-secondary);">
            ℹ ${sugg.message}
          </div>
        `;
        return;
      }

      const candidates = sugg.candidates || [];
      if (candidates.length === 0) {
        suggestionsArea.innerHTML = '<div style="font-size: 0.8125rem; color: var(--text-tertiary);">No se encontraron candidatas disponibles para esta solicitud.</div>';
        return;
      }

      const candidatesHtml = candidates.map(c => {
        const badgeColor = c.eligibility === 'eligible' ? '#199e70' : (c.eligibility === 'review_required' ? '#eb6834' : '#d03b3b');
        const badgeLabel = c.eligibility === 'eligible' ? 'Elegible' : (c.eligibility === 'review_required' ? 'Por Revisar' : 'Excluida');

        return `
          <div style="border: 1px solid var(--border); border-radius: 6px; padding: 12px; margin-bottom: 8px; background: var(--bg-surface);">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
              <strong style="font-size: 0.875rem; color: var(--brand-light);">${c.label} · ${c.equipment_class}</strong>
              <span style="font-size: 0.6875rem; font-weight: 600; padding: 2px 8px; border-radius: 4px; background: ${badgeColor}20; color: ${badgeColor}; border: 1px solid ${badgeColor}40;">
                ${badgeLabel}
              </span>
            </div>
            <div style="font-size: 0.75rem; color: var(--text-secondary); margin-bottom: 6px;">
              ${(c.reasons || []).join(' · ')}
            </div>
            ${c.missing && c.missing.length > 0 ? `
              <div style="font-size: 0.6875rem; color: var(--text-tertiary);">
                ⚠ Faltantes no verificables: ${c.missing[0]}
              </div>
            ` : ''}
          </div>
        `;
      }).join('');

      suggestionsArea.innerHTML = `
        <div style="font-size: 0.75rem; font-weight: 600; text-transform: uppercase; margin-bottom: 8px; color: var(--brand-light);">
          Unidades Candidatas Recomendadas (${candidates.length})
        </div>
        <div style="max-height: 280px; overflow-y: auto;">
          ${candidatesHtml}
        </div>
      `;
    } catch (err) {
      suggestionsArea.innerHTML = `<div style="font-size: 0.75rem; color: #d03b3b;">No se pudieron calcular sugerencias: ${err.message}</div>`;
    }
  }
}
