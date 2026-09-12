import type { ReactNode } from "react"
import { Link } from "@tanstack/react-router"
import { ArrowUpRight } from "lucide-react"
import { equipmentLabel } from "../format"
import type { Equipment } from "../schema"

export function EquipmentLink({
  equipment,
  children,
}: {
  equipment: Equipment
  children?: ReactNode
}) {
  return (
    <Link
      to="/maquinaria/$equipmentId"
      params={{ equipmentId: equipment.id }}
      search={true}
      className="equipment-link"
    >
      {children ?? equipmentLabel(equipment)}
      <ArrowUpRight className="size-3.5" />
    </Link>
  )
}
