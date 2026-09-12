import { useNavigate, useSearch } from "@tanstack/react-router"
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"
import { EquipmentPanel } from "../components/equipment-table"
import { HubBoundary } from "../components/hub-boundary"
import { PageHeading } from "../components/page-heading"
import { filterEquipment } from "../selectors"
import type { Hub } from "../schema"

function EquipmentData({ hub }: { hub: Hub }) {
  const { filter, mode, q } = useSearch({ from: "/maquinaria/" })
  const navigate = useNavigate({ from: "/maquinaria/" })
  const equipment = filterEquipment(hub.equipment, filter)
  return (
    <>
      <div className="filter-toolbar">
        <ToggleGroup
          value={[filter]}
          onValueChange={(value) => {
            const next = value[0]
            if (
              next === "all" ||
              next === "available" ||
              next === "unlinked" ||
              next === "failure"
            )
              void navigate({ search: { mode, q, filter: next } })
          }}
          variant="outline"
          spacing={0}
          aria-label="Filtrar maquinaria"
        >
          <ToggleGroupItem value="all">Toda la maquinaria</ToggleGroupItem>
          <ToggleGroupItem value="available">Disponible</ToggleGroupItem>
          <ToggleGroupItem value="unlinked">
            Vínculo por revisar
          </ToggleGroupItem>
          <ToggleGroupItem value="failure">Con falla activa</ToggleGroupItem>
        </ToggleGroup>
        <span>{equipment.length} equipos visibles</span>
      </div>
      <EquipmentPanel equipment={equipment} mode={hub.mode} />
    </>
  )
}

export function EquipmentPage() {
  return (
    <>
      <PageHeading
        eyebrow="02 / CONSULTA UNIFICADA"
        title="Maquinaria"
        description="Selecciona un equipo para conocer su operación y revisar la evidencia."
      />
      <HubBoundary>{(hub) => <EquipmentData hub={hub} />}</HubBoundary>
    </>
  )
}
