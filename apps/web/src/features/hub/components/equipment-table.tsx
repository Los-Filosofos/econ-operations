import { Link } from "@tanstack/react-router"
import { ArrowUpRight, Boxes, Link2 } from "lucide-react"
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
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { relationLabels } from "../format"
import type { DataMode, Equipment } from "../schema"
import { EquipmentLink } from "./equipment-link"
import { StatusBadge } from "./status-badge"
import { NoRecords } from "./no-records"

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
          {compact ? null : <TableHead>Mantenimiento</TableHead>}
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
              <StatusBadge status={item.machinery_status} />
              <span className="cell-description">Prisma / Nexus</span>
            </TableCell>
            {compact ? null : (
              <TableCell>
                <StatusBadge
                  status={
                    item.maintenance_is_stopped === true
                      ? "Paro registrado"
                      : item.maintenance_is_stopped === false
                        ? "Sin paro registrado"
                        : null
                  }
                  stopped={item.maintenance_is_stopped === true}
                />
                <span className="cell-description">
                  {item.maintenance_failure_id
                    ? "Falla activa registrada"
                    : "Sin referencia de falla activa"}
                </span>
              </TableCell>
            )}
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
  equipment,
  mode,
  compact = false,
}: {
  equipment: Equipment[]
  mode: DataMode
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
        <EquipmentTable equipment={equipment} compact={compact} />
      </CardContent>
      <CardFooter>
        <p className="footnote">
          {equipment.length} equipos visibles ·{" "}
          {mode === "fixture" ? "Escenarios sintéticos" : "Lectura del sandbox"}
        </p>
      </CardFooter>
    </Card>
  )
}
