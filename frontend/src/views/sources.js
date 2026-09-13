import { api } from '../api.js';
import { renderStatusBadge } from '../components/status-badge.js';
import { renderCard } from '../components/card.js';

export async function renderSourcesView(container) {
  container.innerHTML = `
    <div class="page-header fade-in">
      <div>
        <h1 class="page-header__title">Fuentes de Datos & Cobertura</h1>
        <div class="page-header__subtitle">Auditoría de proveniencia, conectores activos y alcance de las observaciones</div>
      </div>
    </div>

    <!-- Health & Status Cards -->
    <div class="indicators-grid fade-in stagger-1" id="sources-cards-container">
      <div style="color: var(--text-secondary); padding: 16px;">Cargando estado de fuentes...</div>
    </div>

    <!-- Sources Detail List -->
    <div class="fade-in stagger-2" id="sources-detail-container" style="display: flex; flex-direction: column; gap: 16px;"></div>
  `;

  try {
    const [hub, status] = await Promise.all([api.getHub(), api.getStatus()]);
    const sources = hub.sources || [];

    // System summary cards
    container.querySelector('#sources-cards-container').innerHTML = `
      ${renderCard({
        title: status.mode.toUpperCase(),
        subtitle: 'MODO DE LECTURA',
        value: status.mode === 'fixture' ? 'Documental' : 'En Vivo',
        secondaryValue: 'Entorno de datos consultado',
        accentColor: status.mode === 'live' ? '#199e70' : '#5a8dbc',
      })}
      ${renderCard({
        title: 'Sincronizador',
        subtitle: 'CICLO AUTOMÁTICO',
        value: status.sync?.enabled ? 'Activo' : 'Desactivado',
        secondaryValue: `Intervalo: ${status.sync?.interval_seconds || 0}s`,
        accentColor: status.sync?.enabled ? '#199e70' : '#868e96',
      })}
      ${renderCard({
        title: 'Versión del Registro',
        subtitle: 'HASH LOCAL (ALEMBIC)',
        value: status.registry_version?.slice(0, 8) || 'e65705db',
        secondaryValue: 'Esquema de base de datos verificado',
        accentColor: '#4a3aa7',
      })}
    `;

    // Detailed sources
    container.querySelector('#sources-detail-container').innerHTML = sources.map(src => `
      <div style="
        background: var(--bg-surface);
        border: 1px solid var(--border);
        border-radius: var(--radius-lg);
        padding: var(--sp-5);
      ">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
          <div>
            <div style="font-size: 0.6875rem; font-weight: 600; text-transform: uppercase; color: var(--text-tertiary);">SISTEMA PROVEEDOR</div>
            <h2 style="font-size: 1.125rem;">${src.name || src.id}</h2>
          </div>
          ${renderStatusBadge(src.status === 'ok' ? 'DISPONIBLE' : 'PENDIENTE', src.status || 'CONECTADO')}
        </div>

        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; margin-bottom: 12px; background: var(--bg-elevated); padding: 12px; border-radius: 6px;">
          <div>
            <div style="font-size: 0.6875rem; color: var(--text-tertiary);">ENTORNO</div>
            <div style="font-size: 0.8125rem; font-weight: 500; margin-top: 2px;">${src.environment || 'sandbox'}</div>
          </div>
          <div>
            <div style="font-size: 0.6875rem; color: var(--text-tertiary);">TIPO DE EVIDENCIA</div>
            <div style="font-size: 0.8125rem; font-weight: 500; margin-top: 2px;">${src.evidence_kind || 'provided_sample'}</div>
          </div>
          <div>
            <div style="font-size: 0.6875rem; color: var(--text-tertiary);">COBERTURA</div>
            <div style="font-size: 0.8125rem; font-weight: 500; margin-top: 2px;">${src.coverage || 'acotada (sin corte conjunto)'}</div>
          </div>
          <div>
            <div style="font-size: 0.6875rem; color: var(--text-tertiary);">CORTE TEMPORAL</div>
            <div class="text-mono" style="font-size: 0.8125rem; margin-top: 2px;">${src.data_as_of || 'null (muestra)'}</div>
          </div>
        </div>

        <div style="font-size: 0.75rem; color: var(--text-secondary); line-height: 1.5;">
          ${src.notes || src.description || 'Fuente registrada en el conector de integración.'}
        </div>
      </div>
    `).join('');

  } catch (err) {
    container.querySelector('#sources-cards-container').innerHTML = `
      <div style="color: #d03b3b; padding: 20px;">Error al consultar fuentes: ${err.message}</div>
    `;
  }
}
