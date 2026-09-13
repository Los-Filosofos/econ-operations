import { api } from '../api.js';

export async function renderFinancialRadarView(container) {
  let selectedRole = 'gerencia_proyecto';
  let isSigned = false;
  let signedHash = '';
  let signedDate = '';

  function generateMockHash() {
    const chars = '0123456789abcdef';
    let hash = 'sha256:';
    for (let i = 0; i < 64; i++) {
      hash += chars[Math.floor(Math.random() * chars.length)];
    }
    return hash;
  }

  function render() {
    container.innerHTML = `
      <div class="radar-container fade-in">
        <!-- Hero ROI Banner -->
        <div class="radar-roi-banner">
          <div>
            <div style="font-size: 0.8125rem; font-weight: 700; color: #34d399; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 4px;">
              Diferenciador Exclusivo · Retorno de Inversión (ROI)
            </div>
            <h1 style="font-size: 1.8rem; font-weight: 800; color: #ffffff; margin-bottom: 6px;">
              Radar de Fugas Financieras & Discrepancias Operativas
            </h1>
            <div style="font-size: 0.875rem; color: #c7d2fe; max-width: 680px;">
              ECON Hub no solo visualiza datos: actúa como un cortafuegos activo que detiene costos ocultos y blinda legalmente la entrega física de maquinaria.
            </div>
          </div>

          <div style="text-align: right; background: rgba(0,0,0,0.3); padding: 16px 24px; border-radius: var(--radius-md); border: 1px solid rgba(52, 211, 153, 0.3);">
            <div style="font-size: 0.75rem; font-weight: 600; color: #a7f3d0; text-transform: uppercase;">Costo de Fricción Evitado</div>
            <div class="radar-roi-amount">+$3,050 USD</div>
            <div style="font-size: 0.75rem; color: #86efac; margin-top: 2px;">en la muestra auditada de 2 solicitudes</div>
          </div>
        </div>

        <!-- 3 Critical Financial Leakage Cards -->
        <div class="leakage-grid">
          <!-- Card 1: Flete en Falso -->
          <div class="leakage-card leakage-card--critical">
            <div>
              <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
                <span style="font-size: 0.75rem; font-weight: 700; color: #f87171; text-transform: uppercase;">Guardia R2 · Taller Central</span>
                <span style="background: rgba(239, 68, 68, 0.15); border: 1px solid rgba(239, 68, 68, 0.4); color: #fca5a5; font-size: 0.6875rem; font-weight: 700; padding: 2px 8px; border-radius: 4px;">
                  RIESGO CRÍTICO DETENIDO
                </span>
              </div>
              <h3 style="font-size: 1.125rem; font-weight: 700; color: #fff; margin-bottom: 6px;">Flete en Falso Bloqueado</h3>
              <p style="font-size: 0.8125rem; color: var(--text-secondary); line-height: 1.5;">
                La unidad <strong>CF-03</strong> tiene avería crítica registrada en taller (falla de motor). Logística intentó generar el despacho documental. La <strong>Guardia R2 bloqueó físicamente</strong> la salida hacia Startrack.
              </p>
            </div>

            <div style="margin-top: 12px; padding-top: 12px; border-top: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center;">
              <div>
                <span style="font-size: 0.6875rem; color: var(--text-tertiary);">Ahorro de Transporte (Cama Baja):</span>
                <div style="font-size: 1.125rem; font-weight: 800; color: #34d399;">+$1,250 USD</div>
              </div>
              <span class="badge-provenance badge-provenance--prisma">Validación Automática</span>
            </div>
          </div>

          <!-- Card 2: Facturación Fantasma -->
          <div class="leakage-card leakage-card--warning">
            <div>
              <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
                <span style="font-size: 0.75rem; font-weight: 700; color: #fbbf24; text-transform: uppercase;">Control de Costos · Cobro a Obra</span>
                <span style="background: rgba(245, 158, 11, 0.15); border: 1px solid rgba(245, 158, 11, 0.4); color: #fde68a; font-size: 0.6875rem; font-weight: 700; padding: 2px 8px; border-radius: 4px;">
                  DESFASE ERP / GPS
                </span>
              </div>
              <h3 style="font-size: 1.125rem; font-weight: 700; color: #fff; margin-bottom: 6px;">Facturación Fantasma Detenida</h3>
              <p style="font-size: 0.8125rem; color: var(--text-secondary); line-height: 1.5;">
                Prisma registra a <strong>CF-03</strong> como «OCUPADA» desde el 11/09. Sin embargo, Startrack confirma que la máquina sigue inmóvil en el predio. ECON frena la imputación indebida de renta interna al proyecto.
              </p>
            </div>

            <div style="margin-top: 12px; padding-top: 12px; border-top: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center;">
              <div>
                <span style="font-size: 0.6875rem; color: var(--text-tertiary);">Sobre-facturación Evitada:</span>
                <div style="font-size: 1.125rem; font-weight: 800; color: #34d399;">+$1,800 USD / sem</div>
              </div>
              <span class="badge-provenance badge-provenance--startrack">Alerta Telemetría</span>
            </div>
          </div>

          <!-- Card 3: Limbo Legal -->
          <div class="leakage-card leakage-card--success">
            <div>
              <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
                <span style="font-size: 0.75rem; font-weight: 700; color: #38bdf8; text-transform: uppercase;">Responsabilidad Civil y Daños</span>
                <span style="background: rgba(56, 189, 248, 0.15); border: 1px solid rgba(56, 189, 248, 0.4); color: #bae6fd; font-size: 0.6875rem; font-weight: 700; padding: 2px 8px; border-radius: 4px;">
                  BLINDAJE JURÍDICO
                </span>
              </div>
              <h3 style="font-size: 1.125rem; font-weight: 700; color: #fff; margin-bottom: 6px;">Cierre de Brecha Legal en Descarga</h3>
              <p style="font-size: 0.8125rem; color: var(--text-secondary); line-height: 1.5;">
                Entrar a una geocerca no prueba que la máquina fue descargada sana y salva. ECON exige que el residente de obra firme el <strong>Acta de Recepción Digital</strong> antes de transferir la responsabilidad civil.
              </p>
            </div>

            <div style="margin-top: 12px; padding-top: 12px; border-top: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center;">
              <div>
                <span style="font-size: 0.6875rem; color: var(--text-tertiary);">Riesgo de Litigio Transporte vs Obra:</span>
                <div style="font-size: 1.125rem; font-weight: 800; color: #38bdf8;">0 Disputas</div>
              </div>
              <span class="badge-provenance badge-provenance--prisma">Ledger Inmutable</span>
            </div>
          </div>
        </div>

        <!-- Interactive Digital Handover Certificate Simulator -->
        <div class="handover-card">
          <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #28374f; padding-bottom: 16px;">
            <div>
              <div style="font-size: 0.75rem; font-weight: 700; color: #818cf8; text-transform: uppercase; letter-spacing: 0.05em;">
                Módulo Transaccional · POST /api/v1/operations/{id}/receipt
              </div>
              <h2 style="font-size: 1.35rem; font-weight: 800; color: #ffffff; margin-top: 2px;">
                Simulador de Acta de Recepción Digital con Sello Forense
              </h2>
            </div>
            <div style="display: flex; align-items: center; gap: 8px;">
              <label style="font-size: 0.75rem; color: var(--text-secondary);">Rol del Firmante:</label>
              <select id="role-selector" style="
                background: #0b0f17;
                border: 1px solid #28374f;
                border-radius: var(--radius-sm);
                color: #fff;
                padding: 6px 12px;
                font-size: 0.75rem;
                font-weight: 600;
              ">
                <option value="gerencia_proyecto" ${selectedRole === 'gerencia_proyecto' ? 'selected' : ''}>Gerencia de Proyecto (Residente de Obra)</option>
                <option value="logistica" ${selectedRole === 'logistica' ? 'selected' : ''}>Logística y Transporte</option>
                <option value="lectura" ${selectedRole === 'lectura' ? 'selected' : ''}>Auditor (Solo Lectura - Sin Permiso)</option>
              </select>
            </div>
          </div>

          <!-- Certificate Details -->
          <div style="display: grid; grid-template-columns: 1.2fr 1fr; gap: 24px;">
            <div>
              <div style="font-size: 0.8125rem; font-weight: 600; color: #fff; margin-bottom: 12px;">
                Verificación de Custodia Física en Destino:
              </div>

              <div style="display: flex; flex-direction: column; gap: 10px; font-size: 0.8125rem; color: #e2e8f0;">
                <label style="display: flex; align-items: center; gap: 10px; cursor: pointer;">
                  <input type="checkbox" checked disabled style="accent-color: #10b981; width: 16px; height: 16px;" />
                  <span>Maquinaria <strong>CF-03 (Cargador frontal)</strong> descargada en plataforma de obra</span>
                </label>
                <label style="display: flex; align-items: center; gap: 10px; cursor: pointer;">
                  <input type="checkbox" checked disabled style="accent-color: #10b981; width: 16px; height: 16px;" />
                  <span>Geocerca <strong>PROY-014 (The Hub - La Unión)</strong> verificada por telemetría</span>
                </label>
                <label style="display: flex; align-items: center; gap: 10px; cursor: pointer;">
                  <input type="checkbox" checked id="chk-condition" style="accent-color: #10b981; width: 16px; height: 16px;" />
                  <span>Inspección visual conforme: sin fugas de aceite ni daños por flete</span>
                </label>
                <label style="display: flex; align-items: center; gap: 10px; cursor: pointer;">
                  <input type="checkbox" checked id="chk-horometer" style="accent-color: #10b981; width: 16px; height: 16px;" />
                  <span>Horómetro de llegada verificado: <strong>1,420.5 horas</strong></span>
                </label>
              </div>

              <div style="margin-top: 16px;">
                <label style="font-size: 0.75rem; color: var(--text-secondary); display: block; margin-bottom: 4px;">Observaciones del Ingeniero Receptor:</label>
                <input type="text" id="receipt-notes" value="Equipo recibido en condiciones operativas óptimas. Listo para jornada." style="
                  width: 100%;
                  background: #0b0f17;
                  border: 1px solid #28374f;
                  border-radius: var(--radius-sm);
                  padding: 8px 12px;
                  color: #fff;
                  font-size: 0.8125rem;
                " />
              </div>
            </div>

            <!-- Signature Seal Panel -->
            <div style="
              background: #0b0f17;
              border: 1px solid #28374f;
              border-radius: var(--radius-md);
              padding: 20px;
              display: flex;
              flex-direction: column;
              justify-content: space-between;
            ">
              <div>
                <div style="font-size: 0.75rem; font-weight: 700; color: var(--text-secondary); text-transform: uppercase; margin-bottom: 6px;">
                  Firma Electrónica & Sello Criptográfico
                </div>
                ${!isSigned ? `
                  <div style="color: var(--text-secondary); font-size: 0.8125rem; line-height: 1.5; margin-bottom: 16px;">
                    Al firmar, se generará una mutación atómica en PostgreSQL dentro de la tabla <code>operation_events</code> protegida por triggers que prohíben <code>UPDATE</code> o <code>DELETE</code>.
                  </div>
                ` : `
                  <div style="display: flex; flex-direction: column; gap: 8px; margin-bottom: 16px;">
                    <div style="display: flex; align-items: center; gap: 8px; color: #34d399; font-weight: 700; font-size: 0.875rem;">
                      <span>✓ ACTA FORMALIZADA EN LEDGER</span>
                    </div>
                    <div class="seal-badge" style="word-break: break-all;">
                      ${signedHash}
                    </div>
                    <div style="font-size: 0.75rem; color: var(--text-secondary);">
                      Fecha de firma: <strong>${signedDate}</strong>
                    </div>
                    <div style="font-size: 0.75rem; color: #93c5fd;">
                      Actor: <strong>Ing. Roberto Palacios (${selectedRole})</strong>
                    </div>
                  </div>
                `}
              </div>

              <div>
                ${selectedRole === 'lectura' ? `
                  <div style="background: rgba(239, 68, 68, 0.15); border: 1px solid rgba(239, 68, 68, 0.4); color: #fca5a5; padding: 10px; border-radius: 4px; font-size: 0.75rem; text-align: center;">
                    ⛔ El rol de solo lectura no tiene permiso <code>declare_reception</code>.
                  </div>
                ` : !isSigned ? `
                  <button id="btn-sign-receipt" style="
                    width: 100%;
                    background: #10b981;
                    border: 1px solid #34d399;
                    color: #fff;
                    padding: 10px;
                    border-radius: var(--radius-sm);
                    font-size: 0.875rem;
                    font-weight: 700;
                    cursor: pointer;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    gap: 8px;
                    box-shadow: 0 0 15px rgba(16, 185, 129, 0.3);
                  ">
                    <span>✍ Firmar y Sellar Acta Digital</span>
                  </button>
                ` : `
                  <button id="btn-reset-receipt" style="
                    width: 100%;
                    background: var(--bg-elevated);
                    border: 1px solid var(--border);
                    color: var(--text-secondary);
                    padding: 8px;
                    border-radius: var(--radius-sm);
                    font-size: 0.75rem;
                    font-weight: 600;
                    cursor: pointer;
                  ">
                    Reiniciar Simulación de Firma
                  </button>
                `}
              </div>
            </div>
          </div>
        </div>
      </div>
    `;

    // Event listeners
    const roleSel = container.querySelector('#role-selector');
    if (roleSel) {
      roleSel.addEventListener('change', (e) => {
        selectedRole = e.target.value;
        render();
      });
    }

    const signBtn = container.querySelector('#btn-sign-receipt');
    if (signBtn) {
      signBtn.addEventListener('click', () => {
        isSigned = true;
        signedHash = generateMockHash();
        signedDate = new Date().toISOString().replace('T', ' ').substring(0, 19) + ' UTC';
        render();
      });
    }

    const resetBtn = container.querySelector('#btn-reset-receipt');
    if (resetBtn) {
      resetBtn.addEventListener('click', () => {
        isSigned = false;
        signedHash = '';
        signedDate = '';
        render();
      });
    }
  }

  render();
}
