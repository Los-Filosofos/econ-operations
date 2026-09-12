import { useState, type FormEvent } from "react"
import {
  Link,
  Outlet,
  useLocation,
  useNavigate,
  useSearch,
} from "@tanstack/react-router"
import {
  Activity,
  ArrowUpRight,
  Bell,
  Boxes,
  Cable,
  ChevronRight,
  ClipboardList,
  FlaskConical,
  LayoutDashboard,
  RefreshCw,
  Route,
  Search,
  ShieldCheck,
} from "lucide-react"

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Field, FieldGroup, FieldLabel } from "@/components/ui/field"
import {
  InputGroup,
  InputGroupAddon,
  InputGroupButton,
  InputGroupInput,
} from "@/components/ui/input-group"
import { Separator } from "@/components/ui/separator"
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarInset,
  SidebarMenu,
  SidebarMenuBadge,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarProvider,
  SidebarTrigger,
  useSidebar,
} from "@/components/ui/sidebar"
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"
import { useHub } from "@/features/hub/api"
import { formatInstant, sourceLabels } from "@/features/hub/format"
import { cn } from "@/lib/utils"

const navigation = [
  { to: "/", title: "Vista general", icon: LayoutDashboard },
  { to: "/maquinaria", title: "Maquinaria", icon: Boxes },
  { to: "/solicitudes", title: "Solicitudes", icon: ClipboardList },
  { to: "/traslados", title: "Traslados", icon: Route },
  { to: "/alertas", title: "Centro de atención", icon: Bell },
] as const

