import { Link } from "@tanstack/react-router"
import { ArrowUpRight } from "lucide-react"
import { formatCount } from "../format"
import type { Hub } from "../schema"

export function SummaryMetrics({ hub }: { hub: Hub }) {
  const metrics = [
    {
      label: "Equipos consultados",
      value: hub.summary.equipment_count,
      detail: "En el alcance de esta lectura",
      filter: "all",
    },
    {
      label: "Estado disponible",
      value: hub.summary.administratively_available,
      detail: "Estado administrativo en Prisma",
      filter: "available",
    },
    {
      label: "Con falla activa",
      value: hub.summary.active_failures,
      detail: `${formatCount(hub.summary.stopped_equipment)} con paro registrado`,
      filter: "failure",
    },
    {
      label: "Sin vínculo confirmado",
      value: hub.summary.unlinked_equipment,
      detail: "Correspondencias por revisar",
      filter: "unlinked",
    },
  ] as const
  return (
    <div
      className="metric-grid"
      aria-label="Indicadores del alcance consultado"
    >
      {metrics.map(({ label, value, detail, filter }, index) => (
        <Link
          key={filter}
          className="metric"
          to="/maquinaria"
          search={(previous) => ({ ...previous, filter })}
          aria-label={`Ver ${label.toLocaleLowerCase("es")}`}
        >
          <span className="metric-label">
            {label}
            <span className="metric-index">0{index + 1}</span>
          </span>
          <span className="metric-value">
            {formatCount(value)}
            <ArrowUpRight className="size-4" />
          </span>
          <span className="metric-description">
            {value === null ? "Sin información suficiente" : detail}
          </span>
        </Link>
      ))}
    </div>
  )
}
