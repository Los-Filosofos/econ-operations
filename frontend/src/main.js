import { Router } from './router.js';
import { createShell } from './components/shell.js';
import { renderGraphView } from './views/graph.js';
import { renderIndicatorsView } from './views/indicators.js';
import { renderIntegrationView } from './views/integration.js';
import { renderOperationsView } from './views/operations.js';
import { renderRequestsView } from './views/requests.js';
import { renderEquipmentView } from './views/equipment.js';
import { renderSourcesView } from './views/sources.js';

const appMount = document.getElementById('app');

let currentViewRenderer = null;

function mountView(path, renderer) {
  currentViewRenderer = renderer;

  // Render Shell if not mounted
  let shell = document.querySelector('.app-shell');
  if (!shell) {
    shell = createShell({ currentPath: path });
    appMount.innerHTML = '';
    appMount.appendChild(shell);

    // Attach global refresh handler
    shell.querySelector('#refresh-btn').addEventListener('click', () => {
      const content = shell.querySelector('#app-content');
      if (currentViewRenderer && content) {
        content.innerHTML = '<div style="padding: 24px; color: var(--text-secondary);">Actualizando vista...</div>';
        currentViewRenderer(content);
      }
    });
  }

  // Update active sidebar nav
  shell.querySelectorAll('.nav-item').forEach(link => {
    const linkPath = link.dataset.path;
    link.classList.toggle('nav-item--active', linkPath === path);
  });

  // Toggle full-screen layout mode for graph
  const contentArea = shell.querySelector('#app-content');
  contentArea.classList.toggle('app-content--full', path === '/');
  contentArea.innerHTML = '';

  // Execute view renderer
  renderer(contentArea);
}

const routes = {
  '/': () => mountView('/', renderGraphView),
  '/indicadores': () => mountView('/indicadores', renderIndicatorsView),
  '/integracion': () => mountView('/integracion', renderIntegrationView),
  '/operaciones': () => mountView('/operaciones', renderOperationsView),
  '/solicitudes': () => mountView('/solicitudes', renderRequestsView),
  '/maquinaria': () => mountView('/maquinaria', renderEquipmentView),
  '/fuentes': () => mountView('/fuentes', renderSourcesView),
};

const router = new Router(routes, () => {
  // Not found fallback
  mountView('/not-found', (container) => {
    container.innerHTML = `
      <div style="padding: 40px; text-align: center;">
        <h2>404 · Vista no encontrada</h2>
        <p style="color: var(--text-secondary); margin-top: 8px;">La ruta especificada no existe.</p>
        <a href="#/" style="display: inline-block; margin-top: 16px;">Volver al Grafo Operativo →</a>
      </div>
    `;
  });
});

router.init();
