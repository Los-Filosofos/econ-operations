import { createFileRoute } from "@tanstack/react-router"
import { EquipmentDetailPage } from "@/features/hub/pages/equipment-detail"

export const Route = createFileRoute("/maquinaria/$equipmentId")({
  component: EquipmentDetailRoute,
})

export function EquipmentDetailRoute() {
  const { equipmentId } = Route.useParams()
  return <EquipmentDetailPage equipmentId={equipmentId} />
}
