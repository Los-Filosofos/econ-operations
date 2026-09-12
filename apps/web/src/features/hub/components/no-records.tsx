import { Link } from "@tanstack/react-router"
import { ArrowUpRight, Boxes } from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  Empty,
  EmptyContent,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "@/components/ui/empty"

export function NoRecords({
  title = "No hay registros en esta consulta",
  description = "Prueba otra búsqueda o revisa la disponibilidad de las fuentes.",
}: {
  title?: string
  description?: string
}) {
  return (
    <Empty className="py-12">
      <EmptyHeader>
        <EmptyMedia variant="icon">
          <Boxes />
        </EmptyMedia>
        <EmptyTitle>{title}</EmptyTitle>
        <EmptyDescription>{description}</EmptyDescription>
      </EmptyHeader>
      <EmptyContent>
        <Button
          variant="outline"
          render={<Link to="/fuentes" search={true} />}
          nativeButton={false}
        >
          Revisar fuentes
          <ArrowUpRight data-icon="inline-end" />
        </Button>
      </EmptyContent>
    </Empty>
  )
}
