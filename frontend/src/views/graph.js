import { api } from '../api.js';
import { stateColor } from '../theme.js';
import { renderStatusBadge } from '../components/status-badge.js';
import ForceGraph3D from '3d-force-graph';
import * as THREE from 'three';

export async function renderGraphView(container) {
  container.innerHTML = `
    <div class="graph-view">
      <!-- Stats bar (Top Left) -->
      <div class="graph-stats" id="graph-stats">
        <div class="graph-stat">
          <span class="graph-stat__dot" style="background: #00f2fe;"></span>
          <span>Iniciando motor 3D...</span>
        </div>
      </div>

      <!-- Command Center HUD Bar (Top Center) -->
      <div class="graph-hud-bar">
        <div class="graph-hud-title">Casos de Uso</div>
        <button class="graph-hud-btn" id="hud-cu01" data-scenario="cu01" title="Caso 1: Solicitud en Prisma y traslado en Startrack">
          <span>⚡ CU-01</span>
          <span>Solicitud ➔ Viaje</span>
        </button>
        <button class="graph-hud-btn" id="hud-cu02" data-scenario="cu02" title="Caso 2: Consistencia de estados (Ocupada vs Completada)">
          <span>⚖️ CU-02</span>
          <span>Estados Separados</span>
        </button>
        <button class="graph-hud-btn graph-hud-btn--danger" id="hud-cu03" data-scenario="cu03" title="Caso 3: Alerta crítica de mantenimiento preventivo">
          <span>🚨 CU-03</span>
          <span>Alerta Obsoleta</span>
        </button>
        <button class="graph-hud-btn graph-hud-btn--success" id="hud-team6" data-scenario="team6" title="Equipo 6: Demostración en vivo con RE-03 y Rodrigo Trujillo">
          <span>🎯 Equipo 6</span>
          <span>Kit RE-03</span>
        </button>
        <button class="graph-hud-btn" id="hud-orbit" title="Activar/desactivar rotación cinematográfica 360°">
          <span>🌌 Órbita</span>
        </button>
      </div>

      <!-- Mode Switch & Tools (Top Right) -->
      <div class="graph-hud-tools">
        <div class="graph-mode-toggle">
          <button class="graph-mode-btn graph-mode-btn--active" id="mode-3d">3D WebGL</button>
          <button class="graph-mode-btn" id="mode-2d">2D Plano</button>
        </div>
        <button class="graph-controls__btn" id="graph-reset" title="Reiniciar Cámara">⟲</button>
      </div>

      <!-- Main Canvas Viewport -->
      <div class="graph-canvas-container" id="graph-container">
        <div id="graph-3d-canvas"></div>
        <div id="graph-2d-canvas-wrap">
          <canvas class="graph-canvas" id="graph-2d-canvas"></canvas>
        </div>
      </div>

      <!-- Bottom Scenario Briefing (Pitch Guide) -->
      <div class="graph-scenario-briefing" id="scenario-briefing">
        <div class="graph-scenario-header">
          <span class="graph-scenario-tag" id="scenario-tag">CASO DE USO 01</span>
          <button class="graph-scenario-close" id="scenario-close">&times;</button>
        </div>
        <div class="graph-scenario-title" id="scenario-title">Solicitud y traslado de maquinaria</div>
        <div class="graph-scenario-body" id="scenario-body">
          Prisma registra la solicitud aprobada y asigna la unidad; Startrack gestiona y monitorea el viaje físico. ECON unifica ambas plataformas preservando la integridad de datos sin pérdida de identificadores.
        </div>
        <div class="graph-scenario-highlight" id="scenario-highlight">
          <span>💡</span>
          <span id="scenario-highlight-text">Trazabilidad completa: CF-03 asignada a PROY-014 vinculada a MOV-PRUEBA-001 en Startrack.</span>
        </div>
      </div>

      <!-- Legend (Bottom Left) -->
      <div class="graph-legend">
        <div style="font-size: 0.6875rem; font-weight: 700; color: #cbd5e1; margin-bottom: 6px; letter-spacing: 0.06em;">CONVENCIONES 3D</div>
        <div class="graph-legend__item">
          <div class="graph-legend__swatch" style="background: #3b82f6; box-shadow: 0 0 8px #3b82f6;"></div>
          <span>Proyecto / Geocerca POI</span>
        </div>
        <div class="graph-legend__item">
          <div class="graph-legend__swatch" style="background: #00ffa3; box-shadow: 0 0 8px #00ffa3;"></div>
          <span>Maquinaria Disponible</span>
        </div>
        <div class="graph-legend__item">
          <div class="graph-legend__swatch" style="background: #f59e0b; box-shadow: 0 0 8px #f59e0b;"></div>
          <span>Maquinaria Ocupada / Traslado</span>
        </div>
        <div class="graph-legend__item">
          <div class="graph-legend__swatch" style="background: #ef4444; box-shadow: 0 0 8px #ef4444;"></div>
          <span>Obsoleta / Tensión Operativa</span>
        </div>
      </div>

      <!-- Context Slide-over Panel (Dual Tech / Non-Tech) -->
      <div class="graph-panel" id="graph-panel">
        <div class="graph-panel__inner" id="graph-panel-content">
          <!-- Filled on node click -->
        </div>
      </div>

      <!-- Cyber Modal for Raw JSON / OpenAPI DevTools -->
      <div class="cyber-modal" id="cyber-modal">
        <div class="cyber-modal-card">
          <div class="cyber-modal-header">
            <div style="font-size: 0.8125rem; font-weight: 700; color: #38bdf8; display: flex; align-items: center; gap: 8px;">
              <span>⚡</span>
              <span id="cyber-modal-title">Inspección de Contrato OpenAPI</span>
            </div>
            <button class="graph-panel__close" id="cyber-modal-close">&times;</button>
          </div>
          <pre class="cyber-modal-body" id="cyber-modal-code"></pre>
        </div>
      </div>
    </div>
  `;

  const container3D = container.querySelector('#graph-3d-canvas');
  const container2DWrap = container.querySelector('#graph-2d-canvas-wrap');
  const canvas2D = container.querySelector('#graph-2d-canvas');
  const panel = container.querySelector('#graph-panel');
  const panelContent = container.querySelector('#graph-panel-content');
  const statsContainer = container.querySelector('#graph-stats');
  const briefingBox = container.querySelector('#scenario-briefing');
  const cyberModal = container.querySelector('#cyber-modal');
  const cyberModalCode = container.querySelector('#cyber-modal-code');
  const cyberModalTitle = container.querySelector('#cyber-modal-title');

  let data = null;
  let nodes = [];
  let edges = [];
  let graph3D = null;
  let activeScenario = null;
  let isAutoOrbiting = false;
  let orbitTimer = null;
  let currentMode = '3d';
  let selectedNode = null;

  // 2D fallback variables
  let ctx2d = canvas2D.getContext('2d');
  let transform2d = { x: 0, y: 0, scale: 1 };
  let isDragging2d = false;
  let dragStart2d = { x: 0, y: 0 };

  try {
    data = await api.getGraph();
    nodes = JSON.parse(JSON.stringify(data.nodes || []));
    edges = JSON.parse(JSON.stringify(data.edges || []));

    // Ensure tension links exist explicitly in links array for 3D visualization
    (data.tensions || []).forEach(tension => {
      if (tension.node_ids && tension.node_ids.length >= 2) {
        edges.push({
          id: `tension:${tension.code}`,
          kind: 'tension',
          source: tension.node_ids[0],
          target: tension.node_ids[1],
          isTension: true,
          tensionData: tension,
        });
      }
    });

    updateStatsBar();
    init3DGraph();
    init2DGraph();
    setupHudListeners();
  } catch (err) {
    statsContainer.innerHTML = `
      <div class="graph-stat" style="border-color: rgba(239, 68, 68, 0.4); color: #fca5a5;">
        <span>Error al cargar grafo: ${err.message}</span>
      </div>
    `;
  }

  function updateStatsBar() {
    const machineCount = nodes.filter(n => n.kind === 'machine').length;
    const projectCount = nodes.filter(n => n.kind === 'project' || n.kind === 'place').length;
    const movementCount = nodes.filter(n => n.kind === 'movement').length;
    const tensionsCount = (data.tensions || []).length;

    statsContainer.innerHTML = `
      <div class="graph-stat">
        <span class="graph-stat__dot" style="background: #00ffa3; box-shadow: 0 0 8px #00ffa3;"></span>
        <span>Maquinarias: <strong class="graph-stat__value">${machineCount}</strong></span>
      </div>
      <div class="graph-stat">
        <span class="graph-stat__dot" style="background: #3b82f6; box-shadow: 0 0 8px #3b82f6;"></span>
        <span>Proyectos: <strong class="graph-stat__value">${projectCount}</strong></span>
      </div>
      <div class="graph-stat">
        <span class="graph-stat__dot" style="background: #f59e0b; box-shadow: 0 0 8px #f59e0b;"></span>
        <span>Traslados: <strong class="graph-stat__value">${movementCount}</strong></span>
      </div>
      ${tensionsCount > 0 ? `
        <div class="graph-stat" style="border-color: rgba(239, 68, 68, 0.4); background: rgba(239, 68, 68, 0.1);">
          <span class="graph-stat__dot" style="background: #ef4444; box-shadow: 0 0 10px #ef4444; animation: pulse-dot 1.5s infinite;"></span>
          <span>Tensiones: <strong class="graph-stat__value" style="color: #fca5a5;">${tensionsCount}</strong></span>
        </div>
      ` : ''}
    `;
  }

  function init3DGraph() {
    const rect = container3D.getBoundingClientRect();
    const width = rect.width || window.innerWidth - 240;
    const height = rect.height || window.innerHeight - 60;

    graph3D = ForceGraph3D()(container3D)
      .width(width)
      .height(height)
      .backgroundColor('#06080d')
      .showNavInfo(false)
      .graphData({ nodes, links: edges })
      .nodeLabel(node => `
        <div style="background: rgba(11, 15, 25, 0.95); padding: 8px 12px; border-radius: 8px; border: 1px solid #38bdf8; font-family: Inter, sans-serif; color: #fff; font-size: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.8);">
          <div style="font-weight: 700; color: #38bdf8; font-size: 13px;">${node.label || node.asset_number || node.id}</div>
          <div style="font-size: 11px; color: #94a3b8; margin-top: 2px;">Tipo: ${node.kind} · Estado: ${node.machinery_status || node.status || 'OK'}</div>
          ${node.machinery_status === 'OBSOLETA' ? '<div style="color: #ef4444; font-weight: bold; margin-top: 4px;">⚠ Mantenimiento Correctivo (Alerta)</div>' : ''}
        </div>
      `)
      .nodeThreeObject(node => {
        const group = new THREE.Group();

        let color = 0x3b82f6;
        let size = 8;

        if (node.kind === 'machine') {
          size = 7;
          if (node.machinery_status === 'OBSOLETA' || node.maintenance_is_stopped) {
            color = 0xef4444;
          } else if (node.machinery_status === 'OCUPADA') {
            color = 0xf59e0b;
          } else {
            color = 0x10b981;
          }
        } else if (node.kind === 'project' || node.kind === 'place') {
          size = 12;
          color = 0x3b82f6;
        } else if (node.kind === 'movement') {
          size = 6;
          color = 0xf59e0b;
        } else if (node.kind === 'request') {
          size = 6;
          color = 0x06b6d4;
        }

        // Main core sphere
        const geometry = new THREE.SphereGeometry(size, 20, 20);
        const material = new THREE.MeshPhongMaterial({
          color: color,
          emissive: color,
          emissiveIntensity: 0.35,
          transparent: true,
          opacity: 0.9,
          shininess: 90,
        });
        const mesh = new THREE.Mesh(geometry, material);
        group.add(mesh);

        // Orbital halo ring for special nodes
        if (node.kind === 'project' || node.machinery_status === 'OBSOLETA') {
          const ringGeo = new THREE.RingGeometry(size * 1.3, size * 1.55, 32);
          const ringMat = new THREE.MeshBasicMaterial({
            color: node.machinery_status === 'OBSOLETA' ? 0xff0055 : 0x00f2fe,
            side: THREE.DoubleSide,
            transparent: true,
            opacity: 0.8,
          });
          const ring = new THREE.Mesh(ringGeo, ringMat);
          ring.rotation.x = Math.PI / 2;
          group.add(ring);
        }

        // Text sprite label
        const canvas = document.createElement('canvas');
        canvas.width = 256;
        canvas.height = 64;
        const ctx = canvas.getContext('2d');
        ctx.font = '700 20px Inter, sans-serif';
        ctx.fillStyle = '#f8fafc';
        ctx.textAlign = 'center';
        const labelText = node.asset_number || node.label || node.id.split(':').pop();
        const shortText = labelText.length > 18 ? labelText.slice(0, 16) + '…' : labelText;
        ctx.fillText(shortText, 128, 40);

        const texture = new THREE.CanvasTexture(canvas);
        const spriteMat = new THREE.SpriteMaterial({ map: texture, transparent: true });
        const sprite = new THREE.Sprite(spriteMat);
        sprite.scale.set(size * 4, size * 1, 1);
        sprite.position.y = size + 7;
        group.add(sprite);

        return group;
      })
      .linkCurvature(0.22)
      .linkWidth(link => link.isTension ? 3.5 : 1.5)
      .linkColor(link => link.isTension ? '#ff0055' : link.kind === 'transfer' ? '#f59e0b' : '#3b82f6')
      .linkDirectionalParticles(link => link.isTension ? 6 : 3)
      .linkDirectionalParticleWidth(link => link.isTension ? 4 : 2.2)
      .linkDirectionalParticleSpeed(link => link.isTension ? 0.018 : 0.006)
      .linkDirectionalParticleColor(link => link.isTension ? '#ff0055' : '#00ffa3')
      .onNodeClick(node => {
        handleSelectNode(node);
      })
      .onBackgroundClick(() => {
        panel.classList.remove('graph-panel--open');
        selectedNode = null;
      });

    // Lights
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.7);
    graph3D.scene().add(ambientLight);
    const pointLight = new THREE.PointLight(0x00f2fe, 1.5, 800);
    pointLight.position.set(0, 200, 300);
    graph3D.scene().add(pointLight);

    // Initial camera position
    setTimeout(() => {
      graph3D.cameraPosition({ x: 0, y: 120, z: 420 }, { x: 0, y: 0, z: 0 }, 1000);
    }, 400);

    window.addEventListener('resize', () => {
      if (currentMode === '3d' && graph3D) {
        const r = container3D.getBoundingClientRect();
        graph3D.width(r.width).height(r.height);
      }
    });
  }

  function handleSelectNode(node) {
    selectedNode = node;
    panel.classList.add('graph-panel--open');
    renderNodeDetails(node, 'executive');

    // Fly camera towards selected node in 3D
    if (currentMode === '3d' && graph3D && node.x !== undefined) {
      graph3D.cameraPosition(
        { x: node.x + 60, y: node.y + 40, z: node.z + 140 },
        { x: node.x, y: node.y, z: node.z },
        1200
      );
    }
  }

  function renderNodeDetails(node, activeTab = 'executive') {
    const isTech = activeTab === 'tech';

    let techSpecificHtml = '';
    let execSpecificHtml = '';

    const isObsolete = node.machinery_status === 'OBSOLETA';
    const isOccupied = node.machinery_status === 'OCUPADA';

    if (node.kind === 'machine') {
      execSpecificHtml = `
        ${isObsolete ? `
          <div class="graph-panel-alert">
            <div class="graph-panel-alert__title">
              <span>🚨</span>
              <span>Alerta Operacional Crítica (Caso 03)</span>
            </div>
            <div class="graph-panel-alert__desc">
              Esta maquinaria figura <strong>OBSOLETA (Mantenimiento Correctivo)</strong> en Prisma. ECON detectó automáticamente que existe una solicitud/traslado programado y activó el <strong>bloqueo preventivo de despacho</strong> para evitar un viaje en falso.
            </div>
          </div>
        ` : ''}

        ${isOccupied ? `
          <div class="graph-panel-success">
            <div class="graph-panel-success__title">
              <span>⚖️</span>
              <span>Consistencia de Estados (Caso 02)</span>
            </div>
            <div class="graph-panel-success__desc">
              Prisma indica <strong>OCUPADA</strong> (recurso en uso en faena) mientras Startrack reporta el traslado como <strong>COMPLETADA</strong>. Ambos estados son correctos simultáneamente: el flete concluyó y la máquina labora en el sitio.
            </div>
          </div>
        ` : ''}

        <div class="graph-panel__section">
          <div class="graph-panel__label">Estado Administrativo</div>
          <div class="graph-panel__value">${renderStatusBadge(node.machinery_status)}</div>
        </div>
        <div class="graph-panel__section">
          <div class="graph-panel__label">Clase & Modelo</div>
          <div class="graph-panel__value">${node.equipment_class || '—'} · ${node.name || '—'}</div>
        </div>
        <div class="graph-panel__section">
          <div class="graph-panel__label">Empresa Propietaria</div>
          <div class="graph-panel__value">${node.company || 'Grupo ECON'}</div>
        </div>
        ${node.assignment_starts_on ? `
          <div class="graph-panel__section">
            <div class="graph-panel__label">Período de Asignación en Obra</div>
            <div class="graph-panel__value text-mono">${node.assignment_starts_on} → ${node.assignment_ends_on || 'En curso'}</div>
          </div>
        ` : ''}
      `;

      techSpecificHtml = `
        <div class="graph-panel__section">
          <div class="graph-panel__label">ID Canónico ECON</div>
          <div class="graph-panel__value text-mono" style="font-size: 0.75rem; color: #38bdf8;">${node.id}</div>
        </div>
        <div class="graph-panel__section">
          <div class="graph-panel__label">Source ID Prisma / Nexus</div>
          <div class="graph-panel__value text-mono" style="font-size: 0.75rem;">${node.source_id || '—'}</div>
        </div>
        <div class="graph-panel__section">
          <div class="graph-panel__label">Verificación de Integridad</div>
          <div class="graph-panel__value" style="color: #34d399; font-size: 0.8125rem;">✔ source_observed (Inmutable)</div>
        </div>
      `;
    } else if (node.kind === 'project' || node.kind === 'place') {
      execSpecificHtml = `
        <div class="graph-panel__section">
          <div class="graph-panel__label">Destino Operativo / Geocerca</div>
          <div class="graph-panel__value">${node.label}</div>
        </div>
        <div class="graph-panel__section">
          <div class="graph-panel__label">Tipo de Recurso</div>
          <div class="graph-panel__value">Proyecto con Geocerca Registrada en Startrack</div>
        </div>
      `;
      techSpecificHtml = `
        <div class="graph-panel__section">
          <div class="graph-panel__label">ID de Geocerca (POI)</div>
          <div class="graph-panel__value text-mono" style="font-size: 0.75rem;">${node.id}</div>
        </div>
      `;
    } else if (node.kind === 'request') {
      execSpecificHtml = `
        <div class="graph-panel__section">
          <div class="graph-panel__label">Estado de Solicitud Prisma</div>
          <div class="graph-panel__value"><span class="badge badge--active">APROBADA</span></div>
        </div>
        <div class="graph-panel__section">
          <div class="graph-panel__label">Rol en el Flujo</div>
          <div class="graph-panel__value">Habilita la preparación de traslado sin generar duplicados.</div>
        </div>
      `;
    }

    const evidenceItems = (node.evidence || []).map(ev => `
      <div style="background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 6px; padding: 8px; margin-bottom: 6px;">
        <div style="font-size: 0.6875rem; font-weight: 700; color: #38bdf8;">ORIGEN: ${ev.origin || ev.provenance?.source || 'Prisma'}</div>
        <div class="text-mono" style="font-size: 0.6875rem; color: #94a3b8; word-break: break-all;">${ev.reference || ev.source_id}</div>
      </div>
    `).join('');

    panelContent.innerHTML = `
      <div class="graph-panel__header">
        <div>
          <div style="font-size: 0.6875rem; font-weight: 800; text-transform: uppercase; color: #00f2fe; letter-spacing: 0.08em;">${node.kind}</div>
          <div class="graph-panel__title">${node.label || node.asset_number || node.id}</div>
        </div>
        <button class="graph-panel__close" id="panel-close-btn">&times;</button>
      </div>

      <div class="graph-panel-tabs">
        <button class="graph-panel-tab ${!isTech ? 'graph-panel-tab--active' : ''}" id="tab-exec">Resumen Ejecutivo</button>
        <button class="graph-panel-tab ${isTech ? 'graph-panel-tab--active' : ''}" id="tab-tech">Telemetría (Tech)</button>
      </div>

      <div id="panel-tab-body">
        ${!isTech ? execSpecificHtml : techSpecificHtml}

        ${evidenceItems ? `
          <div class="graph-panel__section" style="margin-top: 14px;">
            <div class="graph-panel__label">Evidencia Comprobada (${node.evidence.length})</div>
            <div>${evidenceItems}</div>
          </div>
        ` : ''}

        <button class="json-devtools-btn" id="btn-inspect-json">
          <span>🔍</span>
          <span>Inspeccionar Contrato JSON Raw</span>
        </button>
      </div>
    `;

    panelContent.querySelector('#panel-close-btn').addEventListener('click', () => {
      panel.classList.remove('graph-panel--open');
      selectedNode = null;
    });

    panelContent.querySelector('#tab-exec').addEventListener('click', () => {
      renderNodeDetails(node, 'executive');
    });

    panelContent.querySelector('#tab-tech').addEventListener('click', () => {
      renderNodeDetails(node, 'tech');
    });

    panelContent.querySelector('#btn-inspect-json').addEventListener('click', () => {
      cyberModalTitle.textContent = `Contrato JSON: ${node.label || node.id}`;
      cyberModalCode.textContent = JSON.stringify(node, null, 2);
      cyberModal.classList.add('cyber-modal--open');
    });
  }

  // ─── Scenarios Walkthrough Execution ───
  function triggerScenario(scenarioKey) {
    activeScenario = scenarioKey;

    container.querySelectorAll('.graph-hud-btn').forEach(btn => {
      btn.classList.remove('graph-hud-btn--active');
    });

    const activeBtn = container.querySelector(`[data-scenario="${scenarioKey}"]`);
    if (activeBtn) activeBtn.classList.add('graph-hud-btn--active');

    briefingBox.classList.add('graph-scenario-briefing--active');

    if (scenarioKey === 'cu01') {
      container.querySelector('#scenario-tag').textContent = 'CASO DE USO 01 — SOLICITUD Y TRASLADO';
      container.querySelector('#scenario-title').textContent = 'Pipeline Unificado: Prisma ➔ ECON ➔ Startrack';
      container.querySelector('#scenario-body').textContent = 'Se identifica la solicitud Aprobada en Prisma y se mapea con la tarea Pendiente en Startrack (Adriana Steiner). ECON preserva todos los identificadores originales sin inventar fechas ni perder auditoría.';
      container.querySelector('#scenario-highlight-text').textContent = 'Demostración de trazabilidad: CF-03 en PROY-014 con movimiento MOV-PRUEBA-001.';

      const target = nodes.find(n => n.label === 'CF-03' || n.asset_number === 'CF-03');
      if (target) handleSelectNode(target);
    } else if (scenarioKey === 'cu02') {
      container.querySelector('#scenario-tag').textContent = 'CASO DE USO 02 — CONSISTENCIA DE ESTADOS';
      container.querySelector('#scenario-title').textContent = 'Desacoplamiento: Prisma OCUPADA vs Startrack COMPLETADA';
      container.querySelector('#scenario-body').textContent = 'Prisma describe la posesión administrativa de la maquinaria durante la obra ("Ocupada"), mientras Startrack describe la logística de transporte ("Completada"). Ambos estados son simultáneamente verdaderos. ECON audita mediante el Indicador I3 que la tarea completada no sustituye la recepción en obra.';
      container.querySelector('#scenario-highlight-text').textContent = 'Estados separados: cero falsos conflictos; la recepción física requiere declaración expresa.';

      const target = nodes.find(n => n.label === 'CF-03' || n.asset_number === 'CF-03');
      if (target) handleSelectNode(target);
    } else if (scenarioKey === 'cu03') {
      container.querySelector('#scenario-tag').textContent = 'CASO DE USO 03 — PREVENCIÓN DE FALLA OPERACIONAL';
      container.querySelector('#scenario-title').textContent = 'Bloqueo Automático: Maquinaria OBSOLETA con Traslado Programado';
      container.querySelector('#scenario-body').textContent = 'El equipo CF-03 pasa a OBSOLETA (mantenimiento correctivo) en Prisma, pero en Startrack el viaje figura Pendiente. El motor de tensiones de ECON detecta la discrepancia en tiempo real y activa un bloqueo preventivo que impide la salida de carretera.';
      container.querySelector('#scenario-highlight-text').textContent = 'Riesgo Crítico Mitigado: Se previene el flete en falso y el costo operativo asociado.';

      const target = nodes.find(n => n.label === 'CF-03' || n.asset_number === 'CF-03');
      if (target) handleSelectNode(target);
    } else if (scenarioKey === 'team6') {
      container.querySelector('#scenario-tag').textContent = 'EQUIPO 6 — ASIGNACIÓN EN VIVO (KIT RE-03)';
      container.querySelector('#scenario-title').textContent = 'Demostración Flexible: Retroexcavadora RE-03 / Rodrigo Trujillo / Proyecto Zeta';
      container.querySelector('#scenario-body').textContent = 'La plataforma valida que no depende de IDs fijos. Se modela la asignación específica del Equipo 6 consultando el sandbox real en tiempo real (GET /api/v1/hub?mode=live&search=RE-03) con el motorista MOT-006 y PROY-006.';
      container.querySelector('#scenario-highlight-text').textContent = 'Flexibilidad de arquitectura demostrada: preparada para pruebas dinámicas del jurado.';

      // Focus on available equipment or synthesize view
      const target = nodes.find(n => n.label === 'CF-03') || nodes[0];
      if (target) handleSelectNode(target);
    }
  }

  function setupHudListeners() {
    container.querySelector('#hud-cu01').addEventListener('click', () => triggerScenario('cu01'));
    container.querySelector('#hud-cu02').addEventListener('click', () => triggerScenario('cu02'));
    container.querySelector('#hud-cu03').addEventListener('click', () => triggerScenario('cu03'));
    container.querySelector('#hud-team6').addEventListener('click', () => triggerScenario('team6'));

    // Orbit toggle
    container.querySelector('#hud-orbit').addEventListener('click', (e) => {
      isAutoOrbiting = !isAutoOrbiting;
      e.currentTarget.classList.toggle('graph-hud-btn--active', isAutoOrbiting);

      if (isAutoOrbiting) {
        let angle = 0;
        const dist = 380;
        orbitTimer = setInterval(() => {
          angle += 0.008;
          if (graph3D) {
            graph3D.cameraPosition({
              x: dist * Math.sin(angle),
              z: dist * Math.cos(angle),
              y: 80 + 40 * Math.sin(angle * 0.5),
            });
          }
        }, 30);
      } else {
        clearInterval(orbitTimer);
      }
    });

    // 2D / 3D Mode Toggle
    container.querySelector('#mode-3d').addEventListener('click', () => {
      currentMode = '3d';
      container.querySelector('#mode-3d').classList.add('graph-mode-btn--active');
      container.querySelector('#mode-2d').classList.remove('graph-mode-btn--active');
      container3D.style.display = 'block';
      container2DWrap.style.display = 'none';
    });

    container.querySelector('#mode-2d').addEventListener('click', () => {
      currentMode = '2d';
      container.querySelector('#mode-2d').classList.add('graph-mode-btn--active');
      container.querySelector('#mode-3d').classList.remove('graph-mode-btn--active');
      container3D.style.display = 'none';
      container2DWrap.style.display = 'block';
      render2D();
    });

    // Reset camera
    container.querySelector('#graph-reset').addEventListener('click', () => {
      if (currentMode === '3d' && graph3D) {
        graph3D.cameraPosition({ x: 0, y: 120, z: 420 }, { x: 0, y: 0, z: 0 }, 1000);
      } else {
        center2DGraph();
      }
    });

    // Close briefing
    container.querySelector('#scenario-close').addEventListener('click', () => {
      briefingBox.classList.remove('graph-scenario-briefing--active');
      container.querySelectorAll('.graph-hud-btn').forEach(btn => btn.classList.remove('graph-hud-btn--active'));
    });

    // Close Cyber Modal
    container.querySelector('#cyber-modal-close').addEventListener('click', () => {
      cyberModal.classList.remove('cyber-modal--open');
    });
  }

  // ─── 2D Canvas Fallback & Layout ───
  function init2DGraph() {
    compute2DLayout(nodes, edges);
    resize2DCanvas();
    center2DGraph();

    window.addEventListener('resize', resize2DCanvas);

    canvas2D.addEventListener('mousedown', (e) => {
      isDragging2d = true;
      dragStart2d = { x: e.clientX - transform2d.x, y: e.clientY - transform2d.y };
    });

    window.addEventListener('mousemove', (e) => {
      if (!isDragging2d) return;
      transform2d.x = e.clientX - dragStart2d.x;
      transform2d.y = e.clientY - dragStart2d.y;
      render2D();
    });

    window.addEventListener('mouseup', () => {
      isDragging2d = false;
    });

    canvas2D.addEventListener('click', (e) => {
      const rect = canvas2D.getBoundingClientRect();
      const clickX = (e.clientX - rect.left - transform2d.x) / transform2d.scale;
      const clickY = (e.clientY - rect.top - transform2d.y) / transform2d.scale;

      let clicked = null;
      for (const node of nodes) {
        const dist = Math.hypot(clickX - node.x, clickY - node.y);
        if (dist <= (node.radius || 24) + 4) {
          clicked = node;
          break;
        }
      }

      if (clicked) {
        handleSelectNode(clicked);
      }
    });
  }

  function compute2DLayout(nodesList, edgesList) {
    const projects = nodesList.filter(n => n.kind === 'project' || n.kind === 'place');
    const machines = nodesList.filter(n => n.kind === 'machine');
    const requests = nodesList.filter(n => n.kind === 'request');
    const movements = nodesList.filter(n => n.kind === 'movement');

    const centerX = 400;
    const centerY = 350;

    projects.forEach((proj, idx) => {
      const angle = (idx / Math.max(1, projects.length)) * Math.PI * 2;
      const radius = projects.length === 1 ? 0 : 220;
      proj.x = centerX + Math.cos(angle) * radius;
      proj.y = centerY + Math.sin(angle) * radius;
      proj.radius = 42;
    });

    machines.forEach((m, idx) => {
      const angle = (idx / Math.max(1, machines.length)) * Math.PI * 2;
      m.x = centerX + Math.cos(angle) * 160;
      m.y = centerY + Math.sin(angle) * 160;
      m.radius = 24;
    });

    requests.forEach((r, idx) => {
      r.x = centerX - 260 + (idx * 90);
      r.y = centerY + 240;
      r.radius = 18;
    });

    movements.forEach((mv, idx) => {
      mv.x = centerX + 180 + (idx * 80);
      mv.y = centerY - 200;
      mv.radius = 20;
    });
  }

  function resize2DCanvas() {
    const rect = container2DWrap.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    canvas2D.width = rect.width * dpr;
    canvas2D.height = rect.height * dpr;
    canvas2D.style.width = `${rect.width}px`;
    canvas2D.style.height = `${rect.height}px`;
    ctx2d.scale(dpr, dpr);
    render2D();
  }

  function center2DGraph() {
    const rect = container2DWrap.getBoundingClientRect();
    transform2d = {
      x: rect.width / 2 - 400,
      y: rect.height / 2 - 350,
      scale: 1,
    };
    render2D();
  }

  function render2D() {
    if (!ctx2d || currentMode !== '2d') return;
    const width = canvas2D.width / (window.devicePixelRatio || 1);
    const height = canvas2D.height / (window.devicePixelRatio || 1);

    ctx2d.save();
    ctx2d.clearRect(0, 0, width, height);

    ctx2d.fillStyle = '#06080d';
    ctx2d.fillRect(0, 0, width, height);

    ctx2d.translate(transform2d.x, transform2d.y);
    ctx2d.scale(transform2d.scale, transform2d.scale);

    // Draw edges
    edges.forEach(edge => {
      const src = nodes.find(n => n.id === (typeof edge.source === 'object' ? edge.source.id : edge.source));
      const tgt = nodes.find(n => n.id === (typeof edge.target === 'object' ? edge.target.id : edge.target));
      if (!src || !tgt) return;

      ctx2d.beginPath();
      ctx2d.moveTo(src.x, src.y);
      ctx2d.lineTo(tgt.x, tgt.y);

      if (edge.isTension) {
        ctx2d.strokeStyle = '#ff0055';
        ctx2d.lineWidth = 3;
        ctx2d.setLineDash([8, 4]);
      } else if (edge.kind === 'transfer') {
        ctx2d.strokeStyle = '#f59e0b';
        ctx2d.lineWidth = 2.5;
        ctx2d.setLineDash([6, 4]);
      } else {
        ctx2d.strokeStyle = 'rgba(59, 130, 246, 0.4)';
        ctx2d.lineWidth = 1.8;
        ctx2d.setLineDash([]);
      }
      ctx2d.stroke();
      ctx2d.setLineDash([]);
    });

    // Draw nodes
    nodes.forEach(node => {
      ctx2d.beginPath();
      ctx2d.arc(node.x, node.y, node.radius || 24, 0, Math.PI * 2);

      let stroke = '#3b82f6';
      if (node.kind === 'machine') {
        stroke = node.machinery_status === 'OBSOLETA' ? '#ef4444' : node.machinery_status === 'OCUPADA' ? '#f59e0b' : '#10b981';
      }

      ctx2d.fillStyle = '#0b0f19';
      ctx2d.fill();
      ctx2d.strokeStyle = stroke;
      ctx2d.lineWidth = 2.5;
      ctx2d.stroke();

      ctx2d.fillStyle = '#f8fafc';
      ctx2d.font = '600 11px Inter, sans-serif';
      ctx2d.textAlign = 'center';
      ctx2d.fillText(node.label || node.asset_number || 'NODE', node.x, node.y + (node.radius || 24) + 14);
    });

    ctx2d.restore();
  }
}
