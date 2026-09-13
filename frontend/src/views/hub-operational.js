import { api } from '../api.js';

export async function renderHubOperationalView(container) {
  let activeUnitCode = 'CF-03';
  let activeScope = 'reference'; // 'reference' (CF-03 / PROY-014) or 'team6' (RE-03 / PROY-006)
  let hubData = null;

  try {
    hubData = await api.getHub();
  } catch (err) {
    console.error('Error al consultar datos de /hub:', err);
  }

  function render() {
    const isReference = activeScope === 'reference';

    // Reference case (Slide 4 exact values) vs Team 6 case
    const projectCode = isReference ? 'PROY-014' : 'PROY-006';
    const projectName = isReference ? 'PROY-014 · The Hub - La Unión' : 'PROY-006 · Proyecto Zeta';
    const requestsCount = isReference ? '2 solicitudes' : '1 solicitud';
    const unitCode = isReference ? 'CF-03' : 'RE-03';
    const unitName = isReference ? 'Cargador frontal 03' : 'Retroexcavadora 03';
    const unitStatus = isReference ? 'Obsoleta' : 'Disponible';
    const unitStatusWarning = isReference; // Obsoleta has warning
    const prismaStatus = isReference ? 'Aprobada' : 'Aprobada';
    const transferStatus = isReference ? 'Pendiente' : 'En tránsito';
    const assignmentPeriod = isReference ? '11 Sep 2026 → 14 Sep 2026' : '12 Sep 2026 → 18 Sep 2026';
    const docDate = isReference ? '12/09/2026' : '12/09/2026';
    const telemetryQueryDate = '13/09/2026 08:54 UTC';
    const evidenceText = isReference
      ? 'Documental, no confirma presencia física'
      : 'Telemetría GPS confirmada en geocerca de origen';

    container.innerHTML = `
      <div class="hub-operational-layout fade-in">
        <!-- Main Column -->
        <div class="hub-main-column">
          <!-- Slide 4 Intro Banner -->
          <div class="hub-intro-card">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 12px;">
              <div>
                <div class="hub-intro-tag">3. El Hub</div>
                <h1 class="hub-intro-title">Un visualizador de datos con ownership claro</h1>
                <div class="hub-intro-subtitle">
                  ECON Hub reúne información de ambos sistemas y deja visible de dónde viene cada dato.
                </div>
              </div>

              <!-- Scope Toggle (CF-03 vs RE-03) -->
              <div style="display: flex; gap: 8px; background: rgba(0,0,0,0.3); padding: 4px; border-radius: var(--radius-md); border: 1px solid var(--border);">
                <button id="toggle-scope-ref" style="
                  background: ${isReference ? 'var(--brand)' : 'transparent'};
                  color: ${isReference ? '#fff' : 'var(--text-secondary)'};
                  border: none;
                  padding: 6px 12px;
                  border-radius: var(--radius-sm);
                  font-size: 0.75rem;
                  font-weight: 600;
                  cursor: pointer;
                  display: flex;
                  align-items: center;
                  gap: 6px;
                ">
                  <span>📋 Caso Referencia (CF-03)</span>
                </button>
                <button id="toggle-scope-team" style="
                  background: ${!isReference ? 'var(--brand)' : 'transparent'};
                  color: ${!isReference ? '#fff' : 'var(--text-secondary)'};
                  border: none;
                  padding: 6px 12px;
                  border-radius: var(--radius-sm);
                  font-size: 0.75rem;
                  font-weight: 600;
                  cursor: pointer;
                  display: flex;
                  align-items: center;
                  gap: 6px;
                ">
                  <span>🎯 Kit Equipo (RE-03)</span>
                </button>
              </div>
            </div>
          </div>

          <!-- Connected Platforms Banner (Prisma <--> Startrack) -->
          <div class="hub-connected-banner">
            <!-- Prisma Card -->
            <div class="hub-platform-card hub-platform-card--prisma">
              <div class="hub-platform-icon">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M12 2L2 7l10 5 10-5-10-5z"></path>
                  <path d="M2 17l10 5 10-5"></path>
                  <path d="M2 12l10 5 10-5"></path>
                </svg>
              </div>
              <div>
                <div class="hub-platform-title">Prisma</div>
                <div class="hub-platform-meta">${projectCode}</div>
                <div class="hub-platform-detail">${requestsCount}</div>
              </div>
            </div>

            <!-- Central Bridge -->
            <div class="hub-connection-bridge">
              <div class="hub-connection-badge">
                <div class="hub-connection-dots">
                  <span class="hub-connection-dot"></span>
                  <span class="hub-connection-dot"></span>
                </div>
                <span>Datos conectados</span>
              </div>
            </div>

            <!-- Startrack Card -->
            <div class="hub-platform-card hub-platform-card--startrack">
              <div class="hub-platform-icon">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <polygon points="12 2 19 21 12 17 5 21 12 2"></polygon>
                </svg>
              </div>
              <div>
                <div class="hub-platform-title">Startrack</div>
                <div class="hub-platform-meta">${unitCode}</div>
                <div class="hub-platform-detail">${unitName}</div>
              </div>
            </div>
          </div>

          <!-- Consolidated Information (5 Cards Grid) -->
          <div class="hub-consolidated-section">
            <div class="hub-consolidated-header">
              <span>Información consolidada</span>
              <a href="#/movilidad" style="font-size: 0.8125rem; font-weight: 500; display: inline-flex; align-items: center; gap: 4px;">
                <span>Ver Trazabilidad y Movilidad</span>
                <span>→</span>
              </a>
            </div>

            <div class="hub-consolidated-grid">
              <!-- Card 1: Estado Prisma -->
              <div class="hub-attr-card">
                <div class="hub-attr-top">
                  <span class="hub-attr-label">Estado Prisma</span>
                  <span class="badge-provenance badge-provenance--prisma">Dato Prisma</span>
                </div>
                <div class="hub-attr-value" style="display: flex; align-items: center; gap: 6px;">
                  <span style="color: #34d399;">✓</span>
                  <span>${prismaStatus}</span>
                </div>
              </div>

              <!-- Card 2: Estado maquinaria -->
              <div class="hub-attr-card">
                <div class="hub-attr-top">
                  <span class="hub-attr-label">Estado maquinaria</span>
                  <span class="badge-provenance badge-provenance--startrack">Dato Startrack</span>
                </div>
                <div class="hub-attr-value" style="display: flex; align-items: center; gap: 6px;">
                  ${unitStatusWarning ? '<span style="color: #fbbf24;">⚠</span>' : '<span style="color: #34d399;">●</span>'}
                  <span>${unitStatus}</span>
                </div>
              </div>

              <!-- Card 3: Estado de traslado -->
              <div class="hub-attr-card">
                <div class="hub-attr-top">
                  <span class="hub-attr-label">Estado de traslado</span>
                  <span class="badge-provenance badge-provenance--startrack">Dato Startrack</span>
                </div>
                <div class="hub-attr-value" style="display: flex; align-items: center; gap: 6px;">
                  <span style="color: #fbbf24;">⏱</span>
                  <span>${transferStatus}</span>
                </div>
              </div>

              <!-- Card 4: Origen -->
              <div class="hub-attr-card">
                <div class="hub-attr-top">
                  <span class="hub-attr-label">Origen</span>
                  <span class="badge-provenance badge-provenance--prisma">Dato Prisma</span>
                </div>
                <div class="hub-attr-value" style="font-size: 1rem; color: #c7d2fe;">
                  Prisma
                </div>
              </div>

              <!-- Card 5: Fuente complementaria -->
              <div class="hub-attr-card">
                <div class="hub-attr-top">
                  <span class="hub-attr-label">Fuente complementaria</span>
                  <span class="badge-provenance badge-provenance--startrack">Dato Startrack</span>
                </div>
                <div class="hub-attr-value" style="font-size: 1rem; color: #fecaca;">
                  Startrack
                </div>
              </div>
            </div>
          </div>

          <!-- Bottom Action Cards -->
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: var(--sp-4);">
            <div style="
              background: var(--bg-surface);
              border: 1px solid var(--border);
              border-radius: var(--radius-md);
              padding: var(--sp-4) var(--sp-5);
              display: flex;
              align-items: center;
              justify-content: space-between;
            ">
              <div>
                <div style="font-size: 0.8125rem; font-weight: 600; color: #fff;">Optimizador de Traslados (Lámina 5)</div>
                <div style="font-size: 0.75rem; color: var(--text-secondary); margin-top: 2px;">Simulación de rutas y ahorro del -18% en flete</div>
              </div>
              <a href="#/movilidad" style="
                background: var(--brand);
                color: #fff;
                padding: 6px 14px;
                border-radius: var(--radius-sm);
                font-size: 0.75rem;
                font-weight: 600;
              ">Explorar Rutas</a>
            </div>

            <div style="
              background: var(--bg-surface);
              border: 1px solid var(--border);
              border-radius: var(--radius-md);
              padding: var(--sp-4) var(--sp-5);
              display: flex;
              align-items: center;
              justify-content: space-between;
            ">
              <div>
                <div style="font-size: 0.8125rem; font-weight: 600; color: #fff;">Presentación Ejecutiva (Deck PPT)</div>
                <div style="font-size: 0.75rem; color: var(--text-secondary); margin-top: 2px;">Navegar las 6 láminas interactivas del pitch</div>
              </div>
              <a href="#/presentacion" style="
                background: var(--bg-elevated);
                border: 1px solid var(--border);
                color: var(--text-primary);
                padding: 6px 14px;
                border-radius: var(--radius-sm);
                font-size: 0.75rem;
                font-weight: 600;
              ">Abrir Pitch</a>
            </div>
          </div>
        </div>

        <!-- Right Inspection Drawer (Slide 4 Right Panel) -->
        <aside class="hub-inspector">
          <div class="hub-inspector-header">
            <div class="hub-inspector-badge-row">
              <span style="font-size: 0.75rem; color: var(--text-secondary); font-family: var(--font-mono);">${unitCode}</span>
              ${unitStatusWarning ? '<span class="hub-warning-tag">⚠ OBSOLETA</span>' : '<span style="color: #34d399; font-size: 0.75rem; font-weight: 600;">OPERATIVA</span>'}
            </div>
            <div class="hub-inspector-title">${unitCode} · ${unitName}</div>
            <div class="hub-inspector-subtitle">Ficha con trazabilidad y ownership explícito</div>
          </div>

          <div class="hub-inspector-list">
            <!-- Row: Proyecto -->
            <div class="hub-inspector-item">
              <span class="hub-inspector-item-label">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="7"></rect><rect x="14" y="3" width="7" height="7"></rect><rect x="14" y="14" width="7" height="7"></rect><rect x="3" y="14" width="7" height="7"></rect></svg>
                <span>Proyecto</span>
              </span>
              <div class="hub-inspector-item-content">
                <span class="hub-inspector-item-val">${projectCode}</span>
                <span class="badge-provenance badge-provenance--prisma">Dato Prisma</span>
              </div>
            </div>

            <!-- Row: Período -->
            <div class="hub-inspector-item">
              <span class="hub-inspector-item-label">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect><line x1="16" y1="2" x2="16" y2="6"></line><line x1="8" y1="2" x2="8" y2="6"></line><line x1="3" y1="10" x2="21" y2="10"></line></svg>
                <span>Período</span>
              </span>
              <div class="hub-inspector-item-content">
                <span class="hub-inspector-item-val">${assignmentPeriod}</span>
                <span class="badge-provenance badge-provenance--prisma">Dato Prisma</span>
              </div>
            </div>

            <!-- Row: Fecha documental -->
            <div class="hub-inspector-item">
              <span class="hub-inspector-item-label">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg>
                <span>Fecha documental</span>
              </span>
              <div class="hub-inspector-item-content">
                <span class="hub-inspector-item-val">${docDate}</span>
                <span class="badge-provenance badge-provenance--prisma">Dato Prisma</span>
              </div>
            </div>

            <!-- Row: Consulta Telemetría -->
            <div class="hub-inspector-item">
              <span class="hub-inspector-item-label">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>
                <span>Consulta</span>
              </span>
              <div class="hub-inspector-item-content">
                <span class="hub-inspector-item-val">${telemetryQueryDate}</span>
                <span class="badge-provenance badge-provenance--startrack">Dato Startrack</span>
              </div>
            </div>

            <!-- Row: Estado Prisma -->
            <div class="hub-inspector-item">
              <span class="hub-inspector-item-label">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>
                <span>Estado Prisma</span>
              </span>
              <div class="hub-inspector-item-content">
                <span class="hub-inspector-item-val" style="color: #34d399;">${prismaStatus}</span>
                <span class="badge-provenance badge-provenance--prisma">Dato Prisma</span>
              </div>
            </div>

            <!-- Row: Estado maquinaria -->
            <div class="hub-inspector-item">
              <span class="hub-inspector-item-label">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>
                <span>Estado maquinaria</span>
              </span>
              <div class="hub-inspector-item-content">
                <span class="hub-inspector-item-val" style="color: ${unitStatusWarning ? '#fbbf24' : '#34d399'};">${unitStatus}</span>
                <span class="badge-provenance badge-provenance--startrack">Dato Startrack</span>
              </div>
            </div>

            <!-- Row: Estado de traslado -->
            <div class="hub-inspector-item">
              <span class="hub-inspector-item-label">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="17 1 21 5 17 9"></polyline><path d="M3 11V9a4 4 0 0 1 4-4h14"></path><polyline points="7 23 3 19 7 15"></polyline><path d="M21 13v2a4 4 0 0 1-4 4H3"></path></svg>
                <span>Estado traslado</span>
              </span>
              <div class="hub-inspector-item-content">
                <span class="hub-inspector-item-val">${transferStatus}</span>
                <span class="badge-provenance badge-provenance--startrack">Dato Startrack</span>
              </div>
            </div>

            <!-- Row: Evidencia -->
            <div class="hub-inspector-item" style="border-bottom: none;">
              <span class="hub-inspector-item-label" style="align-self: flex-start;">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"></circle><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path></svg>
                <span>Evidencia</span>
              </span>
              <div class="hub-inspector-item-content" style="max-width: 170px;">
                <span class="hub-inspector-item-val" style="font-size: 0.75rem; line-height: 1.3;">${evidenceText}</span>
                <span class="badge-provenance badge-provenance--prisma" style="margin-top: 4px;">Dato Prisma</span>
              </div>
            </div>
          </div>
        </aside>
      </div>
    `;

    // Event listeners
    const btnRef = container.querySelector('#toggle-scope-ref');
    const btnTeam = container.querySelector('#toggle-scope-team');
    if (btnRef) {
      btnRef.addEventListener('click', () => {
        activeScope = 'reference';
        render();
      });
    }
    if (btnTeam) {
      btnTeam.addEventListener('click', () => {
        activeScope = 'team6';
        render();
      });
    }
  }

  render();
}
