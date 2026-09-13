export function renderCard({
  title,
  subtitle,
  value,
  secondaryValue,
  accentColor,
  icon,
  className = '',
  id = '',
  content = '',
}) {
  return `
    <div class="kpi-card ${className}" id="${id}" style="${accentColor ? `--card-accent: ${accentColor};` : ''}">
      <div class="kpi-card__header">
        <div>
          ${subtitle ? `<div class="kpi-card__owner">${subtitle}</div>` : ''}
          ${title ? `<div class="kpi-card__name">${title}</div>` : ''}
        </div>
        ${accentColor ? `<div class="kpi-card__semaphore" style="background: ${accentColor};"></div>` : ''}
      </div>
      ${value !== undefined ? `
        <div class="kpi-card__metrics">
          <div class="kpi-card__metric">
            <span class="kpi-card__metric-value">${value}</span>
            ${secondaryValue ? `<span class="kpi-card__metric-label">${secondaryValue}</span>` : ''}
          </div>
        </div>
      ` : ''}
      ${content}
    </div>
  `;
}
