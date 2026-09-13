// Theme tokens & state color mappers matching backend app/dashboard/theme.py

export const BRAND = "#144f81";
export const BRAND_LIGHT = "#5a8dbc";

export const FAMILY_COLORS = {
  pending: "#eb6834",
  active: "#199e70",
  busy: "#4a3aa7",
  issue: "#d03b3b",
  neutral: "#868e96",
};

export const FAMILIES = {
  pending: new Set(["PENDIENTE", "PENDING", "DRAFT", "QUEUED", "SENDING", "EN CURSO"]),
  active: new Set(["APROBADA", "APPROVED", "DISPONIBLE", "AVAILABLE", "SENT", "COMPLETADA", "COMPLETED"]),
  busy: new Set(["OCUPADA", "OCCUPIED", "ASIGNADA", "ASSIGNED"]),
  issue: new Set(["FAILED", "BLOCKED", "UNKNOWN", "RECHAZADA", "REJECTED", "OBSOLETA"]),
};

export const SEQUENTIAL = ["#86b6ef", "#5598e7", "#2a78d6", "#1c5cab", "#0d366b"];

export function stateFamily(val) {
  if (!val) return "neutral";
  const key = String(val).trim().toUpperCase();
  if (FAMILY_COLORS[key.toLowerCase()]) return key.toLowerCase();
  for (const [family, set] of Object.entries(FAMILIES)) {
    if (set.has(key)) return family;
  }
  return "neutral";
}

export function stateColor(val) {
  return FAMILY_COLORS[stateFamily(val)] || FAMILY_COLORS.neutral;
}
