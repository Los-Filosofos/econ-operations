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
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { EquipmentLink } from "./equipment-link"
import { NoRecords } from "./no-records"
import { StatusBadge } from "./status-badge"
import { relationLabels } from "../format"
import { selectOperations } from "../selectors"
import type { Hub } from "../schema"

export function OperationLedger({ hub }: { hub: Hub }) {
  const operations = selectOperations(hub)
  return (
    <Card className="operation-ledger">
      <CardHeader>
        <CardTitle>Seguimiento de la operación</CardTitle>
        <CardDescription>
          De la necesidad del proyecto a la evidencia del traslado.
        </CardDescription>
        <CardAction>
          <Button
            variant="ghost"
            size="sm"
            render={<Link to="/solicitudes" search={true} />}
            nativeButton={false}
          >
            Solicitudes <ArrowUpRight data-icon="inline-end" />
          </Button>
        </CardAction>
      </CardHeader>
      <CardContent className="px-0">
        {operations.length ? (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>
                  <span className="column-step">01</span> Proyecto / solicitud
                </TableHead>
                <TableHead>
                  <span className="column-step">02</span> Unidad asignada
                </TableHead>
                <TableHead>
                  <span className="column-step">03</span> Tarea de traslado
                </TableHead>
                <TableHead>
                  <span className="column-step">04</span> Evidencia
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {operations.map(({ request, equipment, transfers }) => (
                <TableRow key={request.id}>
                  <TableCell>
                    <strong>
                      {request.project_name ?? "Proyecto sin confirmar"}
                    </strong>
                    <span className="cell-description mono">
                      {request.project_id ?? "Sin código"}
                    </span>
                    <span className="cell-description record-id">
                      {request.id}
                    </span>
                    <StatusBadge status={request.status} />
                  </TableCell>
                  <TableCell>
                    {equipment ? (
                      <>
                        <EquipmentLink equipment={equipment} />
                        <span className="cell-description">
                          {equipment.name}
                        </span>
                        <StatusBadge status={equipment.machinery_status} />
                      </>
                    ) : (
                      <span className="missing-value">
                        {request.machinery_id
                          ? "Fuera de esta consulta"
                          : "Sin unidad vinculada"}
                      </span>
                    )}
                  </TableCell>
                  <TableCell>
                    {transfers.length ? (
                      <div className="transfer-badges">
                        {transfers.map((transfer) => (
                          <div key={transfer.id}>
                            <strong className="mono">{transfer.code}</strong>
                            <span className="cell-description">
                              <StatusBadge status={transfer.status} />
                            </span>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <span className="missing-value">Sin tarea vinculada</span>
                    )}
                  </TableCell>
                  <TableCell>
                    <Badge
                      variant={
                        transfers.length > 0 &&
                        equipment?.relation_status === "confirmed"
                          ? "secondary"
                          : "outline"
                      }
                    >
                      {!equipment
                        ? "Asignación por revisar"
                        : transfers.length === 0
                          ? "Traslado por vincular"
                          : relationLabels[equipment.relation_status]}
                    </Badge>
                    <span className="cell-description">
                      {transfers.length
                        ? "Recepción física sin evidencia en el hub"
                        : "Falta el vínculo solicitud–traslado"}
                    </span>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        ) : (
          <NoRecords
            title="Sin solicitudes en esta lectura"
            description="Consulta maquinaria y fuentes para revisar qué parte de la operación está disponible."
          />
        )}
      </CardContent>
      <CardFooter>
        <p className="footnote">
          {operations.length} solicitudes en el alcance · La asignación, el
          cierre de la tarea y la recepción describen hechos distintos.
        </p>
      </CardFooter>
    </Card>
  )
}
