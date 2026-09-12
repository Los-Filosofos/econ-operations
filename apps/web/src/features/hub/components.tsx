import type { ReactNode } from "react"
import { Link } from "@tanstack/react-router"
import {
  ArrowRight,
  ArrowUpRight,
  Boxes,
  Cable,
  CircleAlert,
  Clock3,
  Database,
  Link2,
  RefreshCw,
  Unplug,
} from "lucide-react"

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
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
  Empty,
  EmptyContent,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "@/components/ui/empty"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { useHub } from "./api"
import {
  equipmentLabel,
  formatInstant,
  originalState,
  relationLabels,
  sourceLabels,
} from "./format"
import type { Equipment, Hub, HubAlert, Provenance, Source } from "./schema"

export function PageHeading({
  eyebrow,
  title,
  description,
  action,
}: {
  eyebrow: string
  title: string
  description: string
  action?: ReactNode
}) {
  return (
    <div className="page-heading">
      <div>
        <p className="eyebrow">{eyebrow}</p>
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      {action}
    </div>
  )
}

export function HubBoundary({
  children,
}: {
  children: (hub: Hub) => ReactNode
}) {
  const query = useHub()
  if (query.isPending)
    return (
      <div
        className="loading-state"
        role="status"
        aria-label="Consultando información"
      >
        <div className="metric-grid">
          {[1, 2, 3, 4].map((item) => (
            <Skeleton key={item} className="h-36" />
          ))}
        </div>
        <Skeleton className="h-80 w-full" />
        <span className="sr-only">Consultando información del hub…</span>
      </div>
    )
  if (query.isError)
    return (
      <Empty className="empty-panel">
        <EmptyHeader>
          <EmptyMedia variant="icon">
            <Unplug />
          </EmptyMedia>
          <EmptyTitle>No pudimos consultar la operación</EmptyTitle>
          <EmptyDescription>{query.error.message}</EmptyDescription>
        </EmptyHeader>
        <EmptyContent>
          <Button
            onClick={() => void query.refetch()}
            disabled={query.isFetching}
          >
            <RefreshCw data-icon="inline-start" />
            Reintentar consulta
          </Button>
        </EmptyContent>
      </Empty>
    )
  return (
    <>
      {query.data.scope.complete ? null : (
        <Alert className="mb-6">
          <CircleAlert />
          <AlertTitle>La consulta tiene información incompleta</AlertTitle>
          <AlertDescription>
            {query.data.scope.description} Las cifras describen únicamente el
            alcance consultado.
          </AlertDescription>
        </Alert>
      )}
      {children(query.data)}
    </>
  )
}

export function NoRecords({
  title = "No hay registros en esta consulta",
  description = "Prueba otra búsqueda o revisa la disponibilidad de las fuentes.",
}: {
  title?: string
  description?: string
}) {
  return (
    <Empty className="py-12">
      <EmptyHeader>
        <EmptyMedia variant="icon">
          <Boxes />
        </EmptyMedia>
        <EmptyTitle>{title}</EmptyTitle>
        <EmptyDescription>{description}</EmptyDescription>
      </EmptyHeader>
      <EmptyContent>
        <Button
          variant="outline"
          render={<Link to="/fuentes" search={true} />}
          nativeButton={false}
        >
          Revisar fuentes
          <ArrowUpRight data-icon="inline-end" />
        </Button>
      </EmptyContent>
    </Empty>
  )
}

export function StatusBadge({
  status,
  stopped = false,
}: {
  status: string | null
  stopped?: boolean
}) {
  return (
    <Badge variant={stopped ? "destructive" : status ? "secondary" : "outline"}>
      {originalState(status)}
    </Badge>
  )
}

export function EquipmentLink({
  equipment,
  children,
}: {
  equipment: Equipment
  children?: ReactNode
}) {
  return (
    <Link
      to="/maquinaria/$equipmentId"
      params={{ equipmentId: equipment.id }}
      search={true}
      className="equipment-link"
    >
      {children ?? equipmentLabel(equipment)}
      <ArrowUpRight className="size-3.5" />
    </Link>
  )
}

