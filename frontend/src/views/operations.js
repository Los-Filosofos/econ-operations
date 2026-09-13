import { api } from '../api.js';
import { renderStatusBadge } from '../components/status-badge.js';
import { renderDataTable } from '../components/data-table.js';
import { renderCard } from '../components/card.js';

export async function renderOperationsView(container) {
  container.innerHTML = `
    <div class="page-header fade-in">
      <div>
        <h1 class="page-header__title">Gestión de Traslados y Operaciones</h1>
        <div class="page-header__subtitle">Preparación de despachos a Startrack, cola de sincronización y constancias de recepción</div>
      </div>
      <div style="display: flex; gap: 8px;">
        <button id="btn-sync-ops" style="
          background: var(--bg-surface);
          border: 1px solid var(--border);
          border-radius: var(--radius-sm);
          color: var(--text-primary);
          padding: 8px 14px;
          cursor: pointer;
          font-weight: 500;
          font-size: 0.8125rem;
          display: flex;
          align-items: center;
          gap: 6px;
        ">
          <span>Sincronizar</span>
        </button>
        <button id="btn-new-plan" style="
          background: var(--brand);
          border: 1px solid var(--brand-light);
          border-radius: var(--radius-sm);
          color: white;
          padding: 8px 14px;
          cursor: pointer;
          font-weight: 600;
          font-size: 0.8125rem;
          display: flex;
          align-items: center;
          gap: 6px;
        ">
          <span>+ Nuevo Plan</span>
        </button>
      </div>
    </div>

    <!-- Summary metrics -->
    <div class="indicators-grid fade-in stagger-1" id="ops-metrics-container">
      <div style="color: var(--text-secondary); padding: 16px;">Cargando operaciones...</div>
    </div>

    <!-- Movements Table -->
    <div class="fade-in stagger-2" id="ops-table-container"></div>

    <!-- Modals container -->
    <div id="ops-modals"></div>
  `;

  let movements = [];

  async function loadData() {
    try {
      const data = await api.getOperations();
      movements = data.movements || [];

      // Metrics
      const total = movements.length;
      const drafts = movements.filter(m => m.state === 'draft').length;
      const sent = movements.filter(m => m.state === 'sent').length;
      const received = movements.filter(m => Boolean(m.receipt)).length;

      container.querySelector('#ops-metrics-container').innerHTML = `
        ${renderCard({ title: 'Total Registrados', value: total, subtitle: 'LIBRO MAYOR', accentColor: '#5a8dbc' })}
        ${renderCard({ title: 'En Borrador', value: drafts, subtitle: 'PENDIENTES DE ENVÍO', accentColor: '#eb6834' })}
        ${renderCard({ title: 'Enviados a Startrack', value: sent, subtitle: 'EN SEGUIMIENTO GPS', accentColor: '#2a78d6' })}
        ${renderCard({ title: 'Recepción Declarada', value: received, subtitle: 'CONFIRMADOS EN DESTINO', accentColor: '#199e70' })}
      `;

      // Table
      const tableEl = renderDataTable({
        title: 'Movimientos de Maquinaria Registrados',
        columns: [
          {
            header: 'Referencia',
            accessor: (m) => m.payload?.remote_id || m.id.split(':').pop(),
            render: (m) => `<strong class="text-mono" style="color: var(--brand-light);">${m.payload?.remote_id || m.id.split(':').pop()}</strong>`,
          },
          {
            header: 'Maquinaria',
            accessor: (m) => m.source_equipment?.asset_number || m.source_equipment?.name || '—',
          },
          {
            header: 'Proyecto Destino',
            accessor: (m) => m.source_request?.project_name || m.payload?.poi_id || '—',
          },
          {
            header: 'Fecha / Hora Programada',
            accessor: (m) => `${m.payload?.start_date || '—'} ${m.payload?.start_time || ''}`,
          },
          {
            header: 'Estado',
            accessor: 'state',
            render: (m) => renderStatusBadge(m.state),
          },
          {
            header: 'Recepción',
            accessor: (m) => m.receipt ? 'Declarada' : 'Pendiente',
            render: (m) => m.receipt ? renderStatusBadge('COMPLETADA', 'Declarada') : '<span class="text-secondary">Sin declarar</span>',
          },
        ],
        data: movements,
        rowClick: (m) => openMovementDetailModal(m),
        emptyMessage: 'No hay movimientos de traslado registrados.',
      });

      const tableContainer = container.querySelector('#ops-table-container');
      tableContainer.innerHTML = '';
      tableContainer.appendChild(tableEl);

    } catch (err) {
      container.querySelector('#ops-metrics-container').innerHTML = `
        <div style="color: #d03b3b; padding: 20px;">Error al cargar operaciones: ${err.message}</div>
      `;
    }
  }

  container.querySelector('#btn-sync-ops').addEventListener('click', async () => {
    const btn = container.querySelector('#btn-sync-ops');
    btn.disabled = true;
    btn.textContent = 'Sincronizando...';
    try {
      await api.syncOperations();
      alert('Sincronización ejecutada con éxito.');
      await loadData();
    } catch (err) {
      alert(`Error en sincronización: ${err.message}`);
    } finally {
      btn.disabled = false;
      btn.textContent = 'Sincronizar';
    }
  });

  container.querySelector('#btn-new-plan').addEventListener('click', () => {
    openNewPlanModal();
  });

  function openMovementDetailModal(m) {
    const modalRoot = container.querySelector('#ops-modals');
    const eventsHtml = (m.events || []).map(ev => `
      <div style="padding: 8px 12px; border-left: 2px solid var(--brand-light); background: rgba(255,255,255,0.02); margin-bottom: 6px;">
        <div style="display: flex; justify-content: space-between; font-size: 0.75rem;">
          <strong style="color: var(--text-primary); text-transform: uppercase;">${ev.kind}</strong>
          <span class="text-mono" style="color: var(--text-tertiary);">${ev.recorded_at ? new Date(ev.recorded_at).toLocaleTimeString() : '—'}</span>
        </div>
        <div style="font-size: 0.6875rem; color: var(--text-secondary); margin-top: 2px;">Estado: ${ev.state}</div>
      </div>
    `).join('');

    modalRoot.innerHTML = `
      <div class="modal-overlay" id="detail-modal-overlay">
        <div class="modal-card">
          <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 16px;">
            <div>
              <div style="font-size: 0.6875rem; text-transform: uppercase; color: var(--text-tertiary);">Detalle del Movimiento</div>
              <h2 style="font-size: 1.125rem;">${m.payload?.remote_id || m.id}</h2>
            </div>
            <button id="modal-close-btn" style="background: none; border: none; font-size: 20px; color: var(--text-secondary); cursor: pointer;">&times;</button>
          </div>

          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 16px; background: var(--bg-elevated); padding: 12px; border-radius: 8px;">
            <div>
              <div style="font-size: 0.6875rem; color: var(--text-tertiary);">ESTADO ACTUAL</div>
              <div style="margin-top: 4px;">${renderStatusBadge(m.state)}</div>
            </div>
            <div>
              <div style="font-size: 0.6875rem; color: var(--text-tertiary);">DESTINO POI</div>
              <div style="font-size: 0.8125rem; font-weight: 500; margin-top: 4px;">${m.payload?.poi_id || '—'}</div>
            </div>
            <div>
              <div style="font-size: 0.6875rem; color: var(--text-tertiary);">EQUIPO</div>
              <div style="font-size: 0.8125rem; font-weight: 500; margin-top: 4px;">${m.source_equipment?.name || '—'} (${m.source_equipment?.asset_number || '—'})</div>
            </div>
            <div>
              <div style="font-size: 0.6875rem; color: var(--text-tertiary);">PROGRAMACIÓN</div>
              <div class="text-mono" style="font-size: 0.8125rem; margin-top: 4px;">${m.payload?.start_date} ${m.payload?.start_time}</div>
            </div>
          </div>

          <div style="margin-bottom: 16px;">
            <div style="font-size: 0.75rem; font-weight: 600; text-transform: uppercase; margin-bottom: 8px;">Payload para Startrack</div>
            <pre style="background: var(--bg-primary); padding: 10px; border-radius: 6px; font-size: 0.75rem; overflow-x: auto; color: var(--brand-light);">${JSON.stringify(m.payload, null, 2)}</pre>
          </div>

          <div style="margin-bottom: 20px;">
            <div style="font-size: 0.75rem; font-weight: 600; text-transform: uppercase; margin-bottom: 8px;">Historial de Eventos del Libro Mayor</div>
            <div>${eventsHtml || '<div style="font-size: 0.75rem; color: var(--text-tertiary);">Sin eventos registrados</div>'}</div>
          </div>

          <!-- Actions -->
          <div style="display: flex; gap: 8px; justify-content: flex-end; border-top: 1px solid var(--border); padding-top: 16px;">
            ${m.state === 'draft' ? `
              <button id="btn-queue-action" style="background: #2a78d6; color: white; border: none; padding: 8px 14px; border-radius: 4px; cursor: pointer; font-size: 0.8125rem; font-weight: 600;">
                Encolar para Envío
              </button>
            ` : ''}
            ${!m.receipt ? `
              <button id="btn-receipt-action" style="background: #199e70; color: white; border: none; padding: 8px 14px; border-radius: 4px; cursor: pointer; font-size: 0.8125rem; font-weight: 600;">
                Declarar Recepción
              </button>
            ` : '<div style="font-size: 0.8125rem; color: #199e70; display: flex; align-items: center; gap: 4px;">✓ Recepción ya declarada</div>'}
          </div>
        </div>
      </div>
    `;

    modalRoot.querySelector('#modal-close-btn').addEventListener('click', () => {
      modalRoot.innerHTML = '';
    });

    const queueBtn = modalRoot.querySelector('#btn-queue-action');
    if (queueBtn) {
      queueBtn.addEventListener('click', async () => {
        try {
          await api.queueMovement(m.id);
          alert('Movimiento encolado.');
          modalRoot.innerHTML = '';
          await loadData();
        } catch (err) {
          alert(`Error al encolar: ${err.message}`);
        }
      });
    }

    const receiptBtn = modalRoot.querySelector('#btn-receipt-action');
    if (receiptBtn) {
      receiptBtn.addEventListener('click', async () => {
        const receivedBy = prompt('Nombre de quien recibe en obra:', 'Ingeniero Residente');
        if (!receivedBy) return;
        try {
          await api.registerReceipt(m.id, {
            received_by: receivedBy,
            condition: 'OPERATIVO',
            notes: 'Recepción confirmada en destino vía frontend web.',
          });
          alert('Recepción declarada con éxito.');
          modalRoot.innerHTML = '';
          await loadData();
        } catch (err) {
          alert(`Error al registrar recepción: ${err.message}`);
        }
      });
    }
  }

  async function openNewPlanModal() {
    const modalRoot = container.querySelector('#ops-modals');
    let catalogs = { pois: [], users: [] };
    let requests = [];
    let equipments = [];

    try {
      catalogs = await api.getCatalogs();
      const hub = await api.getHub();
      requests = hub.requests || [];
      equipments = hub.equipment || [];
    } catch (_) {}

    modalRoot.innerHTML = `
      <div class="modal-overlay" id="plan-modal-overlay">
        <div class="modal-card">
          <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 16px;">
            <div>
              <h2 style="font-size: 1.125rem;">Nuevo Plan de Traslado</h2>
              <div style="font-size: 0.75rem; color: var(--text-secondary);">El plan se guarda localmente en el registro antes de enviarse a Startrack</div>
            </div>
            <button id="plan-close-btn" style="background: none; border: none; font-size: 20px; color: var(--text-secondary); cursor: pointer;">&times;</button>
          </div>

          <form id="new-plan-form" style="display: flex; flex-direction: column; gap: 12px;">
            <div>
              <label style="font-size: 0.6875rem; font-weight: 600; text-transform: uppercase; color: var(--text-tertiary);">Solicitud Asociada (Prisma)</label>
              <select id="plan-request-id" style="width: 100%; padding: 8px; background: var(--bg-elevated); border: 1px solid var(--border); border-radius: 4px; color: var(--text-primary); margin-top: 4px;">
                ${requests.map(r => `<option value="${r.id}">${r.label} (${r.machinery_type || '—'})</option>`).join('')}
              </select>
            </div>

            <div>
              <label style="font-size: 0.6875rem; font-weight: 600; text-transform: uppercase; color: var(--text-tertiary);">Maquinaria a Mover</label>
              <select id="plan-equipment-id" style="width: 100%; padding: 8px; background: var(--bg-elevated); border: 1px solid var(--border); border-radius: 4px; color: var(--text-primary); margin-top: 4px;">
                ${equipments.map(e => `<option value="${e.id}">${e.asset_number || 'EQ'} · ${e.name} [${e.machinery_status}]</option>`).join('')}
              </select>
            </div>

            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px;">
              <div>
                <label style="font-size: 0.6875rem; font-weight: 600; text-transform: uppercase; color: var(--text-tertiary);">Fecha Programada</label>
                <input type="date" id="plan-date" value="${new Date().toISOString().split('T')[0]}" style="width: 100%; padding: 8px; background: var(--bg-elevated); border: 1px solid var(--border); border-radius: 4px; color: var(--text-primary); margin-top: 4px;" required />
              </div>
              <div>
                <label style="font-size: 0.6875rem; font-weight: 600; text-transform: uppercase; color: var(--text-tertiary);">Hora Programada</label>
                <input type="time" id="plan-time" value="08:00" style="width: 100%; padding: 8px; background: var(--bg-elevated); border: 1px solid var(--border); border-radius: 4px; color: var(--text-primary); margin-top: 4px;" required />
              </div>
            </div>

            <div>
              <label style="font-size: 0.6875rem; font-weight: 600; text-transform: uppercase; color: var(--text-tertiary);">Geocerca de Destino (Startrack POI)</label>
              <select id="plan-poi-id" style="width: 100%; padding: 8px; background: var(--bg-elevated); border: 1px solid var(--border); border-radius: 4px; color: var(--text-primary); margin-top: 4px;">
                ${(catalogs.pois || [{ poi_id: 'POI-PROY-014', name: 'Proyecto Xi - La Unión' }]).map(p => `
                  <option value="${p.poi_id}">${p.poi_id} · ${p.name || ''}</option>
                `).join('')}
              </select>
            </div>

            <div>
              <label style="font-size: 0.6875rem; font-weight: 600; text-transform: uppercase; color: var(--text-tertiary);">Referencia Local (Remote ID)</label>
              <input type="text" id="plan-remote-id" value="MOV-${Math.floor(1000 + Math.random() * 9000)}" style="width: 100%; padding: 8px; background: var(--bg-elevated); border: 1px solid var(--border); border-radius: 4px; color: var(--text-primary); font-family: var(--font-mono); margin-top: 4px;" required />
            </div>

            <div style="display: flex; justify-content: flex-end; gap: 8px; margin-top: 12px;">
              <button type="button" id="plan-cancel-btn" style="background: none; border: 1px solid var(--border); padding: 8px 14px; border-radius: 4px; color: var(--text-secondary); cursor: pointer;">Cancelar</button>
              <button type="submit" style="background: var(--brand); color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer; font-weight: 600;">Guardar Plan</button>
            </div>
          </form>
        </div>
      </div>
    `;

    modalRoot.querySelector('#plan-close-btn').addEventListener('click', () => modalRoot.innerHTML = '');
    modalRoot.querySelector('#plan-cancel-btn').addEventListener('click', () => modalRoot.innerHTML = '');

    modalRoot.querySelector('#new-plan-form').addEventListener('submit', async (e) => {
      e.preventDefault();
      const body = {
        request_id: modalRoot.querySelector('#plan-request-id').value,
        machinery_id: modalRoot.querySelector('#plan-equipment-id').value,
        start_date: modalRoot.querySelector('#plan-date').value,
        start_time: modalRoot.querySelector('#plan-time').value + ':00',
        poi_id: modalRoot.querySelector('#plan-poi-id').value,
        remote_id: modalRoot.querySelector('#plan-remote-id').value,
        assigned_user_ids: ['USR-START-01'],
      };

      try {
        await api.savePlan(body);
        alert('Plan de traslado guardado con éxito.');
        modalRoot.innerHTML = '';
        await loadData();
      } catch (err) {
        alert(`Error al guardar plan: ${err.message}`);
      }
    });
  }

  await loadData();
}
