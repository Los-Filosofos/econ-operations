import { ClipboardList, Route } from "lucide-react"
import {
  Card,
  CardAction,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { NoRecords } from "./no-records"
import { StatusBadge } from "./status-badge"
import { ProvenanceBlock } from "./provenance-block"
import type { Equipment, Hub } from "../schema"

export function RelatedRecords({
  equipment,
  requests,
}: {
  equipment: Equipment
  requests: Hub["requests"]
}) {
  return (
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
                  <details className="evidence-disclosure">
                    <summary>Procedencia de la solicitud</summary>
                    <ProvenanceBlock provenance={request.provenance} />
                  </details>
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
  )
}
