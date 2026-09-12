import { Link, useLocation } from "@tanstack/react-router"
import { ArrowUpRight, Eye } from "lucide-react"
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuBadge,
  SidebarMenuButton,
  SidebarMenuItem,
  useSidebar,
} from "@/components/ui/sidebar"
import { Separator } from "@/components/ui/separator"
import { useHub } from "@/features/hub/queries"
import { navigation } from "./navigation"

export function WorkspaceSidebar() {
  const { pathname } = useLocation()
  const { setOpenMobile } = useSidebar()
  const query = useHub()
  const alertsCount = query.isError ? null : query.data?.summary.alerts_count
  return (
    <Sidebar className="econ-sidebar">
      <SidebarHeader className="brand-header">
        <Link
          to="/"
          search={true}
          className="brand"
          aria-label="ECON · Vista general"
          onClick={() => setOpenMobile(false)}
        >
          <img
            src="/brand/econ-white.png"
            alt="Grupo ECON"
            width="148"
            height="67"
          />
        </Link>
        <span className="brand-subtitle">CONTROL DE OPERACIONES</span>
      </SidebarHeader>
      <SidebarContent>
        <SidebarGroup className="px-0">
          <SidebarGroupLabel>CONSULTA OPERATIVA</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu className="gap-0">
              {navigation.map(({ to, title, icon: Icon, index }) => (
                <SidebarMenuItem key={to}>
                  <SidebarMenuButton
                    className="workspace-nav-link"
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
                    <span className="nav-index">{index}</span>
                  </SidebarMenuButton>
                  {to === "/alertas" && alertsCount != null ? (
                    <SidebarMenuBadge>{alertsCount}</SidebarMenuBadge>
                  ) : null}
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
        <div className="sidebar-context">
          <span className="eyebrow">SISTEMAS DE ORIGEN</span>
          <div className="source-pair">
            <span>Prisma / Nexus</span>
            <span>Startrack</span>
          </div>
          <p>Administración y seguimiento, en una misma consulta.</p>
          <Link
            to="/fuentes"
            search={true}
            className="text-link"
            onClick={() => setOpenMobile(false)}
          >
            Revisar fuentes <ArrowUpRight className="size-3.5" />
          </Link>
        </div>
      </SidebarContent>
      <SidebarFooter className="workspace-sidebar-footer">
        <Separator />
        <p className="eyebrow">EQUIPO ASIGNADO EN EL KIT</p>
        <strong>Los Filósofos</strong>
        <span className="assignment-ids">RE-03 / MOT-006 / PROY-006</span>
        <p className="readonly-label">
          <Eye className="size-3.5" /> Espacio de consulta
        </p>
      </SidebarFooter>
    </Sidebar>
  )
}
