export function renderDataTable({
  id = 'table-' + Math.random().toString(36).substr(2, 9),
  title = '',
  columns = [],
  data = [],
  rowClick = null,
  emptyMessage = 'No hay registros para mostrar',
}) {
  const container = document.createElement('div');
  container.className = 'data-table-container fade-in';
  container.id = id;

  let currentData = [...data];
  let sortCol = null;
  let sortAsc = true;
  let filterText = '';

  function renderTableBody() {
    let filtered = currentData.filter(row => {
      if (!filterText) return true;
      return columns.some(col => {
        const val = typeof col.accessor === 'function' ? col.accessor(row) : row[col.accessor];
        return String(val ?? '').toLowerCase().includes(filterText.toLowerCase());
      });
    });

    if (sortCol) {
      filtered.sort((a, b) => {
        const valA = typeof sortCol.accessor === 'function' ? sortCol.accessor(a) : a[sortCol.accessor];
        const valB = typeof sortCol.accessor === 'function' ? sortCol.accessor(b) : b[sortCol.accessor];
        if (valA == null) return 1;
        if (valB == null) return -1;
        if (valA < valB) return sortAsc ? -1 : 1;
        if (valA > valB) return sortAsc ? 1 : -1;
        return 0;
      });
    }

    const tbody = container.querySelector('tbody');
    const countBadge = container.querySelector('.data-table-header__count');
    if (countBadge) countBadge.textContent = `${filtered.length} de ${data.length}`;

    if (!tbody) return;

    if (filtered.length === 0) {
      tbody.innerHTML = `<tr><td colspan="${columns.length}" style="text-align:center; padding: 24px; color: var(--text-tertiary);">${emptyMessage}</td></tr>`;
      return;
    }

    tbody.innerHTML = filtered.map((row, idx) => {
      const cells = columns.map(col => {
        let content = '';
        if (col.render) {
          content = col.render(row);
        } else {
          const raw = typeof col.accessor === 'function' ? col.accessor(row) : row[col.accessor];
          content = raw != null ? String(raw) : '—';
        }
        return `<td>${content}</td>`;
      }).join('');

      return `<tr class="${rowClick ? 'data-table tr--clickable' : ''}" data-row-idx="${idx}">${cells}</tr>`;
    }).join('');

    if (rowClick) {
      tbody.querySelectorAll('tr').forEach((tr, idx) => {
        tr.addEventListener('click', () => rowClick(filtered[idx]));
      });
    }
  }

  container.innerHTML = `
    <div class="data-table-header">
      <div class="data-table-header__title">${title}</div>
      <div class="data-table-header__count">${data.length} registros</div>
    </div>
    <div class="data-table-filter">
      <input type="text" class="data-table-filter__input" placeholder="Filtrar por texto..." />
    </div>
    <div style="overflow-x: auto;">
      <table class="data-table">
        <thead>
          <tr>
            ${columns.map((col, idx) => `
              <th data-col-idx="${idx}">
                ${col.header}
                <span class="sort-arrow">↕</span>
              </th>
            `).join('')}
          </tr>
        </thead>
        <tbody></tbody>
      </table>
    </div>
  `;

  // Attach search filter listener
  const filterInput = container.querySelector('.data-table-filter__input');
  filterInput.addEventListener('input', (e) => {
    filterText = e.target.value;
    renderTableBody();
  });

  // Attach sort headers
  container.querySelectorAll('th').forEach(th => {
    th.addEventListener('click', () => {
      const colIdx = parseInt(th.dataset.colIdx, 10);
      const col = columns[colIdx];
      if (sortCol === col) {
        sortAsc = !sortAsc;
      } else {
        sortCol = col;
        sortAsc = true;
      }

      container.querySelectorAll('th').forEach(h => {
        h.classList.remove('data-table th--sorted');
        const arrow = h.querySelector('.sort-arrow');
        if (arrow) arrow.textContent = '↕';
      });

      th.classList.add('data-table th--sorted');
      const arrow = th.querySelector('.sort-arrow');
      if (arrow) arrow.textContent = sortAsc ? '↑' : '↓';

      renderTableBody();
    });
  });

  renderTableBody();
  return container;
}
