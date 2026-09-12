import { Link } from "@tanstack/react-router"
import { ArrowLeft, Link2 } from "lucide-react"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Separator } from "@/components/ui/separator"
import { AlertItem } from "../components/alert-item"
import { EquipmentFacts } from "../components/equipment-facts"
import { RelatedRecords } from "../components/related-records"
import { HubBoundary } from "../components/hub-boundary"
import { NoRecords } from "../components/no-records"
import { PageHeading } from "../components/page-heading"
import { ProvenanceBlock } from "../components/provenance-block"
import { equipmentLabel, relationLabels } from "../format"
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
      <EquipmentFacts equipment={equipment} />
      <RelatedRecords equipment={equipment} requests={requests} />
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
      <Card className="mt-6">
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
