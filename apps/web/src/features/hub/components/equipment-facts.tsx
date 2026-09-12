import { Badge } from "@/components/ui/badge"
import {
  Card,
  CardAction,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Boxes, MapPin, Wrench } from "lucide-react"
import { StatusBadge } from "./status-badge"
import { formatInstant } from "../format"
import type { Equipment } from "../schema"

export function EquipmentFacts({ equipment }: { equipment: Equipment }) {
  return (
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
          <StatusBadge status={equipment.machinery_status} />
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
              <dt>Clave logística</dt>
              <dd>{equipment.code ?? "Sin clave"}</dd>
            </div>
            <div>
              <dt>Número de activo contable</dt>
              <dd>{equipment.asset_number ?? "Sin número de activo"}</dd>
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
  )
}
