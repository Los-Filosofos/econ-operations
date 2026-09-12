import { Link, useNavigate, useSearch } from "@tanstack/react-router"
import { Activity, FlaskConical, RefreshCw } from "lucide-react"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"
import { useHub } from "@/features/hub/queries"
import { formatInstant, sourceLabels } from "@/features/hub/format"
import { cn } from "@/lib/utils"

export function SourceToolbar() {
  const { mode } = useSearch({ from: "__root__" })
  const navigate = useNavigate()
  const query = useHub()
  return (
    <div className="source-toolbar">
      <div className="source-mode">
        <span>Origen de datos</span>
        <ToggleGroup
          aria-label="Origen de los datos"
          size="sm"
          variant="outline"
          spacing={0}
          value={[mode]}
          onValueChange={(values) => {
            const next = values[0]
            if (next === "live" || next === "fixture")
              void navigate({
                to: ".",
                search: (previous) => ({ ...previous, mode: next }),
              })
          }}
        >
          <ToggleGroupItem value="fixture">
            <FlaskConical /> Ejemplos locales
          </ToggleGroupItem>
          <ToggleGroupItem value="live">
            <Activity /> Sandbox en vivo
          </ToggleGroupItem>
        </ToggleGroup>
      </div>
      <Button
        variant="ghost"
        size="sm"
        disabled={query.isFetching}
        onClick={() => void query.refetch()}
      >
        <RefreshCw
          data-icon="inline-start"
          className={cn(query.isFetching && "animate-spin")}
        />
        {query.isFetching ? "Consultando…" : "Actualizar"}
      </Button>
    </div>
  )
}

export function QueryContext() {
  const { mode, q } = useSearch({ from: "__root__" })
  const navigate = useNavigate()
  return (
    <>
      {mode === "fixture" ? (
        <Alert className="fixture-notice" role="status">
          <FlaskConical />
          <AlertTitle>Demostración local</AlertTitle>
          <AlertDescription>
            Casos, IDs y ubicaciones sintéticos para explorar la operación.
          </AlertDescription>
        </Alert>
      ) : null}
      {q ? (
        <div className="search-scope">
          <span>
            Resultados para <strong>“{q}”</strong>
          </span>
          <Button
            size="sm"
            variant="ghost"
            onClick={() =>
              void navigate({
                to: ".",
                search: (previous) => ({ ...previous, q: "" }),
              })
            }
          >
            Limpiar búsqueda
          </Button>
        </div>
      ) : null}
    </>
  )
}

export function WorkspaceFooter() {
  const query = useHub()
  const data = query.isError ? undefined : query.data
  return (
    <footer className="workspace-footer">
      <div className="page-footer">
        <span>
          GRUPO ECON <span className="footer-divider">/</span> CONTROL DE
          OPERACIONES
        </span>
        <span>
          {data
            ? `Lectura: ${formatInstant(data.generated_at)} · El Salvador (UTC−6)`
            : "Esperando una lectura válida"}
        </span>
      </div>
      <div className="source-bottomline" aria-label="Estado de fuentes">
        {data?.sources.map((source) => (
          <Link key={source.id} to="/fuentes" search={true}>
            <span
              className={cn(
                "status-dot",
                source.status === "error" && "status-dot-error"
              )}
            />
            <strong>
              {source.id === "nexus" ? "Prisma / Nexus" : "Startrack"}
            </strong>
            {sourceLabels[source.status]}
          </Link>
        ))}
      </div>
    </footer>
  )
}
