import type { ReactNode } from "react"
import { CircleAlert, RefreshCw, Unplug } from "lucide-react"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import {
  Empty,
  EmptyContent,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "@/components/ui/empty"
import { Skeleton } from "@/components/ui/skeleton"
import { useHub } from "../queries"
import type { Hub } from "../schema"

export function HubBoundary({
  children,
}: {
  children: (hub: Hub) => ReactNode
}) {
  const query = useHub()
  if (query.isPending)
    return (
      <div
        className="loading-state"
        role="status"
        aria-label="Consultando información"
      >
        <div className="metric-grid">
          {[1, 2, 3, 4].map((item) => (
            <Skeleton key={item} className="h-36" />
          ))}
        </div>
        <Skeleton className="h-80 w-full" />
        <span className="sr-only">Consultando información del hub…</span>
      </div>
    )
  if (query.isError)
    return (
      <Empty className="empty-panel">
        <EmptyHeader>
          <EmptyMedia variant="icon">
            <Unplug />
          </EmptyMedia>
          <EmptyTitle>No pudimos consultar la operación</EmptyTitle>
          <EmptyDescription>{query.error.message}</EmptyDescription>
        </EmptyHeader>
        <EmptyContent>
          <Button
            onClick={() => void query.refetch()}
            disabled={query.isFetching}
          >
            <RefreshCw data-icon="inline-start" />
            Reintentar consulta
          </Button>
        </EmptyContent>
      </Empty>
    )
  return (
    <>
      {query.data.scope.complete ? null : (
        <Alert className="mb-6">
          <CircleAlert />
          <AlertTitle>La consulta tiene información incompleta</AlertTitle>
          <AlertDescription>
            {query.data.scope.description} Las cifras describen únicamente el
            alcance consultado.
          </AlertDescription>
        </Alert>
      )}
      {children(query.data)}
    </>
  )
}