export function EquipmentTable({
  equipment,
  compact = false,
}: {
  equipment: Equipment[]
  compact?: boolean
}) {
  if (equipment.length === 0) return <NoRecords />
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Equipo</TableHead>
          <TableHead>Estado del equipo</TableHead>
          {compact ? null : <TableHead>Proyecto</TableHead>}
          <TableHead>Traslados vinculados</TableHead>
          {compact ? null : <TableHead>Relación entre fuentes</TableHead>}
        </TableRow>
      </TableHeader>
      <TableBody>
        {equipment.map((item) => (
          <TableRow key={item.id}>
            <TableCell>
              <div className="equipment-cell">
                <span className="equipment-symbol">
                  <Boxes className="size-4" />
                </span>
                <div>
                  <EquipmentLink equipment={item} />
                  <span className="cell-description">{item.name}</span>
                </div>
              </div>
            </TableCell>
            <TableCell>
              <StatusBadge
                status={item.machinery_status}
                stopped={item.maintenance_is_stopped === true}
              />
              <span className="cell-description">Prisma / Nexus</span>
            </TableCell>
            {compact ? null : (
              <TableCell>
                <span>{item.project_name ?? "Sin proyecto vinculado"}</span>
                <span className="cell-description">
                  {item.project_id ?? "—"}
                </span>
              </TableCell>
            )}
            <TableCell>
              {item.transfers.length ? (
                <div className="transfer-badges">
                  {item.transfers.map((transfer) => (
                    <div key={transfer.id}>
                      <StatusBadge status={transfer.status} />
                      <span className="cell-description">
                        {transfer.code} · Startrack
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <span className="missing-value">Sin vínculo confirmado</span>
              )}
            </TableCell>
            {compact ? null : (
              <TableCell>
                <span className="relation-label">
                  <Link2 className="size-3.5" />
                  {relationLabels[item.relation_status]}
                </span>
              </TableCell>
            )}
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}

export function EquipmentPanel({
  hub,
  compact = false,
}: {
  hub: Hub
  compact?: boolean
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Maquinaria en contexto</CardTitle>
        <CardDescription>
          El estado administrativo y el traslado se consultan por separado.
        </CardDescription>
        {compact ? (
          <CardAction>
            <Button
              variant="ghost"
              size="sm"
              render={
                <Link
                  to="/maquinaria"
                  search={(previous) => ({ ...previous, filter: "all" })}
                />
              }
              nativeButton={false}
            >
              Ver toda
              <ArrowUpRight data-icon="inline-end" />
            </Button>
          </CardAction>
        ) : null}
      </CardHeader>
      <CardContent className="px-0">
        <EquipmentTable equipment={hub.equipment} compact={compact} />
      </CardContent>
      <CardFooter>
        <p className="footnote">
          {hub.scope.equipment_returned} equipos en esta consulta ·{" "}
          {hub.mode === "fixture"
            ? "Escenarios sintéticos"
            : "Lectura del sandbox"}
        </p>
      </CardFooter>
    </Card>
  )
}

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
    <article className="attention-item">
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

export function ProvenanceBlock({ provenance }: { provenance: Provenance }) {
  return (
    <dl className="provenance-grid">
      <div>
        <dt>Fuente</dt>
        <dd>
          {provenance.source === "nexus" ? "Prisma / Nexus" : "Startrack"}
        </dd>
      </div>
      <div>
        <dt>Entorno</dt>
        <dd>
          {provenance.environment === "local"
            ? "Local · ejemplo sintético"
            : "Sandbox"}
        </dd>
      </div>
      <div>
        <dt>ID en la fuente</dt>
        <dd className="mono break-all">{provenance.source_id}</dd>
      </div>
      <div>
        <dt>Fecha de lectura</dt>
        <dd>{formatInstant(provenance.observed_at)} · UTC−6</dd>
      </div>
    </dl>
  )
}

export function SourceCard({ source }: { source: Source }) {
  return (
    <Card>
      <CardHeader>
        <div className="source-card-brand">
          <span className="equipment-symbol">
            {source.id === "nexus" ? (
              <Database className="size-5" />
            ) : (
              <Cable className="size-5" />
            )}
          </span>
          <div>
            <CardTitle>
              {source.id === "nexus" ? "Prisma / Nexus" : "Startrack"}
            </CardTitle>
            <CardDescription>
              {source.id === "nexus"
                ? "Información administrativa"
                : "Traslados y seguimiento"}
            </CardDescription>
          </div>
        </div>
        <CardAction>
          <Badge
            variant={source.status === "error" ? "destructive" : "outline"}
          >
            {sourceLabels[source.status]}
          </Badge>
        </CardAction>
      </CardHeader>
      <CardContent>
        <p className="source-description">{source.message}</p>
        <div className="source-capabilities">
          {(source.id === "nexus"
            ? ["Maquinaria", "Solicitudes", "Mantenimiento"]
            : ["Tareas", "Motoristas", "Ubicaciones"]
          ).map((item) => (
            <Badge key={item} variant="secondary">
              {item}
            </Badge>
          ))}
        </div>
      </CardContent>
      <CardFooter className="justify-between gap-3">
        <span className="footnote">
          Entorno: {source.environment === "local" ? "local" : "sandbox"}
        </span>
        <span className="footnote icon-line">
          <Clock3 className="size-3.5" />
          {formatInstant(source.observed_at)}
        </span>
      </CardFooter>
    </Card>
  )
}
