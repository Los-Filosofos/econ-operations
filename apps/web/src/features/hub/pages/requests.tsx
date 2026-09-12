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

export function RequestsPage() {
  return (
    <>
      <PageHeading
        eyebrow="03 / PLANIFICACIÓN DE EQUIPOS"
        title="Solicitudes"
        description="Revisa el estado administrativo, el inicio previsto y la maquinaria vinculada."
      />
      <HubBoundary>
        {(hub) => (
          <Card>
            <CardHeader>
              <CardTitle>Solicitudes de maquinaria</CardTitle>
              <CardDescription>
                Una solicitud aprobada requiere revisar también su unidad
                vinculada.
              </CardDescription>
            </CardHeader>
            <CardContent className="px-0">
              {hub.requests.length ? (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Solicitud</TableHead>
                      <TableHead>Proyecto</TableHead>
                      <TableHead>Estado</TableHead>
                      <TableHead>Equipo vinculado</TableHead>
                      <TableHead>Fecha de inicio</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {hub.requests.map((request) => {
                      const equipment = hub.equipment.find(
                        (item) => item.id === request.machinery_id
                      )
                      return (
                        <TableRow key={request.id}>
                          <TableCell>
                            <span className="record-id">{request.id}</span>
                            <span className="cell-description">
                              Prisma / Nexus
                            </span>
                          </TableCell>
                          <TableCell>
                            {request.project_name ?? "Sin proyecto"}
                            <span className="cell-description">
                              {request.project_id ?? "—"}
                            </span>
                          </TableCell>
                          <TableCell>
                            <StatusBadge status={request.status} />
                          </TableCell>
                          <TableCell>
                            {equipment ? (
                              <EquipmentLink equipment={equipment} />
                            ) : (
                              <span className="missing-value">
                                {request.machinery_id
                                  ? "Equipo fuera de esta consulta"
                                  : "Sin unidad vinculada"}
                              </span>
                            )}
                          </TableCell>
                          <TableCell>
                            {request.starts_on ?? "Sin fecha registrada"}
                          </TableCell>
                        </TableRow>
                      )
                    })}
                  </TableBody>
                </Table>
              ) : (
                <NoRecords title="No hay solicitudes en esta consulta" />
              )}
            </CardContent>
          </Card>
        )}
      </HubBoundary>
    </>
  )
}
