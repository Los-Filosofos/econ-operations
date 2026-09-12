import { ArrowRight } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import type { Hub, HubAlert } from "../schema"
import { EquipmentLink } from "./equipment-link"

export function AlertItem({
  alert,
  hub,
  expanded = false,
}: {
  alert: HubAlert
  hub: Hub
  expanded?: boolean
}) {
  const equipment = hub.equipment.find((item) => item.id === alert.equipment_id)
  const severityLabels = {
    critical: "Prioridad alta",
    warning: "Revisar",
    info: "Información",
  }
  return (
    <article className="attention-item" data-severity={alert.severity}>
      <div className="attention-top">
        <Badge
          variant={alert.severity === "critical" ? "destructive" : "outline"}
        >
          {severityLabels[alert.severity]}
        </Badge>
        {equipment ? <EquipmentLink equipment={equipment} /> : null}
      </div>
      <h3>{alert.title}</h3>
      <p>{alert.description}</p>
      <span className="attention-owner">
        Responsable propuesto · {alert.owner}
      </span>
      {expanded ? (
        <details className="evidence-disclosure">
          <summary>
            Ver evidencia de la alerta <ArrowRight className="size-3.5" />
          </summary>
          <ul>
            {alert.evidence.map((evidence, index) => (
              <li key={`${alert.id}-${index}`}>{evidence}</li>
            ))}
          </ul>
        </details>
      ) : null}
    </article>
  )
}
