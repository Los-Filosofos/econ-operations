import { Link } from "@tanstack/react-router"
import { ArrowUpRight } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardAction,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { AlertItem } from "../components/alert-item"
import { EquipmentPanel } from "../components/equipment-table"
import { HubBoundary } from "../components/hub-boundary"
import { NoRecords } from "../components/no-records"
import { OperationLedger } from "../components/operation-ledger"
import { PageHeading } from "../components/page-heading"
import { SummaryMetrics } from "../components/summary-metrics"
import { formatCount, formatInstant } from "../format"
import type { Hub } from "../schema"

function OverviewData({ hub }: { hub: Hub }) {
  return (
    <>
      <SummaryMetrics hub={hub} />
      <div className="overview-grid">
        <div className="overview-primary">
          <OperationLedger hub={hub} />
          <EquipmentPanel equipment={hub.equipment} mode={hub.mode} compact />
        </div>
        <Card className="attention-panel">
          <CardHeader>
            <CardTitle>Requiere atención</CardTitle>
            <CardDescription>
              Condiciones que necesitan revisión.
            </CardDescription>
            <CardAction>
              <Badge variant="secondary">
                {formatCount(hub.summary.alerts_count)}
              </Badge>
            </CardAction>
          </CardHeader>
          <CardContent className="px-0">
            {hub.alerts.length ? (
              hub.alerts
                .slice(0, 3)
                .map((alert) => (
                  <AlertItem key={alert.id} alert={alert} hub={hub} />
                ))
            ) : (
              <NoRecords
                title={
                  hub.summary.alerts_count === null
                    ? "Sin información para evaluar"
                    : "Sin alertas en este alcance"
                }
                description="Las alertas se evalúan sobre los registros de la consulta."
              />
            )}
          </CardContent>
          <CardFooter>
            <Button
              className="w-full"
              variant="outline"
              render={<Link to="/alertas" search={true} />}
              nativeButton={false}
            >
              Ver todos los casos <ArrowUpRight data-icon="inline-end" />
            </Button>
          </CardFooter>
        </Card>
      </div>
      <div className="scope-note">
        <span className="status-dot" />
        <p>
          <strong>Alcance de la lectura.</strong> {hub.scope.description} Datos
          al {formatInstant(hub.data_as_of)}.
        </p>
      </div>
    </>
  )
}

export function OverviewPage() {
  return (
    <>
      <PageHeading
        eyebrow="01 / CONTROL OPERATIVO"
        title="Vista general"
        description="Del requerimiento del proyecto al traslado de la maquinaria."
        action={<Badge variant="outline">Prisma / Nexus + Startrack</Badge>}
      />
      <HubBoundary>{(hub) => <OverviewData hub={hub} />}</HubBoundary>
    </>
  )
}
