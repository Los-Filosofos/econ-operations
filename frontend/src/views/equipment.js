import { api } from '../api.js';
import { renderStatusBadge } from '../components/status-badge.js';
import { renderDataTable } from '../components/data-table.js';

export async function renderEquipmentView(container) {
  container.innerHTML = `
    <div class="page-header fade-in">
      <div>
        <h1 class="page-header__title">Inventario de Maquinaria</h1>
        <div class="page-header__subtitle">Flota consultada de Prisma, asignaciones activas y estado de mantenimiento</div>
      </div>
    </div>

    <div class="fade-in stagger-1" id="equipment-table-container">
      <div style="color: var(--text-secondary); padding: 20px;">Cargando inventario...</div>
    </div>

    <!-- Modals container -->
    <div id="equipment-modals"></div>
  `;

  try {
    const hub = await api.getHub();
    const equipment = hub.equipment || [];

    const tableEl = renderDataTable({
      title: 'Parque de Maquinaria Registrado',
      columns: [
        {
          header: 'Código / Activo',
          accessor: 'asset_number',
          render: (e) => `<strong class="text-mono" style="color: var(--brand-light);">${e.asset_number || '—'}</strong>`,
        },
        { header: 'Descripción', accessor: 'name' },
        { header: 'Clase', accessor: 'equipment_class' },
        { header: 'Empresa', accessor: 'company' },
        {
          header: 'Estado',
          accessor: 'machinery_status',
          render: (e) => renderStatusBadge(e.machinery_status),
        },
        {
          header: 'Proyecto Asignado',
          accessor: (e) => e.project_name || 'Sin proyecto asignado',
          render: (e) => e.project_name ? `<span>${e.project_name}</span>` : '<span class="text-secondary">Disponible</span>',
        },
        {
          header: 'Período Asignado',
          accessor: (e) => e.assignment_starts_on ? `${e.assignment_starts_on} → ${e.assignment_ends_on || '—'}` : '—',
        },
        {
          header: 'Mantenimiento / Paro',
          accessor: (e) => e.maintenance_is_stopped ? 'PARO ACTIVO' : (e.maintenance_failure_id ? 'Falla activa' : 'Normal'),
          render: (e) => e.maintenance_is_stopped
            ? '<span style="color: var(--state-issue); font-weight: 600;">⚠ PARO</span>'
            : (e.maintenance_failure_id ? '<span style="color: var(--state-pending);">Falla</span>' : '<span style="color: var(--state-active);">OK</span>'),
        }
      ],
      data: equipment,
      rowClick: (eq) => openEquipmentModal(eq),
      emptyMessage: 'No hay maquinaria registrada.',
    });

    const tableContainer = container.querySelector('#equipment-table-container');
    tableContainer.innerHTML = '';
    tableContainer.appendChild(tableEl);

  } catch (err) {
    container.querySelector('#equipment-table-container').innerHTML = `
      <div style="color: #d03b3b; padding: 20px;">Error al cargar inventario: ${err.message}</div>
    `;
  }

  function openEquipmentModal(eq) {
    const modalRoot = container.querySelector('#equipment-modals');
    modalRoot.innerHTML = `
      <div class="modal-overlay" id="eq-modal-overlay">
        <div class="modal-card">
          <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 16px;">
            <div>
              <div style="font-size: 0.6875rem; text-transform: uppercase; color: var(--text-tertiary);">Ficha de Unidad</div>
              <h2 style="font-size: 1.125rem;">${eq.asset_number} · ${eq.name}</h2>
            </div>
            <button id="eq-close-btn" style="background: none; border: none; font-size: 20px; color: var(--text-secondary); cursor: pointer;">&times;</button>
          </div>

          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 16px; background: var(--bg-elevated); padding: 12px; border-radius: 8px;">
            <div>
              <div style="font-size: 0.6875rem; color: var(--text-tertiary);">ESTADO ADMINISTRATIVO</div>
              <div style="margin-top: 4px;">${renderStatusBadge(eq.machinery_status)}</div>
            </div>
            <div>
              <div style="font-size: 0.6875rem; color: var(--text-tertiary);">CLASE DE EQUIPO</div>
              <div style="font-size: 0.8125rem; font-weight: 500; margin-top: 4px;">${eq.equipment_class}</div>
            </div>
            <div>
              <div style="font-size: 0.6875rem; color: var(--text-tertiary);">PROYECTO ACTUAL</div>
              <div style="font-size: 0.8125rem; margin-top: 4px;">${eq.project_name || 'Sin asignación activa'}</div>
            </div>
            <div>
              <div style="font-size: 0.6875rem; color: var(--text-tertiary);">PERÍODO DE USO</div>
              <div class="text-mono" style="font-size: 0.8125rem; margin-top: 4px;">${eq.assignment_starts_on || '—'} → ${eq.assignment_ends_on || '—'}</div>
            </div>
          </div>

          <div style="margin-bottom: 16px;">
            <div style="font-size: 0.75rem; font-weight: 600; text-transform: uppercase; margin-bottom: 8px;">Diagnóstico de Mantenimiento</div>
            <div style="background: var(--bg-surface); border: 1px solid var(--border); padding: 10px; border-radius: 6px; font-size: 0.75rem;">
              <div><strong>Falla activa:</strong> ${eq.maintenance_failure_id || 'Ninguna registrada'}</div>
              <div><strong>Estado de falla:</strong> ${eq.maintenance_status || 'Sin reporte'}</div>
              <div><strong>Paro operativo:</strong> ${eq.maintenance_is_stopped ? 'Sí (la unidad no debe programarse para traslados)' : 'No'}</div>
            </div>
          </div>

          <div style="margin-bottom: 16px;">
            <div style="font-size: 0.75rem; font-weight: 600; text-transform: uppercase; margin-bottom: 8px;">Evidencia Documental</div>
            <div style="font-size: 0.75rem; color: var(--text-secondary); line-height: 1.5;">
              <div><strong>Origen:</strong> ${eq.provenance?.source} (${eq.provenance?.environment || 'sandbox'})</div>
              <div class="text-mono" style="font-size: 0.6875rem; color: var(--text-tertiary);">${eq.provenance?.source_reference || eq.provenance?.source_id}</div>
              <div style="margin-top: 4px; color: var(--text-tertiary);">${eq.relation_note || ''}</div>
            </div>
          </div>
        </div>
      </div>
    `;

    modalRoot.querySelector('#eq-close-btn').addEventListener('click', () => {
      modalRoot.innerHTML = '';
    });
  }
}
