import { api } from '../api.js';
import { renderCard } from '../components/card.js';
import { renderDataTable } from '../components/data-table.js';
import { renderStatusBadge } from '../components/status-badge.js';
import Chart from 'chart.js/auto';

export async function renderIndicatorsView(container) {
  container.innerHTML = `
    <div class="page-header fade-in">
      <div>
        <h1 class="page-header__title">Indicadores Operativos & SLAs</h1>
        <div class="page-header__subtitle">Métricas de gobernanza, tiempos de aprobación, vencimientos y recepción sin promedios falsos</div>
      </div>
    </div>

    <!-- Area Summary Cards -->
    <div class="indicators-grid fade-in stagger-1" id="kpi-cards-container">
      <div style="color: var(--text-secondary); padding: 20px;">Cargando indicadores...</div>
    </div>

    <!-- Chart Section -->
    <div class="indicators-chart fade-in stagger-2">
      <div class="indicators-chart__title">Estado de Evaluación de Indicadores por Ficha</div>
      <div style="height: 240px; position: relative;">
        <canvas id="indicators-bar-chart"></canvas>
      </div>
    </div>

    <!-- Table Section -->
    <div style="margin-bottom: var(--sp-6);" class="fade-in stagger-3" id="indicators-table-container"></div>

    <!-- SLA Sheets Accordion -->
    <div class="fade-in stagger-4">
      <h3 style="margin-bottom: var(--sp-4);">Fichas de SLA y Decisiones Operativas (8 Indicadores)</h3>
      <div class="sla-accordion" id="sla-accordion-container"></div>
    </div>

    <!-- Notes -->
    <div class="indicator-notes fade-in stagger-5" id="indicator-notes-container"></div>
  `;

  try {
    const data = await api.getIndicators();
    const indicators = data.indicators || [];

    // 1. Group indicators by owner
    const owners = {
      'Logística': { evaluable: 0, total: 0, color: '#5a8dbc', name: 'Logística y Traslados' },
      'Proyectos': { evaluable: 0, total: 0, color: '#199e70', name: 'Gestión de Proyectos' },
      'Mantenimiento': { evaluable: 0, total: 0, color: '#eb6834', name: 'Mantenimiento y Fallas' },
      'Información': { evaluable: 0, total: 0, color: '#86b6ef', name: 'Gobernanza de Datos' },
    };

    indicators.forEach(ind => {
      const ownerKey = ind.sheet.owner || 'Logística';
      if (!owners[ownerKey]) {
        owners[ownerKey] = { evaluable: 0, total: 0, color: '#868e96', name: ownerKey };
      }
      owners[ownerKey].total += (ind.evaluable_count + ind.partial_count + ind.not_evaluable_count) || (ind.rows ? ind.rows.length : 1);
      owners[ownerKey].evaluable += ind.evaluable_count || 0;
    });

    const cardsHtml = Object.entries(owners).map(([owner, info]) => {
      return renderCard({
        title: info.name,
        subtitle: `ÁREA RESPONSABLE: ${owner.toUpperCase()}`,
        value: info.evaluable,
        secondaryValue: `Casos evaluables (${info.total} observados)`,
        accentColor: info.color,
      });
    }).join('');

    container.querySelector('#kpi-cards-container').innerHTML = cardsHtml;

    // 2. Render Chart.js
    const chartCtx = container.querySelector('#indicators-bar-chart').getContext('2d');
    const labels = indicators.map(i => i.sheet.name.length > 28 ? i.sheet.name.slice(0, 26) + '…' : i.sheet.name);
    const evaluableData = indicators.map(i => i.evaluable_count);
    const notEvaluableData = indicators.map(i => i.not_evaluable_count);

    new Chart(chartCtx, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [
          {
            label: 'Evaluable con Evidencia',
            data: evaluableData,
            backgroundColor: '#199e70',
            borderRadius: 4,
          },
          {
            label: 'No Evaluable / Faltante',
            data: notEvaluableData,
            backgroundColor: '#30363d',
            borderRadius: 4,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: 'top',
            labels: { color: '#8b949e', font: { family: 'Inter' } },
          },
          tooltip: {
            callbacks: {
              title: (items) => indicators[items[0].dataIndex]?.sheet.name,
              afterBody: (items) => {
                const ind = indicators[items[0].dataIndex];
                return `Pregunta: ${ind?.sheet.question}\nDecisión: ${ind?.sheet.decision}`;
              }
            }
          }
        },
        scales: {
          x: {
            stacked: true,
            ticks: { color: '#8b949e', font: { size: 10 } },
            grid: { color: 'rgba(255,255,255,0.05)' },
          },
          y: {
            stacked: true,
            ticks: { color: '#8b949e', stepSize: 1 },
            grid: { color: 'rgba(255,255,255,0.05)' },
          },
        },
      },
    });

    // 3. Render Table of all Rows
    const allRows = [];
    indicators.forEach(ind => {
      (ind.rows || []).forEach(row => {
        allRows.push({
          indicator: ind.sheet.name,
          owner: ind.sheet.owner,
          subject: row.subject_id || row.id || '—',
          status: row.evaluable ? 'EVALUABLE' : (row.reason || 'NO_EVALUABLE'),
          value: row.value != null ? `${row.value} ${ind.sheet.unit}` : '—',
          reason: row.reason || ind.sheet.status_rule || '—',
        });
      });
    });

    const tableEl = renderDataTable({
      title: 'Detalle de Hechos y Casos Evaluados',
      columns: [
        { header: 'Indicador', accessor: 'indicator' },
        { header: 'Área', accessor: 'owner' },
        { header: 'Sujeto / ID', accessor: 'subject' },
        { header: 'Valor Medido', accessor: 'value' },
        {
          header: 'Evaluabilidad',
          accessor: 'status',
          render: (r) => renderStatusBadge(r.status === 'EVALUABLE' ? 'APROBADA' : 'PENDIENTE', r.status),
        },
        { header: 'Motivo / Regla', accessor: 'reason' },
      ],
      data: allRows,
      emptyMessage: 'No hay filas evaluadas en el corte actual (consulte en vivo con sincronización activa).',
    });

    container.querySelector('#indicators-table-container').appendChild(tableEl);

    // 4. Render SLA Accordion
    const accordionHtml = indicators.map((ind, idx) => `
      <div class="sla-item" id="sla-item-${idx}">
        <div class="sla-item__header" onclick="this.parentElement.classList.toggle('sla-item--open')">
          <div class="sla-item__header-left">
            <span style="font-family: var(--font-mono); font-size: 0.75rem; color: var(--brand-light);">#0${idx + 1}</span>
            <span class="sla-item__indicator">${ind.sheet.name}</span>
            <span style="font-size: 0.6875rem; color: var(--text-tertiary);">[${ind.sheet.owner}]</span>
          </div>
          <div style="display: flex; align-items: center; gap: 8px;">
            ${renderStatusBadge(ind.status === 'evaluable' ? 'APROBADA' : 'PENDIENTE', ind.status)}
            <span class="sla-item__chevron">▼</span>
          </div>
        </div>
        <div class="sla-item__body">
          <div class="sla-item__content">
            <div class="sla-field">
              <div class="sla-field__label">Pregunta de Negocio</div>
              <div class="sla-field__value">${ind.sheet.question}</div>
            </div>
            <div class="sla-field">
              <div class="sla-field__label">Decisión Operativa Asociada</div>
              <div class="sla-field__value" style="color: var(--text-primary); font-weight: 500;">${ind.sheet.decision}</div>
            </div>
            <div class="sla-field">
              <div class="sla-field__label">Población & Unidad de Medida</div>
              <div class="sla-field__value">${ind.sheet.population} · Unidad: <span class="text-mono">${ind.sheet.unit}</span></div>
            </div>
            <div class="sla-field">
              <div class="sla-field__label">Regla de Estado & SLA Propuesto</div>
              <div class="sla-field__value text-mono" style="font-size: 0.75rem;">${ind.sheet.status_rule}</div>
            </div>
          </div>
        </div>
      </div>
    `).join('');

    container.querySelector('#sla-accordion-container').innerHTML = accordionHtml;

    // 5. Render Notes
    if (data.notes && data.notes.length > 0) {
      container.querySelector('#indicator-notes-container').innerHTML = `
        <div class="indicator-notes__title">Principios Metodológicos de los Indicadores</div>
        <ul class="indicator-notes__list">
          ${data.notes.map(n => `<li class="indicator-notes__item">${n}</li>`).join('')}
        </ul>
      `;
    }
  } catch (err) {
    container.innerHTML += `<div style="color: #d03b3b; padding: 20px;">Error al cargar indicadores: ${err.message}</div>`;
  }
}
