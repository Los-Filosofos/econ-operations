import type { CSSProperties } from "react"
import { Outlet } from "@tanstack/react-router"
import { SidebarInset, SidebarProvider } from "@/components/ui/sidebar"
import { WorkspaceSidebar } from "@/components/layout/workspace-sidebar"
import { WorkspaceHeader } from "@/components/layout/workspace-header"
import {
  QueryContext,
  SourceToolbar,
  WorkspaceFooter,
} from "@/components/layout/query-context"

export function AppShell() {
  return (
    <SidebarProvider style={{ "--sidebar-width": "14.5rem" } as CSSProperties}>
      <a href="#main-content" className="skip-link">
        Saltar al contenido
      </a>
      <WorkspaceSidebar />
      <SidebarInset className="min-w-0">
        <WorkspaceHeader />
        <SourceToolbar />
        <main id="main-content" tabIndex={-1} className="page-container">
          <QueryContext />
          <Outlet />
        </main>
        <WorkspaceFooter />
      </SidebarInset>
    </SidebarProvider>
  )
}
