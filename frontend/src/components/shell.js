// AppShell Component

export function createShell({ currentPath = '/', onNavigate }) {
  const shell = document.createElement('div');
  shell.className = 'app-shell';

  const navLinks = [
    { path: '/', label: 'Grafo Operativo', icon: 'truck', section: 'Operaciones' },
    { path: '/indicadores', label: 'Indicadores & SLA', icon: 'chart-bar', section: 'Analítica' },
    { path: '/integracion', label: 'Traza Integración', icon: 'arrows-exchange', section: 'Analítica' },
    { path: '/operaciones', label: 'Gestión Traslados', icon: 'clipboard-check', section: 'Gestión' },
    { path: '/solicitudes', label: 'Solicitudes', icon: 'clipboard-list', section: 'Gestión' },
    { path: '/maquinaria', label: 'Maquinaria', icon: 'bulldozer', section: 'Gestión' },
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
        <div class="app-header__brand">
          <div class="app-header__brand-icon">E</div>
          <span>ECON Hub</span>
        </div>
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
