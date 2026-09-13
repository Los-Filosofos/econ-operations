import { stateColor } from '../theme.js';

export function renderStatusBadge(status, label = null) {
  if (!status) return '<span class="text-secondary">—</span>';
  const color = stateColor(status);
  const text = label || status;

  return `
    <span style="
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 2px 8px;
      border-radius: 4px;
      font-size: 0.75rem;
      font-weight: 600;
      background: ${color}18;
      color: ${color};
      border: 1px solid ${color}35;
      font-family: var(--font-mono);
      white-space: nowrap;
    ">
      <span style="
        width: 6px;
        height: 6px;
        border-radius: 50%;
        background: ${color};
      "></span>
      ${text}
    </span>
  `;
}
