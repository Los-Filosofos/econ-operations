// AppShell Component

export function createShell({ currentPath = '/', onNavigate }) {
  const shell = document.createElement('div');
  shell.className = 'app-shell';

  const navLinks = [
    { path: '/', label: 'Vista Operativa', icon: 'layout-dashboard', section: 'Operación' },
    { path: '/movilidad', label: 'Trazabilidad & Movilidad', icon: 'truck', section: 'Operación' },
    { path: '/solicitudes', label: 'Proyectos & Solicitudes', icon: 'clipboard-list', section: 'Gestión' },
    { path: '/maquinaria', label: 'Maquinaria', icon: 'bulldozer', section: 'Gestión' },
    { path: '/operaciones', label: 'Traslados & Despacho', icon: 'clipboard-check', section: 'Gestión' },
    { path: '/indicadores', label: 'Reportes & SLAs', icon: 'chart-bar', section: 'Analítica' },
    { path: '/integracion', label: 'Traza Integración', icon: 'arrows-exchange', section: 'Analítica' },
    { path: '/presentacion', label: 'Presentación Ejecutiva', icon: 'checklist', section: 'Presentación' },
    { path: '/grafo', label: 'Grafo Topológico 3D', icon: 'database', section: 'Avanzado' },
    { path: '/fuentes', label: 'Fuentes & Cobertura', icon: 'database', section: 'Sistema' },
  ];

  let currentSection = '';
  const navHtml = navLinks.map(link => {
    let sectionHeader = '';
    if (link.section !== currentSection) {
      currentSection = link.section;
      sectionHeader = `<div class="app-sidebar__section">${currentSection}</div>`;
    }

    const isActive = currentPath === link.path;
    return `
      ${sectionHeader}
      <a href="#${link.path}" class="nav-item ${isActive ? 'nav-item--active' : ''}" data-path="${link.path}">
        <img src="/icons/${link.icon}.svg" class="nav-item__icon" alt="" />
        <span>${link.label}</span>
      </a>
    `;
  }).join('');

  shell.innerHTML = `
    <header class="app-header">
      <div style="display: flex; align-items: center; gap: 12px;">
        <button class="mobile-toggle" id="mobile-toggle" aria-label="Abrir menú">
          <img src="/icons/menu-2.svg" style="width: 20px; height: 20px;" alt="" />
        </button>
        <a href="#/" class="app-header__brand" style="text-decoration: none;">
          <div class="app-header__brand-icon">E</div>
          <span>ECON Hub</span>
        </a>
      </div>

      <!-- Slide 4 Header Search & Filter Bar -->
      <div class="hub-header-controls">
        <div class="hub-search-wrapper">
          <img src="/icons/search.svg" class="hub-search-icon" alt="" />
          <input type="text" id="global-search-input" class="hub-search-input" placeholder="Buscar proyecto, maquinaria o ID..." />
        </div>
        <select id="global-filter-type" class="hub-filter-select">
          <option value="all">Todos</option>
          <option value="projects">Proyectos</option>
          <option value="machinery">Maquinaria</option>
        </select>
      </div>

      <div class="app-header__status">
        <div class="app-header__mode" id="header-mode-badge">
          <span class="app-header__mode-dot"></span>
          <span>MODO FIXTURE</span>
        </div>
        <button id="refresh-btn" style="
          background: var(--bg-elevated);
          border: 1px solid var(--border);
          border-radius: var(--radius-sm);
          color: var(--text-secondary);
          padding: 6px 10px;
          cursor: pointer;
          display: flex;
          align-items: center;
          gap: 6px;
          font-size: 0.75rem;
          font-weight: 500;
        ">
          <img src="/icons/refresh.svg" style="width: 14px; height: 14px;" alt="" />
          <span>Actualizar</span>
        </button>
      </div>
    </header>

    <aside class="app-sidebar" id="app-sidebar">
      ${navHtml}
    </aside>

    <main class="app-content ${currentPath === '/' ? 'app-content--full' : ''}" id="app-content">
      <!-- Dynamic View Mounted Here -->
    </main>
  `;

  // Mobile drawer toggle
  const mobileToggle = shell.querySelector('#mobile-toggle');
  const sidebar = shell.querySelector('#app-sidebar');
  if (mobileToggle && sidebar) {
    mobileToggle.addEventListener('click', () => {
      sidebar.classList.toggle('app-sidebar--open');
    });
  }

  return shell;
}
