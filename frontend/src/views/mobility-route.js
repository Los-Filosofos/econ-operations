export async function renderMobilityRouteView(container) {
  let selectedUnit = 'CF-07'; // Default recommendation

  function render() {
    const isCF07 = selectedUnit === 'CF-07';

    container.innerHTML = `
      <div class="mobility-container fade-in">
        <!-- Slide 5 Header -->
        <div class="mobility-header">
          <div class="hub-intro-tag">4. Trazabilidad y Movilidad</div>
          <h1 class="hub-intro-title">Mover mejor la maquinaria también es ahorro</h1>
          <div class="hub-intro-subtitle">
            La trazabilidad permite decidir cuál máquina mover, cuánto tarda y cuál alternativa reduce costo.
          </div>
        </div>

        <!-- Main Content Grid (Map + Route Comparison Cards) -->
        <div class="mobility-main-grid">
          <!-- Interactive Route Canvas / Map -->
          <div class="mobility-map-card">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
              <span style="font-size: 0.875rem; font-weight: 600; color: #fff;">Simulador de Despacho y Rutas GPS</span>
              <span style="font-size: 0.75rem; color: var(--text-secondary);">Red Vial & Geocercas Startrack</span>
            </div>

            <div class="mobility-canvas-wrap">
              <svg width="100%" height="100%" viewBox="0 0 600 320" style="position: absolute; top:0; left:0; overflow: visible;">
                <defs>
                  <!-- Glow filter -->
                  <filter id="glow-blue" x="-20%" y="-20%" width="140%" height="140%">
                    <feGaussianBlur stdDeviation="3" result="blur" />
                    <feComposite in="SourceGraphic" in2="blur" operator="over" />
                  </filter>
                  <filter id="glow-green" x="-20%" y="-20%" width="140%" height="140%">
                    <feGaussianBlur stdDeviation="3" result="blur" />
                    <feComposite in="SourceGraphic" in2="blur" operator="over" />
                  </filter>
                </defs>

                <!-- Grid lines background -->
                <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
                  <path d="M 40 0 L 0 0 0 40" fill="none" stroke="rgba(255, 255, 255, 0.03)" stroke-width="1"/>
                </pattern>
                <rect width="600" height="320" fill="url(#grid)" />

                <!-- Route 1: CF-03 to PROY-014 (Longer route: 27 km, 1h 25m) -->
                <!-- Path points: (100, 220) -> (180, 160) -> (300, 120) -> (480, 120) -->
                <path d="M 110 220 C 140 130, 220 120, 310 125 C 380 130, 420 120, 480 120"
                      fill="none"
                      stroke="${!isCF07 ? '#38bdf8' : 'rgba(56, 189, 248, 0.3)'}"
                      stroke-width="${!isCF07 ? '4' : '2'}"
                      stroke-linecap="round"
                      filter="${!isCF07 ? 'url(#glow-blue)' : 'none'}" />

                <!-- Route 2: CF-07 to PROY-014 (Optimized short route: 14 km, 42m) -->
                <!-- Path points: (240, 250) -> (330, 210) -> (480, 120) -->
                <path d="M 240 240 C 310 230, 390 190, 480 120"
                      fill="none"
                      stroke="${isCF07 ? '#34d399' : 'rgba(52, 211, 153, 0.3)'}"
                      stroke-width="${isCF07 ? '4' : '2'}"
                      stroke-dasharray="${isCF07 ? 'none' : '5,5'}"
                      stroke-linecap="round"
                      filter="${isCF07 ? 'url(#glow-green)' : 'none'}" />

                <!-- Node 1: CF-03 Origin -->
                <g transform="translate(110, 220)" style="cursor: pointer;" id="node-cf03">
                  <circle r="22" fill="rgba(56, 189, 248, 0.15)" stroke="#38bdf8" stroke-width="1.5" />
                  <circle r="6" fill="#38bdf8" />
                  <!-- Tooltip / Label -->
                  <rect x="-45" y="28" width="90" height="36" rx="4" fill="#162032" stroke="#263348" />
                  <text x="0" y="44" fill="#ffffff" font-size="10" font-weight="700" text-anchor="middle">CF-03</text>
                  <text x="0" y="56" fill="#8b949e" font-size="8" text-anchor="middle">Programable</text>
                </g>

                <!-- Label for Route 1 (CF-03) -->
                <g transform="translate(240, 95)">
                  <rect x="-38" y="-12" width="76" height="24" rx="12" fill="#111827" stroke="#38bdf8" stroke-width="1" />
                  <text x="0" y="3" fill="#38bdf8" font-size="9" font-weight="600" text-anchor="middle">1 h 25 min · 27 km</text>
                </g>

                <!-- Node 2: CF-07 Origin (Alternative) -->
                <g transform="translate(240, 240)" style="cursor: pointer;" id="node-cf07">
                  <circle r="22" fill="rgba(52, 211, 153, 0.15)" stroke="#34d399" stroke-width="2" />
                  <circle r="6" fill="#34d399" />
                  <!-- Tooltip / Label -->
                  <rect x="-45" y="28" width="90" height="36" rx="4" fill="#162032" stroke="#10b981" />
                  <text x="0" y="44" fill="#34d399" font-size="10" font-weight="700" text-anchor="middle">CF-07</text>
                  <text x="0" y="56" fill="#a7f3d0" font-size="8" text-anchor="middle">Disponible</text>
                </g>

                <!-- Label for Route 2 (CF-07) -->
                <g transform="translate(340, 190)">
                  <rect x="-35" y="-12" width="70" height="24" rx="12" fill="#111827" stroke="#34d399" stroke-width="1" />
                  <text x="0" y="3" fill="#34d399" font-size="9" font-weight="600" text-anchor="middle">42 min · 14 km</text>
                </g>

                <!-- Node 3: PROY-014 Destination -->
                <g transform="translate(480, 120)">
                  <circle r="26" fill="rgba(99, 102, 241, 0.2)" stroke="#818cf8" stroke-width="2" />
                  <circle r="8" fill="#6366f1" />
                  <!-- Pin Icon / Label -->
                  <rect x="-45" y="-45" width="90" height="36" rx="4" fill="#162032" stroke="#6366f1" />
                  <text x="0" y="-29" fill="#c7d2fe" font-size="10" font-weight="700" text-anchor="middle">PROY-014</text>
                  <text x="0" y="-17" fill="#818cf8" font-size="8" text-anchor="middle">DESTINO</text>
                </g>
              </svg>
            </div>
            <div style="font-size: 0.75rem; color: var(--text-tertiary); margin-top: 8px; text-align: right;">
              Haz clic en una opción de la derecha o en los nodos del mapa para evaluar la ruta.
            </div>
          </div>

          <!-- Comparison Cards Column -->
          <div class="mobility-cards-column">
            <!-- Option 1: CF-03 -->
            <div class="mobility-option-card ${!isCF07 ? 'mobility-option-card--active' : ''}" id="card-cf03">
              <div class="mobility-option-header">
                <div style="display: flex; align-items: center; gap: 8px;">
                  <div style="font-size: 1.25rem;">🚜</div>
                  <div>
                    <div style="font-size: 1rem; font-weight: 700; color: #fff;">CF-03</div>
                    <div style="font-size: 0.75rem; color: var(--text-secondary);">Cargador frontal</div>
                  </div>
                </div>
                <span class="badge-provenance badge-provenance--prisma" style="border-color: #38bdf8; color: #38bdf8;">
                  PROGRAMABLE
                </span>
              </div>

              <div class="mobility-metrics-row">
                <div class="mobility-metric-box">
                  <span class="mobility-metric-label">⏱ ETA</span>
                  <span class="mobility-metric-val">1 h 25 min</span>
                </div>
                <div class="mobility-metric-box">
                  <span class="mobility-metric-label">📍 Distancia</span>
                  <span class="mobility-metric-val">27 km</span>
                </div>
                <div class="mobility-metric-box">
                  <span class="mobility-metric-label">🏁 Destino</span>
                  <span class="mobility-metric-val" style="font-size: 0.8125rem;">PROY-014</span>
                </div>
              </div>
            </div>

            <!-- Option 2: CF-07 (Smart Alternative) -->
            <div class="mobility-option-card ${isCF07 ? 'mobility-option-card--active mobility-option-card--recommended' : ''}" id="card-cf07">
              <div class="mobility-option-header">
                <div style="display: flex; align-items: center; gap: 8px;">
                  <div style="font-size: 1.25rem;">⚡</div>
                  <div>
                    <div style="font-size: 1rem; font-weight: 700; color: #34d399;">CF-07</div>
                    <div style="font-size: 0.75rem; color: var(--text-secondary);">Cargador frontal</div>
                  </div>
                </div>
                <span class="savings-tag">
                  ★ ALTERNATIVA CERCANA
                </span>
              </div>

              <div class="mobility-metrics-row">
                <div class="mobility-metric-box">
                  <span class="mobility-metric-label">⏱ ETA</span>
                  <span class="mobility-metric-val" style="color: #34d399;">42 min</span>
                </div>
                <div class="mobility-metric-box">
                  <span class="mobility-metric-label">📍 Distancia</span>
                  <span class="mobility-metric-val" style="color: #34d399;">14 km</span>
                </div>
                <div class="mobility-metric-box">
                  <span class="mobility-metric-label">💰 Ahorro logístico</span>
                  <span class="mobility-metric-val" style="color: #34d399;">-18%</span>
                </div>
              </div>

              <div style="
                margin-top: 8px;
                padding-top: 10px;
                border-top: 1px solid rgba(52, 211, 153, 0.2);
                display: flex;
                align-items: center;
                justify-content: space-between;
              ">
                <span style="font-size: 0.75rem; color: #a7f3d0;">
                  Unidad disponible en obra colindante
                </span>
                <button id="btn-apply-rec" style="
                  background: #10b981;
                  color: #fff;
                  border: none;
                  padding: 6px 12px;
                  border-radius: var(--radius-sm);
                  font-size: 0.75rem;
                  font-weight: 700;
                  cursor: pointer;
                ">
                  Asignar Alternativa
                </button>
              </div>
            </div>
          </div>
        </div>

        <!-- 4 Fleet Mobility KPIs with sparklines (Slide 5 Bottom) -->
        <div class="mobility-kpi-grid">
          <!-- KPI 1: Horas de trabajo -->
          <div class="mobility-kpi-card">
            <div class="mobility-kpi-top">
              <div>
                <span class="mobility-kpi-label">Horas de trabajo</span>
                <div class="mobility-kpi-val">186 h</div>
              </div>
              <div class="mobility-sparkline">
                <div class="sparkline-bar" style="height: 12px;"></div>
                <div class="sparkline-bar" style="height: 16px;"></div>
                <div class="sparkline-bar" style="height: 14px;"></div>
                <div class="sparkline-bar" style="height: 20px;"></div>
                <div class="sparkline-bar" style="height: 24px; background: #38bdf8;"></div>
              </div>
            </div>
            <div class="mobility-kpi-subtext" style="color: #34d399; font-weight: 600;">
              +12% vs. mes anterior
            </div>
          </div>

          <!-- KPI 2: Uso por maquinaria -->
          <div class="mobility-kpi-card">
            <div class="mobility-kpi-top">
              <div>
                <span class="mobility-kpi-label">Uso por maquinaria</span>
                <div class="mobility-kpi-val">78%</div>
              </div>
              <div class="mobility-sparkline">
                <div class="sparkline-bar" style="height: 14px;"></div>
                <div class="sparkline-bar" style="height: 18px;"></div>
                <div class="sparkline-bar" style="height: 16px;"></div>
                <div class="sparkline-bar" style="height: 22px;"></div>
                <div class="sparkline-bar" style="height: 20px; background: #818cf8;"></div>
              </div>
            </div>
            <div class="mobility-kpi-subtext">
              Promedio de flota activa
            </div>
          </div>

          <!-- KPI 3: Disponibilidad -->
          <div class="mobility-kpi-card">
            <div class="mobility-kpi-top">
              <div>
                <span class="mobility-kpi-label">Disponibilidad</span>
                <div class="mobility-kpi-val">92%</div>
              </div>
              <div class="mobility-sparkline">
                <div class="sparkline-bar" style="height: 18px;"></div>
                <div class="sparkline-bar" style="height: 20px;"></div>
                <div class="sparkline-bar" style="height: 22px;"></div>
                <div class="sparkline-bar" style="height: 21px;"></div>
                <div class="sparkline-bar" style="height: 24px; background: #34d399;"></div>
              </div>
            </div>
            <div class="mobility-kpi-subtext">
              Máquinas operativas certificadas
            </div>
          </div>

          <!-- KPI 4: Carga operativa -->
          <div class="mobility-kpi-card">
            <div class="mobility-kpi-top">
              <div>
                <span class="mobility-kpi-label">Carga operativa</span>
                <div class="mobility-kpi-val">64%</div>
              </div>
              <div class="mobility-sparkline">
                <div class="sparkline-bar" style="height: 10px;"></div>
                <div class="sparkline-bar" style="height: 14px;"></div>
                <div class="sparkline-bar" style="height: 18px;"></div>
                <div class="sparkline-bar" style="height: 15px;"></div>
                <div class="sparkline-bar" style="height: 17px; background: #fbbf24;"></div>
              </div>
            </div>
            <div class="mobility-kpi-subtext">
              Capacidad utilizada
            </div>
          </div>
        </div>
      </div>
    `;

    // Interactivity
    const card03 = container.querySelector('#card-cf03');
    const card07 = container.querySelector('#card-cf07');
    const node03 = container.querySelector('#node-cf03');
    const node07 = container.querySelector('#node-cf07');
    const btnApply = container.querySelector('#btn-apply-rec');

    if (card03) {
      card03.addEventListener('click', () => {
        selectedUnit = 'CF-03';
        render();
      });
    }
    if (card07) {
      card07.addEventListener('click', () => {
        selectedUnit = 'CF-07';
        render();
      });
    }
    if (node03) {
      node03.addEventListener('click', () => {
        selectedUnit = 'CF-03';
        render();
      });
    }
    if (node07) {
      node07.addEventListener('click', () => {
        selectedUnit = 'CF-07';
        render();
      });
    }
    if (btnApply) {
      btnApply.addEventListener('click', (e) => {
        e.stopPropagation();
        alert('Alternativa CF-07 seleccionada. Reducción estimada de 43 min en traslado y -18% en costo logístico.');
      });
    }
  }

  render();
}
