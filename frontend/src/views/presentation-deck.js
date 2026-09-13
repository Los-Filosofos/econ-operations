export async function renderPresentationDeckView(container) {
  let currentSlide = 1;
  const totalSlides = 6;

  function render() {
    container.innerHTML = `
      <div class="deck-wrapper fade-in">
        <!-- Top Navigation Bar for Slides -->
        <div class="deck-nav-bar">
          <div style="display: flex; align-items: center; gap: 12px;">
            <a href="#/" style="display: flex; align-items: center; gap: 6px; color: var(--text-secondary); font-size: 0.8125rem;">
              <span>←</span>
              <span>Salir a Vista Operativa</span>
            </a>
            <span style="color: var(--border);">|</span>
            <span style="font-size: 0.8125rem; font-weight: 600; color: #fff;">ECON Hub · Presentación Ejecutiva</span>
          </div>

          <!-- Slide Controls -->
          <div style="display: flex; align-items: center; gap: 12px;">
            <span style="font-size: 0.75rem; color: var(--text-secondary); font-family: var(--font-mono);">
              Lámina ${currentSlide} de ${totalSlides}
            </span>
            <div style="display: flex; gap: 6px;">
              <button id="deck-prev" style="
                background: var(--bg-surface);
                border: 1px solid var(--border);
                color: ${currentSlide > 1 ? '#fff' : 'var(--text-tertiary)'};
                padding: 6px 12px;
                border-radius: var(--radius-sm);
                cursor: ${currentSlide > 1 ? 'pointer' : 'default'};
                font-size: 0.75rem;
                font-weight: 600;
              ">◀ Anterior</button>
              <button id="deck-next" style="
                background: var(--brand);
                border: 1px solid var(--brand);
                color: #fff;
                padding: 6px 12px;
                border-radius: var(--radius-sm);
                cursor: ${currentSlide < totalSlides ? 'pointer' : 'default'};
                font-size: 0.75rem;
                font-weight: 600;
              ">Siguiente ▶</button>
            </div>
          </div>
        </div>

        <!-- Slide Presentation Stage -->
        <div class="deck-slide-container">
          <div class="deck-slide-card fade-in">
            ${getSlideHtml(currentSlide)}
          </div>
        </div>

        <!-- Bottom Dot Indicators -->
        <div style="display: flex; justify-content: center; align-items: center; gap: 8px; padding-top: 8px;">
          ${Array.from({ length: totalSlides }).map((_, i) => `
            <button class="deck-dot-btn" data-slide="${i + 1}" style="
              width: ${currentSlide === i + 1 ? '24px' : '8px'};
              height: 8px;
              border-radius: 4px;
              background: ${currentSlide === i + 1 ? '#38bdf8' : 'var(--border)'};
              border: none;
              cursor: pointer;
              transition: all var(--duration-fast);
            "></button>
          `).join('')}
        </div>
      </div>
    `;

    // Event listeners
    const prevBtn = container.querySelector('#deck-prev');
    const nextBtn = container.querySelector('#deck-next');
    if (prevBtn) {
      prevBtn.addEventListener('click', () => {
        if (currentSlide > 1) {
          currentSlide--;
          render();
        }
      });
    }
    if (nextBtn) {
      nextBtn.addEventListener('click', () => {
        if (currentSlide < totalSlides) {
          currentSlide++;
          render();
        }
      });
    }

    container.querySelectorAll('.deck-dot-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        currentSlide = parseInt(e.currentTarget.dataset.slide, 10);
        render();
      });
    });

    container.querySelectorAll('.deck-index-item').forEach(item => {
      item.addEventListener('click', (e) => {
        const target = parseInt(e.currentTarget.dataset.target, 10);
        if (target) {
          currentSlide = target;
          render();
        }
      });
    });
  }

  function getSlideHtml(slideNum) {
    switch (slideNum) {
      case 1:
        return `
          <div style="text-align: left;">
            <div style="font-size: 0.8125rem; font-weight: 700; color: var(--brand-light); text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 8px;">
              Presentación Indexada
            </div>
            <h1 style="font-size: 2.2rem; font-weight: 800; color: #fff; margin-bottom: 8px;">
              ECON Hub · Presentación indexada
            </h1>
            <p style="font-size: 1.1rem; color: var(--text-secondary); margin-bottom: 32px;">
              Láminas visuales para presentación ejecutiva y técnica de arquitectura
            </p>

            <div style="font-size: 0.9375rem; font-weight: 700; color: #fff; margin-bottom: 12px;">Índice</div>
            <div class="deck-index-list">
              <div class="deck-index-item" data-target="2">
                <span class="deck-index-num">1</span>
                <span>1. El problema</span>
              </div>
              <div class="deck-index-item" data-target="3">
                <span class="deck-index-num">2</span>
                <span>2. La solución</span>
              </div>
              <div class="deck-index-item" data-target="4">
                <span class="deck-index-num">3</span>
                <span>3. El hub</span>
              </div>
              <div class="deck-index-item" data-target="5">
                <span class="deck-index-num">4</span>
                <span>4. Trazabilidad y movilidad</span>
              </div>
              <div class="deck-index-item" data-target="6">
                <span class="deck-index-num">5</span>
                <span>5. Conclusión</span>
              </div>
            </div>

            <div style="margin-top: 36px; font-size: 0.75rem; color: var(--text-tertiary);">
              Orden sugerido: problema → solución → hub → trazabilidad/movilidad → conclusión
            </div>
          </div>
        `;

      case 2:
        return `
          <div style="text-align: center;">
            <div class="hub-intro-tag" style="margin-bottom: 8px;">1. EL PROBLEMA</div>
            <h2 style="font-size: 2rem; font-weight: 800; color: #fff; margin-bottom: 8px;">
              La operación vive partida en 2 sistemas
            </h2>
            <p style="font-size: 1rem; color: var(--text-secondary); margin-bottom: 40px;">
              La información existe, pero no en una sola historia operativa.
            </p>

            <!-- Disconnected Systems Grid -->
            <div style="display: grid; grid-template-columns: 1fr auto 1fr; gap: 24px; align-items: center; max-width: 760px; margin: 0 auto 40px auto;">
              <!-- Prisma Card -->
              <div style="
                background: linear-gradient(135deg, rgba(99, 102, 241, 0.15), rgba(99, 102, 241, 0.05));
                border: 1px solid var(--source-prisma-border);
                border-radius: var(--radius-lg);
                padding: 24px;
                text-align: left;
              ">
                <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 16px;">
                  <div style="background: rgba(99, 102, 241, 0.25); color: #a5b4fc; padding: 8px; border-radius: 8px; font-size: 1.25rem;">
                    🔷
                  </div>
                  <span style="font-size: 1.25rem; font-weight: 700; color: #c7d2fe;">Prisma</span>
                </div>
                <div style="display: flex; flex-direction: column; gap: 10px; font-size: 0.875rem; color: #e2e8f0;">
                  <div style="display: flex; align-items: center; gap: 8px;"><span>📋</span><span>Proyecto</span></div>
                  <div style="display: flex; align-items: center; gap: 8px;"><span>📄</span><span>Solicitud</span></div>
                  <div style="display: flex; align-items: center; gap: 8px;"><span>✅</span><span>Aprobación</span></div>
                </div>
              </div>

              <!-- Broken Link -->
              <div style="display: flex; flex-direction: column; align-items: center; gap: 8px;">
                <div style="
                  width: 44px;
                  height: 44px;
                  border-radius: 50%;
                  background: rgba(239, 68, 68, 0.15);
                  border: 1px solid rgba(239, 68, 68, 0.4);
                  display: flex;
                  align-items: center;
                  justify-content: center;
                  font-size: 1.2rem;
                  color: #f87171;
                ">
                  ⚡
                </div>
                <span style="font-size: 0.6875rem; font-weight: 700; color: #f87171;">DESCONEXIÓN</span>
              </div>

              <!-- Startrack Card -->
              <div style="
                background: linear-gradient(135deg, rgba(239, 68, 68, 0.15), rgba(239, 68, 68, 0.05));
                border: 1px solid var(--source-startrack-border);
                border-radius: var(--radius-lg);
                padding: 24px;
                text-align: left;
              ">
                <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 16px;">
                  <div style="background: rgba(239, 68, 68, 0.25); color: #fca5a5; padding: 8px; border-radius: 8px; font-size: 1.25rem;">
                    🔺
                  </div>
                  <span style="font-size: 1.25rem; font-weight: 700; color: #fecaca;">Startrack</span>
                </div>
                <div style="display: flex; flex-direction: column; gap: 10px; font-size: 0.875rem; color: #e2e8f0;">
                  <div style="display: flex; align-items: center; gap: 8px;"><span>🚛</span><span>Traslado</span></div>
                  <div style="display: flex; align-items: center; gap: 8px;"><span>📍</span><span>Geocerca</span></div>
                  <div style="display: flex; align-items: center; gap: 8px;"><span>🛰</span><span>GPS</span></div>
                </div>
              </div>
            </div>

            <!-- 3 Bottom Pain Points -->
            <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; max-width: 760px; margin: 0 auto;">
              <div style="background: var(--bg-surface); border: 1px solid var(--border); border-radius: var(--radius-md); padding: 16px;">
                <div style="font-size: 1.5rem; margin-bottom: 8px;">🗂</div>
                <div style="font-weight: 600; font-size: 0.875rem; color: #fff;">Datos dispersos</div>
              </div>
              <div style="background: var(--bg-surface); border: 1px solid var(--border); border-radius: var(--radius-md); padding: 16px;">
                <div style="font-size: 1.5rem; margin-bottom: 8px;">📉</div>
                <div style="font-weight: 600; font-size: 0.875rem; color: #fff;">Trazabilidad incompleta</div>
              </div>
              <div style="background: var(--bg-surface); border: 1px solid var(--border); border-radius: var(--radius-md); padding: 16px;">
                <div style="font-size: 1.5rem; margin-bottom: 8px;">⏱</div>
                <div style="font-weight: 600; font-size: 0.875rem; color: #fff;">Decisiones lentas</div>
              </div>
            </div>
          </div>
        `;

      case 3:
        return `
          <div style="text-align: center;">
            <div class="hub-intro-tag" style="margin-bottom: 8px;">2. LA SOLUCIÓN</div>
            <h2 style="font-size: 2rem; font-weight: 800; color: #fff; margin-bottom: 8px;">
              Prisma → ECON Hub → Startrack
            </h2>
            <p style="font-size: 1rem; color: var(--text-secondary); margin-bottom: 40px;">
              Una capa intermedia conecta la operación sin perder ownership del dato.
            </p>

            <!-- 3 Connected Nodes -->
            <div style="display: grid; grid-template-columns: 1fr 1.2fr 1fr; gap: 20px; align-items: center; max-width: 840px; margin: 0 auto 40px auto;">
              <!-- Prisma Node -->
              <div style="
                background: linear-gradient(135deg, rgba(99, 102, 241, 0.12), rgba(99, 102, 241, 0.04));
                border: 1px solid var(--source-prisma-border);
                border-radius: var(--radius-lg);
                padding: 20px;
                text-align: center;
              ">
                <div style="font-size: 1.5rem; margin-bottom: 8px;">🔷</div>
                <div style="font-weight: 700; font-size: 1.125rem; color: #c7d2fe; margin-bottom: 4px;">Prisma</div>
                <div style="font-size: 0.75rem; color: var(--text-secondary);">solicitudes · aprobación</div>
              </div>

              <!-- ECON Hub Node (Central) -->
              <div style="
                background: linear-gradient(135deg, rgba(20, 79, 129, 0.3), rgba(17, 24, 39, 0.9));
                border: 2px solid #38bdf8;
                box-shadow: 0 0 25px rgba(56, 189, 248, 0.25);
                border-radius: var(--radius-xl);
                padding: 28px 20px;
                text-align: center;
              ">
                <div style="font-size: 2rem; margin-bottom: 8px;">🔗</div>
                <div style="font-weight: 800; font-size: 1.3rem; color: #ffffff; margin-bottom: 4px;">ECON Hub</div>
                <div style="font-size: 0.8125rem; color: #38bdf8; font-weight: 600;">mapeo · visualización · evidencia</div>
              </div>

              <!-- Startrack Node -->
              <div style="
                background: linear-gradient(135deg, rgba(239, 68, 68, 0.12), rgba(239, 68, 68, 0.04));
                border: 1px solid var(--source-startrack-border);
                border-radius: var(--radius-lg);
                padding: 20px;
                text-align: center;
              ">
                <div style="font-size: 1.5rem; margin-bottom: 8px;">🔺</div>
                <div style="font-weight: 700; font-size: 1.125rem; color: #fecaca; margin-bottom: 4px;">Startrack</div>
                <div style="font-size: 0.75rem; color: var(--text-secondary);">traslado · geocerca · GPS</div>
              </div>
            </div>

            <!-- 3 Solution Pillars -->
            <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; max-width: 840px; margin: 0 auto;">
              <div style="background: var(--bg-surface); border: 1px solid var(--border); border-radius: var(--radius-md); padding: 16px;">
                <div style="font-size: 1.5rem; margin-bottom: 8px;">⚡</div>
                <div style="font-weight: 600; font-size: 0.875rem; color: #fff;">Menos fricción</div>
              </div>
              <div style="background: var(--bg-surface); border: 1px solid var(--border); border-radius: var(--radius-md); padding: 16px;">
                <div style="font-size: 1.5rem; margin-bottom: 8px;">🛡</div>
                <div style="font-weight: 600; font-size: 0.875rem; color: #fff;">Más control</div>
              </div>
              <div style="background: var(--bg-surface); border: 1px solid var(--border); border-radius: var(--radius-md); padding: 16px;">
                <div style="font-size: 1.5rem; margin-bottom: 8px;">📜</div>
                <div style="font-weight: 600; font-size: 0.875rem; color: #fff;">Historia operativa unificada</div>
              </div>
            </div>
          </div>
        `;

      case 4:
        return `
          <div>
            <div style="text-align: center; margin-bottom: 24px;">
              <div class="hub-intro-tag">3. EL HUB</div>
              <h2 style="font-size: 1.8rem; font-weight: 800; color: #fff; margin-bottom: 4px;">
                Un visualizador de datos con ownership claro
              </h2>
              <p style="font-size: 0.9375rem; color: var(--text-secondary);">
                ECON Hub reúne información de ambos sistemas y deja visible de dónde viene cada dato.
              </p>
            </div>

            <div style="
              background: #0d121c;
              border: 1px solid #233147;
              border-radius: var(--radius-lg);
              padding: 24px;
              margin-bottom: 20px;
            ">
              <div style="display: grid; grid-template-columns: 1fr auto 1fr; gap: 16px; align-items: center; margin-bottom: 20px;">
                <div style="background: rgba(99, 102, 241, 0.15); border: 1px solid rgba(99, 102, 241, 0.4); padding: 16px; border-radius: 8px;">
                  <div style="font-size: 1rem; font-weight: 700; color: #c7d2fe;">Prisma</div>
                  <div style="font-size: 0.8125rem; color: #fff; margin-top: 4px;">PROY-014 · 2 solicitudes</div>
                </div>
                <div style="background: #1e293b; border: 1px solid #334155; padding: 6px 14px; border-radius: 9999px; font-size: 0.75rem; color: #38bdf8; font-weight: 600;">
                  🔗 Datos conectados
                </div>
                <div style="background: rgba(239, 68, 68, 0.15); border: 1px solid rgba(239, 68, 68, 0.4); padding: 16px; border-radius: 8px;">
                  <div style="font-size: 1rem; font-weight: 700; color: #fecaca;">Startrack</div>
                  <div style="font-size: 0.8125rem; color: #fff; margin-top: 4px;">CF-03 · Cargador frontal 03</div>
                </div>
              </div>

              <!-- Mini tags preview -->
              <div style="display: flex; flex-wrap: wrap; gap: 12px; justify-content: center;">
                <span class="badge-provenance badge-provenance--prisma">Estado Prisma: Aprobada (Dato Prisma)</span>
                <span class="badge-provenance badge-provenance--startrack">Estado maquinaria: Obsoleta (Dato Startrack)</span>
                <span class="badge-provenance badge-provenance--startrack">Estado traslado: Pendiente (Dato Startrack)</span>
                <span class="badge-provenance badge-provenance--prisma">Evidencia Documental (Dato Prisma)</span>
              </div>
            </div>

            <div style="text-align: center;">
              <a href="#/" style="
                display: inline-flex;
                align-items: center;
                gap: 8px;
                background: var(--brand);
                color: #fff;
                padding: 10px 24px;
                border-radius: var(--radius-md);
                font-weight: 600;
                font-size: 0.875rem;
              ">
                <span>Abrir Vista Operativa Completa</span>
                <span>→</span>
              </a>
            </div>
          </div>
        `;

      case 5:
        return `
          <div>
            <div style="text-align: center; margin-bottom: 24px;">
              <div class="hub-intro-tag">4. TRAZABILIDAD Y MOVILIDAD</div>
              <h2 style="font-size: 1.8rem; font-weight: 800; color: #fff; margin-bottom: 4px;">
                Mover mejor la maquinaria también es ahorro
              </h2>
              <p style="font-size: 0.9375rem; color: var(--text-secondary);">
                La trazabilidad permite decidir cuál máquina mover, cuánto tarda y cuál alternativa reduce costo.
              </p>
            </div>

            <!-- Route Comparison Preview -->
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; max-width: 760px; margin: 0 auto 24px auto;">
              <div style="background: var(--bg-surface); border: 1px solid var(--border); border-radius: var(--radius-md); padding: 20px;">
                <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                  <span style="font-weight: 700; color: #fff;">CF-03 · Cargador frontal</span>
                  <span style="font-size: 0.6875rem; color: #38bdf8; font-weight: 700;">PROGRAMABLE</span>
                </div>
                <div style="font-size: 0.8125rem; color: var(--text-secondary);">ETA: 1 h 25 min · Distancia: 27 km</div>
              </div>

              <div style="background: linear-gradient(135deg, rgba(16, 185, 129, 0.12), rgba(17, 24, 39, 0.8)); border: 1px solid #10b981; border-radius: var(--radius-md); padding: 20px;">
                <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                  <span style="font-weight: 700; color: #34d399;">CF-07 · Cargador frontal</span>
                  <span class="savings-tag">★ ALTERNATIVA (-18%)</span>
                </div>
                <div style="font-size: 0.8125rem; color: #a7f3d0;">ETA: 42 min · Distancia: 14 km · Ahorro logístico</div>
              </div>
            </div>

            <!-- 4 KPIs snippet -->
            <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; max-width: 760px; margin: 0 auto 24px auto; text-align: center;">
              <div style="background: #0d121c; border: 1px solid var(--border); padding: 12px; border-radius: 6px;">
                <div style="font-size: 1.25rem; font-weight: 700; color: #fff;">186 h</div>
                <div style="font-size: 0.6875rem; color: #34d399;">+12% horas</div>
              </div>
              <div style="background: #0d121c; border: 1px solid var(--border); padding: 12px; border-radius: 6px;">
                <div style="font-size: 1.25rem; font-weight: 700; color: #fff;">78%</div>
                <div style="font-size: 0.6875rem; color: var(--text-secondary);">Uso flota</div>
              </div>
              <div style="background: #0d121c; border: 1px solid var(--border); padding: 12px; border-radius: 6px;">
                <div style="font-size: 1.25rem; font-weight: 700; color: #fff;">92%</div>
                <div style="font-size: 0.6875rem; color: var(--text-secondary);">Disponibilidad</div>
              </div>
              <div style="background: #0d121c; border: 1px solid var(--border); padding: 12px; border-radius: 6px;">
                <div style="font-size: 1.25rem; font-weight: 700; color: #fff;">64%</div>
                <div style="font-size: 0.6875rem; color: var(--text-secondary);">Carga operativa</div>
              </div>
            </div>

            <div style="text-align: center;">
              <a href="#/movilidad" style="
                display: inline-flex;
                align-items: center;
                gap: 8px;
                background: #10b981;
                color: #fff;
                padding: 10px 24px;
                border-radius: var(--radius-md);
                font-weight: 600;
                font-size: 0.875rem;
              ">
                <span>Abrir Simulador de Rutas y Movilidad</span>
                <span>→</span>
              </a>
            </div>
          </div>
        `;

      case 6:
        return `
          <div style="text-align: center;">
            <div class="hub-intro-tag" style="margin-bottom: 8px;">5. CONCLUSIÓN</div>
            <h1 style="font-size: 3rem; font-weight: 800; color: #fff; margin-bottom: 12px; letter-spacing: -0.02em;">
              Gracias
            </h1>
            <p style="font-size: 1.25rem; color: #93c5fd; max-width: 680px; margin: 0 auto 36px auto; font-weight: 500;">
              ECON Hub convierte datos dispersos en decisiones operativas
            </p>

            <!-- 3 Final Pillars -->
            <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 24px; max-width: 780px; margin: 0 auto 40px auto;">
              <div style="background: var(--bg-surface); border: 1px solid var(--border); border-radius: var(--radius-lg); padding: 24px;">
                <div style="font-size: 2rem; margin-bottom: 10px;">🏷</div>
                <div style="font-weight: 700; font-size: 1.125rem; color: #fff; margin-bottom: 6px;">Ownership claro</div>
                <div style="font-size: 0.8125rem; color: var(--text-secondary);">Cada dato conserva y exhibe su sistema de procedencia.</div>
              </div>
              <div style="background: var(--bg-surface); border: 1px solid var(--border); border-radius: var(--radius-lg); padding: 24px;">
                <div style="font-size: 2rem; margin-bottom: 10px;">📜</div>
                <div style="font-weight: 700; font-size: 1.125rem; color: #fff; margin-bottom: 6px;">Trazabilidad real</div>
                <div style="font-size: 0.8125rem; color: var(--text-secondary);">Distinción rigurosa entre estado administrativo y GPS.</div>
              </div>
              <div style="background: var(--bg-surface); border: 1px solid var(--border); border-radius: var(--radius-lg); padding: 24px;">
                <div style="font-size: 2rem; margin-bottom: 10px;">🚚</div>
                <div style="font-weight: 700; font-size: 1.125rem; color: #fff; margin-bottom: 6px;">Movilidad inteligente</div>
                <div style="font-size: 0.8125rem; color: var(--text-secondary);">Ahorro de fletes asignando alternativas de menor costo.</div>
              </div>
            </div>

            <p style="font-size: 0.9375rem; color: var(--text-secondary); margin-bottom: 24px;">
              Una sola vista para entender la operación, decidir mejor y escalar con más control.
            </p>

            <!-- Platform Bridge Footer -->
            <div style="display: inline-flex; align-items: center; gap: 16px; background: rgba(0,0,0,0.4); padding: 10px 24px; border-radius: 9999px; border: 1px solid var(--border);">
              <span style="color: #a5b4fc; font-weight: 700; font-size: 0.875rem;">🔷 Prisma</span>
              <span style="color: var(--text-tertiary);">→</span>
              <span style="color: #38bdf8; font-weight: 800; font-size: 1rem;">ECON Hub</span>
              <span style="color: var(--text-tertiary);">→</span>
              <span style="color: #fca5a5; font-weight: 700; font-size: 0.875rem;">🔺 Startrack</span>
            </div>
          </div>
        `;

      default:
        return '';
    }
  }

  render();
}