function WorkspaceSidebar() {
  const { pathname } = useLocation()
  const { setOpenMobile } = useSidebar()
  const query = useHub()
  const data = query.isError ? undefined : query.data
  return (
    <Sidebar>
      <SidebarHeader className="px-5 py-7">
        <Link
          to="/"
          search={true}
          className="brand"
          aria-label="ECON · Vista general"
          onClick={() => setOpenMobile(false)}
        >
          <span className="brand-mark" aria-hidden="true">
            <span />
            <span />
            <span />
          </span>
          <span>
            ECON<span className="brand-subtitle">HUB DE OPERACIONES</span>
          </span>
        </Link>
      </SidebarHeader>
      <SidebarContent>
        <SidebarGroup className="px-3">
          <SidebarGroupLabel>ESPACIO DE TRABAJO</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu className="gap-1">
              {navigation.map(({ to, title, icon: Icon }) => (
                <SidebarMenuItem key={to}>
                  <SidebarMenuButton
                    className="h-10 px-3"
                    isActive={
                      to === "/" ? pathname === "/" : pathname.startsWith(to)
                    }
                    render={
                      <Link
                        to={to}
                        search={true}
                        onClick={() => setOpenMobile(false)}
                      />
                    }
                  >
                    <Icon />
                    <span>{title}</span>
                  </SidebarMenuButton>
                  {to === "/alertas" && data?.summary.alerts_count != null ? (
                    <SidebarMenuBadge>
                      {data.summary.alerts_count}
                    </SidebarMenuBadge>
                  ) : null}
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
        <SidebarGroup className="mt-7 px-3">
          <SidebarGroupLabel>INTEGRACIÓN</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              <SidebarMenuItem>
                <SidebarMenuButton
                  className="h-10 px-3"
                  isActive={pathname === "/fuentes"}
                  render={
                    <Link
                      to="/fuentes"
                      search={true}
                      onClick={() => setOpenMobile(false)}
                    />
                  }
                >
                  <Cable />
                  <span>Fuentes y trazabilidad</span>
                </SidebarMenuButton>
              </SidebarMenuItem>
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
        <div className="sidebar-context">
          <span className="eyebrow">UNA OPERACIÓN · DOS FUENTES</span>
          <div className="source-pair">
            <span>Prisma</span>
            <span aria-hidden="true">+</span>
            <span>Startrack</span>
          </div>
          <p>La información conserva su origen y su significado.</p>
          <Link to="/fuentes" search={true} className="text-link">
            Ver conexión <ArrowUpRight className="size-3.5" />
          </Link>
        </div>
      </SidebarContent>
      <SidebarFooter className="p-5">
        <Separator className="mb-3" />
        <div className="workspace-team">
          <span className="team-symbol">06</span>
          <div>
            <strong>Los Filósofos</strong>
            <span>Grupo ECON · Equipo 6</span>
          </div>
        </div>
        <p className="readonly-label">
          <ShieldCheck className="size-3.5" /> Espacio de consulta
        </p>
      </SidebarFooter>
    </Sidebar>
  )
}

function WorkspaceSearch({ initialValue }: { initialValue: string }) {
  const [value, setValue] = useState(initialValue)
  const { mode } = useSearch({ from: "__root__" })
  const navigate = useNavigate()
  function submit(event: FormEvent) {
    event.preventDefault()
    void navigate({ to: ".", search: { mode, q: value.trim() } })
  }
  return (
    <form onSubmit={submit} className="workspace-search" role="search">
      <FieldGroup>
        <Field>
          <FieldLabel htmlFor="hub-search" className="sr-only">
            Buscar equipo o proyecto
          </FieldLabel>
          <InputGroup>
            <InputGroupInput
              id="hub-search"
              placeholder="Buscar equipo o proyecto…"
              value={value}
              onChange={(event) => setValue(event.target.value)}
              maxLength={100}
            />
            <InputGroupAddon>
              <Search />
            </InputGroupAddon>
            <InputGroupAddon align="inline-end">
              <InputGroupButton
                type="submit"
                size="icon-xs"
                aria-label="Buscar"
              >
                <ChevronRight />
              </InputGroupButton>
            </InputGroupAddon>
          </InputGroup>
        </Field>
      </FieldGroup>
    </form>
  )
}

export function AppShell() {
  const { mode, q } = useSearch({ from: "__root__" })
  const navigate = useNavigate()
  const query = useHub()
  const data = query.isError ? undefined : query.data
  return (
    <SidebarProvider
      style={{ "--sidebar-width": "15.5rem" } as React.CSSProperties}
    >
      <a href="#main-content" className="skip-link">
        Saltar al contenido
      </a>
      <WorkspaceSidebar />
      <SidebarInset className="min-w-0">
        <header className="workspace-header">
          <div className="header-left">
            <SidebarTrigger aria-label="Abrir o cerrar navegación" />
            <Separator orientation="vertical" className="h-4" />
            <span className="header-breadcrumb">
              Operaciones <ChevronRight className="size-3" />
              <strong>Hub central</strong>
            </span>
          </div>
          <WorkspaceSearch key={q} initialValue={q} />
          <Badge variant="outline">Solo lectura</Badge>
        </header>
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
                  void navigate({ to: ".", search: { mode: next, q } })
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
        <div id="main-content" tabIndex={-1} className="page-container">
          {mode === "fixture" ? (
            <Alert className="mb-6" role="status">
              <FlaskConical />
              <AlertTitle>Estás explorando ejemplos locales</AlertTitle>
              <AlertDescription>
                Los casos y ubicaciones son sintéticos. Permiten revisar el
                funcionamiento del hub.
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
                  void navigate({ to: ".", search: { mode, q: "" } })
                }
              >
                Limpiar búsqueda
              </Button>
            </div>
          ) : null}
          <Outlet />
          <footer className="page-footer">
            <span>ECON · Información con contexto</span>
            <span>
              {data
                ? `Consulta: ${formatInstant(data.generated_at)} · El Salvador (UTC−6)`
                : "Esperando una lectura válida"}
            </span>
          </footer>
        </div>
        <div className="source-bottomline" aria-label="Estado de fuentes">
          {data?.sources.map((source) => (
            <span key={source.id}>
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
            </span>
          ))}
        </div>
      </SidebarInset>
    </SidebarProvider>
  )
}
