import type { Equipment, Source } from "./schema"

const dateTime = new Intl.DateTimeFormat("es-SV", {
  timeZone: "America/El_Salvador",
  day: "2-digit",
  month: "short",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
  hour12: false,
})

export function formatInstant(value: string | null) {
  return value ? dateTime.format(new Date(value)) : "Sin fecha de lectura"
}

export function formatCount(value: number | null) {
  return value === null ? "—" : value.toLocaleString("es-SV")
}

export function originalState(value: string | null) {
  return value?.replaceAll("_", " ") ?? "Sin información"
}

export const relationLabels: Record<Equipment["relation_status"], string> = {
  confirmed: "Vínculo confirmado",
  candidate: "Vínculo por revisar",
  unlinked: "Sin vínculo confirmado",
}

export const sourceLabels: Record<Source["status"], string> = {
  fixture: "Ejemplo local",
  connected: "Conectada",
  partial: "Lectura parcial",
  not_configured: "Pendiente de conexión",
  disabled: "Consulta desactivada",
  error: "Error de lectura",
}

export function equipmentLabel(equipment: Equipment) {
  return equipment.code ?? equipment.asset_number ?? "Sin código"
}
