import { createRootRoute, Link } from "@tanstack/react-router"
import { AppShell } from "@/components/app-shell"
import { Button } from "@/components/ui/button"
import {
  Empty,
  EmptyContent,
  EmptyDescription,
  EmptyHeader,
  EmptyTitle,
} from "@/components/ui/empty"
import { hubSearchSchema } from "@/features/hub/schema"

export const Route = createRootRoute({
  validateSearch: hubSearchSchema,
  component: AppShell,
  errorComponent: () => (
    <Empty className="py-20">
      <EmptyHeader>
        <EmptyTitle>No pudimos abrir esta consulta</EmptyTitle>
        <EmptyDescription>
          Comprueba que el origen sea fixture o live y que la búsqueda tenga
          como máximo 100 caracteres.
        </EmptyDescription>
      </EmptyHeader>
      <EmptyContent>
        <Button render={<a href="/" />} nativeButton={false}>
          Abrir ejemplos locales
        </Button>
      </EmptyContent>
    </Empty>
  ),
  notFoundComponent: () => (
    <Empty className="py-20">
      <EmptyHeader>
        <EmptyTitle>Esta página no existe</EmptyTitle>
        <EmptyDescription>
          Vuelve a la vista general para consultar la operación.
        </EmptyDescription>
      </EmptyHeader>
      <EmptyContent>
        <Button
          render={<Link to="/" search={true} />}
          nativeButton={false}
        >
          Ir a vista general
        </Button>
      </EmptyContent>
    </Empty>
  ),
})
