import type { Equipment, Hub } from "./schema"

export type EquipmentFilter = "all" | "available" | "unlinked" | "failure"

export function filterEquipment(
  equipment: Equipment[],
  filter: EquipmentFilter
) {
  return equipment.filter((item) => {
    switch (filter) {
      case "available":
        return item.machinery_status.toUpperCase() === "DISPONIBLE"
      case "unlinked":
        return item.relation_status !== "confirmed"
      case "failure":
        return item.maintenance_failure_id !== null
      default:
        return true
    }
  })
}

export function selectOperations(hub: Pick<Hub, "equipment" | "requests">) {
  const equipmentById = new Map(
    hub.equipment.map((equipment) => [equipment.id, equipment])
  )
  return hub.requests.map((request) => {
    const equipment = request.machinery_id
      ? equipmentById.get(request.machinery_id)
      : undefined
    return {
      request,
      equipment,
      transfers:
        equipment?.transfers.filter(
          (transfer) => transfer.request_id === request.id
        ) ?? [],
    }
  })
}
