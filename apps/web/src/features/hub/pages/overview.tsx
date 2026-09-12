import { Link } from "@tanstack/react-router"
import {
  ArrowDownRight,
  ArrowUpRight,
  Boxes,
  CheckCheck,
  CircleAlert,
  Link2,
  Route,
  Wrench,
} from "lucide-react"
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
import {
  AlertItem,
  EquipmentPanel,
  HubBoundary,
  NoRecords,
  PageHeading,
} from "../components"
import { formatCount, formatInstant } from "../format"
import type { Hub } from "../schema"

function OverviewData({ hub }: { hub: Hub }) {
  const metrics = [
    {
      label: "Equipos consultados",
      value: hub.summary.equipment_count,
      detail: "En el alcance de esta lectura",
      icon: Boxes,
      filter: "all",
    },
    {
      label: "Estado disponible",
      value: hub.summary.administratively_available,
      detail: "Estado administrativo en Prisma",
      icon: CheckCheck,
      filter: "available",
    },
    {
      label: "Con falla activa",
      value: hub.summary.active_failures,
      detail: `${formatCount(hub.summary.stopped_equipment)} con paro registrado`,
      icon: Wrench,
      filter: "failure",
    },
    {
      label: "Sin vínculo confirmado",
      value: hub.summary.unlinked_equipment,
      detail: "Requieren relacionar sus fuentes",
      icon: Link2,
      filter: "unlinked",
    },
  ] as const
  return (
    <>
      <div className="metric-grid">
        {metrics.map(({ label, value, detail, icon: Icon, filter }) => (
          <Card key={label}>
            <CardHeader>
              <CardDescription>{label}</CardDescription>
              <CardAction>
                <Icon className="metric-icon size-4" />
              </CardAction>
            </CardHeader>
            <CardContent>
              <div className="metric-value">
                {formatCount(value)}
                <Link
                  to="/maquinaria"
                  search={(previous) => ({ ...previous, filter })}
                  aria-label={`Ver ${label.toLocaleLowerCase("es")}`}
                >
                  <ArrowUpRight className="size-5" />
                </Link>
              </div>
              <p className="metric-description">
                {value === null ? "Sin información suficiente" : detail}
              </p>
            </CardContent>
          </Card>
        ))}
      </div>
      <div className="overview-grid">
        <div className="overview-primary">
          <EquipmentPanel hub={hub} compact />
          <Card>
            <CardHeader>
              <CardTitle>Una lectura completa, paso a paso</CardTitle>
              <CardDescription>
                Cada fuente responde una pregunta diferente de la operación.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="operation-chain">
                <div>
                  <span className="chain-number">01</span>
                  <Boxes className="size-5" />
                  <strong>¿Está asignada?</strong>
                  <p>Solicitud, proyecto y estado del equipo.</p>
                  <Badge variant="outline">Prisma / Nexus</Badge>
                </div>
                <ArrowDownRight className="chain-arrow size-5" />
                <div>
                  <span className="chain-number">02</span>
                  <Route className="size-5" />
                  <strong>¿Cómo va el traslado?</strong>
                  <p>Tareas y observaciones con fecha.</p>
                  <Badge variant="outline">Startrack</Badge>
                </div>
                <ArrowDownRight className="chain-arrow size-5" />
                <div>
                  <span className="chain-number">03</span>
                  <CircleAlert className="size-5" />
                  <strong>¿Qué hace falta?</strong>
                  <p>Vínculos, evidencia y atención.</p>
                  <Badge variant="outline">Hub ECON</Badge>
                </div>
              </div>
            </CardContent>
            <CardFooter>
              <p className="footnote">
                Una tarea completada y una maquinaria ocupada pueden coexistir
                correctamente.
              </p>
            </CardFooter>
          </Card>
        </div>
        <Card>
          <CardHeader>
            <CardTitle>Requiere atención</CardTitle>
            <CardDescription>
              Casos que merecen una segunda mirada.
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
              Abrir centro de atención
              <ArrowUpRight data-icon="inline-end" />
            </Button>
          </CardFooter>
        </Card>
      </div>
      <div className="scope-note">
        <span className="status-dot" />
        <p>
          <strong>Alcance de la lectura.</strong> {hub.scope.description}{" "}
          <span>Datos al {formatInstant(hub.data_as_of)}.</span>
        </p>
      </div>
    </>
  )
}

export function OverviewPage() {
  return (
    <>
      <PageHeading
        eyebrow="CONTROL OPERATIVO"
        title="Vista general"
        description="Maquinaria, solicitudes y traslados. Toda la operación, en contexto."
        action={<Badge variant="outline">Prisma + Startrack</Badge>}
      />
      <HubBoundary>{(hub) => <OverviewData hub={hub} />}</HubBoundary>
    </>
  )
}
