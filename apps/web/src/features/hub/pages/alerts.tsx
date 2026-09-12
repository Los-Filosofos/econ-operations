import { useState } from "react"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"
import { AlertItem } from "../components/alert-item"
import { HubBoundary } from "../components/hub-boundary"
import { NoRecords } from "../components/no-records"
import { PageHeading } from "../components/page-heading"
import type { Hub } from "../schema"

function AlertsData({ hub }: { hub: Hub }) {
  const [severity, setSeverity] = useState("all")
  const alerts = hub.alerts.filter(
    (alert) => severity === "all" || alert.severity === severity
  )
  return (
    <>
      <div className="filter-toolbar">
        <ToggleGroup
          aria-label="Filtrar alertas por prioridad"
          value={[severity]}
          onValueChange={(value) => {
            if (value[0]) setSeverity(value[0])
          }}
          variant="outline"
          spacing={0}
        >
          <ToggleGroupItem value="all">Todos los casos</ToggleGroupItem>
          <ToggleGroupItem value="critical">Prioridad alta</ToggleGroupItem>
          <ToggleGroupItem value="warning">Por revisar</ToggleGroupItem>
          <ToggleGroupItem value="info">Información</ToggleGroupItem>
        </ToggleGroup>
        <span>{alerts.length} casos visibles</span>
      </div>
      <Card>
        <CardHeader>
          <CardTitle>Atención con evidencia</CardTitle>
          <CardDescription>
            Responsables propuestos y condiciones que originan cada caso. Reglas
            sujetas a validación operativa.
          </CardDescription>
        </CardHeader>
        <CardContent className="px-0">
          {alerts.length ? (
            alerts.map((alert) => (
              <AlertItem key={alert.id} alert={alert} hub={hub} expanded />
            ))
          ) : (
            <NoRecords
              title={
                hub.summary.alerts_count === null
                  ? "Sin información suficiente para evaluar"
                  : "No hay casos en este filtro"
              }
              description="Un conjunto vacío no permite concluir que toda la operación está libre de riesgos."
            />
          )}
        </CardContent>
      </Card>
    </>
  )
}

export function AlertsPage() {
  return (
    <>
      <PageHeading
        eyebrow="05 / SEGUIMIENTO OPERATIVO"
        title="Centro de atención"
        description="Identifica qué necesita revisión, quién puede atenderlo y por qué."
      />
      <HubBoundary>{(hub) => <AlertsData hub={hub} />}</HubBoundary>
    </>
  )
}
