import { Link } from "@tanstack/react-router"
import {
  ArrowLeft,
  Boxes,
  ClipboardList,
  Link2,
  MapPin,
  Route,
  Wrench,
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
import { Separator } from "@/components/ui/separator"
import {
  AlertItem,
  HubBoundary,
  NoRecords,
  PageHeading,
  ProvenanceBlock,
  StatusBadge,
} from "../components"
import { equipmentLabel, formatInstant, relationLabels } from "../format"
import type { Equipment, Hub } from "../schema"

function EquipmentDetail({
  equipment,
  hub,
}: {
  equipment: Equipment
  hub: Hub
}) {
  const requests = hub.requests.filter((request) =>
    equipment.request_ids.includes(request.id)
  )
  const alerts = hub.alerts.filter(
    (alert) => alert.equipment_id === equipment.id
  )
  return (
    <>
      <PageHeading
        eyebrow="FICHA DE MAQUINARIA"
        title={`${equipmentLabel(equipment)} · ${equipment.name}`}
        description={
          equipment.company ??
          "Consulta de la operación y la evidencia del equipo."
        }
        action={
          <Badge variant="outline">
            {equipment.provenance.environment === "local"
              ? "Ejemplo local"
              : "Sandbox"}
          </Badge>
        }
      />
      <Alert className="mb-6" role="note">
        <Link2 />
        <AlertTitle>{relationLabels[equipment.relation_status]}</AlertTitle>
        <AlertDescription>{equipment.relation_note}</AlertDescription>
      </Alert>
      <div className="detail-top-grid">
        <Card>
          <CardHeader>
            <CardDescription>Estado del equipo</CardDescription>
            <CardTitle>Prisma / Nexus</CardTitle>
            <CardAction>
              <Boxes className="size-5" />
            </CardAction>
          </CardHeader>
          <CardContent>
            <StatusBadge
              status={equipment.machinery_status}
              stopped={equipment.maintenance_is_stopped === true}
            />
            <p className="detail-explanation">
              Describe su estado administrativo. No confirma ubicación, traslado
              ni recepción.
            </p>
            <dl className="detail-grid">
              <div>
                <dt>Proyecto vinculado</dt>
                <dd>{equipment.project_name ?? "Sin proyecto vinculado"}</dd>
              </div>
              <div>
                <dt>Código de proyecto</dt>
                <dd>{equipment.project_id ?? "Sin registro"}</dd>
              </div>
              <div>
                <dt>Motorista</dt>
                <dd>{equipment.driver ?? "Sin motorista confirmado"}</dd>
              </div>
            </dl>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardDescription>Condición registrada</CardDescription>
            <CardTitle>Mantenimiento</CardTitle>
            <CardAction>
              <Wrench className="size-5" />
            </CardAction>
          </CardHeader>
          <CardContent>
            <Badge
              variant={
                equipment.maintenance_is_stopped === true
                  ? "destructive"
                  : "outline"
              }
            >
              {equipment.maintenance_is_stopped === true
                ? "Paro registrado"
                : equipment.maintenance_is_stopped === false
                  ? "Sin paro registrado"
                  : "Paro sin confirmar"}
            </Badge>
            <p className="detail-explanation">
              {equipment.maintenance_failure_id
                ? (equipment.maintenance_status ??
                  "Falla activa registrada; detalle pendiente.")
                : "No se recibió una referencia de falla activa en esta consulta."}
            </p>
            <dl className="detail-grid">
              <div>
                <dt>Referencia de falla</dt>
                <dd className="break-all">
                  {equipment.maintenance_failure_id ?? "Sin referencia"}
                </dd>
              </div>
            </dl>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardDescription>Última observación</CardDescription>
            <CardTitle>Ubicación</CardTitle>
            <CardAction>
              <MapPin className="size-5" />
            </CardAction>
          </CardHeader>
          <CardContent>
            <p className="location-label">
              {equipment.location?.label ?? "Sin ubicación confirmada"}
            </p>
            <p className="detail-explanation">
              {equipment.location
                ? `${formatInstant(equipment.location.observed_at)} · El Salvador (UTC−6). Una lectura reciente del hub no implica una posición reciente.`
                : "Hace falta una observación fechada y la identificación del activo observado."}
            </p>
            {equipment.location ? (
              <Badge variant="outline">
                {equipment.location.provenance.environment === "local"
                  ? "Ubicación sintética"
                  : "Observación del sandbox"}
              </Badge>
            ) : null}
          </CardContent>
        </Card>
      </div>
      <div className="source-grid">
        <Card>
          <CardHeader>
            <CardTitle>Solicitudes relacionadas</CardTitle>
            <CardDescription>
              Registros vinculados por identificador.
            </CardDescription>
            <CardAction>
              <ClipboardList className="size-5" />
            </CardAction>
          </CardHeader>
          <CardContent>
            {requests.length ? (
              <div className="linked-records">
                {requests.map((request) => (
                  <div key={request.id}>
                    <div className="record-heading">
                      <strong className="break-all">{request.id}</strong>
                      <StatusBadge status={request.status} />
                    </div>
                    <p>{request.project_name ?? "Proyecto sin confirmar"}</p>
                    <span className="footnote">
                      Inicio previsto: {request.starts_on ?? "sin fecha"}
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <NoRecords
                title="Sin solicitud en el alcance consultado"
                description="Un registro faltante no confirma que la solicitud no exista en la fuente."
              />
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Traslados relacionados</CardTitle>
            <CardDescription>
              {equipment.transfers.length} tareas. El equipo puede conservar
              varios traslados.
            </CardDescription>
            <CardAction>
              <Route className="size-5" />
            </CardAction>
          </CardHeader>
          <CardContent>
            {equipment.transfers.length ? (
              <div className="linked-records">
                {equipment.transfers.map((transfer) => (
                  <div key={transfer.id}>
                    <div className="record-heading">
                      <strong>{transfer.code}</strong>
                      <StatusBadge status={transfer.status} />
                    </div>
                    <p>
                      {transfer.destination_project_name ??
                        "Destino sin confirmar"}
                    </p>
                    <span className="footnote">
                      {transfer.driver ?? "Motorista sin confirmar"}
                    </span>
                    <details className="evidence-disclosure">
                      <summary>Procedencia de la tarea</summary>
                      <ProvenanceBlock provenance={transfer.provenance} />
                    </details>
                  </div>
                ))}
              </div>
            ) : (
              <NoRecords
                title="Sin vínculo confirmado con un traslado"
                description="Para relacionar una tarea se necesita validar su referencia, equipo y destino."
              />
            )}
          </CardContent>
          <CardFooter>
            <p className="footnote">
              El estado de la tarea y el estado del equipo describen objetos
              diferentes.
            </p>
          </CardFooter>
        </Card>
      </div>
      {alerts.length ? (
        <Card>
          <CardHeader>
            <CardTitle>Atención para este equipo</CardTitle>
            <CardDescription>
              Revisa las condiciones y la evidencia de cada caso.
            </CardDescription>
          </CardHeader>
          <CardContent className="px-0">
            {alerts.map((alert) => (
              <AlertItem key={alert.id} alert={alert} hub={hub} expanded />
            ))}
          </CardContent>
        </Card>
      ) : null}
      <Card>
        <CardHeader>
          <CardTitle>Procedencia del registro</CardTitle>
          <CardDescription>
            Identidad y fecha preservadas desde la fuente.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <ProvenanceBlock provenance={equipment.provenance} />
          {equipment.location ? (
            <>
              <Separator className="my-5" />
              <h3 className="section-label">Procedencia de la ubicación</h3>
              <ProvenanceBlock provenance={equipment.location.provenance} />
            </>
          ) : null}
        </CardContent>
      </Card>
    </>
  )
}

export function EquipmentDetailPage({ equipmentId }: { equipmentId: string }) {
  return (
    <>
      <Button
        variant="ghost"
        className="mb-5"
        render={<Link to="/maquinaria" search={true} />}
        nativeButton={false}
      >
        <ArrowLeft data-icon="inline-start" />
        Volver a maquinaria
      </Button>
      <HubBoundary>
        {(hub) => {
          const equipment = hub.equipment.find(
            (item) => item.id === equipmentId
          )
          return equipment ? (
            <EquipmentDetail equipment={equipment} hub={hub} />
          ) : (
            <NoRecords
              title="Este equipo no está en la consulta actual"
              description="Comprueba el origen seleccionado y limpia la búsqueda para ampliar el alcance."
            />
          )
        }}
      </HubBoundary>
    </>
  )
}
