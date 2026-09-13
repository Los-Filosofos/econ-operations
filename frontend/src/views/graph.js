import { api } from '../api.js';
import { stateColor } from '../theme.js';
import { renderStatusBadge } from '../components/status-badge.js';

export async function renderGraphView(container) {
  container.innerHTML = `
    <div class="graph-view">
      <!-- Stats bar -->
      <div class="graph-stats" id="graph-stats">
        <div class="graph-stat">
          <span class="graph-stat__dot" style="background: var(--state-active);"></span>
          <span>Cargando grafo...</span>
        </div>
      </div>

      <!-- Controls -->
      <div class="graph-controls">
        <button class="graph-controls__btn" id="graph-zoom-in" title="Acercar">+</button>
        <button class="graph-controls__btn" id="graph-zoom-out" title="Alejar">−</button>
        <button class="graph-controls__btn" id="graph-reset" title="Centrar">⟲</button>
      </div>

      <!-- Canvas container -->
      <div class="graph-canvas-container" id="graph-container">
        <canvas class="graph-canvas" id="graph-canvas"></canvas>
      </div>

      <!-- Legend -->
      <div class="graph-legend">
        <div style="font-size: 0.6875rem; font-weight: 600; color: var(--graph-text); margin-bottom: 4px;">ESTADOS</div>
        <div class="graph-legend__item">
          <div class="graph-legend__swatch" style="background: var(--state-active);"></div>
          <span>Disponible / Aprobada</span>
        </div>
        <div class="graph-legend__item">
          <div class="graph-legend__swatch" style="background: var(--state-pending);"></div>
          <span>Pendiente / En curso</span>
        </div>
        <div class="graph-legend__item">
          <div class="graph-legend__swatch" style="background: var(--state-busy);"></div>
          <span>Ocupada / Asignada</span>
        </div>
        <div class="graph-legend__item">
          <div class="graph-legend__swatch" style="background: var(--state-issue);"></div>
          <span>Falla / Obsoleta</span>
        </div>
      </div>

      <!-- Context detail panel -->
      <div class="graph-panel" id="graph-panel">
        <div class="graph-panel__inner" id="graph-panel-content">
          <!-- Filled on node click -->
        </div>
      </div>
    </div>
  `;

  const canvas = container.querySelector('#graph-canvas');
  const canvasContainer = container.querySelector('#graph-container');
  const panel = container.querySelector('#graph-panel');
  const panelContent = container.querySelector('#graph-panel-content');
  const statsContainer = container.querySelector('#graph-stats');

  let ctx = canvas.getContext('2d');
  let data = null;
  let nodes = [];
  let edges = [];
  let selectedNode = null;

  // Viewport transform
  let transform = { x: 0, y: 0, scale: 1 };
  let isDragging = false;
  let dragStart = { x: 0, y: 0 };

  function resizeCanvas() {
    const rect = canvasContainer.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    canvas.style.width = `${rect.width}px`;
    canvas.style.height = `${rect.height}px`;
    ctx.scale(dpr, dpr);
    render();
  }

  window.addEventListener('resize', resizeCanvas);

  try {
    data = await api.getGraph();
    nodes = data.nodes || [];
    edges = data.edges || [];

    // Layout nodes into coordinates
    computeLayout(nodes, edges);

    // Update stats bar
    const machineCount = nodes.filter(n => n.kind === 'machine').length;
    const projectCount = nodes.filter(n => n.kind === 'project').length;
    const movementCount = nodes.filter(n => n.kind === 'movement').length;
    const tensionsCount = (data.tensions || []).length;

    statsContainer.innerHTML = `
      <div class="graph-stat">
        <span class="graph-stat__dot" style="background: #199e70;"></span>
        <span>Maquinaria: <strong class="graph-stat__value">${machineCount}</strong></span>
      </div>
      <div class="graph-stat">
        <span class="graph-stat__dot" style="background: #5a8dbc;"></span>
        <span>Proyectos: <strong class="graph-stat__value">${projectCount}</strong></span>
      </div>
      <div class="graph-stat">
        <span class="graph-stat__dot" style="background: #eb6834;"></span>
        <span>Traslados: <strong class="graph-stat__value">${movementCount}</strong></span>
      </div>
      ${tensionsCount > 0 ? `
        <div class="graph-stat" style="border-color: rgba(208, 59, 59, 0.4);">
          <span class="graph-stat__dot" style="background: #d03b3b;"></span>
          <span>Tensiones: <strong class="graph-stat__value" style="color: #d03b3b;">${tensionsCount}</strong></span>
        </div>
      ` : ''}
    `;

    resizeCanvas();
    centerGraph();
  } catch (err) {
    statsContainer.innerHTML = `
      <div class="graph-stat" style="color: #d03b3b;">
        <span>Error al cargar grafo: ${err.message}</span>
      </div>
    `;
  }

  function computeLayout(nodesList, edgesList) {
    const projects = nodesList.filter(n => n.kind === 'project' || n.kind === 'place');
    const machines = nodesList.filter(n => n.kind === 'machine');
    const requests = nodesList.filter(n => n.kind === 'request');
    const movements = nodesList.filter(n => n.kind === 'movement');

    // Position projects in a central ring or line
    const centerX = 400;
    const centerY = 350;

    if (projects.length === 0) {
      // fallback
      projects.push({ id: 'virtual-hub', label: 'Centro de Operaciones', kind: 'place' });
    }

    projects.forEach((proj, idx) => {
      const angle = (idx / Math.max(1, projects.length)) * Math.PI * 2;
      const radius = projects.length === 1 ? 0 : 220;
      proj.x = centerX + Math.cos(angle) * radius;
      proj.y = centerY + Math.sin(angle) * radius;
      proj.radius = 42;
    });

    // Position machines orbiting the project or in a pool
    machines.forEach((m, idx) => {
      // Check if machine is assigned to a project
      const assignedEdge = edgesList.find(e => e.source === m.id && e.kind === 'assigned_to');
      const targetProj = assignedEdge ? projects.find(p => p.id === assignedEdge.target) : projects[0];

      const baseCenter = targetProj ? { x: targetProj.x, y: targetProj.y } : { x: centerX, y: centerY };
      const orbitAngle = (idx / Math.max(1, machines.length)) * Math.PI * 2 + (targetProj ? 0.5 : 0);
      const orbitRadius = 140 + (idx % 3) * 35;

      m.x = baseCenter.x + Math.cos(orbitAngle) * orbitRadius;
      m.y = baseCenter.y + Math.sin(orbitAngle) * orbitRadius;
      m.radius = 24;
    });

    // Position requests
    requests.forEach((r, idx) => {
      r.x = centerX - 260 + (idx * 90);
      r.y = centerY + 240;
      r.radius = 18;
    });

    // Position movements
    movements.forEach((mv, idx) => {
      mv.x = centerX + 180 + (idx * 80);
      mv.y = centerY - 200;
      mv.radius = 20;
    });
  }

  function render() {
    if (!ctx) return;
    const width = canvas.width / (window.devicePixelRatio || 1);
    const height = canvas.height / (window.devicePixelRatio || 1);

    ctx.save();
    ctx.clearRect(0, 0, width, height);

    // Background grid
    ctx.fillStyle = '#111513';
    ctx.fillRect(0, 0, width, height);

    ctx.translate(transform.x, transform.y);
    ctx.scale(transform.scale, transform.scale);

    // Draw grid dots
    ctx.fillStyle = 'rgba(255, 255, 255, 0.04)';
    const gridSize = 40;
    const startX = Math.floor(-transform.x / transform.scale / gridSize) * gridSize;
    const startY = Math.floor(-transform.y / transform.scale / gridSize) * gridSize;
    const endX = startX + (width / transform.scale) + gridSize;
    const endY = startY + (height / transform.scale) + gridSize;

    for (let gx = startX; gx < endX; gx += gridSize) {
      for (let gy = startY; gy < endY; gy += gridSize) {
        ctx.beginPath();
        ctx.arc(gx, gy, 1, 0, Math.PI * 2);
        ctx.fill();
      }
    }

    // Draw edges
    edges.forEach(edge => {
      const src = nodes.find(n => n.id === edge.source);
      const tgt = nodes.find(n => n.id === edge.target);
      if (!src || !tgt) return;

      ctx.beginPath();
      ctx.moveTo(src.x, src.y);
      ctx.lineTo(tgt.x, tgt.y);

      if (edge.kind === 'assigned_to') {
        ctx.strokeStyle = 'rgba(142, 148, 140, 0.5)';
        ctx.lineWidth = 2;
        ctx.setLineDash([]);
      } else if (edge.kind === 'transfer') {
        ctx.strokeStyle = '#5a8dbc';
        ctx.lineWidth = 2.5;
        ctx.setLineDash([6, 4]);
      } else {
        ctx.strokeStyle = 'rgba(142, 148, 140, 0.3)';
        ctx.lineWidth = 1.5;
        ctx.setLineDash([]);
      }
      ctx.stroke();
      ctx.setLineDash([]);
    });

    // Draw nodes
    nodes.forEach(node => {
      const isSelected = selectedNode && selectedNode.id === node.id;

      // Glow effect for selected
      if (isSelected) {
        ctx.beginPath();
        ctx.arc(node.x, node.y, node.radius + 8, 0, Math.PI * 2);
        ctx.fillStyle = 'rgba(20, 79, 129, 0.35)';
        ctx.fill();
      }

      ctx.beginPath();
      ctx.arc(node.x, node.y, node.radius, 0, Math.PI * 2);

      let fillColor = '#161B18';
      let strokeColor = '#39413B';
      let strokeWidth = 2;

      if (node.kind === 'project' || node.kind === 'place') {
        fillColor = '#1c2333';
        strokeColor = '#5a8dbc';
        strokeWidth = 3;
      } else if (node.kind === 'machine') {
        const color = stateColor(node.machinery_status || 'DISPONIBLE');
        fillColor = '#161B18';
        strokeColor = color;
        strokeWidth = 2.5;
      } else if (node.kind === 'movement') {
        fillColor = '#241a14';
        strokeColor = '#eb6834';
        strokeWidth = 2;
      } else if (node.kind === 'request') {
        fillColor = '#19231f';
        strokeColor = '#199e70';
        strokeWidth = 2;
      }

      ctx.fillStyle = fillColor;
      ctx.fill();
      ctx.strokeStyle = strokeColor;
      ctx.lineWidth = strokeWidth;
      ctx.stroke();

      // Node Label
      ctx.fillStyle = '#F1F0EA';
      ctx.font = node.kind === 'project' ? '600 12px Inter, sans-serif' : '500 11px Inter, sans-serif';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';

      const shortLabel = node.label || node.id.split(':').pop();
      const displayLabel = shortLabel.length > 16 ? shortLabel.slice(0, 14) + '…' : shortLabel;

      ctx.fillText(displayLabel, node.x, node.y + node.radius + 14);

      // Node inner icon / badge
      if (node.kind === 'project') {
        ctx.fillStyle = '#5a8dbc';
        ctx.font = '700 13px Inter, sans-serif';
        ctx.fillText('PROY', node.x, node.y);
      } else if (node.kind === 'machine') {
        ctx.fillStyle = strokeColor;
        ctx.font = '600 11px Roboto Mono, monospace';
        const code = node.asset_number || node.label || 'EQ';
        ctx.fillText(code, node.x, node.y);
      } else if (node.kind === 'movement') {
        ctx.fillStyle = '#eb6834';
        ctx.font = '600 10px Inter, sans-serif';
        ctx.fillText('MOV', node.x, node.y);
      } else if (node.kind === 'request') {
        ctx.fillStyle = '#199e70';
        ctx.font = '600 10px Inter, sans-serif';
        ctx.fillText('REQ', node.x, node.y);
      }
    });

    ctx.restore();
  }

  function centerGraph() {
    if (nodes.length === 0) return;
    const rect = canvasContainer.getBoundingClientRect();
    transform = {
      x: rect.width / 2 - 400,
      y: rect.height / 2 - 350,
      scale: 1,
    };
    render();
  }

  // Mouse / Touch Interaction
  canvasContainer.addEventListener('mousedown', (e) => {
    isDragging = true;
    dragStart = { x: e.clientX - transform.x, y: e.clientY - transform.y };
  });

  window.addEventListener('mousemove', (e) => {
    if (!isDragging) return;
    transform.x = e.clientX - dragStart.x;
    transform.y = e.clientY - dragStart.y;
    render();
  });

  window.addEventListener('mouseup', () => {
    isDragging = false;
  });

  canvasContainer.addEventListener('wheel', (e) => {
    e.preventDefault();
    const zoomFactor = e.deltaY < 0 ? 1.1 : 0.9;
    const newScale = Math.min(2.5, Math.max(0.4, transform.scale * zoomFactor));

    const rect = canvasContainer.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;

    transform.x = mouseX - (mouseX - transform.x) * (newScale / transform.scale);
    transform.y = mouseY - (mouseY - transform.y) * (newScale / transform.scale);
    transform.scale = newScale;

    render();
  }, { passive: false });

  // Node selection on click
  canvasContainer.addEventListener('click', (e) => {
    const rect = canvasContainer.getBoundingClientRect();
    const clickX = (e.clientX - rect.left - transform.x) / transform.scale;
    const clickY = (e.clientY - rect.top - transform.y) / transform.scale;

    let clicked = null;
    for (const node of nodes) {
      const dist = Math.hypot(clickX - node.x, clickY - node.y);
      if (dist <= node.radius + 4) {
        clicked = node;
        break;
      }
    }

    selectedNode = clicked;
    render();

    if (clicked) {
      showNodeDetail(clicked);
    } else {
      panel.classList.remove('graph-panel--open');
    }
  });

  // Controls listeners
  container.querySelector('#graph-zoom-in').addEventListener('click', () => {
    transform.scale = Math.min(2.5, transform.scale * 1.2);
    render();
  });

  container.querySelector('#graph-zoom-out').addEventListener('click', () => {
    transform.scale = Math.max(0.4, transform.scale * 0.8);
    render();
  });

  container.querySelector('#graph-reset').addEventListener('click', () => {
    centerGraph();
  });

  function showNodeDetail(node) {
    panel.classList.add('graph-panel--open');

    let specificHtml = '';
    if (node.kind === 'machine') {
      specificHtml = `
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
          <div class="graph-panel__value">${node.company || '—'}</div>
        </div>
        ${node.assignment_starts_on ? `
          <div class="graph-panel__section">
            <div class="graph-panel__label">Período de Uso</div>
            <div class="graph-panel__value text-mono">${node.assignment_starts_on} → ${node.assignment_ends_on || 'Indefinido'}</div>
          </div>
        ` : ''}
      `;
    } else if (node.kind === 'project' || node.kind === 'place') {
      specificHtml = `
        <div class="graph-panel__section">
          <div class="graph-panel__label">Destino / POI</div>
          <div class="graph-panel__value">${node.label}</div>
        </div>
      `;
    }

    const evidenceHtml = (node.evidence || []).map(ev => `
      <div class="graph-panel__evidence-item">
        <span class="graph-panel__evidence-icon">📄</span>
        <div>
          <div><strong>Fuente:</strong> ${ev.origin || ev.provenance?.source || '—'} (${ev.provenance?.environment || 'sandbox'})</div>
          <div class="text-mono" style="font-size: 0.6875rem; color: var(--text-tertiary);">${ev.reference || ev.source_id}</div>
        </div>
      </div>
    `).join('');

    const missingHtml = (node.missing || []).map(m => `
      <div style="font-size: 0.75rem; color: var(--state-pending); padding: 4px 8px; background: rgba(235, 104, 52, 0.1); border-radius: 4px; margin-bottom: 4px;">
        ⚠ ${m}
      </div>
    `).join('');

    panelContent.innerHTML = `
      <div class="graph-panel__header">
        <div>
          <div style="font-size: 0.6875rem; font-weight: 600; text-transform: uppercase; color: var(--text-tertiary); letter-spacing: 0.08em;">${node.kind}</div>
          <div class="graph-panel__title">${node.label || node.name || node.id}</div>
        </div>
        <button class="graph-panel__close" id="panel-close-btn">&times;</button>
      </div>

      ${specificHtml}

      ${evidenceHtml ? `
        <div class="graph-panel__section">
          <div class="graph-panel__label">Evidencia Comprobada (${node.evidence.length})</div>
          <div class="graph-panel__evidence">${evidenceHtml}</div>
        </div>
      ` : ''}

      ${missingHtml ? `
        <div class="graph-panel__section">
          <div class="graph-panel__label">Faltantes & Observaciones</div>
          <div>${missingHtml}</div>
        </div>
      ` : ''}
    `;

    panelContent.querySelector('#panel-close-btn').addEventListener('click', () => {
      panel.classList.remove('graph-panel--open');
      selectedNode = null;
      render();
    });
  }
}
