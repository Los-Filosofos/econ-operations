import { Route } from "lucide-react"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import {
  Card,
  CardContent,
  CardDescription,
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
import { EquipmentLink } from "../components/equipment-link"
import { HubBoundary } from "../components/hub-boundary"
import { NoRecords } from "../components/no-records"
import { PageHeading } from "../components/page-heading"
import { StatusBadge } from "../components/status-badge"
import { formatInstant, relationLabels } from "../format"

export function TransfersPage() {
  return (
    <>
      <PageHeading
        eyebrow="04 / COORDINACIÓN LOGÍSTICA"
        title="Traslados"
        description="Tareas relacionadas con la maquinaria del alcance consultado."
      />
      <HubBoundary>
        {(hub) => {
          const transfers = hub.equipment.flatMap((equipment) =>
            equipment.transfers.map((transfer) => ({ equipment, transfer }))
          )
          return (
            <>
              <Alert className="mb-6" role="note">
                <Route />
                <AlertTitle>
                  El cierre de la tarea no confirma recepción física
                </AlertTitle>
                <AlertDescription>
                  La llegada y la aceptación en el proyecto necesitan evidencia
                  propia. Una geocerca tampoco confirma por sí sola la entrega.
                </AlertDescription>
              </Alert>
              <Card>
                <CardHeader>
                  <CardTitle>Tareas de traslado</CardTitle>
                  <CardDescription>
                    {transfers.length} tareas vinculadas a los equipos de esta
                    consulta. Un equipo puede tener varios traslados.
                  </CardDescription>
                </CardHeader>
                <CardContent className="px-0">
                  {transfers.length ? (
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Tarea</TableHead>
                          <TableHead>Equipo</TableHead>
                          <TableHead>Estado de tarea</TableHead>
                          <TableHead>Destino y motorista</TableHead>
                          <TableHead>Vinculación</TableHead>
                          <TableHead>Lectura de la fuente</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {transfers.map(({ equipment, transfer }) => (
                          <TableRow key={`${equipment.id}-${transfer.id}`}>
                            <TableCell>
                              <strong>{transfer.code}</strong>
                              <span className="cell-description">
                                Startrack
                              </span>
                            </TableCell>
                            <TableCell>
                              <EquipmentLink equipment={equipment} />
                            </TableCell>
                            <TableCell>
                              <StatusBadge status={transfer.status} />
                            </TableCell>
                            <TableCell>
                              {transfer.destination_project_name ??
                                "Destino sin confirmar"}
                              <span className="cell-description">
                                {transfer.driver ?? "Motorista sin confirmar"}
                              </span>
                            </TableCell>
                            <TableCell>
                              {relationLabels[equipment.relation_status]}
                            </TableCell>
                            <TableCell>
                              {formatInstant(transfer.provenance.observed_at)}
                              <span className="cell-description">
                                {transfer.provenance.environment === "local"
                                  ? "Ejemplo sintético"
                                  : "Sandbox"}
                              </span>
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  ) : (
                    <NoRecords
                      title="No hay traslados vinculados en esta consulta"
                      description="La ausencia de un vínculo no demuestra que no exista una tarea en Startrack."
                    />
                  )}
                </CardContent>
              </Card>
            </>
          )
        }}
      </HubBoundary>
    </>
  )
}
